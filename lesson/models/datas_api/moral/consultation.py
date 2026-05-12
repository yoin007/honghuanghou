# -*- coding: utf-8 -*-
"""
AI诊疗 API

提供AI诊疗会话的管理功能
"""

import logging
from datetime import datetime, date
from typing import Optional, List
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, BackgroundTasks
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission_for_roles,
    get_api_scoped_user_roles,
    get_record_data_scope,
    record_in_scope,
    target_student_in_scope,
)
from models.datas_api.auth import User, get_current_user

# 导入 AI 调用模块（放在顶部，确保后续函数可用）
from .consultation_ai import (
    generate_initial_analysis as ai_generate_initial_analysis,
    detect_followup_type,
    generate_followup_analysis,
    generate_closure_report,
    calculate_days_elapsed
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/consultations", tags=["AI诊疗"])

API_CONSULTATION_LIST = "/api/moral/consultations"
API_CONSULTATION_CREATE = "/api/moral/consultations/create"
API_CONSULTATION_UPDATE = "/api/moral/consultations/update"
API_CONSULTATION_CLOSE = "/api/moral/consultations/close"


def _has_consultation_permission(db, user: User, api_path: str) -> bool:
    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    return any(
        check_moral_permission_for_roles(scoped_roles, permission)
        for permission in ['ai_consultation', 'ai_consultation_own_class']
    )


def _consultation_scope(db, user: User, api_path: str = API_CONSULTATION_LIST) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['ai_consultation'],
        own_class_permissions=['ai_consultation_own_class'],
        own_permissions=['ai_consultation_own_class'],
    )


def _append_consultation_scope_condition(conditions: List[str], params: List, scope: dict, username: str) -> None:
    if scope.get("can_all"):
        return

    parts = []
    if scope.get("can_own"):
        parts.append("ac.creator = ?")
        params.append(username)

    my_class_ids = scope.get("my_class_ids") or []
    if scope.get("can_own_class") and my_class_ids:
        placeholders = ", ".join(["?"] * len(my_class_ids))
        parts.append(f"s.class_id IN ({placeholders})")
        params.extend(my_class_ids)
    elif scope.get("can_own_class") and scope.get("my_class_id") is not None:
        parts.append("s.class_id = ?")
        params.append(scope["my_class_id"])

    my_grade_class_ids = scope.get("my_grade_class_ids") or []
    if scope.get("can_own_grade") and my_grade_class_ids:
        placeholders = ", ".join(["?"] * len(my_grade_class_ids))
        parts.append(f"s.class_id IN ({placeholders})")
        params.extend(my_grade_class_ids)

    teaching_class_ids = scope.get("teaching_class_ids") or []
    if scope.get("can_teaching_classes"):
        if teaching_class_ids:
            placeholders = ", ".join(["?"] * len(teaching_class_ids))
            parts.append(f"s.class_id IN ({placeholders})")
            params.extend(teaching_class_ids)
        else:
            return

    conditions.append("(" + " OR ".join(parts) + ")" if parts else "1 = 0")


def _ensure_consultation_in_scope(db, user: User, consultation_id: int, api_path: str) -> dict:
    consultation = db.query_one(
        """SELECT ac.*, s.class_id, s.grade_id, s.name as student_name, s.gender, c.class_name
        FROM ai_consultation ac
        JOIN student s ON ac.student_id = s.student_id
        JOIN class c ON s.class_id = c.class_id
        WHERE ac.id = ?""",
        (consultation_id,)
    )
    if not consultation:
        raise HTTPException(404, "诊疗会话不存在")

    scope = _consultation_scope(db, user, api_path)
    if not record_in_scope(consultation, scope, username=user.username, recorder_field="creator"):
        raise HTTPException(403, "只能访问授权范围内的诊疗会话")
    return consultation


# =============================================================================
# Pydantic 模型
# =============================================================================

class ConsultationCreate(BaseModel):
    """创建诊疗会话"""
    student_id: str = Field(..., description="学号")
    consultation_type: str = Field(..., description="诊疗类型：academic/behavior/psychological/comprehensive")
    title: Optional[str] = Field(None, description="标题")
    description: Optional[str] = Field(None, description="问题描述")
    priority: Optional[str] = Field("normal", description="优先级：urgent/high/normal/low")


class ConsultationUpdate(BaseModel):
    """更新诊疗会话"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    solution: Optional[str] = None
    outcome: Optional[str] = None
    follow_up_date: Optional[date] = None


class MessageCreate(BaseModel):
    """创建消息"""
    content: str = Field(..., description="消息内容")
    message_type: Optional[str] = Field("user", description="消息类型：user/ai/system")


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="获取诊疗会话列表")
async def get_consultations(
    student_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    consultation_type: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """
    获取诊疗会话列表

    权限说明：
    - cleader: 查看本班学生
    - g_leader: 查看本年级学生
    - xuefa/jiaowu/admin: 查看所有
    """
    with get_moral_db() as db:
        if not _has_consultation_permission(db, user, API_CONSULTATION_LIST):
            raise HTTPException(403, "权限不足")

        conditions = ["1=1"]
        params = []
        view_scope = _consultation_scope(db, user, API_CONSULTATION_LIST)
        _append_consultation_scope_condition(conditions, params, view_scope, user.username)

        if student_id:
            conditions.append("ac.student_id = ?")
            params.append(student_id)

        if status:
            conditions.append("ac.status = ?")
            params.append(status)

        if consultation_type:
            conditions.append("ac.consultation_type = ?")
            params.append(consultation_type)

        if priority:
            conditions.append("ac.priority = ?")
            params.append(priority)

        where_clause = " AND ".join(conditions)

        count_query = f"SELECT COUNT(*) FROM ai_consultation ac JOIN student s ON ac.student_id = s.student_id WHERE {where_clause}"
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT ac.*, s.name as student_name, c.class_name
            FROM ai_consultation ac
            JOIN student s ON ac.student_id = s.student_id
            JOIN class c ON s.class_id = c.class_id
            WHERE {where_clause}
            ORDER BY ac.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        consultations = db.query_all(data_query, tuple(params))

        return {
            "success": True,
            "data": {
                "items": consultations,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


@router.post("", summary="创建诊疗会话")
async def create_consultation(
    consultation: ConsultationCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """创建诊疗会话 - 异步处理 AI 分析"""
    with get_moral_db() as db:
        if not _has_consultation_permission(db, user, API_CONSULTATION_CREATE):
            raise HTTPException(403, "权限不足")

        # 获取学生信息
        student = db.query_one(
            """SELECT s.*, c.leader_name, c.class_name FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE s.student_id = ?""",
            (consultation.student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        if not target_student_in_scope(db, user, API_CONSULTATION_CREATE, student):
            raise HTTPException(403, "不能给授权范围外的学生创建诊疗会话")

        # 创建会话（初始状态为 pending）
        db.execute(
            """INSERT INTO ai_consultation
            (student_id, consultation_type, title, description, priority, creator)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (consultation.student_id, consultation.consultation_type,
             consultation.title, consultation.description,
             consultation.priority, user.username)
        )

        consultation_id = db.lastrowid()

    # 构建学生信息字典（用于 AI 分析）
    student_info = {
        'name': student.get('name', ''),
        'class_name': student.get('class_name', ''),
        'gender': student.get('gender', '未知')
    }

    # 注册后台任务 - AI 分析异步执行
    background_tasks.add_task(
        run_ai_analysis_background,
        consultation_id,
        consultation.consultation_type,
        student_info,
        consultation.description,
        consultation.priority
    )

    return {
        "success": True,
        "message": "诊疗会话创建成功，AI 分析正在生成中",
        "data": {
            "id": consultation_id,
            "ai_analysis_status": "pending",
            "ai_analysis": None
        }
    }


def run_ai_analysis_background(
    consultation_id: int,
    consultation_type: str,
    student: dict,
    description: str,
    priority: str
):
    """后台任务：执行 AI 分析并更新数据库"""
    try:
        from .consultation_ai import generate_initial_analysis as ai_gen

        # 调用 AI 分析
        ai_result = ai_gen(
            consultation_type=consultation_type,
            student=student,
            description=description,
            priority=priority
        )

        # 更新分析结果
        with get_moral_db() as db:
            db.execute(
                """UPDATE ai_consultation SET
                ai_analysis = ?, ai_suggestions = ?, ai_risk_assessment = ?
                WHERE id = ?""",
                (ai_result['analysis'],
                 json.dumps(ai_result['suggestions'], ensure_ascii=False),
                 ai_result['risk_assessment'],
                 consultation_id)
            )

            # 如果有高风险，插入一条系统提示消息
            if ai_result['risk_assessment'] == 'high':
                db.execute(
                    """INSERT INTO ai_consultation_message
                    (consultation_id, message_type, content, sender)
                    VALUES (?, 'system', '⚠️ 本次分析检测到高风险信号，请立即查看并采取行动。', '系统')""",
                    (consultation_id,)
                )

        logger.info(f"AI 分析完成: consultation_id={consultation_id}, risk={ai_result['risk_assessment']}")

    except Exception as e:
        logger.error(f"AI 异步分析失败: consultation_id={consultation_id}, error={e}")
        with get_moral_db() as db:
            db.execute(
                """UPDATE ai_consultation SET
                ai_analysis = 'AI 分析失败，请稍后手动请求分析。',
                ai_risk_assessment = 'unknown'
                WHERE id = ?""",
                (consultation_id,)
            )


@router.get("/{consultation_id}", summary="获取诊疗会话详情")
async def get_consultation(
    consultation_id: int,
    user: User = Depends(get_current_user)
):
    """获取诊疗会话详情"""
    with get_moral_db() as db:
        consultation = _ensure_consultation_in_scope(db, user, consultation_id, API_CONSULTATION_LIST)

        # 获取消息列表
        messages = db.query_all(
            """SELECT id, consultation_id, message_type as sender_type,
                      content, sender, created_at
            FROM ai_consultation_message
            WHERE consultation_id = ?
            ORDER BY created_at ASC""",
            (consultation_id,)
        )

        # 直接返回 consultation 对象，messages 作为属性
        consultation['messages'] = messages

        return {
            "success": True,
            "data": consultation  # 直接返回 consultation，前端可直接访问字段
        }


@router.put("/{consultation_id}", summary="更新诊疗会话")
async def update_consultation(
    consultation_id: int,
    update_data: ConsultationUpdate,
    request: Request,
    user: User = Depends(get_current_user)
):
    """更新诊疗会话"""
    with get_moral_db() as db:
        if not _has_consultation_permission(db, user, API_CONSULTATION_UPDATE):
            raise HTTPException(403, "权限不足")
        _ensure_consultation_in_scope(db, user, consultation_id, API_CONSULTATION_UPDATE)

        updates = []
        params = []

        if update_data.title is not None:
            updates.append("title = ?")
            params.append(update_data.title)

        if update_data.description is not None:
            updates.append("description = ?")
            params.append(update_data.description)

        if update_data.status is not None:
            updates.append("status = ?")
            params.append(update_data.status)

            if update_data.status == 'closed':
                updates.append("closed_at = datetime('now','localtime')")

        if update_data.priority is not None:
            updates.append("priority = ?")
            params.append(update_data.priority)

        if update_data.assignee is not None:
            updates.append("assignee = ?")
            params.append(update_data.assignee)

        if update_data.solution is not None:
            updates.append("solution = ?")
            params.append(update_data.solution)

        if update_data.outcome is not None:
            updates.append("outcome = ?")
            params.append(update_data.outcome)

        if update_data.follow_up_date is not None:
            updates.append("follow_up_date = ?")
            params.append(update_data.follow_up_date)

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(consultation_id)
        db.execute(
            f"UPDATE ai_consultation SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )

        return {"success": True, "message": "更新成功"}


@router.post("/{consultation_id}/messages", summary="添加诊疗消息")
async def add_consultation_message(
    consultation_id: int,
    message: MessageCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user)
):
    """添加诊疗消息 - 异步生成 AI 回复"""
    with get_moral_db() as db:
        if not _has_consultation_permission(db, user, API_CONSULTATION_UPDATE):
            raise HTTPException(403, "权限不足")
        consultation = _ensure_consultation_in_scope(db, user, consultation_id, API_CONSULTATION_UPDATE)

        # 获取历史消息（用于 AI 分析上下文）
        history_messages = db.query_all(
            """SELECT * FROM ai_consultation_message
            WHERE consultation_id = ?
            ORDER BY created_at ASC""",
            (consultation_id,)
        )

        # 插入用户消息（立即返回）
        db.execute(
            """INSERT INTO ai_consultation_message
            (consultation_id, message_type, content, sender)
            VALUES (?, ?, ?, ?)""",
            (consultation_id, message.message_type or 'user', message.content, user.username)
        )

        message_id = db.lastrowid()

    # 异步生成 AI 回复（不阻塞请求）
    if message.message_type != 'ai':
        background_tasks.add_task(
            generate_ai_reply_background,
            consultation_id,
            message.content,
            history_messages,
            consultation
        )

    # 立即返回成功，前端轮询刷新
    return {
        "success": True,
        "message": "消息已发送，AI回复正在生成",
        "data": {
            "message_id": message_id,
            "ai_pending": message.message_type != 'ai'
        }
    }


def generate_ai_reply_background(
    consultation_id: int,
    user_message: str,
    history_messages: list,
    consultation: dict
):
    """后台任务：生成 AI 回复"""
    try:
        # 构建 student 信息
        student = {
            'name': consultation.get('student_name', ''),
            'class_name': consultation.get('class_name', ''),
            'gender': consultation.get('gender', '未知')
        }

        # 获取上次分析
        last_analysis = consultation.get('ai_analysis', '')
        if not last_analysis and history_messages:
            for msg in reversed(history_messages):
                if msg.get('message_type') == 'ai':
                    last_analysis = msg.get('content', '')[:600]
                    break

        # 计算天数和检测追问类型
        days_elapsed = calculate_days_elapsed(consultation.get('created_at', ''))
        followup_type = detect_followup_type(
            consultation.get('consultation_type', 'comprehensive'),
            user_message,
            days_elapsed
        )

        # 调用 AI
        ai_reply = generate_followup_analysis(
            consultation_type=consultation.get('consultation_type', 'comprehensive'),
            followup_type=followup_type,
            student=student,
            teacher_message=user_message,
            last_analysis=last_analysis,
            days_elapsed=days_elapsed,
            current_risk_level=consultation.get('ai_risk_assessment', 'low')
        )

        # 保存 AI 回复
        with get_moral_db() as db:
            db.execute(
                """INSERT INTO ai_consultation_message
                (consultation_id, message_type, content, sender)
                VALUES (?, 'ai', ?, 'AI助手')""",
                (consultation_id, ai_reply)
            )

            # 更新 ai_analysis 字段（最新分析）
            db.execute(
                """UPDATE ai_consultation SET ai_analysis = ? WHERE id = ?""",
                (ai_reply[:2000], consultation_id)
            )

        logger.info(f"AI回复生成完成: consultation_id={consultation_id}")

    except Exception as e:
        logger.error(f"AI回复生成失败: {e}")
        with get_moral_db() as db:
            db.execute(
                """INSERT INTO ai_consultation_message
                (consultation_id, message_type, content, sender)
                VALUES (?, 'ai', 'AI分析暂时不可用，请稍后重试。', 'AI助手')""",
                (consultation_id,)
            )


@router.post("/{consultation_id}/close", summary="关闭诊疗会话")
async def close_consultation(
    consultation_id: int,
    outcome: Optional[str] = Query(None, description="处理结果"),
    request: Request = None,
    user: User = Depends(get_current_user)
):
    """关闭诊疗会话"""
    with get_moral_db() as db:
        if not _has_consultation_permission(db, user, API_CONSULTATION_CLOSE):
            raise HTTPException(403, "权限不足")
        consultation = _ensure_consultation_in_scope(db, user, consultation_id, API_CONSULTATION_CLOSE)

        if consultation['status'] == 'closed':
            raise HTTPException(400, "会话已关闭")

        db.execute(
            """UPDATE ai_consultation SET
            status = 'closed', closed_at = datetime('now','localtime'), outcome = ?
            WHERE id = ?""",
            (outcome, consultation_id)
        )

        return {"success": True, "message": "会话已关闭"}


# =============================================================================
# 辅助函数
# =============================================================================


def generate_initial_analysis(consultation, student) -> dict:
    """
    生成初始AI分析 - 调用真实 AI 模型

    Args:
        consultation: ConsultationCreate 模型对象
        student: 学生信息字典

    Returns:
        dict: 包含 analysis, suggestions, risk_assessment
    """
    try:
        return ai_generate_initial_analysis(
            consultation_type=consultation.consultation_type,
            student=student,
            description=consultation.description,
            priority=consultation.priority
        )
    except Exception as e:
        logger.error(f"AI 初始分析失败: {e}")
        # 降级处理：返回简单模板
        return {
            'analysis': f"针对学生{student.get('name', '该学生')}的{consultation.consultation_type}问题进行分析。\n\nAI分析暂时不可用，请稍后重试或手动补充分析。",
            'suggestions': ['请稍后重新请求AI分析'],
            'risk_assessment': 'low'
        }


def generate_ai_reply(consultation: dict, user_message: str, messages: list = None) -> str:
    """
    根据教师消息生成AI追问分析 - 调用真实 AI 模型

    Args:
        consultation: 诊疗会话信息字典
        user_message: 教师发送的消息内容
        messages: 历史消息列表（可选）

    Returns:
        str: AI 回复内容
    """
    try:
        # 计算持续天数
        days_elapsed = calculate_days_elapsed(consultation.get('created_at', ''))

        # 获取上次分析摘要（从 ai_analysis 字段或最近 AI 消息）
        last_analysis = consultation.get('ai_analysis', '')
        if not last_analysis and messages:
            # 从历史消息中提取最近的 AI 回复
            for msg in reversed(messages):
                if msg.get('sender_type') == 'ai' or msg.get('message_type') == 'ai':
                    last_analysis = msg.get('content', '')[:600]
                    break

        # 构建学生信息
        student = {
            'name': consultation.get('student_name', ''),
            'class_name': consultation.get('class_name', ''),
            'gender': '未知'  # 可以从其他字段补充
        }

        # 检测追问类型
        followup_type = detect_followup_type(
            consultation_type=consultation.get('consultation_type', 'comprehensive'),
            teacher_message=user_message,
            days_elapsed=days_elapsed
        )

        # 生成追问分析
        return generate_followup_analysis(
            consultation_type=consultation.get('consultation_type', 'comprehensive'),
            followup_type=followup_type,
            student=student,
            teacher_message=user_message,
            last_analysis=last_analysis,
            days_elapsed=days_elapsed,
            current_risk_level=consultation.get('ai_risk_assessment', 'low')
        )
    except Exception as e:
        logger.error(f"AI 追问分析失败: {e}")
        return f"AI 分析暂时不可用，请稍后重试。\n\n错误详情：{str(e)}"
