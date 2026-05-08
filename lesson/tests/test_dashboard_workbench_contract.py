# -*- coding: utf-8 -*-
"""Dashboard Workbench contract tests.

Batch25: lock the response shape for teacher workbench endpoint.
"""
import pytest
from fastapi import HTTPException

from models.datas_api.auth import User
from models.datas_api import dashboard


class FakeInvigilationConnection:
    """Fake invigilation DB connection for workbench tests."""

    def __init__(self):
        self.row_factory = None
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def cursor(self):
        return FakeInvigilationCursor()

    def close(self):
        self.closed = True


class FakeInvigilationCursor:
    def __init__(self):
        self.rows = []

    def execute(self, sql, params=None):
        # 返回空列表（模拟无监考任务）
        self.rows = []
        return self

    def fetchall(self):
        return self.rows

    def close(self):
        pass


@pytest.fixture
def users():
    return {
        "teacher": User(username="teacher1", role="teacher"),
        "admin": User(username="admin", role="admin"),
    }


@pytest.fixture(autouse=True)
def isolate_workbench(monkeypatch):
    """隔离 workbench 测试，避免访问真实数据库或课表。"""

    # Mock _get_invigilation_db
    monkeypatch.setattr(dashboard, "_get_invigilation_db", lambda: FakeInvigilationConnection())

    # Mock moral DB
    class FakeMoralDB:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def query_value(self, sql, params=None):
            return 0

    monkeypatch.setattr(dashboard, "get_moral_db", lambda: FakeMoralDB())

    # Mock homework DB
    class FakeHomeworkConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            class FakeCursor:
                def execute(self, sql, params=None):
                    return self

                def fetchone(self):
                    return (0,)
            return FakeCursor()

    monkeypatch.setattr(dashboard, "_get_homework_db", lambda: FakeHomeworkConnection())

    # Mock Lesson
    class FakeLesson:
        lesson_dir = "/tmp/nonexistent-workbench"
        week_change = 0

        def __init__(self):
            self.schedule_service = None

        def get_cache_data(self, key):
            import pandas as pd
            if key == "today_schedule":
                return pd.DataFrame([])
            return None

    monkeypatch.setattr(dashboard, "Lesson", FakeLesson)

    # Mock teacher lesson counts
    monkeypatch.setattr(
        dashboard,
        "_teacher_lesson_counts_from_files",
        lambda start_date, end_date, teacher_name=None: {
            "rows": [],
            "covered_dates": [],
            "source_files": [],
            "lessons": [],
            "message": "test",
        }
    )


class TestTeacherWorkbenchContract:
    """锁定教师工作台返回结构。"""

    @pytest.mark.asyncio
    async def test_workbench_returns_stable_structure(self, users):
        """get_teacher_workbench 返回 cards/tables/range/updated_at 等稳定结构。"""
        result = await dashboard.get_teacher_workbench(user=users["teacher"])

        assert result["success"] is True
        assert "data" in result
        data = result["data"]

        # 必须包含的字段
        for key in ["cards", "tables", "workload", "range", "updated_at"]:
            assert key in data

        # tables 必须包含的字段
        for key in ["today_lessons", "invigilation_tasks", "workload_lessons"]:
            assert key in data["tables"]

        # cards 应为列表
        assert isinstance(data["cards"], list)

        # workload 应包含 lesson_count 和 covered_dates
        assert "lesson_count" in data["workload"]
        assert "covered_dates" in data["workload"]
        assert "lessons" not in data["workload"]

        # range 应包含 start_date 和 end_date
        assert "start_date" in data["range"]
        assert "end_date" in data["range"]

    @pytest.mark.asyncio
    async def test_teacher_can_access_own_workbench(self, users):
        """teacher 可访问自己的工作台。"""
        result = await dashboard.get_teacher_workbench(user=users["teacher"])

        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_invigilation_db_failure_returns_empty_tasks(self, monkeypatch, users):
        """invigilation.db 查询异常时不影响主接口，监考任务返回空列表。"""

        class FailingInvigilationConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                raise Exception("invigilation DB connection failed")

            def close(self):
                pass

        monkeypatch.setattr(
            dashboard,
            "_get_invigilation_db",
            lambda: FailingInvigilationConnection()
        )

        result = await dashboard.get_teacher_workbench(user=users["teacher"])

        # 主接口应该仍然返回成功（异常被吞掉）
        assert result["success"] is True
        # invigilation_tasks 应为空列表（异常时 pass）
        assert result["data"]["tables"]["invigilation_tasks"] == []

    @pytest.mark.asyncio
    async def test_workbench_uses_get_invigilation_db_not_direct_connect(self, monkeypatch, users):
        """workbench 使用 _get_invigilation_db，避免直接 sqlite3.connect。"""

        called = []

        def fake_get_invigilation_db():
            called.append("_get_invigilation_db")
            return FakeInvigilationConnection()

        monkeypatch.setattr(dashboard, "_get_invigilation_db", fake_get_invigilation_db)

        # 禁止 sqlite3.connect（应该不会被调用）
        def forbidden_connect(*args, **kwargs):
            called.append("sqlite3.connect")
            raise AssertionError("sqlite3.connect should not be called")

        monkeypatch.setattr(dashboard.sqlite3, "connect", forbidden_connect)

        result = await dashboard.get_teacher_workbench(user=users["teacher"])

        # 应调用 _get_invigilation_db
        assert "_get_invigilation_db" in called
        # 不应调用 sqlite3.connect
        assert "sqlite3.connect" not in called

    @pytest.mark.asyncio
    async def test_workbench_cards_count_matches_expectation(self, users):
        """workbench cards 数量应稳定（至少 5 个）。"""
        result = await dashboard.get_teacher_workbench(user=users["teacher"])

        cards = result["data"]["cards"]
        # 至少应包含：今日课程、区间课时、发布作业、发布公告、日常记录、点滴记录、监考任务
        assert len(cards) >= 5

        # 每个 card 应有 label / value 结构（metric 使用 label 字段）
        for card in cards:
            assert "label" in card
            assert "value" in card


class TestTeacherWorkbenchPermissions:
    """教师工作台权限测试。"""

    @pytest.mark.asyncio
    async def test_any_authenticated_user_can_access_workbench(self, users):
        """任何认证用户都可以访问自己的工作台。"""
        # teacher
        result1 = await dashboard.get_teacher_workbench(user=users["teacher"])
        assert result1["success"] is True

        # admin
        result2 = await dashboard.get_teacher_workbench(user=users["admin"])
        assert result2["success"] is True
