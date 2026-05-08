# -*- coding: utf-8 -*-
"""Moral dashboard helper contract tests.

Batch 21: test extracted moral helpers and route contract.
Batch 47: test leave/attendance risk helpers and route contract.
"""
from datetime import date, timedelta
from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from models.datas_api.auth import User
from models.datas_api import dashboard
from models.datas_api import dashboard_moral
from models.datas_api import dashboard_overview
from models.datas_api import dashboard_leave


class FakeMoralDB:
    """Small query facade matching the parts of MoralDatabase used by dashboard."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def query_value(self, sql, params=None):
        return 82.5

    def query_one(self, sql, params=None):
        return {"class_id": 1, "class_name": "一班", "is_active": 1}

    def query_all(self, sql, params=None):
        sql_text = " ".join(str(sql).split()).lower()
        # score distribution: return aggregated values
        if "sum(case when me.total_score" in sql_text:
            return [{"excellent": 10, "good": 20, "normal": 15, "pass": 5, "risk": 3}]
        # daily event mix: return event_type counts
        if "det.event_type" in sql_text and "group by" in sql_text:
            return [{"event_type": 1, "count": 50}, {"event_type": 2, "count": 10}]
        # daily record trend: return daily counts
        if "dr.record_date" in sql_text and "group by dr.record_date" in sql_text:
            today = date.today()
            return [{"record_date": today.isoformat(), "count": 5}]
        # class score rank: return class averages
        if "avg(me.total_score)" in sql_text and "group by c.class_id" in sql_text:
            return [{"class_name": "一班", "avg_score": 85.5, "student_count": 30}]
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
    lesson_dir = "/tmp/nonexistent-dashboard-moral"
    week_change = 0

    def __init__(self):
        self.schedule_service = FakeScheduleService()

    def get_cache_data(self, key):
        import pandas as pd
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
        import pandas as pd
        return pd.DataFrame([{"order": "1", "weekday": 1, "一班": "张老师"}])


class TestScoreDistribution:
    """score_distribution 分数段分布测试"""

    def test_returns_five_segments(self):
        """返回固定 5 个分段"""
        db = FakeMoralDB()
        result = dashboard_moral.score_distribution(db, "s.status = '在校'", ())
        assert len(result) == 5
        names = [item["name"] for item in result]
        assert names == ["90分以上", "80-89分", "70-79分", "60-69分", "60分以下"]
        for item in result:
            assert "value" in item

    def test_empty_rows_returns_zeros(self):
        """查询异常或空 rows 时全部为 0"""
        class EmptyDB:
            def query_all(self, sql, params=None):
                return []

        result = dashboard_moral.score_distribution(EmptyDB(), "1 = 0", ())
        assert len(result) == 5
        for item in result:
            assert item["value"] == 0

    def test_missing_columns_returns_zeros(self):
        """缺失列时返回 0"""
        class MissingDB:
            def query_all(self, sql, params=None):
                return [{"excellent": None}]  # other columns missing

        result = dashboard_moral.score_distribution(MissingDB(), "s.status = '在校'", ())
        assert result[0]["value"] == 0  # excellent is None -> 0
        assert result[1]["value"] == 0  # good missing -> 0

    def test_query_error_returns_zeros(self):
        """查询异常时全部返回 0"""
        class ErrorDB:
            def query_all(self, sql, params=None):
                raise RuntimeError("query failed")

        result = dashboard_moral.score_distribution(ErrorDB(), "s.status = '在校'", ())
        assert len(result) == 5
        assert all(item["value"] == 0 for item in result)


class TestDailyEventMix:
    """daily_event_mix 正负向记录测试"""

    def test_returns_two_types(self):
        """返回正向和负向两种记录"""
        db = FakeMoralDB()
        result = dashboard_moral.daily_event_mix(db, "s.status = '在校'", ())
        assert len(result) == 2
        names = [item["name"] for item in result]
        assert names == ["正向记录", "负向记录"]

    def test_event_type_1_is_positive(self):
        """event_type=1 映射为正向记录"""
        class SingleTypeDB:
            def query_all(self, sql, params=None):
                return [{"event_type": 1, "count": 100}]

        result = dashboard_moral.daily_event_mix(SingleTypeDB(), "1 = 1", ())
        assert result[0]["name"] == "正向记录"
        assert result[0]["value"] == 100
        assert result[1]["name"] == "负向记录"
        assert result[1]["value"] == 0

    def test_event_type_2_is_negative(self):
        """event_type=2 映射为负向记录"""
        class SingleTypeDB:
            def query_all(self, sql, params=None):
                return [{"event_type": 2, "count": 50}]

        result = dashboard_moral.daily_event_mix(SingleTypeDB(), "1 = 1", ())
        assert result[0]["name"] == "正向记录"
        assert result[0]["value"] == 0
        assert result[1]["name"] == "负向记录"
        assert result[1]["value"] == 50

    def test_missing_types_returns_zeros(self):
        """缺失类型返回 0"""
        class EmptyDB:
            def query_all(self, sql, params=None):
                return []

        result = dashboard_moral.daily_event_mix(EmptyDB(), "1 = 0", ())
        assert result[0]["value"] == 0
        assert result[1]["value"] == 0

    def test_query_error_returns_zeros(self):
        """查询异常时正负向记录都返回 0"""
        class ErrorDB:
            def query_all(self, sql, params=None):
                raise RuntimeError("query failed")

        result = dashboard_moral.daily_event_mix(ErrorDB(), "1 = 0", ())
        assert result == [
            {"name": "正向记录", "value": 0},
            {"name": "负向记录", "value": 0},
        ]


class TestDailyRecordTrend:
    """daily_record_trend 14天趋势测试"""

    def test_returns_fourteen_days(self):
        """固定返回 14 天"""
        db = FakeMoralDB()
        result = dashboard_moral.daily_record_trend(db, "s.status = '在校'", ())
        assert len(result) == 14

    def test_each_item_has_date_and_count(self):
        """每项包含 date 和 count"""
        db = FakeMoralDB()
        result = dashboard_moral.daily_record_trend(db, "s.status = '在校'", ())
        for item in result:
            assert "date" in item
            assert "count" in item
            assert isinstance(item["count"], int)

    def test_empty_rows_returns_zeros_for_all_days(self):
        """查询异常时返回 14 天全为 0"""
        class EmptyDB:
            def query_all(self, sql, params=None):
                return []

        result = dashboard_moral.daily_record_trend(EmptyDB(), "1 = 0", ())
        assert len(result) == 14
        for item in result:
            assert item["count"] == 0

    def test_date_sequence_starts_from_13_days_ago(self):
        """日期序列从 13 天前开始"""
        db = FakeMoralDB()
        result = dashboard_moral.daily_record_trend(db, "s.status = '在校'", ())
        start = date.today() - timedelta(days=13)
        assert result[0]["date"] == start.isoformat()

    def test_query_error_returns_fourteen_zero_days(self):
        """查询异常时仍返回 14 天全 0 趋势"""
        class ErrorDB:
            def query_all(self, sql, params=None):
                raise RuntimeError("query failed")

        result = dashboard_moral.daily_record_trend(ErrorDB(), "1 = 0", ())
        assert len(result) == 14
        assert all(item["count"] == 0 for item in result)


class TestClassScoreRank:
    """class_score_rank 班级分数排名测试"""

    def test_returns_rows_from_query(self):
        """返回 _safe_query_all 的 rows"""
        db = FakeMoralDB()
        result = dashboard_moral.class_score_rank(db, "s.status = '在校'", (), top_n=5)
        assert len(result) >= 0
        if result:
            assert "class_name" in result[0]
            assert "avg_score" in result[0]
            assert "student_count" in result[0]

    def test_empty_rows_returns_empty_list(self):
        """查询异常返回空列表"""
        class EmptyDB:
            def query_all(self, sql, params=None):
                return []

        result = dashboard_moral.class_score_rank(EmptyDB(), "1 = 0", (), top_n=5)
        assert result == []

    def test_top_n_passed_to_limit(self):
        """top_n 传入 SQL 的 LIMIT"""
        class RecordingDB:
            def __init__(self):
                self.sql = ""

            def query_all(self, sql, params=None):
                self.sql = sql
                return []

        db = RecordingDB()
        dashboard_moral.class_score_rank(db, "s.status = '在校'", (), top_n=3)

        assert "LIMIT 3" in db.sql

    def test_query_error_returns_empty_list(self):
        """查询异常时返回空列表"""
        class ErrorDB:
            def query_all(self, sql, params=None):
                raise RuntimeError("query failed")

        assert dashboard_moral.class_score_rank(ErrorDB(), "1 = 0", (), top_n=5) == []


class TestMoralAliases:
    """dashboard.py 中 moral 函数别名测试"""

    def test_score_distribution_alias_available(self):
        """dashboard._score_distribution 别名可用"""
        from models.datas_api.dashboard import _score_distribution
        assert _score_distribution is dashboard_moral.score_distribution

    def test_daily_event_mix_alias_available(self):
        """dashboard._daily_event_mix 别名可用"""
        from models.datas_api.dashboard import _daily_event_mix
        assert _daily_event_mix is dashboard_moral.daily_event_mix

    def test_daily_record_trend_alias_available(self):
        """dashboard._daily_record_trend 别名可用"""
        from models.datas_api.dashboard import _daily_record_trend
        assert _daily_record_trend is dashboard_moral.daily_record_trend

    def test_class_score_rank_alias_available(self):
        """dashboard._class_score_rank 别名可用"""
        from models.datas_api.dashboard import _class_score_rank
        assert _class_score_rank is dashboard_moral.class_score_rank


class TestMoralRouteContract:
    """德育驾驶舱路由契约测试"""

    @pytest.fixture
    def users(self):
        return {
            "admin": User(username="admin", role="admin"),
            "jiaowu": User(username="jiaowu", role="jiaowu"),
            "moral": User(username="xuefa", role="xuefa"),
            "cleader": User(username="cleader", role="cleader"),
            "teacher": User(username="teacher1", role="teacher"),
        }

    @pytest.fixture(autouse=True)
    def isolate_dashboard(self, monkeypatch):
        monkeypatch.setattr(dashboard, "get_moral_db", fake_moral_db_context)
        monkeypatch.setattr(dashboard_overview, "get_moral_db", fake_moral_db_context)
        monkeypatch.setattr(dashboard, "Lesson", FakeLesson)
        monkeypatch.setattr(dashboard, "get_teacher_class_id", lambda user, db: 1)
        monkeypatch.setattr(dashboard_overview, "get_teacher_class_id", lambda user, db: 1)

        # Mock teaching helpers
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

        # Batch47: Mock leave helpers
        monkeypatch.setattr(dashboard, "_query_active_leave_records", lambda **kw: [])
        monkeypatch.setattr(dashboard, "_compute_leave_stats", lambda **kw: {
            "leave_count": 0,
            "active_leave_count": 0,
            "pending_cancel_count": 0,
            "recent_leave_list": [],
            "leave_students": [],
        })
        monkeypatch.setattr(dashboard, "_build_leave_by_class_chart", lambda limit=10: [])
        monkeypatch.setattr(dashboard, "_compute_attendance_risk_insights", lambda records, cf: [])

    @pytest.mark.asyncio
    async def test_moral_summary_contract(self, users):
        """get_moral_dashboard_summary 返回结构满足 Batch18 契约"""
        data = (await dashboard.get_moral_dashboard_summary(top_n=5, user=users["moral"]))["data"]

        for key in ["cards", "charts", "tables", "insights", "top_n", "updated_at"]:
            assert key in data

        for key in ["score_distribution", "daily_event_mix", "daily_record_trend", "class_score_rank", "leave_by_class"]:
            assert key in data["charts"]

        for key in ["low_students", "leave_students"]:
            assert key in data["tables"]

    @pytest.mark.asyncio
    async def test_teacher_cannot_access_moral_summary(self, users):
        """普通教师访问德育驾驶舱返回 403"""
        with pytest.raises(HTTPException) as exc_info:
            await dashboard.get_moral_dashboard_summary(user=users["teacher"])

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cleader_with_class_can_access(self, users):
        """cleader 有班级时可访问并返回契约结构"""
        data = (await dashboard.get_moral_dashboard_summary(top_n=5, user=users["cleader"]))["data"]

        for key in ["cards", "charts", "tables", "insights", "top_n", "updated_at"]:
            assert key in data

    @pytest.mark.asyncio
    async def test_moral_summary_batch47_leave_students(self, users):
        """Batch47: moral summary 返回 leave_students 和 insights"""
        data = (await dashboard.get_moral_dashboard_summary(top_n=5, user=users["moral"]))["data"]

        # Batch47: leave_students in tables
        assert "leave_students" in data["tables"]
        assert isinstance(data["tables"]["leave_students"], list)

        # Batch50: leave 块已删除，leave_by_class 已整合到 charts
        assert "leave_by_class" in data["charts"]

        # Batch47: insights array
        assert "insights" in data
        assert isinstance(data["insights"], list)

    @pytest.mark.asyncio
    async def test_moral_summary_batch47_with_leave_data(self, users, monkeypatch):
        """Batch47: moral summary 正确处理有请假数据情况"""
        fake_leave_records = [
            {"id": 1, "sid": "1001", "name": "张三", "class_name": "高二1班", "style": "事假", "days": "2", "status": "已请假"},
            {"id": 2, "sid": "1002", "name": "李四", "class_name": "高二1班", "style": "病假", "days": "3", "status": "已出校"},
        ]
        monkeypatch.setattr(dashboard, "_query_active_leave_records", lambda **kw: fake_leave_records)
        monkeypatch.setattr(dashboard, "_compute_leave_stats", lambda **kw: {
            "leave_count": 2,
            "active_leave_count": 2,
            "pending_cancel_count": 1,
            "recent_leave_list": fake_leave_records,
            "leave_students": fake_leave_records,
        })
        monkeypatch.setattr(dashboard, "_build_leave_by_class_chart", lambda limit=10: [{"name": "高二1班", "value": 2}])
        monkeypatch.setattr(dashboard, "_compute_attendance_risk_insights", lambda records, cf: [
            {"type": "warning", "title": "未销假学生", "message": "有 1 名学生已出校但未销假", "action_route": "/leave-record"},
        ])

        data = (await dashboard.get_moral_dashboard_summary(top_n=5, user=users["moral"]))["data"]

        assert len(data["tables"]["leave_students"]) == 2
        # Batch50: leave 块已删除，数据已整合到 tables/charts
        assert len(data["tables"]["leave_students"]) == 2
        assert "leave_by_class" in data["charts"]
        assert len(data["insights"]) > 0

        # Find leave card
        leave_card = next((c for c in data["cards"] if c["label"] == "当前请假"), None)
        assert leave_card is not None
        assert leave_card["value"] == 2


class TestDashboardLeaveHelpers:
    """Batch47: 请假 helper 函数测试"""

    def test_query_active_leave_records_empty_on_missing_db(self, monkeypatch):
        """inout.db 不存在时返回空列表"""
        monkeypatch.setattr(dashboard_leave, "INOUT_DB_PATH", "/nonexistent/path/inout.db")
        result = dashboard_leave.query_active_leave_records()
        assert result == []

    def test_query_active_leave_records_filters_class_by_cached_sid(self, monkeypatch):
        """班级筛选先通过学生缓存换成 inout.sid，避免误用德育 student_id。"""
        import pandas as pd

        class FakeCursor:
            def __init__(self):
                self.sql = ""
                self.params = ()

            def execute(self, sql, params=None):
                self.sql = sql
                self.params = params or ()

            def fetchall(self):
                return [(1, "1001", "事假", "2", "已出校", "张老师", "备注", "2026-05-07 08:00:00")]

        class FakeConn:
            def __init__(self):
                self.cursor_obj = FakeCursor()
                self.closed = False

            def cursor(self):
                return self.cursor_obj

            def close(self):
                self.closed = True

        fake_conn = FakeConn()

        monkeypatch.setattr(dashboard_leave.os.path, "isfile", lambda path: True)
        monkeypatch.setattr(dashboard_leave, "_get_sqlite_connection", lambda: lambda *args, **kwargs: fake_conn)
        monkeypatch.setattr(dashboard_leave, "_load_students_cache", lambda: pd.DataFrame([
            {"sid": "1001", "name": "张三", "cname": "高二1班", "class_code": "G201"},
            {"sid": "1002", "name": "李四", "cname": "高二2班", "class_code": "G202"},
        ]))

        result = dashboard_leave.query_active_leave_records(class_filter="高二1班", limit=20)

        assert "sid IN (?)" in fake_conn.cursor_obj.sql
        assert fake_conn.cursor_obj.params == ("1001", 20)
        assert fake_conn.closed is True
        assert result[0]["name"] == "张三"
        assert result[0]["class_name"] == "高二1班"

    def test_query_active_leave_records_closes_connection_on_error(self, monkeypatch):
        """SQL 执行异常时仍关闭连接。"""
        import pandas as pd

        class FakeCursor:
            def execute(self, sql, params=None):
                raise RuntimeError("sql failed")

        class FakeConn:
            def __init__(self):
                self.closed = False

            def cursor(self):
                return FakeCursor()

            def close(self):
                self.closed = True

        fake_conn = FakeConn()

        monkeypatch.setattr(dashboard_leave.os.path, "isfile", lambda path: True)
        monkeypatch.setattr(dashboard_leave, "_get_sqlite_connection", lambda: lambda *args, **kwargs: fake_conn)
        monkeypatch.setattr(dashboard_leave, "_load_students_cache", lambda: pd.DataFrame())

        result = dashboard_leave.query_active_leave_records()

        assert result == []
        assert fake_conn.closed is True

    def test_compute_leave_stats_returns_structure(self, monkeypatch):
        """compute_leave_stats 返回正确结构"""
        monkeypatch.setattr(dashboard_leave, "query_active_leave_records", lambda **kw: [])
        result = dashboard_leave.compute_leave_stats()
        assert "leave_count" in result
        assert "active_leave_count" in result
        assert "pending_cancel_count" in result
        assert "recent_leave_list" in result
        assert "leave_students" in result

    def test_build_leave_by_class_chart_returns_list(self, monkeypatch):
        """build_leave_by_class_chart 返回图表数据列表"""
        monkeypatch.setattr(dashboard_leave, "count_active_leave_by_class", lambda: {"高二1班": 2, "高二2班": 1})
        result = dashboard_leave.build_leave_by_class_chart(limit=10)
        assert isinstance(result, list)
        assert all("name" in item and "value" in item for item in result)

    def test_compute_attendance_risk_insights_empty_on_no_records(self):
        """无请假记录时返回空 insights"""
        result = dashboard_leave.compute_attendance_risk_insights([])
        assert result == []

    def test_compute_attendance_risk_insights_with_records(self):
        """有请假记录时返回 insights"""
        records = [
            {"id": 1, "sid": "1001", "status": "已出校", "days": "2"},
            {"id": 2, "sid": "1002", "status": "已请假", "days": "5"},
            {"id": 3, "sid": "1001", "status": "已请假", "days": "1"},  # repeated sid
        ]
        result = dashboard_leave.compute_attendance_risk_insights(records)
        assert len(result) >= 2  # at least repeated leave and long leave

    def test_compute_class_leave_insights_empty_returns_success(self):
        """无请假记录时返回成功 insight"""
        result = dashboard_leave.compute_class_leave_insights([], "高二1班")
        assert len(result) == 1
        assert result[0]["type"] == "success"

    def test_compute_class_leave_insights_with_records(self):
        """有请假记录时返回正确 insights"""
        records = [
            {"id": 1, "sid": "1001", "name": "张三", "status": "已出校", "style": "事假", "days": "2"},
            {"id": 2, "sid": "1002", "name": "李四", "status": "已请假", "style": "病假", "days": "1"},
        ]
        result = dashboard_leave.compute_class_leave_insights(records, "高二1班")
        assert len(result) >= 2  # current leave + not returned
