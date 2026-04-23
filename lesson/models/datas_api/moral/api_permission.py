# -*- coding: utf-8 -*-
"""
API权限管理模块

提供API权限配置的增删改查功能
"""

import logging
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    get_current_user,
    log_operation,
    is_admin_user,
)
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-permissions", tags=["API权限管理"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class ApiPermissionCreate(BaseModel):
    """创建API权限配置"""
    api_path: str = Field(..., description="API路径")
    api_name: str = Field(..., description="API名称")
    api_group: str = Field(..., description="API分组")
    allowed_roles: List[str] = Field(..., description="允许访问的角色列表")
    min_level: int = Field(default=0, description="最低等级要求")
    description: Optional[str] = Field(None, description="描述")


class ApiPermissionUpdate(BaseModel):
    """更新API权限配置"""
    api_name: Optional[str] = Field(None, description="API名称")
    api_group: Optional[str] = Field(None, description="API分组")
    allowed_roles: Optional[List[str]] = Field(None, description="允许访问的角色列表")
    min_level: Optional[int] = Field(None, description="最低等级要求")
    description: Optional[str] = Field(None, description="描述")
    is_active: Optional[int] = Field(None, description="是否启用")


# =============================================================================
# 默认API权限配置
# =============================================================================

DEFAULT_API_PERMISSIONS = [
    # 日常表现记录
    {"api_path": "/api/moral/daily-records", "api_name": "获取日常记录列表", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/daily-records/types", "api_name": "获取事件类型", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/daily-records/create", "api_name": "创建日常记录", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/daily-records/batch", "api_name": "批量创建记录", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/daily-records/update", "api_name": "更新日常记录", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/daily-records/delete", "api_name": "删除日常记录", "api_group": "日常表现", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},

    # 点滴记录
    {"api_path": "/api/moral/moment-records", "api_name": "获取点滴记录", "api_group": "点滴记录", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/moment-records/create", "api_name": "创建点滴记录", "api_group": "点滴记录", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader", "teacher"], "min_level": 10},

    # 校级事件
    {"api_path": "/api/moral/school-records", "api_name": "获取校级事件", "api_group": "校级事件", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader"], "min_level": 30},
    {"api_path": "/api/moral/school-records/create", "api_name": "创建校级事件", "api_group": "校级事件", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/school-records/update", "api_name": "更新校级事件", "api_group": "校级事件", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/school-records/delete", "api_name": "删除校级事件", "api_group": "校级事件", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},

    # 处分管理
    {"api_path": "/api/moral/punishments", "api_name": "获取处分记录", "api_group": "处分管理", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/punishments/create", "api_name": "创建处分", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/punishments/revoke", "api_name": "撤销处分", "api_group": "处分管理", "allowed_roles": ["admin", "xuefa"], "min_level": 50},

    # 德育任务
    {"api_path": "/api/moral/tasks", "api_name": "获取德育任务", "api_group": "德育任务", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader"], "min_level": 30},
    {"api_path": "/api/moral/tasks/create", "api_name": "创建德育任务", "api_group": "德育任务", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/tasks/update", "api_name": "更新德育任务", "api_group": "德育任务", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/tasks/delete", "api_name": "删除德育任务", "api_group": "德育任务", "allowed_roles": ["admin", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/tasks/finish", "api_name": "记录任务完成", "api_group": "德育任务", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader"], "min_level": 30},

    # 事件类型管理
    {"api_path": "/api/moral/event-types", "api_name": "创建事件类型", "api_group": "事件类型", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/event-types/update", "api_name": "更新事件类型", "api_group": "事件类型", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/event-types/import", "api_name": "批量导入事件类型", "api_group": "事件类型", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},

    # 学生管理
    {"api_path": "/api/moral/admin/students", "api_name": "获取学生列表", "api_group": "学生管理", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader"], "min_level": 30},
    {"api_path": "/api/moral/admin/students/create", "api_name": "创建学生", "api_group": "学生管理", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
    {"api_path": "/api/moral/admin/students/update", "api_name": "更新学生信息", "api_group": "学生管理", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader"], "min_level": 30},
    {"api_path": "/api/moral/admin/students/batch", "api_name": "批量导入学生", "api_group": "学生管理", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},

    # 系统配置
    {"api_path": "/api/moral/admin/config", "api_name": "系统配置", "api_group": "系统配置", "allowed_roles": ["admin"], "min_level": 100},
    {"api_path": "/api/moral/admin/api-permissions", "api_name": "API权限管理", "api_group": "系统配置", "allowed_roles": ["admin"], "min_level": 100},

    # 生日查看
    {"api_path": "/api/moral/birthdays/upcoming", "api_name": "获取即将生日", "api_group": "生日查看", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader", "teacher"], "min_level": 10},
    {"api_path": "/api/moral/birthdays/today", "api_name": "获取今日生日", "api_group": "生日查看", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader", "teacher"], "min_level": 10},

    # 学生画像
    {"api_path": "/api/moral/profiles/student", "api_name": "获取学生画像", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa", "cleader"], "min_level": 30},
    {"api_path": "/api/moral/profiles/student/generate", "api_name": "生成学生画像", "api_group": "学生画像", "allowed_roles": ["admin", "jiaowu", "xuefa"], "min_level": 50},
]


# =============================================================================
# API路由
# =============================================================================

def require_admin(user: User = Depends(get_current_user)):
    """仅admin可访问"""
    if not is_admin_user(user):
        raise HTTPException(403, "仅管理员可访问")
    return user


@router.get("", summary="获取API权限配置列表")
async def get_api_permissions(
    api_group: Optional[str] = Query(None, description="API分组筛选"),
    user: User = Depends(require_admin)
):
    """获取API权限配置列表（仅admin）"""
    with get_moral_db() as db:
        if api_group:
            configs = db.query_all(
                "SELECT * FROM api_permission_config WHERE api_group = %s ORDER BY api_group, api_path",
                (api_group,)
            )
        else:
            configs = db.query_all(
                "SELECT * FROM api_permission_config ORDER BY api_group, api_path"
            )

        # 解析allowed_roles JSON
        for config in configs:
            if config.get('allowed_roles'):
                try:
                    config['allowed_roles'] = json.loads(config['allowed_roles'])
                except:
                    config['allowed_roles'] = []

        return {"success": True, "data": configs}


@router.post("", summary="创建API权限配置")
async def create_api_permission(
    config: ApiPermissionCreate,
    request: Request,
    user: User = Depends(require_admin)
):
    """创建API权限配置（仅admin）"""
    with get_moral_db() as db:
        # 检查是否已存在
        existing = db.query_one(
            "SELECT id FROM api_permission_config WHERE api_path = %s",
            (config.api_path,)
        )
        if existing:
            raise HTTPException(400, f"API路径 {config.api_path} 已存在")

        allowed_roles_json = json.dumps(config.allowed_roles)

        db.execute(
            """INSERT INTO api_permission_config
            (api_path, api_name, api_group, allowed_roles, min_level, description)
            VALUES (%s, %s, %s, %s, %s, %s)""",
            (config.api_path, config.api_name, config.api_group, allowed_roles_json, config.min_level, config.description)
        )

        config_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'api_permission_config', config_id,
            new_data=config.dict()
        )

        return {"success": True, "message": "创建成功", "data": {"id": config_id}}


@router.put("/{config_id}", summary="更新API权限配置")
async def update_api_permission(
    config_id: int,
    config: ApiPermissionUpdate,
    request: Request,
    user: User = Depends(require_admin)
):
    """更新API权限配置（仅admin）"""
    with get_moral_db() as db:
        existing = db.query_one(
            "SELECT * FROM api_permission_config WHERE id = %s",
            (config_id,)
        )
        if not existing:
            raise HTTPException(404, "配置不存在")

        updates = []
        params = []

        if config.api_name is not None:
            updates.append("api_name = %s")
            params.append(config.api_name)

        if config.api_group is not None:
            updates.append("api_group = %s")
            params.append(config.api_group)

        if config.allowed_roles is not None:
            updates.append("allowed_roles = %s")
            params.append(json.dumps(config.allowed_roles))

        if config.min_level is not None:
            updates.append("min_level = %s")
            params.append(config.min_level)

        if config.description is not None:
            updates.append("description = %s")
            params.append(config.description)

        if config.is_active is not None:
            updates.append("is_active = %s")
            params.append(config.is_active)

        updates.append("updated_at = datetime('now', 'localtime')")

        if not updates:
            return {"success": True, "message": "无变更"}

        params.append(config_id)

        db.execute(
            f"UPDATE api_permission_config SET {', '.join(updates)} WHERE id = %s",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'api_permission_config', config_id,
            new_data=config.dict(exclude_unset=True)
        )

        return {"success": True, "message": "更新成功"}


@router.delete("/{config_id}", summary="删除API权限配置")
async def delete_api_permission(
    config_id: int,
    request: Request,
    user: User = Depends(require_admin)
):
    """删除API权限配置（仅admin）"""
    with get_moral_db() as db:
        existing = db.query_one(
            "SELECT * FROM api_permission_config WHERE id = %s",
            (config_id,)
        )
        if not existing:
            raise HTTPException(404, "配置不存在")

        db.execute(
            "DELETE FROM api_permission_config WHERE id = %s",
            (config_id,)
        )

        log_operation(
            db, user.username, user.role, 'DELETE', 'api_permission_config', config_id
        )

        return {"success": True, "message": "删除成功"}


@router.get("/my-permissions", summary="获取当前用户可访问的API列表")
async def get_my_api_permissions(user: User = Depends(get_current_user)):
    """获取当前用户可访问的API列表"""
    with get_moral_db() as db:
        # 获取所有启用的API配置
        configs = db.query_all(
            "SELECT * FROM api_permission_config WHERE is_active = 1"
        )

        # 过滤用户有权限的API
        allowed_apis = []
        for config in configs:
            try:
                allowed_roles = json.loads(config.get('allowed_roles', '[]'))
            except:
                allowed_roles = []

            # admin拥有所有权限
            if is_admin_user(user):
                allowed_apis.append({
                    "api_path": config['api_path'],
                    "api_name": config['api_name'],
                    "api_group": config['api_group']
                })
                continue

            # 检查角色（支持多角色格式如 teacher/cleader）
            user_roles = user.role.split('/') if '/' in user.role else [user.role]
            if any(role in allowed_roles for role in user_roles):
                allowed_apis.append({
                    "api_path": config['api_path'],
                    "api_name": config['api_name'],
                    "api_group": config['api_group']
                })

        return {"success": True, "data": allowed_apis}


@router.get("/check", summary="检查用户对特定API的权限")
async def check_api_permission_endpoint(
    api_path: str = Query(..., description="API路径"),
    user: User = Depends(get_current_user)
):
    """检查用户对特定API的权限"""
    with get_moral_db() as db:
        config = db.query_one(
            "SELECT allowed_roles, min_level FROM api_permission_config WHERE api_path = %s AND is_active = 1",
            (api_path,)
        )

        # 无配置则默认允许（依赖原有装饰器）
        if not config:
            return {"success": True, "data": {"has_permission": True, "reason": "无权限配置，默认允许"}}

        try:
            allowed_roles = json.loads(config.get('allowed_roles', '[]'))
        except:
            allowed_roles = []

        # admin拥有所有权限
        if is_admin_user(user):
            return {"success": True, "data": {"has_permission": True, "reason": "admin拥有所有权限"}}

        # 检查角色（支持多角色格式）
        user_roles = user.role.split('/') if '/' in user.role else [user.role]
        if any(role in allowed_roles for role in user_roles):
            return {"success": True, "data": {"has_permission": True, "reason": f"角色 {user.role} 在允许列表中"}}

        # 检查等级
        min_level = config.get('min_level', 0)
        from .base import get_user_role_level
        user_level = get_user_role_level(user)

        if min_level > 0 and user_level >= min_level:
            return {"success": True, "data": {"has_permission": True, "reason": f"等级 {user_level} >= {min_level}"}}

        return {"success": True, "data": {"has_permission": False, "reason": "无权限"}}


@router.post("/init", summary="初始化默认API权限配置")
async def init_api_permissions(
    request: Request,
    user: User = Depends(require_admin)
):
    """初始化默认API权限配置（仅admin）"""
    with get_moral_db() as db:
        created_count = 0
        skipped_count = 0

        for default_config in DEFAULT_API_PERMISSIONS:
            existing = db.query_one(
                "SELECT id FROM api_permission_config WHERE api_path = %s",
                (default_config['api_path'],)
            )

            if existing:
                skipped_count += 1
                continue

            allowed_roles_json = json.dumps(default_config['allowed_roles'])

            db.execute(
                """INSERT INTO api_permission_config
                (api_path, api_name, api_group, allowed_roles, min_level, description)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    default_config['api_path'],
                    default_config['api_name'],
                    default_config['api_group'],
                    allowed_roles_json,
                    default_config['min_level'],
                    default_config.get('description', '')
                )
            )
            created_count += 1

        log_operation(
            db, user.username, user.role, 'INIT', 'api_permission_config', None,
            new_data={"created": created_count, "skipped": skipped_count}
        )

        return {
            "success": True,
            "message": f"初始化完成：创建 {created_count} 条，跳过 {skipped_count} 条已存在配置"
        }


@router.get("/groups", summary="获取API分组列表")
async def get_api_groups(user: User = Depends(get_current_user)):
    """获取API分组列表"""
    with get_moral_db() as db:
        groups = db.query_all(
            "SELECT DISTINCT api_group FROM api_permission_config ORDER BY api_group"
        )
        return {"success": True, "data": [g['api_group'] for g in groups]}