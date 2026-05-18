# -*- coding: utf-8 -*-
"""datas_api_legacy schedule routes contract tests.

Batch33: lock the schedule routes response shape and permission behavior.
"""

import pytest
from models.datas_api import legacy_schedule as schedule_module
from models.datas_api import utils as datas_api_utils


class TestScheduleRoutesContract:
    """锁定 schedule 相关路由返回结构和权限行为"""

    @pytest.mark.asyncio
    async def test_import_schedule_module_no_io_side_effects(self):
        """import legacy_schedule 不触发课表 I/O 副作用"""
        # 导入后 cached 变量应为 None（惰性）
        assert schedule_module._cached_schedule_data is None
        assert schedule_module._cached_teachers_data is None
        assert schedule_module._cached_periods is None

    def test_schedule_routes_mounted_in_legacy_router(self):
        """schedule 路由被挂载到 legacy router 中"""
        from models import datas_api_legacy

        schedule_paths = {
            "/class-codes/",
            "/schedule/{class_name}",
            "/todays",
            "/schedules",
            "/periods",
            "/current-classes",
            "/teacher-schedule/{teacher_name}",
            "/teacher-schedule-nextweek/{teacher_name}",
            "/upload-schedule",
        }

        legacy_paths = set()
        for route in datas_api_legacy.router.routes:
            path = getattr(route, "path", "")
            if path in schedule_paths:
                legacy_paths.add(path)

        # 所有 schedule 路由都应在 legacy router 中
        assert schedule_paths == legacy_paths

    def test_schedule_routes_with_permission_have_dependency(self):
        """带权限的 schedule 路由包含 legacy 权限依赖"""
        permission_required_paths = {
            "/current-classes",
            "/teacher-schedule/{teacher_name}",
            "/upload-schedule",
        }

        for route in schedule_module.router.routes:
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

    def test_schedule_routes_without_permission_do_not_have_dependency(self):
        """公开的 schedule 路由不包含权限依赖"""
        public_paths = {
            "/class-codes/",
            "/schedule/{class_name}",
            "/todays",
            "/schedules",
            "/periods",
            "/teacher-schedule-nextweek/{teacher_name}",
        }

        for route in schedule_module.router.routes:
            path = getattr(route, "path", "")
            if path not in public_paths:
                continue
            # 公开路由不应有 check_legacy_api_permission
            dependency_names = set()
            for dep in route.dependant.dependencies:
                dep_func = getattr(dep, "call", None)
                if dep_func:
                    dependency_names.add(dep_func.__name__)
            assert "check_legacy_api_permission" not in dependency_names

    def test_schedule_router_count(self):
        """schedule router 应有 10 个路由"""
        assert len(schedule_module.router.routes) == 10

    def test_teacher_data_keeps_empty_subject_compatibility(self, monkeypatch):
        """教师学科为空时保持旧实现的空列表行为。"""
        class FakeColumn:
            def __init__(self, frame, column):
                self.frame = frame
                self.column = column

            def tolist(self):
                return [row[self.column] for row in self.frame.rows]

            @property
            def values(self):
                return [row[self.column] for row in self.frame.rows]

            def __eq__(self, value):
                return [row[self.column] == value for row in self.frame.rows]

        class FakeTeacherFrame:
            def __init__(self, rows):
                self.rows = rows

            def __getitem__(self, key):
                if isinstance(key, str):
                    return FakeColumn(self, key)
                return FakeTeacherFrame([row for row, keep in zip(self.rows, key) if keep])

            @property
            def values(self):
                return self.rows

        class FakeLesson:
            def get_cache_data(self, key):
                assert key == "teacher_template"
                return FakeTeacherFrame([
                    {"name": "张老师", "subject": "语文/历史"},
                    {"name": "李老师", "subject": ""},
                ])

        monkeypatch.setattr(datas_api_utils, "Lesson", lambda: FakeLesson())

        assert datas_api_utils.get_teacher_data() == {
            "张老师": ["语文", "历史"],
            "李老师": [],
        }
