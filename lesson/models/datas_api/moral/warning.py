# -*- coding: utf-8 -*-
"""
德育预警查询 API

提供预警信息的查询和管理功能
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
)
from .api_permission import require_configured_api_permission
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/warnings", tags=["德育预警"])

# API 路径常量
API_WARNING_LIST = "/api/moral/warnings"


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="获取预警列表")
async def get_warnings(
    is_read: Optional[int] = Query(None, description="是否已读：0=未读，1=已读"),
    warning_level: Optional[str] = Query(None, description="预警级别：warning/error"),
    class_id: Optional[int] = Query(None, description="班级ID"),
    grade_id: Optional[int] = Query(None, description="年级ID"),
    days: int = Query(30, ge=1, le=365, description="查询最近N天的预警"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_configured_api_permission(API_WARNING_LIST, "GET", allow_missing=False))
):
    """
    获取预警列表（管理员/班主任）

    权限：
    - 管理员可查看全部
    - 班主任仅可查看本班
    """
    with get_moral_db() as db:
        conditions = ["wl.id IS NOT NULL"]
        params = []

        # 时间范围
        import datetime
        start_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        conditions.append("wl.created_at >= ?")
        params.append(start_date)

        if is_read is not None:
            conditions.append("wl.is_read = ?")
            params.append(is_read)

        if warning_level:
            conditions.append("wl.warning_level = ?")
            params.append(warning_level)

        if class_id:
            conditions.append("s.class_id = ?")
            params.append(class_id)

        if grade_id:
            conditions.append("s.grade_id = ?")
            params.append(grade_id)

        # 数据范围控制
        view_scope = get_record_data_scope(
            db,
            user,
            API_WARNING_LIST,
            all_permissions=['punishment_manage', 'report_view_all'],
            own_class_permissions=['moral_record_own_class', 'report_view_own_class'],
            own_permissions=['moral_record_input', 'moral_record_view_own'],
        )
        append_record_scope_condition(
            conditions,
            params,
            view_scope,
            table_alias="s",
            username=user.username,
        )

        where_clause = " AND ".join(conditions)

        # 查询总数
        total = db.query_value(
            f"""SELECT COUNT(*) FROM warning_log wl
                JOIN student s ON wl.student_id = s.student_id
                WHERE {where_clause}""",
            params
        )

        # 分页查询
        offset = (page - 1) * page_size
        warnings = db.query_all(
            f"""SELECT wl.id, wl.student_id, wl.warning_level, wl.message, wl.is_read,
                       wl.created_at, wl.rule_id,
                       s.name as student_name, c.class_name, c.class_id, g.grade_name,
                       wc.trigger_type, wc.trigger_value
                FROM warning_log wl
                JOIN student s ON wl.student_id = s.student_id
                JOIN class c ON s.class_id = c.class_id
                JOIN grade g ON s.grade_id = g.grade_id
                LEFT JOIN warning_config wc ON wl.rule_id = wc.id
                WHERE {where_clause}
                ORDER BY wl.created_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        )

        return {
            "success": True,
            "data": warnings,
            "summary": {
                "total": total or 0,
                "unread_count": sum(1 for w in warnings if not w.get("is_read")),
                "query_days": days
            },
            "page": page,
            "page_size": page_size
        }


@router.post("/{warning_id}/read", summary="标记预警已读")
async def mark_warning_read(
    warning_id: int,
    user: User = Depends(require_configured_api_permission(API_WARNING_LIST, "POST", allow_missing=False))
):
    """标记单条预警为已读"""
    with get_moral_db() as db:
        warning = db.query_one(
            """SELECT wl.*, s.class_id
               FROM warning_log wl
               JOIN student s ON wl.student_id = s.student_id
               WHERE wl.id = ?""",
            (warning_id,)
        )
        if not warning:
            raise HTTPException(404, "预警记录不存在")

        # 权限检查
        view_scope = get_record_data_scope(
            db,
            user,
            API_WARNING_LIST,
            all_permissions=['punishment_manage', 'report_view_all'],
            own_class_permissions=['moral_record_own_class', 'report_view_own_class'],
            own_permissions=['moral_record_input', 'moral_record_view_own'],
        )

        if not record_in_scope(warning, view_scope, username=user.username):
            raise HTTPException(403, "只能操作授权范围内的预警")

        db.execute(
            "UPDATE warning_log SET is_read = 1 WHERE id = ?",
            (warning_id,)
        )

        return {"success": True, "message": "已标记为已读"}


@router.post("/mark-all-read", summary="批量标记已读")
async def mark_all_warnings_read(
    user: User = Depends(require_configured_api_permission(API_WARNING_LIST, "POST", allow_missing=False))
):
    """标记当前用户可见范围内的所有预警为已读"""
    with get_moral_db() as db:
        conditions = ["is_read = 0"]
        params = []

        view_scope = get_record_data_scope(
            db,
            user,
            API_WARNING_LIST,
            all_permissions=['punishment_manage', 'report_view_all'],
            own_class_permissions=['moral_record_own_class', 'report_view_own_class'],
            own_permissions=['moral_record_input', 'moral_record_view_own'],
        )

        if not view_scope.get("can_all"):
            student_conditions = []
            student_params = []
            append_record_scope_condition(
                student_conditions,
                student_params,
                view_scope,
                table_alias="s",
                username=user.username,
            )
            student_where = " AND ".join(student_conditions) if student_conditions else "1 = 0"
            conditions.append(f"student_id IN (SELECT s.student_id FROM student s WHERE {student_where})")
            params.extend(student_params)

        where_clause = " AND ".join(conditions)
        db.execute(f"UPDATE warning_log SET is_read = 1 WHERE {where_clause}", params)

        return {"success": True, "message": "已全部标记为已读"}
