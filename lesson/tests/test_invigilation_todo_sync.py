# -*- coding: utf-8 -*-
"""监考安排联动教师待办：对账增/删/改/复活、考前10分钟与间隔5分钟提醒参数、到点自动关闭不标逾期。"""

import asyncio
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from models.datas_api import invigilation
from models.datas_api.auth import User
from models.datas_api.moral import base as moral_base
from models.datas_api.moral import scheduler as moral_scheduler


class MiniMoralDB:
    """内存 sqlite3 包装，模拟 MoralDatabase 接口（与 test_mentor_system 同模式）。"""

    def __init__(self, conn):
        self.conn = conn

    def execute(self, query, params=None):
        cur = self.conn.execute(query, params or ())
        self.conn.commit()
        return cur.rowcount

    def executemany(self, query, params_list):
        cur = self.conn.executemany(query, params_list)
        self.conn.commit()
        return cur.rowcount

    def query_one(self, query, params=None):
        cur = self.conn.execute(query, params or ())
        row = cur.fetchone()
        return dict(row) if row else None

    def query_all(self, query, params=None):
        cur = self.conn.execute(query, params or ())
        return [dict(row) for row in cur.fetchall()]

    def query_value(self, query, params=None):
        row = self.query_one(query, params)
        if not row:
            return None
        return list(row.values())[0]

    def lastrowid(self):
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()


CREATE_INV_SLOT = """
    CREATE TABLE invigilation_slot (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER, grade_id INTEGER, grade_name TEXT,
        exam_date TEXT, start_time TEXT, end_time TEXT, subject TEXT,
        room_name TEXT, room_order INTEGER,
        teacher_id TEXT, teacher_name TEXT, teacher_wxid TEXT,
        assistant_teacher_id TEXT, assistant_teacher_name TEXT, assistant_teacher_wxid TEXT,
        source TEXT, updated_at TEXT
    )
"""


def _future(days=3, hour=14, minute=0):
    dt = datetime.now() + timedelta(days=days)
    return dt.strftime("%Y-%m-%d"), f"{hour:02d}:{minute:02d}"


def _insert_slot(conn, project_id=1, exam_date=None, start="14:00:00", end="16:00:00",
                 teacher_id="T_A", teacher_name="甲老师", assistant_id=None,
                 assistant_name=None, subject="数学", room="301", grade_id=1,
                 grade_name="高一"):
    exam_date = exam_date or _future()[0]
    conn.execute(
        """INSERT INTO invigilation_slot
           (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject,
            room_name, room_order, teacher_id, teacher_name, teacher_wxid,
            assistant_teacher_id, assistant_teacher_name, assistant_teacher_wxid, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, 'wx_a', ?, ?, 'wx_b', 'manual')""",
        (project_id, grade_id, grade_name, exam_date, start, end, subject,
         room, teacher_id, teacher_name, assistant_id, assistant_name),
    )
    conn.commit()


@pytest.fixture
def sync_env(monkeypatch):
    """moral db（内存）+ invigilation db（内存），分别 patch 进被测模块。"""
    moral_conn = sqlite3.connect(":memory:")
    moral_conn.row_factory = sqlite3.Row
    moral_conn.execute(
        """CREATE TABLE teacher (
            teacher_id TEXT PRIMARY KEY, name TEXT, wxid TEXT,
            is_active INTEGER DEFAULT 1, identity_type TEXT DEFAULT 'teacher'
        )"""
    )
    moral_conn.commit()
    moral_db = MiniMoralDB(moral_conn)

    inv_conn = sqlite3.connect(":memory:")
    inv_conn.row_factory = sqlite3.Row
    inv_conn.executescript(CREATE_INV_SLOT)
    inv_conn.commit()

    @contextmanager
    def fake_moral_db():
        yield moral_db

    monkeypatch.setattr(moral_base, "get_moral_db", fake_moral_db)
    monkeypatch.setattr(invigilation, "get_invigilation_db", lambda: inv_conn)

    yield moral_db, inv_conn
    moral_conn.close()
    inv_conn.close()


def _series_for(db, teacher_id):
    return db.query_all(
        """SELECT s.* FROM teacher_todo_series s
           JOIN invigilation_todo_link l ON l.todo_series_id = s.id
           WHERE l.teacher_id = ?""",
        (teacher_id,),
    )


# =============================================================================
# 对账：创建 / 幂等 / 取消 / 换人 / 复活 / 过去场次 / 删除项目
# =============================================================================

def test_sync_creates_todos_with_remind_params(sync_env):
    moral_db, inv_conn = sync_env
    _insert_slot(inv_conn, assistant_id="T_B", assistant_name="乙老师")

    invigilation._sync_project_todos(1)

    series = moral_db.query_all("SELECT * FROM teacher_todo_series")
    assert len(series) == 2  # 主监 + 副监各一条
    for s in series:
        assert s["todo_type"] == "one_off"
        assert s["remind_before_minutes"] == 30
        assert s["reminder_interval"] == 5
        assert s["reminder_count"] == 2
        assert s["notify_assignees"] == 1
        assert s["notify_creator"] == 0
        assert s["wechat_notify_enabled"] == 1
        assert "监考" in s["title"]
        assert "时间：" in (s["description"] or "")
    assert moral_db.query_value("SELECT COUNT(*) FROM invigilation_todo_link") == 2
    assert moral_db.query_value("SELECT COUNT(*) FROM teacher_todo_assignee") == 2

    occ = moral_db.query_one("SELECT * FROM teacher_todo_occurrence LIMIT 1")
    exam_date, _ = _future()
    assert occ["occurrence_date"] == exam_date
    assert occ["scheduled_at"] == f"{exam_date} 14:00:00"
    assert occ["status"] == "pending"


def test_sync_is_idempotent(sync_env):
    moral_db, inv_conn = sync_env
    _insert_slot(inv_conn)

    invigilation._sync_project_todos(1)
    invigilation._sync_project_todos(1)  # 覆盖式保存后重复对账

    assert moral_db.query_value("SELECT COUNT(*) FROM teacher_todo_series") == 1
    assert moral_db.query_value("SELECT COUNT(*) FROM invigilation_todo_link") == 1


def test_sync_deactivates_cancelled_slot(sync_env):
    moral_db, inv_conn = sync_env
    _insert_slot(inv_conn, room="301", teacher_id="T_A")
    _insert_slot(inv_conn, room="302", teacher_id="T_C", teacher_name="丙老师")
    invigilation._sync_project_todos(1)

    # 重存时 301 场被取消：清空后只留 302
    inv_conn.execute("DELETE FROM invigilation_slot WHERE room_name = '301'")
    inv_conn.commit()
    invigilation._sync_project_todos(1)

    assert _series_for(moral_db, "T_A")[0]["is_active"] == 0
    assert _series_for(moral_db, "T_C")[0]["is_active"] == 1


def test_sync_swapped_teacher_gets_new_todo(sync_env):
    moral_db, inv_conn = sync_env
    _insert_slot(inv_conn, teacher_id="T_A")
    invigilation._sync_project_todos(1)

    # 换监：同一场次换人
    inv_conn.execute(
        "UPDATE invigilation_slot SET teacher_id = 'T_D', teacher_name = '丁老师' WHERE id = 1"
    )
    inv_conn.commit()
    invigilation._sync_project_todos(1)

    assert _series_for(moral_db, "T_A")[0]["is_active"] == 0
    new_series = _series_for(moral_db, "T_D")
    assert len(new_series) == 1 and new_series[0]["is_active"] == 1


def test_sync_skips_past_slots(sync_env):
    moral_db, inv_conn = sync_env
    _insert_slot(inv_conn, exam_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"))

    invigilation._sync_project_todos(1)

    assert moral_db.query_value("SELECT COUNT(*) FROM teacher_todo_series") == 0


def test_sync_reactivates_revived_slot(sync_env):
    moral_db, inv_conn = sync_env
    _insert_slot(inv_conn)
    invigilation._sync_project_todos(1)
    invigilation._deactivate_project_todos(1)
    assert _series_for(moral_db, "T_A")[0]["is_active"] == 0

    invigilation._sync_project_todos(1)  # 场次仍在（如删除项目后恢复/误停用）

    assert _series_for(moral_db, "T_A")[0]["is_active"] == 1


def test_deactivate_project_todos(sync_env):
    moral_db, inv_conn = sync_env
    _insert_slot(inv_conn, assistant_id="T_B", assistant_name="乙老师")
    invigilation._sync_project_todos(1)

    invigilation._deactivate_project_todos(1)

    assert moral_db.query_value(
        "SELECT COUNT(*) FROM teacher_todo_series WHERE is_active = 0"
    ) == 2


# =============================================================================
# 端点挂载：保存后自动触发同步（钩子接线验证）
# =============================================================================

def test_save_endpoint_triggers_sync(sync_env, monkeypatch):
    moral_db, inv_conn = sync_env
    inv_conn.execute(
        "CREATE TABLE exam_project (id INTEGER PRIMARY KEY, grade_ids TEXT, status TEXT, first_saved_at TEXT, updated_at TEXT)"
    )
    inv_conn.execute("INSERT INTO exam_project (id, grade_ids) VALUES (1, '[1]')")
    inv_conn.commit()

    calls = []
    monkeypatch.setattr(invigilation, "_sync_project_todos", lambda pid: calls.append(pid))

    class _FakeMoralCtx:
        def __enter__(self):
            return moral_db

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(invigilation, "SQLiteMoralDatabase", lambda: _FakeMoralCtx())

    from models.datas_api.invigilation import InvigilationSlotsBatch, InvigilationSlotCreate
    batch = InvigilationSlotsBatch(slots=[InvigilationSlotCreate(
        grade_id=1, grade_name="高一", exam_date=_future()[0],
        start_time="14:00:00", end_time="16:00:00",
        subject="数学", room_name="301", teacher_id="T_A", teacher_name="甲老师",
    )])

    result = asyncio.run(invigilation.save_invigilation_slots(1, batch, User(username="admin", role="admin")))

    assert result["success"] is True
    assert calls == [1]


# =============================================================================
# 调度语义：到点自动关闭、清历史逾期、未来待办不受影响
# =============================================================================

def _seed_series_with_occurrence(db, scheduled_at, is_overdue=0):
    db.execute(
        """INSERT INTO teacher_todo_series
           (title, creator_teacher_id, todo_type, start_date, time_of_day,
            remind_before_minutes, reminder_interval, reminder_count,
            notify_creator, notify_assignees, is_active)
           VALUES ('测试待办', 'T_X', 'one_off', ?, '08:00', 10, 5, 2, 0, 0, 1)""",
        (scheduled_at[:10],),
    )
    series_id = db.lastrowid()
    db.execute(
        """INSERT INTO teacher_todo_occurrence
           (todo_series_id, occurrence_date, scheduled_at, status, is_overdue)
           VALUES (?, ?, ?, 'pending', ?)""",
        (series_id, scheduled_at[:10], scheduled_at, is_overdue),
    )
    return series_id


@pytest.fixture
def scheduler_env(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    db = MiniMoralDB(conn)

    @contextmanager
    def fake_moral_db():
        yield db

    monkeypatch.setattr(moral_base, "get_moral_db", fake_moral_db)
    sent = []
    monkeypatch.setattr("sendqueue.send_text", lambda *a, **k: sent.append(a))
    yield db, sent
    conn.close()


def test_scheduler_auto_closes_past_occurrence(scheduler_env):
    db, _ = scheduler_env
    from models.datas_api.teacher_todo import ensure_teacher_todo_schema
    ensure_teacher_todo_schema(db)
    past = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    _seed_series_with_occurrence(db, past)

    moral_scheduler.teacher_todo_reminder_task()

    occ = db.query_one("SELECT * FROM teacher_todo_occurrence")
    assert occ["status"] == "completed"
    assert occ["completed_by"] == "system"
    assert occ["is_overdue"] == 0


def test_scheduler_clears_historical_overdue(scheduler_env):
    db, _ = scheduler_env
    from models.datas_api.teacher_todo import ensure_teacher_todo_schema
    ensure_teacher_todo_schema(db)
    past = (datetime.now() - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    _seed_series_with_occurrence(db, past, is_overdue=1)

    moral_scheduler.teacher_todo_reminder_task()

    occ = db.query_one("SELECT * FROM teacher_todo_occurrence")
    assert occ["status"] == "completed"
    assert occ["is_overdue"] == 0


def test_scheduler_keeps_future_occurrence_untouched(scheduler_env):
    db, sent = scheduler_env
    from models.datas_api.teacher_todo import ensure_teacher_todo_schema
    ensure_teacher_todo_schema(db)
    future = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    _seed_series_with_occurrence(db, future)

    moral_scheduler.teacher_todo_reminder_task()

    occ = db.query_one("SELECT * FROM teacher_todo_occurrence")
    assert occ["status"] == "pending"
    assert occ["is_overdue"] == 0
    assert sent == []  # 未到提醒时间，不发消息
