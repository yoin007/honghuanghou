# -*- coding: utf-8 -*-
"""datas_api_legacy entrypoint contract tests.

Batch41: lock the entrypoint cleanup behavior.
"""

import pytest
import jwt
from calendar import timegm

from models import datas_api_legacy
from models.datas_api import legacy_schedule, legacy_homework, legacy_students, legacy_attendance, legacy_daily, legacy_members, legacy_permissions, legacy_tasks, legacy_parking


class TestEntrypointContract:
    """锁定入口清理行为"""

    def test_datas_api_legacy_importable(self):
        """datas_api_legacy 可正常导入"""
        assert datas_api_legacy is not None
        assert hasattr(datas_api_legacy, "router")

    def test_no_direct_business_routes_in_legacy_router(self):
        """datas_api_legacy.router 中直接定义的业务路由数量为 0"""
        direct_routes = [
            route
            for route in datas_api_legacy.router.routes
            if getattr(route, "endpoint", None).__module__ == datas_api_legacy.__name__
        ]
        assert len(direct_routes) == 0

    def test_all_legacy_submodules_mounted(self):
        """所有子模块路由仍挂载到 datas_api_legacy.router"""
        legacy_paths = {
            route.path
            for route in datas_api_legacy.router.routes
        }

        # Schedule routes
        schedule_paths = {route.path for route in legacy_schedule.router.routes}
        assert schedule_paths.issubset(legacy_paths)

        # Homework routes
        homework_paths = {route.path for route in legacy_homework.router.routes}
        assert homework_paths.issubset(legacy_paths)

        # Students routes
        students_paths = {route.path for route in legacy_students.router.routes}
        assert students_paths.issubset(legacy_paths)

        # Attendance routes
        attendance_paths = {route.path for route in legacy_attendance.router.routes}
        assert attendance_paths.issubset(legacy_paths)

        # Daily routes
        daily_paths = {route.path for route in legacy_daily.router.routes}
        assert daily_paths.issubset(legacy_paths)

        # Members routes
        members_paths = {route.path for route in legacy_members.router.routes}
        assert members_paths.issubset(legacy_paths)

        # Permissions routes
        permissions_paths = {route.path for route in legacy_permissions.router.routes}
        assert permissions_paths.issubset(legacy_paths)

        # Tasks routes
        tasks_paths = {route.path for route in legacy_tasks.router.routes}
        assert tasks_paths.issubset(legacy_paths)

        # Parking routes
        parking_paths = {route.path for route in legacy_parking.router.routes}
        assert parking_paths.issubset(legacy_paths)

    def test_compatibility_exports_available(self):
        """关键兼容导出仍可导入"""
        # Schedule compatibility
        from models.datas_api_legacy import get_schedule_data_cached, get_teachers_data_cached, get_periods_cached
        assert get_schedule_data_cached is not None
        assert get_teachers_data_cached is not None
        assert get_periods_cached is not None

        # Homework compatibility
        from models.datas_api_legacy import TEACHER_MESSAGES
        assert TEACHER_MESSAGES is not None

        # Students compatibility
        from models.datas_api_legacy import StudentInfoRequest, get_stu_dict
        assert StudentInfoRequest is not None
        assert get_stu_dict is not None

        # Attendance compatibility
        from models.datas_api_legacy import LeaveRecordRequest
        assert LeaveRecordRequest is not None

        # Daily compatibility
        from models.datas_api_legacy import DailyInfoRequest
        assert DailyInfoRequest is not None

        # Members compatibility
        from models.datas_api_legacy import MemberCreate, MemberUpdate
        assert MemberCreate is not None
        assert MemberUpdate is not None

        # Permissions compatibility
        from models.datas_api_legacy import PermissionCreate, PermissionUpdate
        assert PermissionCreate is not None
        assert PermissionUpdate is not None

    def test_auth_functions_exist(self):
        """认证相关函数存在且可调用"""
        assert hasattr(datas_api_legacy, "check_api_permission")
        assert hasattr(datas_api_legacy, "check_legacy_api_permission")
        assert hasattr(datas_api_legacy, "get_users_dict")
        assert hasattr(datas_api_legacy, "authenticate_user")
        assert hasattr(datas_api_legacy, "create_access_token")
        assert hasattr(datas_api_legacy, "get_current_user")
        assert callable(datas_api_legacy.check_api_permission)
        assert callable(datas_api_legacy.check_legacy_api_permission)
        assert callable(datas_api_legacy.get_users_dict)
        assert callable(datas_api_legacy.authenticate_user)
        assert callable(datas_api_legacy.create_access_token)
        assert callable(datas_api_legacy.get_current_user)

    def test_legacy_permission_helpers_reexport_common_impl(self):
        """权限工具已迁移到 legacy_common，legacy 入口只保留同名兼容导出。"""
        from models.datas_api import legacy_common

        assert datas_api_legacy._match_route is legacy_common._match_route
        assert datas_api_legacy._get_api_rule is legacy_common._get_api_rule
        assert datas_api_legacy.check_api_permission is legacy_common.check_api_permission
        assert datas_api_legacy.check_legacy_api_permission is legacy_common.check_legacy_api_permission

    def test_auth_models_exist(self):
        """认证模型存在且代理正确"""
        from models.datas_api_legacy import Token, TokenData, User
        from models.datas_api.auth import Token as AuthToken, TokenData as AuthTokenData, User as AuthUser

        # Batch74: 认证模型应从 auth.py 代理，同时保留 legacy 原导出名。
        assert Token is AuthToken
        assert TokenData is AuthTokenData
        assert User is AuthUser
        assert Token is not None
        assert TokenData is not None
        assert User is not None

    def test_legacy_oauth2_scheme_keeps_old_token_url(self):
        """legacy oauth2_scheme 暂保留旧 tokenUrl，避免影响旧客户端 OpenAPI 契约。"""
        from models.datas_api.auth import oauth2_scheme as auth_oauth2_scheme

        assert datas_api_legacy.oauth2_scheme.model.flows.password.tokenUrl == "token"
        assert auth_oauth2_scheme.model.flows.password.tokenUrl == "api/token"
        assert datas_api_legacy.oauth2_scheme is not auth_oauth2_scheme

    def test_legacy_role_helpers_keep_xuefa_compatibility(self):
        """legacy 管理员判断仍保留 teacher/xuefa 兼容，auth.py 不直接等同管理员。"""
        from models.datas_api.auth import User, is_admin_user as auth_is_admin_user

        user = User(username="xuefa", role="teacher/xuefa")

        assert datas_api_legacy.is_admin_user(user) is True
        assert auth_is_admin_user(user) is False

    def test_auth_semantic_helpers_cover_role_combinations(self):
        """Batch75: auth.py 新增语义 helper 族覆盖常见角色组合"""
        from models.datas_api.auth import User, is_admin_user, is_admin_or_role

        admin_user = User(username="admin", role="admin")
        jiaowu_user = User(username="jiaowu", role="teacher/jiaowu")
        xuefa_user = User(username="xuefa", role="teacher/xuefa")
        teacher_user = User(username="teacher", role="teacher")

        # is_admin_or_role 语义
        assert is_admin_or_role(admin_user, "jiaowu") is True
        assert is_admin_or_role(jiaowu_user, "jiaowu") is True
        assert is_admin_or_role(xuefa_user, "jiaowu") is False
        assert is_admin_or_role(teacher_user, "jiaowu") is False

        assert is_admin_or_role(admin_user, "xuefa") is True
        assert is_admin_or_role(xuefa_user, "xuefa") is True
        assert is_admin_or_role(jiaowu_user, "xuefa") is False

        # is_admin_user 语义保持（不含 xuefa）
        assert is_admin_user(xuefa_user) is False

    def test_create_access_token_uses_configured_default_expiry(self):
        """legacy token 默认过期时间应使用配置值，而不是旧的 15 分钟写死值。"""
        token = datas_api_legacy.create_access_token({"sub": "legacy-user"})
        payload = jwt.decode(token, datas_api_legacy.SECRET_KEY, algorithms=[datas_api_legacy.ALGORITHM])
        now_utc_seconds = timegm(datas_api_legacy.datetime.utcnow().utctimetuple())
        delta_seconds = payload["exp"] - now_utc_seconds
        expected_seconds = datas_api_legacy.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        assert expected_seconds - 5 <= delta_seconds <= expected_seconds + 5

    def test_no_unused_imports_in_top_section(self):
        """顶部导入清理后不包含未使用导入"""
        import inspect
        source = inspect.getsource(datas_api_legacy)

        # 不应包含这些未使用的导入
        assert "import shutil" not in source
        assert "import json" not in source
        assert "import numpy" not in source
        assert "import math" not in source
        assert "import io" not in source
        assert "import sqlite3" not in source
        assert "from utils.db_config import TASK_DB" not in source
        assert "from models.lesson.homework import Homework" not in source
        assert "from models.daily.inout import InOut" not in source
        assert "from models.daily.daily import Daily" not in source
        assert "from models.manage.member import Member" not in source
        assert "from utils.rate_limit import rate_limiter" not in source
        assert "from utils.cache import cache" not in source
        assert "from utils.operation_log import operation_logger" not in source
        assert "StreamingResponse" not in source
        assert "File, UploadFile" not in source
        assert "OAuth2PasswordRequestForm" not in source

    def test_no_duplicate_imports(self):
        """无重复导入"""
        import inspect
        source = inspect.getsource(datas_api_legacy)

        # OAuth2PasswordBearer 导入应只出现一次（使用时还会出现一次）
        oauth_import_count = source.count("from fastapi.security import OAuth2PasswordBearer")
        assert oauth_import_count == 1, f"from fastapi.security import OAuth2PasswordBearer 出现 {oauth_import_count} 次，应只出现 1 次"

        # BaseModel 导入应只出现一次
        basemodel_import_count = source.count("from pydantic import BaseModel")
        assert basemodel_import_count == 1, f"from pydantic import BaseModel 出现 {basemodel_import_count} 次，应只出现 1 次"

        # datetime/timedelta 导入应只出现一次（组合导入）
        datetime_import_count = source.count("from datetime import datetime")
        assert datetime_import_count == 1, f"from datetime import datetime 出现 {datetime_import_count} 次，应只出现 1 次"

        # Batch74: TokenData 已代理到 auth.py，legacy 不再需要 Optional
        optional_import_count = source.count("from typing import Optional")
        assert optional_import_count == 0, f"from typing import Optional 出现 {optional_import_count} 次，应为 0 次"

        # jwt 导入应只出现一次
        jwt_import_count = source.count("import jwt")
        assert jwt_import_count == 1, f"import jwt 出现 {jwt_import_count} 次，应只出现 1 次"

    def test_router_include_router_calls_exist(self):
        """router.include_router 调用仍存在"""
        import inspect
        source = inspect.getsource(datas_api_legacy)

        assert "router.include_router(schedule_router)" in source
        assert "router.include_router(homework_router)" in source
        assert "router.include_router(students_router)" in source
        assert "router.include_router(attendance_router)" in source
        assert "router.include_router(daily_router)" in source
        assert "router.include_router(members_router)" in source
        assert "router.include_router(permissions_router)" in source
        assert "router.include_router(tasks_router)" in source
        assert "router.include_router(parking_router)" in source
