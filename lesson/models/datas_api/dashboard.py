# -*- coding: utf-8 -*-
"""数据驾驶舱 API。"""

import os
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from models.datas_api.auth import User, get_current_user, is_admin_user
from models.datas_api.moral.base import (
    check_moral_permission,
    get_moral_db,
    get_teacher_class_id,
    has_user_role,
)
from models.lesson.lesson import Lesson

router = APIRouter(prefix="/dashboard", tags=["数据驾驶舱"])


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _is_jiaowu(user: User) -> bool:
    return is_admin_user(user) or has_user_role(user, "jiaowu")


def _is_moral_manager(user: User) -> bool:
    return is_admin_user(user) or any(has_user_role(user, role) for role in ["jiaowu", "xuefa"])


def _date_range(start_date: date, end_date: date) -> List[date]:
    days = (end_date - start_date).days
    if days < 0:
        return []
    return [start_date + timedelta(days=offset) for offset in range(days + 1)]


def _metric(label: str, value, unit: str = "", route: str = "") -> Dict[str, object]:
    return {"label": label, "value": value, "unit": unit, "route": route}


def _normalize_top_n(top_n: int = 5) -> int:
    try:
        value = int(top_n)
    except Exception:
        value = 5
    return max(1, min(value, 50))


def _current_week_range() -> Dict[str, date]:
    today = date.today()
    start = today - timedelta(days=today.weekday())
    return {"start": start, "end": start + timedelta(days=6)}


def _safe_count(db, sql: str, params=None) -> int:
    try:
        return int(db.query_value(sql, params) or 0)
    except Exception:
        return 0


def _safe_query_all(db, sql: str, params=None) -> List[Dict[str, object]]:
    try:
        return db.query_all(sql, params) or []
    except Exception:
        return []


def _score_distribution(db, where_clause: str, params: tuple) -> List[Dict[str, object]]:
    rows = _safe_query_all(
        db,
        f"""SELECT
                SUM(CASE WHEN me.total_score >= 90 THEN 1 ELSE 0 END) AS excellent,
                SUM(CASE WHEN me.total_score >= 80 AND me.total_score < 90 THEN 1 ELSE 0 END) AS good,
                SUM(CASE WHEN me.total_score >= 70 AND me.total_score < 80 THEN 1 ELSE 0 END) AS normal,
                SUM(CASE WHEN me.total_score >= 60 AND me.total_score < 70 THEN 1 ELSE 0 END) AS pass,
                SUM(CASE WHEN me.total_score < 60 THEN 1 ELSE 0 END) AS risk
            FROM moral_evaluation me
            JOIN student s ON me.student_id = s.student_id
            WHERE {where_clause}""",
        params,
    )
    values = rows[0] if rows else {}
    return [
        {"name": "90分以上", "value": int(values.get("excellent") or 0)},
        {"name": "80-89分", "value": int(values.get("good") or 0)},
        {"name": "70-79分", "value": int(values.get("normal") or 0)},
        {"name": "60-69分", "value": int(values.get("pass") or 0)},
        {"name": "60分以下", "value": int(values.get("risk") or 0)},
    ]


def _daily_event_mix(db, where_clause: str, params: tuple) -> List[Dict[str, object]]:
    rows = _safe_query_all(
        db,
        f"""SELECT det.event_type, COUNT(*) AS count
            FROM student_daily_record dr
            JOIN daily_event_type det ON dr.event_id = det.event_id
            JOIN student s ON dr.student_id = s.student_id
            WHERE dr.is_deleted = 0 AND {where_clause}
            GROUP BY det.event_type""",
        params,
    )
    counters = {int(row.get("event_type") or 0): int(row.get("count") or 0) for row in rows}
    return [
        {"name": "正向记录", "value": counters.get(1, 0)},
        {"name": "负向记录", "value": counters.get(2, 0)},
    ]


def _daily_record_trend(db, where_clause: str, params: tuple) -> List[Dict[str, object]]:
    start = date.today() - timedelta(days=13)
    rows = _safe_query_all(
        db,
        f"""SELECT dr.record_date, COUNT(*) AS count
            FROM student_daily_record dr
            JOIN student s ON dr.student_id = s.student_id
            WHERE dr.is_deleted = 0 AND dr.record_date >= %s AND {where_clause}
            GROUP BY dr.record_date
            ORDER BY dr.record_date ASC""",
        (start.isoformat(), *params),
    )
    counts = {str(row.get("record_date"))[:10]: int(row.get("count") or 0) for row in rows}
    return [
        {"date": (start + timedelta(days=offset)).isoformat(), "count": counts.get((start + timedelta(days=offset)).isoformat(), 0)}
        for offset in range(14)
    ]


def _class_score_rank(db, where_clause: str, params: tuple, top_n: int) -> List[Dict[str, object]]:
    return _safe_query_all(
        db,
        f"""SELECT c.class_name, ROUND(AVG(me.total_score), 1) AS avg_score, COUNT(*) AS student_count
            FROM moral_evaluation me
            JOIN student s ON me.student_id = s.student_id
            JOIN class c ON me.class_id = c.class_id
            WHERE {where_clause}
            GROUP BY c.class_id, c.class_name
            ORDER BY avg_score DESC
            LIMIT {top_n}""",
        params,
    )


def _base_overview_cards(user: User) -> List[Dict[str, object]]:
    with get_moral_db() as db:
        cards = [
            _metric("在校学生", _safe_count(db, "SELECT COUNT(*) FROM student WHERE status = '在校'"), "人", "/moral/config/student"),
            _metric("启用班级", _safe_count(db, "SELECT COUNT(*) FROM class WHERE is_active = 1"), "个", "/moral/config/class"),
            _metric(
                "教师账号",
                _safe_count(db, "SELECT COUNT(*) FROM teacher WHERE COALESCE(identity_type, 'teacher') = 'teacher' AND is_active = 1"),
                "人",
                "/teacher-manage",
            ),
        ]

        if _is_moral_manager(user) or has_user_role(user, "cleader"):
            conditions = ["dr.is_deleted = 0"]
            params = []
            if not _is_moral_manager(user) and has_user_role(user, "cleader"):
                my_class_id = get_teacher_class_id(user, db)
                if my_class_id:
                    conditions.append("dr.class_id = %s")
                    params.append(my_class_id)
                else:
                    conditions.append("1 = 0")
            cards.append(_metric(
                "日常记录",
                _safe_count(db, f"SELECT COUNT(*) FROM student_daily_record dr WHERE {' AND '.join(conditions)}", tuple(params)),
                "条",
                "/moral/daily-record",
            ))

        return cards


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
    if not (_is_moral_manager(user) or has_user_role(user, "cleader")):
        raise HTTPException(status_code=403, detail="无德育驾驶舱权限")
    top_n = _normalize_top_n(top_n)

    with get_moral_db() as db:
        conditions = ["s.status = '在校'"]
        params = []
        if not _is_moral_manager(user) and has_user_role(user, "cleader"):
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

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("可见学生", student_count, "人"),
                _metric("日常记录", daily_count, "条", "/moral/daily-record"),
                _metric("平均德育分", round(float(avg_score or 0), 1), "分", "/moral/evaluation"),
            ],
            "charts": charts,
            "tables": {"low_students": low_students},
            "top_n": top_n,
            "updated_at": _now_text(),
        },
    }


def _schedule_frames_for_range(start_date: date, end_date: date) -> List[Dict[str, object]]:
    lesson = Lesson()
    frames = []
    for week_next, schedule_key in [(0, "current_schedule"), (1, "next_schedule")]:
        df = lesson.get_cache_data(schedule_key)
        if df is None or df.empty:
            continue
        week_info = lesson.get_cache_data("week_info")[week_next]
        monday = datetime.strptime(week_info[1], "%Y%m%d").date()
        frames.append({"df": df.copy(), "monday": monday, "week_next": week_next})
    return frames


def _teacher_lesson_counts(start_date: date, end_date: date) -> Dict[str, object]:
    return _teacher_lesson_counts_from_files(start_date, end_date)


def _month_keys_for_range(start_date: date, end_date: date) -> List[str]:
    keys = []
    current = start_date.replace(day=1)
    while current <= end_date:
        keys.append(current.strftime("%Y%m"))
        next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        current = next_month
    return keys


def _week_start_from_schedule_filename(file_name: str) -> Optional[date]:
    import re

    match = re.search(r"(20\d{6})", file_name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d").date()
    except Exception:
        return None


def _schedule_files_for_range(lesson: Lesson, start_date: date, end_date: date) -> List[Dict[str, object]]:
    files = []
    seen = set()
    for month_key in _month_keys_for_range(start_date, end_date):
        schedule_dir = os.path.join(lesson.lesson_dir, month_key, "class_schedule")
        if not os.path.isdir(schedule_dir):
            continue
        for file_name in os.listdir(schedule_dir):
            if file_name.startswith(".") or not file_name.lower().endswith((".xlsx", ".xls")):
                continue
            monday = _week_start_from_schedule_filename(file_name)
            if monday is None:
                continue
            sunday = monday + timedelta(days=6)
            if sunday < start_date or monday > end_date:
                continue
            file_path = os.path.join(schedule_dir, file_name)
            if file_path in seen:
                continue
            seen.add(file_path)
            files.append({"path": file_path, "monday": monday, "file_name": file_name})
    return sorted(files, key=lambda item: (item["monday"], item["file_name"]))


def _format_week_schedule_file(lesson: Lesson, file_path: str, monday: date) -> pd.DataFrame:
    week_num = monday.isocalendar()[1] + lesson.week_change
    week_flag = "单" if week_num % 2 == 1 else "双"
    df = lesson.load_excel_file(file_path)
    if df is None or df.empty:
        return pd.DataFrame()
    return lesson.schedule_service.format_schedule(df, week_flag, replace_flag=True, ignore=False)


def _teacher_lesson_counts_from_files(start_date: date, end_date: date, teacher_name: Optional[str] = None) -> Dict[str, object]:
    lesson = Lesson()
    counter = Counter()
    covered_dates = set()
    source_files = []
    lessons = []
    target_teacher = str(teacher_name).strip() if teacher_name else ""
    class_template = lesson.get_cache_data("class_template")
    class_names = class_template["class_name"].tolist() if class_template is not None and not class_template.empty else []
    teacher_template = lesson.get_cache_data("teacher_template")
    valid_teachers = set()
    if teacher_template is not None and not teacher_template.empty and "name" in teacher_template.columns:
        valid_teachers = {str(name).strip() for name in teacher_template["name"].tolist() if str(name).strip()}
    time_table = lesson.get_cache_data("time_table")
    period_lookup = {}
    if time_table is not None and not time_table.empty:
        for _, row in time_table.iterrows():
            order = str(row.get("order", "")).strip()
            period_lookup[order] = {
                "label": str(row.get("label") or order).strip(),
                "time_range": str(row.get("show_time") or row.get("time_table") or "").strip(),
            }

    for item in _schedule_files_for_range(lesson, start_date, end_date):
        df = _format_week_schedule_file(lesson, item["path"], item["monday"])
        if df.empty:
            continue
        source_files.append(item["file_name"])
        weekday_column = "weekday" if "weekday" in df.columns else "week" if "week" in df.columns else ""
        if not weekday_column:
            continue
        teacher_df = lesson.schedule_service.replace_subject_teacher(df, teacher_flag=True)
        for idx, row in teacher_df.iterrows():
            try:
                weekday = int(row.get(weekday_column))
            except Exception:
                continue
            actual_date = item["monday"] + timedelta(days=weekday - 1)
            if actual_date < start_date or actual_date > end_date:
                continue
            covered_dates.add(actual_date.isoformat())
            order = str(row.get("order", "")).strip()
            period_info = period_lookup.get(order, {"label": order, "time_range": ""})
            for class_name in class_names:
                teacher_value = row.get(class_name)
                if teacher_value is None:
                    continue
                if isinstance(teacher_value, float) and pd.isna(teacher_value):
                    continue
                current_teacher = str(teacher_value).strip()
                if not current_teacher or current_teacher == "-":
                    continue
                if valid_teachers and current_teacher not in valid_teachers:
                    continue
                if target_teacher and current_teacher != target_teacher:
                    continue
                counter[current_teacher] += 1
                if target_teacher:
                    subject_value = df.at[idx, class_name] if class_name in df.columns and idx in df.index else ""
                    lessons.append({
                        "date": actual_date.isoformat(),
                        "weekday": weekday,
                        "period_order": order,
                        "period": period_info.get("label") or order,
                        "time_range": period_info.get("time_range") or "",
                        "class_name": class_name,
                        "subject": str(subject_value or "").strip(),
                    })

    rows = [
        {"teacher_name": name, "lesson_count": count}
        for name, count in counter.most_common()
    ]
    return {
        "rows": rows,
        "covered_dates": sorted(covered_dates),
        "source_files": source_files,
        "lessons": sorted(lessons, key=lambda item: (item["date"], str(item["period_order"]), item["class_name"])),
        "message": "按 lesson.yaml 中 lesson_dir 下对应月份 class_schedule 周课表文件统计。",
    }


def _minutes_from_time(value: str) -> Optional[int]:
    try:
        hour, minute = [int(part) for part in str(value).strip().split(":")[:2]]
        return hour * 60 + minute
    except Exception:
        return None


def _find_current_period(lesson: Lesson) -> Dict[str, object]:
    current_minutes = datetime.now().hour * 60 + datetime.now().minute
    time_table = lesson.get_cache_data("time_table")
    if time_table is None or time_table.empty:
        return {"period": None, "label": "", "time_range": "", "all_periods": []}

    all_periods = []
    for _, row in time_table.iterrows():
        order = str(row.get("order", "")).strip()
        label = str(row.get("label") or order).strip()
        time_range = str(row.get("show_time") or row.get("time_table") or "").strip()
        all_periods.append({"order": order, "label": label, "time_range": time_range})
        if "-" not in time_range:
            continue
        start_time, end_time = [item.strip() for item in time_range.split("-", 1)]
        start_minutes = _minutes_from_time(start_time)
        end_minutes = _minutes_from_time(end_time)
        if start_minutes is None or end_minutes is None:
            continue
        if start_minutes <= current_minutes <= end_minutes:
            return {"period": order, "label": label, "time_range": time_range, "all_periods": all_periods}
    return {"period": None, "label": "", "time_range": "", "all_periods": all_periods}


def _teacher_subject_lookup(lesson: Lesson) -> Dict[str, Dict[str, str]]:
    teacher_template = lesson.get_cache_data("teacher_template")
    if teacher_template is None or teacher_template.empty:
        return {}

    lookup = {}
    for _, row in teacher_template.iterrows():
        teacher_name = str(row.get("name") or "").strip()
        course = str(row.get("course") or "").strip()
        for subject in lesson.schedule_service.split_subjects(row.get("subject")):
            lookup[subject] = {"teacher": teacher_name, "course": course or subject}
    return lookup


def _current_course_snapshot() -> Dict[str, object]:
    lesson = Lesson()
    period_info = _find_current_period(lesson)
    schedule_df = lesson.get_cache_data("today_schedule")
    class_template = lesson.get_cache_data("class_template")
    class_names = class_template["class_name"].tolist() if class_template is not None and not class_template.empty else []

    current_classes = []
    if schedule_df is None or schedule_df.empty or not period_info["period"]:
        return {
            "current_period": period_info["label"],
            "current_period_order": period_info["period"],
            "current_time_range": period_info["time_range"],
            "active_class_count": 0,
            "current_classes": current_classes,
            "all_periods": period_info["all_periods"],
        }

    df = schedule_df.copy()
    if "order" not in df.columns:
        return {
            "current_period": period_info["label"],
            "current_period_order": period_info["period"],
            "current_time_range": period_info["time_range"],
            "active_class_count": 0,
            "current_classes": current_classes,
            "all_periods": period_info["all_periods"],
        }

    df["order"] = df["order"].astype(str)
    df_current = df[df["order"] == str(period_info["period"])]
    if df_current.empty:
        return {
            "current_period": period_info["label"],
            "current_period_order": period_info["period"],
            "current_time_range": period_info["time_range"],
            "active_class_count": 0,
            "current_classes": current_classes,
            "all_periods": period_info["all_periods"],
        }

    subject_lookup = _teacher_subject_lookup(lesson)
    row = df_current.iloc[0]
    for class_name in class_names:
        if class_name not in df_current.columns:
            continue
        subject = row.get(class_name)
        if subject is None or (isinstance(subject, float) and pd.isna(subject)):
            continue
        subject = str(subject).strip()
        if not subject or subject == "-":
            continue
        teacher_info = subject_lookup.get(subject, {})
        current_classes.append({
            "class_name": class_name,
            "subject": subject,
            "course": teacher_info.get("course") or subject,
            "teacher": teacher_info.get("teacher") or "未知教师",
            "period": period_info["label"],
            "period_order": period_info["period"],
            "time_range": period_info["time_range"],
        })

    return {
        "current_period": period_info["label"],
        "current_period_order": period_info["period"],
        "current_time_range": period_info["time_range"],
        "active_class_count": len(current_classes),
        "current_classes": current_classes,
        "all_periods": period_info["all_periods"],
    }


@router.get("/teaching/summary", summary="教务驾驶舱总览")
async def get_teaching_dashboard_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    top_n: int = Query(5, ge=1, le=50),
    user: User = Depends(get_current_user),
):
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
            ],
            "charts": {
                "teacher_workload_rank": workload_rank,
                "class_size_rank": class_size_rank,
                "resource_mix": [
                    {"name": "班级", "value": class_count},
                    {"name": "学生", "value": student_count},
                    {"name": "教师", "value": teacher_count},
                ],
            },
            "tables": {"teacher_workload": workload["rows"], "teacher_workload_rank": workload_rank},
            "current_course": current_course,
            "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "covered_dates": workload["covered_dates"],
            "source_files": workload["source_files"],
            "top_n": top_n,
            "message": workload["message"],
            "updated_at": _now_text(),
        },
    }


# =============================================================================
# 第二阶段：班级驾驶舱 & 教师工作台
# =============================================================================

def _get_homework_db():
    """获取作业数据库连接"""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "databases", "homework.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _get_inout_db():
    """获取请假数据库连接"""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "databases", "inout.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


@router.get("/class/summary", summary="班级驾驶舱总览")
async def get_class_dashboard_summary(
    class_id: Optional[int] = Query(None, description="班级ID，班主任默认本班"),
    top_n: int = Query(5, ge=1, le=50),
    user: User = Depends(get_current_user),
):
    """班级驾驶舱：班级基础、学习活动、德育表现、出勤事务、生日关怀"""
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
        student_count = len(students)
        male_count = sum(1 for s in students if s.get("gender") == "男")
        female_count = sum(1 for s in students if s.get("gender") == "女")
        unknown_gender_count = student_count - male_count - female_count

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
        avg_score = round(float(eval_stats.get("avg_score") or 0), 1)
        evaluated_count = int(eval_stats.get("evaluated_count") or 0)
        low_count = int(eval_stats.get("low_count") or 0)
        pass_count = int(eval_stats.get("pass_count") or 0)
        unevaluated_count = max(student_count - evaluated_count, 0)
        low_students = db.query_all(
            """SELECT s.student_id, s.name, me.total_score
            FROM moral_evaluation me
            JOIN student s ON me.student_id = s.student_id
            WHERE me.class_id = %s AND me.total_score < 60
            ORDER BY me.total_score ASC LIMIT %s""",
            (class_id, top_n)
        )

        # 本月生日学生
        today = date.today()
        birthday_this_month = [
            s for s in students
            if s.get("birthday") and str(s["birthday"])[5:7] == str(today.month).zfill(2)
        ]

        # 本周生日学生
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        birthday_this_week = []
        for s in students:
            if not s.get("birthday"):
                continue
            bd = str(s["birthday"])
            try:
                bd_date = date(today.year, int(bd[5:7]), int(bd[8:10]))
                if week_start <= bd_date <= week_end:
                    birthday_this_week.append(s)
            except:
                pass

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

    # 出勤统计（请假）
    leave_count = 0
    active_leave_count = 0
    try:
        with _get_inout_db() as io_db:
            cursor = io_db.cursor()
            # 获取班级学生ID列表
            student_ids = [s["student_id"] for s in students]
            if student_ids:
                placeholders = ",".join(["?" for _ in student_ids])
                cursor.execute(
                    f"SELECT COUNT(*) FROM inout WHERE sid IN ({placeholders}) AND style = '请假'",
                    tuple(student_ids)
                )
                leave_count = cursor.fetchone()[0] or 0
                cursor.execute(
                    f"SELECT COUNT(*) FROM inout WHERE sid IN ({placeholders}) AND style = '请假' AND active = 1",
                    tuple(student_ids)
                )
                active_leave_count = cursor.fetchone()[0] or 0
    except Exception:
        pass

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
                _metric("请假人数", active_leave_count, "人"),
            ],
            "charts": {
                "gender_mix": [
                    {"name": "男生", "value": male_count},
                    {"name": "女生", "value": female_count},
                    {"name": "未维护", "value": unknown_gender_count},
                ],
                "score_band": [
                    {"name": "60分以下", "value": low_count},
                    {"name": "60分以上", "value": pass_count},
                    {"name": "未评价", "value": unevaluated_count},
                ],
            },
            "tables": {
                "low_students": low_students,
                "birthday_this_month": [{"name": s["name"], "birthday": s["birthday"]} for s in birthday_this_month],
                "birthday_this_week": [{"name": s["name"], "birthday": s["birthday"]} for s in birthday_this_week],
            },
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
    today_lessons = []
    try:
        lesson = Lesson()
        schedule_df = lesson.get_cache_data("today_schedule")
        if schedule_df is not None and not schedule_df.empty:
            subject_df = schedule_df.copy()
            teacher_df = lesson.schedule_service.replace_subject_teacher(schedule_df, teacher_flag=True)
            time_table = lesson.get_cache_data("time_table")
            period_lookup = {}
            if time_table is not None and not time_table.empty:
                for _, period_row in time_table.iterrows():
                    order = str(period_row.get("order", "")).strip()
                    period_lookup[order] = {
                        "label": str(period_row.get("label") or order).strip(),
                        "time_range": str(period_row.get("show_time") or period_row.get("time_table") or "").strip(),
                    }
            class_template = lesson.get_cache_data("class_template")
            class_names = class_template["class_name"].tolist() if class_template is not None and not class_template.empty else []
            for idx, row in teacher_df.iterrows():
                order = str(row.get("order", "")).strip()
                period_info = period_lookup.get(order, {"label": order, "time_range": ""})
                for class_name in class_names:
                    if class_name not in teacher_df.columns:
                        continue
                    teacher_in_cell = str(row.get(class_name) or "").strip()
                    if teacher_in_cell == teacher_name:
                        subject_value = subject_df.at[idx, class_name] if class_name in subject_df.columns and idx in subject_df.index else ""
                        today_lessons.append({
                            "class_name": class_name,
                            "time": period_info.get("time_range") or period_info.get("label") or "",
                            "period": period_info.get("label") or order,
                            "subject": str(subject_value or "").strip(),
                        })
    except Exception:
        pass

    # 发布统计（作业、公告）
    homework_published = 0
    announcements_published = 0
    try:
        with _get_homework_db() as hw_db:
            cursor = hw_db.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM homework WHERE teacher = ? AND deleted = 0",
                (teacher_name,)
            )
            homework_published = cursor.fetchone()[0] or 0
            cursor.execute(
                "SELECT COUNT(*) FROM announcements WHERE author = ? AND deleted = 0",
                (teacher_name,)
            )
            announcements_published = cursor.fetchone()[0] or 0
    except Exception:
        pass

    # 德育参与（自己创建的日常记录、点滴记录）
    with get_moral_db() as db:
        daily_created = _safe_count(
            db,
            "SELECT COUNT(*) FROM student_daily_record WHERE recorder = %s AND is_deleted = 0",
            (teacher_name,)
        )
        moment_created = _safe_count(
            db,
            "SELECT COUNT(*) FROM student_moment_record WHERE recorder = %s AND is_deleted = 0",
            (teacher_name,)
        )

    # 监考任务（近期监考安排）
    invigilation_tasks = []
    try:
        inv_db_path = os.path.join(os.path.dirname(__file__), "..", "..", "databases", "invigilation.db")
        with sqlite3.connect(inv_db_path) as inv_db:
            inv_db.row_factory = sqlite3.Row
            cursor = inv_db.cursor()
            # 查询该教师的监考安排
            cursor.execute(
                """SELECT p.name AS project_name, s.exam_date, s.start_time, s.end_time,
                          s.subject, s.room_name, s.grade_name
                FROM invigilation_slot s
                JOIN exam_project p ON s.project_id = p.id
                WHERE s.teacher_name = ? AND s.exam_date >= ?
                ORDER BY s.exam_date, s.start_time
                LIMIT 10""",
                (teacher_name, today_str)
            )
            for row in cursor.fetchall():
                invigilation_tasks.append(dict(row))
    except Exception:
        pass

    lesson_workload = _teacher_lesson_counts_from_files(start_date, end_date, teacher_name=teacher_name)
    my_lesson_count = sum(row["lesson_count"] for row in lesson_workload["rows"])

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("今日课程", len(today_lessons), "节"),
                _metric("区间课时", my_lesson_count, "节"),
                _metric("发布作业", homework_published, "份", "/homework"),
                _metric("发布公告", announcements_published, "份"),
                _metric("日常记录", daily_created, "条", "/moral/daily-record"),
                _metric("点滴记录", moment_created, "条", "/moral/moment-record"),
                _metric("监考任务", len(invigilation_tasks), "场", "/invigilation"),
            ],
            "tables": {
                "today_lessons": today_lessons,
                "invigilation_tasks": invigilation_tasks,
                "workload_lessons": lesson_workload["lessons"],
            },
            "workload": {
                "lesson_count": my_lesson_count,
                "covered_dates": lesson_workload["covered_dates"],
                "source_files": lesson_workload["source_files"],
                "lessons": lesson_workload["lessons"],
                "message": lesson_workload["message"],
            },
            "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "updated_at": _now_text(),
        },
    }


def _get_invigilation_db():
    """获取监考数据库连接"""
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), "..", "..", "databases", "invigilation.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


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

    # 监考数据库统计
    project_stats = {"total": 0, "draft": 0, "saved": 0, "notified": 0}
    slot_stats = {"total": 0, "arranged": 0, "unarranged": 0, "conflict": 0}
    notification_stats = {"success": 0, "failed": 0, "skipped": 0, "pending": 0}
    teacher_workload = []
    unarranged_slots = []
    conflict_slots = []
    notification_failed = []
    recent_projects = []

    try:
        with _get_invigilation_db() as inv_db:
            cursor = inv_db.cursor()

            # 1. 考试项目状态统计
            cursor.execute(
                """SELECT status, COUNT(*) AS count FROM exam_project GROUP BY status"""
            )
            for row in cursor.fetchall():
                status = row["status"]
                count = row["count"]
                project_stats["total"] += count
                if status in project_stats:
                    project_stats[status] = count

            # 2. 监考场次统计（已安排/未安排）
            cursor.execute(
                """SELECT COUNT(*) FROM invigilation_slot WHERE exam_date >= ?""",
                (today_str,)
            )
            slot_stats["total"] = cursor.fetchone()[0] or 0

            cursor.execute(
                """SELECT COUNT(*) FROM invigilation_slot
                   WHERE exam_date >= ? AND teacher_id IS NOT NULL AND teacher_id != ''""",
                (today_str,)
            )
            slot_stats["arranged"] = cursor.fetchone()[0] or 0
            slot_stats["unarranged"] = slot_stats["total"] - slot_stats["arranged"]

            # 3. 冲突场次检测（同一教师同一时间）
            cursor.execute(
                """SELECT teacher_name, exam_date, start_time, COUNT(*) AS count
                   FROM invigilation_slot
                   WHERE exam_date >= ? AND teacher_name IS NOT NULL AND teacher_name != ''
                   GROUP BY teacher_name, exam_date, start_time
                   HAVING count > 1""",
                (today_str,)
            )
            conflict_count = 0
            for row in cursor.fetchall():
                conflict_count += row["count"] - 1  # 冒泡数减1为冲突数
            slot_stats["conflict"] = conflict_count

            # 4. 通知状态统计
            cursor.execute(
                """SELECT sent_status, COUNT(*) AS count
                   FROM invigilation_notification_log
                   GROUP BY sent_status"""
            )
            for row in cursor.fetchall():
                status = row["sent_status"]
                count = row["count"]
                if status in notification_stats:
                    notification_stats[status] = count

            # 5. 教师监考负载排行
            cursor.execute(
                """SELECT teacher_name, COUNT(*) AS invigilation_count
                   FROM invigilation_slot
                   WHERE exam_date >= ? AND teacher_name IS NOT NULL AND teacher_name != ''
                   GROUP BY teacher_name
                   ORDER BY invigilation_count DESC
                   LIMIT ?""",
                (today_str, top_n)
            )
            for row in cursor.fetchall():
                teacher_workload.append({
                    "teacher_name": row["teacher_name"],
                    "invigilation_count": row["invigilation_count"],
                })

            # 6. 未安排场次列表
            cursor.execute(
                """SELECT s.project_id, p.name AS project_name, s.exam_date,
                          s.start_time, s.end_time, s.subject, s.room_name, s.grade_name
                   FROM invigilation_slot s
                   LEFT JOIN exam_project p ON s.project_id = p.id
                   WHERE s.exam_date >= ?
                     AND (s.teacher_id IS NULL OR s.teacher_id = '')
                   ORDER BY s.exam_date, s.start_time
                   LIMIT 10""",
                (today_str,)
            )
            for row in cursor.fetchall():
                unarranged_slots.append(dict(row))

            # 7. 冲突场次详情
            cursor.execute(
                """SELECT teacher_name, exam_date, start_time,
                          GROUP_CONCAT(subject || ' (' || room_name || ')', ', ') AS subjects
                   FROM invigilation_slot
                   WHERE exam_date >= ? AND teacher_name IS NOT NULL AND teacher_name != ''
                   GROUP BY teacher_name, exam_date, start_time
                   HAVING COUNT(*) > 1
                   ORDER BY exam_date, start_time
                   LIMIT 10""",
                (today_str,)
            )
            for row in cursor.fetchall():
                conflict_slots.append(dict(row))

            # 8. 通知失败记录
            cursor.execute(
                """SELECT n.project_id, p.name AS project_name, n.teacher_name,
                          n.sent_status, n.sent_at, n.error_message
                   FROM invigilation_notification_log n
                   LEFT JOIN exam_project p ON n.project_id = p.id
                   WHERE n.sent_status IN ('failed', 'skipped')
                   ORDER BY n.sent_at DESC
                   LIMIT 10"""
            )
            for row in cursor.fetchall():
                notification_failed.append(dict(row))

            # 9. 近期考试项目
            cursor.execute(
                """SELECT id, name, status, grade_ids, version_no, updated_at
                   FROM exam_project
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (top_n,)
            )
            for row in cursor.fetchall():
                recent_projects.append(dict(row))

    except Exception as e:
        import traceback
        traceback.print_exc()

    # 计算通知成功率
    total_notifications = sum(notification_stats.values())
    notification_success_rate = 0
    if total_notifications > 0:
        notification_success_rate = round(
            notification_stats["success"] / total_notifications * 100, 1
        )

    # 计算安排完整率
    arrangement_rate = 0
    if slot_stats["total"] > 0:
        arrangement_rate = round(
            slot_stats["arranged"] / slot_stats["total"] * 100, 1
        )

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("考试项目", project_stats["total"], "个", "/invigilation"),
                _metric("待安排场次", slot_stats["unarranged"], "场"),
                _metric("冲突场次", slot_stats["conflict"], "场"),
                _metric("安排完整率", arrangement_rate, "%"),
                _metric("通知成功率", notification_success_rate, "%"),
                _metric("通知失败", notification_stats["failed"] + notification_stats["skipped"], "条"),
            ],
            "charts": {
                "project_status": [
                    {"name": "草稿", "value": project_stats["draft"]},
                    {"name": "已保存", "value": project_stats["saved"]},
                    {"name": "已通知", "value": project_stats["notified"]},
                ],
                "notification_status": [
                    {"name": "成功", "value": notification_stats["success"]},
                    {"name": "失败", "value": notification_stats["failed"]},
                    {"name": "跳过", "value": notification_stats["skipped"]},
                    {"name": "待发送", "value": notification_stats["pending"]},
                ],
                "teacher_workload_rank": teacher_workload,
                "teacher_workload_top5": teacher_workload,
            },
            "tables": {
                "unarranged_slots": unarranged_slots,
                "conflict_slots": conflict_slots,
                "notification_failed": notification_failed,
                "recent_projects": recent_projects,
                "teacher_workload_rank": teacher_workload,
                "teacher_workload_top5": teacher_workload,
            },
            "top_n": top_n,
            "updated_at": _now_text(),
        },
    }


# =============================================================================
# 第四阶段：系统运维驾驶舱
# =============================================================================

import glob as glob_module


def _get_db_stats(db_path: str) -> Dict[str, object]:
    """获取数据库统计信息"""
    if not os.path.exists(db_path):
        return {"exists": False, "size_kb": 0, "tables": []}
    size_kb = os.path.getsize(db_path) / 1024
    tables = []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = [row["name"] for row in cursor.fetchall()]
        for table_name in table_names:
            cursor.execute(f"SELECT COUNT(*) AS count FROM {table_name}")
            count = cursor.fetchone()["count"]
            tables.append({"name": table_name, "count": count})
        conn.close()
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
    for db_name in ["moral.db", "auth.db", "homework.db", "inout.db", "invigilation.db", "task.db"]:
        db_path = os.path.join(db_dir, db_name)
        stats = _get_db_stats(db_path)
        stats["name"] = db_name
        db_files.append(stats)
        if stats["exists"]:
            total_size_kb += stats["size_kb"]

    # 2. 用户统计（从 auth.db）
    user_count = 0
    role_distribution = []
    try:
        auth_db_path = os.path.join(db_dir, "auth.db")
        if os.path.exists(auth_db_path):
            conn = sqlite3.connect(auth_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS count FROM users WHERE is_active = 1")
            user_count = cursor.fetchone()["count"]
            cursor.execute(
                """SELECT r.role_name, COUNT(ur.user_id) AS count
                   FROM user_roles ur
                   JOIN roles r ON ur.role_id = r.id
                   GROUP BY r.role_name"""
            )
            for row in cursor.fetchall():
                role_distribution.append({"role": row["role_name"], "count": row["count"]})
            conn.close()
    except Exception:
        pass

    # 3. 教师统计（从 moral.db teacher 表）
    teacher_stats = {"total": 0, "teacher": 0, "admin": 0, "other": 0}
    try:
        moral_db_path = os.path.join(db_dir, "moral.db")
        if os.path.exists(moral_db_path):
            conn = sqlite3.connect(moral_db_path)
            conn.row_factory = sqlite3.Row
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
            conn.close()
    except Exception:
        pass

    # 4. API 权限风险检测（从 moral.db api_permission_config）
    api_permission_risks = []
    try:
        moral_db_path = os.path.join(db_dir, "moral.db")
        if os.path.exists(moral_db_path):
            conn = sqlite3.connect(moral_db_path)
            conn.row_factory = sqlite3.Row
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
            conn.close()
    except Exception:
        pass

    # 5. 操作日志统计（从 moral_operation_log）
    operation_stats = []
    recent_operations = []
    try:
        moral_db_path = os.path.join(db_dir, "moral.db")
        if os.path.exists(moral_db_path):
            conn = sqlite3.connect(moral_db_path)
            conn.row_factory = sqlite3.Row
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
            conn.close()
    except Exception:
        pass

    # 6. 任务状态（从 task.db）
    task_stats = {"total": 0, "running": 0, "failed": 0, "success": 0}
    try:
        task_db_path = os.path.join(db_dir, "task.db")
        if os.path.exists(task_db_path):
            conn = sqlite3.connect(task_db_path)
            conn.row_factory = sqlite3.Row
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
            conn.close()
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
