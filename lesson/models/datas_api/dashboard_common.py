# -*- coding: utf-8 -*-
"""Shared helpers for dashboard routes and services."""

from datetime import date, datetime, timedelta
from typing import Dict, List

from models.datas_api.auth import User, is_admin_user
from models.datas_api.moral.base import has_user_role


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_jiaowu(user: User) -> bool:
    return is_admin_user(user) or has_user_role(user, "jiaowu")


def is_moral_manager(user: User) -> bool:
    return is_admin_user(user) or any(has_user_role(user, role) for role in ["jiaowu", "xuefa"])


def date_range(start_date: date, end_date: date) -> List[date]:
    days = (end_date - start_date).days
    if days < 0:
        return []
    return [start_date + timedelta(days=offset) for offset in range(days + 1)]


def metric(label: str, value, unit: str = "", route: str = "") -> Dict[str, object]:
    return {"label": label, "value": value, "unit": unit, "route": route}


def normalize_top_n(top_n: int = 5) -> int:
    try:
        value = int(top_n)
    except Exception:
        value = 5
    return max(1, min(value, 50))


def current_week_range(today: date = None) -> Dict[str, date]:
    current = today or date.today()
    start = current - timedelta(days=current.weekday())
    return {"start": start, "end": start + timedelta(days=6)}


def safe_count(db, sql: str, params=None) -> int:
    try:
        return int(db.query_value(sql, params) or 0)
    except Exception:
        return 0


def safe_query_all(db, sql: str, params=None) -> List[Dict[str, object]]:
    try:
        return db.query_all(sql, params) or []
    except Exception:
        return []
