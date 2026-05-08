# -*- coding: utf-8 -*-
"""datas_api_legacy students routes contract tests.

Batch35: lock the students/class-info routes response shape and permission behavior.
"""

import pytest
from models.datas_api import legacy_students as students_module
from models import datas_api_legacy


class TestStudentsRoutesContract:
    """锁定 students/class-info 相关路由返回结构和权限行为"""

    def test_students_routes_mounted_in_legacy_router(self):
        """students/class-info 路由被挂载到 legacy router 中"""
        students_paths = {
            "/class-info/{class_code}",
            "/students/{class_code}",
            "/students/export/{class_code}",
            "/students/import/{class_code}",
            "/students_status/{class_code}",
            "/student_info/",
        }

        legacy_paths = set()
        for route in datas_api_legacy.router.routes:
            path = getattr(route, "path", "")
            if path in students_paths:
                legacy_paths.add(path)

        # 所有 students 路由都应在 legacy router 中
        assert students_paths == legacy_paths

    def test_students_router_count(self):
        """students router 应有 6 个路由"""
        assert len(students_module.router.routes) == 6

    def test_routes_without_permission_dependency(self):
        """students 路由均为公开路由，不包含权限依赖"""
        public_paths = {
            "/class-info/{class_code}",
            "/students/{class_code}",
            "/students/export/{class_code}",
            "/students/import/{class_code}",
            "/students_status/{class_code}",
            "/student_info/",
        }

        for route in students_module.router.routes:
            path = getattr(route, "path", "")
            if path not in public_paths:
                continue
            # 公开路由不应有 unified_api_permission 或其他权限依赖
            dependency_names = set()
            for dep in route.dependant.dependencies:
                dep_func = getattr(dep, "call", None)
                if dep_func:
                    dependency_names.add(dep_func.__name__)
            assert "unified_api_permission" not in dependency_names
            assert "check_legacy_api_permission" not in dependency_names

    def test_student_info_request_fields(self):
        """StudentInfoRequest 字段兼容"""
        req = students_module.StudentInfoRequest(sid="12345", classCode="202401")
        assert req.sid == "12345"
        assert req.classCode == "202401"

    def test_compatibility_imports_in_legacy_module(self):
        """datas_api_legacy.py 中有兼容导入"""
        # 检查 StudentInfoRequest 可以从 legacy module 导入
        from models.datas_api_legacy import StudentInfoRequest
        assert StudentInfoRequest == students_module.StudentInfoRequest

        # 检查 get_stu_dict 可以从 legacy module 导入
        from models.datas_api_legacy import get_stu_dict
        assert get_stu_dict == students_module.get_stu_dict

    def test_import_file_type_validation(self):
        """导入路由文件类型校验仍为 xlsx/xls"""
        # 检查路由函数中包含文件类型校验逻辑
        import inspect
        source = inspect.getsource(students_module.import_students_excel)
        assert ".xlsx" in source or ".xls" in source
        assert "只允许上传" in source or "格式" in source

    def test_get_stu_dict_function_exists(self):
        """get_stu_dict 函数存在且签名正确"""
        import inspect
        sig = inspect.signature(students_module.get_stu_dict)
        assert "sid" in sig.parameters
        # 返回值应为 dict
        # 实际测试需要在有数据的情况下运行

    def test_total_legacy_router_count(self):
        """legacy router 总路由数应包含 schedule + homework + students + 其他"""
        from models.datas_api import legacy_schedule as schedule_module
        from models.datas_api import legacy_homework as homework_module

        total = len(datas_api_legacy.router.routes)
        schedule_count = len(schedule_module.router.routes)
        homework_count = len(homework_module.router.routes)
        students_count = len(students_module.router.routes)

        # 总路由数应大于子模块路由数之和（因为还有直接在 legacy 文件中的路由）
        assert total >= schedule_count + homework_count + students_count
        # 当前总数应为 50
        assert total == 50

    def test_class_info_returns_structured_response(self):
        """class-info 路由返回结构符合预期"""
        # 验证路由定义中返回 class_info 字段
        import inspect
        source = inspect.getsource(students_module.get_class_info)
        assert "class_info" in source
        assert "className" in source
        assert "classTeacher" in source
        assert "studentCount" in source

    def test_students_export_uses_streaming_response(self):
        """导出路由使用 StreamingResponse"""
        import inspect
        source = inspect.getsource(students_module.export_students_excel)
        assert "StreamingResponse" in source
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in source