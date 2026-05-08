# -*- coding: utf-8 -*-
"""Teaching dashboard helpers.

Batch 20: Extracted from dashboard.py to keep route handlers thin.
"""

import os
import re
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from models.lesson.lesson import Lesson


def schedule_frames_for_range(start_date: date, end_date: date) -> List[Dict[str, object]]:
    """Get cached schedule frames for date range.

    Args:
        start_date: Range start.
        end_date: Range end.

    Returns:
        List of dicts with df/monday/week_next.
    """
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


def teacher_lesson_counts(start_date: date, end_date: date) -> Dict[str, object]:
    """Count lessons per teacher in date range.

    Delegates to teacher_lesson_counts_from_files.

    Args:
        start_date: Range start.
        end_date: Range end.

    Returns:
        Dict with rows/covered_dates/source_files/lessons/message.
    """
    return teacher_lesson_counts_from_files(start_date, end_date)


def month_keys_for_range(start_date: date, end_date: date) -> List[str]:
    """Generate month keys (YYYYMM) for date range.

    Args:
        start_date: Range start.
        end_date: Range end.

    Returns:
        List of month keys.
    """
    keys = []
    current = start_date.replace(day=1)
    while current <= end_date:
        keys.append(current.strftime("%Y%m"))
        next_month = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        current = next_month
    return keys


def week_start_from_schedule_filename(file_name: str) -> Optional[date]:
    """Parse Monday date from schedule file name.

    Args:
        file_name: File name like 'schedule_20260505.xlsx'.

    Returns:
        Monday date if pattern found, None otherwise.
    """
    match = re.search(r"(20\d{6})", file_name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d").date()
    except Exception:
        return None


def schedule_files_for_range(lesson: Lesson, start_date: date, end_date: date) -> List[Dict[str, object]]:
    """Find schedule files covering date range.

    Args:
        lesson: Lesson instance for lesson_dir.
        start_date: Range start.
        end_date: Range end.

    Returns:
        List of dicts with path/monday/file_name.
    """
    files = []
    seen = set()
    for month_key in month_keys_for_range(start_date, end_date):
        schedule_dir = os.path.join(lesson.lesson_dir, month_key, "class_schedule")
        if not os.path.isdir(schedule_dir):
            continue
        for file_name in os.listdir(schedule_dir):
            if file_name.startswith(".") or not file_name.lower().endswith((".xlsx", ".xls")):
                continue
            monday = week_start_from_schedule_filename(file_name)
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


def format_week_schedule_file(lesson: Lesson, file_path: str, monday: date) -> pd.DataFrame:
    """Format schedule file for analysis.

    Args:
        lesson: Lesson instance.
        file_path: Excel file path.
        monday: Monday date for week context.

    Returns:
        Formatted DataFrame or empty DataFrame on error.
    """
    week_num = monday.isocalendar()[1] + lesson.week_change
    week_flag = "单" if week_num % 2 == 1 else "双"
    df = lesson.load_excel_file(file_path)
    if df is None or df.empty:
        return pd.DataFrame()
    return lesson.schedule_service.format_schedule(df, week_flag, replace_flag=True, ignore=False)


def teacher_lesson_counts_from_files(start_date: date, end_date: date, teacher_name: Optional[str] = None) -> Dict[str, object]:
    """Count lessons per teacher by scanning schedule files.

    Args:
        start_date: Range start.
        end_date: Range end.
        teacher_name: Optional specific teacher to filter.

    Returns:
        Dict with rows/covered_dates/source_files/lessons/message.
    """
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

    for item in schedule_files_for_range(lesson, start_date, end_date):
        df = format_week_schedule_file(lesson, item["path"], item["monday"])
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


def minutes_from_time(value: str) -> Optional[int]:
    """Convert HH:MM to minutes.

    Args:
        value: Time string like "08:00".

    Returns:
        Minutes since midnight, or None on parse error.
    """
    try:
        hour, minute = [int(part) for part in str(value).strip().split(":")[:2]]
        return hour * 60 + minute
    except Exception:
        return None


def find_current_period(lesson: Lesson) -> Dict[str, object]:
    """Find current period based on current time.

    Args:
        lesson: Lesson instance with time_table cache.

    Returns:
        Dict with period/label/time_range/all_periods.
    """
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
        start_minutes = minutes_from_time(start_time)
        end_minutes = minutes_from_time(end_time)
        if start_minutes is None or end_minutes is None:
            continue
        if start_minutes <= current_minutes <= end_minutes:
            return {"period": order, "label": label, "time_range": time_range, "all_periods": all_periods}
    return {"period": None, "label": "", "time_range": "", "all_periods": all_periods}


def teacher_subject_lookup(lesson: Lesson) -> Dict[str, Dict[str, str]]:
    """Build subject -> teacher/course lookup from teacher_template.

    Args:
        lesson: Lesson instance with teacher_template cache.

    Returns:
        Dict mapping subject to {teacher, course}.
    """
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


def current_course_snapshot() -> Dict[str, object]:
    """Snapshot of current course activity across all classes.

    Returns:
        Dict with current_period/current_period_order/current_time_range/
        active_class_count/current_classes/all_periods.
    """
    lesson = Lesson()
    period_info = find_current_period(lesson)
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

    subject_lookup = teacher_subject_lookup(lesson)
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


def build_filegather_summary(month: Optional[str] = None) -> Dict[str, object]:
    """Build file upload summary from FileGatherDB.

    Batch 23: Reuses FileGatherDB.get_statistics() for dashboard.
    Batch 46: Enhanced with completion_rate, pending_file_list, overdue, recent_files.

    Args:
        month: Optional month filter (YYYYMM format).

    Returns:
        Dict with cards/charts/tables for file upload status.
        Returns zeros on error or missing data.
    """
    try:
        from models.filegather_db import FileGatherDB
        fg_db = FileGatherDB()
        stats = fg_db.get_statistics(month)
    except Exception:
        stats = {"total_files": 0, "pending_files": 0, "done_files": 0, "by_user": [],
                 "completion_rate": 0.0, "pending_file_list": [], "overdue_pending_count": 0,
                 "recent_file_list": []}

    if not isinstance(stats, dict):
        stats = {}

    total_files = int(stats.get("total_files") or 0)
    pending_files = int(stats.get("pending_files") or 0)
    done_files = int(stats.get("done_files") or 0)
    by_user = stats.get("by_user") or []
    if not isinstance(by_user, list):
        by_user = []

    # Batch46: 新增深度指标
    completion_rate = float(stats.get("completion_rate") or 0.0)
    pending_file_list = stats.get("pending_file_list") or []
    if not isinstance(pending_file_list, list):
        pending_file_list = []
    overdue_pending_count = int(stats.get("overdue_pending_count") or 0)
    recent_file_list = stats.get("recent_file_list") or []
    if not isinstance(recent_file_list, list):
        recent_file_list = []

    # Cards: 待处理, 本月文件, 已完成, 完成率, 逾期
    cards = [
        {"name": "待处理文件", "value": pending_files},
        {"name": "本月文件", "value": total_files},
        {"name": "已完成文件", "value": done_files},
        {"name": "完成率", "value": completion_rate, "unit": "%"},
        {"name": "逾期文件", "value": overdue_pending_count},
    ]

    # Charts: file_upload_status pie chart data
    charts = {
        "file_upload_status": [
            {"name": "待处理", "value": pending_files},
            {"name": "已完成", "value": done_files},
        ],
    }

    # Tables: top uploaders (by_user already limited to 10)
    tables = {
        "file_upload_top_users": by_user[:10],
        "pending_file_list": pending_file_list[:10],  # 最近待处理
        "recent_file_list": recent_file_list[:10],  # 最近上传
    }

    return {
        "cards": cards,
        "charts": charts,
        "tables": tables,
        "month": month,
        "completion_rate": completion_rate,
        "overdue_pending_count": overdue_pending_count,
        "pending_file_list": pending_file_list,
        "recent_file_list": recent_file_list,
    }
