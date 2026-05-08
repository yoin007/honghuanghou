# -*- coding: utf-8 -*-
"""Dashboard API contract tests.

Batch 18: lock the response shape before splitting dashboard.py.
"""
from contextlib import contextmanager
from datetime import date

import pytest
from fastapi import HTTPException

from models.datas_api.auth import User
from models.datas_api import dashboard
from models.datas_api import dashboard_overview
from models.datas_api import dashboard_teaching


class FakeMoralDB:
    """Small query facade matching the parts of MoralDatabase used by dashboard."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def query_value(self, sql, params=None):
        sql_text = " ".join(str(sql).split()).lower()
        if "avg(" in sql_text:
            return 82.5
        return 3

    def query_one(self, sql, params=None):
        sql_text = " ".join(str(sql).split()).lower()
        if "from class" in sql_text:
            return {"class_id": 1, "class_name": "一班", "is_active": 1}
        if "from moral_evaluation" in sql_text:
            return {
                "avg_score": 82.5,
                "min_score": 55,
                "max_score": 99,
                "evaluated_count": 2,
                "low_count": 1,
                "pass_count": 1,
            }
        if "select level from teacher" in sql_text:
            return {"level": 100}
        return {"count": 1}

    def query_all(self, sql, params=None):
        sql_text = " ".join(str(sql).split()).lower()
        if "from student where class_id" in sql_text:
            return [
                {"student_id": "S1", "name": "张三", "gender": "男", "birthday": "2010-05-10"},
                {"student_id": "S2", "name": "李四", "gender": "女", "birthday": "2010-06-10"},
            ]
        if "low" in sql_text or "total_score < 60" in sql_text:
            return [{"student_id": "S1", "name": "张三", "class_name": "一班", "total_score": 55, "level": "关注"}]
        if "group by c.class_id" in sql_text:
            return [{"class_name": "一班", "avg_score": 82.5, "student_count": 2}]
        if "left join student" in sql_text and "class_name" in sql_text:
            return [{"class_name": "一班", "student_count": 2}]
        if "daily_event_type" in sql_text:
            return [{"event_type": 1, "count": 2}, {"event_type": 2, "count": 1}]
        if "record_date" in sql_text:
            return [{"record_date": date.today().isoformat(), "count": 1}]
        return []


@contextmanager
def fake_moral_db_context():
    yield FakeMoralDB()


class FakeCursor:
    def __init__(self, kind="generic"):
        self.kind = kind
        self.rows = []
        self.one = (0,)
        self.closed = False

    def execute(self, sql, params=None):
        sql_text = " ".join(str(sql).split()).lower()
        self.rows = []
        self.one = (0,)
        if self.kind == "homework":
            self.one = (2,)
        elif self.kind == "inout":
            self.one = (1,)
        elif self.kind == "invigilation":
            self._execute_invigilation(sql_text)
        elif self.kind == "system":
            self._execute_system(sql_text)
        return self

    def _execute_invigilation(self, sql_text):
        if "from exam_project group by status" in sql_text:
            self.rows = [{"status": "draft", "count": 1}, {"status": "saved", "count": 1}]
        elif "count(*) from invigilation_slot where exam_date" in sql_text and "teacher_id" not in sql_text:
            self.one = (3,)
        elif "teacher_id is not null" in sql_text:
            self.one = (2,)
        elif "sent_status" in sql_text and "group by" in sql_text:
            self.rows = [{"sent_status": "success", "count": 2}, {"sent_status": "failed", "count": 1}]
        elif "teacher_name, count(*) as invigilation_count" in sql_text:
            self.rows = [{"teacher_name": "teacher1", "invigilation_count": 2}]
        elif "teacher_name, exam_date, start_time, count(*) as count" in sql_text:
            self.rows = []
        elif "teacher_name, exam_date, start_time" in sql_text and "group_concat" in sql_text:
            self.rows = []
        elif "sent_status in" in sql_text:
            self.rows = []
        elif "from exam_project" in sql_text:
            self.rows = [{"id": 1, "name": "期中", "status": "draft", "grade_ids": "1", "version_no": 1, "updated_at": "2026-05-05"}]
        else:
            self.rows = []

    def _execute_system(self, sql_text):
        if "sqlite_master" in sql_text and "scheduled_tasks" in sql_text:
            self.rows = [{"name": "scheduled_tasks"}]
            self.one = {"name": "scheduled_tasks"}
        elif "from teacher where identity_type" in sql_text and "count(*) as count" in sql_text:
            self.one = {"count": 3}
        elif "group by role" in sql_text:
            self.rows = [{"role": "teacher", "count": 2}, {"role": "admin", "count": 1}]
        elif "count(*) as total" in sql_text and "from teacher" in sql_text:
            self.one = {"total": 3, "teacher": 2, "admin": 1, "other": 0}
        elif "from api_permission_config" in sql_text:
            self.rows = []
        elif "from moral_operation_log" in sql_text and "group by operation" in sql_text:
            self.rows = [{"operation": "UPDATE", "count": 1}]
        elif "from moral_operation_log" in sql_text:
            self.rows = []
        elif "from scheduled_tasks" in sql_text:
            self.one = {"total": 0, "running": 0, "failed": 0, "success": 0}
        else:
            self.rows = []
            self.one = (0,)

    def fetchone(self):
        return self.one

    def fetchall(self):
        return self.rows

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, kind="generic"):
        self.kind = kind
        self.row_factory = None
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def cursor(self):
        return FakeCursor(self.kind)

    def execute(self, sql, params=None):
        cursor = FakeCursor(self.kind)
        return cursor.execute(sql, params)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class FakeScheduleService:
    def replace_subject_teacher(self, df, teacher_flag=False):
        return df.copy()

    def split_subjects(self, value):
        return [str(value)] if value else []

    def format_schedule(self, df, week_flag, replace_flag=True, ignore=False):
        return df


class FakeLesson:
    lesson_dir = "/tmp/nonexistent-dashboard-contract"
    week_change = 0

    def __init__(self):
        self.schedule_service = FakeScheduleService()

    def get_cache_data(self, key):
        import pandas as pd

        if key == "time_table":
            return pd.DataFrame([{"order": "1", "label": "第一节", "show_time": "00:00-23:59"}])
        if key == "class_template":
            return pd.DataFrame([{"class_name": "一班"}])
        if key == "teacher_template":
            return pd.DataFrame([{"name": "teacher1", "subject": "语文", "course": "语文"}])
        if key == "today_schedule":
            return pd.DataFrame([{"order": "1", "一班": "语文"}])
        if key == "week_info":
            return [(None, "20260504"), (None, "20260511")]
        if key in {"current_schedule", "next_schedule"}:
            return pd.DataFrame([{"order": "1", "weekday": 1, "一班": "teacher1"}])
        return None

    def load_excel_file(self, path):
        import pandas as pd

        return pd.DataFrame([{"order": "1", "weekday": 1, "一班": "teacher1"}])


@pytest.fixture
def users():
    return {
        "admin": User(username="admin", role="admin"),
        "jiaowu": User(username="jiaowu", role="jiaowu"),
        "moral": User(username="xuefa", role="xuefa"),
        "cleader": User(username="cleader", role="cleader"),
        "teacher": User(username="teacher1", role="teacher"),
    }


@pytest.fixture(autouse=True)
def isolate_dashboard(monkeypatch):
    monkeypatch.setattr(dashboard, "get_moral_db", fake_moral_db_context)
    monkeypatch.setattr(dashboard_overview, "get_moral_db", fake_moral_db_context)
    monkeypatch.setattr(dashboard, "Lesson", FakeLesson)
    monkeypatch.setattr(dashboard_teaching, "Lesson", FakeLesson)
    monkeypatch.setattr(dashboard, "_get_homework_db", lambda: FakeConnection("homework"))
    monkeypatch.setattr(dashboard, "_get_inout_db", lambda: FakeConnection("inout"))
    monkeypatch.setattr(dashboard, "_get_invigilation_db", lambda: FakeConnection("invigilation"))
    monkeypatch.setattr(dashboard, "get_teacher_class_id", lambda user, db: 1)
    monkeypatch.setattr(dashboard_overview, "get_teacher_class_id", lambda user, db: 1)
    monkeypatch.setattr(dashboard.os.path, "exists", lambda path: True)
    monkeypatch.setattr(dashboard.os.path, "getsize", lambda path: 2048)

    # Mock teaching helper functions to avoid real database calls
    fake_workload = {
        "rows": [{"teacher_name": "张老师", "lesson_count": 5}],
        "covered_dates": ["2026-05-05"],
        "source_files": ["test.xlsx"],
        "lessons": [],
        "message": "test",
    }
    monkeypatch.setattr(dashboard, "_teacher_lesson_counts", lambda s, e: fake_workload)
    monkeypatch.setattr(dashboard, "_teacher_lesson_counts_from_files", lambda s, e, **kw: fake_workload)
    monkeypatch.setattr(dashboard, "_current_course_snapshot", lambda: {
        "current_period": "第一节",
        "current_period_order": "1",
        "current_time_range": "08:00-08:45",
        "active_class_count": 1,
        "current_classes": [{"class_name": "一班", "subject": "语文"}],
        "all_periods": [{"order": "1", "label": "第一节", "time_range": "08:00-08:45"}],
    })

    def fake_connect(path, *args, **kwargs):
        path_text = str(path)
        if "invigilation" in path_text:
            return FakeConnection("invigilation")
        if "task" in path_text:
            return FakeConnection("system")
        return FakeConnection("system")

    monkeypatch.setattr(dashboard.sqlite3, "connect", fake_connect)


def assert_success_data(result):
    assert result["success"] is True
    assert "data" in result
    assert isinstance(result["data"], dict)
    return result["data"]


@pytest.mark.asyncio
async def test_overview_contract(users):
    data = assert_success_data(await dashboard.get_dashboard_overview(user=users["admin"]))

    for key in ["cards", "modules", "alerts", "updated_at"]:
        assert key in data


@pytest.mark.asyncio
async def test_moral_summary_contract(users):
    data = assert_success_data(await dashboard.get_moral_dashboard_summary(top_n=5, user=users["moral"]))

    for key in ["cards", "charts", "tables", "insights", "top_n", "updated_at"]:
        assert key in data
    for key in ["score_distribution", "daily_event_mix", "daily_record_trend", "class_score_rank", "leave_by_class"]:
        assert key in data["charts"]
    for key in ["low_students", "leave_students"]:
        assert key in data["tables"]


@pytest.mark.asyncio
async def test_teaching_summary_contract(users):
    data = assert_success_data(await dashboard.get_teaching_dashboard_summary(top_n=5, user=users["jiaowu"]))

    for key in [
        "cards",
        "charts",
        "tables",
        "current_course",
        "range",
        "covered_dates",
        "source_files",
        "top_n",
        "message",
        "updated_at",
    ]:
        assert key in data
    for key in ["teacher_workload_rank", "class_size_rank", "resource_mix", "file_upload_status"]:
        assert key in data["charts"]
    # Batch50: teacher_workload 已删除，合并到 teacher_workload_rank
    for key in ["teacher_workload_rank", "file_upload_top_users", "pending_file_list", "recent_file_list"]:
        assert key in data["tables"]
        assert key in data["tables"]


@pytest.mark.asyncio
async def test_class_summary_contract(users):
    data = assert_success_data(await dashboard.get_class_dashboard_summary(class_id=1, top_n=5, user=users["cleader"]))

    for key in ["cards", "charts", "tables", "class_info", "top_n", "updated_at"]:
        assert key in data
    for key in ["gender_mix", "score_band"]:
        assert key in data["charts"]
    for key in ["low_students", "birthday_this_month", "birthday_this_week"]:
        assert key in data["tables"]


@pytest.mark.asyncio
async def test_teacher_workbench_contract(users):
    data = assert_success_data(await dashboard.get_teacher_workbench(user=users["teacher"]))

    for key in ["cards", "tables", "workload", "range", "updated_at"]:
        assert key in data
    for key in ["today_lessons", "invigilation_tasks", "workload_lessons"]:
        assert key in data["tables"]
    assert "lessons" not in data["workload"]


@pytest.mark.asyncio
async def test_invigilation_summary_contract(users):
    data = assert_success_data(await dashboard.get_invigilation_dashboard_summary(top_n=5, user=users["jiaowu"]))

    for key in ["cards", "charts", "tables", "top_n", "updated_at"]:
        assert key in data
    for key in ["project_status", "notification_status", "teacher_workload_rank"]:
        assert key in data["charts"]
    for key in [
        "unarranged_slots",
        "conflict_slots",
        "notification_failed",
        "recent_projects",
        "teacher_workload_rank",
    ]:
        assert key in data["tables"]


@pytest.mark.asyncio
async def test_system_summary_contract(users):
    data = assert_success_data(await dashboard.get_system_dashboard_summary(user=users["admin"]))

    for key in ["cards", "charts", "tables", "task_stats", "updated_at"]:
        assert key in data
    for key in ["role_distribution", "operation_stats", "teacher_identity"]:
        assert key in data["charts"]
    for key in ["db_files", "api_permission_risks", "recent_operations"]:
        assert key in data["tables"]


@pytest.mark.asyncio
async def test_teacher_cannot_access_moral_summary(users):
    with pytest.raises(HTTPException) as exc_info:
        await dashboard.get_moral_dashboard_summary(user=users["teacher"])

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_teacher_cannot_access_teaching_summary(users):
    with pytest.raises(HTTPException) as exc_info:
        await dashboard.get_teaching_dashboard_summary(user=users["teacher"])

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_access_system_summary(users):
    with pytest.raises(HTTPException) as exc_info:
        await dashboard.get_system_dashboard_summary(user=users["jiaowu"])

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_cleader_without_class_cannot_access_class_summary(monkeypatch, users):
    monkeypatch.setattr(dashboard, "get_teacher_class_id", lambda user, db: None)

    with pytest.raises(HTTPException) as exc_info:
        await dashboard.get_class_dashboard_summary(class_id=None, user=users["cleader"])

    assert exc_info.value.status_code == 403
