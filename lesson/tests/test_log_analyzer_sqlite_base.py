"""log_analyzer sqlite_base 迁移回归测试。"""

from models.manage import log_analyzer


def test_analyze_inactive_members_uses_connection_manager(monkeypatch):
    """潜水成员分析应通过 SQLiteConnectionManager 关闭连接。"""
    events = []

    class FakeCursor:
        def execute(self, sql, params=None):
            events.append(("execute", sql, params))
            return self

        def fetchall(self):
            return [("wx-001", "张三"), ("wx-002", "李四")]

    class FakeConnection:
        def cursor(self):
            events.append("cursor")
            return FakeCursor()

    class FakeConnectionManager:
        def __init__(self, db_path, **kwargs):
            events.append(("init", db_path, kwargs))

        def __enter__(self):
            events.append("enter")
            return FakeConnection()

        def __exit__(self, exc_type, exc_val, exc_tb):
            events.append(("exit", exc_type, exc_val, exc_tb))
            return False

    monkeypatch.setattr(
        "models.datas_api.repositories.sqlite_base.SQLiteConnectionManager",
        FakeConnectionManager,
    )

    result = log_analyzer.analyze_inactive_members("room-001", {"wx-001": 3})

    assert result["total"] == 2
    assert result["active_count"] == 1
    assert result["inactive_count"] == 1
    assert result["inactive_list"] == [{"id": "wx-002", "name": "李四"}]
    assert events[0][0] == "init"
    assert "enter" in events
    assert "cursor" in events
    assert any(isinstance(event, tuple) and event[0] == "exit" for event in events)
