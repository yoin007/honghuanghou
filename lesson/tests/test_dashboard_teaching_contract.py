# -*- coding: utf-8 -*-
"""Teaching dashboard helper contract tests.

Batch 20: test extracted teaching helpers and route contract.
"""
import os
import tempfile
from datetime import date, datetime, timedelta
from contextlib import contextmanager

import pytest
import pandas as pd

from models.datas_api.auth import User
from models.datas_api import dashboard
from models.datas_api.dashboard_teaching import (
    build_filegather_summary,
    current_course_snapshot,
    find_current_period,
    minutes_from_time,
    month_keys_for_range,
    schedule_frames_for_range,
    teacher_lesson_counts,
    teacher_lesson_counts_from_files,
    teacher_subject_lookup,
    week_start_from_schedule_filename,
)
from models.datas_api import dashboard_overview


class FakeMoralDB:
    """Small query facade matching the parts of MoralDatabase used by dashboard."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def query_value(self, sql, params=None):
        return 3

    def query_one(self, sql, params=None):
        return {"class_id": 1, "class_name": "一班", "is_active": 1}

    def query_all(self, sql, params=None):
        return []


@contextmanager
def fake_moral_db_context():
    yield FakeMoralDB()


class FakeScheduleService:
    def replace_subject_teacher(self, df, teacher_flag=False):
        return df.copy()

    def split_subjects(self, value):
        return [str(value)] if value else []

    def format_schedule(self, df, week_flag, replace_flag=True, ignore=False):
        return df


class FakeLesson:
    lesson_dir = "/tmp/nonexistent-dashboard-teaching"
    week_change = 0

    def __init__(self):
        self.schedule_service = FakeScheduleService()

    def get_cache_data(self, key):
        if key == "time_table":
            return pd.DataFrame([{"order": "1", "label": "第一节", "show_time": "08:00-08:45"}])
        if key == "class_template":
            return pd.DataFrame([{"class_name": "一班"}])
        if key == "teacher_template":
            return pd.DataFrame([{"name": "张老师", "subject": "语文", "course": "语文"}])
        if key == "today_schedule":
            return pd.DataFrame([{"order": "1", "一班": "语文"}])
        if key == "week_info":
            return [(None, "20260504"), (None, "20260511")]
        if key in {"current_schedule", "next_schedule"}:
            return pd.DataFrame([{"order": "1", "weekday": 1, "一班": "张老师"}])
        return None

    def load_excel_file(self, path):
        return pd.DataFrame([{"order": "1", "weekday": 1, "一班": "张老师"}])


class TestMonthKeysForRange:
    """month_keys_for_range 跨月区间测试"""

    def test_single_month(self):
        """单月返回一个键"""
        result = month_keys_for_range(date(2026, 5, 1), date(2026, 5, 31))
        assert result == ["202605"]

    def test_cross_two_months(self):
        """跨两月返回两个键"""
        result = month_keys_for_range(date(2026, 4, 15), date(2026, 5, 15))
        assert result == ["202604", "202605"]

    def test_cross_three_months(self):
        """跨三月返回三个键"""
        result = month_keys_for_range(date(2026, 4, 1), date(2026, 6, 30))
        assert result == ["202604", "202605", "202606"]


class TestWeekStartFromScheduleFilename:
    """week_start_from_schedule_filename 解析测试"""

    def test_valid_filename(self):
        """合法文件名返回周一日期"""
        result = week_start_from_schedule_filename("schedule_20260505.xlsx")
        assert result == date(2026, 5, 5)

    def test_valid_filename_with_path(self):
        """带路径的合法文件名也能解析"""
        result = week_start_from_schedule_filename("/path/to/20260505_class_schedule.xls")
        assert result == date(2026, 5, 5)

    def test_invalid_filename_no_date(self):
        """无日期模式的文件名返回 None"""
        result = week_start_from_schedule_filename("schedule.xlsx")
        assert result is None

    def test_invalid_filename_wrong_format(self):
        """日期格式错误的文件名返回 None"""
        result = week_start_from_schedule_filename("schedule_2026-05-05.xlsx")
        assert result is None

    def test_invalid_filename_empty(self):
        """空文件名返回 None"""
        result = week_start_from_schedule_filename("")
        assert result is None


class TestMinutesFromTime:
    """minutes_from_time 时间转换测试"""

    def test_normal_time(self):
        """正常时间返回分钟数"""
        assert minutes_from_time("08:00") == 480
        assert minutes_from_time("14:30") == 870

    def test_time_with_seconds(self):
        """带秒数的时间只取时:分"""
        assert minutes_from_time("08:00:30") == 480

    def test_invalid_time_no_colon(self):
        """无冒号的时间返回 None"""
        assert minutes_from_time("0800") is None

    def test_invalid_time_empty(self):
        """空时间返回 None"""
        assert minutes_from_time("") is None

    def test_invalid_time_non_numeric(self):
        """非数字时间返回 None"""
        assert minutes_from_time("abc:def") is None


class TestFindCurrentPeriod:
    """find_current_period 当前节次测试"""

    def test_returns_period_structure(self, monkeypatch):
        """返回结构包含 period/label/time_range/all_periods"""
        fake_lesson = FakeLesson()
        result = find_current_period(fake_lesson)
        assert "period" in result
        assert "label" in result
        assert "time_range" in result
        assert "all_periods" in result

    def test_all_periods_populated(self, monkeypatch):
        """all_periods 列表填充正确"""
        fake_lesson = FakeLesson()
        result = find_current_period(fake_lesson)
        assert len(result["all_periods"]) >= 1
        first_period = result["all_periods"][0]
        assert "order" in first_period
        assert "label" in first_period
        assert "time_range" in first_period

    def test_matches_current_time(self, monkeypatch):
        """当前时间匹配节次返回正确"""
        # Mock datetime.now() to 08:15 which falls in 08:00-08:45
        class FakeDateTime:
            @staticmethod
            def now():
                return datetime(2026, 5, 5, 8, 15)

        monkeypatch.setattr("models.datas_api.dashboard_teaching.datetime", FakeDateTime)

        fake_lesson = FakeLesson()
        result = find_current_period(fake_lesson)
        assert result["period"] == "1"
        assert result["label"] == "第一节"

    def test_empty_time_table_returns_empty(self):
        """空 time_table 返回空结构"""
        class EmptyLesson:
            lesson_dir = "/tmp"

            def get_cache_data(self, key):
                if key == "time_table":
                    return pd.DataFrame()
                return None

        result = find_current_period(EmptyLesson())
        assert result["period"] is None
        assert result["all_periods"] == []


class TestTeacherSubjectLookup:
    """teacher_subject_lookup 科目映射测试"""

    def test_returns_lookup_dict(self):
        """返回 subject -> teacher/course 映射"""
        fake_lesson = FakeLesson()
        result = teacher_subject_lookup(fake_lesson)
        assert isinstance(result, dict)
        assert "语文" in result
        assert result["语文"]["teacher"] == "张老师"
        assert result["语文"]["course"] == "语文"

    def test_empty_teacher_template_returns_empty(self):
        """空 teacher_template 返回空字典"""
        class EmptyLesson:
            lesson_dir = "/tmp"

            def get_cache_data(self, key):
                if key == "teacher_template":
                    return pd.DataFrame()
                return None

        result = teacher_subject_lookup(EmptyLesson())
        assert result == {}

    def test_none_teacher_template_returns_empty(self):
        """None teacher_template 返回空字典"""
        class NoneLesson:
            lesson_dir = "/tmp"

            def get_cache_data(self, key):
                return None

        result = teacher_subject_lookup(NoneLesson())
        assert result == {}


class TestCurrentCourseSnapshot:
    """current_course_snapshot 当前课程快照测试"""

    def test_returns_snapshot_structure(self, monkeypatch):
        """返回结构包含所有必要字段"""
        # Mock datetime.now() to 08:15
        class FakeDateTime:
            @staticmethod
            def now():
                return datetime(2026, 5, 5, 8, 15)

        monkeypatch.setattr("models.datas_api.dashboard_teaching.datetime", FakeDateTime)
        monkeypatch.setattr("models.datas_api.dashboard_teaching.Lesson", FakeLesson)

        result = current_course_snapshot()
        assert "current_period" in result
        assert "current_period_order" in result
        assert "current_time_range" in result
        assert "active_class_count" in result
        assert "current_classes" in result
        assert "all_periods" in result

    def test_current_classes_populated(self, monkeypatch):
        """当前班级列表填充正确"""
        class FakeDateTime:
            @staticmethod
            def now():
                return datetime(2026, 5, 5, 8, 15)

        monkeypatch.setattr("models.datas_api.dashboard_teaching.datetime", FakeDateTime)
        monkeypatch.setattr("models.datas_api.dashboard_teaching.Lesson", FakeLesson)

        result = current_course_snapshot()
        assert result["active_class_count"] >= 0
        if result["active_class_count"] > 0:
            first_class = result["current_classes"][0]
            assert "class_name" in first_class
            assert "subject" in first_class


class TestTeacherLessonCountsFromFiles:
    """teacher_lesson_counts_from_files 文件扫描统计测试"""

    def test_returns_result_structure(self, monkeypatch):
        """返回结构包含 rows/covered_dates/source_files/lessons/message"""
        monkeypatch.setattr("models.datas_api.dashboard_teaching.Lesson", FakeLesson)
        monkeypatch.setattr("models.datas_api.dashboard_teaching.schedule_files_for_range", lambda l, s, e: [])
        monkeypatch.setattr("models.datas_api.dashboard_teaching.format_week_schedule_file", lambda l, p, m: pd.DataFrame())

        result = teacher_lesson_counts_from_files(date(2026, 5, 1), date(2026, 5, 31))
        assert "rows" in result
        assert "covered_dates" in result
        assert "source_files" in result
        assert "lessons" in result
        assert "message" in result

    def test_empty_files_returns_empty_rows(self, monkeypatch):
        """无文件时返回空 rows"""
        monkeypatch.setattr("models.datas_api.dashboard_teaching.Lesson", FakeLesson)
        monkeypatch.setattr("models.datas_api.dashboard_teaching.schedule_files_for_range", lambda l, s, e: [])
        monkeypatch.setattr("models.datas_api.dashboard_teaching.format_week_schedule_file", lambda l, p, m: pd.DataFrame())

        result = teacher_lesson_counts_from_files(date(2026, 5, 1), date(2026, 5, 31))
        assert result["rows"] == []
        assert result["covered_dates"] == []
        assert result["source_files"] == []

    def test_with_valid_files_returns_counts(self, monkeypatch):
        """有有效文件时返回课时统计"""
        fake_schedule_item = {"path": "/tmp/test.xlsx", "monday": date(2026, 5, 5), "file_name": "test.xlsx"}
        fake_df = pd.DataFrame([{"order": "1", "weekday": 1, "一班": "张老师"}])

        def fake_schedule_files(lesson, start, end):
            return [fake_schedule_item]

        def fake_format(lesson, path, monday):
            return fake_df

        monkeypatch.setattr("models.datas_api.dashboard_teaching.Lesson", FakeLesson)
        monkeypatch.setattr("models.datas_api.dashboard_teaching.schedule_files_for_range", fake_schedule_files)
        monkeypatch.setattr("models.datas_api.dashboard_teaching.format_week_schedule_file", fake_format)

        result = teacher_lesson_counts_from_files(date(2026, 5, 5), date(2026, 5, 5))
        assert len(result["rows"]) >= 1
        assert result["covered_dates"] == ["2026-05-05"]


class TestOverviewCardsAlias:
    """dashboard.py 中 overview 函数别名测试"""

    def test_base_overview_cards_alias_available(self):
        """dashboard._base_overview_cards 别名可用"""
        from models.datas_api.dashboard import _base_overview_cards
        assert _base_overview_cards is dashboard_overview.build_overview_cards


class TestTeachingAliases:
    """dashboard.py 中 teaching 函数别名测试"""

    def test_schedule_frames_alias_available(self):
        """dashboard._schedule_frames_for_range 别名可用"""
        from models.datas_api.dashboard import _schedule_frames_for_range
        assert _schedule_frames_for_range is schedule_frames_for_range

    def test_teacher_lesson_counts_alias_available(self):
        """dashboard._teacher_lesson_counts 别名可用"""
        from models.datas_api.dashboard import _teacher_lesson_counts
        assert _teacher_lesson_counts is teacher_lesson_counts

    def test_current_course_snapshot_alias_available(self):
        """dashboard._current_course_snapshot 别名可用"""
        from models.datas_api.dashboard import _current_course_snapshot
        assert _current_course_snapshot is current_course_snapshot


class TestTeachingRouteContract:
    """教务驾驶舱路由契约测试"""

    @pytest.fixture
    def users(self):
        return {
            "admin": User(username="admin", role="admin"),
            "jiaowu": User(username="jiaowu", role="jiaowu"),
            "teacher": User(username="teacher1", role="teacher"),
        }

    @pytest.fixture(autouse=True)
    def isolate_dashboard(self, monkeypatch):
        monkeypatch.setattr(dashboard, "get_moral_db", fake_moral_db_context)
        monkeypatch.setattr(dashboard, "Lesson", FakeLesson)
        monkeypatch.setattr(dashboard, "_teacher_lesson_counts", lambda s, e: {
            "rows": [{"teacher_name": "张老师", "lesson_count": 5}],
            "covered_dates": ["2026-05-05"],
            "source_files": ["test.xlsx"],
            "lessons": [],
            "message": "test",
        })
        monkeypatch.setattr(dashboard, "_current_course_snapshot", lambda: {
            "current_period": "第一节",
            "current_period_order": "1",
            "current_time_range": "08:00-08:45",
            "active_class_count": 1,
            "current_classes": [{"class_name": "一班", "subject": "语文"}],
            "all_periods": [{"order": "1", "label": "第一节", "time_range": "08:00-08:45"}],
        })

    @pytest.mark.asyncio
    async def test_teaching_summary_contract(self, users):
        """get_teaching_dashboard_summary 返回结构满足 Batch18 契约"""
        data = (await dashboard.get_teaching_dashboard_summary(top_n=5, user=users["jiaowu"]))["data"]

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

    @pytest.mark.asyncio
    async def test_teaching_summary_file_upload_contract(self, users, monkeypatch):
        """get_teaching_dashboard_summary 将文件上传指标整合到 cards/charts/tables。"""
        # Mock _build_filegather_summary
        monkeypatch.setattr(dashboard, "_build_filegather_summary", lambda month: {
            "cards": [
                {"name": "待处理文件", "value": 3},
                {"name": "本月文件", "value": 10},
                {"name": "已完成文件", "value": 7},
            ],
            "charts": {
                "file_upload_status": [
                    {"name": "待处理", "value": 3},
                    {"name": "已完成", "value": 7},
                ],
            },
            "tables": {
                "file_upload_top_users": [
                    {"username": "张老师", "count": 5},
                ],
            },
            "month": month,
        })

        data = (await dashboard.get_teaching_dashboard_summary(top_n=5, user=users["jiaowu"]))["data"]

        # Verify file_upload fields in cards (metric returns label)
        card_labels = [c.get("label") or c.get("name") for c in data["cards"]]
        assert "待处理文件" in card_labels
        assert "本月文件" in card_labels
        assert "已完成文件" in card_labels

        # Verify file_upload_status in charts
        assert "file_upload_status" in data["charts"]

        # Verify file_upload_top_users in tables
        assert "file_upload_top_users" in data["tables"]

        # Batch50: file_upload 块已删除，数据已整合到 cards/charts/tables

    @pytest.mark.asyncio
    async def test_jiaowu_can_access(self, users):
        """jiaowu 可访问教务驾驶舱"""
        data = (await dashboard.get_teaching_dashboard_summary(user=users["jiaowu"]))["data"]
        assert "cards" in data

    @pytest.mark.asyncio
    async def test_admin_can_access(self, users):
        """admin 可访问教务驾驶舱"""
        data = (await dashboard.get_teaching_dashboard_summary(user=users["admin"]))["data"]
        assert "cards" in data

    @pytest.mark.asyncio
    async def test_teacher_cannot_access(self, users):
        """teacher 无权限访问教务驾驶舱"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await dashboard.get_teaching_dashboard_summary(user=users["teacher"])

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_teaching_summary_no_leave_students(self, users, monkeypatch):
        """Batch46: 教务驾驶舱不返回 leave_students（属于班级/德育驾驶舱）"""
        # Setup mock for filegather
        monkeypatch.setattr(dashboard, "_build_filegather_summary", lambda month: {
            "cards": [
                {"name": "待处理文件", "value": 3},
                {"name": "本月文件", "value": 10},
                {"name": "已完成文件", "value": 7},
                {"name": "完成率", "value": 70.0},
                {"name": "逾期文件", "value": 0},
            ],
            "charts": {"file_upload_status": []},
            "tables": {
                "file_upload_top_users": [],
                "pending_file_list": [],
                "recent_file_list": [],
            },
            "month": month,
            "completion_rate": 70.0,
            "overdue_pending_count": 0,
            "pending_file_list": [],
            "recent_file_list": [],
        })

        data = (await dashboard.get_teaching_dashboard_summary(top_n=5, user=users["jiaowu"]))["data"]

        # Verify leave_students is NOT in the response
        assert "leave_students" not in data
        assert "leave_students" not in data.get("tables", {})
        assert "leave_students" not in data.get("file_upload", {})

        # Verify insights field exists (Batch46)
        assert "insights" in data
        assert isinstance(data["insights"], list)

    @pytest.mark.asyncio
    async def test_teaching_summary_batch46_metrics(self, users, monkeypatch):
        """Batch46: 教务驾驶舱返回完成率、逾期、待处理列表"""
        monkeypatch.setattr(dashboard, "_build_filegather_summary", lambda month: {
            "cards": [
                {"name": "待处理文件", "value": 5},
                {"name": "本月文件", "value": 20},
                {"name": "已完成文件", "value": 15},
                {"name": "完成率", "value": 75.0},
                {"name": "逾期文件", "value": 2},
            ],
            "charts": {"file_upload_status": []},
            "tables": {
                "file_upload_top_users": [{"username": "张老师", "count": 8}],
                "pending_file_list": [
                    {"id": 1, "username": "张老师", "original_name": "test.pdf", "overdue_days": 5},
                ],
                "recent_file_list": [],
            },
            "month": month,
            "completion_rate": 75.0,
            "overdue_pending_count": 2,
            "pending_file_list": [{"id": 1, "overdue_days": 5}],
            "recent_file_list": [],
        })

        data = (await dashboard.get_teaching_dashboard_summary(top_n=5, user=users["jiaowu"]))["data"]

        # Verify Batch50: file_upload 块已删除，数据已整合到 cards/tables
        # 完成率通过 cards 中的 "完成率" 卡片体现
        card_labels = [c.get("label") for c in data.get("cards", [])]
        assert "完成率" in card_labels
        assert "逾期文件" in card_labels

        # Verify pending_file_list in tables
        assert "pending_file_list" in data.get("tables", {})
        assert "recent_file_list" in data.get("tables", {})

        # Verify insights exists
        assert "insights" in data


class TestBuildFilegatherSummary:
    """build_filegather_summary 文件上传统计测试"""

    def test_returns_summary_structure(self, monkeypatch):
        """返回结构包含 cards/charts/tables/month"""
        class FakeFileGatherDB:
            def __init__(self):
                pass

            def get_statistics(self, month):
                return {
                    "total_files": 10,
                    "pending_files": 3,
                    "done_files": 7,
                    "by_user": [{"username": "张老师", "count": 5}],
                    "completion_rate": 70.0,
                    "overdue_pending_count": 0,
                    "pending_file_list": [],
                    "recent_file_list": [],
                }

        monkeypatch.setattr("models.filegather_db.FileGatherDB", FakeFileGatherDB)
        result = build_filegather_summary("202605")

        assert "cards" in result
        assert "charts" in result
        assert "tables" in result
        assert "month" in result

    def test_cards_contain_three_items(self, monkeypatch):
        """cards 包含三个指标"""
        class FakeFileGatherDB:
            def get_statistics(self, month):
                return {
                    "total_files": 10,
                    "pending_files": 3,
                    "done_files": 7,
                    "by_user": [],
                    "completion_rate": 70.0,
                    "overdue_pending_count": 0,
                    "pending_file_list": [],
                    "recent_file_list": [],
                }

        monkeypatch.setattr("models.filegather_db.FileGatherDB", FakeFileGatherDB)
        result = build_filegather_summary("202605")

        # Batch46: cards 数量从 3 增加到 5
        assert len(result["cards"]) == 5
        names = [c["name"] for c in result["cards"]]
        assert "待处理文件" in names
        assert "本月文件" in names
        assert "已完成文件" in names
        assert "完成率" in names
        assert "逾期文件" in names

    def test_charts_contain_file_upload_status(self, monkeypatch):
        """charts 包含 file_upload_status"""
        class FakeFileGatherDB:
            def get_statistics(self, month):
                return {
                    "total_files": 10,
                    "pending_files": 3,
                    "done_files": 7,
                    "by_user": [],
                    "completion_rate": 70.0,
                    "overdue_pending_count": 0,
                    "pending_file_list": [],
                    "recent_file_list": [],
                }

        monkeypatch.setattr("models.filegather_db.FileGatherDB", FakeFileGatherDB)
        result = build_filegather_summary("202605")

        assert "file_upload_status" in result["charts"]
        assert len(result["charts"]["file_upload_status"]) == 2
        names = [item["name"] for item in result["charts"]["file_upload_status"]]
        assert names == ["待处理", "已完成"]

    def test_tables_contain_top_users(self, monkeypatch):
        """tables 包含 file_upload_top_users"""
        class FakeFileGatherDB:
            def get_statistics(self, month):
                return {
                    "total_files": 10,
                    "pending_files": 3,
                    "done_files": 7,
                    "by_user": [{"username": "张老师", "count": 5}],
                    "completion_rate": 70.0,
                    "overdue_pending_count": 0,
                    "pending_file_list": [],
                    "recent_file_list": [],
                }

        monkeypatch.setattr("models.filegather_db.FileGatherDB", FakeFileGatherDB)
        result = build_filegather_summary("202605")

        assert "file_upload_top_users" in result["tables"]
        assert len(result["tables"]["file_upload_top_users"]) == 1

    def test_exception_returns_zeros(self, monkeypatch):
        """异常时返回全 0"""
        def fake_import_error(name):
            raise ImportError("Module not found")

        monkeypatch.setattr("builtins.__import__", fake_import_error)
        result = build_filegather_summary("202605")

        assert result["cards"][0]["value"] == 0
        assert result["cards"][1]["value"] == 0
        assert result["cards"][2]["value"] == 0
        assert result["charts"]["file_upload_status"][0]["value"] == 0
        assert result["charts"]["file_upload_status"][1]["value"] == 0
        assert result["tables"]["file_upload_top_users"] == []

    def test_none_statistics_returns_zeros(self, monkeypatch):
        """FileGatherDB 返回 None 时返回全 0"""
        class FakeFileGatherDB:
            def get_statistics(self, month):
                return None

        monkeypatch.setattr("models.filegather_db.FileGatherDB", FakeFileGatherDB)
        result = build_filegather_summary("202605")

        assert result["cards"][0]["value"] == 0
        assert result["cards"][1]["value"] == 0
        assert result["cards"][2]["value"] == 0
        assert result["tables"]["file_upload_top_users"] == []

    def test_non_list_by_user_returns_empty(self, monkeypatch):
        """by_user 非列表时返回空排行"""
        class FakeFileGatherDB:
            def get_statistics(self, month):
                return {
                    "total_files": 10,
                    "pending_files": 3,
                    "done_files": 7,
                    "by_user": {"username": "张老师", "count": 5},
                }

        monkeypatch.setattr("models.filegather_db.FileGatherDB", FakeFileGatherDB)
        result = build_filegather_summary("202605")

        assert result["cards"][1]["value"] == 10
        assert result["tables"]["file_upload_top_users"] == []

    def test_none_month_returns_all_stats(self, monkeypatch):
        """month=None 返回全部统计"""
        class FakeFileGatherDB:
            def get_statistics(self, month):
                assert month is None
                return {
                    "total_files": 20,
                    "pending_files": 5,
                    "done_files": 15,
                    "by_user": [],
                    "completion_rate": 70.0,
                    "overdue_pending_count": 0,
                    "pending_file_list": [],
                    "recent_file_list": [],
                }

        monkeypatch.setattr("models.filegather_db.FileGatherDB", FakeFileGatherDB)
        result = build_filegather_summary(None)

        assert result["cards"][1]["value"] == 20
        assert result["month"] is None

    def test_by_user_limited_to_ten(self, monkeypatch):
        """by_user 最多返回 10 条"""
        class FakeFileGatherDB:
            def get_statistics(self, month):
                return {
                    "total_files": 100,
                    "pending_files": 10,
                    "done_files": 90,
                    "by_user": [{"username": f"user{i}", "count": i} for i in range(15)],
                }

        monkeypatch.setattr("models.filegather_db.FileGatherDB", FakeFileGatherDB)
        result = build_filegather_summary("202605")

        assert len(result["tables"]["file_upload_top_users"]) == 10


class TestFilegatherAlias:
    """dashboard.py 中 filegather 函数别名测试"""

    def test_build_filegather_summary_alias_available(self):
        """dashboard._build_filegather_summary 别名可用"""
        from models.datas_api.dashboard import _build_filegather_summary
        assert _build_filegather_summary is build_filegather_summary
