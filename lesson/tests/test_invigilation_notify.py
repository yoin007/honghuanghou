# -*- coding: utf-8 -*-
"""监考通知聚合发送：同老师多场变更合并为一条消息，队列条数=老师人数而非变更条数。"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from models.datas_api import invigilation
from models.datas_api.auth import User


@pytest.fixture
def notify_env(monkeypatch):
    """独立内存 invigilation.db（含 notify 所需的四张表），patch send_text 捕获消息。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE exam_project (
            id INTEGER PRIMARY KEY, name TEXT, grade_ids TEXT,
            version_no INTEGER DEFAULT 0, status TEXT,
            first_saved_at TEXT, notified_at TEXT, updated_at TEXT
        );
        CREATE TABLE invigilation_slot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER, grade_id INTEGER, grade_name TEXT,
            exam_date TEXT, start_time TEXT, end_time TEXT, subject TEXT,
            room_name TEXT, room_order INTEGER,
            teacher_id TEXT, teacher_name TEXT, teacher_wxid TEXT,
            assistant_teacher_id TEXT, assistant_teacher_name TEXT, assistant_teacher_wxid TEXT,
            source TEXT, updated_at TEXT
        );
        CREATE TABLE invigilation_snapshot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER, version_no INTEGER, slots_json TEXT, created_at TEXT
        );
        CREATE TABLE invigilation_notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER, version_no INTEGER,
            teacher_name TEXT, teacher_id TEXT, receiver TEXT,
            message TEXT, change_type TEXT, slots_json TEXT,
            sent_status TEXT, error_message TEXT, sent_at TEXT, queue_row_id INTEGER
        );
    """)
    conn.execute(
        "INSERT INTO exam_project (id, name, grade_ids, version_no) VALUES (1, '期中考试', '[1]', 0)"
    )
    conn.commit()

    sent = []
    monkeypatch.setattr(invigilation, "send_text", lambda content, wxid, producer="x": sent.append((content, wxid)) or 100)
    monkeypatch.setattr(invigilation, "get_invigilation_db", lambda: conn)

    def _slot(teacher_id, teacher_name, wxid, date, start, room, subject="数学"):
        conn.execute(
            """INSERT INTO invigilation_slot
               (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject,
                room_name, room_order, teacher_id, teacher_name, teacher_wxid, source)
               VALUES (1, 1, '高一', ?, ?, '16:00:00', ?, ?, 0, ?, ?, ?, 'manual')""",
            (date, start, subject, room, teacher_id, teacher_name, wxid),
        )
        conn.commit()

    yield conn, sent, _slot
    conn.close()


def _notify(**kwargs):
    from models.datas_api.invigilation import NotifyRequestV2
    return invigilation.send_notifications(
        1, user=User(username="admin", role="admin"),
        request=NotifyRequestV2(**kwargs),
    )


def test_added_aggregated_per_teacher(notify_env):
    conn, sent, slot = notify_env
    slot("T_A", "甲老师", "wx_a", "2026-11-20", "08:00:00", "301")
    slot("T_A", "甲老师", "wx_a", "2026-11-20", "10:00:00", "302")
    slot("T_B", "乙老师", "wx_b", "2026-11-20", "08:00:00", "303")
    # 甲老师兼副监一场：消息里要体现主/副监差异
    conn.execute(
        """INSERT INTO invigilation_slot
           (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject,
            room_name, room_order, teacher_id, teacher_name, teacher_wxid,
            assistant_teacher_id, assistant_teacher_name, assistant_teacher_wxid, source)
           VALUES (1, 1, '高一', '2026-11-21', '14:00:00', '16:00:00', '英语', '305', 0,
                   'T_X', '戊老师', 'wx_x', 'T_A', '甲老师', 'wx_a', 'manual')"""
    )
    conn.commit()

    result = _notify(notify_added=True)

    assert result["success"] is True
    assert result["data"]["added"] == 5  # 5 条变更项（新场次主监+副监各一条）
    assert len(sent) == 3  # 甲/乙/戊各一条（甲老师主监两场+副监一场合并为一条，角色标注区分）
    jia = [c for c, w in sent if w == "wx_a"][0]
    assert "1. 【主监】2026-11-20 08:00:00-16:00:00 数学 高一 301" in jia
    assert "2. 【主监】2026-11-20 10:00:00-16:00:00 数学 高一 302" in jia
    assert "3. 【副监】2026-11-21 14:00:00-16:00:00 英语 高一 305" in jia
    wu = [c for c, w in sent if w == "wx_x"][0]
    assert "【主监】2026-11-21 14:00:00-16:00:00 英语 高一 305" in wu
    # 日志条数与消息条数一致
    assert conn.execute("SELECT COUNT(*) FROM invigilation_notification_log").fetchone()[0] == 3


def test_removed_aggregated_per_teacher_and_reason(notify_env):
    conn, sent, slot = notify_env
    slot("T_A", "甲老师", "wx_a", "2026-11-20", "08:00:00", "301")
    slot("T_A", "甲老师", "wx_a", "2026-11-20", "10:00:00", "302")
    # 先通知一次建立快照
    _notify(notify_added=True)
    sent.clear()

    # 全部取消
    conn.execute("DELETE FROM invigilation_slot")
    conn.commit()
    result = _notify(notify_added=False, notify_removed=True)

    assert result["data"]["removed"] == 2
    assert len(sent) == 1  # 同老师同原因合并为一条
    content = sent[0][0]
    assert "【取消监考】" in content
    assert "1. 【主监】2026-11-20 08:00:00" in content
    assert "2. 【主监】2026-11-20 10:00:00" in content
    assert "原因：场次取消" in content


def test_swap_message_shows_roles(notify_env):
    conn, sent, slot = notify_env
    slot("T_A", "甲老师", "wx_a", "2026-11-20", "08:00:00", "301")
    slot("T_B", "乙老师", "wx_b", "2026-11-20", "08:00:00", "302")
    _notify(notify_added=True)
    sent.clear()

    # 换监：甲↔乙（各自仍是主监角色）
    conn.execute("UPDATE invigilation_slot SET teacher_id = 'T_B', teacher_name = '乙老师', teacher_wxid = 'wx_b' WHERE room_name = '301'")
    conn.execute("UPDATE invigilation_slot SET teacher_id = 'T_A', teacher_name = '甲老师', teacher_wxid = 'wx_a' WHERE room_name = '302'")
    conn.commit()

    result = _notify(notify_added=False, notify_removed=False, notify_changed=True)

    assert result["data"]["swapped"] == 1
    assert len(sent) == 2  # 双方各一条
    jia = [c for c, w in sent if w == "wx_a"][0]
    assert "【监考调整】" in jia
    assert "原安排：【主监】2026-11-20 08:00:00-16:00:00 数学 高一 301" in jia
    assert "新安排：【主监】2026-11-20 08:00:00-16:00:00 数学 高一 302" in jia
    yi = [c for c, w in sent if w == "wx_b"][0]
    assert "原安排：【主监】2026-11-20 08:00:00-16:00:00 数学 高一 302" in yi
    assert "新安排：【主监】2026-11-20 08:00:00-16:00:00 数学 高一 301" in yi


def test_grade_filter_scopes_notify(notify_env):
    conn, sent, slot = notify_env
    slot("T_A", "甲老师", "wx_a", "2026-11-20", "08:00:00", "301")          # grade_id 默认 1
    conn.execute(
        """INSERT INTO invigilation_slot
           (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject,
            room_name, room_order, teacher_id, teacher_name, teacher_wxid, source)
           VALUES (1, 2, '高二', '2026-11-20', '08:00:00', '10:00:00', '数学', '201', 0, 'T_C', '丙老师', 'wx_c', 'manual')"""
    )
    conn.commit()

    result = _notify(notify_added=True, grade_ids=[1])  # 只通知高一年级

    assert result["data"]["added"] == 1  # 高二的场次被过滤
    assert [w for _, w in sent] == ["wx_a"]


def test_reminder_branch_still_works(notify_env):
    conn, sent, slot = notify_env
    slot("T_A", "甲老师", "wx_a", "2026-11-20", "08:00:00", "301")
    _notify(notify_added=True)
    sent.clear()

    # 无变化 → reminder 聚合（原有行为保持）
    result = _notify(notify_added=False, notify_removed=False, notify_changed=False, notify_reminder=True)
    assert result["data"]["reminded"] == 1
    assert len(sent) == 1
    assert "【监考提醒】" in sent[0][0]
