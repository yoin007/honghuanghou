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
    status: Optional[str] = Query(None, description="状态：active/resolved"),
    handle_status: Optional[str] = Query(None, description="处置状态：handled=已处置 / unhandled=未处置"),
    warning_level: Optional[str] = Query(None, description="预警级别：warning/error/escalation_*"),
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
    import datetime

    with get_moral_db() as db:
        # 用 (condition, params) 成对构建，避免过滤时索引错位
        filters = [("wl.id IS NOT NULL", [])]

        # 时间范围
        start_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        filters.append(("wl.created_at >= ?", [start_date]))

        if is_read is not None:
            filters.append(("wl.is_read = ?", [is_read]))

        if status:
            filters.append(("wl.status = ?", [status]))

        if warning_level:
            filters.append(("wl.warning_level = ?", [warning_level]))

        if class_id:
            filters.append(("s.class_id = ?", [class_id]))

        if grade_id:
            filters.append(("s.grade_id = ?", [grade_id]))

        if handle_status == 'handled':
            filters.append(("(SELECT COUNT(*) FROM warning_handle wh WHERE wh.warning_id = wl.id) > 0", []))
        elif handle_status == 'unhandled':
            filters.append(("(SELECT COUNT(*) FROM warning_handle wh WHERE wh.warning_id = wl.id) = 0", []))

        # 数据范围控制
        view_scope = get_record_data_scope(
            db,
            user,
            API_WARNING_LIST,
            all_permissions=['punishment_manage', 'report_view_all'],
            own_class_permissions=['moral_record_own_class', 'report_view_own_class'],
            own_permissions=['moral_record_input', 'moral_record_view_own'],
        )

        scope_conditions = []
        scope_params = []
        append_record_scope_condition(
            scope_conditions,
            scope_params,
            view_scope,
            table_alias="s",
            username=user.username,
        )
        if scope_conditions:
            filters.append((" AND ".join(scope_conditions), scope_params))

        conditions = [f[0] for f in filters]
        params = [p for f in filters for p in f[1]]
        where_clause = " AND ".join(conditions)

        # 无 status 条件的基础 where（用于 total/统计）
        base_filters = [f for f in filters if f[0] != "wl.status = ?"]
        base_conditions = [f[0] for f in base_filters]
        base_params = [p for f in base_filters for p in f[1]]
        base_where_clause = " AND ".join(base_conditions)

        # 查询总数（不受 status 选项卡影响）
        total = db.query_value(
            f"""SELECT COUNT(*) FROM warning_log wl
                JOIN student s ON wl.student_id = s.student_id
                WHERE {base_where_clause}""",
            base_params
        )

        # 活跃/已消除统计（按当前筛选条件）
        active_total = db.query_value(
            f"""SELECT COUNT(*) FROM warning_log wl
                JOIN student s ON wl.student_id = s.student_id
                WHERE {base_where_clause} AND wl.status = 'active'""",
            base_params
        )
        resolved_total = db.query_value(
            f"""SELECT COUNT(*) FROM warning_log wl
                JOIN student s ON wl.student_id = s.student_id
                WHERE {base_where_clause} AND wl.status = 'resolved'""",
            base_params
        )

        # 分页查询（补充 status/resolved_at/resolved_reason/handle_count 字段）
        offset = (page - 1) * page_size
        warnings = db.query_all(
            f"""SELECT wl.id, wl.student_id, wl.warning_level, wl.message, wl.is_read,
                       wl.created_at, wl.rule_id, wl.status, wl.resolved_at, wl.resolved_reason,
                       s.name as student_name, c.class_name, c.class_id, g.grade_name,
                       wc.trigger_type, wc.trigger_value,
                       COALESCE((SELECT COUNT(*) FROM warning_handle wh WHERE wh.warning_id = wl.id), 0) as handle_count
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

        # 活跃且未处置的数量（真正需要关注的预警）
        unhandled_active = db.query_value(
            f"""SELECT COUNT(*) FROM warning_log wl
                JOIN student s ON wl.student_id = s.student_id
                WHERE {base_where_clause}
                  AND wl.status = 'active'
                  AND (SELECT COUNT(*) FROM warning_handle wh WHERE wh.warning_id = wl.id) = 0""",
            base_params
        )

        return {
            "success": True,
            "data": warnings,
            "summary": {
                "total": total or 0,
                "active_count": active_total or 0,
                "resolved_count": resolved_total or 0,
                "unread_count": sum(1 for w in warnings if not w.get("is_read")),
                "unhandled_active_count": unhandled_active or 0,
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


@router.post("/{warning_id}/resolve", summary="标记预警已消除")
async def resolve_warning(
    warning_id: int,
    user: User = Depends(require_configured_api_permission(API_WARNING_LIST, "POST", allow_missing=False))
):
    """手动标记单条预警为已消除"""
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
            """UPDATE warning_log
               SET status = 'resolved',
                   resolved_at = datetime('now', 'localtime'),
                   resolved_reason = 'manual'
               WHERE id = ?""",
            (warning_id,)
        )

        return {"success": True, "message": "已标记为消除"}


@router.post("/batch-resolve", summary="批量标记消除")
async def batch_resolve_warnings(
    user: User = Depends(require_configured_api_permission(API_WARNING_LIST, "POST", allow_missing=False))
):
    """标记当前用户可见范围内所有活跃预警为已消除"""
    with get_moral_db() as db:
        conditions = ["status = 'active'"]
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
        count = db.query_value(
            f"SELECT COUNT(*) FROM warning_log WHERE {where_clause}",
            params
        )
        db.execute(
            f"""UPDATE warning_log
                SET status = 'resolved',
                    resolved_at = datetime('now', 'localtime'),
                    resolved_reason = 'manual'
                WHERE {where_clause}""",
            params
        )

        return {"success": True, "message": f"已消除 {count or 0} 条预警", "count": count or 0}
