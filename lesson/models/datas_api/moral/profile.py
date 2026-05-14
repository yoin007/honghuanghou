# -*- coding: utf-8 -*-
"""
学生画像 API

提供学生画像的生成和查询功能
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal
import json
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    get_current_semester,
    get_teacher_class_id,
    has_user_role,
    check_moral_permission_for_roles,
    get_api_scoped_user_roles,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
)
from .api_permission import require_configured_api_permission
from models.datas_api.auth import User
from .ai_model_config import get_current_model

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["学生画像"])

API_PROFILE_VIEW = "/api/moral/profiles/student/{student_id}"
API_PROFILE_GENERATE = "/api/moral/profiles/student/{student_id}/generate"
API_PROFILE_GENERATE_ASYNC = "/api/moral/profiles/student/{student_id}/generate-async"
API_PROFILE_GENERATION_STATUS = "/api/moral/profiles/generation-status/{job_id}"
API_PROFILE_BATCH_GENERATE = "/api/moral/profiles/batch-generate"
API_PROFILE_CONFIG = "/api/moral/profiles/config"
API_PROFILE_LIST = "/api/moral/profiles"
PROFILE_GENERATION_JOBS: Dict[str, Dict[str, Any]] = {}
PROFILE_JOB_TTL_SECONDS = 30 * 60


def _scoped_roles(db, user: User, api_path: str) -> List[str]:
    return get_api_scoped_user_roles(db, user, api_path)


def _has_scoped_permission(db, user: User, api_path: str, permission: str) -> bool:
    return check_moral_permission_for_roles(_scoped_roles(db, user, api_path), permission)


def _student_allowed_by_profile_scope(db, user: User, student: dict, api_path: str) -> bool:
    if has_user_role(user, 'student'):
        return user.username == student.get('student_id')
    scope = get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['student_profile', 'profile_view_all'],
        own_class_permissions=['student_profile_own_class', 'profile_view_own_class'],
        own_permissions=[],
    )
    return record_in_scope(student, scope, username=user.username, recorder_field='student_id')


def _cleanup_profile_jobs() -> None:
    now = time.time()
    expired = [
        job_id for job_id, job in PROFILE_GENERATION_JOBS.items()
        if now - job.get('created_at', now) > PROFILE_JOB_TTL_SECONDS
    ]
    for job_id in expired:
        PROFILE_GENERATION_JOBS.pop(job_id, None)


def _generate_student_profile_payload(student_id: str, use_ai: bool = True, generated_by: str = None) -> dict:
    """生成并保存单个学生画像，返回前端可直接展示的数据。"""
    with get_moral_db() as db:
        student = db.query_one(
            """SELECT s.*, c.class_name, g.grade_name
            FROM student s
            LEFT JOIN class c ON s.class_id = c.class_id
            LEFT JOIN grade g ON s.grade_id = g.grade_id
            WHERE s.student_id = ?""",
            (student_id,)
        )
        if not student:
            raise ValueError("学生不存在")

        current_semester = get_current_semester(db)
        semester_id = current_semester['semester_id'] if current_semester else None

        # 使用全量数据生成画像（一生一册模式）
        analysis = analyze_student_data(db, student_id, None)
        config = get_all_profile_config(db)
        profile_output = build_profile_output(student, analysis, config, use_ai=use_ai)

        profile_summary = profile_output['profile_summary']
        profile_tags = profile_output['profile_tags']
        strength_tags = profile_output['strength_tags']
        improvement_tags = profile_output['improvement_tags']
        moral_score = profile_output['scores']['moral']
        attitude_score = profile_output['scores']['attitude']
        social_score = profile_output['scores']['social']
        growth_score = profile_output['scores']['growth']
        risk_level = profile_output['risk_level']
        suggestions = profile_output['suggestions']

        current_version = db.query_value(
            "SELECT MAX(profile_version) FROM student_profile WHERE student_id = ?",
            (student_id,)
        ) or 0
        new_version = current_version + 1

        db.execute(
            """INSERT INTO student_profile
            (student_id, profile_version, profile_summary, profile_tags, strength_tags,
             improvement_tags, risk_level, moral_score, attitude_score, social_score,
             growth_score, suggestions, data_source_summary, generated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                student_id,
                new_version,
                profile_summary,
                json.dumps(profile_tags, ensure_ascii=False, cls=DecimalEncoder),
                json.dumps(strength_tags, ensure_ascii=False, cls=DecimalEncoder),
                json.dumps(improvement_tags, ensure_ascii=False, cls=DecimalEncoder),
                risk_level,
                moral_score,
                attitude_score,
                social_score,
                growth_score,
                suggestions,
                json.dumps(analysis, ensure_ascii=False, cls=DecimalEncoder),
                generated_by
            )
        )
        profile_id = db.lastrowid()

        profile_data = {
            'profile_summary': profile_summary,
            'profile_tags': profile_tags,
            'scores': {
                'moral': moral_score,
                'attitude': attitude_score,
                'social': social_score,
                'growth': growth_score
            },
            'risk_level': risk_level,
            'suggestions': suggestions,
            'analysis': analysis
        }
        db.execute(
            """INSERT INTO student_profile_history
            (student_id, profile_version, profile_data)
            VALUES (?, ?, ?)""",
            (student_id, new_version, json.dumps(profile_data, ensure_ascii=False, cls=DecimalEncoder))
        )

        return {
            "profile_id": profile_id,
            "student_id": student_id,
            "student_name": student.get('name', ''),
            "class_name": student.get('class_name', ''),
            "grade_name": student.get('grade_name', ''),
            "profile_summary": profile_summary,
            "profile_tags": profile_tags,
            "strength_tags": strength_tags,
            "improvement_tags": improvement_tags,
            "risk_level": risk_level,
            "suggestions": suggestions,
            "scores": {
                "moral": moral_score,
                "attitude": attitude_score,
                "social": social_score,
                "growth": growth_score
            },
            "analysis": analysis,
            "generated_at": datetime.now().isoformat(),
            "ai_used": profile_output.get('ai_used', False)
        }


def _run_profile_generation_job(job_id: str, student_id: str) -> None:
    job = PROFILE_GENERATION_JOBS.get(job_id)
    if not job:
        return
    generated_by = job.get('generated_by')
    job.update({"status": "running", "message": "正在生成学生画像"})
    try:
        data = _generate_student_profile_payload(student_id, use_ai=True, generated_by=generated_by)
        job.update({
            "status": "success",
            "message": "画像生成成功",
            "data": data,
            "finished_at": time.time(),
        })
    except Exception as exc:
        logger.exception("学生画像异步生成失败: ?", exc)
        job.update({
            "status": "failed",
            "message": str(exc) or "画像生成失败",
            "finished_at": time.time(),
        })


def _run_profile_batch_generation_job(job_id: str) -> None:
    job = PROFILE_GENERATION_JOBS.get(job_id)
    if not job:
        return
    students = job.get('students') or []
    semester_id = job.get('semester_id')
    generated_by = job.get('generated_by')
    job.update({
        "status": "running",
        "message": "正在批量生成学生画像",
        "started_at": time.time(),
    })
    success_count = 0
    errors = []
    generated_profiles = []
    try:
        with get_moral_db() as db:
            for index, student in enumerate(students, start=1):
                job.update({
                    "current": index,
                    "current_student_id": student.get('student_id'),
                    "current_student_name": student.get('name') or student.get('student_id'),
                    "message": f"正在生成 {index}/{len(students)}",
                })
                try:
                    result = generate_single_profile_internal(
                        db,
                        student['student_id'],
                        semester_id,
                        generated_by=generated_by,
                    )
                    success_count += 1
                    if len(generated_profiles) < 20:
                        generated_profiles.append(result)
                except Exception as exc:
                    error_msg = f"{student.get('student_id')}({student.get('name', '')}): {str(exc)}"
                    errors.append(error_msg)
                    logger.error("批量生成画像失败: %s", error_msg)
                job.update({
                    "success_count": success_count,
                    "error_count": len(errors),
                    "errors": errors[:10],
                    "generated_profiles": generated_profiles,
                })

        job.update({
            "status": "success" if not errors else "partial_success",
            "message": f"批量生成完成：成功 {success_count} 个，失败 {len(errors)} 个",
            "success_count": success_count,
            "error_count": len(errors),
            "errors": errors[:10],
            "generated_profiles": generated_profiles,
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "total_count": len(students),
                "errors": errors[:10],
                "generated_profiles": generated_profiles,
            },
            "finished_at": time.time(),
        })
    except Exception as exc:
        logger.exception("学生画像批量生成任务失败: %s", exc)
        job.update({
            "status": "failed",
            "message": str(exc) or "批量生成画像任务失败",
            "success_count": success_count,
            "error_count": len(errors) + 1,
            "errors": (errors + [str(exc)])[:10],
            "finished_at": time.time(),
        })


class DecimalEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理Decimal类型"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# =============================================================================
# Pydantic 模型
# =============================================================================

class ProfileUpdate(BaseModel):
    """更新学生画像"""
    profile_summary: Optional[str] = Field(None, description="画像摘要")
    profile_tags: Optional[List[str]] = Field(None, description="画像标签")
    strength_tags: Optional[List[str]] = Field(None, description="优势标签")
    improvement_tags: Optional[List[str]] = Field(None, description="待改进标签")
    risk_level: Optional[str] = Field(None, description="风险等级")
    suggestions: Optional[str] = Field(None, description="个性化建议")


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="获取画像列表")
async def list_profiles(
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_configured_api_permission(API_PROFILE_LIST, "GET", allow_missing=False))
):
    """
    获取已生成画像的学生列表

    权限说明：
    - 班主任只能查看本班学生
    - xuefa/jiaowu/admin 可查看所有
    """
    with get_moral_db() as db:
        scope = get_record_data_scope(
            db,
            user,
            API_PROFILE_LIST,
            all_permissions=['student_profile', 'profile_view_all'],
            own_class_permissions=['student_profile_own_class', 'profile_view_own_class'],
            own_permissions=[],
        )

        # 构建查询条件
        conditions = ["sp.id IS NOT NULL"]
        params = []

        if class_id:
            conditions.append("s.class_id = ?")
            params.append(class_id)

        if grade_id:
            conditions.append("s.grade_id = ?")
            params.append(grade_id)

        # 数据范围筛选（使用配置驱动的数据范围规则）
        append_record_scope_condition(
            conditions,
            params,
            scope,
            table_alias="s",
            class_field="class_id",
            username=user.username,
        )

        # 查询总数
        count_query = f"""
            SELECT COUNT(DISTINCT s.student_id)
            FROM student s
            JOIN student_profile sp ON s.student_id = sp.student_id
            WHERE {' AND '.join(conditions)}
        """
        total = db.query_value(count_query, tuple(params) if params else None) or 0

        # 分页查询
        offset = (page - 1) * page_size
        list_query = f"""
            SELECT
                s.student_id,
                s.name as student_name,
                c.class_name,
                g.grade_name,
                sp.profile_version,
                sp.generated_at,
                sp.generated_by,
                sp.risk_level,
                sp.moral_score,
                sp.attitude_score,
                sp.social_score,
                sp.growth_score
            FROM student s
            JOIN student_profile sp ON s.student_id = sp.student_id
            LEFT JOIN class c ON s.class_id = c.class_id
            LEFT JOIN grade g ON s.grade_id = g.grade_id
            WHERE {' AND '.join(conditions)}
            GROUP BY s.student_id
            ORDER BY sp.generated_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        profiles = db.query_all(list_query, tuple(params))

        return {
            "success": True,
            "data": {
                "profiles": profiles,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


@router.get("/student/{student_id}", summary="获取学生画像")
async def get_student_profile(
    student_id: str,
    user: User = Depends(require_configured_api_permission(API_PROFILE_VIEW, "GET", allow_missing=False))
):
    """
    获取学生画像

    权限说明：
    - 学生只能查看自己的画像
    - 家长只能查看子女的画像
    - 班主任可查看本班学生
    - xuefa/jiaowu/admin 可查看所有
    """
    with get_moral_db() as db:
        # 权限检查
        if has_user_role(user, 'student') and user.username != student_id:
            raise HTTPException(403, "只能查看自己的画像")

        # 获取学生信息
        student = db.query_one(
            """SELECT s.*, c.class_name, c.leader_name
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE s.student_id = ?""",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        if not _student_allowed_by_profile_scope(db, user, student, API_PROFILE_VIEW):
            raise HTTPException(403, "只能查看授权范围内学生画像")

        # 获取最新画像
        profile = db.query_one(
            """SELECT * FROM student_profile
            WHERE student_id = ?
            ORDER BY profile_version DESC LIMIT 1""",
            (student_id,)
        )

        # 获取画像历史
        history = db.query_all(
            """SELECT id, profile_version, created_at,
            JSON_EXTRACT(profile_data, '$.profile_summary') as summary
            FROM student_profile_history
            WHERE student_id = ?
            ORDER BY profile_version DESC
            LIMIT 10""",
            (student_id,)
        )

        return {
            "success": True,
            "data": {
                "student": {
                    "student_id": student['student_id'],
                    "name": student['name'],
                    "class_name": student['class_name']
                },
                "profile": profile,
                "history": history
            }
        }


@router.post("/student/{student_id}/generate", summary="生成学生画像")
async def generate_student_profile(
    student_id: str,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PROFILE_GENERATE, "POST", allow_missing=False))
):
    """
    生成学生画像（基于德育数据分析）

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        if not (
            _has_scoped_permission(db, user, API_PROFILE_GENERATE, 'student_profile')
            or _has_scoped_permission(db, user, API_PROFILE_GENERATE, 'student_profile_own_class')
        ):
            raise HTTPException(403, "权限不足：需要学生画像生成权限")

        # 获取学生信息（包含班级和年级名称）
        student = db.query_one(
            """SELECT s.*, c.class_name, g.grade_name
            FROM student s
            LEFT JOIN class c ON s.class_id = c.class_id
            LEFT JOIN grade g ON s.grade_id = g.grade_id
            WHERE s.student_id = ?""",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        if not _student_allowed_by_profile_scope(db, user, student, API_PROFILE_GENERATE):
            raise HTTPException(403, "只能生成授权范围内学生画像")

    data = _generate_student_profile_payload(student_id, use_ai=True, generated_by=user.username)
    return {"success": True, "message": "画像生成成功", "data": data}


@router.post("/student/{student_id}/generate-async", summary="异步生成学生画像")
async def generate_student_profile_async(
    student_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_configured_api_permission(API_PROFILE_GENERATE_ASYNC, "POST", allow_missing=False))
):
    """创建画像生成任务，立即返回任务ID，由前端轮询结果。"""
    _cleanup_profile_jobs()
    with get_moral_db() as db:
        if not (
            _has_scoped_permission(db, user, API_PROFILE_GENERATE, 'student_profile')
            or _has_scoped_permission(db, user, API_PROFILE_GENERATE, 'student_profile_own_class')
        ):
            raise HTTPException(403, "权限不足：需要学生画像生成权限")

        student = db.query_one(
            """SELECT s.*, c.class_name, g.grade_name
            FROM student s
            LEFT JOIN class c ON s.class_id = c.class_id
            LEFT JOIN grade g ON s.grade_id = g.grade_id
            WHERE s.student_id = ?""",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")
        if not _student_allowed_by_profile_scope(db, user, student, API_PROFILE_GENERATE):
            raise HTTPException(403, "只能生成授权范围内学生画像")

    job_id = uuid.uuid4().hex
    PROFILE_GENERATION_JOBS[job_id] = {
        "job_id": job_id,
        "student_id": student_id,
        "generated_by": user.username,
        "status": "queued",
        "message": "画像生成任务已提交",
        "created_at": time.time(),
    }
    background_tasks.add_task(_run_profile_generation_job, job_id, student_id)
    return {
        "success": True,
        "message": "画像生成任务已提交",
        "data": {"job_id": job_id, "status": "queued"}
    }


@router.get("/generation-status/{job_id}", summary="查询画像生成任务状态")
async def get_profile_generation_status(
    job_id: str,
    user: User = Depends(require_configured_api_permission(API_PROFILE_GENERATION_STATUS, "GET", allow_missing=False))
):
    """查询画像生成任务状态。"""
    _cleanup_profile_jobs()
    job = PROFILE_GENERATION_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "画像生成任务不存在或已过期")
    return {
        "success": True,
        "data": {
            "job_id": job_id,
            "student_id": job.get("student_id"),
            "status": job.get("status"),
            "message": job.get("message"),
            "total_count": job.get("total_count"),
            "success_count": job.get("success_count"),
            "error_count": job.get("error_count"),
            "current": job.get("current"),
            "current_student_id": job.get("current_student_id"),
            "current_student_name": job.get("current_student_name"),
            "errors": job.get("errors") or [],
            "generated_profiles": job.get("generated_profiles") or [],
            "data": job.get("data"),
        }
    }


def generate_single_profile_internal(db, student_id: str, semester_id: int, generated_by: str = None) -> dict:
    """
    单个学生画像生成的内部函数（用于批量生成）

    Args:
        db: 数据库连接
        student_id: 学生ID
        semester_id: 学期ID
        generated_by: 生成人用户名

    Returns:
        dict: 生成结果
    """
    # 获取学生信息
    student = db.query_one(
        """SELECT s.*, c.class_name, g.grade_name
        FROM student s
        LEFT JOIN class c ON s.class_id = c.class_id
        LEFT JOIN grade g ON s.grade_id = g.grade_id
        WHERE s.student_id = ?""",
        (student_id,)
    )
    if not student:
        raise ValueError(f"学生不存在: {student_id}")

    # 分析学生数据
    analysis = analyze_student_data(db, student_id, semester_id)

    # 获取配置
    config = get_all_profile_config(db)

    profile_output = build_profile_output(student, analysis, config, use_ai=False)
    profile_summary = profile_output['profile_summary']
    profile_tags = profile_output['profile_tags']
    strength_tags = profile_output['strength_tags']
    improvement_tags = profile_output['improvement_tags']
    moral_score = profile_output['scores']['moral']
    attitude_score = profile_output['scores']['attitude']
    social_score = profile_output['scores']['social']
    growth_score = profile_output['scores']['growth']
    risk_level = profile_output['risk_level']
    suggestions = profile_output['suggestions']

    # 获取当前版本号
    current_version = db.query_value(
        "SELECT MAX(profile_version) FROM student_profile WHERE student_id = ?",
        (student_id,)
    ) or 0

    new_version = current_version + 1

    # 保存画像
    db.execute(
        """INSERT INTO student_profile
        (student_id, profile_version, profile_summary, profile_tags, strength_tags,
         improvement_tags, risk_level, moral_score, attitude_score, social_score,
         growth_score, suggestions, data_source_summary, generated_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            student_id,
            new_version,
            profile_summary,
            json.dumps(profile_tags, ensure_ascii=False, cls=DecimalEncoder),
            json.dumps(strength_tags, ensure_ascii=False, cls=DecimalEncoder),
            json.dumps(improvement_tags, ensure_ascii=False, cls=DecimalEncoder),
            risk_level,
            moral_score,
            attitude_score,
            social_score,
            growth_score,
            suggestions,
            json.dumps(analysis, ensure_ascii=False, cls=DecimalEncoder),
            generated_by
        )
    )

    profile_id = db.lastrowid()

    # 保存历史
    profile_data = {
        'profile_summary': profile_summary,
        'profile_tags': profile_tags,
        'scores': {
            'moral': moral_score,
            'attitude': attitude_score,
            'social': social_score,
            'growth': growth_score
        },
        'risk_level': risk_level,
        'suggestions': suggestions,
        'analysis': analysis
    }
    db.execute(
        """INSERT INTO student_profile_history
        (student_id, profile_version, profile_data)
        VALUES (?, ?, ?)""",
        (student_id, new_version, json.dumps(profile_data, ensure_ascii=False, cls=DecimalEncoder))
    )

    return {
        "profile_id": profile_id,
        "student_id": student_id,
        "student_name": student.get('name', ''),
        "class_name": student.get('class_name', ''),
        "grade_name": student.get('grade_name', ''),
        "risk_level": risk_level,
        "scores": {
            "moral": moral_score,
            "attitude": attitude_score,
            "social": social_score,
            "growth": growth_score
        }
    }


@router.post("/batch-generate", summary="批量生成学生画像")
async def batch_generate_profiles(
    background_tasks: BackgroundTasks,
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    request: Request = None,
    user: User = Depends(require_configured_api_permission(API_PROFILE_BATCH_GENERATE, "POST", allow_missing=False))
):
    """批量生成学生画像"""
    with get_moral_db() as db:
        _cleanup_profile_jobs()
        can_generate_all = _has_scoped_permission(db, user, API_PROFILE_BATCH_GENERATE, 'student_profile')
        can_generate_own_class = _has_scoped_permission(db, user, API_PROFILE_BATCH_GENERATE, 'student_profile_own_class')
        if not can_generate_all and not can_generate_own_class:
            raise HTTPException(403, "权限不足：需要学生画像生成权限")

        # 获取当前学期
        current_semester = get_current_semester(db)
        semester_id = current_semester['semester_id'] if current_semester else None

        if not semester_id:
            raise HTTPException(400, "无法获取当前学期信息")

        # 获取学生列表
        conditions = ["status = '在校'"]
        params = []

        if class_id:
            conditions.append("class_id = ?")
            params.append(class_id)

        if grade_id:
            conditions.append("grade_id = ?")
            params.append(grade_id)

        if not can_generate_all:
            my_class_id = get_teacher_class_id(user, db)
            if not my_class_id:
                return {
                    "success": True,
                    "message": "没有找到需要生成画像的学生",
                    "data": {"success_count": 0, "error_count": 0, "errors": []}
                }
            conditions.append("class_id = ?")
            params.append(my_class_id)

        students = db.query_all(
            f"SELECT student_id, name FROM student WHERE {' AND '.join(conditions)}",
            tuple(params) if params else None
        )

        if not students:
            return {
                "success": True,
                "message": "没有找到需要生成画像的学生",
                "data": {
                    "success_count": 0,
                    "error_count": 0,
                    "total_count": 0,
                    "errors": []
                }
            }

        job_id = uuid.uuid4().hex
        PROFILE_GENERATION_JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "message": "批量画像生成任务已提交",
            "created_at": time.time(),
            "generated_by": user.username,
            "semester_id": semester_id,
            "students": [dict(student) for student in students],
            "total_count": len(students),
            "success_count": 0,
            "error_count": 0,
            "current": 0,
            "errors": [],
            "generated_profiles": [],
        }
        background_tasks.add_task(_run_profile_batch_generation_job, job_id)

        return {
            "success": True,
            "message": "批量画像生成任务已提交",
            "data": {
                "job_id": job_id,
                "status": "queued",
                "total_count": len(students),
                "success_count": 0,
                "error_count": 0,
                "errors": [],
                "generated_profiles": [],
            }
        }


@router.get("/config", summary="获取画像配置")
async def get_profile_config(user: User = Depends(require_configured_api_permission(API_PROFILE_CONFIG, "GET", allow_missing=False))):
    """获取画像配置"""
    with get_moral_db() as db:
        configs = db.query_all("SELECT * FROM profile_config")

        config_dict = {}
        for config in configs:
            config_dict[config['config_key']] = config['config_value']

        return {"success": True, "data": config_dict}


# =============================================================================
# 配置管理
# =============================================================================

# 默认配置（当数据库无配置时使用）
DEFAULT_CONFIG = {
    "scoring_weights": {
        "moral": {"base": 80, "positive_weight": 2, "negative_weight": 3},
        "attitude": {"base": 80, "completion_weight": 40},
        "social": {"base": 75, "collective_weight": 2},
        "growth": {"base": 75, "honor_weight": 5}
    },
    "tag_rules": {
        "积极进取": {"positive_count_min": 5},
        "遵纪守法": {"negative_count_max": 2},
        "勤奋刻苦": {"positive_negative_ratio_min": 2},
        "责任担当": {"task_completion_rate_min": 0.8},
        "诚实守信": {"negative_count_max": 0},
        "乐于助人": {"collective_count_min": 3},
        "团结协作": {"collective_count_min": 5},
        "文明礼貌": {"positive_rate_min": 0.8}
    },
    "risk_thresholds": {
        "high": {"negative_count": 10, "punishment_count": 2},
        "medium": {"negative_count": 5, "punishment_count": 1}
    }
}


def get_profile_config_value(db, key: str, default=None) -> dict:
    """获取画像配置参数"""
    try:
        config = db.query_one(
            "SELECT config_value FROM profile_config WHERE config_key = ?",
            (key,)
        )
        if config:
            return json.loads(config['config_value'])
        return default if default is not None else DEFAULT_CONFIG.get(key, {})
    except Exception as e:
        logger.warning(f"获取配置失败: {key}, {str(e)}")
        return default if default is not None else DEFAULT_CONFIG.get(key, {})


def get_all_profile_config(db) -> dict:
    """获取所有画像配置"""
    config = DEFAULT_CONFIG.copy()
    try:
        configs = db.query_all("SELECT config_key, config_value FROM profile_config")
        for row in configs:
            try:
                config[row['config_key']] = json.loads(row['config_value'])
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.warning(f"获取配置失败: {str(e)}")
    return config


# =============================================================================
# 辅助函数
# =============================================================================

def analyze_student_data(db, student_id: str, semester_id: int = None) -> dict:
    """分析学生数据

    Args:
        db: 数据库连接
        student_id: 学生ID
        semester_id: 学期ID，None 表示查询全量数据（一生一册模式）
    """
    analysis = {}

    # 构建学期筛选条件
    semester_filter = "AND dr.semester_id = ?" if semester_id else ""
    semester_params = (student_id, semester_id) if semester_id else (student_id,)

    # 日常表现统计
    daily_stats = db.query_all(
        f"""SELECT de.event_type, COUNT(*) as count, SUM(dr.score) as total_score
        FROM student_daily_record dr
        JOIN daily_event_type de ON dr.event_id = de.event_id
        WHERE dr.student_id = ? {semester_filter} AND dr.is_deleted = 0
        GROUP BY de.event_type""",
        semester_params
    )
    analysis['daily_stats'] = {str(s['event_type']): {'count': s['count'], 'total': s['total_score']} for s in daily_stats}
    analysis['daily_recent'] = db.query_all(
        f"""SELECT dr.record_date, det.event_name, det.event_type, dr.score, dr.remark
        FROM student_daily_record dr
        JOIN daily_event_type det ON dr.event_id = det.event_id
        WHERE dr.student_id = ? {semester_filter} AND dr.is_deleted = 0
        ORDER BY dr.record_date DESC, dr.created_at DESC
        LIMIT 8""",
        semester_params
    )

    # 校级事件统计
    school_stats = db.query_all(
        f"""SELECT se.event_type, COUNT(*) as count, SUM(sr.score) as total_score
        FROM student_school_record sr
        JOIN school_event_type se ON sr.event_id = se.event_id
        WHERE sr.student_id = ? {semester_filter} AND sr.is_deleted = 0
        GROUP BY se.event_type""",
        semester_params
    )
    analysis['school_stats'] = {str(s['event_type']): {'count': s['count'], 'total': s['total_score']} for s in school_stats}
    analysis['school_recent'] = db.query_all(
        f"""SELECT sr.get_date as record_date, setype.event_name, setype.event_type, sr.score, sr.proof
        FROM student_school_record sr
        JOIN school_event_type setype ON sr.event_id = setype.event_id
        WHERE sr.student_id = ? {semester_filter} AND sr.is_deleted = 0
        ORDER BY sr.get_date DESC, sr.created_at DESC
        LIMIT 8""",
        semester_params
    )

    # 任务完成情况（按学年或全量）
    if semester_id:
        task_stats = db.query_one(
            """SELECT
            COUNT(*) as total,
            SUM(CASE WHEN stf.status = 1 THEN 1 ELSE 0 END) as finished,
            SUM(CASE WHEN stf.status = 1 THEN stf.current_score ELSE 0 END) as score
            FROM student_task_finish stf
            JOIN semester sem ON sem.semester_id = ?
            JOIN school_year sy ON sem.year_id = sy.year_id
            WHERE stf.student_id = ? AND stf.year_id = sy.year_id""",
            (semester_id, student_id)
        )
        analysis['task_recent'] = db.query_all(
            """SELECT gmt.task_name, gmt.deadline_type, stf.status, stf.current_score, stf.finish_date
            FROM student_task_finish stf
            JOIN grade_moral_task gmt ON stf.task_id = gmt.task_id
            JOIN semester sem ON sem.semester_id = ?
            JOIN school_year sy ON sem.year_id = sy.year_id
            WHERE stf.student_id = ? AND stf.year_id = sy.year_id
            ORDER BY COALESCE(stf.finish_date, stf.created_at) DESC
            LIMIT 8""",
            (semester_id, student_id)
        )
    else:
        # 全量查询
        task_stats = db.query_one(
            """SELECT
            COUNT(*) as total,
            SUM(CASE WHEN stf.status = 1 THEN 1 ELSE 0 END) as finished,
            SUM(CASE WHEN stf.status = 1 THEN stf.current_score ELSE 0 END) as score
            FROM student_task_finish stf
            WHERE stf.student_id = ?""",
            (student_id,)
        )
        analysis['task_recent'] = db.query_all(
            """SELECT gmt.task_name, gmt.deadline_type, stf.status, stf.current_score, stf.finish_date
            FROM student_task_finish stf
            JOIN grade_moral_task gmt ON stf.task_id = gmt.task_id
            WHERE stf.student_id = ?
            ORDER BY COALESCE(stf.finish_date, stf.created_at) DESC
            LIMIT 8""",
            (student_id,)
        )
    analysis['task_stats'] = task_stats or {'total': 0, 'finished': 0, 'score': 0}

    # 集体活动参与统计（用于社交评分）
    collective_stats = db.query_one(
        f"""SELECT COUNT(*) as collective_count, COALESCE(SUM(d.score_assigned), 0) as score
        FROM collective_event_distribution d
        JOIN collective_event e ON d.event_id = e.event_id
        WHERE d.student_id = ? {semester_filter} AND d.is_participant = 1""",
        semester_params
    )
    analysis['collective_stats'] = collective_stats or {'collective_count': 0, 'score': 0}
    analysis['collective_recent'] = db.query_all(
        f"""SELECT e.event_date, e.event_name, e.event_type, d.score_assigned, d.remark
        FROM collective_event_distribution d
        JOIN collective_event e ON d.event_id = e.event_id
        WHERE d.student_id = ? {semester_filter} AND d.is_participant = 1
        ORDER BY e.event_date DESC
        LIMIT 8""",
        semester_params
    )

    # 处分统计
    punishment_stats = db.query_one(
        f"""SELECT COUNT(*) as count, COALESCE(SUM(ABS(score_deduct)), 0) as total_deduct,
        SUM(CASE WHEN is_revoked = 1 THEN 1 ELSE 0 END) as revoked_count
        FROM punishment_record
        WHERE student_id = ? {semester_filter}""",
        semester_params
    )
    analysis['punishment_stats'] = punishment_stats or {'count': 0, 'total_deduct': 0, 'revoked_count': 0}
    analysis['punishment_recent'] = db.query_all(
        f"""SELECT punishment_date, level, reason, ABS(score_deduct) as score_deduct, is_revoked
        FROM punishment_record
        WHERE student_id = ? {semester_filter}
        ORDER BY punishment_date DESC, created_at DESC
        LIMIT 5""",
        semester_params
    )

    analysis['daily_top_events'] = db.query_all(
        f"""SELECT det.event_name, det.event_type, COUNT(*) as count, COALESCE(SUM(dr.score), 0) as total_score
        FROM student_daily_record dr
        JOIN daily_event_type det ON dr.event_id = det.event_id
        WHERE dr.student_id = ? {semester_filter} AND dr.is_deleted = 0
        GROUP BY det.event_id
        ORDER BY count DESC, ABS(total_score) DESC
        LIMIT 8""",
        semester_params
    )

    # 点滴记录统计
    analysis['moment_stats'] = db.query_one(
        f"""SELECT COUNT(*) as count
        FROM moment_record
        WHERE student_id = ? {semester_filter}""",
        semester_params
    ) or {'count': 0}
    analysis['moment_recent'] = db.query_all(
        f"""SELECT record_date, record_type, content, tags
        FROM moment_record
        WHERE student_id = ? {semester_filter}
        ORDER BY record_date DESC, created_at DESC
        LIMIT 8""",
        semester_params
    )

    # 德育评价（学期关联）
    if semester_id:
        evaluation = db.query_one(
            """SELECT total_score, level
            FROM moral_evaluation
            WHERE student_id = ? AND semester_id = ?""",
            (student_id, semester_id)
        )
    else:
        # 全量取最新一条
        evaluation = db.query_one(
            """SELECT total_score, level
            FROM moral_evaluation
            WHERE student_id = ?
            ORDER BY semester_id DESC
            LIMIT 1""",
            (student_id,)
        )
    analysis['evaluation'] = evaluation or {'total_score': None, 'level': None}

    return analysis


def build_profile_output(student: dict, analysis: dict, config: dict, use_ai: bool = True) -> dict:
    """生成画像内容，AI 不可用时退回本地规则。"""
    profile_tags = generate_profile_tags(analysis, config.get('tag_rules', {}))
    strength_tags = [
        tag for tag in profile_tags
        if tag in ['责任担当', '诚实守信', '乐于助人', '勤奋刻苦', '积极进取', '团结协作', '文明礼貌', '遵纪守法']
    ]
    improvement_tags = [tag for tag in profile_tags if tag not in strength_tags]

    scores = {
        'moral': calculate_moral_subscore(analysis, config.get('scoring_weights', {}).get('moral', {})),
        'attitude': calculate_attitude_subscore(analysis, config.get('scoring_weights', {}).get('attitude', {})),
        'social': calculate_social_subscore(analysis, config.get('scoring_weights', {}).get('social', {})),
        'growth': calculate_growth_subscore(analysis, config.get('scoring_weights', {}).get('growth', {})),
    }
    risk_level = assess_risk_level(analysis, config.get('risk_thresholds', {}))

    output = {
        'profile_summary': generate_profile_summary(analysis),
        'profile_tags': profile_tags,
        'strength_tags': strength_tags,
        'improvement_tags': improvement_tags,
        'risk_level': risk_level,
        'scores': scores,
        'suggestions': generate_suggestions(analysis, risk_level),
        'ai_used': False,
    }

    if not use_ai:
        return output

    ai_output = generate_ai_profile_output(student, analysis, output)
    if ai_output:
        output.update(ai_output)
        output['ai_used'] = True

    return output


def generate_ai_profile_output(student: dict, analysis: dict, fallback: dict) -> Optional[dict]:
    """调用项目现有大模型配置生成更自然的画像文本。"""
    evidence_summary = build_evidence_summary(analysis, fallback)
    compact = {
        'student': {
            'name': student.get('name'),
            'class_name': student.get('class_name'),
            'grade_name': student.get('grade_name'),
        },
        'evidence_summary': evidence_summary,
        'evaluation': analysis.get('evaluation', {}),
        'daily_stats': analysis.get('daily_stats', {}),
        'daily_top_events': analysis.get('daily_top_events', []),
        'school_stats': analysis.get('school_stats', {}),
        'task_stats': analysis.get('task_stats', {}),
        'collective_stats': analysis.get('collective_stats', {}),
        'punishment_stats': analysis.get('punishment_stats', {}),
        'moment_stats': analysis.get('moment_stats', {}),
        'recent_evidence': {
            'daily': analysis.get('daily_recent', [])[:8],
            'school': analysis.get('school_recent', [])[:8],
            'task': analysis.get('task_recent', [])[:8],
            'collective': analysis.get('collective_recent', [])[:8],
            'punishment': analysis.get('punishment_recent', [])[:5],
            'moment': analysis.get('moment_recent', [])[:8],
        },
        'fallback': fallback,
    }
    prompt = f"""请基于以下学生德育真实数据生成一份较完整的学生画像。必须只依据给定数据表达，不能编造没有出现过的事实、心理诊断、家庭情况或成绩情况。

请输出严格 JSON，字段如下：
- profile_summary: 字符串，800-1500字，使用中文分段。必须包含以下小标题：总体判断、优势表现、待关注表现、关键证据、育人建议。每段都要引用具体数字或具体事件名称/日期作为依据；没有数据的方面要明确写“暂无相关记录”，不要空泛夸奖。
- suggestions: 字符串，4-6条具体建议，每条以“1.”、“2.”编号，建议必须可执行，包含跟进人、观察点或周期。
- profile_tags: 字符串数组，6-10个标签，既可以包含优势标签，也可以包含待关注标签。

写作要求：
- 语言温和、客观、面向班主任/德育老师使用。
- 不要只写结论，要解释“为什么这样判断”。
- 如果正向、负向数据都有，要体现平衡，不要一边倒。
- 如果数据较少，要说明画像可信度有限，并建议补充观察记录。

数据：
{json.dumps(compact, ensure_ascii=False, cls=DecimalEncoder)}
"""
    try:
        from openai import OpenAI
        from config.config import Config

        client = OpenAI(
            api_key=Config().get_config("bailian_token", "token.yaml"),
            base_url="https://coding.dashscope.aliyuncs.com/v1",
            timeout=20,
        )
        completion = client.chat.completions.create(
            model=get_current_model('profile_generate'),
            messages=[
                {"role": "system", "content": "你是学校德育数据分析助手，擅长把学生真实德育数据转化为有证据、有边界、可行动的学生画像。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.25,
            max_tokens=2200,
        )
        content = completion.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        if not content.startswith("{"):
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                content = content[start:end + 1]
        parsed = json.loads(content)
        result = {}
        if parsed.get('profile_summary'):
            result['profile_summary'] = str(parsed['profile_summary'])[:4000]
        if parsed.get('suggestions'):
            result['suggestions'] = str(parsed['suggestions'])[:2500]
        if isinstance(parsed.get('profile_tags'), list):
            tags = [str(tag)[:20] for tag in parsed['profile_tags'] if tag]
            if tags:
                result['profile_tags'] = tags[:8]
                result['strength_tags'] = [
                    tag for tag in tags
                    if tag in ['责任担当', '诚实守信', '乐于助人', '勤奋刻苦', '积极进取', '团结协作', '文明礼貌', '遵纪守法']
                ]
                result['improvement_tags'] = [tag for tag in tags if tag not in result['strength_tags']]
        return result or None
    except Exception as e:
        logger.warning(f"AI画像生成失败，使用本地规则: {e}")
        return None


def _num(value, default=0):
    try:
        return float(value if value is not None else default)
    except (TypeError, ValueError):
        return default


def build_evidence_summary(analysis: dict, fallback: dict) -> dict:
    """把画像证据整理成稳定摘要，供AI和本地规则复用。"""
    positive_count = int(_num(analysis.get('daily_stats', {}).get('1', {}).get('count')))
    positive_score = _num(analysis.get('daily_stats', {}).get('1', {}).get('total'))
    negative_count = int(_num(analysis.get('daily_stats', {}).get('2', {}).get('count')))
    negative_score = _num(analysis.get('daily_stats', {}).get('2', {}).get('total'))
    task_total = int(_num(analysis.get('task_stats', {}).get('total')))
    task_finished = int(_num(analysis.get('task_stats', {}).get('finished')))
    task_rate = task_finished / task_total if task_total else None
    collective_count = int(_num(analysis.get('collective_stats', {}).get('collective_count')))
    punishment_count = int(_num(analysis.get('punishment_stats', {}).get('count')))
    moment_count = int(_num(analysis.get('moment_stats', {}).get('count')))
    evaluation = analysis.get('evaluation', {}) or {}

    return {
        'evaluation_score': evaluation.get('total_score'),
        'evaluation_level': evaluation.get('level'),
        'daily_positive_count': positive_count,
        'daily_positive_score': positive_score,
        'daily_negative_count': negative_count,
        'daily_negative_score': negative_score,
        'positive_negative_ratio': round(positive_count / max(1, negative_count), 2),
        'task_total': task_total,
        'task_finished': task_finished,
        'task_completion_rate': round(task_rate, 2) if task_rate is not None else None,
        'collective_count': collective_count,
        'collective_score': _num(analysis.get('collective_stats', {}).get('score')),
        'punishment_count': punishment_count,
        'punishment_deduct': _num(analysis.get('punishment_stats', {}).get('total_deduct')),
        'moment_count': moment_count,
        'risk_level': fallback.get('risk_level'),
        'subscores': fallback.get('scores', {}),
        'rule_tags': fallback.get('profile_tags', []),
    }


def generate_profile_summary(analysis: dict) -> str:
    """生成画像摘要"""
    positive_count = analysis.get('daily_stats', {}).get('1', {}).get('count', 0)
    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0)
    honor_count = analysis.get('school_stats', {}).get('1', {}).get('count', 0)
    collective_count = analysis.get('collective_stats', {}).get('collective_count', 0) or 0
    punishment_count = analysis.get('punishment_stats', {}).get('count', 0) or 0
    evaluation = analysis.get('evaluation', {})

    evidence = build_evidence_summary(analysis, {'risk_level': assess_risk_level(analysis), 'scores': {}, 'profile_tags': []})
    top_events = analysis.get('daily_top_events', [])[:4]
    recent_daily = analysis.get('daily_recent', [])[:4]
    recent_moments = analysis.get('moment_recent', [])[:3]
    parts = []

    overview = []
    if evaluation.get('total_score') is not None:
        overview.append(f"当前德育总分{float(evaluation['total_score']):.1f}，等级为{evaluation.get('level') or '未定级'}")
    overview.append(
        f"本学期日常正向记录{positive_count}次、累计{_num(analysis.get('daily_stats', {}).get('1', {}).get('total')):+.0f}分，"
        f"需改进记录{negative_count}次、累计{_num(analysis.get('daily_stats', {}).get('2', {}).get('total')):+.0f}分"
    )
    parts.append("总体判断：" + "；".join(overview) + "。")

    strengths = []
    if positive_count > negative_count * 2:
        strengths.append(f"正向记录数量明显多于需改进记录，正负比约{evidence['positive_negative_ratio']}:1")
    elif positive_count > negative_count:
        strengths.append("正向记录略多于需改进记录，整体表现较稳")
    if honor_count > 0:
        strengths.append(f"获得{honor_count}项校级或以上正向记录")
    if collective_count > 0:
        strengths.append(f"参与{collective_count}次集体事件，集体参与有记录支撑")

    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 0
    concerns = []
    if negative_count >= positive_count:
        concerns.append("需改进记录不少于正向记录，行为习惯稳定性需要持续观察")
    if punishment_count > 0:
        concerns.append(f"有{punishment_count}条处分记录，累计扣分{evidence['punishment_deduct']:.0f}分")

    if task_total > 0:
        rate = task_finished / task_total * 100
        if rate >= 80:
            strengths.append(f"德育任务完成率{rate:.0f}%，任务态度较好")
        elif rate >= 60:
            concerns.append(f"德育任务完成率{rate:.0f}%，仍有提升空间")
        else:
            concerns.append(f"德育任务完成率{rate:.0f}%，需要加强跟进")
    else:
        concerns.append("暂无德育任务完成数据，任务态度判断依据不足")
    parts.append("优势表现：" + ("；".join(strengths) if strengths else "暂无明显优势标签，需要继续积累正向行为证据") + "。")
    parts.append("待关注表现：" + ("；".join(concerns) if concerns else "当前未见明显风险记录，但仍建议保持常态观察") + "。")

    evidence_lines = []
    if top_events:
        evidence_lines.append("高频日常事件：" + "、".join([f"{e.get('event_name')} {e.get('count')}次" for e in top_events if e.get('event_name')]))
    if recent_daily:
        evidence_lines.append("近日表现：" + "；".join([f"{r.get('record_date')} {r.get('event_name')}({r.get('score'):+})" for r in recent_daily if r.get('event_name')]))
    if recent_moments:
        evidence_lines.append("点滴记录：" + "；".join([f"{m.get('record_date')} {str(m.get('content') or '')[:30]}" for m in recent_moments]))
    parts.append("关键证据：" + ("；".join(evidence_lines) if evidence_lines else "暂无足够近期事件记录") + "。")

    return "\n".join(parts) if parts else "暂无足够数据生成画像"


def generate_profile_tags(analysis: dict, config: dict = None) -> List[str]:
    """生成画像标签（支持配置化规则）"""
    if config is None:
        config = DEFAULT_CONFIG['tag_rules']

    tags = []

    positive_count = analysis.get('daily_stats', {}).get('1', {}).get('count', 0) or 0
    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0) or 0
    total_daily_count = positive_count + negative_count

    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 0
    if task_total == 0:
        task_total = 1
    task_completion_rate = task_finished / task_total

    collective_count = analysis.get('collective_stats', {}).get('collective_count', 0) or 0

    # 计算正向事件比例（用于"文明礼貌"标签）
    positive_rate = positive_count / max(1, total_daily_count)

    # 积极进取：正向事件达到阈值
    rule = config.get('积极进取', {})
    if positive_count >= rule.get('positive_count_min', 5):
        tags.append("积极进取")

    # 遵纪守法：消极事件不超过阈值
    rule = config.get('遵纪守法', {})
    if negative_count <= rule.get('negative_count_max', 2):
        tags.append("遵纪守法")

    # 勤奋刻苦：正向/消极比例达到阈值
    rule = config.get('勤奋刻苦', {})
    ratio_min = rule.get('positive_negative_ratio_min', 2)
    if negative_count == 0 or (positive_count / max(1, negative_count)) >= ratio_min:
        tags.append("勤奋刻苦")

    # 责任担当：任务完成率达到阈值
    rule = config.get('责任担当', {})
    if task_completion_rate >= rule.get('task_completion_rate_min', 0.8):
        tags.append("责任担当")

    # 诚实守信：消极事件为0
    rule = config.get('诚实守信', {})
    if negative_count <= rule.get('negative_count_max', 0):
        tags.append("诚实守信")

    # 乐于助人：集体活动参与达到阈值
    rule = config.get('乐于助人', {})
    if collective_count >= rule.get('collective_count_min', 3):
        tags.append("乐于助人")

    # 团结协作：集体活动参与达到更高阈值
    rule = config.get('团结协作', {})
    if collective_count >= rule.get('collective_count_min', 5):
        tags.append("团结协作")

    # 文明礼貌：正向事件比例达到阈值
    rule = config.get('文明礼貌', {})
    if positive_rate >= rule.get('positive_rate_min', 0.8):
        tags.append("文明礼貌")

    return tags[:8] if tags else ["待观察"]


def calculate_moral_subscore(analysis: dict, config: dict = None) -> float:
    """计算品德评分（支持配置化权重）"""
    if config is None:
        config = DEFAULT_CONFIG['scoring_weights']['moral']

    base = float(config.get('base', 80))
    positive_weight = float(config.get('positive_weight', 2))
    negative_weight = float(config.get('negative_weight', 3))

    positive = analysis.get('daily_stats', {}).get('1', {}).get('count', 0) or 0
    negative = analysis.get('daily_stats', {}).get('2', {}).get('count', 0) or 0

    return min(100, max(0, base + positive * positive_weight - negative * negative_weight))


def calculate_attitude_subscore(analysis: dict, config: dict = None) -> float:
    """计算态度评分（支持配置化权重）"""
    if config is None:
        config = DEFAULT_CONFIG['scoring_weights']['attitude']

    base = float(config.get('base', 80))
    completion_weight = float(config.get('completion_weight', 40))

    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 1
    if task_total == 0:
        task_total = 1

    completion_rate = task_finished / task_total
    return min(100, max(0, base + (completion_rate - 0.5) * completion_weight))


def calculate_social_subscore(analysis: dict, config: dict = None) -> float:
    """计算社交评分（基于集体活动参与）"""
    if config is None:
        config = DEFAULT_CONFIG['scoring_weights']['social']

    base = float(config.get('base', 75))
    collective_weight = float(config.get('collective_weight', 2))

    # 获取集体活动参与次数
    collective_count = analysis.get('collective_stats', {}).get('collective_count', 0) or 0

    # 计算社交评分：基础分 + 集体活动参与加分
    return min(100, max(0, base + collective_count * collective_weight))


def calculate_growth_subscore(analysis: dict, config: dict = None) -> float:
    """计算成长评分（支持配置化权重）"""
    if config is None:
        config = DEFAULT_CONFIG['scoring_weights']['growth']

    base = float(config.get('base', 75))
    honor_weight = float(config.get('honor_weight', 5))

    honor_count = analysis.get('school_stats', {}).get('1', {}).get('count', 0) or 0

    return min(100, max(0, base + honor_count * honor_weight))


def assess_risk_level(analysis: dict, config: dict = None) -> str:
    """评估风险等级（支持配置化阈值）"""
    if config is None:
        config = DEFAULT_CONFIG['risk_thresholds']

    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0) or 0
    punishment_count = analysis.get('punishment_stats', {}).get('count', 0) or 0

    # 高风险阈值
    high_threshold = config.get('high', {})
    high_negative = high_threshold.get('negative_count', 10)
    high_punishment = high_threshold.get('punishment_count', 2)

    # 中风险阈值
    medium_threshold = config.get('medium', {})
    medium_negative = medium_threshold.get('negative_count', 5)
    medium_punishment = medium_threshold.get('punishment_count', 1)

    if negative_count >= high_negative or punishment_count >= high_punishment:
        return "high"
    elif negative_count >= medium_negative or punishment_count >= medium_punishment:
        return "medium"
    else:
        return "low"


def generate_suggestions(analysis: dict, risk_level: str) -> str:
    """根据画像分析生成个性化建议"""
    suggestions = []

    # 根据消极事件数量
    negative_count = analysis.get('daily_stats', {}).get('2', {}).get('count', 0) or 0
    if negative_count > 10:
        suggestions.append("班主任每周固定复盘一次高频需改进事件，和学生共同确认1个可观察的行为目标")
    elif negative_count > 5:
        suggestions.append("德育老师或班主任连续两周跟踪日常规范表现，重点观察迟到、课堂纪律、作业习惯等重复事件")

    # 根据惩罚事件
    punishment_count = analysis.get('punishment_stats', {}).get('count', 0) or 0
    if punishment_count >= 2:
        suggestions.append("针对处分记录建立家校沟通台账，明确整改事项、责任人和复查时间")

    # 根据任务完成情况
    task_finished = analysis.get('task_stats', {}).get('finished', 0) or 0
    task_total = analysis.get('task_stats', {}).get('total', 0) or 1
    task_rate = task_finished / max(1, task_total)
    if task_rate < 0.4:
        suggestions.append("为德育任务设置分阶段清单，每周检查完成进度，避免任务集中拖延")
    elif task_rate < 0.6:
        suggestions.append("提醒学生把未完成任务拆成小步骤，并在班级层面给予过程性反馈")

    # 根据集体活动参与情况
    collective_count = analysis.get('collective_stats', {}).get('collective_count', 0) or 0
    if collective_count < 2:
        suggestions.append("安排一次适合其能力的班级服务或小组协作任务，增加可记录的集体参与证据")

    # 根据荣誉获取情况
    honor_count = analysis.get('school_stats', {}).get('1', {}).get('count', 0) or 0
    positive_count = analysis.get('daily_stats', {}).get('1', {}).get('count', 0) or 0
    if honor_count == 0 and positive_count < 3:
        suggestions.append("设置一项两周内可达成的正向行为目标，达成后及时记录，帮助学生形成正反馈")

    # 根据风险等级给出针对性建议
    if risk_level == "high":
        suggestions.append("建议启动重点关注机制，形成班主任、年级、家长共同参与的月度跟进记录")
    elif risk_level == "medium":
        suggestions.append("建议加强日常观察和引导，重点看同类问题是否在两周内下降")

    # 如果表现良好，给出正面建议
    if not suggestions:
        positive_rate = positive_count / max(1, positive_count + negative_count)
        if positive_rate > 0.8 and collective_count >= 3:
            suggestions.append("继续保持良好习惯，可安排班级服务或同伴带动任务，观察其责任担当表现")
        else:
            suggestions.append("继续积累正向表现记录，建议班主任关注其稳定性和主动参与情况")

    top_events = analysis.get('daily_top_events', []) or []
    if positive_count > 0 and len(suggestions) < 4:
        positive_events = [e for e in top_events if int(e.get('event_type') or 0) == 1 and e.get('event_name')]
        if positive_events:
            suggestions.append(f"围绕“{positive_events[0]['event_name']}”等已有正向表现继续设计激励，让优势行为可重复、可记录")
        else:
            suggestions.append("每周至少补充一次正向观察记录，帮助画像更准确地区分稳定优势和偶发表现")

    if negative_count > 0 and len(suggestions) < 4:
        negative_events = [e for e in top_events if int(e.get('event_type') or 0) == 2 and e.get('event_name')]
        if negative_events:
            suggestions.append(f"对“{negative_events[0]['event_name']}”等重复问题设定明确改进标准，两周后复盘是否下降")
        else:
            suggestions.append("把需改进记录按类型复盘，找出最容易先改变的一项行为作为切入口")

    if collective_count < 3 and len(suggestions) < 4:
        suggestions.append("安排一次班级公共事务或小组协作岗位，观察其沟通、守时和责任完成情况")

    moment_count = analysis.get('moment_stats', {}).get('count', 0) or 0
    if moment_count < 2 and len(suggestions) < 4:
        suggestions.append("建议任课教师或班主任补充点滴记录，记录课堂参与、人际互动和任务执行等过程性表现")

    if len(suggestions) < 4:
        suggestions.append("一个月后重新生成画像，对比正向记录、需改进记录和任务完成率的变化")

    return "\n".join([f"{idx + 1}. {text}" for idx, text in enumerate(suggestions[:6])]) if suggestions else "1. 继续保持良好表现，并积累更多过程性观察记录"
