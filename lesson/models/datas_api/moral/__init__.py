# -*- coding: utf-8 -*-
"""
德育评价系统 API 模块

提供德育评价相关的所有API接口：
- 日常表现记录 (daily_record)
- 校级事件记录 (school_event)
- 德育任务管理 (task)
- 处分管理 (punishment)
- 评价查询 (evaluation)
- 学生画像 (profile)
- 生日提醒 (birthday)
- AI诊疗 (consultation)
- 系统管理 (admin)

权限角色说明：
- admin: 系统管理员，拥有所有权限
- jiaowu: 教发部，负责教学质量、教师管理
- xuefa: 学发部，负责德育评价管理
- cleader: 班主任，管理本班数据
- teacher: 普通教师，可录入德育记录
- student: 学生，可查看自己数据
- parent: 家长，可查看子女数据
"""

from .base import (
    get_moral_db,
    MoralDB,
    check_moral_permission,
    check_class_access,
    get_current_semester,
    get_current_school_year,
    get_next_school_year,
    get_user_role_level,
    MORAL_PERMISSIONS,
)

from .daily_record import router as daily_record_router
from .school_event import router as school_event_router
from .task import router as task_router
from .punishment import router as punishment_router
from .evaluation import router as evaluation_router
from .profile import router as profile_router
from .birthday import router as birthday_router
from .consultation import router as consultation_router
from .admin import router as admin_router
from .escalation_api import router as escalation_router
from .moment_api import router as moment_router
from .timeline_api import router as timeline_router
from .api_permission import router as api_permission_router
from .collective import router as collective_router
from .carryover import router as carryover_router
from .scheduler import scheduler_router
from .database_admin import router as database_admin_router
from .menu_permission import router as menu_permission_router

from fastapi import APIRouter
from fastapi import Depends
from typing import List
import json

# 创建主路由聚合器
router = APIRouter(prefix="/moral", tags=["德育评价"])


# =============================================================================
# 直接挂载的路由（不带子前缀）
# =============================================================================

@router.get("/punishment-types", summary="获取处罚类型列表")
async def get_punishment_types_direct():
    """
    获取处罚类型列表（用于前端下拉框）

    无需权限验证（前端展示需要）
    """
    with get_moral_db() as db:
        config = db.query_one(
            "SELECT config_value FROM moral_config WHERE config_key = 'punishment_types'"
        )
        if config:
            try:
                types = json.loads(config['config_value'])
                return {"success": True, "data": types}
            except:
                pass
    # 默认值
    default_types = [
        {"action": "warning", "name": "警告", "level": None},
        {"action": "serious_warning", "name": "严重警告", "level": "一级"},
        {"action": "criticism", "name": "通报", "level": "二级"},
        {"action": "demerit", "name": "记过", "level": "三级"},
        {"action": "observation", "name": "留校查看", "level": "四级"}
    ]
    return {"success": True, "data": default_types}


# 包含所有子路由
router.include_router(daily_record_router)
router.include_router(school_event_router)
router.include_router(task_router)
router.include_router(punishment_router)
router.include_router(evaluation_router)
router.include_router(profile_router)
router.include_router(birthday_router)
router.include_router(consultation_router)
router.include_router(admin_router)
router.include_router(escalation_router)
router.include_router(moment_router)
router.include_router(timeline_router)
router.include_router(api_permission_router)
router.include_router(collective_router)
router.include_router(carryover_router)
router.include_router(scheduler_router)
router.include_router(database_admin_router)
router.include_router(menu_permission_router)

__all__ = [
    'router',
    'get_moral_db',
    'MoralDB',
    'check_moral_permission',
    'check_class_access',
    'get_current_semester',
    'get_current_school_year',
    'get_next_school_year',
    'get_user_role_level',
    'MORAL_PERMISSIONS',
]