# -*- coding: utf-8 -*-
"""Dashboard Teacher Workbench 业务逻辑模块。

Batch27: 将 get_teacher_workbench 中的业务逻辑抽取为独立辅助函数。
"""

import sqlite3
from datetime import date
from typing import Dict, List, Optional


def get_teacher_today_lessons(teacher_name: str, lesson) -> List[Dict]:
    """获取教师今日课程列表。

    Args:
        teacher_name: 教师用户名
        lesson: Lesson 实例（课表缓存）

    Returns:
        今日课程列表，每项包含 class_name/time/period/subject
    """
    today_lessons = []
    try:
        schedule_df = lesson.get_cache_data("today_schedule")
        if schedule_df is None or schedule_df.empty:
            return today_lessons

        subject_df = schedule_df.copy()
        teacher_df = lesson.schedule_service.replace_subject_teacher(schedule_df, teacher_flag=True)

        # 构造节次信息映射
        time_table = lesson.get_cache_data("time_table")
        period_lookup = {}
        if time_table is not None and not time_table.empty:
            for _, period_row in time_table.iterrows():
                order = str(period_row.get("order", "")).strip()
                period_lookup[order] = {
                    "label": str(period_row.get("label") or order).strip(),
                    "time_range": str(period_row.get("show_time") or period_row.get("time_table") or "").strip(),
                }

        # 获取班级列表
        class_template = lesson.get_cache_data("class_template")
        class_names = class_template["class_name"].tolist() if class_template is not None and not class_template.empty else []

        # 匹配教师课程
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

    return today_lessons


def get_teacher_publication_stats(teacher_name: str, homework_db_conn) -> Dict[str, int]:
    """获取教师发布统计（作业、公告）。

    Args:
        teacher_name: 教师用户名
        homework_db_conn: homework.db 连接上下文管理器

    Returns:
        {"homework_published": int, "announcements_published": int}
    """
    homework_published = 0
    announcements_published = 0

    try:
        with homework_db_conn() as hw_db:
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

    return {
        "homework_published": homework_published,
        "announcements_published": announcements_published,
    }


def get_teacher_moral_stats(teacher_name: str, moral_db, safe_count) -> Dict[str, int]:
    """获取教师德育参与统计（日常记录、点滴记录）。

    Args:
        teacher_name: 教师用户名
        moral_db: moral.db 上下文管理器
        safe_count: 安全计数辅助函数

    Returns:
        {"daily_created": int, "moment_created": int}
    """
    with moral_db() as db:
        daily_created = safe_count(
            db,
            "SELECT COUNT(*) FROM student_daily_record WHERE recorder = ? AND is_deleted = 0",
            (teacher_name,)
        )
        moment_created = safe_count(
            db,
            "SELECT COUNT(*) FROM student_moment_record WHERE recorder = ? AND is_deleted = 0",
            (teacher_name,)
        )

    return {
        "daily_created": daily_created,
        "moment_created": moment_created,
    }


def get_teacher_invigilation_tasks(teacher_name: str, today_str: str, invigilation_db_conn) -> List[Dict]:
    """获取教师近期监考任务。

    Args:
        teacher_name: 教师用户名
        today_str: 今日日期字符串（YYYY-MM-DD）
        invigilation_db_conn: invigilation.db 连接上下文管理器

    Returns:
        监考任务列表，每项包含 project_name/exam_date/start_time/end_time/subject/room_name/grade_name
    """
    invigilation_tasks = []

    try:
        with invigilation_db_conn() as inv_db:
            cursor = inv_db.cursor()
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

    return invigilation_tasks


def build_teacher_workbench_response(
    teacher_name: str,
    today_lessons: List[Dict],
    publication_stats: Dict[str, int],
    moral_stats: Dict[str, int],
    invigilation_tasks: List[Dict],
    lesson_workload: Dict,
    start_date: date,
    end_date: date,
    metric,
    now_text,
) -> Dict:
    """组装教师工作台返回数据。

    Args:
        teacher_name: 教师用户名
        today_lessons: 今日课程列表
        publication_stats: 发布统计
        moral_stats: 德育参与统计
        invigilation_tasks: 监考任务列表
        lesson_workload: 课时统计数据
        start_date: 统计起始日期
        end_date: 统计结束日期
        metric: 指标卡片辅助函数
        now_text: 当前时间文本函数

    Returns:
        Teacher Workbench API 返回结构
    """
    my_lesson_count = sum(row["lesson_count"] for row in lesson_workload["rows"])

    return {
        "success": True,
        "data": {
            "cards": [
                metric("今日课程", len(today_lessons), "节"),
                metric("区间课时", my_lesson_count, "节"),
                metric("发布作业", publication_stats["homework_published"], "份", "/homework"),
                metric("发布公告", publication_stats["announcements_published"], "份"),
                metric("日常记录", moral_stats["daily_created"], "条", "/moral/daily-record"),
                metric("点滴记录", moral_stats["moment_created"], "条", "/moral/moment-record"),
                metric("监考任务", len(invigilation_tasks), "场", "/invigilation"),
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
                "message": lesson_workload["message"],
            },
            "range": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
            "updated_at": now_text(),
        },
    }
