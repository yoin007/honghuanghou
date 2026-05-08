# -*- coding: utf-8 -*-
"""数据驾驶舱 API。"""

import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models.datas_api.auth import User, get_current_user, is_admin_user
from models.datas_api.moral.base import (
    check_moral_permission,
    get_moral_db,
    get_teacher_class_id,
    has_user_role,
)
from models.datas_api.dashboard_common import (
    current_week_range as _current_week_range,
    date_range as _date_range,
    is_jiaowu as _is_jiaowu,
    is_moral_manager as _is_moral_manager,
    metric as _metric,
    normalize_top_n as _normalize_top_n,
    now_text as _now_text,
    safe_count as _safe_count,
    safe_query_all as _safe_query_all,
)
from models.datas_api.dashboard_overview import (
    build_overview_cards as _base_overview_cards,
)
from models.datas_api.dashboard_teaching import (
    build_filegather_summary as _build_filegather_summary,
    current_course_snapshot as _current_course_snapshot,
    find_current_period as _find_current_period,
    format_week_schedule_file as _format_week_schedule_file,
    minutes_from_time as _minutes_from_time,
    month_keys_for_range as _month_keys_for_range,
    schedule_files_for_range as _schedule_files_for_range,
    schedule_frames_for_range as _schedule_frames_for_range,
    teacher_lesson_counts as _teacher_lesson_counts,
    teacher_lesson_counts_from_files as _teacher_lesson_counts_from_files,
    teacher_subject_lookup as _teacher_subject_lookup,
    week_start_from_schedule_filename as _week_start_from_schedule_filename,
)
from models.datas_api.dashboard_moral import (
    class_score_rank as _class_score_rank,
    daily_event_mix as _daily_event_mix,
    daily_record_trend as _daily_record_trend,
    score_distribution as _score_distribution,
)
from models.datas_api.dashboard_class import (
    build_gender_mix as _build_gender_mix,
    build_score_band as _build_score_band,
    compute_class_stats as _compute_class_stats,
    filter_birthday_this_month as _filter_birthday_this_month,
    filter_birthday_this_week as _filter_birthday_this_week,
    format_birthday_list as _format_birthday_list,
)
from models.datas_api.dashboard_workbench import (
    build_teacher_workbench_response as _build_teacher_workbench_response,
    get_teacher_invigilation_tasks as _get_teacher_invigilation_tasks,
    get_teacher_moral_stats as _get_teacher_moral_stats,
    get_teacher_publication_stats as _get_teacher_publication_stats,
    get_teacher_today_lessons as _get_teacher_today_lessons,
)
from models.datas_api.dashboard_invigilation import (
    build_invigilation_dashboard_response as _build_invigilation_dashboard_response,
    get_invigilation_conflict_count as _get_invigilation_conflict_count,
    get_invigilation_conflict_slots as _get_invigilation_conflict_slots,
    get_invigilation_notification_failed as _get_invigilation_notification_failed,
    get_invigilation_notification_stats as _get_invigilation_notification_stats,
    get_invigilation_project_stats as _get_invigilation_project_stats,
    get_invigilation_recent_projects as _get_invigilation_recent_projects,
    get_invigilation_slot_stats as _get_invigilation_slot_stats,
    get_invigilation_teacher_workload as _get_invigilation_teacher_workload,
    get_invigilation_unarranged_slots as _get_invigilation_unarranged_slots,
)
from models.datas_api.dashboard_leave import (
    build_leave_by_class_chart as _build_leave_by_class_chart,
    compute_attendance_risk_insights as _compute_attendance_risk_insights,
    compute_class_leave_insights as _compute_class_leave_insights,
    compute_leave_stats as _compute_leave_stats,
    query_active_leave_records as _query_active_leave_records,
)
from models.lesson.lesson import Lesson

router = APIRouter(prefix="/dashboard", tags=["数据驾驶舱"])


class _ClosingSQLiteConnection:
    """Delegate sqlite connection access and close after with blocks."""

    def __init__(self, conn):
        self._conn = conn

    def __enter__(self):
        self._conn.__enter__()
        return self._conn

    def __exit__(self, exc_type, exc, tb):
        try:
            return self._conn.__exit__(exc_type, exc, tb)
        finally:
            self._conn.close()

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def close(self):
        return self._conn.close()


@router.get("/overview", summary="当前用户数据驾驶舱总览")
async def get_dashboard_overview(user: User = Depends(get_current_user)):
    cards = _base_overview_cards(user)
    modules = [
        {"title": "德育驾驶舱", "route": "/dashboard/moral", "visible": _is_moral_manager(user) or has_user_role(user, "cleader")},
        {"title": "教务驾驶舱", "route": "/dashboard/teaching", "visible": _is_jiaowu(user)},
    ]
    alerts = []
    with get_moral_db() as db:
        if _is_moral_manager(user):
            low_score = _safe_count(db, "SELECT COUNT(*) FROM moral_evaluation WHERE total_score < 60")
            if low_score:
                alerts.append({"level": "warning", "title": "低分学生关注", "message": f"当前有 {low_score} 名学生德育分低于 60 分"})
    return {
        "success": True,
        "data": {
            "cards": cards,
            "modules": [item for item in modules if item["visible"]],
            "alerts": alerts,
            "updated_at": _now_text(),
        },
    }


@router.get("/moral/summary", summary="德育驾驶舱总览")
async def get_moral_dashboard_summary(
    top_n: int = Query(5, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    """德育驾驶舱：德育分分布、日常记录、低分学生关注、请假出勤风险。
    Batch47: 增加请假与出勤风险数据展示。
    """
    if not (_is_moral_manager(user) or has_user_role(user, "cleader")):
        raise HTTPException(status_code=403, detail="无德育驾驶舱权限")
    top_n = _normalize_top_n(top_n)

    # Determine class filter for cleader
    class_filter = None
    with get_moral_db() as db:
        if not _is_moral_manager(user) and has_user_role(user, "cleader"):
            my_class_id = get_teacher_class_id(user, db)
            if my_class_id:
                class_info = db.query_one("SELECT class_name FROM class WHERE class_id = %s", (my_class_id,))
                if class_info:
                    class_filter = class_info["class_name"]

    with get_moral_db() as db:
        conditions = ["s.status = '在校'"]
        params = []
        if class_filter:
            my_class_id = get_teacher_class_id(user, db)
            if not my_class_id:
                conditions.append("1 = 0")
            else:
                conditions.append("s.class_id = %s")
                params.append(my_class_id)

        where_clause = " AND ".join(conditions)
        student_count = _safe_count(db, f"SELECT COUNT(*) FROM student s WHERE {where_clause}", tuple(params))
        daily_count = _safe_count(
            db,
            f"""SELECT COUNT(*)
                FROM student_daily_record dr
                JOIN student s ON dr.student_id = s.student_id
                WHERE dr.is_deleted = 0 AND {where_clause}""",
            tuple(params),
        )
        avg_score = db.query_value(
            f"""SELECT AVG(me.total_score)
                FROM moral_evaluation me
                JOIN student s ON me.student_id = s.student_id
                WHERE {where_clause}""",
            tuple(params),
        )
        low_students = db.query_all(
            f"""SELECT s.student_id, s.name, c.class_name, me.total_score, me.level
                FROM moral_evaluation me
                JOIN student s ON me.student_id = s.student_id
                JOIN class c ON s.class_id = c.class_id
                WHERE {where_clause} AND me.total_score < 60
                ORDER BY me.total_score ASC
                LIMIT {top_n}""",
            tuple(params),
        )
        query_params = tuple(params)
        charts = {
            "score_distribution": _score_distribution(db, where_clause, query_params),
            "daily_event_mix": _daily_event_mix(db, where_clause, query_params),
            "daily_record_trend": _daily_record_trend(db, where_clause, query_params),
            "class_score_rank": _class_score_rank(db, where_clause, query_params, top_n),
        }

    # Batch47: 请假与出勤风险数据
    leave_records = _query_active_leave_records(class_filter=class_filter, limit=50)
    leave_stats = _compute_leave_stats(class_filter=class_filter)
    leave_by_class = _build_leave_by_class_chart(limit=top_n) if not class_filter else []
    leave_insights = _compute_attendance_risk_insights(leave_records, class_filter)

    # Batch50: 将 leave_by_class 添加到 charts
    charts["leave_by_class"] = leave_by_class

    # Batch47: Build insights combining moral warnings
    insights = []
    if len(low_students) > 0:
        insights.append({
            "type": "warning",
            "title": "低分学生关注",
            "message": f"当前有 {len(low_students)} 名学生德育分低于 60 分，建议重点关注。",
            "action_route": "/moral/evaluation"
        })
    insights.extend(leave_insights)
    if not insights and student_count > 0:
        insights.append({
            "type": "success",
            "title": "德育运行正常",
            "message": "当前德育评价与出勤状况良好。",
            "action_route": None
        })

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("可见学生", student_count, "人"),
                _metric("日常记录", daily_count, "条", "/moral/daily-record"),
                _metric("平均德育分", round(float(avg_score or 0), 1), "分", "/moral/evaluation"),
                _metric("当前请假", leave_stats["active_leave_count"], "人", "/leave-record"),
            ],
            "charts": charts,
            "tables": {
                "low_students": low_students,
                "leave_students": leave_records[:20],
            },
            "insights": insights,
            "top_n": top_n,
            "updated_at": _now_text(),
        },
    }


@router.get("/teaching/summary", summary="教务驾驶舱总览")
async def get_teaching_dashboard_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    top_n: int = Query(5, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    """教务驾驶舱：文件上传流转、课表覆盖、教师课时、教学运行态势。

    Batch46: 增强文件深度指标、教学运行 insights。
    注意：教务驾驶舱不展示请假学生数据（tables 不含 leave_students）。
    """
    if not _is_jiaowu(user):
        raise HTTPException(status_code=403, detail="无教务驾驶舱权限")

    week_range = _current_week_range()
    if not isinstance(start_date, date):
        start_date = None
    if not isinstance(end_date, date):
        end_date = None
    start_date = start_date or week_range["start"]
    end_date = end_date or week_range["end"]
    top_n = _normalize_top_n(top_n)
    if (end_date - start_date).days > 62:
        raise HTTPException(status_code=400, detail="统计时间跨度不能超过 62 天")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")

    with get_moral_db() as db:
        class_count = _safe_count(db, "SELECT COUNT(*) FROM class WHERE is_active = 1")
        student_count = _safe_count(db, "SELECT COUNT(*) FROM student WHERE status = '在校'")
        teacher_count = _safe_count(db, "SELECT COUNT(*) FROM teacher WHERE COALESCE(identity_type, 'teacher') = 'teacher' AND is_active = 1")
        class_size_rank = _safe_query_all(
            db,
            f"""SELECT c.class_name, COUNT(s.student_id) AS student_count
                FROM class c
                LEFT JOIN student s ON s.class_id = c.class_id AND s.status = '在校'
                WHERE c.is_active = 1
                GROUP BY c.class_id, c.class_name
                ORDER BY student_count DESC
                LIMIT {top_n}""",
        )

    workload = _teacher_lesson_counts(start_date, end_date)
    workload_rank = workload["rows"][:top_n]
    current_course = _current_course_snapshot()

    # Batch 23 + 46: File upload summary with depth metrics
    current_month = start_date.strftime("%Y%m") if start_date else None
    filegather_summary = _build_filegather_summary(current_month)
    fg_cards = filegather_summary["cards"]
    fg_charts = filegather_summary["charts"]
    fg_tables = filegather_summary["tables"]

    # Batch46: 深度指标
    completion_rate = filegather_summary.get("completion_rate", 0.0)
    overdue_pending_count = filegather_summary.get("overdue_pending_count", 0)
    pending_file_list = filegather_summary.get("pending_file_list", [])
    recent_file_list = filegather_summary.get("recent_file_list", [])

    # Batch46: 计算 insights
    insights = []

    # 1. 逾期文件提示
    if overdue_pending_count > 0:
        insights.append({
            "type": "warning",
            "title": "逾期文件待处理",
            "message": f"有 {overdue_pending_count} 个文件超过3天未处理，建议优先处理避免积压。",
            "action_route": "/filegather"
        })

    # 2. 课表覆盖不足提示
    covered_dates = workload.get("covered_dates", [])
    expected_days = (end_date - start_date).days + 1
    if len(covered_dates) < expected_days * 0.5:
        insights.append({
            "type": "warning",
            "title": "课表覆盖不足",
            "message": f"指定时间段内仅有 {len(covered_dates)} 天课表数据，建议检查课表文件是否完整。",
            "action_route": "/schedules"
        })

    # 3. 教师课时负载差异明显
    if len(workload["rows"]) >= 3:
        counts = [row["lesson_count"] for row in workload["rows"]]
        max_count = max(counts)
        avg_count = sum(counts) / len(counts)
        if max_count > avg_count * 1.5:
            insights.append({
                "type": "info",
                "title": "课时负载差异",
                "message": f"最高课时教师课时数为 {max_count}，平均值 {round(avg_count, 1)}，建议关注排课均衡。",
                "action_route": "/schedules"
            })

    # 4. 无异常时正向提示
    if not insights:
        if completion_rate >= 80 and len(covered_dates) >= expected_days * 0.8:
            insights.append({
                "type": "success",
                "title": "教学运行正常",
                "message": "文件处理及时，课表覆盖完整，教学运行态势良好。",
                "action_route": None
            })

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("班级", class_count, "个", "/moral/config/class"),
                _metric("在校学生", student_count, "人", "/moral/config/student"),
                _metric("教师账号", teacher_count, "人", "/teacher-manage"),
                _metric("区间课时", sum(row["lesson_count"] for row in workload["rows"]), "节"),
                _metric("当前课节", current_course["current_period"] or "非上课", ""),
                _metric("正在上课", current_course["active_class_count"], "个班"),
                _metric("待处理文件", fg_cards[0]["value"] if len(fg_cards) > 0 else 0, "份", "/filegather"),
                _metric("本月文件", fg_cards[1]["value"] if len(fg_cards) > 1 else 0, "份", "/filegather"),
                _metric("已完成文件", fg_cards[2]["value"] if len(fg_cards) > 2 else 0, "份", "/filegather"),
                _metric("完成率", completion_rate, "%", "/filegather"),
                _metric("逾期文件", overdue_pending_count, "份", "/filegather"),
            ],
            "charts": {
                "teacher_workload_rank": workload_rank,
                "class_size_rank": class_size_rank,
                "resource_mix": [
                    {"name": "班级", "value": class_count},
                    {"name": "学生", "value": student_count},
                    {"name": "教师", "value": teacher_count},
                ],
                "file_upload_status": fg_charts["file_upload_status"],
            },
            "tables": {
                "teacher_workload_rank": workload_rank,
                "file_upload_top_users": fg_tables["file_upload_top_users"],
                "pending_file_list": fg_tables.get("pending_file_list", []),
                "recent_file_list": fg_tables.get("recent_file_list", []),
                # 注意：教务驾驶舱不返回 leave_students
            },
            "current_course": current_course,
            "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "covered_dates": workload["covered_dates"],
            "source_files": workload["source_files"],
            "top_n": top_n,
            "message": workload["message"],
            "insights": insights,
            "updated_at": _now_text(),
        },
    }


# =============================================================================
# 第二阶段：班级驾驶舱 & 教师工作台
# =============================================================================

def _get_homework_db():
    """获取作业数据库连接"""
    # 延迟导入避免循环依赖
    from models.datas_api.repositories.sqlite_base import get_sqlite_connection

    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "databases", "homework.db")
    conn = get_sqlite_connection(db_path, row_factory=sqlite3.Row)
    return _ClosingSQLiteConnection(conn)


def _get_inout_db():
    """获取请假数据库连接"""
    # 延迟导入避免循环依赖
    from models.datas_api.repositories.sqlite_base import get_sqlite_connection

    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "databases", "inout.db")
    conn = get_sqlite_connection(db_path, row_factory=sqlite3.Row)
    return _ClosingSQLiteConnection(conn)


@router.get("/class/summary", summary="班级驾驶舱总览")
async def get_class_dashboard_summary(
    class_id: Optional[int] = Query(None, description="班级ID，班主任默认本班"),
    top_n: int = Query(5, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    """班级驾驶舱：班级基础、学习活动、德育表现、出勤事务、生日关怀。
    Batch47: 增强请假学生名单展示、出勤 insights。
    """
    top_n = _normalize_top_n(top_n)
    with get_moral_db() as db:
        if not isinstance(class_id, int):
            class_id = None

        # 确定查询班级
        if not class_id:
            if has_user_role(user, "cleader") and not _is_moral_manager(user):
                class_id = get_teacher_class_id(user, db)
                if not class_id:
                    raise HTTPException(status_code=403, detail="未找到班主任班级")
            elif _is_moral_manager(user) or _is_jiaowu(user):
                # 教务/管理员默认第一个班级
                first_class = db.query_one("SELECT class_id FROM class WHERE is_active = 1 ORDER BY class_id LIMIT 1")
                class_id = first_class["class_id"] if first_class else None
            else:
                raise HTTPException(status_code=403, detail="无班级驾驶舱权限")

        if not class_id:
            raise HTTPException(status_code=404, detail="班级不存在")

        if not (_is_moral_manager(user) or _is_jiaowu(user)):
            if not has_user_role(user, "cleader"):
                raise HTTPException(status_code=403, detail="无班级驾驶舱权限")
            my_class_id = get_teacher_class_id(user, db)
            if not my_class_id or my_class_id != class_id:
                raise HTTPException(status_code=403, detail="只能查看自己班级的驾驶舱")

        # 班级基础信息
        class_info = db.query_one("SELECT * FROM class WHERE class_id = %s AND is_active = 1", (class_id,))
        if not class_info:
            raise HTTPException(status_code=404, detail="班级不存在")

        class_name = class_info["class_name"]

        # 学生统计
        students = db.query_all(
            "SELECT student_id, name, gender, birthday FROM student WHERE class_id = %s AND status = '在校'",
            (class_id,)
        )

        # 德育评价统计
        eval_stats = db.query_one(
            """SELECT
                AVG(total_score) AS avg_score,
                MIN(total_score) AS min_score,
                MAX(total_score) AS max_score,
                COUNT(*) AS evaluated_count,
                SUM(CASE WHEN total_score < 60 THEN 1 ELSE 0 END) AS low_count,
                SUM(CASE WHEN total_score >= 60 THEN 1 ELSE 0 END) AS pass_count
            FROM moral_evaluation WHERE class_id = %s""",
            (class_id,)
        )
        class_stats = _compute_class_stats(students, eval_stats)
        student_count = class_stats["student_count"]
        male_count = class_stats["male_count"]
        female_count = class_stats["female_count"]
        unknown_gender_count = class_stats["unknown_gender_count"]
        avg_score = class_stats["avg_score"]
        low_count = class_stats["low_count"]
        unevaluated_count = class_stats["unevaluated_count"]

        low_students = db.query_all(
            """SELECT s.student_id, s.name, me.total_score
            FROM moral_evaluation me
            JOIN student s ON me.student_id = s.student_id
            WHERE me.class_id = %s AND me.total_score < 60
            ORDER BY me.total_score ASC LIMIT %s""",
            (class_id, top_n)
        )

        # 本月/本周生日学生
        today = date.today()
        birthday_this_month = _filter_birthday_this_month(students, today.month)
        birthday_this_week = _filter_birthday_this_week(students, today)

    # 学习活动统计（作业、公告）
    homework_count = 0
    announcement_count = 0
    try:
        with _get_homework_db() as hw_db:
            cursor = hw_db.cursor()
            # 作业数
            cursor.execute(
                "SELECT COUNT(*) FROM homework WHERE class_code = ? AND deleted = 0",
                (class_name,)
            )
            homework_count = cursor.fetchone()[0] or 0
            # 公告数
            cursor.execute(
                "SELECT COUNT(*) FROM announcements WHERE class_code = ? AND deleted = 0",
                (class_name,)
            )
            announcement_count = cursor.fetchone()[0] or 0
    except Exception:
        pass

    # Batch47: 出勤统计（请假）使用新 helper
    leave_records = _query_active_leave_records(class_filter=class_name, limit=50)
    leave_stats = _compute_leave_stats(class_filter=class_name)
    active_leave_count = len(leave_records)
    leave_insights = _compute_class_leave_insights(leave_records, class_name)

    # Batch47: Build insights combining class warnings
    insights = []
    if low_count > 0:
        insights.append({
            "type": "warning",
            "title": "低分学生关注",
            "message": f"{class_name} 有 {low_count} 名学生德育分低于 60 分。",
            "action_route": "/moral/evaluation"
        })
    if unevaluated_count > 0:
        insights.append({
            "type": "info",
            "title": "待评价学生",
            "message": f"{class_name} 有 {unevaluated_count} 名学生未完成德育评价。",
            "action_route": "/moral/evaluation"
        })
    insights.extend(leave_insights)
    # Remove duplicate success insight if already present
    success_insights = [i for i in insights if i["type"] == "success"]
    if len(insights) > 1 and success_insights:
        insights = [i for i in insights if i["type"] != "success"]
    if not insights:
        insights.append({
            "type": "success",
            "title": "班级运行正常",
            "message": f"{class_name} 当前出勤与德育状况良好。",
            "action_route": None
        })

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("班级人数", student_count, "人", "/moral/config/student"),
                _metric("男生", male_count, "人"),
                _metric("女生", female_count, "人"),
                _metric("性别未维护", unknown_gender_count, "人"),
                _metric("平均德育分", avg_score, "分", "/moral/evaluation"),
                _metric("低分学生", low_count, "人"),
                _metric("本月作业", homework_count, "份", "/homework"),
                _metric("本月公告", announcement_count, "份"),
                _metric("请假人数", active_leave_count, "人", "/leave-record"),
            ],
            "charts": {
                "gender_mix": _build_gender_mix(students),
                "score_band": _build_score_band(eval_stats, student_count),
            },
            "tables": {
                "low_students": low_students,
                "birthday_this_month": _format_birthday_list(birthday_this_month),
                "birthday_this_week": _format_birthday_list(birthday_this_week),
                "leave_students": leave_records[:20],
            },
            "insights": insights,
            "class_info": {
                "class_id": class_id,
                "class_name": class_name,
            },
            "top_n": top_n,
            "updated_at": _now_text(),
        },
    }


@router.get("/teacher/workbench", summary="教师个人工作台")
async def get_teacher_workbench(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
):
    """教师工作台：今日事项、发布内容、德育参与、监考任务"""
    teacher_name = user.username
    today_str = date.today().isoformat()
    today = date.today()
    if not isinstance(start_date, date):
        start_date = None
    if not isinstance(end_date, date):
        end_date = None
    week_range = _current_week_range()
    start_date = start_date or week_range["start"]
    end_date = end_date or week_range["end"]
    if (end_date - start_date).days > 30:
        raise HTTPException(status_code=400, detail="教师个人课时统计时间跨度不能超过 31 天")
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")

    # 今日课程（从课表）
    lesson = Lesson()
    today_lessons = _get_teacher_today_lessons(teacher_name, lesson)

    # 发布统计（作业、公告）
    publication_stats = _get_teacher_publication_stats(teacher_name, _get_homework_db)

    # 德育参与（自己创建的日常记录、点滴记录）
    moral_stats = _get_teacher_moral_stats(teacher_name, get_moral_db, _safe_count)

    # 监考任务（近期监考安排）
    invigilation_tasks = _get_teacher_invigilation_tasks(teacher_name, today_str, _get_invigilation_db)

    # 课时统计
    lesson_workload = _teacher_lesson_counts_from_files(start_date, end_date, teacher_name=teacher_name)

    # 组装返回数据
    return _build_teacher_workbench_response(
        teacher_name=teacher_name,
        today_lessons=today_lessons,
        publication_stats=publication_stats,
        moral_stats=moral_stats,
        invigilation_tasks=invigilation_tasks,
        lesson_workload=lesson_workload,
        start_date=start_date,
        end_date=end_date,
        metric=_metric,
        now_text=_now_text,
    )


def _get_invigilation_db():
    """获取监考数据库连接"""
    # 延迟导入避免循环依赖
    from models.datas_api.repositories.sqlite_base import get_sqlite_connection

    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "databases", "invigilation.db")
    conn = get_sqlite_connection(db_path, row_factory=sqlite3.Row)
    return _ClosingSQLiteConnection(conn)


@router.get("/invigilation/summary", summary="监考驾驶舱总览")
async def get_invigilation_dashboard_summary(
    top_n: int = Query(5, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    """监考驾驶舱：考试项目状态、安排完整度、通知状态、教师负载、预警列表"""
    if not _is_jiaowu(user):
        raise HTTPException(status_code=403, detail="无监考驾驶舱权限")
    top_n = _normalize_top_n(top_n)

    today_str = date.today().isoformat()

    # 调用 dashboard_invigilation 辅助函数
    project_stats = _get_invigilation_project_stats(_get_invigilation_db)
    slot_stats = _get_invigilation_slot_stats(_get_invigilation_db, today_str)
    conflict_count = _get_invigilation_conflict_count(_get_invigilation_db, today_str)
    notification_stats = _get_invigilation_notification_stats(_get_invigilation_db)
    teacher_workload = _get_invigilation_teacher_workload(_get_invigilation_db, today_str, top_n)
    unarranged_slots = _get_invigilation_unarranged_slots(_get_invigilation_db, today_str)
    conflict_slots = _get_invigilation_conflict_slots(_get_invigilation_db, today_str)
    notification_failed = _get_invigilation_notification_failed(_get_invigilation_db)
    recent_projects = _get_invigilation_recent_projects(_get_invigilation_db, top_n)

    # 组装返回结构
    return _build_invigilation_dashboard_response(
        project_stats=project_stats,
        slot_stats=slot_stats,
        conflict_count=conflict_count,
        notification_stats=notification_stats,
        teacher_workload=teacher_workload,
        unarranged_slots=unarranged_slots,
        conflict_slots=conflict_slots,
        notification_failed=notification_failed,
        recent_projects=recent_projects,
        top_n=top_n,
        metric=_metric,
        now_text=_now_text,
    )


# =============================================================================
# 第四阶段：系统运维驾驶舱
# =============================================================================

import glob as glob_module


def _get_system_sqlite_db(db_path: str):
    """获取系统运维驾驶舱数据库连接（用于 moral.db / task.db 统计）"""
    # 延迟导入避免循环依赖
    from models.datas_api.repositories.sqlite_base import get_sqlite_connection

    conn = get_sqlite_connection(db_path, row_factory=sqlite3.Row)
    return _ClosingSQLiteConnection(conn)


def _get_db_stats(db_path: str) -> Dict[str, object]:
    """获取数据库统计信息"""
    if not os.path.exists(db_path):
        return {"exists": False, "size_kb": 0, "tables": []}
    size_kb = os.path.getsize(db_path) / 1024
    tables = []
    try:
        with _get_system_sqlite_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            table_names = [row["name"] for row in cursor.fetchall()]
            for table_name in table_names:
                cursor.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
                count = cursor.fetchone()["count"]
                tables.append({"name": table_name, "count": count})
    except Exception:
        pass
    return {"exists": True, "size_kb": round(size_kb, 1), "tables": tables}


@router.get("/system/summary", summary="系统运维驾驶舱总览")
async def get_system_dashboard_summary(user: User = Depends(get_current_user)):
    """系统运维驾驶舱：服务状态、数据库统计、用户权限、操作审计"""
    if not is_admin_user(user):
        raise HTTPException(status_code=403, detail="无系统运维驾驶舱权限")

    # 1. 数据库统计
    db_dir = os.path.join(os.path.dirname(__file__), "..", "..", "databases")
    db_files = []
    total_size_kb = 0
    for db_name in ["moral.db", "homework.db", "inout.db", "invigilation.db", "task.db"]:
        db_path = os.path.join(db_dir, db_name)
        stats = _get_db_stats(db_path)
        stats["name"] = db_name
        db_files.append(stats)
        if stats["exists"]:
            total_size_kb += stats["size_kb"]

    # 2. 用户统计（从 moral.db teacher 表）
    user_count = 0
    role_distribution = []
    try:
        moral_db_path = os.path.join(db_dir, "moral.db")
        if os.path.exists(moral_db_path):
            with _get_system_sqlite_db(moral_db_path) as conn:
                cursor = conn.cursor()
                # 从 teacher 表统计用户
                cursor.execute("SELECT COUNT(*) AS count FROM teacher WHERE identity_type = 'teacher'")
                user_count = cursor.fetchone()["count"]
                # 统计角色分布（role 字段可能包含多角色如 teacher/cleader）
                cursor.execute("SELECT role, COUNT(*) AS count FROM teacher WHERE identity_type = 'teacher' GROUP BY role")
                for row in cursor.fetchall():
                    role_distribution.append({"role": row["role"] or "teacher", "count": row["count"]})
    except Exception:
        pass

    # 3. 教师统计（从 moral.db teacher 表）
    teacher_stats = {"total": 0, "teacher": 0, "admin": 0, "other": 0}
    try:
        moral_db_path = os.path.join(db_dir, "moral.db")
        if os.path.exists(moral_db_path):
            with _get_system_sqlite_db(moral_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN COALESCE(identity_type, 'teacher') = 'teacher' THEN 1 ELSE 0 END) AS teacher,
                        SUM(CASE WHEN identity_type = 'admin' THEN 1 ELSE 0 END) AS admin,
                        SUM(CASE WHEN identity_type IS NOT NULL AND identity_type NOT IN ('teacher', 'admin') THEN 1 ELSE 0 END) AS other
                    FROM teacher WHERE is_active = 1"""
                )
                row = cursor.fetchone()
                teacher_stats = dict(row) if row else teacher_stats
    except Exception:
        pass

    # 4. API 权限风险检测（从 moral.db api_permission_config）
    api_permission_risks = []
    try:
        moral_db_path = os.path.join(db_dir, "moral.db")
        if os.path.exists(moral_db_path):
            with _get_system_sqlite_db(moral_db_path) as conn:
                cursor = conn.cursor()
                # 查找敏感 API 允许了普通教师权限的配置
                cursor.execute(
                    """SELECT api_path, allowed_roles, policy_mode, description
                       FROM api_permission_config
                       WHERE is_active = 1
                         AND (
                           (policy_mode = 'any_role' AND allowed_roles LIKE '%teacher%')
                           OR (policy_mode = 'any_role' AND allowed_roles LIKE '%student%')
                           OR (policy_mode = 'any_role' AND allowed_roles LIKE '%parent%')
                         )"""
                )
                for row in cursor.fetchall():
                    api_permission_risks.append({
                        "api_path": row["api_path"],
                        "allowed_roles": row["allowed_roles"],
                        "policy_mode": row["policy_mode"],
                        "description": row["description"],
                    })
    except Exception:
        pass

    # 5. 操作日志统计（从 moral_operation_log）
    operation_stats = []
    recent_operations = []
    try:
        moral_db_path = os.path.join(db_dir, "moral.db")
        if os.path.exists(moral_db_path):
            with _get_system_sqlite_db(moral_db_path) as conn:
                cursor = conn.cursor()
                # 操作类型统计
                cursor.execute(
                    """SELECT operation, COUNT(*) AS count
                       FROM moral_operation_log
                       GROUP BY operation
                       ORDER BY count DESC"""
                )
                for row in cursor.fetchall():
                    operation_stats.append({"type": row["operation"], "count": row["count"]})
                # 最近敏感操作（删除、更新）
                cursor.execute(
                    """SELECT operation, table_name, record_id, operator, created_at, reason, new_data
                       FROM moral_operation_log
                       WHERE operation IN ('DELETE', 'UPDATE')
                       ORDER BY created_at DESC
                       LIMIT 10"""
                )
                for row in cursor.fetchall():
                    recent_operations.append({
                        "operation_type": row["operation"],
                        "table_name": row["table_name"],
                        "record_id": row["record_id"],
                        "operator": row["operator"],
                        "operated_at": row["created_at"],
                        "detail": row["reason"] or row["new_data"] or "",
                    })
    except Exception:
        pass

    # 6. 任务状态（从 task.db）
    task_stats = {"total": 0, "running": 0, "failed": 0, "success": 0}
    try:
        task_db_path = os.path.join(db_dir, "task.db")
        if os.path.exists(task_db_path):
            with _get_system_sqlite_db(task_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduled_tasks'")
                if cursor.fetchone():
                    cursor.execute(
                        """SELECT
                            COUNT(*) AS total,
                            SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running,
                            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success
                        FROM scheduled_tasks"""
                    )
                    row = cursor.fetchone()
                    task_stats = dict(row) if row else task_stats
    except Exception:
        pass

    # 计算表记录总数
    total_records = 0
    for db in db_files:
        if db["exists"]:
            total_records += sum(t["count"] for t in db["tables"])

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("数据库文件", len([d for d in db_files if d["exists"]]), "个"),
                _metric("总大小", round(total_size_kb / 1024, 2), "MB"),
                _metric("总记录数", total_records, "条"),
                _metric("活跃用户", user_count, "人", "/member-manage"),
                _metric("教师账号", teacher_stats.get("teacher", 0), "人", "/teacher-manage"),
                _metric("权限风险", len(api_permission_risks), "项", "/moral/config/api-permission"),
            ],
            "charts": {
                "role_distribution": role_distribution,
                "operation_stats": operation_stats,
                "teacher_identity": [
                    {"name": "教师", "value": teacher_stats.get("teacher", 0)},
                    {"name": "管理员", "value": teacher_stats.get("admin", 0)},
                    {"name": "其他", "value": teacher_stats.get("other", 0)},
                ],
            },
            "tables": {
                "db_files": db_files,
                "api_permission_risks": api_permission_risks,
                "recent_operations": recent_operations,
            },
            "task_stats": task_stats,
            "updated_at": _now_text(),
        },
    }
