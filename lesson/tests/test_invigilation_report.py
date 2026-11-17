# -*- coding: utf-8 -*-
"""监考工作量报表：主副监权重折算 + 脏数据口径一致性 + 权重配置端点。"""

import io
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from openpyxl import load_workbook

from models.datas_api import invigilation
from models.datas_api.auth import User


@pytest.fixture
def report_env(monkeypatch):
    """独立内存 invigilation.db（含权重配置表），patch 连接函数。"""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE exam_project (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE invigilation_slot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER, grade_id INTEGER, grade_name TEXT,
            exam_date TEXT, start_time TEXT, end_time TEXT, subject TEXT,
            room_name TEXT, room_order INTEGER,
            teacher_id TEXT, teacher_name TEXT,
            assistant_teacher_id TEXT, assistant_teacher_name TEXT
        );
        CREATE TABLE invigilation_config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO exam_project (id, name) VALUES (1, '期中考试');
    """)
    conn.commit()
    monkeypatch.setattr(invigilation, "get_invigilation_db", lambda: conn)

    def _slot(teacher_id, teacher_name, date="2026-11-20", start="08:00:00", end="10:00:00",
              assistant_id=None, assistant_name=None):
        conn.execute(
            """INSERT INTO invigilation_slot
               (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject,
                room_name, room_order, teacher_id, teacher_name,
                assistant_teacher_id, assistant_teacher_name)
               VALUES (1, 1, '高一', ?, ?, ?, '数学', '301', 0, ?, ?, ?, ?)""",
            (date, start, end, teacher_id, teacher_name, assistant_id, assistant_name),
        )
        conn.commit()

    def _set_weight(key, value):
        conn.execute(
            "INSERT OR REPLACE INTO invigilation_config (key, value) VALUES (?, ?)",
            (key, str(value)),
        )
        conn.commit()

    yield conn, _slot, _set_weight
    conn.close()


def _run_report():
    import asyncio

    resp = invigilation.export_workload_report(1, user=User(username="admin", role="admin"))

    async def _collect():
        return b"".join([chunk async for chunk in resp.body_iterator])

    data = asyncio.run(_collect())
    wb = load_workbook(io.BytesIO(data))
    return wb


def _sheet_rows(wb, name):
    ws = wb[name]
    rows = list(ws.iter_rows(values_only=True))
    header = list(rows[0])
    return header, [dict(zip(header, r)) for r in rows[1:]]


def test_default_weights_count_full(report_env):
    """默认权重 1.0：主副监各算整场、整时长（120 分钟），主副场次分开。"""
    conn, slot, _ = report_env
    slot("T_A", "甲老师", assistant_id="T_B", assistant_name="乙老师")

    wb = _run_report()
    header, rows = _sheet_rows(wb, '工作量汇总')
    assert '主监场次' in header and '副监场次' in header
    by_name = {r['教师姓名']: r for r in rows}
    assert by_name['甲老师']['主监场次'] == 1
    assert by_name['甲老师']['副监场次'] == 0
    assert by_name['甲老师']['监考场次(折算)'] == 1
    assert by_name['甲老师']['监考时长(分钟,折算)'] == 120
    assert by_name['乙老师']['主监场次'] == 0
    assert by_name['乙老师']['副监场次'] == 1
    assert by_name['乙老师']['监考场次(折算)'] == 1
    assert by_name['乙老师']['监考时长(分钟,折算)'] == 120


def test_assistant_weight_halves_count_and_duration(report_env):
    """副监权重 0.5：副监原始场次仍计 1，折算 0.5、时长 60；主监不受影响。"""
    conn, slot, set_weight = report_env
    set_weight('assistant_weight', 0.5)
    slot("T_A", "甲老师", assistant_id="T_B", assistant_name="乙老师")
    slot("T_B", "乙老师")  # 乙老师另有一场主监

    wb = _run_report()
    _, rows = _sheet_rows(wb, '工作量汇总')
    by_name = {r['教师姓名']: r for r in rows}
    assert by_name['甲老师']['主监场次'] == 1
    assert by_name['甲老师']['监考时长(分钟,折算)'] == 120
    assert by_name['乙老师']['主监场次'] == 1
    assert by_name['乙老师']['副监场次'] == 1
    assert by_name['乙老师']['监考场次(折算)'] == 1.5  # 主监 1 + 副监 0.5
    assert by_name['乙老师']['监考时长(分钟,折算)'] == 180  # 120 + 120*0.5


def test_zero_weight_still_counts_slots(report_env):
    """权重为 0：原始场次照常统计，只有折算列归零。"""
    conn, slot, set_weight = report_env
    set_weight('assistant_weight', 0)
    slot("T_A", "甲老师", assistant_id="T_B", assistant_name="乙老师")

    wb = _run_report()
    _, rows = _sheet_rows(wb, '工作量汇总')
    by_name = {r['教师姓名']: r for r in rows}
    assert by_name['乙老师']['副监场次'] == 1          # 原始场次不受权重影响
    assert by_name['乙老师']['监考场次(折算)'] == 0    # 折算归零
    assert by_name['乙老师']['监考时长(分钟,折算)'] == 0
    # 概览里的副监总场次也照常统计
    _, overview = _sheet_rows(wb, '统计概览')
    items = {r['统计项']: r['数值'] for r in overview}
    assert items['副监总场次'] == 1


def test_dirty_time_row_excluded_from_both_metrics(report_env):
    """时间格式非法的行：场次和时长同时排除，两边口径一致。"""
    conn, slot, _ = report_env
    slot("T_A", "甲老师")                       # 正常：1 场 120 分钟
    slot("T_A", "甲老师", start="abc", end="10:00:00")  # 脏数据：不计场、不计时

    wb = _run_report()
    _, rows = _sheet_rows(wb, '工作量汇总')
    by_name = {r['教师姓名']: r for r in rows}
    assert by_name['甲老师']['监考场次(折算)'] == 1
    assert by_name['甲老师']['监考时长(分钟,折算)'] == 120


def test_overview_shows_weights(report_env):
    """统计概览体现当前权重与主副总场次，且总人次按折算。"""
    conn, slot, set_weight = report_env
    set_weight('primary_weight', 1)
    set_weight('assistant_weight', 0.5)
    slot("T_A", "甲老师", assistant_id="T_B", assistant_name="乙老师")

    wb = _run_report()
    _, rows = _sheet_rows(wb, '统计概览')
    items = {r['统计项']: r['数值'] for r in rows}
    assert items['主监权重'] == 1
    assert items['副监权重'] == 0.5
    assert items['主监总场次'] == 1
    assert items['副监总场次'] == 1
    assert items['总监考人次(折算)'] == 1.5


# =============================================================================
# 权重配置端点
# =============================================================================

def test_weight_config_roundtrip(report_env):
    conn, _, _ = report_env
    user = User(username="jw", role="jiaowu")

    updated = invigilation.update_weight_config(
        invigilation.WeightConfigUpdate(primary_weight=1, assistant_weight=0.5), user=user)
    assert updated["success"] is True

    got = invigilation.get_weight_config(user=user)
    assert got["data"] == {"primary_weight": 1.0, "assistant_weight": 0.5}

    # 报表读取到的是最新权重
    conn.execute(
        """INSERT INTO invigilation_slot
           (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject,
            room_name, room_order, teacher_id, teacher_name)
           VALUES (1, 1, '高一', '2026-11-20', '08:00:00', '10:00:00', '数学', '301', 0, 'T_A', '甲老师')"""
    )
    conn.commit()
    wb = _run_report()
    _, rows = _sheet_rows(wb, '统计概览')
    items = {r['统计项']: r['数值'] for r in rows}
    assert items['副监权重'] == 0.5


def test_weight_config_rejects_out_of_range(report_env):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        invigilation.update_weight_config(
            invigilation.WeightConfigUpdate(primary_weight=1, assistant_weight=11),
            user=User(username="admin", role="admin"),
        )
    assert exc.value.status_code == 400


def test_weight_reader_falls_back_on_bad_value(report_env):
    """库里的值非法（越界/非数字）时回落默认 1.0。"""
    conn, _, set_weight = report_env
    set_weight('primary_weight', 'abc')
    set_weight('assistant_weight', 99)
    assert invigilation.get_invigilation_weights() == (1.0, 1.0)
