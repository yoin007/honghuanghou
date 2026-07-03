# -*- coding: utf-8 -*-
"""Dashboard Invigilation 业务逻辑模块。

Batch28: 将 get_invigilation_dashboard_summary 中的业务逻辑抽取为独立辅助函数。
"""

from typing import Dict, List


def get_invigilation_project_stats(inv_db_conn) -> Dict[str, int]:
    """获取考试项目状态统计。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器

    Returns:
        {"total": int, "draft": int, "saved": int, "notified": int}
    """
    project_stats = {"total": 0, "draft": 0, "saved": 0, "notified": 0}

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()
            cursor.execute(
                """SELECT status, COUNT(*) AS count FROM exam_project GROUP BY status"""
            )
            for row in cursor.fetchall():
                status = row["status"]
                count = row["count"]
                project_stats["total"] += count
                if status in project_stats:
                    project_stats[status] = count
    except Exception:
        pass

    return project_stats


def get_invigilation_slot_stats(inv_db_conn, today_str: str) -> Dict[str, int]:
    """获取监考场次统计（已安排/未安排）。

    已安排定义：主监或副监至少一位有效教师。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器
        today_str: 今日日期字符串（YYYY-MM-DD）

    Returns:
        {"total": int, "arranged": int, "unarranged": int}
    """
    slot_stats = {"total": 0, "arranged": 0, "unarranged": 0}

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()

            cursor.execute(
                """SELECT COUNT(*) FROM invigilation_slot WHERE exam_date >= ?""",
                (today_str,)
            )
            slot_stats["total"] = cursor.fetchone()[0] or 0

            cursor.execute(
                """SELECT COUNT(*) FROM invigilation_slot
                   WHERE exam_date >= ?
                     AND (
                       (teacher_id IS NOT NULL AND teacher_id != '')
                       OR (assistant_teacher_id IS NOT NULL AND assistant_teacher_id != '')
                     )""",
                (today_str,)
            )
            slot_stats["arranged"] = cursor.fetchone()[0] or 0
            slot_stats["unarranged"] = slot_stats["total"] - slot_stats["arranged"]
    except Exception:
        pass

    return slot_stats


def get_invigilation_conflict_count(inv_db_conn, today_str: str) -> int:
    """获取冲突场次数（同一教师同一时间；主监副监都算）。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器
        today_str: 今日日期字符串（YYYY-MM-DD）

    Returns:
        冲突场次数量
    """
    conflict_count = 0

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()
            cursor.execute(
                """WITH slot_role AS (
                       SELECT teacher_name, exam_date, start_time
                       FROM invigilation_slot
                       WHERE exam_date >= ? AND teacher_name IS NOT NULL AND teacher_name != ''
                       UNION ALL
                       SELECT assistant_teacher_name AS teacher_name, exam_date, start_time
                       FROM invigilation_slot
                       WHERE exam_date >= ? AND assistant_teacher_name IS NOT NULL AND assistant_teacher_name != ''
                   )
                   SELECT teacher_name, exam_date, start_time, COUNT(*) AS count
                   FROM slot_role
                   GROUP BY teacher_name, exam_date, start_time
                   HAVING count > 1""",
                (today_str, today_str)
            )
            for row in cursor.fetchall():
                conflict_count += row["count"] - 1
    except Exception:
        pass

    return conflict_count


def get_invigilation_notification_stats(inv_db_conn) -> Dict[str, int]:
    """获取通知状态统计。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器

    Returns:
        {"success": int, "failed": int, "skipped": int, "pending": int}
    """
    notification_stats = {"success": 0, "failed": 0, "skipped": 0, "pending": 0}

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()
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
    except Exception:
        pass

    return notification_stats


def get_invigilation_teacher_workload(inv_db_conn, today_str: str, top_n: int) -> List[Dict]:
    """获取教师监考负载排行（主监副监都计入）。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器
        today_str: 今日日期字符串（YYYY-MM-DD）
        top_n: 返回数量限制

    Returns:
        教师监考负载列表，每项包含 teacher_name/invigilation_count
    """
    teacher_workload = []

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()
            cursor.execute(
                """WITH slot_role AS (
                       SELECT teacher_name
                       FROM invigilation_slot
                       WHERE exam_date >= ? AND teacher_name IS NOT NULL AND teacher_name != ''
                       UNION ALL
                       SELECT assistant_teacher_name AS teacher_name
                       FROM invigilation_slot
                       WHERE exam_date >= ? AND assistant_teacher_name IS NOT NULL AND assistant_teacher_name != ''
                   )
                   SELECT teacher_name, COUNT(*) AS invigilation_count
                   FROM slot_role
                   GROUP BY teacher_name
                   ORDER BY invigilation_count DESC
                   LIMIT ?""",
                (today_str, today_str, top_n)
            )
            for row in cursor.fetchall():
                teacher_workload.append({
                    "teacher_name": row["teacher_name"],
                    "invigilation_count": row["invigilation_count"],
                })
    except Exception:
        pass

    return teacher_workload


def get_invigilation_unarranged_slots(inv_db_conn, today_str: str) -> List[Dict]:
    """获取未安排场次列表（主监副监均无）。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器
        today_str: 今日日期字符串（YYYY-MM-DD）

    Returns:
        未安排场次列表，每项包含 project_id/project_name/exam_date/start_time/end_time/subject/room_name/grade_name
    """
    unarranged_slots = []

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()
            cursor.execute(
                """SELECT s.project_id, p.name AS project_name, s.exam_date,
                          s.start_time, s.end_time, s.subject, s.room_name, s.grade_name
                   FROM invigilation_slot s
                   LEFT JOIN exam_project p ON s.project_id = p.id
                   WHERE s.exam_date >= ?
                     AND (s.teacher_id IS NULL OR s.teacher_id = '')
                     AND (s.assistant_teacher_id IS NULL OR s.assistant_teacher_id = '')
                   ORDER BY s.exam_date, s.start_time
                   LIMIT 10""",
                (today_str,)
            )
            for row in cursor.fetchall():
                unarranged_slots.append(dict(row))
    except Exception:
        pass

    return unarranged_slots


def get_invigilation_conflict_slots(inv_db_conn, today_str: str) -> List[Dict]:
    """获取冲突场次详情（主监副监都算）。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器
        today_str: 今日日期字符串（YYYY-MM-DD）

    Returns:
        冲突场次列表，每项包含 teacher_name/exam_date/start_time/subjects
    """
    conflict_slots = []

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()
            cursor.execute(
                """WITH slot_role AS (
                       SELECT teacher_name, exam_date, start_time, subject, room_name
                       FROM invigilation_slot
                       WHERE exam_date >= ? AND teacher_name IS NOT NULL AND teacher_name != ''
                       UNION ALL
                       SELECT assistant_teacher_name AS teacher_name, exam_date, start_time, subject, room_name
                       FROM invigilation_slot
                       WHERE exam_date >= ? AND assistant_teacher_name IS NOT NULL AND assistant_teacher_name != ''
                   )
                   SELECT teacher_name, exam_date, start_time,
                          GROUP_CONCAT(subject || ' (' || room_name || ')', ', ') AS subjects
                   FROM slot_role
                   GROUP BY teacher_name, exam_date, start_time
                   HAVING COUNT(*) > 1
                   ORDER BY exam_date, start_time
                   LIMIT 10""",
                (today_str, today_str)
            )
            for row in cursor.fetchall():
                conflict_slots.append(dict(row))
    except Exception:
        pass

    return conflict_slots


def get_invigilation_notification_failed(inv_db_conn) -> List[Dict]:
    """获取通知失败记录。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器

    Returns:
        通知失败列表，每项包含 project_id/project_name/teacher_name/sent_status/sent_at/error_message
    """
    notification_failed = []

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()
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
    except Exception:
        pass

    return notification_failed


def get_invigilation_recent_projects(inv_db_conn, top_n: int) -> List[Dict]:
    """获取近期考试项目列表。

    Args:
        inv_db_conn: invigilation.db 连接上下文管理器
        top_n: 返回数量限制

    Returns:
        近期项目列表，每项包含 id/name/status/grade_ids/version_no/updated_at
    """
    recent_projects = []

    try:
        with inv_db_conn() as inv_db:
            cursor = inv_db.cursor()
            cursor.execute(
                """SELECT id, name, status, grade_ids, version_no, updated_at
                   FROM exam_project
                   ORDER BY updated_at DESC
                   LIMIT ?""",
                (top_n,)
            )
            for row in cursor.fetchall():
                recent_projects.append(dict(row))
    except Exception:
        pass

    return recent_projects


def build_invigilation_dashboard_response(
    project_stats: Dict[str, int],
    slot_stats: Dict[str, int],
    conflict_count: int,
    notification_stats: Dict[str, int],
    teacher_workload: List[Dict],
    unarranged_slots: List[Dict],
    conflict_slots: List[Dict],
    notification_failed: List[Dict],
    recent_projects: List[Dict],
    top_n: int,
    metric,
    now_text,
) -> Dict:
    """组装监考驾驶舱返回数据。

    Args:
        project_stats: 考试项目状态统计
        slot_stats: 监考场次统计
        conflict_count: 冲突场次数
        notification_stats: 通知状态统计
        teacher_workload: 教师监考负载排行
        unarranged_slots: 未安排场次列表
        conflict_slots: 冲突场次详情
        notification_failed: 通知失败记录
        recent_projects: 近期考试项目列表
        top_n: 返回数量限制
        metric: 指标卡片辅助函数
        now_text: 当前时间文本函数

    Returns:
        Invigilation Dashboard API 返回结构
    """
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
                metric("考试项目", project_stats["total"], "个", "/invigilation"),
                metric("待安排场次", slot_stats["unarranged"], "场"),
                metric("冲突场次", conflict_count, "场"),
                metric("安排完整率", arrangement_rate, "%"),
                metric("通知成功率", notification_success_rate, "%"),
                metric("通知失败", notification_stats["failed"] + notification_stats["skipped"], "条"),
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
            },
            "tables": {
                "unarranged_slots": unarranged_slots,
                "conflict_slots": conflict_slots,
                "notification_failed": notification_failed,
                "recent_projects": recent_projects,
                "teacher_workload_rank": teacher_workload,
            },
            "top_n": top_n,
            "updated_at": now_text(),
        },
    }