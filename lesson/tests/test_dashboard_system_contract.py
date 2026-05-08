# -*- coding: utf-8 -*-
"""Dashboard System contract tests.

Batch25: lock the response shape for system dashboard endpoint.
"""
import pytest
from fastapi import HTTPException

from models.datas_api.auth import User
from models.datas_api import dashboard


class FakeMoralDB:
    """Fake moral DB for system dashboard tests."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def query_value(self, sql, params=None):
        return 0

    def query_one(self, sql, params=None):
        # 根据不同 SQL 返回不同 fake 数据
        sql_text = " ".join(str(sql).split()).lower()
        if "from teacher where identity_type" in sql_text and "count(*) as count" in sql_text:
            return {"count": 3}
        elif "count(*) as total" in sql_text and "from teacher" in sql_text:
            return {"total": 3, "teacher": 2, "admin": 1, "other": 0}
        return {"count": 0}

    def query_all(self, sql, params=None):
        sql_text = " ".join(str(sql).split()).lower()
        if "group by role" in sql_text:
            return [{"role": "teacher", "count": 2}, {"role": "admin", "count": 1}]
        if "from api_permission_config" in sql_text:
            return []
        if "from moral_operation_log" in sql_text and "group by operation" in sql_text:
            return [{"operation": "UPDATE", "count": 1}]
        return []


class FakeSystemConnection:
    """Fake system DB connection (moral/task) for tests."""

    def __init__(self, kind="system"):
        self.kind = kind
        self.row_factory = None
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def cursor(self):
        return FakeSystemCursor(self.kind)

    def execute(self, sql, params=None):
        cursor = FakeSystemCursor(self.kind)
        return cursor.execute(sql, params)

    def close(self):
        self.closed = True


class FakeSystemCursor:
    def __init__(self, kind="system"):
        self.kind = kind
        self.rows = []
        self.one = {"count": 0}

    def execute(self, sql, params=None):
        sql_text = " ".join(str(sql).split()).lower()
        self.rows = []
        self.one = {"count": 0}

        # 处理 teacher 表查询
        if "from teacher where identity_type" in sql_text:
            self.one = {"count": 3}
        elif "group by role" in sql_text:
            self.rows = [{"role": "teacher", "count": 2}]
        elif "count(*) as total" in sql_text and "from teacher" in sql_text:
            self.one = {"total": 3, "teacher": 2, "admin": 1, "other": 0}
        # 处理 api_permission_config 查询
        elif "from api_permission_config" in sql_text:
            self.rows = []
        # 处理 moral_operation_log 查询
        elif "from moral_operation_log" in sql_text and "group by operation" in sql_text:
            self.rows = [{"operation": "UPDATE", "count": 1}]
        # 处理 task.db scheduled_tasks 查询（关键：匹配正确 SQL）
        elif "select" in sql_text and "total" in sql_text and "running" in sql_text and "from scheduled_tasks" in sql_text:
            self.one = {"total": 0, "running": 0, "failed": 0, "success": 0}
        # 处理 sqlite_master 查询
        elif "sqlite_master" in sql_text:
            self.rows = [{"name": "scheduled_tasks"}]
            self.one = {"name": "scheduled_tasks"}
        else:
            self.one = {"count": 0}
            self.rows = []

        return self

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.rows

    def close(self):
        pass


@pytest.fixture
def users():
    return {
        "admin": User(username="admin", role="admin"),
        "teacher": User(username="teacher1", role="teacher"),
        "jiaowu": User(username="jiaowu", role="jiaowu"),
    }


@pytest.fixture(autouse=True)
def isolate_system_dashboard(monkeypatch):
    """隔离 system dashboard 测试，避免访问真实数据库。"""

    # Mock get_moral_db
    monkeypatch.setattr(dashboard, "get_moral_db", lambda: FakeMoralDB())

    # Mock sqlite_base connection factory（禁止真实连接）
    def fake_get_sqlite_connection(path, *args, **kwargs):
        path_text = str(path)
        if "moral" in path_text or "task" in path_text:
            return FakeSystemConnection("system")
        return FakeSystemConnection("generic")

    monkeypatch.setattr(
        "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
        fake_get_sqlite_connection,
    )

    def forbidden_direct_connect(*args, **kwargs):
        raise AssertionError("system dashboard should use sqlite_base, not sqlite3.connect")

    monkeypatch.setattr(dashboard.sqlite3, "connect", forbidden_direct_connect)

    # Mock os.path.exists 和 os.path.getsize
    monkeypatch.setattr(dashboard.os.path, "exists", lambda path: True)
    monkeypatch.setattr(dashboard.os.path, "getsize", lambda path: 2048)


class TestSystemDashboardContract:
    """锁定系统运维驾驶舱返回结构。"""

    @pytest.mark.asyncio
    async def test_system_dashboard_returns_stable_structure(self, users):
        """get_system_dashboard_summary 返回 cards/charts/tables/updated_at 等稳定结构。"""
        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        assert result["success"] is True
        assert "data" in result
        data = result["data"]

        # 必须包含的字段
        for key in ["cards", "charts", "tables", "task_stats", "updated_at"]:
            assert key in data

        # charts 必须包含的字段
        for key in ["role_distribution", "operation_stats", "teacher_identity"]:
            assert key in data["charts"]

        # tables 必须包含的字段
        for key in ["db_files", "api_permission_risks", "recent_operations"]:
            assert key in data["tables"]

        # cards 应为列表
        assert isinstance(data["cards"], list)

        # task_stats 应包含字段（scheduled_tasks 统计）
        assert "total" in data["task_stats"]
        assert "running" in data["task_stats"]
        assert "failed" in data["task_stats"]
        assert "success" in data["task_stats"]

    @pytest.mark.asyncio
    async def test_admin_can_access_system_dashboard(self, users):
        """admin 可访问系统运维驾驶舱。"""
        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        assert result["success"] is True
        assert "data" in result

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access_system_dashboard(self, users):
        """非 admin 无权限访问。"""
        with pytest.raises(HTTPException) as exc_info:
            await dashboard.get_system_dashboard_summary(user=users["teacher"])

        assert exc_info.value.status_code == 403

        with pytest.raises(HTTPException) as exc_info:
            await dashboard.get_system_dashboard_summary(user=users["jiaowu"])

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_system_dashboard_uses_fake_connections(self, monkeypatch, users):
        """system dashboard 使用 sqlite_base fake connection，不能访问真实数据库。"""

        sqlite_base_called = []

        def tracking_get_sqlite_connection(path, *args, **kwargs):
            sqlite_base_called.append({"path": str(path), "kwargs": kwargs})
            return FakeSystemConnection("system")

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            tracking_get_sqlite_connection,
        )

        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        # 应调用 sqlite_base，并由 helper 统一设置 Row row_factory。
        assert len(sqlite_base_called) > 0
        assert all(item["kwargs"].get("row_factory") is dashboard.sqlite3.Row for item in sqlite_base_called)
        # 应成功返回数据
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_system_dashboard_cards_count_matches_expectation(self, users):
        """system dashboard cards 数量应稳定。"""
        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        cards = result["data"]["cards"]
        # 至少应包含：教师总数、用户统计、任务统计等
        assert len(cards) >= 2

        # 每个 card 应有 label / value 结构（metric 使用 label 字段）
        for card in cards:
            assert "label" in card
            assert "value" in card

    @pytest.mark.asyncio
    async def test_system_dashboard_db_files_table_structure(self, users):
        """db_files 表格结构应稳定。"""
        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        db_files = result["data"]["tables"]["db_files"]
        assert isinstance(db_files, list)

        # 每个 db_file 应包含 name / exists / size_kb / tables 字段
        for db_file in db_files:
            assert "name" in db_file
            assert "exists" in db_file
            assert "size_kb" in db_file
            assert "tables" in db_file

    @pytest.mark.asyncio
    async def test_system_dashboard_moral_db_failure_returns_graceful_defaults(self, monkeypatch, users):
        """moral.db 查询异常时返回优雅默认值。"""

        class FailingMoralDB:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def query_value(self, sql, params=None):
                raise Exception("moral DB query failed")

            def query_one(self, sql, params=None):
                raise Exception("moral DB query failed")

            def query_all(self, sql, params=None):
                raise Exception("moral DB query failed")

        monkeypatch.setattr(dashboard, "get_moral_db", lambda: FailingMoralDB())

        # 即使 moral.db 查询失败，sqlite 直连统计仍应返回数据
        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        # 主接口应该仍然返回成功（异常被吞掉）
        assert result["success"] is True
        # 各字段应有默认值（不为 None）
        assert result["data"]["tables"]["db_files"] is not None
        # recent_operations 在异常时可能为空列表，不为 None
        assert result["data"]["tables"]["recent_operations"] is not None


class TestSystemDashboardPermissions:
    """系统运维驾驶舱权限测试。"""

    @pytest.mark.asyncio
    async def test_only_admin_role_can_access(self, users):
        """只有 admin role 可以访问。"""
        # admin 可访问
        result = await dashboard.get_system_dashboard_summary(user=users["admin"])
        assert result["success"] is True

        # teacher 不可访问
        with pytest.raises(HTTPException) as exc_info:
            await dashboard.get_system_dashboard_summary(user=users["teacher"])
        assert exc_info.value.status_code == 403

        # jiaowu 不可访问
        with pytest.raises(HTTPException) as exc_info:
            await dashboard.get_system_dashboard_summary(user=users["jiaowu"])
        assert exc_info.value.status_code == 403


class TestSystemDashboardSQLiteBaseUsage:
    """验证 system dashboard 使用 sqlite_base。"""

    @pytest.mark.asyncio
    async def test_get_db_stats_uses_sqlite_base(self, monkeypatch, users):
        """_get_db_stats 使用 sqlite_base。"""

        called = []

        def fake_get_sqlite_connection(db_path, **kwargs):
            called.append(("sqlite_base", str(db_path)))
            # 返回 fake connection
            return FakeSystemConnection("system")

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        # 应通过 sqlite_base 获取连接
        assert ("sqlite_base" in [c[0] for c in called])

    @pytest.mark.asyncio
    async def test_moral_db_system_stats_uses_sqlite_base(self, monkeypatch, users):
        """moral.db system 统计使用 sqlite_base 或统一 helper。"""

        called = []

        class TrackingFakeConnection(FakeSystemConnection):
            def __init__(self, db_path):
                super().__init__("system")
                called.append(("connection", str(db_path)))

        def fake_get_sqlite_connection(db_path, **kwargs):
            return TrackingFakeConnection(db_path)

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        # 应成功返回数据
        assert result["success"] is True
        assert any("moral.db" in item[1] for item in called)
        assert any("task.db" in item[1] for item in called)

    @pytest.mark.asyncio
    async def test_connection_closes_on_normal_path(self, monkeypatch, users):
        """正常路径连接会关闭。"""

        closed = []

        class NormalFakeConnection(FakeSystemConnection):
            def close(self):
                closed.append(True)
                super().close()

        def fake_get_sqlite_connection(db_path, **kwargs):
            return NormalFakeConnection()

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        # 主接口应该成功返回
        assert result["success"] is True
        # 正常路径连接也应关闭（_get_db_stats, moral.db, task.db）
        assert len(closed) >= 1

    @pytest.mark.asyncio
    async def test_exception_path_gracefully_handled(self, monkeypatch, users):
        """异常路径下主接口仍能成功返回，且已打开连接会关闭。"""

        closed = []

        class FailingFakeConnection:
            def __init__(self):
                self.row_factory = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                closed.append("__exit__")
                return False

            def cursor(self):
                raise Exception("query failed")

            def close(self):
                closed.append("close")

        def fake_get_sqlite_connection(db_path, **kwargs):
            return FailingFakeConnection()

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        # 主接口应该仍然返回成功（异常被吞掉）
        assert result["success"] is True
        # 各字段应有默认值
        assert result["data"]["tables"]["db_files"] is not None
        assert result["data"]["task_stats"] is not None
        # 异常发生在 cursor() 后，连接已进入 with，wrapper 必须负责释放。
        assert "close" in closed

    @pytest.mark.asyncio
    async def test_system_dashboard_contract_stable_after_migration(self, users):
        """system dashboard 契约迁移后仍稳定。"""
        result = await dashboard.get_system_dashboard_summary(user=users["admin"])

        # 必须包含的字段
        for key in ["cards", "charts", "tables", "task_stats", "updated_at"]:
            assert key in result["data"]

        # tables 必须包含的字段
        for key in ["db_files", "api_permission_risks", "recent_operations"]:
            assert key in result["data"]["tables"]

        # task_stats 必须包含的字段
        for key in ["total", "running", "failed", "success"]:
            assert key in result["data"]["task_stats"]
