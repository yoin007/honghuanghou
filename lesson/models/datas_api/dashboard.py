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


def _class_score_top5(db, where_clause: str, params: tuple) -> List[Dict[str, object]]:
    return _safe_query_all(
        db,
        f"""SELECT c.class_name, ROUND(AVG(me.total_score), 1) AS avg_score, COUNT(*) AS student_count
            FROM moral_evaluation me
            JOIN student s ON me.student_id = s.student_id
            JOIN class c ON me.class_id = c.class_id
            WHERE {where_clause}
            GROUP BY c.class_id, c.class_name
            ORDER BY avg_score DESC
            LIMIT 5""",
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
        query_params = tuple(params)
        charts = {
            "score_distribution": _score_distribution(db, where_clause, query_params),
            "daily_event_mix": _daily_event_mix(db, where_clause, query_params),
            "daily_record_trend": _daily_record_trend(db, where_clause, query_params),
            "class_score_top5": _class_score_top5(db, where_clause, query_params),
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
    if not isinstance(start_date, date):
        start_date = None
    if not isinstance(end_date, date):
        end_date = None
    start_date = start_date or today
    end_date = end_date or (today + timedelta(days=6))
    if (end_date - start_date).days > 62:
        raise HTTPException(status_code=400, detail="统计时间跨度不能超过 62 天")

    with get_moral_db() as db:
        class_count = _safe_count(db, "SELECT COUNT(*) FROM class WHERE is_active = 1")
        student_count = _safe_count(db, "SELECT COUNT(*) FROM student WHERE status = '在校'")
        teacher_count = _safe_count(db, "SELECT COUNT(*) FROM teacher WHERE COALESCE(identity_type, 'teacher') = 'teacher' AND is_active = 1")
        class_size_top5 = _safe_query_all(
            db,
            """SELECT c.class_name, COUNT(s.student_id) AS student_count
                FROM class c
                LEFT JOIN student s ON s.class_id = c.class_id AND s.status = '在校'
                WHERE c.is_active = 1
                GROUP BY c.class_id, c.class_name
                ORDER BY student_count DESC
                LIMIT 5""",
        )

    workload = _teacher_lesson_counts(start_date, end_date)
    workload_top5 = workload["top5"]
    return {
        "success": True,
        "data": {
            "cards": [
                _metric("班级", class_count, "个", "/moral/config/class"),
                _metric("在校学生", student_count, "人", "/moral/config/student"),
                _metric("教师账号", teacher_count, "人", "/teacher-manage"),
                _metric("区间课时", sum(row["lesson_count"] for row in workload["rows"]), "节"),
            ],
            "charts": {
                "teacher_workload_top5": workload_top5,
                "class_size_top5": class_size_top5,
                "resource_mix": [
                    {"name": "班级", "value": class_count},
                    {"name": "学生", "value": student_count},
                    {"name": "教师", "value": teacher_count},
                ],
            },
            "tables": {"teacher_workload": workload["rows"], "teacher_workload_top5": workload_top5},
            "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "covered_dates": workload["covered_dates"],
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
    user: User = Depends(get_current_user),
):
    """班级驾驶舱：班级基础、学习活动、德育表现、出勤事务、生日关怀"""
    with get_moral_db() as db:
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
        female_count = student_count - male_count

        # 德育评价统计
        eval_stats = db.query_one(
            """SELECT
                AVG(total_score) AS avg_score,
                MIN(total_score) AS min_score,
                MAX(total_score) AS max_score,
                SUM(CASE WHEN total_score < 60 THEN 1 ELSE 0 END) AS low_count
            FROM moral_evaluation WHERE class_id = %s""",
            (class_id,)
        )
        avg_score = round(float(eval_stats.get("avg_score") or 0), 1)
        low_students = db.query_all(
            """SELECT s.student_id, s.name, me.total_score
            FROM moral_evaluation me
            JOIN student s ON me.student_id = s.student_id
            WHERE me.class_id = %s AND me.total_score < 60
            ORDER BY me.total_score ASC LIMIT 5""",
            (class_id,)
        )

        # 本月生日学生
        today = date.today()
        month_start = today.replace(day=1)
        month_end = (month_start.replace(month=month_start.month % 12 + 1, day=1) - timedelta(days=1)).isoformat()
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
                _metric("平均德育分", avg_score, "分", "/moral/evaluation"),
                _metric("低分学生", len(low_students), "人"),
                _metric("本月作业", homework_count, "份", "/homework"),
                _metric("本月公告", announcement_count, "份"),
                _metric("请假人数", active_leave_count, "人"),
            ],
            "charts": {
                "gender_mix": [
                    {"name": "男生", "value": male_count},
                    {"name": "女生", "value": female_count},
                ],
                "score_band": [
                    {"name": "60分以下", "value": len(low_students)},
                    {"name": "60分以上", "value": student_count - len(low_students)},
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
            "updated_at": _now_text(),
        },
    }


@router.get("/teacher/workbench", summary="教师个人工作台")
async def get_teacher_workbench(user: User = Depends(get_current_user)):
    """教师工作台：今日事项、发布内容、德育参与、监考任务"""
    teacher_name = user.username
    today_str = date.today().isoformat()

    # 今日课程（从课表）
    today_lessons = []
    try:
        lesson = Lesson()
        schedule_df = lesson.get_cache_data("current_schedule")
        if schedule_df is not None and not schedule_df.empty:
            weekday = date.today().weekday() + 1  # Monday = 1
            teacher_df = lesson.schedule_service.replace_subject_teacher(schedule_df, teacher_flag=True)
            for col in teacher_df.columns:
                if col in ["weekday", "time", "subject", "class"]:
                    continue
                # 检查该列是否有当前教师的名字
                mask = teacher_df["weekday"] == weekday
                for idx in teacher_df[mask].index:
                    teacher_in_cell = str(teacher_df.at[idx, col] or "")
                    if teacher_name in teacher_in_cell:
                        today_lessons.append({
                            "class_name": col,
                            "time": str(teacher_df.at[idx, "time"] or ""),
                            "subject": str(teacher_df.at[idx, "subject"] or ""),
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

    return {
        "success": True,
        "data": {
            "cards": [
                _metric("今日课程", len(today_lessons), "节"),
                _metric("发布作业", homework_published, "份", "/homework"),
                _metric("发布公告", announcements_published, "份"),
                _metric("日常记录", daily_created, "条", "/moral/daily-record"),
                _metric("点滴记录", moment_created, "条", "/moral/moment-record"),
                _metric("监考任务", len(invigilation_tasks), "场", "/invigilation"),
            ],
            "tables": {
                "today_lessons": today_lessons,
                "invigilation_tasks": invigilation_tasks,
            },
            "updated_at": _now_text(),
        },
    }
