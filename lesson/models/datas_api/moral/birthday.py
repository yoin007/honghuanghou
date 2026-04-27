# -*- coding: utf-8 -*-
"""
生日查看与提醒 API

提供查看即将过生日学生名单、发送祝福、配置管理等功能
"""

import logging
import json
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    get_teacher_class_id,
    log_operation,
    require_permission,
)
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/birthdays", tags=["生日查看"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class BlessingSend(BaseModel):
    """发送祝福请求"""
    student_id: str = Field(..., description="学号")
    message: Optional[str] = Field(None, description="祝福内容（可选，使用模板则不需要）")


class BirthdayConfigUpdate(BaseModel):
    """更新生日提醒配置"""
    reminder_days_before: Optional[int] = Field(None, description="提前提醒天数")
    reminder_time: Optional[dict] = Field(None, description="提醒时间")
    blessing_enabled: Optional[bool] = Field(None, description="是否启用祝福")
    message_template: Optional[dict] = Field(None, description="祝福模板")


# =============================================================================
# API 路由 - 基础查询
# =============================================================================


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
    - teacher/cleader: 查看本班
    - xuefa/jiaowu/admin: 查看所有，支持班级筛选
    """
    with get_moral_db() as db:
        today = date.today()
        end_date = today + timedelta(days=days)

        conditions = ["s.birthday IS NOT NULL", "s.status = '在校'"]
        params = []

        # 权限过滤
        my_class_id = get_teacher_class_id(user, db)
        has_full_permission = check_moral_permission(user, 'birthday_reminder')

        if not has_full_permission:
            if my_class_id:
                conditions.append("s.class_id = %s")
                params.append(my_class_id)
            else:
                return {"success": True, "data": []}
        elif class_id:
            conditions.append("s.class_id = %s")
            params.append(class_id)

        where_clause = " AND ".join(conditions)

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

        result = []
        for student in students:
            birthday_md = student['birthday_md']
            this_year_birthday = date(today.year, int(birthday_md.split('-')[0]), int(birthday_md.split('-')[1]))

            if this_year_birthday < today:
                next_birthday = date(today.year + 1, int(birthday_md.split('-')[0]), int(birthday_md.split('-')[1]))
            else:
                next_birthday = this_year_birthday

            days_until = (next_birthday - today).days

            result.append({
                'student_id': student['student_id'],
                'name': student['name'],
                'birthday': student['birthday'],
                'class_name': student['class_name'],
                'leader_name': student['leader_name'],
                'next_birthday': str(next_birthday),
                'days_until': days_until
            })

        result.sort(key=lambda x: x['days_until'])

        return {"success": True, "data": result}


@router.get("/today", summary="获取今日过生日的学生")
async def get_today_birthdays(
    user: User = Depends(get_current_user)
):
    """
    获取今日过生日的学生

    权限说明：
    - teacher/cleader: 只能查看本班学生
    - jiaowu/xuefa/admin: 可查看所有
    """
    with get_moral_db() as db:
        today = date.today()

        conditions = ["s.birthday IS NOT NULL", "s.status = '在校'"]
        params = []

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