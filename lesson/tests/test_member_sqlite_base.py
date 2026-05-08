"""Member 模块 sqlite_base 迁移回归测试。"""

from models.manage import member as member_module


def test_member_context_uses_sqlite_connection_manager(monkeypatch):
    """Member 上下文应通过 SQLiteConnectionManager 关闭连接。"""
    events = []

    class FakeCursor:
        pass

    class FakeConnection:
        row_factory = None

        def cursor(self):
            events.append("cursor")
            return FakeCursor()

    class FakeConnectionManager:
        def __init__(self, db_path, **kwargs):
            events.append(("init", db_path, kwargs))
            self.conn = FakeConnection()

        def __enter__(self):
            events.append("enter")
            return self.conn

        def __exit__(self, exc_type, exc_val, exc_tb):
            events.append(("exit", exc_type, exc_val, exc_tb))
            return False

    monkeypatch.setattr(member_module, "_get_sqlite_connection_manager", lambda: FakeConnectionManager)

    with member_module.Member() as m:
        assert m.__conn__ is not None
        assert m.__cursor__ is not None

    assert events[0][0] == "init"
    assert events[0][2]["row_factory"] is member_module.sqlite3.Row
    assert "enter" in events
    assert "cursor" in events
    assert any(isinstance(event, tuple) and event[0] == "exit" for event in events)
    assert m.__conn__ is None
    assert m.__cursor__ is None


def test_member_crud_uses_temp_moral_db(monkeypatch, tmp_path):
    """成员 CRUD 在迁移到 SQLiteConnectionManager 后仍能提交并查询。"""
    db_path = str(tmp_path / "moral.db")
    monkeypatch.setattr(member_module, "MORAL_DB", db_path)

    member = member_module.Member()

    inserted = member.insert_member(
        uuid="wx-001",
        wxid="wx-001",
        alias="测试成员",
        active=1,
        score=60,
        balance=5,
        level=2,
        model="plus",
        ai_flag=1,
        birthday="2026-01-01",
        note="initial",
    )
    assert inserted == 1

    rows = member.member_info()
    assert rows is not None
    assert len(rows) == 1
    assert rows[0][2] == "wx-001"
    assert rows[0][3] == "测试成员"

    updated = member.update_member("wx-001", score=80, note="updated")
    assert updated == 1

    row = member.member_info("wx-001")
    assert row is not None
    assert row[5] == 80
    assert row[12] == "updated"

    deleted = member.delte_member("wx-001")
    assert deleted == 1

    row = member.member_info("wx-001")
    assert row is not None
    assert row[4] == 0
