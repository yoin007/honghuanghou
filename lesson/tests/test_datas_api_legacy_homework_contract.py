# -*- coding: utf-8 -*-
"""datas_api_legacy homework/announcement routes contract tests.

Batch34: lock the homework/announcement routes response shape and permission behavior.
"""

import pytest
from models.datas_api import legacy_homework as homework_module
from models.datas_api import legacy_schedule as schedule_module
from models import datas_api_legacy


class TestHomeworkRoutesContract:
    """锁定 homework/announcement 相关路由返回结构和权限行为"""

    def test_homework_routes_mounted_in_legacy_router(self):
        """homework/announcement 路由被挂载到 legacy router 中"""
        homework_paths = {
            "/homework/{class_code}",
            "/homework/",
            "/homework/batch",
            "/homework/{hw_id}",
            "/announcements/{class_code}",
            "/announcement/",
            "/announcement/{ann_id}",
            "/messages/{class_code}",
        }

        legacy_paths = set()
        for route in datas_api_legacy.router.routes:
            path = getattr(route, "path", "")
            if path in homework_paths:
                legacy_paths.add(path)

        # 所有 homework/announcement 路由都应在 legacy router 中
        assert homework_paths == legacy_paths

    def test_homework_router_count(self):
        """homework router 应有 10 个路由"""
        # homework module has 8 routes + schedule module has 10 = 18 total in sub-modules
        # plus routes directly in datas_api_legacy.py
        assert len(homework_module.router.routes) == 10

    def test_routes_with_unified_permission_dependency(self):
        """需要登录的路由包含统一鉴权依赖"""
        permission_required_paths = {
            "/homework/",
            "/homework/batch",
            "/homework/{hw_id}",
            "/announcement/",
            "/announcement/{ann_id}",
        }

        for route in homework_module.router.routes:
            path = getattr(route, "path", "")
            if path not in permission_required_paths:
                continue
            dependency_names = set()
            for dep in route.dependant.dependencies:
                dep_func = getattr(dep, "call", None)
                if dep_func:
                    dependency_names.add(dep_func.__name__)
            assert "check" in dependency_names

    def test_routes_without_login_dependency(self):
        """公开的 homework 路由不包含登录依赖"""
        public_paths = {
            "/homework/{class_code}",
            "/announcements/{class_code}",
            "/messages/{class_code}",
        }

        for route in homework_module.router.routes:
            path = getattr(route, "path", "")
            if path not in public_paths:
                continue
            # 公开路由不应有 get_current_user 作为必需依赖
            dependency_names = set()
            for dep in route.dependant.dependencies:
                dep_func = getattr(dep, "call", None)
                if dep_func:
                    dependency_names.add(dep_func.__name__)
            # 这些路由可能有 current_user 参数，但不是必需的 Depends
            # 只有 /homework/ POST 路由有真正的登录依赖
            assert "get_current_user" not in dependency_names

    def test_teacher_messages_data_structure(self):
        """TEACHER_MESSAGES 数据结构保持不变"""
        assert "202401" in homework_module.TEACHER_MESSAGES
        msg = homework_module.TEACHER_MESSAGES["202401"]
        assert "content" in msg
        assert "teacher" in msg
        assert "date" in msg

    def test_model_classes_exist(self):
        """Pydantic model 类存在且字段正确"""
        # HomeworkForm
        hw_form = homework_module.HomeworkForm(
            classCode="202401",
            subject="语文",
            teacher="张老师",
            content="测试作业",
            deadline="2024-12-20",
            duration=30,
            type="日常"
        )
        assert hw_form.classCode == "202401"
        assert hw_form.subject == "语文"

        # HomeworkIds
        hw_ids = homework_module.HomeworkIds(ids=[1, 2, 3], classCode="202401")
        assert hw_ids.ids == [1, 2, 3]

        # AnnouncementForm
        ann_form = homework_module.AnnouncementForm(
            classCode="202401",
            title="测试公告",
            author="张老师",
            content="公告内容"
        )
        assert ann_form.title == "测试公告"

        # HomeworkUpdateForm - all optional fields
        hw_update = homework_module.HomeworkUpdateForm(subject="数学")
        assert hw_update.subject == "数学"
        assert hw_update.content is None

        # AnnouncementUpdateForm - all optional fields
        ann_update = homework_module.AnnouncementUpdateForm(title="新标题")
        assert ann_update.title == "新标题"
        assert ann_update.content is None

    def test_compatibility_imports_in_legacy_module(self):
        """datas_api_legacy.py 中有兼容导入"""
        # 检查 TEACHER_MESSAGES 可以从 legacy module 导入
        from models.datas_api_legacy import TEACHER_MESSAGES
        assert TEACHER_MESSAGES == homework_module.TEACHER_MESSAGES

    def test_total_legacy_router_count(self):
        """legacy router 总路由数应包含 homework + schedule + 其他"""
        # schedule: 10 routes
        # homework: 10 routes (包括重复的 /homework/{hw_id} GET/DELETE)
        # 其他直接在 datas_api_legacy.py: 约 30+ routes
        # 总数应约 50+
        total = len(datas_api_legacy.router.routes)
        schedule_count = len(schedule_module.router.routes)
        homework_count = len(homework_module.router.routes)
        # 总路由数应大于子模块路由数之和（因为还有直接在 legacy 文件中的路由）
        assert total >= schedule_count + homework_count

    @pytest.mark.asyncio
    async def test_get_class_announcements_closes_homework_connection(self, monkeypatch):
        """公告查询成功时必须关闭 Homework 连接。"""
        events = []

        class FakeHomework:
            def __enter__(self):
                events.append("enter")
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append("exit")

            def get_announcement(self, class_code):
                assert class_code == "202401"
                return [{"title": "测试公告"}]

        monkeypatch.setattr(homework_module, "Homework", FakeHomework)

        result = await homework_module.get_class_announcements("202401")

        assert result == {"announcements": [{"title": "测试公告"}]}
        assert events == ["enter", "exit"]

    @pytest.mark.asyncio
    async def test_get_class_announcements_closes_on_error(self, monkeypatch):
        """公告查询异常时也必须关闭 Homework 连接。"""
        events = []

        class FakeHomework:
            def __enter__(self):
                events.append("enter")
                return self

            def __exit__(self, exc_type, exc, tb):
                events.append("exit")

            def get_announcement(self, class_code):
                raise RuntimeError("db failed")

        monkeypatch.setattr(homework_module, "Homework", FakeHomework)

        with pytest.raises(RuntimeError, match="db failed"):
            await homework_module.get_class_announcements("202401")

        assert events == ["enter", "exit"]
