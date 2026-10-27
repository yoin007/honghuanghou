# -*- coding: utf-8 -*-
"""导师制（mentor system）测试：范围 token、名单分配、谈话记录、预警联动、工作量统计。"""

import asyncio
import os
import sqlite3
import sys
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import HTTPException

from models.datas_api.auth import User
from models.datas_api.moral import base as moral_base
from models.datas_api.moral import mentor_api
from models.datas_api.moral.base import (
    append_record_scope_condition,
    get_record_data_scope,
    get_teacher_mentor_student_ids,
    record_in_scope,
    target_student_in_scope,
)
from models.datas_api.moral.mentor_api import MentorAssign, MentorTalkCreate, MentorTalkUpdate


class _FakeRequest:
    """端点内 request.client 判空用的桩对象。"""

    client = None


# =============================================================================
# 内存 SQLite 环境
# =============================================================================

class MiniMoralDB:
    """内存 sqlite3 包装，模拟 MoralDatabase 接口。"""

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


MENTOR_RULES = {
    "/api/moral/mentor-roster": {
        "admin": ["all"], "jiaowu": ["all"], "xuefa": ["all"],
        "g_leader": ["managed_grades"],
    },
    "/api/moral/mentor-roster/assign": {},
    "/api/moral/mentor-roster/batch": {},
    "/api/moral/mentor-roster/delete": {},
    "/api/moral/mentor-roster/template": {},
    "/api/moral/mentor-roster/my-students": {
        "admin": ["all"], "jiaowu": ["all"], "xuefa": ["all"],
        "g_leader": ["managed_grades"], "teacher": ["mentor_students"],
    },
    "/api/moral/mentor-talks": {
        "admin": ["all"], "jiaowu": ["all"], "xuefa": ["all"],
        "g_leader": ["managed_grades"], "teacher": ["mentor_students"],
    },
    "/api/moral/mentor-talks/create": {},
    "/api/moral/mentor-talks/update": {
        "admin": ["all"], "jiaowu": ["all"], "xuefa": ["all"],
        "g_leader": ["managed_grades"], "teacher": ["own_created"],
    },
    "/api/moral/mentor-talks/delete": {
        "admin": ["all"], "jiaowu": ["all"], "xuefa": ["all"],
        "g_leader": ["managed_grades"], "teacher": ["own_created"],
    },
    "/api/moral/mentor-talks/statistics": {
        "admin": ["all"], "jiaowu": ["all"], "xuefa": ["all"],
        "g_leader": ["managed_grades"], "teacher": ["mentor_students"],
    },
    "/api/moral/mentor-talks/not-talked": {
        "admin": ["all"], "jiaowu": ["all"], "xuefa": ["all"],
        "g_leader": ["managed_grades"], "teacher": ["mentor_students"],
    },
}

MENTOR_TARGET_RULES = {
    "/api/moral/mentor-roster/assign": {
        "admin": ["all_students"], "jiaowu": ["all_students"], "xuefa": ["all_students"],
        "g_leader": ["managed_grades"],
    },
    "/api/moral/mentor-roster/batch": {
        "admin": ["all_students"], "jiaowu": ["all_students"], "xuefa": ["all_students"],
        "g_leader": ["managed_grades"],
    },
    "/api/moral/mentor-talks/create": {
        "admin": ["all_students"], "jiaowu": ["all_students"], "xuefa": ["all_students"],
        "g_leader": ["managed_grades"], "teacher": ["mentor_students"],
    },
}


def _build_test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE teacher (
            teacher_id TEXT PRIMARY KEY, name TEXT, wxid TEXT, role TEXT DEFAULT 'teacher',
            level INTEGER, is_active INTEGER DEFAULT 1, password_hash TEXT
        );
        CREATE TABLE student (
            student_id TEXT PRIMARY KEY, name TEXT, class_id INTEGER, grade_id INTEGER,
            status TEXT DEFAULT '在校'
        );
        CREATE TABLE class (
            class_id INTEGER PRIMARY KEY, class_name TEXT, grade_id INTEGER,
            is_active INTEGER DEFAULT 1, leader_ids TEXT, leader_names TEXT,
            leader_wxid TEXT, leader_name TEXT
        );
        CREATE TABLE grade (
            grade_id INTEGER PRIMARY KEY, grade_name TEXT, is_archived INTEGER DEFAULT 0,
            leader_ids TEXT, leader_names TEXT
        );
        CREATE TABLE semester (
            semester_id INTEGER PRIMARY KEY, semester_name TEXT, year_id INTEGER,
            start_date TEXT, end_date TEXT, status INTEGER DEFAULT 0
        );
        CREATE TABLE warning_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rule_name TEXT, trigger_type TEXT,
            trigger_value INTEGER, time_window_days INTEGER, notify_roles TEXT,
            is_active INTEGER DEFAULT 1, is_deleted INTEGER DEFAULT 0
        );
        CREATE TABLE warning_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, student_id TEXT NOT NULL,
            rule_id INTEGER NOT NULL, semester_id INTEGER, warning_level TEXT,
            message TEXT, is_read INTEGER DEFAULT 0, status TEXT DEFAULT 'active',
            resolved_at TEXT, resolved_reason TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE moral_config (config_key TEXT PRIMARY KEY, config_value TEXT);
        CREATE TABLE moral_operation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, operator TEXT, operator_role TEXT,
            operation TEXT, table_name TEXT, record_id INTEGER, semester_id INTEGER,
            old_data TEXT, new_data TEXT, reason TEXT, ip_address TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE api_permission_module (
            id INTEGER PRIMARY KEY AUTOINCREMENT, module_name TEXT, allowed_roles TEXT,
            min_level INTEGER, policy_mode TEXT, is_active INTEGER DEFAULT 1
        );
        CREATE TABLE api_permission_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT, api_path TEXT, api_name TEXT, api_group TEXT,
            allowed_roles TEXT, min_level INTEGER DEFAULT 0, http_method TEXT DEFAULT '*',
            match_type TEXT DEFAULT 'exact', policy_mode TEXT DEFAULT 'role_and_level',
            is_public INTEGER DEFAULT 0, enforce_backend INTEGER DEFAULT 1,
            resource_type TEXT, action_type TEXT, module_id INTEGER,
            inherit_from_module INTEGER DEFAULT 0, auth_mode TEXT DEFAULT 'jwt',
            data_scope_rules TEXT DEFAULT '{}', target_scope_rules TEXT DEFAULT '{}',
            operation_scope_rules TEXT DEFAULT '{}', is_active INTEGER DEFAULT 1
        );
    """)
    cur.execute("INSERT INTO semester (semester_id, semester_name, year_id, status) VALUES (1, '2025-2026上', 1, 1)")
    cur.execute("INSERT INTO grade (grade_id, grade_name) VALUES (1, '高一')")
    cur.execute("INSERT INTO class (class_id, class_name, grade_id) VALUES (11, '高一1班', 1)")
    cur.execute("INSERT INTO class (class_id, class_name, grade_id) VALUES (12, '高一2班', 1)")
    cur.execute("INSERT INTO student (student_id, name, class_id, grade_id) VALUES ('S001', '张小明', 11, 1)")
    cur.execute("INSERT INTO student (student_id, name, class_id, grade_id) VALUES ('S002', '李小红', 11, 1)")
    cur.execute("INSERT INTO student (student_id, name, class_id, grade_id) VALUES ('S003', '王小刚', 12, 1)")
    cur.execute("INSERT INTO teacher (teacher_id, name, wxid, role) VALUES ('T_王老师', '王老师', 'wx_wang', 'teacher')")
    cur.execute("INSERT INTO teacher (teacher_id, name, wxid, role) VALUES ('T_赵主任', '赵主任', 'wx_zhao', 'teacher/g_leader')")
    cur.execute("UPDATE grade SET leader_ids = 'T_赵主任', leader_names = '赵主任' WHERE grade_id = 1")

    # 导师制权限配置行
    roles_by_path = {
        "/api/moral/mentor-roster": ["admin", "jiaowu", "xuefa", "g_leader"],
        "/api/moral/mentor-roster/assign": ["admin", "jiaowu", "xuefa", "g_leader"],
        "/api/moral/mentor-roster/batch": ["admin", "jiaowu", "xuefa", "g_leader"],
        "/api/moral/mentor-roster/delete": ["admin", "jiaowu", "xuefa", "g_leader"],
        "/api/moral/mentor-roster/template": ["admin", "jiaowu", "xuefa", "g_leader"],
        "/api/moral/mentor-roster/my-students": ["admin", "jiaowu", "xuefa", "g_leader", "teacher"],
        "/api/moral/mentor-talks": ["admin", "jiaowu", "xuefa", "g_leader", "teacher"],
        "/api/moral/mentor-talks/create": ["admin", "jiaowu", "xuefa", "g_leader", "teacher"],
        "/api/moral/mentor-talks/update": ["admin", "jiaowu", "xuefa", "g_leader", "teacher"],
        "/api/moral/mentor-talks/delete": ["admin", "jiaowu", "xuefa", "g_leader", "teacher"],
        "/api/moral/mentor-talks/statistics": ["admin", "jiaowu", "xuefa", "g_leader", "teacher"],
        "/api/moral/mentor-talks/not-talked": ["admin", "jiaowu", "xuefa", "g_leader", "teacher"],
    }
    for path, roles in roles_by_path.items():
        cur.execute(
            """INSERT INTO api_permission_config
               (api_path, api_name, allowed_roles, min_level, data_scope_rules,
                target_scope_rules, operation_scope_rules)
               VALUES (?, ?, ?, 10, ?, ?, ?)""",
            (
                path, path,
                __import__("json").dumps(roles),
                __import__("json").dumps(MENTOR_RULES.get(path, {})),
                __import__("json").dumps(MENTOR_TARGET_RULES.get(path, {})),
                __import__("json").dumps(MENTOR_RULES.get(path, {})),
            ),
        )
    conn.commit()
    return conn


@pytest.fixture
def mentor_db():
    conn = _build_test_db()
    db = MiniMoralDB(conn)

    @contextmanager
    def fake_get_moral_db():
        yield db

    original = mentor_api.get_moral_db
    mentor_api.get_moral_db = fake_get_moral_db
    yield db
    mentor_api.get_moral_db = original
    conn.close()


@pytest.fixture
def roster_seeded(mentor_db):
    """已分配：王老师带 S001/S002，赵主任带 S003"""
    db = mentor_db
    mentor_api._ensure_schema(db)
    db.execute(
        """INSERT INTO teacher_mentor_student
           (teacher_id, teacher_name, student_id, student_name, class_id, grade_id, semester_id, assigned_by)
           VALUES ('T_王老师', '王老师', 'S001', '张小明', 11, 1, 1, 'admin')"""
    )
    db.execute(
        """INSERT INTO teacher_mentor_student
           (teacher_id, teacher_name, student_id, student_name, class_id, grade_id, semester_id, assigned_by)
           VALUES ('T_王老师', '王老师', 'S002', '李小红', 11, 1, 1, 'admin')"""
    )
    db.execute(
        """INSERT INTO teacher_mentor_student
           (teacher_id, teacher_name, student_id, student_name, class_id, grade_id, semester_id, assigned_by)
           VALUES ('T_赵主任', '赵主任', 'S003', '王小刚', 12, 1, 1, 'admin')"""
    )
    return db


# =============================================================================
# 范围 token：mentor_students
# =============================================================================

def test_mentor_scope_token_resolves_student_ids(roster_seeded):
    user = User(username="王老师", role="teacher")
    scope = get_record_data_scope(
        roster_seeded, user, "/api/moral/mentor-talks",
        all_permissions=["mentor_talk_manage"],
        own_class_permissions=[],
        own_permissions=["mentor_talk_manage"],
    )
    assert scope["can_mentor"] is True
    assert sorted(scope["mentor_student_ids"]) == ["S001", "S002"]


def test_mentor_scope_sql_condition(roster_seeded):
    user = User(username="王老师", role="teacher")
    scope = get_record_data_scope(
        roster_seeded, user, "/api/moral/mentor-talks",
        all_permissions=["mentor_talk_manage"],
        own_class_permissions=[],
        own_permissions=["mentor_talk_manage"],
    )
    conditions = []
    params = []
    append_record_scope_condition(conditions, params, scope, table_alias="mtr", username=user.username)
    assert len(conditions) == 1
    assert "mtr.student_id IN" in conditions[0]
    assert set(params) == {"S001", "S002"}


def test_mentor_scope_empty_roster_yields_no_results(mentor_db):
    user = User(username="王老师", role="teacher")
    scope = get_record_data_scope(
        mentor_db, user, "/api/moral/mentor-talks",
        all_permissions=["mentor_talk_manage"],
        own_class_permissions=[],
        own_permissions=["mentor_talk_manage"],
    )
    assert scope["can_mentor"] is True
    assert scope["mentor_student_ids"] == []
    conditions = []
    params = []
    append_record_scope_condition(conditions, params, scope, table_alias="mtr", username=user.username)
    assert conditions == ["(1 = 0)"]


def test_record_in_scope_by_mentor(roster_seeded):
    user = User(username="王老师", role="teacher")
    scope = get_record_data_scope(
        roster_seeded, user, "/api/moral/mentor-talks",
        all_permissions=["mentor_talk_manage"],
        own_class_permissions=[],
        own_permissions=["mentor_talk_manage"],
    )
    assert record_in_scope({"student_id": "S001", "recorder": "其他人"}, scope, username="王老师")
    assert not record_in_scope({"student_id": "S003", "recorder": "王老师"}, scope, username="王老师")


def test_mentor_tab_in_scope_tabs(roster_seeded):
    user = User(username="王老师", role="teacher")
    result = moral_base.get_user_data_scope_tabs(
        roster_seeded, user, "mentor-talks",
        all_permissions=["mentor_talk_manage"],
        own_class_permissions=[],
        own_permissions=["mentor_talk_manage"],
    )
    keys = [tab["key"] for tab in result["tabs"]]
    assert "mentor_students" in keys
    assert result["default_tab"] == "mentor_students"


def test_target_student_in_scope_mentor(roster_seeded):
    teacher_user = User(username="王老师", role="teacher")
    in_roster = {"student_id": "S001", "class_id": 11, "grade_id": 1}
    not_in_roster = {"student_id": "S003", "class_id": 12, "grade_id": 1}
    assert target_student_in_scope(roster_seeded, teacher_user, "/api/moral/mentor-talks/create", in_roster)
    assert not target_student_in_scope(roster_seeded, teacher_user, "/api/moral/mentor-talks/create", not_in_roster)


def test_get_teacher_mentor_student_ids_all_semesters(roster_seeded):
    user = User(username="王老师", role="teacher")
    assert sorted(get_teacher_mentor_student_ids(user, roster_seeded)) == ["S001", "S002"]
    assert sorted(get_teacher_mentor_student_ids(user, roster_seeded, semester_id=1)) == ["S001", "S002"]
    assert get_teacher_mentor_student_ids(user, roster_seeded, semester_id=99) == []


# =============================================================================
# 建表幂等
# =============================================================================

def test_ensure_schema_idempotent(mentor_db):
    db = mentor_db
    mentor_api._ensure_schema(db)
    mentor_api._ensure_schema(db)
    count = db.query_value(
        "SELECT COUNT(*) FROM warning_config WHERE trigger_type = 'mentor_talk_risk'"
    )
    assert count == 1
    tables = db.query_all(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('teacher_mentor_student','mentor_talk_record')"
    )
    assert len(tables) == 2


# =============================================================================
# 名单分配
# =============================================================================

def test_assign_then_reassign(mentor_db):
    db = mentor_db
    admin = User(username="admin", role="admin")

    result = asyncio.run(mentor_api.assign_mentor(
        MentorAssign(teacher_id="T_王老师", student_ids=["S001"]), _FakeRequest(), admin,
    ))
    assert result["data"]["success_count"] == 1
    assert result["data"]["update_count"] == 0

    # 同学期重复分配 = 更换导师
    result = asyncio.run(mentor_api.assign_mentor(
        MentorAssign(teacher_id="T_赵主任", student_ids=["S001"]), _FakeRequest(), admin,
    ))
    assert result["data"]["update_count"] == 1

    row = db.query_one(
        "SELECT teacher_id, teacher_name FROM teacher_mentor_student WHERE student_id = 'S001' AND semester_id = 1"
    )
    assert row["teacher_id"] == "T_赵主任"
    assert db.query_value(
        "SELECT COUNT(*) FROM teacher_mentor_student WHERE student_id = 'S001'"
    ) == 1


def test_assign_rejects_student_out_of_scope(roster_seeded):
    # 年级主任未管理该年级时分配被拒
    db = roster_seeded
    db.execute("UPDATE grade SET leader_ids = '', leader_names = '' WHERE grade_id = 1")
    outsider = User(username="张主任", role="g_leader")
    db.execute(
        "INSERT INTO teacher (teacher_id, name, role) VALUES ('T_张主任', '张主任', 'teacher/g_leader')"
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mentor_api.assign_mentor(
            MentorAssign(teacher_id="T_张主任", student_ids=["S001"]), _FakeRequest(), outsider,
        ))
    assert exc_info.value.status_code == 403


# =============================================================================
# 谈话记录 + 预警联动
# =============================================================================

def _talk_data(student_id="S001", risk_level="green", escalated=0, escalate_path=None):
    return MentorTalkCreate(
        student_id=student_id,
        talk_date="2026-10-15",
        talk_category="心理疏导",
        subject="考试焦虑",
        summary="学生近期考试焦虑明显",
        diagnosis="需持续关注",
        risk_level=risk_level,
        escalated=escalated,
        escalate_path=escalate_path,
    )


def test_create_talk_red_creates_error_warning(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    result = asyncio.run(mentor_api.create_mentor_talk(_talk_data(risk_level="red"), _FakeRequest(), teacher))
    assert result["success"] is True

    warnings = db.query_all("SELECT * FROM warning_log")
    assert len(warnings) == 1
    assert warnings[0]["warning_level"] == "error"
    assert warnings[0]["status"] == "active"
    assert "张小明" in warnings[0]["message"]

    # 记录快照：导师取自名单
    record = db.query_one("SELECT * FROM mentor_talk_record")
    assert record["mentor_id"] == "T_王老师"
    assert record["mentor_name"] == "王老师"
    assert record["semester_id"] == 1


def test_create_talk_yellow_creates_general_warning(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(risk_level="yellow"), _FakeRequest(), teacher))
    warnings = db.query_all("SELECT warning_level FROM warning_log")
    assert warnings == [{"warning_level": "warning"}]


def test_create_talk_green_no_warning(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(risk_level="green"), _FakeRequest(), teacher))
    assert db.query_value("SELECT COUNT(*) FROM warning_log") == 0


def test_red_warning_dedup(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(risk_level="red"), _FakeRequest(), teacher))
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(risk_level="red"), _FakeRequest(), teacher))
    assert db.query_value("SELECT COUNT(*) FROM warning_log WHERE warning_level = 'error'") == 1


def test_update_to_red_creates_warning(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    result = asyncio.run(mentor_api.create_mentor_talk(_talk_data(risk_level="green"), _FakeRequest(), teacher))
    record_id = result["data"]["record_id"]

    asyncio.run(mentor_api.update_mentor_talk(
        record_id, MentorTalkUpdate(risk_level="red"), _FakeRequest(), teacher,
    ))
    warnings = db.query_all("SELECT warning_level FROM warning_log")
    assert warnings == [{"warning_level": "error"}]


def test_teacher_cannot_create_talk_for_non_mentor_student(roster_seeded):
    teacher = User(username="王老师", role="teacher")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mentor_api.create_mentor_talk(_talk_data(student_id="S003"), _FakeRequest(), teacher))
    assert exc_info.value.status_code == 403


def test_invalid_category_rejected(roster_seeded):
    teacher = User(username="王老师", role="teacher")
    data = _talk_data()
    data.talk_category = "无效类别"
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mentor_api.create_mentor_talk(data, _FakeRequest(), teacher))
    assert exc_info.value.status_code == 400


def test_escalation_sends_notification(roster_seeded, monkeypatch):
    db = roster_seeded
    sent = []

    import sendqueue
    monkeypatch.setattr(sendqueue, "send_text", lambda content, receiver, **kw: sent.append((content, receiver, kw.get("producer"))))

    # 配置学发接收人
    db.execute("INSERT INTO moral_config (config_key, config_value) VALUES ('xuefa_notify_wxid', 'wx_xuefa')")

    teacher = User(username="王老师", role="teacher")
    asyncio.run(mentor_api.create_mentor_talk(
        _talk_data(risk_level="red", escalated=1, escalate_path="xuefa"), _FakeRequest(), teacher,
    ))

    assert len(sent) == 1
    content, receiver, producer = sent[0]
    assert receiver == "wx_xuefa"
    assert producer == "mentor_escalation"
    assert "升级" in content


def test_escalation_without_config_skips_silently(roster_seeded, monkeypatch):
    db = roster_seeded
    sent = []
    import sendqueue
    monkeypatch.setattr(sendqueue, "send_text", lambda *a, **kw: sent.append(a))

    teacher = User(username="王老师", role="teacher")
    asyncio.run(mentor_api.create_mentor_talk(
        _talk_data(risk_level="red", escalated=1, escalate_path="principal"), _FakeRequest(), teacher,
    ))
    assert sent == []
    # 记录仍然创建成功
    assert db.query_value("SELECT COUNT(*) FROM mentor_talk_record") == 1


def test_delete_talk_soft_deletes(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    result = asyncio.run(mentor_api.create_mentor_talk(_talk_data(), _FakeRequest(), teacher))
    record_id = result["data"]["record_id"]

    asyncio.run(mentor_api.delete_mentor_talk(record_id, _FakeRequest(), teacher))
    assert db.query_value(
        "SELECT is_deleted FROM mentor_talk_record WHERE record_id = ?", (record_id,)
    ) == 1


# =============================================================================
# 工作量统计
# =============================================================================

def test_statistics_coverage(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(student_id="S001", risk_level="red"), _FakeRequest(), teacher))

    admin = User(username="admin", role="admin")
    result = asyncio.run(mentor_api.get_mentor_talk_statistics(None, None, None, admin))
    items = {item["teacher_name"]: item for item in result["data"]["items"]}

    assert items["王老师"]["assigned_count"] == 2
    assert items["王老师"]["talked_count"] == 1
    assert items["王老师"]["coverage_pct"] == 50.0
    assert items["王老师"]["red_count"] == 1
    assert items["赵主任"]["assigned_count"] == 1
    assert items["赵主任"]["talked_count"] == 0


def test_not_talked_excludes_talked_students(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    asyncio.run(mentor_api.create_mentor_talk(
        MentorTalkCreate(
            student_id="S001", talk_date="2026-10-15", talk_category="学业辅导",
            summary="学业压力谈话",
            risk_level="green",
        ), _FakeRequest(), teacher,
    ))

    admin = User(username="admin", role="admin")
    result = asyncio.run(mentor_api.get_not_talked_students(None, None, "2026-10", 1, 100, admin))
    student_ids = [item["student_id"] for item in result["data"]["items"]]
    assert "S001" not in student_ids
    assert set(student_ids) == {"S002", "S003"}
    assert result["data"]["total"] == 2


def test_statistics_with_month_filter(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    # 10月有谈话、11月没有
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(student_id="S001"), _FakeRequest(), teacher))

    admin = User(username="admin", role="admin")
    result = asyncio.run(mentor_api.get_mentor_talk_statistics(None, None, "2026-10", admin))
    items = {item["teacher_name"]: item for item in result["data"]["items"]}
    assert items["王老师"]["talked_count"] == 1

    result = asyncio.run(mentor_api.get_mentor_talk_statistics(None, None, "2026-11", admin))
    items = {item["teacher_name"]: item for item in result["data"]["items"]}
    assert items["王老师"]["talked_count"] == 0
    assert items["王老师"]["assigned_count"] == 2


def test_statistics_teacher_sees_own_rows(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(student_id="S001"), _FakeRequest(), teacher))

    result = asyncio.run(mentor_api.get_mentor_talk_statistics(None, None, None, teacher))
    items = result["data"]["items"]
    # 只统计自己名下（王老师 2 人），不含赵主任
    assert {item["teacher_name"] for item in items} == {"王老师"}
    assert items[0]["talked_count"] == 1


def test_admin_scope_own_filters_by_recorder(roster_seeded):
    """管理员「我创建的」页签：只返回自己创建的记录（scope=own 不再 403）"""
    db = roster_seeded
    admin = User(username="admin", role="admin")
    other = User(username="管理员乙", role="admin")
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(student_id="S001"), _FakeRequest(), admin))
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(student_id="S002"), _FakeRequest(), other))

    # 直接调用端点时 Query 默认对象为真值，需显式传 None（生产由 FastAPI 注入解析）
    result = asyncio.run(mentor_api.get_mentor_talks(None, None, None, None, None, None, None, "own", 1, 20, admin))
    recorders = {row["recorder"] for row in result["data"]["items"]}
    assert recorders == {"admin"}


def test_not_talked_teacher_sees_own_students(roster_seeded):
    """教师查未谈话名单：只返回自己名下的学生"""
    teacher = User(username="王老师", role="teacher")
    result = asyncio.run(mentor_api.get_not_talked_students(None, None, "2026-10", 1, 100, teacher))
    student_ids = {item["student_id"] for item in result["data"]["items"]}
    assert student_ids == {"S001", "S002"}


def test_roster_list_denied_for_teacher(roster_seeded):
    """名单权限收敛后：教师访问名单列表 403（由权限配置层拒绝）"""
    from models.datas_api.moral import api_permission as ap

    teacher = User(username="王老师", role="teacher")
    decision = ap.check_configured_api_permission(
        teacher, "/api/moral/mentor-roster", "GET", allow_missing=False,
    )
    assert decision["allowed"] is False


# =============================================================================
# 谈话类别配置
# =============================================================================

def test_categories_default_five(mentor_db):
    mentor_api._ensure_schema(mentor_db)
    result = asyncio.run(mentor_api.get_talk_categories(teacher_user()))
    assert result["data"]["categories"] == ["思想引导", "学业辅导", "心理疏导", "生活指导", "生涯向导"]


def teacher_user():
    return User(username="王老师", role="teacher")


def test_categories_configurable(roster_seeded):
    db = roster_seeded
    admin = User(username="admin", role="admin")

    result = asyncio.run(mentor_api.update_talk_categories(
        mentor_api.TalkCategoriesUpdate(categories=["思想引导", "生涯规划", "宿舍生活"]),
        _FakeRequest(), admin,
    ))
    assert result["success"] is True

    # 新类别生效：旧类别被拒、新类别通过
    teacher = teacher_user()
    data = _talk_data()
    data.talk_category = "心理疏导"
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mentor_api.create_mentor_talk(data, _FakeRequest(), teacher))
    assert exc_info.value.status_code == 400

    data.talk_category = "宿舍生活"
    result = asyncio.run(mentor_api.create_mentor_talk(data, _FakeRequest(), teacher))
    assert result["success"] is True


def test_categories_update_denied_for_teacher(mentor_db):
    mentor_api._ensure_schema(mentor_db)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mentor_api.update_talk_categories(
            mentor_api.TalkCategoriesUpdate(categories=["测试"]),
            _FakeRequest(), teacher_user(),
        ))
    assert exc_info.value.status_code == 403


# =============================================================================
# 下次谈话 → 教师待办
# =============================================================================

def test_next_talk_creates_todo(roster_seeded):
    db = roster_seeded
    teacher = teacher_user()
    data = _talk_data()
    data.next_talk_date = "2026-11-05"
    result = asyncio.run(mentor_api.create_mentor_talk(data, _FakeRequest(), teacher))

    record = db.query_one("SELECT * FROM mentor_talk_record WHERE record_id = ?", (result["data"]["record_id"],))
    assert record["todo_series_id"] is not None

    series = db.query_one("SELECT * FROM teacher_todo_series WHERE id = ?", (record["todo_series_id"],))
    assert series["todo_type"] == "one_off"
    assert series["start_date"] == "2026-11-05"
    assert "张小明" in series["title"]
    assert series["is_active"] == 1

    assignee = db.query_one(
        "SELECT * FROM teacher_todo_assignee WHERE todo_series_id = ?", (series["id"],)
    )
    assert assignee["teacher_id"] == "T_王老师"

    occurrence = db.query_one(
        "SELECT * FROM teacher_todo_occurrence WHERE todo_series_id = ?", (series["id"],)
    )
    assert occurrence["occurrence_date"] == "2026-11-05"
    assert occurrence["status"] == "pending"


def test_update_next_talk_syncs_todo(roster_seeded):
    db = roster_seeded
    teacher = teacher_user()
    data = _talk_data()
    data.next_talk_date = "2026-11-05"
    result = asyncio.run(mentor_api.create_mentor_talk(data, _FakeRequest(), teacher))
    record_id = result["data"]["record_id"]

    # 改期：series 同步更新
    asyncio.run(mentor_api.update_mentor_talk(
        record_id, MentorTalkUpdate(next_talk_date="2026-11-10"), _FakeRequest(), teacher,
    ))
    record = db.query_one("SELECT * FROM mentor_talk_record WHERE record_id = ?", (record_id,))
    series = db.query_one("SELECT * FROM teacher_todo_series WHERE id = ?", (record["todo_series_id"],))
    assert series["start_date"] == "2026-11-10"
    occurrence = db.query_one(
        "SELECT * FROM teacher_todo_occurrence WHERE todo_series_id = ?", (series["id"],)
    )
    assert occurrence["occurrence_date"] == "2026-11-10"

    # 清空下次谈话：待办停用
    asyncio.run(mentor_api.update_mentor_talk(
        record_id, MentorTalkUpdate(next_talk_date=None), _FakeRequest(), teacher,
    ))
    record = db.query_one("SELECT * FROM mentor_talk_record WHERE record_id = ?", (record_id,))
    series = db.query_one("SELECT * FROM teacher_todo_series WHERE id = ?", (record["todo_series_id"],))
    assert series["is_active"] == 0


def test_no_next_talk_no_todo(roster_seeded):
    db = roster_seeded
    teacher = teacher_user()
    result = asyncio.run(mentor_api.create_mentor_talk(_talk_data(), _FakeRequest(), teacher))
    record = db.query_one("SELECT * FROM mentor_talk_record WHERE record_id = ?", (result["data"]["record_id"],))
    assert record["todo_series_id"] is None
    assert db.query_value("SELECT COUNT(*) FROM teacher_todo_series") == 0


# =============================================================================
# 导生本月状态名单
# =============================================================================

def test_student_status_talked_split(roster_seeded):
    db = roster_seeded
    teacher = teacher_user()
    asyncio.run(mentor_api.create_mentor_talk(_talk_data(student_id="S001"), _FakeRequest(), teacher))

    admin = User(username="admin", role="admin")
    result = asyncio.run(mentor_api.get_mentor_student_status(None, None, "2026-10", admin))
    items = {item["student_id"]: item for item in result["data"]["items"]}
    assert items["S001"]["talked"] is True
    assert items["S001"]["talked_count"] == 1
    assert items["S001"]["last_talk_date"] == "2026-10-15"
    assert items["S002"]["talked"] is False
    assert items["S003"]["talked"] is False

    # 教师只看自己的导生
    result = asyncio.run(mentor_api.get_mentor_student_status(None, None, "2026-10", teacher))
    student_ids = {item["student_id"] for item in result["data"]["items"]}
    assert student_ids == {"S001", "S002"}


# =============================================================================
# 谈话记录批量导入
# =============================================================================

def _batch_item(student_id="S001", **overrides):
    base = {
        "student_id": student_id, "talk_date": "2026-10-21", "talk_category": "学业辅导",
        "summary": "批量导入的谈话纪要", "risk_level": "green",
    }
    base.update(overrides)
    return base


def test_batch_import_success_and_mixed_errors(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    items = [
        _batch_item("S001"),
        _batch_item("S002", summary="第二个人的纪要"),
        _batch_item("S003"),  # 非自己导生 → 行级失败
        _batch_item("S001", talk_category="不存在的类别"),  # 类别无效 → 行级失败
    ]
    result = asyncio.run(mentor_api.batch_import_mentor_talks(
        mentor_api.MentorTalkBatchImport(items=items), _FakeRequest(), teacher,
    ))
    assert result["data"]["success_count"] == 2
    assert result["data"]["failed_count"] == 2
    reasons = {(e["row"], e["student_id"]) for e in result["data"]["errors"]}
    assert (4, "S003") in {r for r in reasons}
    # S001 只有一条（重复学号两条，一条成功一条失败）
    assert db.query_value("SELECT COUNT(*) FROM mentor_talk_record WHERE student_id = 'S001'") == 1


def test_batch_import_red_risk_triggers_warning(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    items = [_batch_item("S001", risk_level="red")]
    result = asyncio.run(mentor_api.batch_import_mentor_talks(
        mentor_api.MentorTalkBatchImport(items=items), _FakeRequest(), teacher,
    ))
    assert result["data"]["success_count"] == 1
    warnings = db.query_all("SELECT warning_level FROM warning_log")
    assert warnings == [{"warning_level": "error"}]


def test_batch_import_next_talk_creates_todo(roster_seeded):
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    items = [_batch_item("S001", need_follow_up=1, next_talk_date="2026-11-01")]
    result = asyncio.run(mentor_api.batch_import_mentor_talks(
        mentor_api.MentorTalkBatchImport(items=items), _FakeRequest(), teacher,
    ))
    assert result["data"]["success_count"] == 1
    record = db.query_one(
        "SELECT * FROM mentor_talk_record WHERE student_id = 'S001'"
    )
    assert record["todo_series_id"] is not None
    series = db.query_one("SELECT * FROM teacher_todo_series WHERE id = ?", (record["todo_series_id"],))
    assert series["start_date"] == "2026-11-01"


def test_batch_import_empty_rejected(roster_seeded):
    teacher = User(username="王老师", role="teacher")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(mentor_api.batch_import_mentor_talks(
            mentor_api.MentorTalkBatchImport(items=[]), _FakeRequest(), teacher,
        ))
    assert exc_info.value.status_code == 400


def test_talk_routes_bind_to_real_endpoints():
    """回归：装饰器必须挂在真正的端点上（曾经错挂到内部函数导致路由 422）"""
    from models.datas_api.moral.mentor_api import talk_router

    post_routes = [r for r in talk_router.routes if "POST" in getattr(r, "methods", set()) and r.path == "/mentor-talks"]
    assert len(post_routes) == 1
    assert post_routes[0].endpoint.__name__ == "create_mentor_talk"

    # 每个路由端点必须是协程函数（内部辅助函数不带装饰器）
    for r in talk_router.routes:
        import inspect
        assert inspect.iscoroutinefunction(r.endpoint), f"{r.path} 的端点不是协程: {r.endpoint.__name__}"


def test_talk_batch_name_mismatch_rejected(roster_seeded):
    """谈话批量导入：姓名与学号不匹配 → 行级失败并提示学号对应姓名"""
    db = roster_seeded
    teacher = User(username="王老师", role="teacher")
    items = [
        _batch_item("S001", student_name="张小明"),   # 正确
        _batch_item("S002", student_name="李小红 "),  # 带空格应归一后匹配
        _batch_item("S001", student_name="错误名字"),  # 不匹配
    ]
    result = asyncio.run(mentor_api.batch_import_mentor_talks(
        mentor_api.MentorTalkBatchImport(items=items), _FakeRequest(), teacher,
    ))
    assert result["data"]["success_count"] == 2
    assert result["data"]["failed_count"] == 1
    err = result["data"]["errors"][0]
    assert "不匹配" in err["reason"] and "张小明" in err["reason"]


def test_roster_batch_name_mismatch_rejected(mentor_db):
    """名单批量导入：姓名与学号不匹配 → 行级失败（上次错名静默导入的教训）"""
    db = mentor_db
    mentor_api._ensure_schema(db)
    admin = User(username="admin", role="admin")
    result = asyncio.run(mentor_api.batch_import_roster(
        mentor_api.MentorBatchImport(items=[
            mentor_api.MentorBatchItem(teacher_id="T_王老师", student_id="S001", student_name="张小明"),
            mentor_api.MentorBatchItem(teacher_id="T_王老师", student_id="S002", student_name="错误名字"),
        ]), _FakeRequest(), admin,
    ))
    assert result["data"]["success_count"] == 1
    assert len(result["data"]["errors"]) == 1
    assert "不匹配" in result["data"]["errors"][0]["reason"]
