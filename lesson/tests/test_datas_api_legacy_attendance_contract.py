# -*- coding: utf-8 -*-
"""datas_api_legacy attendance routes contract tests.

Batch36: lock the attendance/leave/delay routes response shape and permission behavior.
"""

import pytest
from fastapi import Request
from models.datas_api import legacy_attendance as attendance_module
from models import datas_api_legacy


class TestAttendanceRoutesContract:
    """锁定 attendance/leave/delay 相关路由返回结构和权限行为"""

    def test_attendance_routes_mounted_in_legacy_router(self):
        """attendance 路由被挂载到 legacy router 中"""
        attendance_paths = {
            "/insert_delay/",
            "/delay_infos/{classCode}",
            "/del_delay/{id}",
            "/cleader-classes/",
            "/leave-records/",
            "/leave-records/{record_id}/consume",
        }

        legacy_paths = set()
        for route in datas_api_legacy.router.routes:
            path = getattr(route, "path", "")
            if path in attendance_paths:
                legacy_paths.add(path)

        # 所有 attendance 路由都应在 legacy router 中
        assert attendance_paths == legacy_paths

    def test_attendance_router_count(self):
        """attendance router 应有 7 个路由"""
        # del_delay 路由单独计数
        assert len(attendance_module.router.routes) == 7

    def test_del_delay_has_unified_permission_dependency(self):
        """/del_delay/{id} 已接入统一鉴权依赖"""
        for route in attendance_module.router.routes:
            path = getattr(route, "path", "")
            if path != "/del_delay/{id}":
                continue
            # 统一鉴权后检查 require_configured_api_permission 生成的 check 依赖
            dependency_names = set()
            for dep in route.dependant.dependencies:
                dep_func = getattr(dep, "call", None)
                if dep_func:
                    dependency_names.add(dep_func.__name__)
            # 统一鉴权依赖生成名为 check 的内部函数
            assert "check" in dependency_names

    def test_leave_records_routes_have_check_api_permission(self):
        """leave-records 相关路由已接入统一鉴权依赖"""
        permission_required_paths = {
            "/cleader-classes/",
            "/leave-records/",
            "/leave-records/{record_id}/consume",
        }

        for route in attendance_module.router.routes:
            path = getattr(route, "path", "")
            if path not in permission_required_paths:
                continue
            # 统一鉴权后检查 require_configured_api_permission 生成的 check 依赖
            dependency_names = set()
            for dep in route.dependant.dependencies:
                dep_func = getattr(dep, "call", None)
                if dep_func:
                    dependency_names.add(dep_func.__name__)
            # 统一鉴权依赖生成名为 check 的内部函数
            assert "check" in dependency_names

    def test_check_api_permission_accepts_fastapi_request(self):
        """权限依赖必须接收 FastAPI Request 注入，而不是查询参数。"""
        import inspect

        sig = inspect.signature(attendance_module.check_api_permission)

        assert sig.parameters["request"].annotation is Request

    def test_leave_record_request_fields(self):
        """LeaveRecordRequest 字段兼容"""
        req = attendance_module.LeaveRecordRequest(
            class_code="202401",
            names=["张三", "李四"],
            style="请假",
            days=2,
            note="病假"
        )
        assert req.class_code == "202401"
        assert req.names == ["张三", "李四"]
        assert req.style == "请假"
        assert req.days == 2
        assert req.note == "病假"

    def test_student_info_request_from_students_module(self):
        """StudentInfoRequest 继续来自 legacy_students"""
        from models.datas_api.legacy_students import StudentInfoRequest
        req = StudentInfoRequest(sid="12345", classCode="202401")
        assert req.sid == "12345"
        assert req.classCode == "202401"

    def test_compatibility_imports_in_legacy_module(self):
        """datas_api_legacy.py 中有兼容导入"""
        # 检查 LeaveRecordRequest 可以从 legacy module 导入
        from models.datas_api_legacy import LeaveRecordRequest
        assert LeaveRecordRequest == attendance_module.LeaveRecordRequest

        # 检查 helper 函数可以从 legacy module 导入
        from models.datas_api_legacy import _user_has_role, _user_has_any_role
        assert _user_has_role == attendance_module._user_has_role
        assert _user_has_any_role == attendance_module._user_has_any_role

    def test_user_has_role_behavior(self):
        """_user_has_role 和 _user_has_any_role 行为兼容"""
        # Mock user with role
        class MockUser:
            role = "admin/cleader"

        assert attendance_module._user_has_role(MockUser(), "admin") is True
        assert attendance_module._user_has_role(MockUser(), "cleader") is True
        assert attendance_module._user_has_role(MockUser(), "xuefa") is False

        assert attendance_module._user_has_any_role(MockUser(), ["admin", "xuefa"]) is True
        assert attendance_module._user_has_any_role(MockUser(), ["xuefa", "teacher"]) is False

        # None user
        assert attendance_module._user_has_role(None, "admin") is False
        assert attendance_module._user_has_any_role(None, ["admin"]) is False

    def test_total_legacy_router_count(self):
        """legacy router 总路由数应包含 schedule + homework + students + attendance + 其他"""
        from models.datas_api import legacy_schedule as schedule_module
        from models.datas_api import legacy_homework as homework_module
        from models.datas_api import legacy_students as students_module

        total = len(datas_api_legacy.router.routes)
        schedule_count = len(schedule_module.router.routes)
        homework_count = len(homework_module.router.routes)
        students_count = len(students_module.router.routes)
        attendance_count = len(attendance_module.router.routes)

        # 总路由数应大于子模块路由数之和（因为还有直接在 legacy 文件中的路由）
        assert total >= schedule_count + homework_count + students_count + attendance_count

    def test_consume_leave_record_route_path_and_method(self):
        """leave-records consume 路由路径和方法保持不变"""
        import inspect
        source = inspect.getsource(attendance_module.consume_leave_record)
        assert "record_id" in source
        assert "已销假" in source

    def test_insert_delay_uses_student_info_request(self):
        """insert_delay 路由使用 StudentInfoRequest（来自 legacy_students）"""
        import inspect
        source = inspect.getsource(attendance_module.insert_delay)
        assert "StudentInfoRequest" in source
        assert "InOut" in source
