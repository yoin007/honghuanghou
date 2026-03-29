# -*- coding: utf-8 -*-
"""
AI诊疗 API

提供AI诊疗会话的管理功能
"""

import logging
from datetime import datetime, date
from typing import Optional, List
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    check_class_access,
    require_permission,
)
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/consultations", tags=["AI诊疗"])


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
    - xuefa/jiaowu/admin: 查看所有
    """
    with get_moral_db() as db:
        if not check_moral_permission(user, 'ai_consultation') and \
           not check_moral_permission(user, 'ai_consultation_own_class'):
            raise HTTPException(403, "权限不足")

        conditions = ["1=1"]
        params = []

        if student_id:
            conditions.append("ac.student_id = %s")
            params.append(student_id)

        if status:
            conditions.append("ac.status = %s")
            params.append(status)

        if consultation_type:
            conditions.append("ac.consultation_type = %s")
            params.append(consultation_type)

        if priority:
            conditions.append("ac.priority = %s")
            params.append(priority)

        where_clause = " AND ".join(conditions)

        count_query = f"SELECT COUNT(*) FROM ai_consultation ac WHERE {where_clause}"
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT ac.*, s.name as student_name, c.class_name
            FROM ai_consultation ac
            JOIN student s ON ac.student_id = s.student_id
            JOIN class c ON s.class_id = c.class_id
            WHERE {where_clause}
            ORDER BY ac.created_at DESC
            LIMIT %s OFFSET %s
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
    user: User = Depends(require_permission('ai_consultation_own_class'))
):
    """创建诊疗会话"""
    with get_moral_db() as db:
        # 获取学生信息
        student = db.query_one(
            """SELECT s.*, c.leader_name FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE s.student_id = %s""",
            (consultation.student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        # 权限检查：班主任只能处理本班
        if user.role == 'cleader' and student['leader_name'] != user.username:
            if not check_moral_permission(user, 'ai_consultation'):
                raise HTTPException(403, "只能处理本班学生")

        # 创建会话
        db.execute(
            """INSERT INTO ai_consultation
            (student_id, consultation_type, title, description, priority, creator)
            VALUES (%s, %s, %s, %s, %s, %s)""",
            (consultation.student_id, consultation.consultation_type,
             consultation.title, consultation.description,
             consultation.priority, user.username)
        )

        consultation_id = db.lastrowid()

        # 初始AI分析
        ai_analysis = generate_initial_analysis(consultation, student)
        if ai_analysis:
            db.execute(
                """UPDATE ai_consultation SET
                ai_analysis = %s, ai_suggestions = %s, ai_risk_assessment = %s
                WHERE id = %s""",
                (ai_analysis['analysis'], json.dumps(ai_analysis['suggestions'], ensure_ascii=False),
                 ai_analysis['risk_assessment'], consultation_id)
            )

        return {
            "success": True,
            "message": "诊疗会话创建成功",
            "data": {
                "id": consultation_id,
                "ai_analysis": ai_analysis
            }
        }


@router.get("/{consultation_id}", summary="获取诊疗会话详情")
async def get_consultation(
    consultation_id: int,
    user: User = Depends(get_current_user)
):
    """获取诊疗会话详情"""
    with get_moral_db() as db:
        consultation = db.query_one(
            """SELECT ac.*, s.name as student_name, c.class_name
            FROM ai_consultation ac
            JOIN student s ON ac.student_id = s.student_id
            JOIN class c ON s.class_id = c.class_id
            WHERE ac.id = %s""",
            (consultation_id,)
        )
        if not consultation:
            raise HTTPException(404, "诊疗会话不存在")

        # 获取消息列表
        messages = db.query_all(
            """SELECT * FROM ai_consultation_message
            WHERE consultation_id = %s
            ORDER BY created_at ASC""",
            (consultation_id,)
        )

        return {
            "success": True,
            "data": {
                "consultation": consultation,
                "messages": messages
            }
        }


@router.put("/{consultation_id}", summary="更新诊疗会话")
async def update_consultation(
    consultation_id: int,
    update_data: ConsultationUpdate,
    request: Request,
    user: User = Depends(require_permission('ai_consultation_own_class'))
):
    """更新诊疗会话"""
    with get_moral_db() as db:
        consultation = db.query_one(
            "SELECT * FROM ai_consultation WHERE id = %s",
            (consultation_id,)
        )
        if not consultation:
            raise HTTPException(404, "诊疗会话不存在")

        updates = []
        params = []

        if update_data.title is not None:
            updates.append("title = %s")
            params.append(update_data.title)

        if update_data.description is not None:
            updates.append("description = %s")
            params.append(update_data.description)

        if update_data.status is not None:
            updates.append("status = %s")
            params.append(update_data.status)

            if update_data.status == 'closed':
                updates.append("closed_at = NOW()")

        if update_data.priority is not None:
            updates.append("priority = %s")
            params.append(update_data.priority)

        if update_data.assignee is not None:
            updates.append("assignee = %s")
            params.append(update_data.assignee)

        if update_data.solution is not None:
            updates.append("solution = %s")
            params.append(update_data.solution)

        if update_data.outcome is not None:
            updates.append("outcome = %s")
            params.append(update_data.outcome)

        if update_data.follow_up_date is not None:
            updates.append("follow_up_date = %s")
            params.append(update_data.follow_up_date)

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(consultation_id)
        db.execute(
            f"UPDATE ai_consultation SET {', '.join(updates)} WHERE id = %s",
            tuple(params)
        )

        return {"success": True, "message": "更新成功"}


@router.post("/{consultation_id}/messages", summary="添加诊疗消息")
async def add_consultation_message(
    consultation_id: int,
    message: MessageCreate,
    request: Request,
    user: User = Depends(get_current_user)
):
    """添加诊疗消息"""
    with get_moral_db() as db:
        consultation = db.query_one(
            "SELECT * FROM ai_consultation WHERE id = %s",
            (consultation_id,)
        )
        if not consultation:
            raise HTTPException(404, "诊疗会话不存在")

        # 插入用户消息
        db.execute(
            """INSERT INTO ai_consultation_message
            (consultation_id, message_type, content, sender)
            VALUES (%s, %s, %s, %s)""",
            (consultation_id, message.message_type, message.content, user.username)
        )

        # 如果是用户消息，生成AI回复
        if message.message_type == 'user':
            ai_reply = generate_ai_reply(consultation, message.content)
            if ai_reply:
                db.execute(
                    """INSERT INTO ai_consultation_message
                    (consultation_id, message_type, content, sender)
                    VALUES (%s, 'ai', %s, 'AI助手')""",
                    (consultation_id, ai_reply)
                )

        return {"success": True, "message": "消息添加成功"}


@router.post("/{consultation_id}/close", summary="关闭诊疗会话")
async def close_consultation(
    consultation_id: int,
    outcome: Optional[str] = Query(None, description="处理结果"),
    request: Request = None,
    user: User = Depends(require_permission('ai_consultation_own_class'))
):
    """关闭诊疗会话"""
    with get_moral_db() as db:
        consultation = db.query_one(
            "SELECT * FROM ai_consultation WHERE id = %s",
            (consultation_id,)
        )
        if not consultation:
            raise HTTPException(404, "诊疗会话不存在")

        if consultation['status'] == 'closed':
            raise HTTPException(400, "会话已关闭")

        db.execute(
            """UPDATE ai_consultation SET
            status = 'closed', closed_at = NOW(), outcome = %s
            WHERE id = %s""",
            (outcome, consultation_id)
        )

        return {"success": True, "message": "会话已关闭"}


# =============================================================================
# 辅助函数
# =============================================================================

def generate_initial_analysis(consultation, student) -> dict:
    """生成初始AI分析"""
    # 简化版本，实际应调用AI模型
    analysis_templates = {
        'academic': f"针对学生{student['name']}的学业问题进行分析...",
        'behavior': f"针对学生{student['name']}的行为表现进行分析...",
        'psychological': f"针对学生{student['name']}的心理状况进行分析...",
        'comprehensive': f"对学生{student['name']}进行综合分析..."
    }

    suggestions_map = {
        'academic': ['加强课后辅导', '优化学习方法', '建立学习计划'],
        'behavior': ['加强日常关注', '家校沟通', '制定行为规范'],
        'psychological': ['心理咨询', '关爱陪伴', '积极引导'],
        'comprehensive': ['全面关注', '定期跟进', '多方协作']
    }

    consultation_type = consultation.consultation_type

    return {
        'analysis': analysis_templates.get(consultation_type, '暂无分析'),
        'suggestions': suggestions_map.get(consultation_type, []),
        'risk_assessment': 'low'
    }


def generate_ai_reply(consultation, user_message: str) -> str:
    """生成AI回复"""
    # 简化版本
    if '怎么办' in user_message or '如何' in user_message:
        return "建议您可以从以下几个方面入手：\n1. 了解具体原因\n2. 制定改进计划\n3. 持续跟进进展"

    return "感谢您的反馈，我会继续关注该学生的情况。如有其他问题，请随时沟通。"