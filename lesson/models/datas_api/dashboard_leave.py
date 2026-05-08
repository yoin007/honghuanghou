# -*- coding: utf-8 -*-
"""Leave (请假/出勤) dashboard helpers.

Batch 47: Extracted for class/moral dashboards to show leave/attendance risk data.

Provides helpers for querying inout.db leave records and enriching with student info.
"""

import os
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "databases")
INOUT_DB_PATH = os.path.join(DB_DIR, "inout.db")


def _get_sqlite_connection():
    """延迟导入避免循环依赖"""
    from models.datas_api.repositories.sqlite_base import get_sqlite_connection
    return get_sqlite_connection


def get_inout_db_path() -> str:
    """Get inout.db path."""
    return INOUT_DB_PATH


def _normalize_sid(value) -> str:
    """Normalize sid values from SQLite/Pandas into stable strings."""
    if pd.isna(value):
        return ""
    if isinstance(value, (int, float)):
        return str(int(value))
    return str(value)


def _load_students_cache() -> pd.DataFrame:
    """Load and normalize Lesson students cache."""
    from models.lesson.lesson import Lesson

    students_df = Lesson().get_cache_data("students")
    if students_df is None or students_df.empty:
        return pd.DataFrame()
    students_df = students_df.copy()
    if "sid" not in students_df.columns:
        return pd.DataFrame()
    students_df["sid"] = students_df["sid"].apply(_normalize_sid)
    return students_df


def query_active_leave_records(
    class_filter: Optional[str] = None,
    student_ids: Optional[List[str]] = None,
    limit: int = 20,
) -> List[Dict[str, object]]:
    """Query active leave records from inout.db.

    Args:
        class_filter: Optional class name to filter (cname).
        student_ids: Optional list of student IDs (sid) to filter.
        limit: Maximum records to return.

    Returns:
        List of dicts with id/sid/name/class_name/style/days/status/recorder/note/create_at.
        Empty list on error or no data.
    """
    get_sqlite_connection = _get_sqlite_connection()
    if not os.path.isfile(INOUT_DB_PATH):
        return []

    students_df = _load_students_cache()
    sid_filter = [str(sid) for sid in student_ids] if student_ids else []
    if class_filter:
        if students_df.empty or "cname" not in students_df.columns:
            return []
        class_student_sids = [
            sid for sid in students_df.loc[students_df["cname"].astype(str).str.strip() == class_filter, "sid"].tolist()
            if sid
        ]
        if not class_student_sids:
            return []
        sid_filter = sorted(set(sid_filter).intersection(class_student_sids)) if sid_filter else class_student_sids
        if not sid_filter:
            return []

    conn = None
    try:
        conn = get_sqlite_connection(INOUT_DB_PATH, row_factory=None)
        cursor = conn.cursor()
        # Query active=1, style != '延时', status not '已销假'/'已取消'/'已完成'
        sql = """
            SELECT id, sid, style, days, status, recorder, note, create_at
            FROM inout
            WHERE active = 1 AND style != '延时'
              AND status NOT IN ('已销假', '已取消', '已完成')
        """
        params = []

        if sid_filter:
            placeholders = ",".join(["?" for _ in sid_filter])
            sql += f" AND sid IN ({placeholders})"
            params.extend(sid_filter)

        sql += " ORDER BY create_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
    except Exception:
        return []
    finally:
        if conn is not None:
            conn.close()

    if not rows:
        return []

    if students_df is None or students_df.empty:
        return [{"id": r[0], "sid": r[1], "style": r[2], "days": r[3], "status": r[4],
                 "recorder": r[5], "note": r[6], "create_at": r[7], "name": "", "class_name": "", "class_code": ""}
                for r in rows]

    result = []
    for row in rows:
        record_id, sid, style, days, status, recorder, note, create_at = row
        sid_str = _normalize_sid(sid)

        # Find student info
        student_match = students_df[students_df["sid"] == sid_str]
        if student_match.empty:
            result.append({
                "id": record_id, "sid": sid_str, "style": style, "days": days,
                "status": status, "recorder": recorder, "note": note, "create_at": create_at,
                "name": "", "class_name": "", "class_code": ""
            })
            continue

        student = student_match.iloc[0]
        class_name = str(student.get("cname") or "").strip()
        class_code = str(student.get("class_code") or class_name).strip()
        name = str(student.get("name") or "").strip()

        # Apply class filter if specified
        if class_filter and class_name != class_filter:
            continue

        result.append({
            "id": record_id,
            "sid": sid_str,
            "name": name,
            "class_name": class_name,
            "class_code": class_code,
            "style": style,
            "days": days,
            "status": status,
            "recorder": recorder,
            "note": note,
            "create_at": create_at,
        })

    return result


def count_active_leave_by_class(class_name: Optional[str] = None) -> Dict[str, int]:
    """Count active leave records grouped by class.

    Args:
        class_name: Optional class to filter. If None, returns counts for all classes.

    Returns:
        Dict mapping class_name to count. Empty dict on error.
    """
    records = query_active_leave_records(class_filter=class_name, limit=1000)
    counter = Counter()
    for r in records:
        class_name_key = r.get("class_name") or "未知班级"
        counter[class_name_key] += 1

    return dict(counter)


def compute_leave_stats(student_ids: Optional[List[str]] = None, class_filter: Optional[str] = None) -> Dict[str, object]:
    """Compute leave statistics for dashboard cards.

    Args:
        student_ids: Optional list of student IDs to filter.
        class_filter: Optional class name to filter.

    Returns:
        Dict with leave_count/active_leave_count/pending_cancel_count/recent_leave_list.
    """
    records = query_active_leave_records(class_filter=class_filter, student_ids=student_ids, limit=100)

    active_leave_count = len(records)
    pending_cancel_count = sum(1 for r in records if r.get("status") == "已请假")

    # Recent leave list (top 10)
    recent_leave_list = [
        {
            "id": r["id"],
            "name": r["name"],
            "class_name": r["class_name"],
            "style": r["style"],
            "days": r["days"],
            "status": r["status"],
            "create_at": r["create_at"],
        }
        for r in records[:10]
    ]

    return {
        "leave_count": active_leave_count,  # Total active leave
        "active_leave_count": active_leave_count,  # Same as above
        "pending_cancel_count": pending_cancel_count,  # Not yet canceled/returned
        "recent_leave_list": recent_leave_list,
        "leave_students": records[:20],  # Full list for tables
    }


def build_leave_by_class_chart(limit: int = 10) -> List[Dict[str, object]]:
    """Build leave count by class chart data.

    Args:
        limit: Maximum classes to return.

    Returns:
        List of dicts with class_name/count for pie/bar chart.
    """
    counts = count_active_leave_by_class()
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"name": class_name, "value": count} for class_name, count in sorted_counts]


def compute_attendance_risk_insights(leave_records: List[Dict], class_filter: Optional[str] = None) -> List[Dict[str, object]]:
    """Compute attendance risk insights for moral dashboard.

    Args:
        leave_records: List of leave records from query_active_leave_records.
        class_filter: Optional class name if viewing specific class.

    Returns:
        List of insight dicts with type/title/message/action_route.
    """
    insights = []

    if not leave_records:
        return insights

    # 1. Multiple leave check (repeated leave pattern)
    from collections import defaultdict
    student_leave_count = defaultdict(int)
    for r in leave_records:
        if r.get("sid"):
            student_leave_count[r["sid"]] += 1

    repeated_leave_students = [sid for sid, cnt in student_leave_count.items() if cnt >= 2]
    if repeated_leave_students:
        insights.append({
            "type": "warning",
            "title": "反复请假倾向",
            "message": f"发现 {len(repeated_leave_students)} 名学生有多次请假记录，建议关注出勤状况。",
            "action_route": "/moral/leave-record"
        })

    # 2. Long leave check (days > 3)
    long_leave_records = [r for r in leave_records if r.get("days") and str(r["days"]).isdigit() and int(r["days"]) > 3]
    if long_leave_records:
        insights.append({
            "type": "info",
            "title": "长假学生关注",
            "message": f"有 {len(long_leave_records)} 名学生请假天数超过 3 天，建议跟进返校安排。",
            "action_route": "/moral/leave-record"
        })

    # 3. Not yet left school (status = '已请假')
    pending_leave = [r for r in leave_records if r.get("status") == "已请假"]
    if pending_leave:
        insights.append({
            "type": "info",
            "title": "待出校学生",
            "message": f"有 {len(pending_leave)} 名学生已请假但未出校，请确认是否已离校。",
            "action_route": "/leave-record"
        })

    # 4. Not yet returned (status = '已出校')
    not_returned = [r for r in leave_records if r.get("status") == "已出校"]
    if not_returned:
        insights.append({
            "type": "warning",
            "title": "未销假学生",
            "message": f"有 {len(not_returned)} 名学生已出校但未销假，请及时跟进返校情况。",
            "action_route": "/leave-record"
        })

    return insights


def compute_class_leave_insights(leave_records: List[Dict], class_name: str) -> List[Dict[str, object]]:
    """Compute leave insights for class dashboard (班主任视角).

    Args:
        leave_records: List of leave records for this class.
        class_name: Class name for context.

    Returns:
        List of insight dicts.
    """
    insights = []

    if not leave_records:
        insights.append({
            "type": "success",
            "title": "出勤正常",
            "message": f"{class_name} 当前无请假学生。",
            "action_route": None
        })
        return insights

    # 1. Current leave count
    insights.append({
        "type": "info",
        "title": "当前请假学生",
        "message": f"{class_name} 有 {len(leave_records)} 名学生当前请假。",
        "action_route": "/leave-record"
    })

    # 2. Not yet returned
    not_returned = [r for r in leave_records if r.get("status") == "已出校"]
    if not_returned:
        student_names = ", ".join([r.get("name", "未知") for r in not_returned[:3]])
        if len(not_returned) > 3:
            student_names += f" 等 {len(not_returned)} 人"
        insights.append({
            "type": "warning",
            "title": "未销假需跟进",
            "message": f"{student_names} 已出校但未销假，请及时确认返校。",
            "action_route": "/leave-record"
        })

    # 3. Repeated leave in class
    from collections import defaultdict
    student_leave_count = defaultdict(int)
    for r in leave_records:
        if r.get("sid"):
            student_leave_count[r["sid"]] += 1

    repeated = [sid for sid, cnt in student_leave_count.items() if cnt >= 2]
    if repeated:
        insights.append({
            "type": "warning",
            "title": "反复请假关注",
            "message": f"本班有 {len(repeated)} 名学生多次请假，建议了解原因。",
            "action_route": "/moral/leave-record"
        })

    return insights
