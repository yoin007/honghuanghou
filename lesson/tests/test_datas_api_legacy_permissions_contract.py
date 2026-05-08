# -*- coding: utf-8 -*-
"""datas_api_legacy permissions routes contract tests.

Batch39: lock the permissions routes response shape and permission behavior.
"""

import pytest
from fastapi import Request
from models.datas_api import legacy_permissions as permissions_module
from models import datas_api_legacy


class TestPermissionsRoutesContract:
    """锁定 permissions 相关路由返回结构和权限行为"""

    def test_permissions_routes_mounted_in_legacy_router(self):
        """permissions 路由被挂载到 legacy router 中"""
        permissions_paths = {
            "/permissions",
            "/permissions/{id}",
        }

        legacy_paths = set()
        for route in datas_api_legacy.router.routes:
            path = getattr(route, "path", "")
            if path in permissions_paths:
                legacy_paths.add(path)

        # 所有 permissions 路由都应在 legacy router 中
        assert permissions_paths == legacy_paths

    def test_permissions_router_count(self):
        """permissions router 应有 4 个路由"""
        assert len(permissions_module.router.routes) == 4

    def test_all_permissions_routes_have_check_api_permission(self):
        """4 个 permissions 路由均包含 check_api_permission 依赖"""
        permissions_paths = {
            "/permissions",
            "/permissions/{id}",
        }

        for route in permissions_module.router.routes:
            path = getattr(route, "path", "")
            if path not in permissions_paths:
                continue
            # 检查是否有 check_api_permission 依赖
            dependency_names = set()
            for dep in route.dependant.dependencies:
                dep_func = getattr(dep, "call", None)
                if dep_func:
                    dependency_names.add(dep_func.__name__)
            assert "check_api_permission" in dependency_names

    def test_check_api_permission_accepts_fastapi_request(self):
        """权限依赖必须接收 FastAPI Request 注入，而不是查询参数"""
        import inspect

        sig = inspect.signature(permissions_module.check_api_permission)
        assert sig.parameters["request"].annotation is Request

    def test_permission_create_fields(self):
        """PermissionCreate 字段兼容"""
        req = permissions_module.PermissionCreate(
            func="test_func",
            func_name="测试功能",
            pattern="/test/*",
            white_list="admin,cleader",
            module="test_module",
            activate=1,
            black_list="student",
            type="api",
            keywords="test",
            ai_flag=1,
            need_at=1,
            reply="测试回复",
            level=2,
            priority=50,
            example="/test/example",
            check_permission=1,
            score=10,
            balance=5,
            notes="测试备注"
        )
        assert req.func == "test_func"
        assert req.func_name == "测试功能"
        assert req.pattern == "/test/*"
        assert req.white_list == "admin,cleader"
        assert req.module == "test_module"
        assert req.activate == 1
        assert req.black_list == "student"
        assert req.type == "api"
        assert req.keywords == "test"
        assert req.ai_flag == 1
        assert req.need_at == 1
        assert req.reply == "测试回复"
        assert req.level == 2
        assert req.priority == 50
        assert req.example == "/test/example"
        assert req.check_permission == 1
        assert req.score == 10
        assert req.balance == 5
        assert req.notes == "测试备注"

    def test_permission_update_fields(self):
        """PermissionUpdate 字段兼容"""
        req = permissions_module.PermissionUpdate(
            func_name="新功能名",
            pattern="/new/*",
            activate=0,
            black_list="new_black",
            white_list="new_white",
            type="new_type",
            keywords="new_keywords",
            ai_flag=2,
            need_at=2,
            reply="新回复",
            module="new_module",
            level=3,
            priority=10,
            example="/new/example",
            check_permission=0,
            score=20,
            balance=10,
            notes="新备注"
        )
        assert req.func_name == "新功能名"
        assert req.pattern == "/new/*"
        assert req.activate == 0
        assert req.black_list == "new_black"
        assert req.white_list == "new_white"
        assert req.type == "new_type"
        assert req.keywords == "new_keywords"
        assert req.ai_flag == 2
        assert req.need_at == 2
        assert req.reply == "新回复"
        assert req.module == "new_module"
        assert req.level == 3
        assert req.priority == 10
        assert req.example == "/new/example"
        assert req.check_permission == 0
        assert req.score == 20
        assert req.balance == 10
        assert req.notes == "新备注"

    def test_permission_update_optional_fields(self):
        """PermissionUpdate 字段可选"""
        req = permissions_module.PermissionUpdate(func_name="仅更新功能名")
        assert req.func_name == "仅更新功能名"
        assert req.pattern is None
        assert req.activate is None
        assert req.black_list is None
        assert req.white_list is None
        assert req.type is None
        assert req.keywords is None
        assert req.ai_flag is None
        assert req.need_at is None
        assert req.reply is None
        assert req.module is None
        assert req.level is None
        assert req.priority is None
        assert req.example is None
        assert req.check_permission is None
        assert req.score is None
        assert req.balance is None
        assert req.notes is None

    def test_compatibility_imports_in_legacy_module(self):
        """datas_api_legacy.py 中有兼容导入"""
        # 检查 PermissionCreate 可以从 legacy module 导入
        from models.datas_api_legacy import PermissionCreate
        assert PermissionCreate == permissions_module.PermissionCreate

        # 检查 PermissionUpdate 可以从 legacy module 导入
        from models.datas_api_legacy import PermissionUpdate
        assert PermissionUpdate == permissions_module.PermissionUpdate

    def test_no_duplicate_permissions_routes_in_legacy(self):
        """datas_api_legacy.py 中不再重复注册 permissions 路由"""
        import inspect
        source = inspect.getsource(datas_api_legacy)
        # 检查没有 permissions 路由定义函数
        assert "async def get_permissions(" not in source
        assert "async def create_permission(" not in source
        assert "async def update_permission(" not in source
        assert "async def delete_permission(" not in source
        # 检查没有 PermissionCreate/PermissionUpdate 类定义
        assert "class PermissionCreate(BaseModel):" not in source
        assert "class PermissionUpdate(BaseModel):" not in source

    def test_get_permissions_response_structure_compatible(self):
        """GET /permissions 的响应结构保持兼容"""
        import inspect
        source = inspect.getsource(permissions_module.get_permissions)
        # 检查返回结构
        assert '"total"' in source or "'total'" in source
        assert '"page"' in source or "'page'" in source
        assert '"page_size"' in source or "'page_size'" in source
        assert '"data"' in source or "'data'" in source
        assert "permissions" in source

    def test_create_permission_request_params_compatible(self):
        """POST /permissions 的请求参数保持兼容"""
        import inspect
        source = inspect.getsource(permissions_module.create_permission)
        assert "PermissionCreate" in source
        assert "权限创建成功" in source or "success" in source
        assert "insert_permission" in source

    def test_update_permission_request_params_compatible(self):
        """PUT /permissions/{id} 的请求参数保持兼容"""
        import inspect
        source = inspect.getsource(permissions_module.update_permission)
        assert "PermissionUpdate" in source
        assert "id" in source
        assert "权限更新成功" in source or "权限ID不存在" in source
        assert "update_permission" in source

    def test_delete_permission_request_params_compatible(self):
        """DELETE /permissions/{id} 的请求参数保持兼容"""
        import inspect
        source = inspect.getsource(permissions_module.delete_permission)
        assert "id" in source
        assert "权限删除成功" in source or "权限ID不存在" in source
        assert "delte_permission" in source

    def test_member_context_manager_used(self):
        """Member 上下文使用 with Member() as m 模式"""
        import inspect
        # 检查所有 permissions 路由都使用 with Member()
        for func_name in ["get_permissions", "create_permission", "update_permission", "delete_permission"]:
            func = getattr(permissions_module, func_name)
            source = inspect.getsource(func)
            assert "with Member()" in source

    def test_total_legacy_router_count(self):
        """legacy router 总路由数应包含各子模块路由"""
        from models.datas_api import legacy_schedule as schedule_module
        from models.datas_api import legacy_homework as homework_module
        from models.datas_api import legacy_students as students_module
        from models.datas_api import legacy_attendance as attendance_module
        from models.datas_api import legacy_daily as daily_module
        from models.datas_api import legacy_members as members_module

        total = len(datas_api_legacy.router.routes)
        schedule_count = len(schedule_module.router.routes)
        homework_count = len(homework_module.router.routes)
        students_count = len(students_module.router.routes)
        attendance_count = len(attendance_module.router.routes)
        daily_count = len(daily_module.router.routes)
        members_count = len(members_module.router.routes)
        permissions_count = len(permissions_module.router.routes)

        # 总路由数应大于子模块路由数之和
        assert total >= schedule_count + homework_count + students_count + attendance_count + daily_count + members_count + permissions_count