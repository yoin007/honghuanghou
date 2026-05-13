# -*- coding: utf-8 -*-
"""
德育评价系统基础模块

提供：
- 数据库连接管理（SQLite）
- 权限检查函数
- 通用工具函数
"""

import logging
import json
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime, date

from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel

from utils.sqlite_moral_db import MoralDatabase as SQLiteMoralDatabase
from models.datas_api.auth import User, get_current_user, get_current_user_optional, is_admin_user

logger = logging.getLogger(__name__)

# =============================================================================
# 权限配置
# =============================================================================

# 德育系统权限定义
MORAL_PERMISSIONS = {
    'admin': {
        'name': '管理员',
        'level': 100,
        'permissions': ['all']
    },
    'jiaowu': {
        'name': '教发部',
        'level': 60,
        'permissions': [
            'moral_record_manage',
            'moral_record_input',     # 可以录入记录
            'moral_record_own_class',
            'student_manage',         # 学生管理
            'student_manage_all',     # 全量学生管理（不限班级）
            'teacher_manage',
            'class_manage',
            'report_view_all',
            'grade_manage',
            'semester_manage',
            'birthday_reminder',
            'student_profile',
            'moment_view_all',
            'profile_view_all',
            'collective_event_manage',
        ]
    },
    'xuefa': {
        'name': '学发部',
        'level': 50,
        'permissions': [
            'moral_record_manage',
            'moral_record_input',     # 可以录入记录
            'moral_record_own_class',
            'punishment_manage',
            'event_type_manage',
            'class_change_approve',
            'report_view_all',
            'student_manage',         # 学生管理
            'student_manage_all',     # 全量学生管理（不限班级）
            'ai_consultation',
            'birthday_reminder',
            'student_profile',
            'moment_view_all',
            'profile_view_all',
            'collective_event_manage',
            'semester_manage',        # 学期结转管理
        ]
    },
    'g_leader': {
        'name': '年级主任',
        'level': 30,
        'permissions': [
            'moral_record_input',           # 可以录入记录
            'moral_record_own_grade',       # 本年级德育记录管理
            'moral_record_view_own_grade',  # 查看本年级记录
            'report_view_own_grade',        # 本年级报告查看
            'student_manage_own_grade',     # 本年级学生管理
            'homework_publish',
            'announcement_publish',
            'leave_approve_own_grade',      # 本年级请假审批
            'ai_consultation_own_grade',    # 本年级AI诊疗
            'student_profile_own_grade',    # 本年级学生画像
            'birthday_reminder_own_grade',  # 本年级生日提醒
            'moment_create',
            'moment_view_own_grade',        # 本年级点滴记录
            'profile_view_own_grade',       # 本年级画像查看
            'collective_event_manage',      # 集体事件管理
        ]
    },
    'cleader': {
        'name': '班主任',
        'level': 20,
        'permissions': [
            'moral_record_input',      # 可以录入记录
            'moral_record_own_class',  # 本班德育记录/任务管理
            'moral_record_view_own',   # 只能查看自己创建的记录
            'report_view_own_class',
            'student_manage_own_class', # 只能管理本班学生（新增、导入）
            'homework_publish',
            'announcement_publish',
            'leave_approve',
            'ai_consultation_own_class',
            'student_profile_own_class',
            'birthday_reminder_own_class',
            'moment_create',
            'moment_view_own',
            'profile_view_own_class',
            'collective_event_manage',
        ]
    },
    'teacher': {
        'name': '教师',
        'level': 10,
        'permissions': [
            'homework_publish',
            'schedule_view',
            'student_view',
            'moral_record_input',
            'moral_record_view_own',  # 只能查看自己创建的记录
            'moment_create',
            'moment_view_own',
        ]
    },
    'student': {
        'name': '学生',
        'level': 1,
        'permissions': [
            'moral_self_view',
            'homework_view',
            'schedule_view',
            'profile_self_view',
            'birthday_blessing_receive',
        ]
    },
    'parent': {
        'name': '家长',
        'level': 1,
        'permissions': [
            'moral_child_view',
            'profile_child_view',
            'birthday_reminder_child',
        ]
    }
}


# =============================================================================
# 数据库连接
# =============================================================================

@contextmanager
def get_moral_db():
    """
    获取德育数据库连接的上下文管理器（SQLite）

    使用方式:
        with get_moral_db() as db:
            result = db.query_all("SELECT * FROM student")
    """
    with SQLiteMoralDatabase() as db:
        yield db


class MoralDB:
    """德育数据库操作便捷类（SQLite）"""

    def __init__(self):
        self._db = None

    def __enter__(self):
        self._db = SQLiteMoralDatabase()
        self._db.__enter__()
        return self._db

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._db.__exit__(exc_type, exc_val, exc_tb)


# =============================================================================
# 权限检查函数
# =============================================================================

def get_user_role_level(user: User) -> int:
    """
    获取用户角色等级

    优先读取 teacher 表中的实际等级字段，
    如果未配置则回退到角色预设等级。

    Args:
        user: 用户对象

    Returns:
        int: 角色等级
    """
    if not user:
        return 0

    # 优先从 teacher 表获取用户实际等级（支持个性化管控）
    try:
        with get_moral_db() as db:
            teacher_row = db.query_one(
                "SELECT level FROM teacher WHERE name = ? AND is_active = 1",
                (user.username,)
            )
            if teacher_row:
                db_level = teacher_row.get('level')
                if db_level is not None and int(db_level) > 0:
                    return int(db_level)
    except Exception:
        pass  # 查询失败则回退到角色预设等级

    # 回退：使用角色预设等级（多角色取最高）
    role = user.role if hasattr(user, 'role') else 'teacher'
    roles = role.split('/') if '/' in role else [role]
    max_level = 0
    for r in roles:
        role_config = MORAL_PERMISSIONS.get(r, {})
        level = role_config.get('level', 0)
        max_level = max(max_level, level)

    return max_level


def get_user_roles(user: User) -> List[str]:
    """获取用户角色列表，兼容 teacher/xuefa 这类多角色格式。"""
    if not user:
        return []

    role = user.role if hasattr(user, 'role') else ''
    return [r for r in str(role).split('/') if r]


def has_user_role(user: User, role: str) -> bool:
    """检查用户是否包含指定角色。"""
    return role in get_user_roles(user)


def check_moral_permission(user: User, permission: str) -> bool:
    """
    检查用户是否有指定权限

    Args:
        user: 用户对象
        permission: 权限名称

    Returns:
        bool: 是否有权限
    """
    if not user:
        return False

    # admin 拥有所有权限
    if is_admin_user(user):
        return True

    role = user.role if hasattr(user, 'role') else 'teacher'

    # 支持多角色格式：任一角色有权限即可
    roles = role.split('/') if '/' in role else [role]
    for r in roles:
        role_config = MORAL_PERMISSIONS.get(r, {})
        permissions = role_config.get('permissions', [])

        # 'all' 表示拥有所有权限
        if 'all' in permissions:
            return True

        if permission in permissions:
            return True

    return False


def check_moral_permission_for_roles(roles: List[str], permission: str) -> bool:
    """按指定角色集合检查权限，用于多角色用户在某个API下的业务范围收敛。"""
    for role in roles or []:
        role_config = MORAL_PERMISSIONS.get(role, {})
        permissions = role_config.get('permissions', [])
        if 'all' in permissions or permission in permissions:
            return True
    return False


def check_any_moral_permission_for_roles(roles: List[str], permissions: List[str]) -> bool:
    """按指定角色集合检查任一权限。"""
    return any(check_moral_permission_for_roles(roles, permission) for permission in permissions)


def get_api_scoped_user_roles(db: SQLiteMoralDatabase, user: User, api_path: str) -> List[str]:
    """
    获取用户在指定API配置下实际生效的角色。

    多角色用户只保留该API允许的角色，避免“API只允许教师访问，
    但用户同时有教发部身份，于是业务数据范围被提升”的问题。
    """
    user_roles = get_user_roles(user)
    if not user_roles or is_admin_user(user):
        return user_roles

    config = db.query_one(
        """SELECT c.allowed_roles, c.inherit_from_module, c.is_public,
                  m.allowed_roles AS module_allowed_roles
           FROM api_permission_config c
           LEFT JOIN api_permission_module m ON c.module_id = m.id
           WHERE c.api_path = ? AND c.is_active = 1
           LIMIT 1""",
        (api_path,)
    )
    if not config or int(config.get('is_public') or 0) == 1:
        return user_roles

    raw_roles = config.get('module_allowed_roles') if int(config.get('inherit_from_module') or 0) == 1 else config.get('allowed_roles')
    try:
        allowed_roles = json.loads(raw_roles or '[]')
    except Exception:
        allowed_roles = []

    if not allowed_roles:
        return user_roles

    scoped_roles = [role for role in user_roles if role in allowed_roles]
    return scoped_roles


def get_scoped_role_permissions(db: SQLiteMoralDatabase, user: User, api_path: str) -> Dict[str, Any]:
    """返回用户在某个API配置下收敛后的角色和权限判断器。"""
    roles = get_api_scoped_user_roles(db, user, api_path)
    return {
        "roles": roles,
        "has": lambda permission: check_moral_permission_for_roles(roles, permission),
        "has_any": lambda permissions: check_any_moral_permission_for_roles(roles, permissions),
    }


def get_record_data_scope(
    db: SQLiteMoralDatabase,
    user: User,
    api_path: str,
    *,
    all_permissions: List[str],
    own_class_permissions: List[str],
    own_permissions: List[str],
) -> Dict[str, Any]:
    """
    计算记录类数据范围。

    all: 全部记录
    own_class: 当前班主任班级学生的记录
    teaching_classes: 当前教师任教班级学生的记录；未维护任教班级时默认全校
    own: 当前用户自己创建的记录
    """
    scoped = get_scoped_role_permissions(db, user, api_path)
    if is_admin_user(user):
        return {
            "can_all": True,
            "can_own_class": False,
            "can_own": True,
            "my_class_id": None,
            "roles": scoped["roles"],
        }

    configured_scope = _get_configured_data_scope(db, user, api_path, scoped["roles"])
    if configured_scope is not None:
        return configured_scope

    if scoped["has_any"](all_permissions):
        return {
            "can_all": True,
            "can_own_class": False,
            "can_own": True,
            "my_class_id": None,
            "roles": scoped["roles"],
        }

    my_class_id = get_teacher_class_id(user, db)
    my_class_ids = get_teacher_class_ids(user, db)
    teaching_class_ids = get_teacher_teaching_class_ids(user, db)
    can_own_class = bool(my_class_id) and scoped["has_any"](own_class_permissions)
    can_own = scoped["has_any"](own_permissions) or can_own_class

    # 年级主任范围：如果未从配置获取，则回退到角色判断
    can_own_grade = has_user_role(user, 'g_leader') and not (scoped["has_any"](all_permissions) or can_own_class)
    my_grade_class_ids = []
    if can_own_grade:
        my_grade_ids = get_teacher_grade_ids(user, db)
        if my_grade_ids:
            grade_ids_str = ",".join(map(str, my_grade_ids))
            rows = db.query_all(
                f"SELECT class_id FROM class WHERE grade_id IN ({grade_ids_str}) AND is_active = 1"
            )
            my_grade_class_ids = [row["class_id"] for row in rows]

    return {
        "can_all": False,
        "can_own_class": can_own_class,
        "can_own_grade": can_own_grade,
        "my_grade_class_ids": my_grade_class_ids,
        "can_teaching_classes": False,
        "teaching_class_ids": teaching_class_ids,
        "can_own": can_own,
        "my_class_id": my_class_id if can_own_class else None,
        "my_class_ids": my_class_ids if can_own_class else [],
        "roles": scoped["roles"],
    }


def get_user_data_scope_tabs(
    db: SQLiteMoralDatabase,
    user: User,
    module: str,
    *,
    all_permissions: List[str],
    own_class_permissions: List[str],
    own_permissions: List[str],
) -> Dict[str, Any]:
    """
    获取用户在指定模块的数据范围选项卡配置。

    用于前端动态渲染选项卡 UI，返回用户可用的数据范围选项。

    Args:
        db: 数据库连接
        user: 用户对象
        module: 模块名称（如 "moment-records", "daily-records"）
        all_permissions: 全部数据权限列表
        own_class_permissions: 本班数据权限列表
        own_permissions: 自己数据权限列表

    Returns:
        dict: {
            "tabs": [{"key": "own", "label": "我创建的"}, ...],
            "default_tab": "own_class",  # 默认选项卡
        }
    """
    api_path = f"/api/moral/{module}"
    scope = get_record_data_scope(
        db, user, api_path,
        all_permissions=all_permissions,
        own_class_permissions=own_class_permissions,
        own_permissions=own_permissions,
    )

    tabs = []
    if scope.get("can_own"):
        tabs.append({"key": "own", "label": "我创建的"})
    if scope.get("can_own_class"):
        tabs.append({"key": "own_class", "label": "我的班级"})
    if scope.get("can_own_grade"):
        tabs.append({"key": "own_grade", "label": "我的年级"})
    if scope.get("can_all"):
        tabs.append({"key": "all", "label": "全校记录"})

    # 确定默认选项卡：多选项时默认范围最大的
    if len(tabs) == 0:
        default_tab = None
    elif len(tabs) == 1:
        default_tab = tabs[0]["key"]
    else:
        # 范围优先级：all > own_grade > own_class > own
        default_tab = tabs[-1]["key"]

    return {
        "tabs": tabs,
        "default_tab": default_tab,
    }


def _get_configured_data_scope(
    db: SQLiteMoralDatabase,
    user: User,
    api_path: str,
    roles: List[str],
) -> Optional[Dict[str, Any]]:
    """读取 API 权限配置中的角色数据范围规则。"""
    from models.datas_api.moral.api_permission import _get_matching_config

    config = _get_matching_config(db, api_path, "GET")
    if not config:
        # 精确路径回退：兼容尚未走 pattern matching 的旧配置，也便于轻量测试库复用。
        config = db.query_one(
            """
            SELECT data_scope_rules, operation_scope_rules
            FROM api_permission_config
            WHERE api_path = ? AND is_active = 1
            LIMIT 1
            """,
            (api_path,),
        )
    if not config:
        return None

    action_tokens = ("/update", "/delete", "/revoke", "/review", "/close")
    use_operation_rules = any(token in api_path for token in action_tokens)
    raw_rules = config.get("operation_scope_rules") if use_operation_rules else config.get("data_scope_rules")
    if use_operation_rules and not raw_rules:
        raw_rules = config.get("data_scope_rules")
    if not raw_rules:
        return None

    try:
        rules = json.loads(raw_rules) if isinstance(raw_rules, str) else raw_rules
    except Exception:
        return None
    if not isinstance(rules, dict) or not rules:
        return None

    scopes = set()
    for role in roles or []:
        role_scopes = rules.get(role) or []
        if isinstance(role_scopes, list):
            scopes.update(str(scope) for scope in role_scopes)

    can_own_class = "own_class" in scopes or "managed_classes" in scopes
    can_teaching_classes = "teaching_classes" in scopes
    can_own_grade = "g_leader_grade" in scopes or "grade_students" in scopes or "managed_grades" in scopes

    my_grade_ids = get_teacher_grade_ids(user, db) if can_own_grade else []
    my_grade_class_ids = []
    if my_grade_ids:
        grade_ids_str = ",".join(map(str, my_grade_ids))
        rows = db.query_all(
            f"SELECT class_id FROM class WHERE grade_id IN ({grade_ids_str}) AND is_active = 1"
        )
        my_grade_class_ids = [row["class_id"] for row in rows]

    return {
        "can_all": "all" in scopes,
        "can_own_class": can_own_class,
        "my_class_ids": get_teacher_class_ids(user, db) if can_own_class else [],
        "can_own_grade": can_own_grade,
        "my_grade_ids": my_grade_ids,
        "my_grade_class_ids": my_grade_class_ids,
        "can_teaching_classes": can_teaching_classes,
        "teaching_class_ids": get_teacher_teaching_class_ids(user, db) if can_teaching_classes else [],
        "can_own": bool({"own", "own_created", "self"} & scopes),
        "my_class_id": get_teacher_class_id(user, db) if can_own_class else None,
        "roles": roles,
    }


def append_record_scope_condition(
    conditions: List[str],
    params: List[Any],
    scope: Dict[str, Any],
    *,
    table_alias: str,
    recorder_field: str = "recorder",
    class_field: str = "class_id",
    username: str,
) -> None:
    """把记录范围转换为 SQL 条件。"""
    if scope.get("can_all"):
        return

    parts = []
    if scope.get("can_own"):
        parts.append(f"{table_alias}.{recorder_field} = ?")
        params.append(username)
    my_class_ids = scope.get("my_class_ids") or []
    if scope.get("can_own_class") and my_class_ids:
        placeholders = ", ".join(["?"] * len(my_class_ids))
        parts.append(f"{table_alias}.{class_field} IN ({placeholders})")
        params.extend(my_class_ids)
    elif scope.get("can_own_class") and scope.get("my_class_id") is not None:
        parts.append(f"{table_alias}.{class_field} = ?")
        params.append(scope["my_class_id"])

    # 年级范围：通过班级 ID 列表过滤
    my_grade_class_ids = scope.get("my_grade_class_ids") or []
    if scope.get("can_own_grade") and my_grade_class_ids:
        placeholders = ", ".join(["?"] * len(my_grade_class_ids))
        parts.append(f"{table_alias}.{class_field} IN ({placeholders})")
        params.extend(my_grade_class_ids)

    teaching_class_ids = scope.get("teaching_class_ids") or []
    if scope.get("can_teaching_classes"):
        if teaching_class_ids:
            placeholders = ", ".join(["?"] * len(teaching_class_ids))
            parts.append(f"{table_alias}.{class_field} IN ({placeholders})")
            params.extend(teaching_class_ids)
        else:
            return

    if not parts:
        conditions.append("1 = 0")
    else:
        conditions.append("(" + " OR ".join(parts) + ")")


def record_in_scope(
    record: Dict[str, Any],
    scope: Dict[str, Any],
    *,
    username: str,
    recorder_field: str = "recorder",
    class_field: str = "class_id",
) -> bool:
    """判断单条记录是否在数据范围内。"""
    if scope.get("can_all"):
        return True
    if scope.get("can_own") and record.get(recorder_field) == username:
        return True
    if (
        scope.get("can_own_class")
        and scope.get("my_class_id") is not None
        and record.get(class_field) == scope.get("my_class_id")
    ):
        return True
    my_class_ids = scope.get("my_class_ids") or []
    if scope.get("can_own_class") and my_class_ids:
        return record.get(class_field) in my_class_ids
    # 年级范围：判断记录的班级是否在年级班级列表中
    my_grade_class_ids = scope.get("my_grade_class_ids") or []
    if scope.get("can_own_grade") and my_grade_class_ids:
        return record.get(class_field) in my_grade_class_ids
    if scope.get("can_teaching_classes"):
        teaching_class_ids = scope.get("teaching_class_ids") or []
        return not teaching_class_ids or record.get(class_field) in teaching_class_ids
    return False


def record_action_flags(
    record: Dict[str, Any],
    edit_scope: Dict[str, Any],
    delete_scope: Optional[Dict[str, Any]] = None,
    *,
    username: str,
    recorder_field: str = "recorder",
    class_field: str = "class_id",
) -> Dict[str, bool]:
    """生成前端行级操作能力。"""
    delete_scope = delete_scope or edit_scope
    return {
        "can_edit": record_in_scope(
            record,
            edit_scope,
            username=username,
            recorder_field=recorder_field,
            class_field=class_field,
        ),
        "can_delete": record_in_scope(
            record,
            delete_scope,
            username=username,
            recorder_field=recorder_field,
            class_field=class_field,
        ),
    }


def target_student_in_scope(
    db: SQLiteMoralDatabase,
    user: User,
    api_path: str,
    student: Dict[str, Any],
) -> bool:
    """判断创建/录入接口是否允许选择目标学生。"""
    if is_admin_user(user):
        return True

    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    config = db.query_one(
        """SELECT target_scope_rules
           FROM api_permission_config
           WHERE api_path = ? AND is_active = 1
           LIMIT 1""",
        (api_path,)
    )
    if not config or not config.get("target_scope_rules"):
        return True

    try:
        rules = json.loads(config.get("target_scope_rules"))
    except Exception:
        return True
    if not isinstance(rules, dict) or not rules:
        return True

    scopes = set()
    for role in scoped_roles:
        role_scopes = rules.get(role) or []
        if isinstance(role_scopes, list):
            scopes.update(str(scope) for scope in role_scopes)

    if "all_students" in scopes or "all" in scopes:
        return True

    # 多角色场景：任一条件匹配即允许
    # 年级主任：检查年级范围
    if "g_leader_grade" in scopes or "grade_students" in scopes or "managed_grades" in scopes:
        student_grade_id = student.get("grade_id")
        my_grade_ids = get_teacher_grade_ids(user, db)
        if student_grade_id in my_grade_ids:
            return True

    # 班主任：检查班级范围
    if "own_class" in scopes or "managed_classes" in scopes:
        my_class_ids = get_teacher_class_ids(user, db)
        if my_class_ids and student.get("class_id") in my_class_ids:
            return True

    # 教师：检查任教班级范围
    if "teaching_classes" in scopes:
        teaching_class_ids = get_teacher_teaching_class_ids(user, db)
        if not teaching_class_ids:
            return True
        if teaching_class_ids and student.get("class_id") in teaching_class_ids:
            return True

    return False


def check_class_access(user: User, class_id: int, db: SQLiteMoralDatabase) -> bool:
    """
    检查用户是否有班级访问权限

    Args:
        user: 用户对象
        class_id: 班级ID
        db: 数据库连接

    Returns:
        bool: 是否有权限
    """
    if not user:
        return False

    # admin 和 xuefa/jiaowu 可以访问所有班级
    if check_moral_permission(user, 'report_view_all'):
        return True

    # 班主任只能访问自己的班级
    if check_moral_permission(user, 'report_view_own_class'):
        class_info = db.query_one(
            "SELECT leader_wxid, leader_name FROM class WHERE class_id = ?",
            (class_id,)
        )
        if class_info:
            username = user.username if hasattr(user, 'username') else ''
            leader_name = class_info.get('leader_name', '')

            # 方式1：直接匹配（leader_name 存的是 teacher_id）
            if leader_name == username:
                return True

            # 方式2：通过 teacher 表关联（username 是 teacher_id，leader_name 是姓名）
            # 获取当前登录教师的姓名，与 leader_name 比较
            teacher = db.query_one(
                "SELECT name FROM teacher WHERE teacher_id = ?",
                (username,)
            )
            if teacher and teacher.get('name') == leader_name:
                return True

            # 方式3：通过 leader_wxid 匹配（如果已配置）
            leader_wxid = class_info.get('leader_wxid', '')
            if leader_wxid and leader_wxid == username:
                return True

    return False


def get_teacher_class_id(user: User, db: SQLiteMoralDatabase) -> Optional[int]:
    """获取班主任管理的班级ID（向后兼容，返回第一个）。

    改进：支持多人班主任，返回用户作为班主任的第一个班级ID。
    若需要获取所有班主任班级，请使用 get_teacher_class_ids。

    Args:
        user: 用户对象
        db: 数据库连接

    Returns:
        班级ID，如果不是班主任或未关联班级则返回 None
    """
    class_ids = get_teacher_class_ids(user, db)
    return class_ids[0] if class_ids else None


def get_class_leader_ids(class_id: int, db: SQLiteMoralDatabase) -> List[str]:
    """获取班级所有班主任ID列表（支持多人）。

    Args:
        class_id: 班级ID
        db: 数据库连接

    Returns:
        班主任ID列表（如 ['T_张三', 'T_李四']），无班主任时返回空列表
    """
    if not class_id:
        return []

    class_info = db.query_one(
        "SELECT leader_ids, leader_wxid FROM class WHERE class_id = ?",
        (class_id,)
    )
    if not class_info:
        return []

    # 优先使用新的 leader_ids 字段（多人支持）
    leader_ids_str = class_info.get('leader_ids', '')
    if leader_ids_str:
        return [lid.strip() for lid in leader_ids_str.split(',') if lid.strip()]

    # 回退兼容：单值 leader_wxid
    leader_wxid = class_info.get('leader_wxid', '')
    if leader_wxid:
        return [leader_wxid]

    return []


def get_class_leader_names(class_id: int, db: SQLiteMoralDatabase) -> List[str]:
    """获取班级所有班主任姓名列表（支持多人）。

    Args:
        class_id: 班级ID
        db: 数据库连接

    Returns:
        班主任姓名列表（如 ['张三', '李四']），无班主任时返回空列表
    """
    if not class_id:
        return []

    class_info = db.query_one(
        "SELECT leader_names, leader_name FROM class WHERE class_id = ?",
        (class_id,)
    )
    if not class_info:
        return []

    # 优先使用新的 leader_names 字段（多人支持）
    leader_names_str = class_info.get('leader_names', '')
    if leader_names_str:
        return [name.strip() for name in leader_names_str.split(',') if name.strip()]

    # 回退兼容：单值 leader_name
    leader_name = class_info.get('leader_name', '')
    if leader_name:
        return [leader_name]

    return []


def is_class_leader(user: User, class_id: int, db: SQLiteMoralDatabase) -> bool:
    """检查用户是否是某班级的班主任（支持多人）。

    Args:
        user: 用户对象
        class_id: 班级ID
        db: 数据库连接

    Returns:
        是否是该班级的班主任
    """
    if not user or not class_id:
        return False

    username = user.username if hasattr(user, 'username') else ''

    # 兼容两种格式：'xxx' 和 'T_xxx'
    user_candidates = [username]
    if not username.startswith('T_'):
        user_candidates.append(f'T_{username}')

    # 获取班级所有班主任ID
    leader_ids = get_class_leader_ids(class_id, db)
    for leader_id in leader_ids:
        if leader_id in user_candidates:
            return True

    # 也检查班主任姓名匹配（用于 teacher.name）
    leader_names = get_class_leader_names(class_id, db)
    teacher_names = []
    for tid in user_candidates:
        teacher = db.query_one(
            "SELECT name FROM teacher WHERE teacher_id = ?",
            (tid,)
        )
        if teacher and teacher.get('name'):
            teacher_names.append(teacher.get('name'))

    for leader_name in leader_names:
        if leader_name in teacher_names:
            return True

    return False


def get_teacher_class_ids(user: User, db: SQLiteMoralDatabase) -> List[int]:
    """获取用户作为班主任的所有班级ID（支持多人班主任）。

    Args:
        user: 用户对象
        db: 数据库连接

    Returns:
        班级ID列表（用户可能是多个班级的班主任）
    """
    if not user:
        return []

    username = user.username if hasattr(user, 'username') else ''

    # 兼容两种格式
    user_candidates = [username]
    if not username.startswith('T_'):
        user_candidates.append(f'T_{username}')

    # 获取教师姓名用于匹配
    teacher_names = []
    for tid in user_candidates:
        teacher = db.query_one(
            "SELECT name FROM teacher WHERE teacher_id = ?",
            (tid,)
        )
        if teacher and teacher.get('name'):
            teacher_names.append(teacher.get('name'))

    class_ids = set()

    # 方式1：通过 leader_ids 字段匹配（多人支持）
    for uid in user_candidates:
        rows = db.query_all(
            "SELECT class_id FROM class WHERE leader_ids LIKE ? AND is_active = 1",
            (f'%{uid}%',)
        )
        for row in rows:
            # 精确匹配：确认 uid 确实在列表中
            leader_ids_str = row.get('leader_ids', '')
            leader_ids = [lid.strip() for lid in leader_ids_str.split(',') if lid.strip()]
            if uid in leader_ids:
                class_ids.add(row['class_id'])

    # 方式2：通过 leader_names 字段匹配（多人支持）
    for name in teacher_names:
        rows = db.query_all(
            "SELECT class_id FROM class WHERE leader_names LIKE ? AND is_active = 1",
            (f'%{name}%',)
        )
        for row in rows:
            leader_names_str = row.get('leader_names', '')
            leader_names = [n.strip() for n in leader_names_str.split(',') if n.strip()]
            if name in leader_names:
                class_ids.add(row['class_id'])

    # 方式3：回退兼容单值字段
    for uid in user_candidates:
        my_class = db.query_one(
            "SELECT class_id FROM class WHERE leader_wxid = ? AND is_active = 1",
            (uid,)
        )
        if my_class:
            class_ids.add(my_class['class_id'])

    for name in teacher_names:
        my_class = db.query_one(
            "SELECT class_id FROM class WHERE leader_name = ? AND is_active = 1",
            (name,)
        )
        if my_class:
            class_ids.add(my_class['class_id'])

    return list(class_ids)


def get_grade_leader_ids(grade_id: int, db: SQLiteMoralDatabase) -> List[str]:
    """获取年级所有年级主任ID列表（支持多人）。

    Args:
        grade_id: 年级ID
        db: 数据库连接

    Returns:
        年级主任ID列表（如 ['T_张三', 'T_李四']），无年级主任时返回空列表
    """
    if not grade_id:
        return []

    grade_info = db.query_one(
        "SELECT leader_ids FROM grade WHERE grade_id = ?",
        (grade_id,)
    )
    if not grade_info:
        return []

    leader_ids_str = grade_info.get('leader_ids', '')
    if leader_ids_str:
        return [lid.strip() for lid in leader_ids_str.split(',') if lid.strip()]

    return []


def get_grade_leader_names(grade_id: int, db: SQLiteMoralDatabase) -> List[str]:
    """获取年级所有年级主任姓名列表（支持多人）。

    Args:
        grade_id: 年级ID
        db: 数据库连接

    Returns:
        年级主任姓名列表（如 ['张三', '李四']），无年级主任时返回空列表
    """
    if not grade_id:
        return []

    grade_info = db.query_one(
        "SELECT leader_names FROM grade WHERE grade_id = ?",
        (grade_id,)
    )
    if not grade_info:
        return []

    leader_names_str = grade_info.get('leader_names', '')
    if leader_names_str:
        return [name.strip() for name in leader_names_str.split(',') if name.strip()]

    return []


def is_grade_leader(user: User, grade_id: int, db: SQLiteMoralDatabase) -> bool:
    """检查用户是否是某年级的年级主任（支持多人）。

    Args:
        user: 用户对象
        grade_id: 年级ID
        db: 数据库连接

    Returns:
        是否是该年级的年级主任
    """
    if not user or not grade_id:
        return False

    username = user.username if hasattr(user, 'username') else ''

    user_candidates = [username]
    if not username.startswith('T_'):
        user_candidates.append(f'T_{username}')

    # 获取年级所有年级主任ID
    leader_ids = get_grade_leader_ids(grade_id, db)
    for leader_id in leader_ids:
        if leader_id in user_candidates:
            return True

    # 也检查年级主任姓名匹配
    leader_names = get_grade_leader_names(grade_id, db)
    teacher_names = []
    for tid in user_candidates:
        teacher = db.query_one(
            "SELECT name FROM teacher WHERE teacher_id = ?",
            (tid,)
        )
        if teacher and teacher.get('name'):
            teacher_names.append(teacher.get('name'))

    for leader_name in leader_names:
        if leader_name in teacher_names:
            return True

    return False


def get_teacher_grade_ids(user: User, db: SQLiteMoralDatabase) -> List[int]:
    """获取年级主任管理的年级ID列表。

    改进：支持多人年级主任，通过 grade.leader_ids/leader_names 匹配。
    无匹配时回退到任教班级推断。

    Args:
        user: 用户对象
        db: 数据库连接

    Returns:
        年级ID列表
    """
    if not user:
        return []

    username = user.username if hasattr(user, 'username') else ''

    user_candidates = [username]
    if not username.startswith('T_'):
        user_candidates.append(f'T_{username}')

    # 获取教师姓名
    teacher_names = []
    for tid in user_candidates:
        teacher = db.query_one(
            "SELECT name FROM teacher WHERE teacher_id = ?",
            (tid,)
        )
        if teacher and teacher.get('name'):
            teacher_names.append(teacher.get('name'))

    grade_ids = set()

    # 方式1：通过 grade.leader_ids 字段匹配（多人支持）
    for uid in user_candidates:
        rows = db.query_all(
            "SELECT grade_id FROM grade WHERE leader_ids LIKE ?",
            (f'%{uid}%',)
        )
        for row in rows:
            leader_ids_str = row.get('leader_ids', '')
            leader_ids = [lid.strip() for lid in leader_ids_str.split(',') if lid.strip()]
            if uid in leader_ids:
                grade_ids.add(row['grade_id'])

    # 方式2：通过 grade.leader_names 字段匹配（多人支持）
    for name in teacher_names:
        rows = db.query_all(
            "SELECT grade_id FROM grade WHERE leader_names LIKE ?",
            (f'%{name}%',)
        )
        for row in rows:
            leader_names_str = row.get('leader_names', '')
            leader_names = [n.strip() for n in leader_names_str.split(',') if n.strip()]
            if name in leader_names:
                grade_ids.add(row['grade_id'])

    # 方式3：回退到任教班级推断
    if not grade_ids:
        teaching_class_ids = get_teacher_teaching_class_ids(user, db)
        if teaching_class_ids:
            class_ids_str = ','.join(map(str, teaching_class_ids))
            rows = db.query_all(
                f"SELECT DISTINCT grade_id FROM class WHERE class_id IN ({class_ids_str}) AND is_active = 1"
            )
            for row in rows:
                if row.get('grade_id'):
                    grade_ids.add(row['grade_id'])

    return list(grade_ids)


def get_teacher_teaching_class_ids(user: User, db: SQLiteMoralDatabase) -> List[int]:
    """获取教师任教班级ID列表。

    依赖 teacher_teaching_class 映射表。没有维护映射时返回空列表；
    teaching_classes 范围会把空列表解释为禁止所有（需显式配置）。

    支持两种 teacher_id 格式匹配：
    - 直接匹配（如 'T_李婷婷'）
    - 加 T_ 前缀匹配（如 username='李婷婷' → 'T_李婷婷'）
    """
    if not user:
        return []

    try:
        table_exists = db.query_one(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'teacher_teaching_class'"
        )
    except Exception:
        table_exists = None
    if not table_exists:
        return []

    username = user.username if hasattr(user, 'username') else ''

    # 兼容两种 teacher_id 格式：'xxx' 和 'T_xxx'
    teacher_id_candidates = [username]
    if not username.startswith('T_'):
        teacher_id_candidates.append(f'T_{username}')

    # 查询 teacher 表获取教师姓名
    teacher_names = []
    for tid in teacher_id_candidates:
        teacher = db.query_one(
            "SELECT name FROM teacher WHERE teacher_id = ?",
            (tid,)
        )
        if teacher and teacher.get('name'):
            teacher_names.append(teacher.get('name'))

    # 构建查询条件
    conditions = ["is_active = 1"]
    teacher_id_match = " OR ".join([f"teacher_id = ?" for _ in teacher_id_candidates])
    conditions.append(f"({teacher_id_match})")
    params = teacher_id_candidates

    if teacher_names:
        teacher_name_match = " OR ".join([f"teacher_name = ?" for _ in teacher_names])
        conditions[-1] = conditions[-1][:-1] + f" OR {teacher_name_match})"
        params.extend(teacher_names)

    rows = db.query_all(
        f"SELECT DISTINCT class_id FROM teacher_teaching_class WHERE {' AND '.join(conditions)}",
        tuple(params)
    )
    return [int(row["class_id"]) for row in rows if row.get("class_id") is not None]


def require_permission(permission: str):
    """
    权限检查装饰器工厂函数

    Args:
        permission: 需要的权限名称

    Returns:
        依赖函数
    """
    async def check(request: Request, user: User = Depends(get_current_user)):
        try:
            from .api_permission import check_configured_api_permission
            decision = check_configured_api_permission(
                user,
                request.url.path,
                request.method,
                allow_missing=True,
            )
            if not decision.get("allowed"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=decision.get("reason") or "API权限不足",
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("API配置鉴权失败，回退到静态权限检查: %s", exc)

        if not check_moral_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：需要 {permission} 权限"
            )
        return user
    return check


def require_role_level(min_level: int):
    """
    角色等级检查装饰器工厂函数

    Args:
        min_level: 最低角色等级

    Returns:
        依赖函数
    """
    async def check(user: User = Depends(get_current_user)):
        user_level = get_user_role_level(user)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足：需要角色等级 {min_level} 以上"
            )
        return user
    return check


# =============================================================================
# 学年学期工具函数
# =============================================================================

def get_current_school_year(db: SQLiteMoralDatabase) -> Optional[Dict[str, Any]]:
    """
    获取当前学年

    Args:
        db: 数据库连接

    Returns:
        当前学年信息，包含 year_id, year_name 等
    """
    return db.query_one(
        "SELECT * FROM school_year WHERE is_current = 1 LIMIT 1"
    )


def get_next_school_year(db: SQLiteMoralDatabase, current_year_id: int) -> Optional[Dict[str, Any]]:
    """
    获取下一个学年

    Args:
        db: 数据库连接
        current_year_id: 当前学年ID

    Returns:
        下一个学年信息，如果不存在则返回None
    """
    return db.query_one(
        "SELECT * FROM school_year WHERE year_id = ? LIMIT 1",
        (current_year_id + 1,)
    )


def get_current_semester(db: SQLiteMoralDatabase) -> Optional[Dict[str, Any]]:
    """
    获取当前学期

    Args:
        db: 数据库连接

    Returns:
        当前学期信息，包含 semester_id, semester_name 等
    """
    return db.query_one(
        "SELECT * FROM semester WHERE status = 1 LIMIT 1"
    )


def get_or_create_current_semester(db: SQLiteMoralDatabase) -> Dict[str, Any]:
    """
    获取或创建当前学期

    如果不存在当前学期，自动创建

    Args:
        db: 数据库连接

    Returns:
        当前学期信息
    """
    semester = get_current_semester(db)
    if semester:
        return semester

    # 创建当前学年
    current_year = datetime.now().year
    year_name = f"{current_year}-{current_year + 1}学年"

    year = db.query_one(
        "SELECT * FROM school_year WHERE year_name = ?",
        (year_name,)
    )

    if not year:
        db.execute(
            """INSERT INTO school_year (year_name, start_date, end_date, is_current)
            VALUES (?, ?, ?, 1)""",
            (year_name, date(current_year, 9, 1), date(current_year + 1, 7, 15))
        )
        year = db.query_one(
            "SELECT * FROM school_year WHERE year_name = ?",
            (year_name,)
        )

    year_id = year['year_id']

    # 创建当前学期
    semester_name = f"{current_year}-{current_year + 1}上"
    db.execute(
        """INSERT INTO semester (semester_name, year_id, start_date, end_date, status)
        VALUES (?, ?, ?, ?, 1)""",
        (semester_name, year_id, date(current_year, 9, 1), date(current_year + 1, 1, 20))
    )

    return get_current_semester(db)


# =============================================================================
# Pydantic 模型
# =============================================================================

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = True
    message: str = "操作成功"


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: List[Dict[str, Any]] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


# =============================================================================
# 工具函数
# =============================================================================

def calculate_moral_level(score: float) -> str:
    """
    根据分数计算德育等级

    Args:
        score: 德育总分

    Returns:
        等级：优秀/良好/合格/不合格
    """
    if score >= 90:
        return "优秀"
    elif score >= 75:
        return "良好"
    elif score >= 60:
        return "合格"
    else:
        return "不合格"


def get_student_class_snapshot(db: SQLiteMoralDatabase, student_id: str) -> Optional[Dict[str, Any]]:
    """
    获取学生当前班级信息快照

    Args:
        db: 数据库连接
        student_id: 学号

    Returns:
        包含 class_id, grade_id 的字典
    """
    return db.query_one(
        """SELECT class_id, grade_id FROM student
        WHERE student_id = ? AND status = '在校'""",
        (student_id,)
    )


def log_operation(
    db: SQLiteMoralDatabase,
    operator: str,
    operator_role: str,
    operation: str,
    table_name: str,
    record_id: int,
    semester_id: int = None,
    old_data: dict = None,
    new_data: dict = None,
    reason: str = None,
    ip_address: str = None
):
    """
    记录操作日志

    Args:
        db: 数据库连接
        operator: 操作人
        operator_role: 操作人角色
        operation: 操作类型
        table_name: 表名
        record_id: 记录ID
        semester_id: 学期ID
        old_data: 旧数据
        new_data: 新数据
        reason: 原因
        ip_address: IP地址
    """
    import json

    try:
        db.execute(
            """INSERT INTO moral_operation_log
            (operator, operator_role, operation, table_name, record_id, semester_id, old_data, new_data, reason, ip_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                operator,
                operator_role,
                operation,
                table_name,
                record_id,
                semester_id,
                json.dumps(old_data, ensure_ascii=False) if old_data else None,
                json.dumps(new_data, ensure_ascii=False) if new_data else None,
                reason,
                ip_address
            )
        )
    except Exception as e:
        logger.error(f"Failed to log operation: {e}")


__all__ = [
    'MORAL_PERMISSIONS',
    'get_moral_db',
    'MoralDB',
    'get_user_role_level',
    'get_user_roles',
    'has_user_role',
    'check_moral_permission',
    'check_moral_permission_for_roles',
    'check_any_moral_permission_for_roles',
    'get_api_scoped_user_roles',
    'get_scoped_role_permissions',
    'get_record_data_scope',
    'get_teacher_teaching_class_ids',
    'append_record_scope_condition',
    'record_in_scope',
    'record_action_flags',
    'target_student_in_scope',
    'check_class_access',
    'require_permission',
    'require_role_level',
    'get_current_school_year',
    'get_current_semester',
    'get_or_create_current_semester',
    'calculate_moral_level',
    'get_student_class_snapshot',
    'log_operation',
    'BaseResponse',
    'PaginationParams',
    'PaginatedResponse',
]
