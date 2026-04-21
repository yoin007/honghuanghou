# -*- coding: utf-8 -*-
"""
德育评价系统基础模块

提供：
- 数据库连接管理（SQLite）
- 权限检查函数
- 通用工具函数
"""

import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from datetime import datetime, date

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from utils.sqlite_moral_db import MoralDatabase as SQLiteMoralDatabase
from models.datas_api.auth import User, get_current_user, is_admin_user

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
            'student_manage',
            'teacher_manage',
            'class_manage',
            'report_view_all',
            'grade_manage',
            'semester_manage',
            'birthday_reminder',
            'student_profile',
            'moment_view_all',
            'profile_view_all',
        ]
    },
    'xuefa': {
        'name': '学发部',
        'level': 50,
        'permissions': [
            'moral_record_manage',
            'moral_record_input',     # 可以录入记录
            'punishment_manage',
            'event_type_manage',
            'class_change_approve',
            'report_view_all',
            'student_manage',
            'ai_consultation',
            'birthday_reminder',
            'student_profile',
            'moment_view_all',
            'profile_view_all',
        ]
    },
    'cleader': {
        'name': '班主任',
        'level': 30,
        'permissions': [
            'moral_record_input',      # 可以录入记录
            'moral_record_view_own',   # 只能查看自己创建的记录
            'homework_publish',
            'announcement_publish',
            'leave_approve',
            'ai_consultation_own_class',
            'student_profile_own_class',
            'birthday_reminder_own_class',
            'moment_create',
            'moment_view_own',
            'profile_view_own_class',
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

    Args:
        user: 用户对象

    Returns:
        int: 角色等级
    """
    if not user:
        return 0

    role = user.role if hasattr(user, 'role') else 'teacher'
    role_config = MORAL_PERMISSIONS.get(role, {})

    return role_config.get('level', 0)


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
    role_config = MORAL_PERMISSIONS.get(role, {})

    permissions = role_config.get('permissions', [])

    # 'all' 表示拥有所有权限
    if 'all' in permissions:
        return True

    return permission in permissions


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
            "SELECT leader_wxid, leader_name FROM class WHERE class_id = %s",
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
                "SELECT name FROM teacher WHERE teacher_id = %s",
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
    """
    获取班主任管理的班级ID

    Args:
        user: 用户对象
        db: 数据库连接

    Returns:
        班级ID，如果不是班主任或未关联班级则返回 None
    """
    if not user:
        return None

    username = user.username if hasattr(user, 'username') else ''

    # 方式1：通过 teacher 表关联（username 是 teacher_id）
    teacher = db.query_one(
        "SELECT name FROM teacher WHERE teacher_id = %s",
        (username,)
    )
    if teacher:
        teacher_name = teacher.get('name', '')
        # 用教师姓名匹配 class.leader_name
        my_class = db.query_one(
            "SELECT class_id FROM class WHERE leader_name = %s AND is_active = 1",
            (teacher_name,)
        )
        if my_class:
            return my_class['class_id']

    # 方式2：直接用 username 匹配 leader_name（如果 leader_name 存的是 teacher_id）
    my_class = db.query_one(
        "SELECT class_id FROM class WHERE leader_name = %s AND is_active = 1",
        (username,)
    )
    if my_class:
        return my_class['class_id']

    # 方式3：通过 leader_wxid 匹配
    my_class = db.query_one(
        "SELECT class_id FROM class WHERE leader_wxid = %s AND is_active = 1",
        (username,)
    )
    if my_class:
        return my_class['class_id']

    return None


def require_permission(permission: str):
    """
    权限检查装饰器工厂函数

    Args:
        permission: 需要的权限名称

    Returns:
        依赖函数
    """
    async def check(user: User = Depends(get_current_user)):
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
        "SELECT * FROM school_year WHERE year_name = %s",
        (year_name,)
    )

    if not year:
        db.execute(
            """INSERT INTO school_year (year_name, start_date, end_date, is_current)
            VALUES (%s, %s, %s, 1)""",
            (year_name, date(current_year, 9, 1), date(current_year + 1, 7, 15))
        )
        year = db.query_one(
            "SELECT * FROM school_year WHERE year_name = %s",
            (year_name,)
        )

    year_id = year['year_id']

    # 创建当前学期
    semester_name = f"{current_year}-{current_year + 1}上"
    db.execute(
        """INSERT INTO semester (semester_name, year_id, start_date, end_date, status)
        VALUES (%s, %s, %s, %s, 1)""",
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
        WHERE student_id = %s AND status = '在校'""",
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
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
    'check_moral_permission',
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