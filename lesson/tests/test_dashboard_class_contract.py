# -*- coding: utf-8 -*-
"""Class dashboard helper contract tests.

Batch 22: test extracted class helpers and route contract.
Batch 47: test leave/attendance risk helpers and route contract.
"""
from datetime import date, timedelta
from contextlib import contextmanager

import pytest
from fastapi import HTTPException

from models.datas_api.auth import User
from models.datas_api import dashboard
from models.datas_api import dashboard_class
from models.datas_api import dashboard_overview
from models.datas_api import dashboard_moral
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
        sql_text = " ".join(str(sql).split()).lower()
        if "from class" in sql_text:
            return {"class_id": 1, "class_name": "一班", "is_active": 1}
        if "avg(total_score)" in sql_text and "from moral_evaluation where class_id" in sql_text:
            return {
                "avg_score": 82.5,
                "min_score": 55,
                "max_score": 99,
                "evaluated_count": 30,
                "low_count": 3,
                "pass_count": 27,
            }
        return {"count": 1}

    def query_all(self, sql, params=None):
        sql_text = " ".join(str(sql).split()).lower()
        if "from student where class_id" in sql_text:
            return [
                {"student_id": "S1", "name": "张三", "gender": "男", "birthday": "2010-05-10"},
                {"student_id": "S2", "name": "李四", "gender": "女", "birthday": "2010-06-15"},
                {"student_id": "S3", "name": "王五", "gender": None, "birthday": None},
            ]
        if "me.total_score < 60" in sql_text:
            return [{"student_id": "S1", "name": "张三", "total_score": 55}]
        return []


@contextmanager
def fake_moral_db_context():
    yield FakeMoralDB()


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
        return FakeCursor(self.kind)

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class FakeCursor:
    def __init__(self, kind="generic"):
        self.kind = kind

    def execute(self, sql, params=None):
        return self

    def fetchone(self):
        if self.kind == "homework":
            return (2,)
        elif self.kind == "inout":
            return (1,)
        return (0,)

    def close(self):
        pass


class FakeScheduleService:
    def replace_subject_teacher(self, df, teacher_flag=False):
        import pandas as pd
        return pd.DataFrame()

    def split_subjects(self, value):
        return [str(value)] if value else []

    def format_schedule(self, df, week_flag, replace_flag=True, ignore=False):
        import pandas as pd
        return pd.DataFrame()


class FakeLesson:
    lesson_dir = "/tmp/nonexistent-dashboard-class"
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
        return None

    def load_excel_file(self, path):
        import pandas as pd
        return pd.DataFrame()


class TestBuildGenderMix:
    """build_gender_mix 性别分布测试"""

    def test_returns_three_types(self):
        """返回三种性别类型"""
        students = [
            {"gender": "男"},
            {"gender": "男"},
            {"gender": "女"},
            {"gender": None},
        ]
        result = dashboard_class.build_gender_mix(students)
        assert len(result) == 3
        names = [item["name"] for item in result]
        assert names == ["男生", "女生", "未维护"]

    def test_counts_correct(self):
        """计数正确"""
        students = [
            {"gender": "男"},
            {"gender": "男"},
            {"gender": "女"},
            {"gender": None},
        ]
        result = dashboard_class.build_gender_mix(students)
        assert result[0]["value"] == 2  # 男生
        assert result[1]["value"] == 1  # 女生
        assert result[2]["value"] == 1  # 未维护

    def test_empty_students_returns_zeros(self):
        """空学生列表返回全 0"""
        result = dashboard_class.build_gender_mix([])
        assert result[0]["value"] == 0
        assert result[1]["value"] == 0
        assert result[2]["value"] == 0

    def test_all_male(self):
        """全是男生"""
        students = [{"gender": "男"} for _ in range(5)]
        result = dashboard_class.build_gender_mix(students)
        assert result[0]["value"] == 5
        assert result[1]["value"] == 0
        assert result[2]["value"] == 0


class TestBuildScoreBand:
    """build_score_band 分数段测试"""

    def test_returns_three_bands(self):
        """返回三个分数段"""
        eval_stats = {"low_count": 3, "pass_count": 27, "evaluated_count": 30}
        result = dashboard_class.build_score_band(eval_stats, 35)
        assert len(result) == 3
        names = [item["name"] for item in result]
        assert names == ["60分以下", "60分以上", "未评价"]

    def test_unevaluated_count_correct(self):
        """未评价数正确"""
        eval_stats = {"low_count": 3, "pass_count": 27, "evaluated_count": 30}
        result = dashboard_class.build_score_band(eval_stats, 35)
        assert result[2]["value"] == 5  # 35 - 30

    def test_empty_eval_returns_zeros(self):
        """空评价统计返回全 0"""
        result = dashboard_class.build_score_band({}, 30)
        assert result[0]["value"] == 0
        assert result[1]["value"] == 0
        assert result[2]["value"] == 30  # 全部未评价

    def test_none_eval_returns_zeros(self):
        """None 评价统计返回全 0"""
        result = dashboard_class.build_score_band(None, 30)
        assert result[0]["value"] == 0
        assert result[1]["value"] == 0
        assert result[2]["value"] == 30

    def test_all_evaluated(self):
        """全部已评价"""
        eval_stats = {"low_count": 5, "pass_count": 25, "evaluated_count": 30}
        result = dashboard_class.build_score_band(eval_stats, 30)
        assert result[2]["value"] == 0  # 无未评价


class TestFilterBirthdayThisMonth:
    """filter_birthday_this_month 本月生日筛选测试"""

    def test_filters_by_month(self):
        """按月份筛选"""
        students = [
            {"name": "张三", "birthday": "2010-05-10"},
            {"name": "李四", "birthday": "2010-06-15"},
        ]
        result = dashboard_class.filter_birthday_this_month(students, 5)
        assert len(result) == 1
        assert result[0]["name"] == "张三"

    def test_empty_birthday_skipped(self):
        """空生日跳过"""
        students = [
            {"name": "张三", "birthday": "2010-05-10"},
            {"name": "李四", "birthday": None},
        ]
        result = dashboard_class.filter_birthday_this_month(students, 5)
        assert len(result) == 1

    def test_no_match_returns_empty(self):
        """无匹配返回空"""
        students = [
            {"name": "张三", "birthday": "2010-06-10"},
        ]
        result = dashboard_class.filter_birthday_this_month(students, 5)
        assert result == []

    def test_invalid_birthday_skipped(self):
        """非法生日跳过"""
        students = [
            {"name": "张三", "birthday": "invalid"},
        ]
        result = dashboard_class.filter_birthday_this_month(students, 5)
        assert result == []


class TestFilterBirthdayThisWeek:
    """filter_birthday_this_week 本周生日筛选测试"""

    def test_filters_by_week(self):
        """按周筛选"""
        # Create a date that falls in current week
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        # Birthday on Wednesday of current week
        bd_in_week = week_start + timedelta(days=2)
        students = [
            {"name": "张三", "birthday": f"2010-{bd_in_week.month:02d}-{bd_in_week.day:02d}"},
        ]
        result = dashboard_class.filter_birthday_this_week(students, today)
        assert len(result) == 1

    def test_outside_week_skipped(self):
        """周外生日跳过"""
        today = date.today()
        week_end = today - timedelta(days=today.weekday()) + timedelta(days=6)
        # Birthday next week
        bd_outside = week_end + timedelta(days=7)
        students = [
            {"name": "张三", "birthday": f"2010-{bd_outside.month:02d}-{bd_outside.day:02d}"},
        ]
        result = dashboard_class.filter_birthday_this_week(students, today)
        assert result == []

    def test_empty_birthday_skipped(self):
        """空生日跳过"""
        students = [{"name": "张三", "birthday": None}]
        result = dashboard_class.filter_birthday_this_week(students, date.today())
        assert result == []

    def test_invalid_birthday_skipped(self):
        """非法生日格式跳过"""
        students = [{"name": "张三", "birthday": "invalid"}]
        result = dashboard_class.filter_birthday_this_week(students, date.today())
        assert result == []


class TestFormatBirthdayList:
    """format_birthday_list 生日列表格式化测试"""

    def test_returns_name_and_birthday(self):
        """只返回 name 和 birthday"""
        students = [
            {"name": "张三", "birthday": "2010-05-10", "gender": "男"},
        ]
        result = dashboard_class.format_birthday_list(students)
        assert len(result) == 1
        assert result[0] == {"name": "张三", "birthday": "2010-05-10"}

    def test_empty_returns_empty(self):
        """空列表返回空"""
        result = dashboard_class.format_birthday_list([])
        assert result == []

    def test_multiple_students(self):
        """多个学生"""
        students = [
            {"name": "张三", "birthday": "2010-05-10"},
            {"name": "李四", "birthday": "2010-06-15"},
        ]
        result = dashboard_class.format_birthday_list(students)
        assert len(result) == 2


class TestComputeClassStats:
    """compute_class_stats 班级统计测试"""

    def test_returns_all_stats(self):
        """返回所有统计字段"""
        students = [
            {"gender": "男"},
            {"gender": "女"},
            {"gender": None},
        ]
        eval_stats = {"avg_score": 85.5, "low_count": 2, "evaluated_count": 3}
        result = dashboard_class.compute_class_stats(students, eval_stats)
        assert "student_count" in result
        assert "male_count" in result
        assert "female_count" in result
        assert "unknown_gender_count" in result
        assert "avg_score" in result
        assert "low_count" in result
        assert "unevaluated_count" in result

    def test_counts_correct(self):
        """计数正确"""
        students = [
            {"gender": "男"},
            {"gender": "男"},
            {"gender": "女"},
        ]
        eval_stats = {"avg_score": 80.0, "low_count": 1, "evaluated_count": 3}
        result = dashboard_class.compute_class_stats(students, eval_stats)
        assert result["student_count"] == 3
        assert result["male_count"] == 2
        assert result["female_count"] == 1
        assert result["unknown_gender_count"] == 0
        assert result["avg_score"] == 80.0
        assert result["low_count"] == 1

    def test_none_eval_stats_returns_defaults(self):
        """None 评价统计返回默认值"""
        students = [{"gender": "男"}, {"gender": None}]
        result = dashboard_class.compute_class_stats(students, None)

        assert result["student_count"] == 2
        assert result["male_count"] == 1
        assert result["female_count"] == 0
        assert result["unknown_gender_count"] == 1
        assert result["avg_score"] == 0.0
        assert result["low_count"] == 0
        assert result["unevaluated_count"] == 2


class TestClassAliases:
    """dashboard.py 中 class 函数别名测试"""

    def test_build_gender_mix_alias_available(self):
        """dashboard._build_gender_mix 别名可用"""
        from models.datas_api.dashboard import _build_gender_mix
        assert _build_gender_mix is dashboard_class.build_gender_mix

    def test_build_score_band_alias_available(self):
        """dashboard._build_score_band 别名可用"""
        from models.datas_api.dashboard import _build_score_band
        assert _build_score_band is dashboard_class.build_score_band

    def test_filter_birthday_this_month_alias_available(self):
        """dashboard._filter_birthday_this_month 别名可用"""
        from models.datas_api.dashboard import _filter_birthday_this_month
        assert _filter_birthday_this_month is dashboard_class.filter_birthday_this_month

    def test_filter_birthday_this_week_alias_available(self):
        """dashboard._filter_birthday_this_week 别名可用"""
        from models.datas_api.dashboard import _filter_birthday_this_week
        assert _filter_birthday_this_week is dashboard_class.filter_birthday_this_week

    def test_format_birthday_list_alias_available(self):
        """dashboard._format_birthday_list 别名可用"""
        from models.datas_api.dashboard import _format_birthday_list
        assert _format_birthday_list is dashboard_class.format_birthday_list

    def test_compute_class_stats_alias_available(self):
        """dashboard._compute_class_stats 别名可用"""
        from models.datas_api.dashboard import _compute_class_stats
        assert _compute_class_stats is dashboard_class.compute_class_stats


class TestClassRouteContract:
    """班级驾驶舱路由契约测试"""

    @pytest.fixture
    def users(self):
        return {
            "admin": User(username="admin", role="admin"),
            "jiaowu": User(username="jiaowu", role="jiaowu"),
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

        # Mock homework/inout db
        monkeypatch.setattr(dashboard, "_get_homework_db", lambda: FakeConnection("homework"))
        monkeypatch.setattr(dashboard, "_get_inout_db", lambda: FakeConnection("inout"))

        # Mock teaching helpers
        fake_workload = {
            "rows": [],
            "covered_dates": [],
            "source_files": [],
            "lessons": [],
            "message": "test",
        }
        monkeypatch.setattr(dashboard, "_teacher_lesson_counts", lambda s, e: fake_workload)
        monkeypatch.setattr(dashboard, "_teacher_lesson_counts_from_files", lambda s, e, **kw: fake_workload)
        monkeypatch.setattr(dashboard, "_current_course_snapshot", lambda: {
            "current_period": None,
            "current_period_order": None,
            "current_time_range": "",
            "active_class_count": 0,
            "current_classes": [],
            "all_periods": [],
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
        monkeypatch.setattr(dashboard, "_compute_class_leave_insights", lambda records, cn: [])

    @pytest.mark.asyncio
    async def test_class_summary_contract(self, users):
        """get_class_dashboard_summary 返回结构满足 Batch18 契约"""
        data = (await dashboard.get_class_dashboard_summary(class_id=1, top_n=5, user=users["admin"]))["data"]

        for key in ["cards", "charts", "tables", "class_info", "top_n", "updated_at"]:
            assert key in data

        for key in ["gender_mix", "score_band"]:
            assert key in data["charts"]

        for key in ["low_students", "birthday_this_month", "birthday_this_week"]:
            assert key in data["tables"]

    @pytest.mark.asyncio
    async def test_admin_can_access(self, users):
        """admin 可访问班级驾驶舱"""
        data = (await dashboard.get_class_dashboard_summary(class_id=1, user=users["admin"]))["data"]
        assert "cards" in data

    @pytest.mark.asyncio
    async def test_jiaowu_can_access(self, users):
        """jiaowu 可访问班级驾驶舱"""
        data = (await dashboard.get_class_dashboard_summary(class_id=1, user=users["jiaowu"]))["data"]
        assert "cards" in data

    @pytest.mark.asyncio
    async def test_cleader_can_access_own_class(self, users):
        """cleader 可访问自己班级"""
        data = (await dashboard.get_class_dashboard_summary(user=users["cleader"]))["data"]
        assert "cards" in data

    @pytest.mark.asyncio
    async def test_teacher_cannot_access_class_summary(self, users):
        """teacher 无权限访问班级驾驶舱"""
        with pytest.raises(HTTPException) as exc_info:
            await dashboard.get_class_dashboard_summary(user=users["teacher"])

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cleader_cannot_access_other_class(self, users, monkeypatch):
        """cleader 只能访问自己班级"""
        # cleader's class is 1, try to access class 2
        monkeypatch.setattr(dashboard, "get_teacher_class_id", lambda user, db: 1)

        with pytest.raises(HTTPException) as exc_info:
            await dashboard.get_class_dashboard_summary(class_id=2, user=users["cleader"])

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_class_summary_batch47_leave_students(self, users):
        """Batch47: class summary 返回 leave_students 和 insights"""
        data = (await dashboard.get_class_dashboard_summary(class_id=1, top_n=5, user=users["admin"]))["data"]

        # Batch47: leave_students in tables
        assert "leave_students" in data["tables"]
        assert isinstance(data["tables"]["leave_students"], list)

        # Batch50: leave 块已删除，数据已整合到 tables.leave_students

        # Batch47: insights array
        assert "insights" in data
        assert isinstance(data["insights"], list)

    @pytest.mark.asyncio
    async def test_class_summary_batch47_with_leave_data(self, users, monkeypatch):
        """Batch47: class summary 正确处理有请假数据情况"""
        fake_leave_records = [
            {"id": 1, "sid": "1001", "name": "张三", "class_name": "高二1班", "style": "事假", "days": "2", "status": "已出校"},
        ]
        monkeypatch.setattr(dashboard, "_query_active_leave_records", lambda **kw: fake_leave_records)
        monkeypatch.setattr(dashboard, "_compute_leave_stats", lambda **kw: {
            "leave_count": 1,
            "active_leave_count": 1,
            "pending_cancel_count": 1,
            "recent_leave_list": fake_leave_records,
            "leave_students": fake_leave_records,
        })
        monkeypatch.setattr(dashboard, "_compute_class_leave_insights", lambda records, cn: [
            {"type": "warning", "title": "未销假需跟进", "message": "张三 已出校但未销假", "action_route": "/leave-record"},
        ])

        data = (await dashboard.get_class_dashboard_summary(class_id=1, top_n=5, user=users["admin"]))["data"]

        assert len(data["tables"]["leave_students"]) == 1
        # Batch50: leave 块已删除，请假人数通过 cards["请假人数"] 获取
        assert len(data["insights"]) >= 1

        # Find leave card
        leave_card = next((c for c in data["cards"] if c["label"] == "请假人数"), None)
        assert leave_card is not None
        assert leave_card["value"] == 1
