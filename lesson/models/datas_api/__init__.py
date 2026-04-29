# -*- coding: utf-8 -*-
"""
DataS API 模块

按功能区域划分:
- 认证相关: auth 模块
- 管理员管理: admin 模块
- 教师管理: teachers 模块
- 德育评价: moral 模块
- 其他功能: 暂在主模块中

从 v2.0 开始逐步迁移到独立模块
v3.0 新增德育评价模块
"""

import logging
from fastapi import APIRouter

# 导入各功能模块的路由
from .auth import (
    router as auth_router,
    Token,
    TokenData,
    User,
    get_current_user,
    get_user,
    authenticate_user,
    create_access_token,
    get_users_dict,
    hash_password,
    verify_password,
    verify_password_compat,
    get_password_hash,
    is_admin_user,
    get_current_active_user,
    oauth2_scheme,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

from .admin import router as admin_router
from .teachers import router as teachers_router
from .filegather import router as filegather_router
from .dashboard import router as dashboard_router

# 导入德育评价模块
from .moral import router as moral_router

# 导入监考安排模块
from .invigilation import router as invigilation_router

# 导入工具函数
from .utils import (
    refresh_teacher_cache,
    refresh_schedule_cache,
    backup_excel_file,
    get_schedule_data,
    get_teacher_data,
    get_time_table,
    WEEKDAYS,
)

# 导入旧模块中尚未迁移的路由
from models import datas_api_legacy
legacy_router = datas_api_legacy.router

# 创建主路由聚合器
router = APIRouter()

# 包含所有子路由
router.include_router(auth_router)
router.include_router(admin_router)
router.include_router(teachers_router)
router.include_router(filegather_router)
router.include_router(dashboard_router)
# 包含德育评价路由
router.include_router(moral_router)
# 包含监考安排路由
router.include_router(invigilation_router)
# 包含旧模块中尚未迁移的路由
router.include_router(legacy_router)

# 导出所有需要的内容
__all__ = [
    # 路由
    'router',
    'auth_router',
    'admin_router',
    'teachers_router',
    'filegather_router',
    'dashboard_router',
    'moral_router',
    'invigilation_router',
    # 认证相关
    'Token',
    'TokenData',
    'User',
    'get_current_user',
    'get_user',
    'authenticate_user',
    'create_access_token',
    'get_users_dict',
    'hash_password',
    'verify_password',
    'verify_password_compat',
    'get_password_hash',
    'is_admin_user',
    'get_current_active_user',
    'oauth2_scheme',
    # 配置
    'SECRET_KEY',
    'ALGORITHM',
    'ACCESS_TOKEN_EXPIRE_MINUTES',
    # 工具函数
    'refresh_teacher_cache',
    'refresh_schedule_cache',
    'backup_excel_file',
    'get_schedule_data',
    'get_teacher_data',
    'get_time_table',
    'WEEKDAYS',
]

# 保留向后兼容的导入
# 后续将从各模块导入
logger = logging.getLogger(__name__)
