# -*- coding: utf-8 -*-
"""Post-handoff regression tests for newly added admin and trend APIs."""

from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from models.datas_api.auth import User
from models.datas_api import dashboard_trend
from models.datas_api.moral import base as moral_base
from models.datas_api.moral import database_admin


class _FakeTrendDB:
    def __init__(self, query_one_rows):
        self._query_one_rows = list(query_one_rows)

    def query_one(self, *_args, **_kwargs):
        if self._query_one_rows:
            return self._query_one_rows.pop(0)
        return None

    def query_all(self, *_args, **_kwargs):
        return []


@contextmanager
def _trend_db_context(rows):
    yield _FakeTrendDB(rows)


def test_database_admin_rejects_path_traversal_and_non_clearable_tables():
    with pytest.raises(HTTPException) as traversal_exc:
        database_admin._resolve_database_path("../moral.db")
    assert traversal_exc.value.status_code == 400

    with pytest.raises(HTTPException) as table_exc:
        database_admin._ensure_clearable_table("moral.db", "teacher")
    assert table_exc.value.status_code == 400

    database_admin._ensure_clearable_table("moral.db", "student_daily_record")


@pytest.mark.asyncio
async def test_grade_trend_blocks_other_grade_for_grade_leader(monkeypatch):
    monkeypatch.setattr(
        dashboard_trend,
        "get_moral_db",
        lambda: _trend_db_context([
            {"grade_id": 2, "grade_name": "高二年级"},
        ]),
    )
    monkeypatch.setattr(moral_base, "is_grade_leader", lambda *_args, **_kwargs: False)

    with pytest.raises(HTTPException) as exc_info:
        await dashboard_trend.get_grade_score_trend(
            "2",
            user=User(username="grade-leader", role="g_leader"),
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_student_trend_uses_student_grade_for_grade_leader_scope(monkeypatch):
    monkeypatch.setattr(
        dashboard_trend,
        "get_moral_db",
        lambda: _trend_db_context([
            {"student_id": "S-1", "name": "学生甲", "class_id": 20, "grade_id": 2},
        ]),
    )
    monkeypatch.setattr(moral_base, "is_grade_leader", lambda *_args, **_kwargs: False)

    with pytest.raises(HTTPException) as exc_info:
        await dashboard_trend.get_student_score_trend(
            "S-1",
            user=User(username="grade-leader", role="g_leader"),
        )

    assert exc_info.value.status_code == 403
