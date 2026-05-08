# -*- coding: utf-8 -*-
"""datas_api_legacy daily routes contract tests.

Batch37: lock the daily routes response shape and permission behavior.
"""

import pytest
from fastapi import Request
from models.datas_api import legacy_daily as daily_module
from models import datas_api_legacy


class TestDailyRoutesContract:
    """锁定 daily 相关路由返回结构和权限行为"""

    def test_daily_routes_mounted_in_legacy_router(self):
        """daily 路由被挂载到 legacy router 中"""
        daily_paths = {
            "/insert_daily/",
            "/get_dailies/",
            "/export_dailies/",
        }

        legacy_paths = set()
        for route in datas_api_legacy.router.routes:
            path = getattr(route, "path", "")
            if path in daily_paths:
                legacy_paths.add(path)

        # 所有 daily 路由都应在 legacy router 中
        assert daily_paths == legacy_paths

    def test_daily_router_count(self):
        """daily router 应有 3 个路由"""
        assert len(daily_module.router.routes) == 3

    def test_all_daily_routes_have_check_api_permission(self):
        """三个 daily 路由均包含 check_api_permission 依赖"""
        daily_paths = {
            "/insert_daily/",
            "/get_dailies/",
            "/export_dailies/",
        }

        for route in daily_module.router.routes:
            path = getattr(route, "path", "")
            if path not in daily_paths:
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

        sig = inspect.signature(daily_module.check_api_permission)
        assert sig.parameters["request"].annotation is Request

    def test_daily_info_request_fields(self):
        """DailyInfoRequest 字段兼容"""
        req = daily_module.DailyInfoRequest(
            class_code="202401",
            names=["张三", "李四"],
            type="纪律",
            event="迟到",
            remark="第一次",
            recorder="王老师"
        )
        assert req.class_code == "202401"
        assert req.names == ["张三", "李四"]
        assert req.type == "纪律"
        assert req.event == "迟到"
        assert req.remark == "第一次"
        assert req.recorder == "王老师"

    def test_compatibility_imports_in_legacy_module(self):
        """datas_api_legacy.py 中有兼容导入"""
        # 检查 DailyInfoRequest 可以从 legacy module 导入
        from models.datas_api_legacy import DailyInfoRequest
        assert DailyInfoRequest == daily_module.DailyInfoRequest

    def test_no_duplicate_daily_routes_in_legacy(self):
        """datas_api_legacy.py 中不再重复注册 daily 路由"""
        # 检查 legacy 文件中没有 insert_daily/get_dailies/export_dailies 路由定义
        import inspect
        source = inspect.getsource(datas_api_legacy)
        # 检查没有 @router.post("/insert_daily/") 等
        assert "@router.post(\"/insert_daily/\")" not in source
        assert "@router.get(\"/get_dailies/\")" not in source
        assert "@router.get(\"/export_dailies/\")" not in source

    def test_export_dailies_returns_streaming_response(self):
        """export_dailies 仍返回 StreamingResponse 或原有导出响应结构"""
        import inspect
        source = inspect.getsource(daily_module.export_dailies)
        assert "StreamingResponse" in source
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in source

    def test_insert_daily_request_params_compatible(self):
        """insert_daily 的请求参数保持兼容"""
        import inspect
        source = inspect.getsource(daily_module.insert_daily)
        assert "DailyInfoRequest" in source
        assert "daily_ids" in source
        assert "已记录" in source

    def test_get_dailies_query_params_compatible(self):
        """get_dailies 的查询参数保持兼容"""
        import inspect
        source = inspect.getsource(daily_module.get_dailies)
        assert "date" in source
        assert "class_code" in source
        assert "name" in source
        assert "current_user" in source

    def test_daily_reuses_attendance_helpers(self):
        """daily 模块复用 attendance 的 helper 函数"""
        import inspect
        source = inspect.getsource(daily_module)
        assert "_user_has_role" in source
        assert "_can_manage_all_classes" in source
        assert "_get_cleader_class_rows" in source
        # 确认是从 legacy_attendance 导入，而非重新定义
        assert "from models.datas_api.legacy_attendance import" in source

    def test_total_legacy_router_count(self):
        """legacy router 总路由数应包含各子模块路由"""
        from models.datas_api import legacy_schedule as schedule_module
        from models.datas_api import legacy_homework as homework_module
        from models.datas_api import legacy_students as students_module
        from models.datas_api import legacy_attendance as attendance_module

        total = len(datas_api_legacy.router.routes)
        schedule_count = len(schedule_module.router.routes)
        homework_count = len(homework_module.router.routes)
        students_count = len(students_module.router.routes)
        attendance_count = len(attendance_module.router.routes)
        daily_count = len(daily_module.router.routes)

        # 总路由数应大于子模块路由数之和
        assert total >= schedule_count + homework_count + students_count + attendance_count + daily_count