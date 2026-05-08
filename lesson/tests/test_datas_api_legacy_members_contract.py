# -*- coding: utf-8 -*-
"""datas_api_legacy members routes contract tests.

Batch38: lock the members routes response shape and permission behavior.
"""

import pytest
from fastapi import Request
from models.datas_api import legacy_members as members_module
from models import datas_api_legacy


class TestMembersRoutesContract:
    """锁定 members 相关路由返回结构和权限行为"""

    def test_members_routes_mounted_in_legacy_router(self):
        """members 路由被挂载到 legacy router 中"""
        members_paths = {
            "/members",
            "/members/{uuid}",
        }

        legacy_paths = set()
        for route in datas_api_legacy.router.routes:
            path = getattr(route, "path", "")
            if path in members_paths:
                legacy_paths.add(path)

        # 所有 members 路由都应在 legacy router 中
        assert members_paths == legacy_paths

    def test_members_router_count(self):
        """members router 应有 4 个路由"""
        assert len(members_module.router.routes) == 4

    def test_all_members_routes_have_check_api_permission(self):
        """4 个 members 路由均包含 check_api_permission 依赖"""
        members_paths = {
            "/members",
            "/members/{uuid}",
        }

        for route in members_module.router.routes:
            path = getattr(route, "path", "")
            if path not in members_paths:
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

        sig = inspect.signature(members_module.check_api_permission)
        assert sig.parameters["request"].annotation is Request

    def test_member_create_fields(self):
        """MemberCreate 字段兼容"""
        req = members_module.MemberCreate(
            uuid="test-uuid",
            wxid="test-wxid",
            alias="测试用户",
            active=1,
            score=100,
            balance=50,
            level=2,
            model="pro",
            ai_flag=1,
            birthday="2000-01-01",
            note="测试备注"
        )
        assert req.uuid == "test-uuid"
        assert req.wxid == "test-wxid"
        assert req.alias == "测试用户"
        assert req.active == 1
        assert req.score == 100
        assert req.balance == 50
        assert req.level == 2
        assert req.model == "pro"
        assert req.ai_flag == 1
        assert req.birthday == "2000-01-01"
        assert req.note == "测试备注"

    def test_member_update_fields(self):
        """MemberUpdate 字段兼容"""
        req = members_module.MemberUpdate(
            alias="新别名",
            active=0,
            score=200,
            balance=100,
            level=3,
            model="vip",
            ai_flag=2,
            birthday="1999-12-31"
        )
        assert req.alias == "新别名"
        assert req.active == 0
        assert req.score == 200
        assert req.balance == 100
        assert req.level == 3
        assert req.model == "vip"
        assert req.ai_flag == 2
        assert req.birthday == "1999-12-31"

    def test_member_update_optional_fields(self):
        """MemberUpdate 字段可选"""
        req = members_module.MemberUpdate(alias="仅更新别名")
        assert req.alias == "仅更新别名"
        assert req.active is None
        assert req.score is None
        assert req.balance is None

    def test_compatibility_imports_in_legacy_module(self):
        """datas_api_legacy.py 中有兼容导入"""
        # 检查 MemberCreate 可以从 legacy module 导入
        from models.datas_api_legacy import MemberCreate
        assert MemberCreate == members_module.MemberCreate

        # 检查 MemberUpdate 可以从 legacy module 导入
        from models.datas_api_legacy import MemberUpdate
        assert MemberUpdate == members_module.MemberUpdate

    def test_no_duplicate_members_routes_in_legacy(self):
        """datas_api_legacy.py 中不再重复注册 members 路由"""
        import inspect
        source = inspect.getsource(datas_api_legacy)
        # 检查没有 @router.get("/members") 等（注意：/members 路径在 permissions 路由中没有）
        # 因为路径已迁移，legacy 文件中不应有这些路由定义
        assert "async def get_members(" not in source
        assert "async def create_member(" not in source
        assert "async def update_member(" not in source
        assert "async def delete_member(" not in source

    def test_get_members_response_structure_compatible(self):
        """GET /members 的响应结构保持兼容"""
        import inspect
        source = inspect.getsource(members_module.get_members)
        # 检查返回结构
        assert '"total"' in source or "'total'" in source
        assert '"page"' in source or "'page'" in source
        assert '"page_size"' in source or "'page_size'" in source
        assert '"data"' in source or "'data'" in source

    def test_create_member_request_params_compatible(self):
        """POST /members 的请求参数保持兼容"""
        import inspect
        source = inspect.getsource(members_module.create_member)
        assert "MemberCreate" in source
        assert "会员创建成功" in source or "success" in source

    def test_update_member_request_params_compatible(self):
        """PUT /members/{uuid} 的请求参数保持兼容"""
        import inspect
        source = inspect.getsource(members_module.update_member)
        assert "MemberUpdate" in source
        assert "uuid" in source
        assert "会员更新成功" in source or "会员不存在" in source

    def test_delete_member_request_params_compatible(self):
        """DELETE /members/{uuid} 的请求参数保持兼容"""
        import inspect
        source = inspect.getsource(members_module.delete_member)
        assert "uuid" in source
        assert "会员删除成功" in source or "会员不存在" in source

    def test_member_context_manager_used(self):
        """Member 上下文使用 with Member() as m 模式"""
        import inspect
        # 检查所有 members 路由都使用 with Member()
        for func_name in ["get_members", "create_member", "update_member", "delete_member"]:
            func = getattr(members_module, func_name)
            source = inspect.getsource(func)
            assert "with Member()" in source

    def test_total_legacy_router_count(self):
        """legacy router 总路由数应包含各子模块路由"""
        from models.datas_api import legacy_schedule as schedule_module
        from models.datas_api import legacy_homework as homework_module
        from models.datas_api import legacy_students as students_module
        from models.datas_api import legacy_attendance as attendance_module
        from models.datas_api import legacy_daily as daily_module

        total = len(datas_api_legacy.router.routes)
        schedule_count = len(schedule_module.router.routes)
        homework_count = len(homework_module.router.routes)
        students_count = len(students_module.router.routes)
        attendance_count = len(attendance_module.router.routes)
        daily_count = len(daily_module.router.routes)
        members_count = len(members_module.router.routes)

        # 总路由数应大于子模块路由数之和
        assert total >= schedule_count + homework_count + students_count + attendance_count + daily_count + members_count