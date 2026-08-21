# -*- coding: utf-8 -*-
"""
德育预警规则配置 API

提供预警规则的增删改查功能
"""

import logging
import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .api_permission import require_configured_api_permission
from .base import get_moral_db, log_operation
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/warning-config", tags=["德育预警规则配置"])


def _ensure_schema(db):
    """确保 warning_config 表结构完整"""
    columns = [row['name'] for row in db.query_all("PRAGMA table_info(warning_config)") or []]
    if 'is_deleted' not in columns:
        db.execute("ALTER TABLE warning_config ADD COLUMN is_deleted INTEGER DEFAULT 0")
    if 'time_window_days' not in columns:
        db.execute("ALTER TABLE warning_config ADD COLUMN time_window_days INTEGER")
        # 给现有规则设默认值：
        # - 违纪次数类：默认7天（一周）
        # - 扣分过多（负数 threshold）：默认30天
        # - 低分预警（正数 threshold）：NULL = 整个学期（当前状态）
        db.execute(
            "UPDATE warning_config SET time_window_days = 7 WHERE trigger_type = 'count_threshold'"
        )
        db.execute(
            "UPDATE warning_config SET time_window_days = 30 WHERE trigger_type = 'score_threshold' AND trigger_value < 0"
        )

API_WARNING_CONFIG_LIST = "/api/moral/warning-config"
API_WARNING_CONFIG_CREATE = "/api/moral/warning-config/create"
API_WARNING_CONFIG_UPDATE = "/api/moral/warning-config/update"
API_WARNING_CONFIG_DELETE = "/api/moral/warning-config/delete"


# =============================================================================
# Pydantic 模型
# =============================================================================

class WarningRuleCreate(BaseModel):
    """创建预警规则"""
    rule_name: str = Field(..., description="规则名称", min_length=1, max_length=50)
    trigger_type: str = Field(..., description="触发类型：score_threshold/count_threshold")
    trigger_value: int = Field(..., description="触发阈值")
    time_window_days: Optional[int] = Field(None, description="时间窗口（天），0=不限制（整个学期/当前状态）", ge=0, le=365)
    notify_roles: List[str] = Field(default_factory=list, description="通知角色列表")
    is_active: int = Field(1, description="是否启用：1=启用，0=停用")


class WarningRuleUpdate(BaseModel):
    """更新预警规则"""
    rule_name: Optional[str] = Field(None, description="规则名称")
    trigger_type: Optional[str] = Field(None, description="触发类型")
    trigger_value: Optional[int] = Field(None, description="触发阈值")
    time_window_days: Optional[int] = Field(None, description="时间窗口（天），0=不限制，None=不更新此字段", ge=0, le=365)
    notify_roles: Optional[List[str]] = Field(None, description="通知角色列表")
    is_active: Optional[int] = Field(None, description="是否启用")


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="获取预警规则列表")
async def get_warning_config_list(
    is_active: Optional[int] = Query(None, description="是否启用筛选"),
    trigger_type: Optional[str] = Query(None, description="触发类型筛选"),
    user: User = Depends(require_configured_api_permission(API_WARNING_CONFIG_LIST, "GET", allow_missing=False))
):
    """获取所有预警规则"""
    with get_moral_db() as db:
        _ensure_schema(db)

        conditions = ["is_deleted = 0"]
        params = []

        if is_active is not None:
            conditions.append("is_active = ?")
            params.append(is_active)

        if trigger_type:
            conditions.append("trigger_type = ?")
            params.append(trigger_type)

        where_clause = " AND ".join(conditions)
        rules = db.query_all(
            f"SELECT * FROM warning_config WHERE {where_clause} ORDER BY id ASC",
            tuple(params) if params else None
        )

        # 解析 notify_roles JSON
        result = []
        for rule in rules or []:
            rule_dict = dict(rule)
            try:
                rule_dict['notify_roles'] = json.loads(rule_dict.get('notify_roles') or '[]')
            except (json.JSONDecodeError, TypeError):
                rule_dict['notify_roles'] = []
            result.append(rule_dict)

        return {"success": True, "data": result}


@router.post("", summary="创建预警规则")
async def create_warning_rule(
    rule_data: WarningRuleCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_WARNING_CONFIG_CREATE, "POST", allow_missing=False))
):
    """创建新的预警规则"""
    with get_moral_db() as db:
        _ensure_schema(db)
        db.execute(
            """INSERT INTO warning_config
               (rule_name, trigger_type, trigger_value, time_window_days, notify_roles, is_active)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                rule_data.rule_name,
                rule_data.trigger_type,
                rule_data.trigger_value,
                rule_data.time_window_days if rule_data.time_window_days and rule_data.time_window_days > 0 else None,
                json.dumps(rule_data.notify_roles),
                rule_data.is_active
            )
        )

        rule_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'warning_config',
            rule_id,
            new_data={
                'rule_name': rule_data.rule_name,
                'trigger_type': rule_data.trigger_type,
                'trigger_value': rule_data.trigger_value,
                'notify_roles': rule_data.notify_roles,
                'is_active': rule_data.is_active,
            },
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "规则创建成功", "data": {"id": rule_id}}


@router.put("/{rule_id}", summary="更新预警规则")
async def update_warning_rule(
    rule_id: int,
    update_data: WarningRuleUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_WARNING_CONFIG_UPDATE, "PUT", allow_missing=False))
):
    """更新预警规则"""
    with get_moral_db() as db:
        _ensure_schema(db)

        old_rule = db.query_one(
            "SELECT * FROM warning_config WHERE id = ? AND is_deleted = 0",
            (rule_id,)
        )
        if not old_rule:
            raise HTTPException(404, "规则不存在")

        updates = []
        params = []
        old_data = dict(old_rule)

        if update_data.rule_name is not None:
            updates.append("rule_name = ?")
            params.append(update_data.rule_name)

        if update_data.trigger_type is not None:
            updates.append("trigger_type = ?")
            params.append(update_data.trigger_type)

        if update_data.trigger_value is not None:
            updates.append("trigger_value = ?")
            params.append(update_data.trigger_value)

        # time_window_days：None 表示不更新；0 表示清空（不限制时间窗口）；>0 表示具体天数
        if update_data.time_window_days is not None:
            updates.append("time_window_days = ?")
            params.append(update_data.time_window_days if update_data.time_window_days > 0 else None)

        if update_data.notify_roles is not None:
            updates.append("notify_roles = ?")
            params.append(json.dumps(update_data.notify_roles))

        if update_data.is_active is not None:
            updates.append("is_active = ?")
            params.append(update_data.is_active)

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(rule_id)
        db.execute(
            f"UPDATE warning_config SET {', '.join(updates)} WHERE id = ?",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'warning_config',
            rule_id,
            old_data=old_data,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "规则更新成功"}


@router.delete("/{rule_id}", summary="删除预警规则")
async def delete_warning_rule(
    rule_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_WARNING_CONFIG_DELETE, "DELETE", allow_missing=False))
):
    """删除预警规则（逻辑删除）"""
    with get_moral_db() as db:
        _ensure_schema(db)

        old_rule = db.query_one(
            "SELECT * FROM warning_config WHERE id = ? AND is_deleted = 0",
            (rule_id,)
        )
        if not old_rule:
            raise HTTPException(404, "规则不存在")

        # 逻辑删除：标记 is_deleted = 1，同时停用。历史预警日志的外键不受影响。
        db.execute(
            "UPDATE warning_config SET is_deleted = 1, is_active = 0 WHERE id = ?",
            (rule_id,)
        )

        log_operation(
            db, user.username, user.role, 'DELETE', 'warning_config',
            rule_id,
            old_data=dict(old_rule),
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "规则已删除"}
