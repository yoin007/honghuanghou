# -*- coding: utf-8 -*-
"""
预警处置记录 API

提供预警处置记录的增删改查功能
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .api_permission import require_configured_api_permission
from .base import get_moral_db, log_operation, get_record_data_scope, record_in_scope
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(tags=["德育预警处置"])

API_WARNING_HANDLE_LIST = "/api/moral/warning-handle/list"
API_WARNING_HANDLE_CREATE = "/api/moral/warning-handle/create"
API_WARNING_HANDLE_UPDATE = "/api/moral/warning-handle/update"
API_WARNING_HANDLE_DELETE = "/api/moral/warning-handle/delete"

# 数据范围判断复用预警日志的权限
API_WARNING_REFERENCE = "/api/moral/warnings"


def _ensure_warning_access(db, user: User, warning_id: int) -> dict:
    """校验用户是否有权限操作这条预警，返回预警详情。"""
    warning = db.query_one(
        """SELECT wl.*, s.class_id, s.grade_id, s.student_id
           FROM warning_log wl
           JOIN student s ON wl.student_id = s.student_id
           WHERE wl.id = ?""",
        (warning_id,)
    )
    if not warning:
        raise HTTPException(404, "预警记录不存在")

    scope = get_record_data_scope(
        db,
        user,
        API_WARNING_REFERENCE,
        all_permissions=['punishment_manage', 'report_view_all'],
        own_class_permissions=['moral_record_own_class', 'report_view_own_class'],
        own_permissions=['moral_record_input', 'moral_record_view_own'],
    )
    if not record_in_scope(warning, scope, username=user.username):
        raise HTTPException(403, "只能操作授权范围内的预警")

    return warning


# =============================================================================
# Pydantic 模型
# =============================================================================

class WarningHandleCreate(BaseModel):
    """创建处置记录"""
    handle_type: str = Field(..., description="处置方式：talk/parent/home_visit/psychology/class_criticism/other")
    handle_date: Optional[str] = Field(None, description="处置日期 YYYY-MM-DD")
    content: str = Field(..., description="处置详情", min_length=1)
    effect: Optional[str] = Field(None, description="效果评估：good/normal/poor")
    follow_up_date: Optional[str] = Field(None, description="计划回访日期")
    resolve_warning: bool = Field(False, description="是否同时消除预警")


class WarningHandleUpdate(BaseModel):
    """更新处置记录"""
    handle_type: Optional[str] = Field(None, description="处置方式")
    handle_date: Optional[str] = Field(None, description="处置日期")
    content: Optional[str] = Field(None, description="处置详情")
    effect: Optional[str] = Field(None, description="效果评估")
    follow_up_date: Optional[str] = Field(None, description="计划回访日期")


# =============================================================================
# API 路由
# =============================================================================

@router.get("/warnings/{warning_id}/handles", summary="获取预警的处置记录列表")
async def get_warning_handles(
    warning_id: int,
    user: User = Depends(require_configured_api_permission(API_WARNING_HANDLE_LIST, "GET", allow_missing=False))
):
    """获取某条预警的所有处置记录，按时间倒序"""
    with get_moral_db() as db:
        _ensure_warning_access(db, user, warning_id)

        handles = db.query_all(
            """SELECT * FROM warning_handle
               WHERE warning_id = ?
               ORDER BY handle_date DESC, created_at DESC""",
            (warning_id,)
        )

        return {"success": True, "data": handles or []}


@router.post("/warnings/{warning_id}/handles", summary="新增处置记录")
async def create_warning_handle(
    warning_id: int,
    handle_data: WarningHandleCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_WARNING_HANDLE_CREATE, "POST", allow_missing=False))
):
    """新增处置记录，可选同时消除预警"""
    with get_moral_db() as db:
        warning = _ensure_warning_access(db, user, warning_id)

        # 获取处理人信息
        handler_name = getattr(user, 'name', None) or getattr(user, 'username', user.username)

        db.execute(
            """INSERT INTO warning_handle
               (warning_id, handle_type, handle_date, handler_name, handler_id,
                content, effect, follow_up_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                warning_id,
                handle_data.handle_type,
                handle_data.handle_date,
                handler_name,
                user.username,
                handle_data.content,
                handle_data.effect,
                handle_data.follow_up_date,
            )
        )

        handle_id = db.lastrowid()

        # 可选：同时消除预警
        resolved = False
        if handle_data.resolve_warning and warning['status'] == 'active':
            db.execute(
                """UPDATE warning_log
                   SET status = 'resolved',
                       resolved_at = datetime('now', 'localtime'),
                       resolved_reason = 'manual'
                   WHERE id = ?""",
                (warning_id,)
            )
            resolved = True

        log_operation(
            db, user.username, user.role, 'INSERT', 'warning_handle',
            handle_id, warning.get('semester_id'),
            new_data={
                'warning_id': warning_id,
                'handle_type': handle_data.handle_type,
                'content': handle_data.content[:100] + ('...' if len(handle_data.content) > 100 else ''),
                'effect': handle_data.effect,
                'resolve_warning': handle_data.resolve_warning,
            },
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "message": "处置记录已保存" + ("，预警已消除" if resolved else ""),
            "data": {"id": handle_id, "resolved": resolved}
        }


@router.put("/warnings/{warning_id}/handles/{handle_id}", summary="更新处置记录")
async def update_warning_handle(
    warning_id: int,
    handle_id: int,
    update_data: WarningHandleUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_WARNING_HANDLE_UPDATE, "PUT", allow_missing=False))
):
    """更新处置记录（仅创建人或管理员可编辑）"""
    with get_moral_db() as db:
        _ensure_warning_access(db, user, warning_id)

        old = db.query_one(
            "SELECT * FROM warning_handle WHERE id = ? AND warning_id = ?",
            (handle_id, warning_id)
        )
        if not old:
            raise HTTPException(404, "处置记录不存在")

        # 权限：管理员可改所有，普通用户只能改自己创建的
        is_admin = user.role == 'admin' or getattr(user, 'is_admin', False)
        if not is_admin and old['handler_id'] != user.username:
            raise HTTPException(403, "只能修改自己创建的处置记录")

        updates = []
        params = []

        if update_data.handle_type is not None:
            updates.append("handle_type = ?")
            params.append(update_data.handle_type)
        if update_data.handle_date is not None:
            updates.append("handle_date = ?")
            params.append(update_data.handle_date)
        if update_data.content is not None:
            updates.append("content = ?")
            params.append(update_data.content)
        if update_data.effect is not None:
            updates.append("effect = ?")
            params.append(update_data.effect)
        if update_data.follow_up_date is not None:
            updates.append("follow_up_date = ?")
            params.append(update_data.follow_up_date)

        if not updates:
            return {"success": True, "message": "无更新内容"}

        updates.append("updated_at = datetime('now', 'localtime')")
        params.append(handle_id)

        db.execute(
            f"UPDATE warning_handle SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'warning_handle',
            handle_id,
            old_data={'id': handle_id, 'warning_id': warning_id},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "更新成功"}


@router.delete("/warnings/{warning_id}/handles/{handle_id}", summary="删除处置记录")
async def delete_warning_handle(
    warning_id: int,
    handle_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_WARNING_HANDLE_DELETE, "DELETE", allow_missing=False))
):
    """删除处置记录（仅创建人或管理员）"""
    with get_moral_db() as db:
        _ensure_warning_access(db, user, warning_id)

        old = db.query_one(
            "SELECT * FROM warning_handle WHERE id = ? AND warning_id = ?",
            (handle_id, warning_id)
        )
        if not old:
            raise HTTPException(404, "处置记录不存在")

        is_admin = user.role == 'admin' or getattr(user, 'is_admin', False)
        if not is_admin and old['handler_id'] != user.username:
            raise HTTPException(403, "只能删除自己创建的处置记录")

        db.execute("DELETE FROM warning_handle WHERE id = ?", (handle_id,))

        log_operation(
            db, user.username, user.role, 'DELETE', 'warning_handle',
            handle_id,
            old_data={'id': handle_id, 'warning_id': warning_id},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "已删除"}
