# -*- coding: utf-8 -*-
"""datas_api_legacy parking routes contract tests.

Batch40: lock the vehicle-inout route mounting and permission behavior.
"""

import pytest

from models import datas_api_legacy
from models.datas_api import legacy_parking as parking_module


class TestParkingRoutesContract:
    """锁定 parking/vehicle-inout 相关路由行为"""

    def test_parking_route_mounted_in_legacy_router(self):
        """vehicle-inout 路由被挂载到 legacy router 中"""
        paths = {getattr(route, "path", "") for route in datas_api_legacy.router.routes}

        assert "/vehicle-inout/{counts}" in paths

    def test_parking_router_count(self):
        """parking router 应只有 1 个路由"""
        assert len(parking_module.router.routes) == 1

    def test_vehicle_inout_has_unified_api_permission_dependency(self):
        """/vehicle-inout/{counts} 保留 unified_api_permission 依赖"""
        route = parking_module.router.routes[0]
        dependency_names = {
            getattr(getattr(dep, "call", None), "__name__", "")
            for dep in route.dependant.dependencies
        }

        assert "check" in dependency_names

    def test_no_direct_business_routes_left_in_legacy(self):
        """datas_api_legacy.py 不再直接注册业务路由"""
        direct_route_paths = [
            getattr(route, "path", "")
            for route in datas_api_legacy.router.routes
            if getattr(route, "endpoint", None).__module__ == datas_api_legacy.__name__
        ]

        assert direct_route_paths == []

    def test_vehicle_inout_not_defined_directly_in_legacy(self):
        """datas_api_legacy.py 中不再直接定义 vehicle-inout 路由"""
        import inspect

        source = inspect.getsource(datas_api_legacy)

        assert '@router.get("/vehicle-inout/{counts}"' not in source
        assert "async def get_vehicle_inout(" not in source

    @pytest.mark.asyncio
    async def test_get_vehicle_inout_returns_parking_records(self, monkeypatch):
        """get_vehicle_inout 返回 get_parking_records 的原始结果"""
        calls = []

        def fake_get_parking_records(counts):
            calls.append(counts)
            return [{"plate": "TEST-001"}]

        monkeypatch.setattr(parking_module, "get_parking_records", fake_get_parking_records)

        result = await parking_module.get_vehicle_inout(7)

        assert calls == [7]
        assert result == [{"plate": "TEST-001"}]

    def test_legacy_compatibility_exports_remain_available(self):
        """legacy 兼容符号仍可从 datas_api_legacy 导入"""
        from models.datas_api_legacy import DailyInfoRequest
        from models.datas_api_legacy import LeaveRecordRequest
        from models.datas_api_legacy import MemberCreate
        from models.datas_api_legacy import MemberUpdate
        from models.datas_api_legacy import PermissionCreate
        from models.datas_api_legacy import PermissionUpdate
        from models.datas_api_legacy import StudentInfoRequest
        from models.datas_api_legacy import TEACHER_MESSAGES
        from models.datas_api_legacy import get_stu_dict

        assert TEACHER_MESSAGES
        assert StudentInfoRequest
        assert get_stu_dict
        assert LeaveRecordRequest
        assert DailyInfoRequest
        assert MemberCreate
        assert MemberUpdate
        assert PermissionCreate
        assert PermissionUpdate
