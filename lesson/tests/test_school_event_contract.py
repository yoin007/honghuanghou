# -*- coding: utf-8 -*-
"""校级事件接口契约测试。"""

import os
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.datas_api.auth import User
from models.datas_api.moral import school_event


class FakeSchoolRecordDB:
    def __init__(self):
        self.executed = []

    def query_one(self, sql, params=None):
        if "FROM school_event_type" in sql:
            return {"event_id": 1, "score": 5}
        if "FROM student_school_record" in sql and "proof = ?" in sql:
            raise AssertionError("校级事件创建不应按 proof 做全局唯一校验")
        return None

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def lastrowid(self):
        return 1001


@pytest.mark.asyncio
async def test_create_school_record_allows_reused_evidence(monkeypatch):
    """证明材料可以被不同校级事件记录复用。"""
    fake_db = FakeSchoolRecordDB()

    @contextmanager
    def fake_moral_db():
        yield fake_db

    monkeypatch.setattr(school_event, "get_moral_db", fake_moral_db)
    monkeypatch.setattr(school_event, "_has_scoped_any_permission", lambda *args, **kwargs: True)
    monkeypatch.setattr(school_event, "get_current_semester", lambda db: {"semester_id": 20})
    monkeypatch.setattr(
        school_event,
        "get_student_class_snapshot",
        lambda db, student_id: {"student_id": student_id, "class_id": 2, "grade_id": 1},
    )
    monkeypatch.setattr(school_event, "target_student_in_scope", lambda *args, **kwargs: True)
    monkeypatch.setattr(school_event, "_refresh_school_record_evaluation", lambda *args, **kwargs: None)
    monkeypatch.setattr(school_event, "log_operation", lambda *args, **kwargs: None)

    request = MagicMock()
    request.client.host = "127.0.0.1"
    user = User(username="学发老师", role="xuefa")
    record = school_event.SchoolRecordCreate(
        student_id="20241005",
        event_id=1,
        description="校级表彰",
        evidence="同一份证明材料",
    )

    result = await school_event.create_school_record(record, request, user)

    assert result["success"] is True
    assert fake_db.executed
