# -*- coding: utf-8 -*-
"""Dashboard common helper tests."""

from datetime import date

from models.datas_api.auth import User
from models.datas_api import dashboard_common


class FakeDB:
    def __init__(self, value=3, rows=None, fail=False):
        self.value = value
        self.rows = rows if rows is not None else [{"id": 1}]
        self.fail = fail
        self.calls = []

    def query_value(self, sql, params=None):
        self.calls.append(("query_value", sql, params))
        if self.fail:
            raise RuntimeError("query failed")
        return self.value

    def query_all(self, sql, params=None):
        self.calls.append(("query_all", sql, params))
        if self.fail:
            raise RuntimeError("query failed")
        return self.rows


def test_metric_shape_and_defaults():
    assert dashboard_common.metric("教师账号", 3) == {
        "label": "教师账号",
        "value": 3,
        "unit": "",
        "route": "",
    }
    assert dashboard_common.metric("作业", 2, "份", "/homework") == {
        "label": "作业",
        "value": 2,
        "unit": "份",
        "route": "/homework",
    }


def test_normalize_top_n_boundaries_and_invalid_values():
    assert dashboard_common.normalize_top_n(5) == 5
    assert dashboard_common.normalize_top_n("10") == 10
    assert dashboard_common.normalize_top_n(0) == 1
    assert dashboard_common.normalize_top_n(-9) == 1
    assert dashboard_common.normalize_top_n(99) == 50
    assert dashboard_common.normalize_top_n("bad") == 5


def test_date_range_inclusive_and_reverse():
    assert dashboard_common.date_range(date(2026, 5, 1), date(2026, 5, 3)) == [
        date(2026, 5, 1),
        date(2026, 5, 2),
        date(2026, 5, 3),
    ]
    assert dashboard_common.date_range(date(2026, 5, 3), date(2026, 5, 1)) == []


def test_current_week_range_can_use_injected_today():
    week = dashboard_common.current_week_range(date(2026, 5, 6))

    assert week == {"start": date(2026, 5, 4), "end": date(2026, 5, 10)}


def test_permission_helpers_for_admin_jiaowu_xuefa_and_teacher():
    admin = User(username="admin", role="admin")
    jiaowu = User(username="jiaowu", role="teacher/jiaowu")
    xuefa = User(username="xuefa", role="teacher/xuefa")
    teacher = User(username="teacher", role="teacher")

    assert dashboard_common.is_jiaowu(admin) is True
    assert dashboard_common.is_jiaowu(jiaowu) is True
    assert dashboard_common.is_jiaowu(xuefa) is False
    assert dashboard_common.is_jiaowu(teacher) is False

    assert dashboard_common.is_moral_manager(admin) is True
    assert dashboard_common.is_moral_manager(jiaowu) is True
    assert dashboard_common.is_moral_manager(xuefa) is True
    assert dashboard_common.is_moral_manager(teacher) is False


def test_safe_count_returns_int_and_preserves_params():
    db = FakeDB(value="7")

    assert dashboard_common.safe_count(db, "SELECT COUNT(*)", ("x",)) == 7
    assert db.calls == [("query_value", "SELECT COUNT(*)", ("x",))]


def test_safe_count_returns_zero_on_error_or_empty_value():
    assert dashboard_common.safe_count(FakeDB(value=None), "SELECT") == 0
    assert dashboard_common.safe_count(FakeDB(fail=True), "SELECT") == 0


def test_safe_query_all_returns_rows_and_preserves_params():
    rows = [{"name": "一班"}]
    db = FakeDB(rows=rows)

    assert dashboard_common.safe_query_all(db, "SELECT *", (1,)) == rows
    assert db.calls == [("query_all", "SELECT *", (1,))]


def test_safe_query_all_returns_empty_list_on_error_or_none():
    class NoneRowsDB:
        def query_all(self, sql, params=None):
            return None

    assert dashboard_common.safe_query_all(NoneRowsDB(), "SELECT") == []

    db = FakeDB(fail=True)
    assert dashboard_common.safe_query_all(db, "SELECT") == []
