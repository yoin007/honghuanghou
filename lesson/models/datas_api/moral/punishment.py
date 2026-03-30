# -*- coding: utf-8 -*-
"""
处分管理 API

提供处分记录的管理功能
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    get_current_semester,
    get_student_class_snapshot,
    log_operation,
    require_permission,
)
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/punishments", tags=["处分管理"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class PunishmentCreate(BaseModel):
    """创建处分记录"""
    student_id: str = Field(..., description="学号")
    punishment_type: str = Field(..., description="处分类型")
    punishment_level: int = Field(2, description="处分等级")
    punishment_date: date = Field(..., description="处分日期")
    punishment_reason: Optional[str] = Field(None, description="处分原因")
    evidence: Optional[str] = Field(None, description="证据材料")
    score_deduct: Optional[int] = Field(None, description="扣分")


class PunishmentRevoke(BaseModel):
    """撤销处分"""
    revoke_reason: str = Field(..., description="撤销原因")


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="获取处分记录列表")
async def get_punishments(
    student_id: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    semester_id: Optional[int] = Query(None),
    is_revoked: Optional[int] = Query(None, description="是否已撤销"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """
    获取处分记录列表

    权限说明：
    - admin/xuefa/jiaowu: 可查看所有
    - cleader: 只能查看本班
    """
    with get_moral_db() as db:
        # 权限检查
        if not check_moral_permission(user, 'punishment_manage') and \
           not check_moral_permission(user, 'report_view_all'):
            raise HTTPException(403, "权限不足")

        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        conditions = ["1=1"]
        params = []

        if student_id:
            conditions.append("p.student_id = %s")
            params.append(student_id)

        if class_id:
            conditions.append("p.class_id = %s")
            params.append(class_id)

        if grade_id:
            conditions.append("p.grade_id = %s")
            params.append(grade_id)

        if semester_id:
            conditions.append("p.semester_id = %s")
            params.append(semester_id)

        if is_revoked is not None:
            conditions.append("p.is_revoked = %s")
            params.append(is_revoked)

        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*) FROM punishment_record p WHERE {where_clause}
        """
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT p.id as record_id, p.student_id, p.punishment_date, p.score_deduct,
                   p.level as punishment_level, p.reason as punishment_reason,
                   p.is_revoked, p.revoke_date, p.revoke_reason,
                   se.event_name as punishment_type,
                   s.name as student_name, c.class_name, g.grade_name
            FROM punishment_record p
            JOIN student s ON p.student_id = s.student_id
            JOIN school_event_type se ON p.event_id = se.event_id
            JOIN class c ON p.class_id = c.class_id
            JOIN grade g ON p.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY p.punishment_date DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        records = db.query_all(data_query, tuple(params))

        return {
            "success": True,
            "data": {
                "items": records,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


@router.post("", summary="创建处分记录")
async def create_punishment(
    punishment: PunishmentCreate,
    request: Request,
    user: User = Depends(require_permission('punishment_manage'))
):
    """创建处分记录"""
    with get_moral_db() as db:
        current_semester = get_current_semester(db)
        if not current_semester:
            raise HTTPException(400, "当前学期未配置")

        semester_id = current_semester['semester_id']

        # 获取学生班级信息
        student_info = get_student_class_snapshot(db, punishment.student_id)
        if not student_info:
            raise HTTPException(404, f"学生 {punishment.student_id} 不存在或不在校")

        # 根据处分类型名称查找或创建事件类型
        event = db.query_one(
            "SELECT * FROM school_event_type WHERE event_name = %s AND event_type = 2",
            (punishment.punishment_type,)
        )
        if not event:
            # 如果不存在，创建一个新的事件类型
            level_score_map = {1: -5, 2: -10, 3: -20, 4: -30}
            score = punishment.score_deduct if punishment.score_deduct else level_score_map.get(punishment.punishment_level, -10)
            db.execute(
                """INSERT INTO school_event_type (event_name, event_type, score, is_active)
                VALUES (%s, 2, %s, 1)""",
                (punishment.punishment_type, score)
            )
            event_id = db.lastrowid()
        else:
            event_id = event['event_id']

        # 计算扣分
        level_score_map = {1: -5, 2: -10, 3: -20, 4: -30}
        score_deduct = punishment.score_deduct if punishment.score_deduct else level_score_map.get(punishment.punishment_level, -10)

        # 处分等级文本
        level_map = {1: '一级', 2: '二级', 3: '三级', 4: '四级'}
        level_text = level_map.get(punishment.punishment_level, '二级')

        # 插入记录
        db.execute(
            """INSERT INTO punishment_record
            (student_id, event_id, semester_id, punishment_date, class_id, grade_id,
             score_deduct, level, reason, recorder)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                punishment.student_id,
                event_id,
                semester_id,
                punishment.punishment_date,
                student_info['class_id'],
                student_info['grade_id'],
                score_deduct,
                level_text,
                punishment.punishment_reason,
                user.username
            )
        )

        record_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'punishment_record',
            record_id, semester_id,
            new_data={'student_id': punishment.student_id, 'reason': punishment.punishment_reason},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "处分记录创建成功", "data": {"id": record_id}}


@router.put("/{record_id}", summary="更新处分记录")
async def update_punishment(
    record_id: int,
    punishment: PunishmentCreate,
    request: Request,
    user: User = Depends(require_permission('punishment_manage'))
):
    """更新处分记录"""
    with get_moral_db() as db:
        old_record = db.query_one(
            "SELECT * FROM punishment_record WHERE id = %s",
            (record_id,)
        )
        if not old_record:
            raise HTTPException(404, "记录不存在")

        # 处分等级文本
        level_map = {1: '一级', 2: '二级', 3: '三级', 4: '四级'}
        level_text = level_map.get(punishment.punishment_level, '二级')

        db.execute(
            """UPDATE punishment_record SET
            punishment_date = %s, level = %s, reason = %s, score_deduct = %s
            WHERE id = %s""",
            (punishment.punishment_date, level_text, punishment.punishment_reason,
             punishment.score_deduct, record_id)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'punishment_record',
            record_id, old_record['semester_id'],
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "处分记录更新成功"}


@router.post("/{record_id}/revoke", summary="撤销处分")
async def revoke_punishment(
    record_id: int,
    revoke_data: PunishmentRevoke,
    request: Request,
    user: User = Depends(require_permission('punishment_manage'))
):
    """撤销处分"""
    with get_moral_db() as db:
        old_record = db.query_one(
            "SELECT * FROM punishment_record WHERE id = %s",
            (record_id,)
        )
        if not old_record:
            raise HTTPException(404, "记录不存在")

        if old_record['is_revoked'] == 1:
            raise HTTPException(400, "该处分已撤销")

        db.execute(
            """UPDATE punishment_record SET
            is_revoked = 1, revoke_date = %s, revoke_by = %s, revoke_reason = %s
            WHERE id = %s""",
            (date.today(), user.username, revoke_data.revoke_reason, record_id)
        )

        log_operation(
            db, user.username, user.role, 'REVOKE', 'punishment_record',
            record_id, old_record['semester_id'],
            new_data={'revoke_reason': revoke_data.revoke_reason},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "处分已撤销"}