# -*- coding: utf-8 -*-
"""Class dashboard helpers.

Batch 22: Extracted from dashboard.py to keep route handlers thin.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional


def build_gender_mix(students: List[Dict]) -> List[Dict[str, object]]:
    """Build gender distribution chart data.

    Args:
        students: List of student dicts with gender field.

    Returns:
        List of 3 dicts: 男生, 女生, 未维护.
    """
    student_count = len(students)
    male_count = sum(1 for s in students if s.get("gender") == "男")
    female_count = sum(1 for s in students if s.get("gender") == "女")
    unknown_gender_count = student_count - male_count - female_count
    return [
        {"name": "男生", "value": male_count},
        {"name": "女生", "value": female_count},
        {"name": "未维护", "value": unknown_gender_count},
    ]


def build_score_band(eval_stats: Optional[Dict], student_count: int) -> List[Dict[str, object]]:
    """Build score band chart data.

    Args:
        eval_stats: Dict with avg_score, low_count, pass_count, evaluated_count.
        student_count: Total student count.

    Returns:
        List of 3 dicts: 60分以下, 60分以上, 未评价.
    """
    stats = eval_stats or {}
    low_count = int(stats.get("low_count") or 0)
    pass_count = int(stats.get("pass_count") or 0)
    evaluated_count = int(stats.get("evaluated_count") or 0)
    unevaluated_count = max(student_count - evaluated_count, 0)
    return [
        {"name": "60分以下", "value": low_count},
        {"name": "60分以上", "value": pass_count},
        {"name": "未评价", "value": unevaluated_count},
    ]


def filter_birthday_this_month(students: List[Dict], month: int) -> List[Dict]:
    """Filter students with birthday in given month.

    Args:
        students: List of student dicts with birthday field.
        month: Month number (1-12).

    Returns:
        List of student dicts with birthday in the month.
    """
    return [
        s for s in students
        if s.get("birthday") and str(s["birthday"])[5:7] == str(month).zfill(2)
    ]


def filter_birthday_this_week(students: List[Dict], today: date) -> List[Dict]:
    """Filter students with birthday in current week.

    Args:
        students: List of student dicts with birthday field.
        today: Current date.

    Returns:
        List of student dicts with birthday in the week.
    """
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    result = []
    for s in students:
        if not s.get("birthday"):
            continue
        bd = str(s["birthday"])
        try:
            bd_date = date(today.year, int(bd[5:7]), int(bd[8:10]))
            if week_start <= bd_date <= week_end:
                result.append(s)
        except (ValueError, IndexError):
            pass
    return result


def format_birthday_list(students: List[Dict]) -> List[Dict[str, str]]:
    """Format birthday list for dashboard tables.

    Args:
        students: List of student dicts with name and birthday.

    Returns:
        List of dicts with only name and birthday fields.
    """
    return [{"name": s["name"], "birthday": s["birthday"]} for s in students]


def compute_class_stats(students: List[Dict], eval_stats: Optional[Dict]) -> Dict[str, object]:
    """Compute class statistics for dashboard cards.

    Args:
        students: List of student dicts.
        eval_stats: Dict with avg_score, low_count, pass_count, evaluated_count.

    Returns:
        Dict with student_count, male_count, female_count, unknown_gender_count,
        avg_score, low_count, unevaluated_count.
    """
    student_count = len(students)
    male_count = sum(1 for s in students if s.get("gender") == "男")
    female_count = sum(1 for s in students if s.get("gender") == "女")
    unknown_gender_count = student_count - male_count - female_count
    stats = eval_stats or {}
    avg_score = round(float(stats.get("avg_score") or 0), 1)
    low_count = int(stats.get("low_count") or 0)
    evaluated_count = int(stats.get("evaluated_count") or 0)
    unevaluated_count = max(student_count - evaluated_count, 0)
    return {
        "student_count": student_count,
        "male_count": male_count,
        "female_count": female_count,
        "unknown_gender_count": unknown_gender_count,
        "avg_score": avg_score,
        "low_count": low_count,
        "unevaluated_count": unevaluated_count,
    }
