# -*- coding: utf-8 -*-
"""数据驾驶舱 API。"""

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


def _safe_count(db, sql: str, params=None) -> int:
    try:
        return int(db.query_value(sql, params) or 0)
    except Exception:
        return 0


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
async def get_moral_dashboard_summary(user: User = Depends(get_current_user)):
    if not (_is_moral_manager(user) or has_user_role(user, "cleader")):
        raise HTTPException(status_code=403, detail="无德育驾驶舱权限")

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
                LIMIT 5""",
            tuple(params),
        )

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("可见学生", student_count, "人"),
                _metric("日常记录", daily_count, "条", "/moral/daily-record"),
                _metric("平均德育分", round(float(avg_score or 0), 1), "分", "/moral/evaluation"),
            ],
            "tables": {"low_students": low_students},
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
    lesson = Lesson()
    counter = Counter()
    covered_dates = set()
    class_template = lesson.get_cache_data("class_template")
    class_names = class_template["class_name"].tolist() if class_template is not None and not class_template.empty else []

    for item in _schedule_frames_for_range(start_date, end_date):
        df = item["df"]
        if "weekday" not in df.columns:
            continue
        teacher_df = lesson.schedule_service.replace_subject_teacher(df, teacher_flag=True)
        for _, row in teacher_df.iterrows():
            try:
                weekday = int(row.get("weekday"))
            except Exception:
                continue
            actual_date = item["monday"] + timedelta(days=weekday - 1)
            if actual_date < start_date or actual_date > end_date:
                continue
            covered_dates.add(actual_date.isoformat())
            for class_name in class_names:
                teacher_name = row.get(class_name)
                if teacher_name is None:
                    continue
                if isinstance(teacher_name, float) and pd.isna(teacher_name):
                    continue
                teacher_name = str(teacher_name).strip()
                if not teacher_name or teacher_name == "-":
                    continue
                counter[teacher_name] += 1

    rows = [
        {"teacher_name": name, "lesson_count": count}
        for name, count in counter.most_common()
    ]
    return {
        "rows": rows,
        "top5": rows[:5],
        "covered_dates": sorted(covered_dates),
        "message": "仅统计当前系统已加载的当前周/下周课表。",
    }


@router.get("/teaching/summary", summary="教务驾驶舱总览")
async def get_teaching_dashboard_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user: User = Depends(get_current_user),
):
    if not _is_jiaowu(user):
        raise HTTPException(status_code=403, detail="无教务驾驶舱权限")

    today = date.today()
    start_date = start_date or today
    end_date = end_date or (today + timedelta(days=6))
    if (end_date - start_date).days > 62:
        raise HTTPException(status_code=400, detail="统计时间跨度不能超过 62 天")

    with get_moral_db() as db:
        class_count = _safe_count(db, "SELECT COUNT(*) FROM class WHERE is_active = 1")
        student_count = _safe_count(db, "SELECT COUNT(*) FROM student WHERE status = '在校'")
        teacher_count = _safe_count(db, "SELECT COUNT(*) FROM teacher WHERE COALESCE(identity_type, 'teacher') = 'teacher' AND is_active = 1")

    workload = _teacher_lesson_counts(start_date, end_date)
    return {
        "success": True,
        "data": {
            "cards": [
                _metric("班级", class_count, "个", "/moral/config/class"),
                _metric("在校学生", student_count, "人", "/moral/config/student"),
                _metric("教师账号", teacher_count, "人", "/teacher-manage"),
                _metric("区间课时", sum(row["lesson_count"] for row in workload["rows"]), "节"),
            ],
            "tables": {"teacher_workload": workload["rows"], "teacher_workload_top5": workload["top5"]},
            "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "covered_dates": workload["covered_dates"],
            "message": workload["message"],
            "updated_at": _now_text(),
        },
    }
