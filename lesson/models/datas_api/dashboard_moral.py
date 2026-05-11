# -*- coding: utf-8 -*-
"""Moral dashboard helpers.

Batch 21: Extracted from dashboard.py to keep route handlers thin.
"""

from datetime import date, timedelta
from typing import Dict, List

from models.datas_api.dashboard_common import safe_query_all


def score_distribution(db, where_clause: str, params: tuple) -> List[Dict[str, object]]:
    """Build score distribution chart data.

    Args:
        db: Moral database connection.
        where_clause: SQL WHERE clause for filtering.
        params: Query parameters.

    Returns:
        List of 5 dicts: 90分以上, 80-89分, 70-79分, 60-69分, 60分以下.
    """
    rows = safe_query_all(
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


def daily_event_mix(db, where_clause: str, params: tuple) -> List[Dict[str, object]]:
    """Build daily event mix chart data (positive vs negative records).

    Args:
        db: Moral database connection.
        where_clause: SQL WHERE clause for filtering.
        params: Query parameters.

    Returns:
        List of 2 dicts: 正向记录, 负向记录.
    """
    rows = safe_query_all(
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


def daily_record_trend(db, where_clause: str, params: tuple) -> List[Dict[str, object]]:
    """Build daily record trend chart data for last 14 days.

    Args:
        db: Moral database connection.
        where_clause: SQL WHERE clause for filtering.
        params: Query parameters.

    Returns:
        List of 14 dicts with date and count keys.
    """
    start = date.today() - timedelta(days=13)
    rows = safe_query_all(
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


def class_score_rank(db, where_clause: str, params: tuple, top_n: int) -> List[Dict[str, object]]:
    """Build class score rank table data.

    Args:
        db: Moral database connection.
        where_clause: SQL WHERE clause for filtering.
        params: Query parameters.
        top_n: Number of top classes to return.

    Returns:
        List of dicts with class_name, avg_score, student_count.
    """
    return safe_query_all(
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


def class_score_rank_all(db, class_filter: str = None, grade_filter: int = None, top_n: int = 10) -> List[Dict[str, object]]:
    """Build class score rank for all visible classes based on role.

    Args:
        db: Moral database connection.
        class_filter: Class name filter for cleader (single class).
        grade_filter: Grade ID filter for g_leader (grade classes).
        top_n: Maximum number of classes to return.

    Returns:
        List of dicts with class_name, avg_score, student_count.
    """
    # Build WHERE clause for class filtering
    conditions = ["c.is_active = 1"]
    params = []

    if class_filter:
        conditions.append("c.class_name = %s")
        params.append(class_filter)
    elif grade_filter:
        conditions.append("c.grade_id = %s")
        params.append(grade_filter)

    where_clause = " AND ".join(conditions)

    return safe_query_all(
        db,
        f"""SELECT c.class_name, ROUND(AVG(me.total_score), 1) AS avg_score, COUNT(*) AS student_count
            FROM moral_evaluation me
            JOIN class c ON me.class_id = c.class_id
            WHERE {where_clause}
            GROUP BY c.class_id, c.class_name
            ORDER BY avg_score DESC
            LIMIT {top_n}""",
        tuple(params) if params else (),
    )