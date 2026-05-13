# -*- coding: utf-8 -*-
"""
集体事件管理 API

提供集体事件的创建、分配和管理功能
"""

import logging
import json
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    get_current_semester,
    log_operation,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
    has_user_role,
)
from .api_permission import require_configured_api_permission
from models.datas_api.auth import is_admin_user
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collective-events", tags=["集体事件"])

API_COLLECTIVE_LIST = "/api/moral/collective-events"
API_COLLECTIVE_CREATE = "/api/moral/collective-events/create"
API_COLLECTIVE_UPDATE = "/api/moral/collective-events/update"
API_COLLECTIVE_DELETE = "/api/moral/collective-events/delete"
API_COLLECTIVE_DISTRIBUTION_UPDATE = "/api/moral/collective-events/distributions/update"

# =============================================================================
# Pydantic 模型
# =============================================================================

class CollectiveEventCreate(BaseModel):
    """创建集体事件"""
    event_name: str = Field(..., description="事件名称")
    event_type: str = Field(..., description="事件类型：班级荣誉/集体活动/集体违纪")
    event_date: date = Field(..., description="事件日期")
    score: int = Field(..., description="每人得分/扣分")
    class_id: int = Field(..., description="班级ID")
    description: Optional[str] = Field(None, description="事件描述")


class CollectiveEventUpdate(BaseModel):
    """更新集体事件"""
    event_name: Optional[str] = Field(None, description="事件名称")
    event_type: Optional[str] = Field(None, description="事件类型")
    event_date: Optional[date] = Field(None, description="事件日期")
    score: Optional[int] = Field(None, description="每人得分/扣分")
    description: Optional[str] = Field(None, description="事件描述")


class DistributionUpdate(BaseModel):
    """更新分配记录"""
    is_participant: int = Field(..., description="是否参与：1=是，0=否")
    score_assigned: Optional[int] = Field(None, description="实际得分（不参与时为0）")
    remark: Optional[str] = Field(None, description="备注")


def ensure_collective_class_access(user: User, db, class_id: int, api_path: str = API_COLLECTIVE_LIST):
    """校验集体事件班级访问范围。"""
    if is_admin_user(user):
        return

    scope = get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['report_view_all', 'moral_record_manage'],
        own_class_permissions=['moral_record_own_class', 'report_view_own_class'],
        own_permissions=[],
    )
    if record_in_scope({"class_id": class_id}, scope, username=user.username):
        return

    raise HTTPException(403, "只能访问授权班级范围内的集体事件")


# =============================================================================
# API 路由 - 集体事件管理
# =============================================================================

@router.get("", summary="获取集体事件列表")
async def get_collective_events(
    class_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    semester_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_configured_api_permission(API_COLLECTIVE_LIST, "GET", allow_missing=False))
):
    """
    获取集体事件列表

    权限说明：
    - admin/jiaowu/xuefa: 可查看所有
    - cleader: 只能查看本班
    """
    with get_moral_db() as db:
        
        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        conditions = ["ce.semester_id = ?"]
        params = [semester_id]

        if class_id:
            conditions.append("ce.class_id = ?")
            params.append(class_id)

        view_scope = get_record_data_scope(
            db,
            user,
            API_COLLECTIVE_LIST,
            all_permissions=['report_view_all', 'moral_record_manage'],
            own_class_permissions=['moral_record_own_class', 'report_view_own_class'],
            own_permissions=[],
        )
        append_record_scope_condition(
            conditions,
            params,
            view_scope,
            table_alias="ce",
            username=user.username,
        )

        if event_type:
            conditions.append("ce.event_type = ?")
            params.append(event_type)

        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*) FROM collective_event ce WHERE {where_clause}
        """
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT ce.event_id, ce.event_name, ce.event_type, ce.event_date, ce.class_id, ce.score,
                   ce.description, ce.created_at, c.class_name, g.grade_name,
                   (SELECT COUNT(*) FROM collective_event_distribution ced
                    WHERE ced.event_id = ce.event_id AND ced.is_participant = 1) as participant_count
            FROM collective_event ce
            JOIN class c ON ce.class_id = c.class_id
            JOIN grade g ON c.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY ce.event_date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        events = db.query_all(data_query, tuple(params))

        return {
            "success": True,
            "data": {
                "items": events,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


@router.post("", summary="创建集体事件")
async def create_collective_event(
    event: CollectiveEventCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_COLLECTIVE_CREATE, "POST", allow_missing=False))
):
    """
    创建集体事件并自动分配给班级学生

    流程：
    1. 创建集体事件记录
    2. 获取班级所有在校学生
    3. 自动为每个学生分配分数
    """
    with get_moral_db() as db:
        
        current_semester = get_current_semester(db)
        if not current_semester:
            raise HTTPException(400, "当前学期未配置")

        semester_id = current_semester['semester_id']

        # 检查班级是否存在
        class_info = db.query_one(
            "SELECT c.class_id, c.class_name, c.grade_id FROM class c WHERE c.class_id = ?",
            (event.class_id,)
        )
        if not class_info:
            raise HTTPException(404, "班级不存在")

        ensure_collective_class_access(user, db, event.class_id, API_COLLECTIVE_CREATE)

        # 分值校验
        if event.event_type in ['班级荣誉', '集体活动']:
            if event.score <= 0:
                raise HTTPException(400, "荣誉/活动分值必须为正数")
        elif event.event_type == '集体违纪':
            if event.score >= 0:
                raise HTTPException(400, "违纪扣分必须为负数")

        # 创建集体事件
        db.execute(
            """INSERT INTO collective_event
            (event_name, event_type, semester_id, event_date, class_id, score, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event.event_name, event.event_type, semester_id, event.event_date,
             event.class_id, event.score, event.description)
        )

        event_id = db.lastrowid()

        # 获取班级所有在校学生
        students = db.query_all(
            """SELECT s.student_id, s.class_id FROM student s
            WHERE s.class_id = ? AND s.status = '在校'""",
            (event.class_id,)
        )

        # 为每个学生分配分数
        for student in students:
            db.execute(
                """INSERT INTO collective_event_distribution
                (event_id, student_id, class_id, score_assigned, is_participant, remark)
                VALUES (?, ?, ?, ?, 1, NULL)""",
                (event_id, student['student_id'], student['class_id'], event.score)
            )

        from .evaluation import calculate_evaluation
        for student in students:
            calculate_evaluation(
                db,
                student['student_id'],
                semester_id,
                student['class_id'],
                class_info['grade_id'],
            )

        log_operation(
            db, user.username, user.role, 'INSERT', 'collective_event', event_id,
            semester_id,
            new_data={'event_name': event.event_name, 'class_id': event.class_id,
                      'score': event.score, 'student_count': len(students)},
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "message": f"集体事件创建成功，已分配给 {len(students)} 名学生",
            "data": {"event_id": event_id, "student_count": len(students)}
        }


@router.get("/{event_id}", summary="获取集体事件详情")
async def get_collective_event(
    event_id: int,
    user: User = Depends(require_configured_api_permission(API_COLLECTIVE_LIST, "GET", allow_missing=False))
):
    """获取集体事件详情，包含分配列表"""
    with get_moral_db() as db:
        
        event = db.query_one(
            """SELECT ce.*, c.class_name, g.grade_name
            FROM collective_event ce
            JOIN class c ON ce.class_id = c.class_id
            JOIN grade g ON c.grade_id = g.grade_id
            WHERE ce.event_id = ?""",
            (event_id,)
        )

        if not event:
            raise HTTPException(404, "事件不存在")

        ensure_collective_class_access(user, db, event['class_id'], API_COLLECTIVE_LIST)

        # 获取分配列表
        distributions = db.query_all(
            """SELECT ced.*, s.name as student_name
            FROM collective_event_distribution ced
            JOIN student s ON ced.student_id = s.student_id
            WHERE ced.event_id = ?
            ORDER BY s.student_id""",
            (event_id,)
        )

        event['distributions'] = distributions

        return {"success": True, "data": event}


@router.put("/{event_id}", summary="更新集体事件")
async def update_collective_event(
    event_id: int,
    event: CollectiveEventUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_COLLECTIVE_UPDATE, "PUT", allow_missing=False))
):
    """更新集体事件基本信息"""
    with get_moral_db() as db:
        
        old_event = db.query_one(
            "SELECT * FROM collective_event WHERE event_id = ?",
            (event_id,)
        )
        if not old_event:
            raise HTTPException(404, "事件不存在")

        ensure_collective_class_access(user, db, old_event['class_id'], API_COLLECTIVE_UPDATE)

        # 构建更新语句
        updates = []
        params = []

        if event.event_name is not None:
            updates.append("event_name = ?")
            params.append(event.event_name)

        if event.event_type is not None:
            updates.append("event_type = ?")
            params.append(event.event_type)

        if event.event_date is not None:
            updates.append("event_date = ?")
            params.append(event.event_date)

        if event.score is not None:
            updates.append("score = ?")
            params.append(event.score)

        if event.description is not None:
            updates.append("description = ?")
            params.append(event.description)

        if not updates:
            return {"success": True, "message": "无需更新"}

        params.append(event_id)
        update_query = f"UPDATE collective_event SET {', '.join(updates)} WHERE event_id = ?"
        db.execute(update_query, tuple(params))

        if event.score is not None:
            db.execute(
                """UPDATE collective_event_distribution
                SET score_assigned = ?
                WHERE event_id = ? AND is_participant = 1""",
                (event.score, event_id)
            )

        distributions = db.query_all(
            """SELECT ced.student_id, ced.class_id, c.grade_id
            FROM collective_event_distribution ced
            JOIN class c ON ced.class_id = c.class_id
            WHERE ced.event_id = ?""",
            (event_id,)
        )
        from .evaluation import calculate_evaluation
        for distribution in distributions:
            calculate_evaluation(
                db,
                distribution['student_id'],
                old_event['semester_id'],
                distribution['class_id'],
                distribution['grade_id'],
            )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'collective_event', event_id,
            old_event['semester_id'],
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "事件更新成功"}


@router.delete("/{event_id}", summary="删除集体事件")
async def delete_collective_event(
    event_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_COLLECTIVE_DELETE, "DELETE", allow_missing=False))
):
    """删除集体事件及其分配记录"""
    with get_moral_db() as db:
        
        event = db.query_one(
            "SELECT * FROM collective_event WHERE event_id = ?",
            (event_id,)
        )
        if not event:
            raise HTTPException(404, "事件不存在")

        ensure_collective_class_access(user, db, event['class_id'], API_COLLECTIVE_DELETE)

        distributions = db.query_all(
            """SELECT ced.student_id, ced.class_id, c.grade_id
            FROM collective_event_distribution ced
            JOIN class c ON ced.class_id = c.class_id
            WHERE ced.event_id = ?""",
            (event_id,)
        )

        # 删除分配记录
        db.execute(
            "DELETE FROM collective_event_distribution WHERE event_id = ?",
            (event_id,)
        )

        # 删除事件
        db.execute(
            "DELETE FROM collective_event WHERE event_id = ?",
            (event_id,)
        )

        log_operation(
            db, user.username, user.role, 'DELETE', 'collective_event', event_id,
            event['semester_id'],
            ip_address=request.client.host if request.client else None
        )

        from .evaluation import calculate_evaluation
        for distribution in distributions:
            calculate_evaluation(
                db,
                distribution['student_id'],
                event['semester_id'],
                distribution['class_id'],
                distribution['grade_id'],
            )

        return {"success": True, "message": "事件已删除"}


# =============================================================================
# API 路由 - 分配管理
# =============================================================================

@router.get("/{event_id}/distributions", summary="获取分配列表")
async def get_distributions(
    event_id: int,
    user: User = Depends(require_configured_api_permission(API_COLLECTIVE_LIST, "GET", allow_missing=False))
):
    """获取集体事件的学生分配列表"""
    with get_moral_db() as db:
        
        event = db.query_one(
            "SELECT class_id FROM collective_event WHERE event_id = ?",
            (event_id,)
        )
        if not event:
            raise HTTPException(404, "事件不存在")

        ensure_collective_class_access(user, db, event['class_id'], API_COLLECTIVE_LIST)

        distributions = db.query_all(
            """SELECT ced.id, ced.event_id, ced.student_id, ced.score_assigned,
                   ced.is_participant, ced.remark,
                   s.name as student_name, s.status as student_status
            FROM collective_event_distribution ced
            JOIN student s ON ced.student_id = s.student_id
            WHERE ced.event_id = ?
            ORDER BY s.student_id""",
            (event_id,)
        )

        return {"success": True, "data": distributions}


@router.put("/{event_id}/distributions/{distribution_id}", summary="更新分配记录")
async def update_distribution(
    event_id: int,
    distribution_id: int,
    update: DistributionUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_COLLECTIVE_DISTRIBUTION_UPDATE, "PUT", allow_missing=False))
):
    """
    更新单个学生的分配记录

    用例：学生未参与集体活动，标记不加分
    """
    with get_moral_db() as db:
        
        distribution = db.query_one(
            """SELECT ced.*, ce.score as original_score
            FROM collective_event_distribution ced
            JOIN collective_event ce ON ced.event_id = ce.event_id
            WHERE ced.id = ? AND ced.event_id = ?""",
            (distribution_id, event_id)
        )

        if not distribution:
            raise HTTPException(404, "分配记录不存在")

        ensure_collective_class_access(user, db, distribution['class_id'], API_COLLECTIVE_DISTRIBUTION_UPDATE)

        # 计算实际得分
        if update.is_participant == 0:
            score_assigned = 0
        else:
            score_assigned = update.score_assigned if update.score_assigned else distribution['original_score']

        db.execute(
            """UPDATE collective_event_distribution SET
            is_participant = ?, score_assigned = ?, remark = ?
            WHERE id = ?""",
            (update.is_participant, score_assigned, update.remark, distribution_id)
        )

        event = db.query_one(
            "SELECT semester_id FROM collective_event WHERE event_id = ?",
            (event_id,)
        )
        class_info = db.query_one(
            "SELECT grade_id FROM class WHERE class_id = ?",
            (distribution['class_id'],)
        )
        if event and class_info:
            from .evaluation import calculate_evaluation
            calculate_evaluation(
                db,
                distribution['student_id'],
                event['semester_id'],
                distribution['class_id'],
                class_info['grade_id'],
            )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'collective_event_distribution',
            distribution_id, None,
            new_data={'is_participant': update.is_participant, 'score_assigned': score_assigned},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "分配记录已更新"}


@router.get("/student/{student_id}", summary="获取学生集体事件得分汇总")
async def get_student_collective_score(
    student_id: str,
    semester_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    """获取学生在某学期的集体事件得分汇总"""
    with get_moral_db() as db:
        student = db.query_one(
            "SELECT student_id, class_id FROM student WHERE student_id = ?",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        if has_user_role(user, 'student'):
            if user.username != student_id:
                raise HTTPException(403, "只能查看自己的集体事件得分")
        else:
            ensure_collective_class_access(user, db, student['class_id'], API_COLLECTIVE_LIST)

        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        records = db.query_all(
            """SELECT ced.id, ced.score_assigned, ced.is_participant,
                   ce.event_id, ce.event_name, ce.event_type, ce.event_date
            FROM collective_event_distribution ced
            JOIN collective_event ce ON ced.event_id = ce.event_id
            WHERE ced.student_id = ? AND ce.semester_id = ?
            ORDER BY ce.event_date DESC""",
            (student_id, semester_id)
        )

        total_score = sum(r['score_assigned'] or 0 for r in records if r['is_participant'] == 1)

        return {
            "success": True,
            "data": {
                "records": records,
                "total_score": total_score,
                "record_count": len(records)
            }
        }
