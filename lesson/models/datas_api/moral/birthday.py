# -*- coding: utf-8 -*-
"""
生日提醒 API

提供生日提醒的管理功能
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    require_permission,
    get_teacher_class_id,
)
from models.datas_api.auth import User, get_current_user

# 尝试导入微信发送函数
try:
    from sendqueue import send_text
    WX_SEND_AVAILABLE = True
except ImportError:
    WX_SEND_AVAILABLE = False
    send_text = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/birthdays", tags=["生日提醒"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class BirthdayReminderCreate(BaseModel):
    """创建生日提醒"""
    student_id: str = Field(..., description="学号")
    student_name: Optional[str] = Field(None, description="学生姓名（可选）")
    reminder_date: date = Field(..., description="提醒日期")
    message: Optional[str] = Field(None, description="祝福内容")
    recipient_type: Optional[str] = Field("student", description="接收人类型")


# =============================================================================
# API 路由
# =============================================================================

@router.get("/upcoming", summary="获取即将到来的生日")
async def get_upcoming_birthdays(
    days: int = Query(7, ge=1, le=30, description="提前天数"),
    class_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    """
    获取即将到来的生日列表

    权限说明：
    - teacher: 可查看
    - cleader: 查看本班
    - xuefa/jiaowu/admin: 查看所有
    """
    with get_moral_db() as db:
        today = date.today()
        end_date = today + timedelta(days=days)

        # 获取本月和下月过生日的学生
        conditions = ["s.birthday IS NOT NULL", "s.status = '在校'"]
        params = []

        # 权限过滤：
        # - 有 birthday_reminder 权限（admin/jiaowu/xuefa）：可查看全部，支持班级筛选
        # - 无该权限（teacher/cleader）：只能查看本班，强制过滤
        my_class_id = get_teacher_class_id(user, db)
        has_full_permission = check_moral_permission(user, 'birthday_reminder')

        if not has_full_permission:
            # teacher/cleader 只能看本班
            if my_class_id:
                conditions.append("s.class_id = %s")
                params.append(my_class_id)
            else:
                return {"success": True, "data": []}
        elif class_id:
            # admin/jiaowu/xuefa 支持班级筛选
            conditions.append("s.class_id = %s")
            params.append(class_id)

        where_clause = " AND ".join(conditions)

        # 查询即将过生日的学生
        query = f"""
            SELECT s.student_id, s.name, s.birthday, c.class_name, c.leader_name,
                   strftime('%m-%d', s.birthday) as birthday_md
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE {where_clause}
            AND (
                strftime('%m-%d', s.birthday) BETWEEN strftime('%m-%d', %s)
                AND strftime('%m-%d', %s)
                OR strftime('%m-%d', s.birthday) BETWEEN '01-01'
                AND strftime('%m-%d', %s)
            )
            ORDER BY strftime('%m-%d', s.birthday)
        """
        params.extend([today, end_date, end_date])

        students = db.query_all(query, tuple(params))

        # 处理结果，计算实际年份
        result = []
        for student in students:
            birthday_md = student['birthday_md']
            # 构建今年的生日日期
            this_year_birthday = date(today.year, int(birthday_md.split('-')[0]), int(birthday_md.split('-')[1]))

            # 如果已过，计算明年的
            if this_year_birthday < today:
                next_birthday = date(today.year + 1, int(birthday_md.split('-')[0]), int(birthday_md.split('-')[1]))
            else:
                next_birthday = this_year_birthday

            days_until = (next_birthday - today).days

            result.append({
                **student,
                'next_birthday': next_birthday,
                'days_until': days_until
            })

        # 按距离生日天数排序
        result.sort(key=lambda x: x['days_until'])

        return {"success": True, "data": result}


@router.get("/today", summary="获取今日过生日的学生")
async def get_today_birthdays(
    user: User = Depends(get_current_user)
):
    """
    获取今日过生日的学生

    权限说明：
    - cleader: 只能查看本班学生
    - jiaowu/xuefa/admin: 可查看所有
    """
    with get_moral_db() as db:
        today = date.today()

        conditions = ["s.birthday IS NOT NULL", "s.status = '在校'"]
        params = []

        # 权限过滤：无 birthday_reminder 权限只能看本班
        my_class_id = get_teacher_class_id(user, db)
        if not check_moral_permission(user, 'birthday_reminder'):
            if my_class_id:
                conditions.append("s.class_id = %s")
                params.append(my_class_id)
            else:
                return {"success": True, "data": []}

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT s.student_id, s.name, s.birthday, c.class_name, c.leader_name
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE {where_clause}
            AND CAST(strftime('%m', s.birthday) AS INTEGER) = %s
            AND CAST(strftime('%d', s.birthday) AS INTEGER) = %s
        """
        params.extend([today.month, today.day])
        students = db.query_all(query, tuple(params))

        return {"success": True, "data": students}


@router.get("/reminders", summary="获取生日提醒列表")
async def get_birthday_reminders(
    student_id: Optional[str] = Query(None),
    is_sent: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """
    获取生日提醒列表

    权限说明：
    - cleader: 只能查看本班学生的提醒
    - jiaowu/xuefa/admin: 可查看所有
    """
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if student_id:
            conditions.append("br.student_id = %s")
            params.append(student_id)

        if is_sent is not None:
            conditions.append("br.is_sent = %s")
            params.append(is_sent)

        # 班主任权限过滤：强制只能查看本班
        my_class_id = get_teacher_class_id(user, db)
        if user.role == 'cleader' and not check_moral_permission(user, 'birthday_reminder'):
            if my_class_id:
                conditions.append("s.class_id = %s")
                params.append(my_class_id)
            else:
                return {"success": True, "data": {"items": [], "total": 0, "page": page, "page_size": page_size}}

        where_clause = " AND ".join(conditions)

        # count_query 需要同样的 JOIN 才能按班级过滤
        count_query = f"""
            SELECT COUNT(*) FROM birthday_reminder br
            JOIN student s ON br.student_id = s.student_id
            WHERE {where_clause}
        """
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT br.*, s.name as student_name, c.class_name
            FROM birthday_reminder br
            JOIN student s ON br.student_id = s.student_id
            JOIN class c ON s.class_id = c.class_id
            WHERE {where_clause}
            ORDER BY br.reminder_date DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        reminders = db.query_all(data_query, tuple(params))

        return {
            "success": True,
            "data": {
                "items": reminders,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


@router.post("/reminders", summary="创建生日提醒")
async def create_birthday_reminder(
    reminder: BirthdayReminderCreate,
    request: Request,
    user: User = Depends(require_permission('birthday_reminder'))
):
    """创建生日提醒"""
    with get_moral_db() as db:
        # 检查学生是否存在
        student = db.query_one(
            "SELECT * FROM student WHERE student_id = %s",
            (reminder.student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        db.execute(
            """INSERT INTO birthday_reminder
            (student_id, reminder_date, reminder_type, message, recipient_type)
            VALUES (%s, %s, %s, %s, %s)""",
            (reminder.student_id, reminder.reminder_date, 'birthday',
             reminder.message, reminder.recipient_type)
        )

        reminder_id = db.lastrowid()

        return {"success": True, "message": "提醒创建成功", "data": {"id": reminder_id}}


@router.post("/reminders/{reminder_id}/send", summary="发送生日提醒")
async def send_birthday_reminder(
    reminder_id: int,
    request: Request,
    user: User = Depends(require_permission('birthday_reminder'))
):
    """发送生日提醒"""
    with get_moral_db() as db:
        reminder = db.query_one(
            """SELECT br.*, s.name as student_name, s.class_id
            FROM birthday_reminder br
            JOIN student s ON br.student_id = s.student_id
            WHERE br.id = %s""",
            (reminder_id,)
        )
        if not reminder:
            raise HTTPException(404, "提醒不存在")

        if reminder['is_sent'] == 1:
            raise HTTPException(400, "该提醒已发送")

        # 构建提醒消息
        student_name = reminder['student_name'] or '同学'
        reminder_date = reminder['reminder_date']
        custom_message = reminder['message']

        message = custom_message or f"🎂 生日提醒：{student_name}将于{reminder_date}过生日，请提前准备祝福！"

        # 查找班主任 wxid 并发送微信通知
        class_id = reminder['class_id']
        wxid_sent = False

        if class_id and WX_SEND_AVAILABLE and send_text:
            class_info = db.query_one(
                "SELECT leader_name, leader_wxid FROM class WHERE class_id = %s",
                (class_id,)
            )

            if class_info:
                # 尝试多种方式获取班主任 wxid
                leader_wxid = class_info['leader_wxid']

                # 方式1：直接使用 class.leader_wxid
                if leader_wxid:
                    try:
                        send_text(message, leader_wxid, producer="birthday_reminder")
                        wxid_sent = True
                        logger.info(f"生日提醒已发送给班主任 {class_info['leader_name']}: {leader_wxid}")
                    except Exception as e:
                        logger.error(f"发送微信消息失败: {e}")

                # 方式2：通过 contacts 表查找（如果 class.leader_wxid 为空）
                if not wxid_sent and class_info['leader_name']:
                    try:
                        import sqlite3
                        import os
                        # contacts 表在 databases/wechat.db 或 databases/member.db
                        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "databases")
                        for db_file in ['wechat.db', 'member.db']:
                            db_path = os.path.join(db_dir, db_file)
                            if os.path.exists(db_path):
                                conn = sqlite3.connect(db_path)
                                conn.row_factory = sqlite3.Row
                                cursor = conn.cursor()
                                cursor.execute("SELECT wxid FROM contacts WHERE name = ? LIMIT 1", (class_info['leader_name'],))
                                row = cursor.fetchone()
                                conn.close()
                                if row and row['wxid']:
                                    send_text(message, row['wxid'], producer="birthday_reminder")
                                    wxid_sent = True
                                    logger.info(f"生日提醒已通过contacts发送给班主任 {class_info['leader_name']}")
                                    break
                    except Exception as e:
                        logger.warning(f"查找contacts表失败: {e}")

        # 更新发送状态
        db.execute(
            """UPDATE birthday_reminder SET
            is_sent = 1, sent_at = datetime('now', 'localtime')
            WHERE id = %s""",
            (reminder_id,)
        )

        result_msg = "提醒已发送"
        if wxid_sent:
            result_msg += "（微信通知已发送给班主任）"
        elif not WX_SEND_AVAILABLE:
            result_msg += "（微信发送模块未加载）"
        elif not class_id:
            result_msg += "（学生无班级信息）"

        return {"success": True, "message": result_msg, "data": {"wxid_sent": wxid_sent}}


@router.get("/config", summary="获取生日提醒配置")
async def get_birthday_config(user: User = Depends(get_current_user)):
    """获取生日提醒配置"""
    with get_moral_db() as db:
        configs = db.query_all("SELECT * FROM birthday_reminder_config")

        config_dict = {}
        for config in configs:
            config_dict[config['config_key']] = config['config_value']

        return {"success": True, "data": config_dict}


@router.post("/generate", summary="生成本月生日提醒")
async def generate_monthly_reminders(
    request: Request,
    user: User = Depends(require_permission('birthday_reminder'))
):
    """生成本月生日提醒"""
    with get_moral_db() as db:
        today = date.today()
        month_start = date(today.year, today.month, 1)

        # 如果是12月，下个月是明年1月
        if today.month == 12:
            month_end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(today.year, today.month + 1, 1) - timedelta(days=1)

        # 获取本月过生日的学生
        students = db.query_all(
            """SELECT s.student_id, s.name, s.birthday
            FROM student s
            WHERE s.birthday IS NOT NULL
            AND s.status = '在校'
            AND CAST(strftime('%m', s.birthday) AS INTEGER) = %s""",
            (today.month,)
        )

        created_count = 0
        for student in students:
            # 检查是否已存在提醒
            existing = db.query_one(
                """SELECT id FROM birthday_reminder
                WHERE student_id = %s AND reminder_type = 'birthday'
                AND CAST(strftime('%Y', reminder_date) AS INTEGER) = %s""",
                (student['student_id'], today.year)
            )

            if not existing:
                # 创建提醒
                birthday = student['birthday']
                reminder_date = date(today.year, birthday.month, birthday.day)

                db.execute(
                    """INSERT INTO birthday_reminder
                    (student_id, reminder_date, reminder_type, recipient_type)
                    VALUES (%s, %s, 'birthday', 'student')""",
                    (student['student_id'], reminder_date)
                )
                created_count += 1

        return {
            "success": True,
            "message": f"成功创建 {created_count} 个生日提醒",
            "data": {"created_count": created_count}
        }