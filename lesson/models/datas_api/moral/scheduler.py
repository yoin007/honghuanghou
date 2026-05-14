# -*- coding: utf-8 -*-
"""
德育评价系统定时任务调度模块

使用 APScheduler 实现定时任务：
- birthday_reminder（每日05:21）：检测今日生日学生，发布班级公告
- birthday_blessing（每日05:51）：发布班级祝福公告
- profile_update_check（每周一09:00）：检查需要更新画像的学生
- semester_evaluation（学期末）：计算学期德育评价
- task_carryover（学年末）：处理未完成任务结转
- warning_check（每日10:00）：检查预警阈值
"""

import logging
import json
from datetime import datetime, date, timedelta
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# 全局调度器实例
scheduler = None


def get_scheduler():
    """获取调度器实例"""
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler()
    return scheduler


# =============================================================================
# 定时任务定义
# =============================================================================

def birthday_reminder_task():
    """
    每日生日提醒任务（05:21执行）

    流程：
    1. 查询今日生日学生
    2. 发布班级公告通知全班
    3. 记录日志
    """
    logger.info("执行生日提醒任务")

    from .base import get_moral_db
    from models.lesson.homework import Homework

    with get_moral_db() as db:
        today = datetime.now().strftime('%m-%d')

        # 查询今日生日学生，按班级分组
        students = db.query_all(
            """SELECT s.student_id, s.name, s.birthday,
                   c.class_id, c.class_code, c.class_name, c.leader_wxid, c.leader_name, c.leader_ids, c.leader_names,
                   g.grade_name
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            JOIN grade g ON s.grade_id = g.grade_id
            WHERE strftime('%m-%d', s.birthday) = ?
            AND s.status = '在校'
            AND s.is_active = 1""",
            (today,)
        )

        if not students:
            logger.info("今日无学生生日")
            return

        logger.info(f"今日有 {len(students)} 位学生生日")

        # 按班级分组，每班发布一次公告
        from collections import defaultdict
        class_students = defaultdict(list)
        for student in students:
            class_students[student['class_code']].append(student)

        # 发布班级公告
        with Homework() as hw:
            for class_code, class_student_list in class_students.items():
                # 构建公告内容
                student_names = [s['name'] for s in class_student_list]
                class_name = class_student_list[0]['class_name']

                # 获取班主任名称作为署名
                leader_names_str = class_student_list[0].get('leader_names', '')
                leader_name = class_student_list[0].get('leader_name', '')
                if leader_names_str:
                    first_leader = leader_names_str.split(',')[0].strip()
                    author = first_leader or "班主任"
                else:
                    author = leader_name or "班主任"

                if len(student_names) == 1:
                    content = (
                        f"🎂 今日生日提醒\n\n"
                        f"亲爱的同学们，今天是 {student_names[0]} 同学的生日！\n"
                        f"让我们一起为 {student_names[0]} 送上祝福，祝生日快乐，学业进步！\n\n"
                        f"— {author}\n"
                        f"{datetime.now().strftime('%Y-%m-%d')}"
                    )
                else:
                    names_str = '、'.join(student_names)
                    content = (
                        f"🎂 今日生日提醒\n\n"
                        f"亲爱的同学们，今天是 {names_str} 同学的生日！\n"
                        f"让我们一起为他们送上祝福，祝生日快乐，学业进步！\n\n"
                        f"— {author}\n"
                        f"{datetime.now().strftime('%Y-%m-%d')}"
                    )

                title = f"🎂 今日生日提醒"

                try:
                    hw.add_announcement(class_code, title, author, content, None)
                    logger.info(f"已发布班级公告：{class_name}，作者：{author}，学生：{student_names}")
                except Exception as e:
                    logger.error(f"发布公告失败（{class_name}）：{e}")

        # 记录提醒日志
        for student in students:
            db.execute(
                """INSERT INTO birthday_reminder
                (student_id, reminder_date, reminder_type, message, is_sent, recipient_type)
                VALUES (?, ?, 'birthday', ?, 1, 'class')""",
                (student['student_id'], date.today(), f"班级公告：{class_name}")
            )


def birthday_blessing_task():
    """
    每日生日祝福任务（05:51执行）

    发布班级祝福公告
    """
    logger.info("执行生日祝福任务")

    from .base import get_moral_db
    from models.lesson.homework import Homework

    with get_moral_db() as db:
        # 检查祝福配置是否启用
        config = db.query_one(
            """SELECT config_value FROM birthday_reminder_config
            WHERE config_key = 'blessing_enabled'"""
        )

        # 默认启用
        blessing_enabled = True
        if config:
            try:
                import json
                blessing_enabled = json.loads(config['config_value'])
            except:
                pass

        if not blessing_enabled:
            logger.info("生日祝福功能已禁用")
            return

        today = datetime.now().strftime('%m-%d')

        # 查询今日生日学生，按班级分组
        students = db.query_all(
            """SELECT s.student_id, s.name, s.birthday,
                   c.class_id, c.class_code, c.class_name, c.leader_name, c.leader_ids, c.leader_names
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE strftime('%m-%d', s.birthday) = ?
            AND s.status = '在校'
            AND s.is_active = 1""",
            (today,)
        )

        if not students:
            logger.info("今日无学生生日")
            return

        logger.info(f"今日有 {len(students)} 位学生生日，准备发布祝福公告")

        # 按班级分组
        class_students = defaultdict(list)
        for student in students:
            class_students[student['class_code']].append(student)

        # 获取祝福模板
        template_config = db.query_one(
            """SELECT config_value FROM birthday_reminder_config
            WHERE config_key = 'message_template'"""
        )

        template = "亲爱的 {name}，今天是你的生日，祝你生日快乐，学业进步，前程似锦！🎉"
        if template_config:
            try:
                import json
                templates = json.loads(template_config['config_value'])
                template = templates.get('student', template)
            except:
                pass

        # 发布班级祝福公告
        with Homework() as hw:
            for class_code, class_student_list in class_students.items():
                class_name = class_student_list[0]['class_name']
                student_names = [s['name'] for s in class_student_list]

                # 获取班主任名称作为署名
                leader_names_str = class_student_list[0].get('leader_names', '')
                leader_name = class_student_list[0].get('leader_name', '')
                if leader_names_str:
                    first_leader = leader_names_str.split(',')[0].strip()
                    author = first_leader or "班主任"
                else:
                    author = leader_name or "班主任"

                # 构建祝福内容
                if len(student_names) == 1:
                    individual_blessing = template.format(name=student_names[0])
                    content = (
                        f"🎉 生日快乐！\n\n"
                        f"{individual_blessing}\n\n"
                        f"— {author}\n"
                        f"{datetime.now().strftime('%Y-%m-%d')}"
                    )
                else:
                    blessings = []
                    for name in student_names:
                        blessings.append(template.format(name=name))
                    content = (
                        f"🎉 生日快乐！\n\n"
                        f"{chr(10).join(blessings)}\n\n"
                        f"— {author}\n"
                        f"{datetime.now().strftime('%Y-%m-%d')}"
                    )

                title = f"🎉 生日祝福"

                try:
                    hw.add_announcement(class_code, title, author, content, None)
                    logger.info(f"已发布班级祝福公告：{class_name}，作者：{author}，学生：{student_names}")

                    # 记录发送日志
                    for student in class_student_list:
                        db.execute(
                            """INSERT INTO birthday_reminder
                            (student_id, reminder_date, reminder_type, message, is_sent, sent_at, recipient_type)
                            VALUES (?, ?, 'blessing', ?, 1, datetime('now','localtime'), 'class')""",
                            (student['student_id'], date.today(), f"班级祝福公告：{class_name}")
                        )
                except Exception as e:
                    logger.error(f"发布祝福公告失败（{class_name}）：{e}")


def profile_update_check_task():
    """
    每周一画像更新检查任务（09:00执行）

    检查新记录超过阈值的学生，触发画像生成
    """
    logger.info("执行画像更新检查任务")

    from .base import get_moral_db
    from .profile import generate_student_profile_internal

    with get_moral_db() as db:
        # 获取画像更新配置
        config = db.query_one(
            """SELECT config_value FROM profile_config WHERE config_key = 'update_frequency'"""
        )

        min_records = 5  # 默认阈值
        if config:
            try:
                import json
                freq_config = json.loads(config['config_value'])
                min_records = freq_config.get('min_records', 5)
            except:
                pass

        current_semester = db.query_one(
            "SELECT semester_id FROM semester WHERE status = 1"
        )

        if not current_semester:
            logger.warning("当前学期未配置")
            return

        semester_id = current_semester['semester_id']

        # 查找本周新增记录超过阈值的学生
        week_start = date.today() - timedelta(days=7)

        students_with_new_records = db.query_all(
            """SELECT s.student_id, s.name, COUNT(*) as new_record_count
            FROM student s
            JOIN student_daily_record dr ON s.student_id = dr.student_id
            WHERE dr.semester_id = ?
            AND dr.record_date >= ?
            AND dr.is_deleted = 0
            AND s.status = '在校'
            GROUP BY s.student_id
            HAVING COUNT(*) >= ?""",
            (semester_id, week_start, min_records)
        )

        if not students_with_new_records:
            logger.info("本周无学生需要更新画像")
            return

        logger.info(f"本周有 {len(students_with_new_records)} 位学生需要更新画像")

        for student in students_with_new_records[:10]:  # 限制每次最多生成10个
            try:
                generate_student_profile_internal(db, student['student_id'])
                logger.info(f"已生成学生画像：{student['name']}")
            except Exception as e:
                logger.error(f"生成画像失败：{student['student_id']}，错误：{e}")


def warning_check_task():
    """
    每日预警检查任务（10:00执行）

    检查德育分过低、扣分过多、违纪次数过多的学生
    """
    logger.info("执行预警检查任务")

    from .base import get_moral_db

    with get_moral_db() as db:
        current_semester = db.query_one(
            "SELECT semester_id FROM semester WHERE status = 1"
        )

        if not current_semester:
            return

        semester_id = current_semester['semester_id']

        # 获取预警配置
        warning_configs = db.query_all(
            "SELECT * FROM warning_config WHERE is_active = 1"
        )

        for config in warning_configs:
            trigger_type = config['trigger_type']
            trigger_value = config['trigger_value']

            if trigger_type == 'score_threshold':
                # 德育分过低预警（< 50）或扣分过多预警（累计扣分 > 20）
                if trigger_value < 60:  # 低分预警
                    low_score_students = db.query_all(
                        """SELECT me.student_id, s.name, me.total_score, c.class_name, c.leader_name
                        FROM moral_evaluation me
                        JOIN student s ON me.student_id = s.student_id
                        JOIN class c ON s.class_id = c.class_id
                        WHERE me.semester_id = ? AND me.total_score < ?""",
                        (semester_id, trigger_value)
                    )

                    for student in low_score_students:
                        # 检查是否已有预警记录
                        existing = db.query_one(
                            """SELECT id FROM warning_log
                            WHERE student_id = ? AND semester_id = ?
                            AND rule_id = ? AND DATE(created_at) = ?""",
                            (student['student_id'], semester_id, config['id'], date.today())
                        )

                        if not existing:
                            message = (
                                f"【德育预警】\n"
                                f"学生：{student['name']}（{student['student_id']}）\n"
                                f"班级：{student['class_name']}\n"
                                f"当前总分：{student['total_score']}分\n"
                                f"预警类型：德育分过低\n"
                                f"阈值：{trigger_value}分\n"
                                f"请及时关注并采取干预措施。"
                            )

                            db.execute(
                                """INSERT INTO warning_log
                                (student_id, rule_id, semester_id, warning_level, message)
                                VALUES (?, ?, ?, 'warning', ?)""",
                                (student['student_id'], config['id'], semester_id, message)
                            )

                            logger.warning(f"预警：{student['name']} 德育分过低（{student['total_score']}分）")

            elif trigger_type == 'count_threshold':
                # 违纪次数过多预警
                high_negative_students = db.query_all(
                    """SELECT dr.student_id, s.name, COUNT(*) as negative_count,
                           c.class_name, c.leader_name
                    FROM student_daily_record dr
                    JOIN student s ON dr.student_id = s.student_id
                    JOIN class c ON s.class_id = c.class_id
                    JOIN daily_event_type det ON dr.event_id = det.event_id
                    WHERE dr.semester_id = ?
                    AND det.event_type = 2  -- 消极事件
                    AND dr.is_deleted = 0
                    AND s.status = '在校'
                    GROUP BY dr.student_id
                    HAVING COUNT(*) >= ?""",
                    (semester_id, trigger_value)
                )

                for student in high_negative_students:
                    existing = db.query_one(
                        """SELECT id FROM warning_log
                        WHERE student_id = ? AND semester_id = ?
                        AND rule_id = ? AND DATE(created_at) = ?""",
                        (student['student_id'], semester_id, config['id'], date.today())
                    )

                    if not existing:
                        message = (
                            f"【德育预警】\n"
                            f"学生：{student['name']}（{student['student_id']}）\n"
                            f"班级：{student['class_name']}\n"
                            f"违纪次数：{student['negative_count']}次\n"
                            f"预警类型：违纪次数过多\n"
                            f"阈值：{trigger_value}次\n"
                            f"请及时关注并采取干预措施。"
                        )

                        db.execute(
                            """INSERT INTO warning_log
                            (student_id, rule_id, semester_id, warning_level, message)
                            VALUES (?, ?, ?, 'warning', ?)""",
                            (student['student_id'], config['id'], semester_id, message)
                        )

                        logger.warning(f"预警：{student['name']} 违纪次数过多（{student['negative_count']}次）")


def punishment_expire_reminder_task():
    """
    处分到期提醒任务（每日08:00执行）

    流程：
    1. 查询未来7天内到期且未撤销的处分
    2. 发送提前提醒通知（班级公告）
    3. 查询今日已到期且未撤销的处分
    4. 发送到期提醒通知（班级公告）
    5. 记录提醒日志
    """
    logger.info("执行处分到期提醒任务")

    from .base import get_moral_db
    from models.lesson.homework import Homework

    with get_moral_db() as db:
        today = date.today()
        pre_expire_date = today + timedelta(days=7)  # 提前7天提醒

        # 1. 查询未来7天内到期处分（提前提醒）
        upcoming_expires = db.query_all(
            """SELECT p.id, p.student_id, p.punishment_date, p.expire_date,
                   p.level, p.can_apply_revoke, s.name as student_name,
                   c.class_code, c.class_name, c.leader_name, c.leader_names
            FROM punishment_record p
            JOIN student s ON p.student_id = s.student_id
            JOIN class c ON p.class_id = c.class_id
            WHERE p.is_revoked = 0
            AND p.expire_date IS NOT NULL
            AND p.expire_date > ?
            AND p.expire_date <= ?
            AND NOT EXISTS (
                SELECT 1 FROM punishment_expire_reminder r
                WHERE r.punishment_id = p.id AND r.reminder_type = 'pre_expire'
            )""",
            (today.strftime("%Y-%m-%d"), pre_expire_date.strftime("%Y-%m-%d"))
        )

        for punishment in upcoming_expires:
            days_until = (datetime.strptime(punishment['expire_date'], "%Y-%m-%d").date() - today).days
            student_name = punishment['student_name']
            class_name = punishment['class_name']
            class_code = punishment['class_code']

            # 发送班级公告
            content = (
                f"【处分到期提醒】\n\n"
                f"学生 {student_name} 的处分（{punishment['level']}）将于 {days_until} 天后到期。\n"
                f"处分日期：{punishment['punishment_date']}\n"
                f"到期日期：{punishment['expire_date']}\n\n"
                f"如观察期表现良好，可在到期后申请撤销处分。\n"
                f"— 德育评价系统\n"
                f"{today.strftime('%Y-%m-%d')}"
            )

            with Homework() as hw:
                leader_names_str = punishment.get('leader_names', '')
                leader_name = punishment.get('leader_name', '')
                if leader_names_str:
                    first_leader = leader_names_str.split(',')[0].strip()
                    author = first_leader or "德育系统"
                else:
                    author = leader_name or "德育系统"
                hw.add_announcement(class_code, "处分到期提醒", author, content, None)

            # 记录提醒日志
            db.execute(
                """INSERT INTO punishment_expire_reminder
                (punishment_id, student_id, expire_date, reminder_type, reminder_days,
                 is_sent, sent_at, recipient_type, message)
                VALUES (?, ?, ?, 'pre_expire', ?, 1, datetime('now','localtime'), 'class_teacher', ?)""",
                (punishment['id'], punishment['student_id'], punishment['expire_date'],
                 days_until, f"班级公告：{class_name}")
            )

            logger.info(f"已发送提前提醒：{student_name}（{class_name}），{days_until}天后到期")

        # 2. 查询今日到期处分
        today_expires = db.query_all(
            """SELECT p.id, p.student_id, p.punishment_date, p.expire_date,
                   p.level, p.can_apply_revoke, s.name as student_name,
                   c.class_code, c.class_name, c.leader_name, c.leader_names
            FROM punishment_record p
            JOIN student s ON p.student_id = s.student_id
            JOIN class c ON p.class_id = c.class_id
            WHERE p.is_revoked = 0
            AND p.expire_date IS NOT NULL
            AND p.expire_date = ?
            AND NOT EXISTS (
                SELECT 1 FROM punishment_expire_reminder r
                WHERE r.punishment_id = p.id AND r.reminder_type = 'expired'
            )""",
            (today.strftime("%Y-%m-%d"),)
        )

        for punishment in today_expires:
            student_name = punishment['student_name']
            class_name = punishment['class_name']
            class_code = punishment['class_code']

            content = (
                f"【处分已到期】\n\n"
                f"学生 {student_name} 的处分（{punishment['level']}）今日已到期。\n"
                f"处分日期：{punishment['punishment_date']}\n"
                f"到期日期：{punishment['expire_date']}\n\n"
            )

            if punishment['can_apply_revoke'] == 1:
                content += "观察期表现良好者可申请撤销处分，请在德育系统提交申请。\n"

            content += f"— 德育评价系统\n{today.strftime('%Y-%m-%d')}"

            with Homework() as hw:
                leader_names_str = punishment.get('leader_names', '')
                leader_name = punishment.get('leader_name', '')
                if leader_names_str:
                    first_leader = leader_names_str.split(',')[0].strip()
                    author = first_leader or "德育系统"
                else:
                    author = leader_name or "德育系统"
                hw.add_announcement(class_code, "处分已到期", author, content, None)

            db.execute(
                """INSERT INTO punishment_expire_reminder
                (punishment_id, student_id, expire_date, reminder_type,
                 is_sent, sent_at, recipient_type, message)
                VALUES (?, ?, ?, 'expired', 1, datetime('now','localtime'), 'class_teacher', ?)""",
                (punishment['id'], punishment['student_id'], punishment['expire_date'],
                 f"班级公告：{class_name}")
            )

            logger.info(f"已发送到期提醒：{student_name}（{class_name}）")


def teacher_todo_reminder_task():
    """
    教师待办提醒任务（每分钟执行）

    流程：
    1. 查询需要发送提醒的待办（scheduled_at - remind_before_minutes <= 当前时间）
    2. 检查已发送次数和上次发送时间
    3. 若次数<3且距上次>=2分钟，发送微信提醒
    4. 若次数=3且仍pending，标记为逾期
    5. 记录提醒日志
    """
    logger.info("执行教师待办提醒任务")

    from .base import get_moral_db
    from models.datas_api.teacher_todo import ensure_teacher_todo_schema, ensure_future_occurrences
    from sendqueue import send_text

    MAX_REMINDERS = 3  # 最大提醒次数
    REMINDER_INTERVAL = 2  # 提醒间隔（分钟）
    REMIND_BEFORE = 5  # 提前5分钟开始提醒

    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        ensure_future_occurrences(db)
        now = datetime.now()

        # 查询需要提醒的待办实例（pending 且未逾期）
        remindables = db.query_all(
            """SELECT o.id as occurrence_id, o.todo_series_id, o.scheduled_at, o.occurrence_date,
                   t.title, t.description, t.wechat_notify_enabled, t.remind_before_minutes,
                   t.notify_creator, t.notify_assignees, t.creator_teacher_id, t.creator_name,
                   t.time_of_day
            FROM teacher_todo_occurrence o
            JOIN teacher_todo_series t ON o.todo_series_id = t.id
            WHERE o.status = 'pending'
            AND o.is_overdue = 0
            AND t.is_active = 1
            AND t.wechat_notify_enabled = 1"""
        )

        for todo in remindables:
            scheduled_at = todo['scheduled_at']

            # 固定提前5分钟开始提醒
            try:
                scheduled_dt = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M:%S")
            except:
                scheduled_dt = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M")

            remind_time = scheduled_dt - timedelta(minutes=REMIND_BEFORE)

            # 判断是否应该发送提醒（当前时间 >= 提醒时间）
            if now < remind_time:
                continue  # 还没到提醒时间，跳过

            # 获取需要通知的教师列表
            notify_teacher_ids = []
            if todo['notify_creator'] == 1:
                notify_teacher_ids.append(todo['creator_teacher_id'])
            if todo['notify_assignees'] == 1:
                assignees = db.query_all(
                    """SELECT teacher_id FROM teacher_todo_assignee WHERE todo_series_id = ?""",
                    (todo['todo_series_id'],)
                )
                for a in assignees:
                    if a['teacher_id'] == todo['creator_teacher_id'] and todo['notify_creator'] != 1:
                        continue
                    if a['teacher_id'] not in notify_teacher_ids:
                        notify_teacher_ids.append(a['teacher_id'])

            # 检查教师是否有微信ID
            for teacher_id in notify_teacher_ids:
                # 查询已发送提醒次数和上次发送时间
                reminder_stats = db.query_one(
                    """SELECT COUNT(*) as sent_count,
                              MAX(actual_remind_time) as last_remind_time
                       FROM teacher_todo_reminder_log
                       WHERE occurrence_id = ? AND teacher_id = ? AND is_sent = 1""",
                    (todo['occurrence_id'], teacher_id)
                )
                sent_count = reminder_stats['sent_count'] or 0
                last_remind_time_str = reminder_stats['last_remind_time']

                # 检查是否已发送3次，标记逾期
                if sent_count >= MAX_REMINDERS:
                    db.execute(
                        """UPDATE teacher_todo_occurrence SET is_overdue = 1 WHERE id = ?""",
                        (todo['occurrence_id'],)
                    )
                    logger.info(f"待办 {todo['title']} 已发送3次提醒仍未完成，标记为逾期")
                    continue

                # 检查距离上次提醒是否>=2分钟
                if last_remind_time_str:
                    try:
                        last_remind_dt = datetime.strptime(last_remind_time_str, "%Y-%m-%d %H:%M:%S")
                        if now < last_remind_dt + timedelta(minutes=REMINDER_INTERVAL):
                            continue  # 距上次提醒不足2分钟，跳过
                    except:
                        pass  # 时间解析失败，允许发送

                teacher = db.query_one(
                    """SELECT teacher_id, name, wxid, notice_enabled
                       FROM teacher
                       WHERE (teacher_id = ? OR name = ?) AND is_active = 1""",
                    (teacher_id, teacher_id)
                )

                if not teacher:
                    continue

                # 教师关闭通知时，记录但不计入提醒次数
                if int(teacher.get("notice_enabled") or 0) != 1:
                    logger.debug(f"教师 {teacher_id} 已关闭通知，跳过微信通知")
                    continue

                wxid = teacher.get('wxid')
                if not wxid:
                    logger.debug(f"教师 {teacher_id} 无微信ID，跳过微信通知")
                    continue

                # 构建提醒消息（第N次提醒）
                title = todo['title']
                time_str = todo['time_of_day'] or '08:00'
                date_str = todo['occurrence_date']
                next_sequence = sent_count + 1

                message = (
                    f"【待办提醒】（第{next_sequence}次）\n"
                    f"标题：{title}\n"
                    f"时间：{date_str} {time_str}\n"
                    f"{todo['description'] or ''}\n\n"
                    f"— 数字天龙"
                )

                is_sent = 1
                log_message = message
                try:
                    send_text(message, wxid, producer="teacher_todo")
                except Exception as exc:
                    is_sent = 0
                    log_message = f"发送失败: {exc}"
                    logger.exception("教师待办微信提醒发送失败: teacher_id=%s", teacher_id)

                # 记录提醒日志（使用 reminder_sequence）
                db.execute(
                    """INSERT INTO teacher_todo_reminder_log
                    (occurrence_id, receiver_teacher_id, planned_remind_at,
                     todo_series_id, teacher_id, reminder_type,
                     remind_before_minutes, scheduled_remind_time, actual_remind_time,
                     message, is_sent, reminder_sequence)
                    VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?, ?, ?, ?, ?)""",
                    (
                        todo['occurrence_id'],
                        teacher_id,
                        remind_time.strftime("%Y-%m-%d %H:%M:%S"),
                        todo['todo_series_id'],
                        teacher_id,
                        REMIND_BEFORE,
                        remind_time.strftime("%Y-%m-%d %H:%M:%S"),
                        now.strftime("%Y-%m-%d %H:%M:%S"),
                        log_message,
                        is_sent,
                        next_sequence,
                    )
                )

                logger.info(f"已发送待办提醒（第{next_sequence}次）：{title} → 教师 {teacher_id}")

                # 如果是第3次提醒且发送成功，标记逾期
                if is_sent == 1 and next_sequence >= MAX_REMINDERS:
                    db.execute(
                        """UPDATE teacher_todo_occurrence SET is_overdue = 1 WHERE id = ?""",
                        (todo['occurrence_id'],)
                    )
                    logger.info(f"待办 {title} 已发送{MAX_REMINDERS}次提醒，标记为逾期")


def semester_evaluation_task():
    """
    学期末德育评价计算任务

    执行时机：学期末（需手动触发或配置具体日期）
    """
    logger.info("执行学期末评价计算任务")

    from .base import get_moral_db
    from .evaluation import calculate_all_evaluations

    with get_moral_db() as db:
        current_semester = db.query_one(
            "SELECT * FROM semester WHERE status = 1"
        )

        if not current_semester:
            logger.warning("当前学期未配置")
            return

        semester_id = current_semester['semester_id']

        # 计算所有在校学生的德育评价
        result = calculate_all_evaluations(db, semester_id)

        logger.info(f"学期末评价计算完成：成功 {result['success']}, 失败 {result['failed']}")


def task_carryover_year_end_task():
    """
    学年末任务结转任务

    执行时机：学年末（需手动触发或配置具体日期）
    """
    logger.info("执行学年末任务结转任务")

    from .base import get_moral_db
    from .carryover import execute_task_carryover, get_next_school_year

    with get_moral_db() as db:
        # 获取当前学年
        current_year = db.query_one(
            "SELECT * FROM school_year WHERE is_current = 1"
        )

        if not current_year:
            logger.warning("当前学年未配置")
            return

        # 获取下一个学年
        next_year = get_next_school_year(db, current_year['year_id'])

        if not next_year:
            logger.warning("未找到下一学年配置，无法执行结转")
            return

        # 执行结转
        result = execute_task_carryover(db, current_year['year_id'], next_year['year_id'])

        logger.info(
            f"学年末任务结转完成：总数 {result['total_unfinished']}, "
            f"成功 {result['carryover_success']}, "
            f"作废 {result['carryover_skipped']}"
        )


def database_backup_task():
    """
    数据库自动备份任务

    流程：
    1. 检查备份配置是否启用
    2. 执行备份（使用 zipfile）
    3. 清理旧备份
    4. 记录备份历史
    """
    logger.info("执行数据库自动备份任务")

    from .base import get_moral_db

    with get_moral_db() as db:
        # 获取定时备份配置
        config = db.query_one(
            "SELECT config_value FROM moral_config WHERE config_key = 'backup_schedule'"
        )

        if config:
            try:
                schedule_config = json.loads(config['config_value'])
                if not schedule_config.get('enabled'):
                    logger.info("定时备份已禁用，跳过")
                    return
            except:
                pass

        # 执行备份
        from .database_backup import execute_backup_internal
        result = execute_backup_internal(
            db,
            backup_type='scheduled',
            operator='system'
        )

        if result['success']:
            logger.info(f"自动备份完成：{result['backup_name']} ({result['file_size']} 字节)")
        else:
            logger.error(f"自动备份失败：{result['error']}")


def update_backup_job(config: dict):
    """
    根据配置动态更新备份任务

    Args:
        config: 定时备份配置 {"enabled": bool, "day_of_week": str, "hour": int, "minute": int}
    """
    global scheduler

    if scheduler is None or not scheduler.running:
        logger.warning("调度器未运行，无法更新备份任务")
        return

    job_id = 'database_backup'

    # 先移除现有任务
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)

    # 如果启用，重新添加
    if config.get('enabled'):
        trigger = CronTrigger(
            day_of_week=config.get('day_of_week', 'sun'),
            hour=config.get('hour', 3),
            minute=config.get('minute', 0)
        )
        scheduler.add_job(
            database_backup_task,
            trigger,
            id=job_id,
            name='数据库自动备份任务',
            replace_existing=True
        )
        logger.info(f"已更新定时备份任务：{config.get('day_of_week')} {config.get('hour')}:{config.get('minute')}")
    else:
        logger.info("定时备份已禁用，任务已移除")


# =============================================================================
# 调度器启动与停止
# =============================================================================

def start_scheduler():
    """启动定时任务调度器"""
    global scheduler

    if scheduler is not None and scheduler.running:
        logger.warning("调度器已在运行")
        return

    scheduler = BackgroundScheduler()

    # 添加定时任务
    # 生日提醒（每日05:21）
    scheduler.add_job(
        birthday_reminder_task,
        CronTrigger(hour=5, minute=21),
        id='birthday_reminder',
        name='生日提醒任务',
        replace_existing=True
    )

    # 生日祝福（每日05:51）
    # scheduler.add_job(
    #     birthday_blessing_task,
    #     CronTrigger(hour=5, minute=51),
    #     id='birthday_blessing',
    #     name='生日祝福任务',
    #     replace_existing=True
    # )

    # 画像更新检查（每周一09:00）
    scheduler.add_job(
        profile_update_check_task,
        CronTrigger(day_of_week='mon', hour=9, minute=0),
        id='profile_update_check',
        name='画像更新检查任务',
        replace_existing=True
    )

    # 预警检查（每日10:00）
    scheduler.add_job(
        warning_check_task,
        CronTrigger(hour=10, minute=0),
        id='warning_check',
        name='预警检查任务',
        replace_existing=True
    )

    # 处分到期提醒（每日08:00）
    scheduler.add_job(
        punishment_expire_reminder_task,
        CronTrigger(hour=8, minute=0),
        id='punishment_expire_reminder',
        name='处分到期提醒任务',
        replace_existing=True
    )

    # 教师待办提醒（每分钟）
    scheduler.add_job(
        teacher_todo_reminder_task,
        CronTrigger(minute='*'),
        id='teacher_todo_reminder',
        name='教师待办提醒任务',
        replace_existing=True
    )

    # 数据库自动备份（默认周日凌晨3点）
    scheduler.add_job(
        database_backup_task,
        CronTrigger(day_of_week='sun', hour=3, minute=0),
        id='database_backup',
        name='数据库自动备份任务',
        replace_existing=True
    )

    # 学期末评价（学期末）- 手动触发或配置具体日期
    # 学年末结转（学年末）- 手动触发或配置具体日期

    scheduler.start()
    logger.info("定时任务调度器已启动")

    # 打印任务列表
    jobs = scheduler.get_jobs()
    for job in jobs:
        logger.info(f"任务: {job.name}, 触发器: {job.trigger}")


def stop_scheduler():
    """停止定时任务调度器"""
    global scheduler

    if scheduler is not None and scheduler.running:
        scheduler.shutdown()
        logger.info("定时任务调度器已停止")


def get_scheduler_status():
    """获取调度器状态"""
    global scheduler

    if scheduler is None:
        return {"running": False, "jobs": []}

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run": str(job.next_run_time) if job.next_run_time else None
        })

    return {
        "running": scheduler.running,
        "jobs": jobs
    }


# =============================================================================
# API路由（调度器管理）
# =============================================================================

from fastapi import APIRouter, Depends
from .api_permission import require_configured_api_permission
from .base import require_permission
from models.datas_api.auth import User

scheduler_router = APIRouter(prefix="/scheduler", tags=["定时任务"])


@scheduler_router.get("/status", summary="获取调度器状态")
async def api_get_scheduler_status(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """获取定时任务调度器状态"""
    status = get_scheduler_status()
    return {"success": True, "data": status}


@scheduler_router.post("/start", summary="启动调度器")
async def api_start_scheduler(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """启动定时任务调度器"""
    try:
        start_scheduler()
        return {"success": True, "message": "调度器已启动"}
    except Exception as e:
        return {"success": False, "message": f"启动失败：{str(e)}"}


@scheduler_router.post("/stop", summary="停止调度器")
async def api_stop_scheduler(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """停止定时任务调度器"""
    try:
        stop_scheduler()
        return {"success": True, "message": "调度器已停止"}
    except Exception as e:
        return {"success": False, "message": f"停止失败：{str(e)}"}


@scheduler_router.post("/trigger/birthday-reminder", summary="手动触发生日提醒")
async def api_trigger_birthday_reminder(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """手动触发生日提醒任务"""
    try:
        birthday_reminder_task()
        return {"success": True, "message": "生日提醒任务已执行"}
    except Exception as e:
        return {"success": False, "message": f"执行失败：{str(e)}"}


@scheduler_router.post("/trigger/warning-check", summary="手动触发预警检查")
async def api_trigger_warning_check(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """手动触发预警检查任务"""
    try:
        warning_check_task()
        return {"success": True, "message": "预警检查任务已执行"}
    except Exception as e:
        return {"success": False, "message": f"执行失败：{str(e)}"}


@scheduler_router.post("/trigger/punishment-expire-reminder", summary="手动触发处分到期提醒")
async def api_trigger_punishment_expire_reminder(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """手动触发处分到期提醒任务"""
    try:
        punishment_expire_reminder_task()
        return {"success": True, "message": "处分到期提醒任务已执行"}
    except Exception as e:
        return {"success": False, "message": f"执行失败：{str(e)}"}


@scheduler_router.post("/trigger/semester-evaluation", summary="手动触发学期评价计算")
async def api_trigger_semester_evaluation(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """手动触发学期末德育评价计算"""
    try:
        semester_evaluation_task()
        return {"success": True, "message": "学期评价计算任务已执行"}
    except Exception as e:
        return {"success": False, "message": f"执行失败：{str(e)}"}


@scheduler_router.post("/trigger/task-carryover", summary="手动触发任务结转")
async def api_trigger_task_carryover(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """手动触发学年末任务结转"""
    try:
        task_carryover_year_end_task()
        return {"success": True, "message": "任务结转已执行"}
    except Exception as e:
        return {"success": False, "message": f"执行失败：{str(e)}"}


@scheduler_router.post("/trigger/teacher-todo-reminder", summary="手动触发教师待办提醒")
async def api_trigger_teacher_todo_reminder(
    user: User = Depends(require_configured_api_permission("/api/moral/scheduler", "GET", allow_missing=False))
):
    """手动触发教师待办提醒任务"""
    try:
        teacher_todo_reminder_task()
        return {"success": True, "message": "教师待办提醒任务已执行"}
    except Exception as e:
        return {"success": False, "message": f"执行失败：{str(e)}"}
