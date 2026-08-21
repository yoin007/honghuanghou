# -*- coding: utf-8 -*-
"""Moral dashboard helpers.

Batch 21: Extracted from dashboard.py to keep route handlers thin.
Batch 28: 改为实时计算德育总分（与 moral/evaluation 页面口径一致），
         不再依赖 moral_evaluation 表的快照数据。
         计算公式：基础分 + 日常表现分 + 校级事件分 + 任务完成分 + 集体事件分 - 处分扣分
"""

from datetime import date, timedelta
from typing import Dict, List, Optional

from models.datas_api.dashboard_common import safe_query_all


def _get_base_score(db) -> float:
    """读取德育基础分配置，默认 80。"""
    val = db.query_value(
        "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
    )
    try:
        return float(val) if val is not None else 80.0
    except (ValueError, TypeError):
        return 80.0


def _real_time_score_cte(semester_id: int, base_score: float) -> str:
    """构造实时计算学生德育总分的 CTE 片段。

    对每个学生计算 total_score = base_score + daily + school + task + collective - punishment。
    semester_id 直接嵌入 SQL（整数，安全）。

    返回的 CTE 名称为 student_score，字段：student_id, total_score
    可被上层 SQL JOIN 使用。
    """
    return f"""
    student_score AS (
        SELECT
            s.student_id,
            s.class_id,
            ( {base_score}
              + COALESCE((SELECT SUM(score) FROM student_daily_record dr
                          WHERE dr.student_id = s.student_id
                            AND dr.semester_id = {semester_id}
                            AND dr.is_deleted = 0), 0)
              + COALESCE((SELECT SUM(score) FROM student_school_record sr
                          WHERE sr.student_id = s.student_id
                            AND sr.semester_id = {semester_id}
                            AND sr.is_deleted = 0), 0)
              + COALESCE((SELECT SUM(stf.current_score)
                            FROM student_task_finish stf
                            JOIN semester sem ON sem.semester_id = {semester_id}
                           WHERE stf.student_id = s.student_id
                             AND stf.status = 1
                             AND stf.finish_date >= sem.start_date
                             AND stf.finish_date <= sem.end_date), 0)
              + COALESCE((SELECT SUM(ced.score_assigned)
                            FROM collective_event_distribution ced
                            JOIN collective_event ce ON ced.event_id = ce.event_id
                           WHERE ced.student_id = s.student_id
                             AND ce.semester_id = {semester_id}
                             AND ced.is_participant = 1), 0)
              - COALESCE((SELECT SUM(ABS(score_deduct))
                            FROM punishment_record pr
                           WHERE pr.student_id = s.student_id
                             AND pr.semester_id = {semester_id}
                             AND pr.is_revoked = 0), 0)
            ) AS total_score
        FROM student s
        WHERE s.status = '在校'
    )
    """


def score_distribution(
    db,
    class_ids: Optional[List[int]] = None,
    semester_id: int = None,
) -> List[Dict[str, object]]:
    """Build score distribution chart data (实时计算).

    Args:
        db: Moral database connection.
        class_ids: 限制的班级 ID 列表，None 表示全校。
        semester_id: 学期 ID，必填。

    Returns:
        List of 5 dicts: 90分以上, 80-89分, 70-79分, 60-69分, 60分以下.
    """
    if not semester_id:
        return [
            {"name": "90分以上", "value": 0},
            {"name": "80-89分", "value": 0},
            {"name": "70-79分", "value": 0},
            {"name": "60-69分", "value": 0},
            {"name": "60分以下", "value": 0},
        ]

    base_score = _get_base_score(db)
    cte = _real_time_score_cte(semester_id, base_score)

    class_clause = ""
    params = []
    if class_ids:
        ids = [int(x) for x in class_ids if x]
        if ids:
            class_clause = f" AND ss.class_id IN ({','.join(['?'] * len(ids))})"
            params.extend(ids)

    rows = safe_query_all(
        db,
        f"""WITH {cte}
            SELECT
                SUM(CASE WHEN ss.total_score >= 90 THEN 1 ELSE 0 END) AS excellent,
                SUM(CASE WHEN ss.total_score >= 80 AND ss.total_score < 90 THEN 1 ELSE 0 END) AS good,
                SUM(CASE WHEN ss.total_score >= 70 AND ss.total_score < 80 THEN 1 ELSE 0 END) AS normal,
                SUM(CASE WHEN ss.total_score >= 60 AND ss.total_score < 70 THEN 1 ELSE 0 END) AS pass,
                SUM(CASE WHEN ss.total_score < 60 THEN 1 ELSE 0 END) AS risk
            FROM student_score ss
            WHERE 1=1{class_clause}""",
        tuple(params),
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


def daily_record_trend(
    db,
    where_clause: str,
    params: tuple,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, object]]:
    """Build daily record trend chart data.

    Args:
        db: Moral database connection.
        where_clause: SQL WHERE clause for filtering.
        params: Query parameters.

    Returns:
        List of dicts with date and count keys. Defaults to recent 14 days.
    """
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=13))
    if end < start:
        start, end = end, start

    rows = safe_query_all(
        db,
        f"""SELECT DATE(dr.record_date) as record_date, COUNT(*) AS count
            FROM student_daily_record dr
            JOIN student s ON dr.student_id = s.student_id
            WHERE dr.is_deleted = 0 AND dr.record_date >= ? AND dr.record_date <= ? AND {where_clause}
            GROUP BY DATE(dr.record_date)
            ORDER BY DATE(dr.record_date) ASC""",
        (start.isoformat(), end.isoformat(), *params),
    )
    counts = {str(row.get("record_date"))[:10]: int(row.get("count") or 0) for row in rows}
    days = (end - start).days
    return [
        {"date": (start + timedelta(days=offset)).isoformat(), "count": counts.get((start + timedelta(days=offset)).isoformat(), 0)}
        for offset in range(days + 1)
    ]


def class_score_rank_all(
    db,
    class_filter=None,
    grade_filter=None,
    top_n: int = 10,
    semester_id: int = None,
) -> List[Dict[str, object]]:
    """Build class score rank for all visible classes (实时计算德育总分).

    与 moral/evaluation 页面口径一致：基础分 + 日常 + 校级 + 任务 + 集体 - 处分。

    Args:
        db: Moral database connection.
        class_filter: 班级 ID 过滤（班主任单班）。
        grade_filter: 年级 ID 过滤（年级主任）。
        top_n: 返回班级数上限。
        semester_id: 学期 ID，必填（无则返回空）。

    Returns:
        List of dicts with class_name, avg_score, student_count.
    """
    if not semester_id:
        return []

    base_score = _get_base_score(db)
    cte = _real_time_score_cte(semester_id, base_score)

    # 班级过滤条件（基于 class 表）
    class_conditions = ["c.is_active = 1"]
    class_params = []

    if class_filter:
        if isinstance(class_filter, (list, tuple, set)):
            ids = [int(item) for item in class_filter if item]
            if ids:
                class_conditions.append(f"c.class_id IN ({','.join(['?'] * len(ids))})")
                class_params.extend(ids)
        else:
            class_conditions.append("c.class_id = ?")
            class_params.append(class_filter)
    elif grade_filter:
        if isinstance(grade_filter, (list, tuple, set)):
            ids = [int(item) for item in grade_filter if item]
            if ids:
                class_conditions.append(f"c.grade_id IN ({','.join(['?'] * len(ids))})")
                class_params.extend(ids)
        else:
            class_conditions.append("c.grade_id = ?")
            class_params.append(grade_filter)

    class_where = " AND ".join(class_conditions)

    return safe_query_all(
        db,
        f"""WITH {cte}
            SELECT c.class_name,
                   ROUND(AVG(ss.total_score), 1) AS avg_score,
                   COUNT(*) AS student_count
            FROM student_score ss
            JOIN class c ON ss.class_id = c.class_id
            WHERE {class_where}
            GROUP BY c.class_id, c.class_name
            ORDER BY avg_score DESC
            LIMIT {top_n}""",
        tuple(class_params),
    )


def get_avg_moral_score(
    db,
    class_ids: Optional[List[int]] = None,
    semester_id: int = None,
) -> float:
    """计算指定范围内学生的平均德育分（实时计算）。

    Args:
        db: Moral database connection.
        class_ids: 班级 ID 列表，None 表示全校。
        semester_id: 学期 ID。

    Returns:
        平均总分，无数据返回 0.0。
    """
    if not semester_id:
        return 0.0

    base_score = _get_base_score(db)
    cte = _real_time_score_cte(semester_id, base_score)

    class_clause = ""
    params = []
    if class_ids:
        ids = [int(x) for x in class_ids if x]
        if ids:
            class_clause = f" AND ss.class_id IN ({','.join(['?'] * len(ids))})"
            params.extend(ids)

    val = db.query_value(
        f"""WITH {cte}
            SELECT AVG(ss.total_score) FROM student_score ss
            WHERE 1=1{class_clause}""",
        tuple(params),
    )
    try:
        return float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return 0.0


def get_low_score_students(
    db,
    class_ids: Optional[List[int]] = None,
    semester_id: int = None,
    limit: int = 10,
    below: float = 60.0,
) -> List[Dict]:
    """获取低分学生列表（实时计算德育总分）。

    Args:
        db: Moral database connection.
        class_ids: 班级 ID 列表，None 表示全校。
        semester_id: 学期 ID。
        limit: 返回条数。
        below: 低于此分数视为低分。

    Returns:
        学生列表，每项含 student_id, name, class_name, total_score, level。
    """
    from models.datas_api.moral.base import calculate_moral_level

    if not semester_id:
        return []

    base_score = _get_base_score(db)
    cte = _real_time_score_cte(semester_id, base_score)

    class_clause = ""
    params = []
    if class_ids:
        ids = [int(x) for x in class_ids if x]
        if ids:
            class_clause = f" AND ss.class_id IN ({','.join(['?'] * len(ids))})"
            params.extend(ids)

    params = tuple(params) + (below, limit)
    rows = safe_query_all(
        db,
        f"""WITH {cte}
            SELECT s.student_id, s.name, c.class_name, ss.total_score
            FROM student_score ss
            JOIN student s ON ss.student_id = s.student_id
            JOIN class c ON s.class_id = c.class_id
            WHERE 1=1{class_clause} AND ss.total_score < ?
            ORDER BY ss.total_score ASC
            LIMIT ?""",
        params,
    )
    result = []
    for row in rows:
        score = float(row.get("total_score") or 0)
        result.append({
            "student_id": row.get("student_id"),
            "name": row.get("name"),
            "class_name": row.get("class_name"),
            "total_score": score,
            "level": calculate_moral_level(score),
        })
    return result


def get_eval_stats(
    db,
    class_ids: Optional[List[int]] = None,
    semester_id: int = None,
) -> Dict[str, float]:
    """获取德育评价统计（实时计算）。

    Args:
        db: Moral database connection.
        class_ids: 班级 ID 列表。
        semester_id: 学期 ID。

    Returns:
        {avg_score, min_score, max_score, evaluated_count, low_count, pass_count}
    """
    if not semester_id:
        return {
            "avg_score": 0.0,
            "min_score": 0.0,
            "max_score": 0.0,
            "evaluated_count": 0,
            "low_count": 0,
            "pass_count": 0,
        }

    base_score = _get_base_score(db)
    cte = _real_time_score_cte(semester_id, base_score)

    class_clause = ""
    params = []
    if class_ids:
        ids = [int(x) for x in class_ids if x]
        if ids:
            class_clause = f" AND ss.class_id IN ({','.join(['?'] * len(ids))})"
            params.extend(ids)

    row = db.query_one(
        f"""WITH {cte}
            SELECT
                AVG(ss.total_score) AS avg_score,
                MIN(ss.total_score) AS min_score,
                MAX(ss.total_score) AS max_score,
                COUNT(*) AS evaluated_count,
                SUM(CASE WHEN ss.total_score < 60 THEN 1 ELSE 0 END) AS low_count,
                SUM(CASE WHEN ss.total_score >= 60 THEN 1 ELSE 0 END) AS pass_count
            FROM student_score ss
            WHERE 1=1{class_clause}""",
        tuple(params),
    )
    if not row:
        return {
            "avg_score": 0.0, "min_score": 0.0, "max_score": 0.0,
            "evaluated_count": 0, "low_count": 0, "pass_count": 0,
        }
    return {
        "avg_score": float(row.get("avg_score") or 0),
        "min_score": float(row.get("min_score") or 0),
        "max_score": float(row.get("max_score") or 0),
        "evaluated_count": int(row.get("evaluated_count") or 0),
        "low_count": int(row.get("low_count") or 0),
        "pass_count": int(row.get("pass_count") or 0),
    }
