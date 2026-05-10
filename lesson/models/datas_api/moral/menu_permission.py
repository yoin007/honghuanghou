# -*- coding: utf-8 -*-
"""
菜单权限配置 API

提供导航栏菜单的动态权限配置管理
仅限管理员访问
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from models.datas_api.auth import User, get_current_user
from models.datas_api.moral.base import log_operation, get_moral_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/menu-permission", tags=["菜单权限配置"])

# 所有可用角色
ALL_ROLES = ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"]

# 所有菜单分组
MENU_GROUPS = ["public", "teacher", "jiaowu", "moral", "dashboard", "system"]

# 静态默认配置（用于初始化）
DEFAULT_MENU_CONFIG = [
    # 公共菜单
    {"key": "homework", "label": "班级作业", "route": "/homework", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 10},
    {"key": "basic-info", "label": "班级信息", "route": "/basic-info", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 20},
    {"key": "class-students", "label": "班级学生", "route": "/class-students", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 30},
    {"key": "announcement", "label": "班级公告", "route": "/announcement", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 40},
    {"key": "delay-application", "label": "延时申请", "route": "/delay-application", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 50},
    {"key": "leave-record", "label": "请假记录", "route": "/leave-record", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 60},
    {"key": "schedule", "label": "课程表", "route": "/schedule", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 70},
    {"key": "schedules", "label": "总课表", "route": "/schedules", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 80},
    {"key": "random-call", "label": "随机点名", "route": "/random-call", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 90},
    {"key": "loud-pk", "label": "大声PK", "route": "/loud-pk", "group": "public", "roles": ["all"], "is_public": 1, "sort_order": 100},
    # 教师菜单
    {"key": "publish-homework", "label": "发布作业", "route": "/publish-homework", "group": "teacher", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 10},
    {"key": "publish-announcement", "label": "发布公告", "route": "/publish-announcement", "group": "teacher", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 20},
    {"key": "file-upload", "label": "文件上传", "route": "/file-upload", "group": "teacher", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 30},
    {"key": "my-files", "label": "我的文件", "route": "/my-files", "group": "teacher", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 40},
    # 教务菜单
    {"key": "admin-files", "label": "文件管理", "route": "/admin-files", "group": "jiaowu", "roles": ["jiaowu", "admin"], "is_public": 0, "sort_order": 10},
    {"key": "admin-files-done", "label": "已查阅文件", "route": "/admin-files-done", "group": "jiaowu", "roles": ["jiaowu", "admin"], "is_public": 0, "sort_order": 20},
    {"key": "upload-schedule", "label": "更新课表", "route": "/upload-schedule", "group": "jiaowu", "roles": ["jiaowu", "admin"], "is_public": 0, "sort_order": 30},
    {"key": "invigilation", "label": "监考安排", "route": "/invigilation", "group": "jiaowu", "roles": ["jiaowu", "admin"], "is_public": 0, "sort_order": 40},
    # 德育菜单
    {"key": "moral-daily", "label": "日常表现", "route": "/moral/daily-record", "group": "moral", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 10},
    {"key": "moral-school", "label": "校级事件", "route": "/moral/school-event", "group": "moral", "roles": ["cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 20},
    {"key": "moral-task", "label": "德育任务", "route": "/moral/task", "group": "moral", "roles": ["cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 30},
    {"key": "moral-punishment", "label": "处分管理", "route": "/moral/punishment", "group": "moral", "roles": ["xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 40},
    {"key": "moral-collective", "label": "集体事件", "route": "/moral/collective", "group": "moral", "roles": ["cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 50},
    {"key": "moral-evaluation", "label": "评价查询", "route": "/moral/evaluation", "group": "moral", "roles": ["cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 60},
    {"key": "moral-moment", "label": "点滴记录", "route": "/moral/moment", "group": "moral", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 70},
    {"key": "moral-lifebook", "label": "一生一册", "route": "/moral/lifebook", "group": "moral", "roles": ["cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 80},
    {"key": "moral-profile", "label": "学生画像", "route": "/moral/profile", "group": "moral", "roles": ["cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 90},
    {"key": "moral-birthday", "label": "生日提醒", "route": "/moral/birthday", "group": "moral", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 100},
    {"key": "moral-student-manage", "label": "学生管理", "route": "/moral/config/student", "group": "moral", "roles": ["g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 110},
    {"key": "moral-config", "label": "德育配置", "route": "/moral/config", "group": "moral", "roles": ["xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 120},
    # 驾驶舱菜单
    {"key": "dashboard-overview", "label": "总览", "route": "/dashboard", "group": "dashboard", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 10},
    {"key": "dashboard-moral", "label": "德育驾驶舱", "route": "/dashboard/moral", "group": "dashboard", "roles": ["cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 20},
    {"key": "dashboard-teaching", "label": "教务驾驶舱", "route": "/dashboard/teaching", "group": "dashboard", "roles": ["jiaowu", "admin"], "is_public": 0, "sort_order": 30},
    {"key": "dashboard-class", "label": "班级驾驶舱", "route": "/dashboard/class", "group": "dashboard", "roles": ["cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 40},
    {"key": "dashboard-grade", "label": "年级驾驶舱", "route": "/dashboard/grade", "group": "dashboard", "roles": ["g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 50},
    {"key": "dashboard-teacher", "label": "教师工作台", "route": "/dashboard/teacher", "group": "dashboard", "roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"], "is_public": 0, "sort_order": 60},
    {"key": "dashboard-invigilation", "label": "监考驾驶舱", "route": "/dashboard/invigilation", "group": "dashboard", "roles": ["jiaowu", "admin"], "is_public": 0, "sort_order": 70},
    {"key": "dashboard-system", "label": "系统运维", "route": "/dashboard/system", "group": "dashboard", "roles": ["admin"], "is_public": 0, "sort_order": 80},
    # 系统管理菜单
    {"key": "member-manage", "label": "会员管理", "route": "/member-manage", "group": "system", "roles": ["admin"], "is_public": 0, "sort_order": 10},
    {"key": "permission-manage", "label": "权限管理", "route": "/permission-manage", "group": "system", "roles": ["admin"], "is_public": 0, "sort_order": 20},
    {"key": "task-manage", "label": "任务管理", "route": "/task-manage", "group": "system", "roles": ["admin"], "is_public": 0, "sort_order": 30},
    {"key": "system-monitor", "label": "系统监控", "route": "/system-monitor", "group": "system", "roles": ["admin"], "is_public": 0, "sort_order": 40},
    {"key": "teacher-manage", "label": "教师管理", "route": "/teacher-manage", "group": "system", "roles": ["admin"], "is_public": 0, "sort_order": 50},
    {"key": "moral-api-permission", "label": "API权限", "route": "/moral/config/api-permission", "group": "system", "roles": ["admin"], "is_public": 0, "sort_order": 60},
    {"key": "moral-database", "label": "数据库管理", "route": "/moral/config/database", "group": "system", "roles": ["admin"], "is_public": 0, "sort_order": 70},
    {"key": "moral-menu-permission", "label": "菜单权限", "route": "/moral/config/menu-permission", "group": "system", "roles": ["admin"], "is_public": 0, "sort_order": 80},
]


# ==================== Pydantic 模型 ====================

class MenuConfigItem(BaseModel):
    """菜单配置项"""
    menu_key: str = Field(..., description="菜单唯一标识")
    menu_label: str = Field(..., description="显示名称")
    menu_route: str = Field(..., description="路由路径")
    menu_group: str = Field(..., description="所属分组")
    allowed_roles: List[str] = Field(..., description="允许访问的角色列表")
    is_public: bool = Field(False, description="是否公开（无需登录）")
    requires_auth: bool = Field(True, description="是否需要登录")
    sort_order: int = Field(0, description="排序权重")
    is_active: bool = Field(True, description="是否启用")
    description: Optional[str] = Field(None, description="描述说明")


class BatchUpdateRequest(BaseModel):
    """批量更新请求"""
    menu_keys: List[str] = Field(..., description="要更新的菜单key列表")
    allowed_roles: List[str] = Field(..., description="新的角色列表")


class BatchUpdateByGroupRequest(BaseModel):
    """按分组批量更新请求"""
    menu_group: str = Field(..., description="菜单分组")
    allowed_roles: List[str] = Field(..., description="新的角色列表")


# ==================== 工具函数 ====================

def is_admin_user(user: User) -> bool:
    """检查是否是管理员"""
    return user.role in ["admin", "jiaowu"]


def ensure_menu_table_exists(db):
    """确保菜单权限表存在"""
    db.execute("""
        CREATE TABLE IF NOT EXISTS menu_permission_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            menu_key TEXT NOT NULL UNIQUE,
            menu_label TEXT NOT NULL,
            menu_route TEXT NOT NULL,
            menu_group TEXT NOT NULL,
            allowed_roles TEXT NOT NULL DEFAULT '[]',
            is_public INTEGER DEFAULT 0,
            requires_auth INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            description TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    # 使用原生连接创建索引（因为 MoralDatabase.execute 返回 int）
    conn = db._connection
    conn.execute("CREATE INDEX IF NOT EXISTS idx_menu_permission_key ON menu_permission_config(menu_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_menu_permission_group ON menu_permission_config(menu_group)")


# ==================== API 路由 ====================

@router.get("/list", summary="获取所有菜单配置")
async def list_menu_config(
    group: Optional[str] = None,
    user: User = Depends(get_current_user)
):
    """获取所有菜单权限配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        if group:
            rows = db.query_all(
                "SELECT * FROM menu_permission_config WHERE menu_group = ? ORDER BY sort_order, menu_key",
                (group,)
            )
        else:
            rows = db.query_all(
                "SELECT * FROM menu_permission_config ORDER BY menu_group, sort_order, menu_key"
            )

        configs = []
        for row in rows:
            configs.append({
                "id": row["id"],
                "menu_key": row["menu_key"],
                "menu_label": row["menu_label"],
                "menu_route": row["menu_route"],
                "menu_group": row["menu_group"],
                "allowed_roles": json.loads(row["allowed_roles"]) if row["allowed_roles"] else [],
                "is_public": bool(row["is_public"]),
                "requires_auth": bool(row["requires_auth"]),
                "sort_order": row["sort_order"],
                "is_active": bool(row["is_active"]),
                "description": row["description"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })

        return {"success": True, "data": configs}


@router.get("/my-menu", summary="获取当前用户可见的菜单配置")
async def get_my_menu_config(user: User = Depends(get_current_user)):
    """获取当前登录用户可见的菜单配置（无需 admin 权限）"""
    # 从 user.role 解析用户角色
    role_text = str(user.role or '')
    user_roles = role_text.split('/') if role_text else []

    # 默认所有教师都有 teacher 角色
    if 'teacher' not in user_roles and 'admin' not in user_roles:
        user_roles.append('teacher')

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        # 查询所有启用的菜单配置
        rows = db.query_all(
            "SELECT * FROM menu_permission_config WHERE is_active = 1 ORDER BY menu_group, sort_order, menu_key"
        )

        configs = []
        for row in rows:
            allowed_roles = json.loads(row["allowed_roles"]) if row["allowed_roles"] else []

            # 判断用户是否可见：
            # 1. is_public = 1 公开菜单，所有人可见
            # 2. allowed_roles 包含用户任一角色
            is_visible = bool(row["is_public"]) or any(r in user_roles for r in allowed_roles)

            if is_visible:
                configs.append({
                    "menu_key": row["menu_key"],
                    "menu_label": row["menu_label"],
                    "menu_route": row["menu_route"],
                    "menu_group": row["menu_group"],
                    "allowed_roles": allowed_roles,
                    "is_public": bool(row["is_public"]),
                    "sort_order": row["sort_order"],
                    "is_active": bool(row["is_active"])
                })

        return {"success": True, "data": configs}


@router.get("/groups", summary="获取菜单分组列表")
async def get_menu_groups(user: User = Depends(get_current_user)):
    """获取所有菜单分组"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    return {"success": True, "data": MENU_GROUPS}


@router.get("/roles", summary="获取所有角色列表")
async def get_all_roles(user: User = Depends(get_current_user)):
    """获取所有可用角色"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以访问")

    return {"success": True, "data": ALL_ROLES}


@router.post("/create", summary="创建菜单配置")
async def create_menu_config(
    config: MenuConfigItem,
    req: Request,
    user: User = Depends(get_current_user)
):
    """创建新的菜单权限配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行此操作")

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        # 检查是否已存在
        existing = db.query_one(
            "SELECT id FROM menu_permission_config WHERE menu_key = ?",
            (config.menu_key,)
        )
        if existing:
            raise HTTPException(400, f"菜单 {config.menu_key} 已存在")

        db.execute(
            """INSERT INTO menu_permission_config
            (menu_key, menu_label, menu_route, menu_group, allowed_roles, is_public,
             requires_auth, sort_order, is_active, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                config.menu_key,
                config.menu_label,
                config.menu_route,
                config.menu_group,
                json.dumps(config.allowed_roles),
                int(config.is_public),
                int(config.requires_auth),
                config.sort_order,
                int(config.is_active),
                config.description
            )
        )

        # 记录操作日志
        log_operation(
            db=db,
            operator=user.username,
            operator_role=user.role,
            operation='CREATE',
            table_name='menu_permission_config',
            record_id=0,
            old_data=None,
            new_data=config.dict(),
            ip_address=req.client.host if req.client else None
        )

        logger.info(f"管理员 {user.username} 创建菜单配置 {config.menu_key}")

        return {"success": True, "message": f"菜单 {config.menu_label} 创建成功"}


@router.put("/{menu_key}", summary="更新菜单配置")
async def update_menu_config(
    menu_key: str,
    config: MenuConfigItem,
    req: Request,
    user: User = Depends(get_current_user)
):
    """更新菜单权限配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行此操作")

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        # 获取旧数据
        old_row = db.query_one(
            "SELECT * FROM menu_permission_config WHERE menu_key = ?",
            (menu_key,)
        )
        if not old_row:
            raise HTTPException(404, f"菜单 {menu_key} 不存在")

        old_data = {
            "menu_key": old_row["menu_key"],
            "menu_label": old_row["menu_label"],
            "allowed_roles": json.loads(old_row["allowed_roles"]) if old_row["allowed_roles"] else [],
            "is_public": bool(old_row["is_public"]),
        }

        db.execute(
            """UPDATE menu_permission_config
            SET menu_label = ?, menu_route = ?, menu_group = ?, allowed_roles = ?,
                is_public = ?, requires_auth = ?, sort_order = ?, is_active = ?,
                description = ?, updated_at = datetime('now', 'localtime')
            WHERE menu_key = ?""",
            (
                config.menu_label,
                config.menu_route,
                config.menu_group,
                json.dumps(config.allowed_roles),
                int(config.is_public),
                int(config.requires_auth),
                config.sort_order,
                int(config.is_active),
                config.description,
                menu_key
            )
        )

        # 记录操作日志
        log_operation(
            db=db,
            operator=user.username,
            operator_role=user.role,
            operation='UPDATE',
            table_name='menu_permission_config',
            record_id=old_row["id"],
            old_data=old_data,
            new_data=config.dict(),
            ip_address=req.client.host if req.client else None
        )

        logger.info(f"管理员 {user.username} 更新菜单配置 {menu_key}")

        return {"success": True, "message": f"菜单 {config.menu_label} 更新成功"}


@router.delete("/{menu_key}", summary="删除菜单配置")
async def delete_menu_config(
    menu_key: str,
    req: Request,
    user: User = Depends(get_current_user)
):
    """删除菜单权限配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行此操作")

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        # 获取旧数据
        old_row = db.query_one(
            "SELECT * FROM menu_permission_config WHERE menu_key = ?",
            (menu_key,)
        )
        if not old_row:
            raise HTTPException(404, f"菜单 {menu_key} 不存在")

        old_data = dict(old_row)

        db.execute("DELETE FROM menu_permission_config WHERE menu_key = ?", (menu_key,))

        # 记录操作日志
        log_operation(
            db=db,
            operator=user.username,
            operator_role=user.role,
            operation='DELETE',
            table_name='menu_permission_config',
            record_id=old_row["id"],
            old_data=old_data,
            new_data=None,
            ip_address=req.client.host if req.client else None
        )

        logger.info(f"管理员 {user.username} 删除菜单配置 {menu_key}")

        return {"success": True, "message": f"菜单 {old_row['menu_label']} 删除成功"}


@router.post("/batch", summary="批量更新菜单角色")
async def batch_update_roles(
    request: BatchUpdateRequest,
    req: Request,
    user: User = Depends(get_current_user)
):
    """批量更新多个菜单的角色配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行此操作")

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        updated_count = 0
        for menu_key in request.menu_keys:
            result = db.execute(
                """UPDATE menu_permission_config
                SET allowed_roles = ?, updated_at = datetime('now', 'localtime')
                WHERE menu_key = ?""",
                (json.dumps(request.allowed_roles), menu_key)
            )
            if result > 0:
                updated_count += result

        logger.info(f"管理员 {user.username} 批量更新 {updated_count} 个菜单的角色配置")

        return {
            "success": True,
            "message": f"成功更新 {updated_count} 个菜单",
            "data": {"updated_count": updated_count}
        }


@router.post("/batch-by-group", summary="按分组批量更新菜单角色")
async def batch_update_by_group(
    request: BatchUpdateByGroupRequest,
    req: Request,
    user: User = Depends(get_current_user)
):
    """按分组批量更新菜单的角色配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行此操作")

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        updated_count = db.execute(
            """UPDATE menu_permission_config
            SET allowed_roles = ?, updated_at = datetime('now', 'localtime')
            WHERE menu_group = ?""",
            (json.dumps(request.allowed_roles), request.menu_group)
        )

        logger.info(f"管理员 {user.username} 批量更新分组 {request.menu_group} 的角色配置")

        return {
            "success": True,
            "message": f"成功更新分组 {request.menu_group} 的 {updated_count} 个菜单",
            "data": {"updated_count": updated_count}
        }


@router.post("/init", summary="初始化默认菜单配置")
async def init_default_config(
    req: Request,
    user: User = Depends(get_current_user)
):
    """从静态配置初始化菜单权限配置"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行此操作")

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        # 检查是否已有配置
        existing_count = db.query_value("SELECT COUNT(*) FROM menu_permission_config")
        if existing_count > 0:
            return {"success": True, "message": f"已有 {existing_count} 条配置，无需初始化"}

        # 插入默认配置
        inserted_count = 0
        for item in DEFAULT_MENU_CONFIG:
            roles = item["roles"] if item["roles"] != ["all"] else []
            is_public = 1 if item["roles"] == ["all"] else 0

            db.execute(
                """INSERT INTO menu_permission_config
                (menu_key, menu_label, menu_route, menu_group, allowed_roles, is_public, requires_auth, sort_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    item["key"],
                    item["label"],
                    item["route"],
                    item["group"],
                    json.dumps(roles),
                    is_public,
                    int(not is_public),  # 公开的无需登录
                    item.get("sort_order", 0)
                )
            )
            inserted_count += 1

        # 记录操作日志
        log_operation(
            db=db,
            operator=user.username,
            operator_role=user.role,
            operation='INIT',
            table_name='menu_permission_config',
            record_id=0,
            old_data=None,
            new_data={"count": inserted_count},
            ip_address=req.client.host if req.client else None
        )

        logger.info(f"管理员 {user.username} 初始化菜单配置，插入 {inserted_count} 条")

        return {"success": True, "message": f"成功初始化 {inserted_count} 条菜单配置"}


@router.post("/reset", summary="重置为默认配置")
async def reset_to_default(
    req: Request,
    user: User = Depends(get_current_user)
):
    """重置所有菜单配置为默认值"""
    if not is_admin_user(user):
        raise HTTPException(403, "只有管理员可以执行此操作")

    with get_moral_db() as db:
        ensure_menu_table_exists(db)

        # 清空现有配置
        db.execute("DELETE FROM menu_permission_config")

        # 插入默认配置
        inserted_count = 0
        for item in DEFAULT_MENU_CONFIG:
            roles = item["roles"] if item["roles"] != ["all"] else []
            is_public = 1 if item["roles"] == ["all"] else 0

            db.execute(
                """INSERT INTO menu_permission_config
                (menu_key, menu_label, menu_route, menu_group, allowed_roles, is_public, requires_auth, sort_order, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    item["key"],
                    item["label"],
                    item["route"],
                    item["group"],
                    json.dumps(roles),
                    is_public,
                    int(not is_public),
                    item.get("sort_order", 0)
                )
            )
            inserted_count += 1

        logger.info(f"管理员 {user.username} 重置菜单配置")

        return {"success": True, "message": f"已重置为默认配置，共 {inserted_count} 条"}