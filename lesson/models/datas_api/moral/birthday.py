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
    get_record_data_scope,
    append_record_scope_condition,
    log_operation,
)
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/birthdays", tags=["生日查看"])

API_BIRTHDAY_UPCOMING = "/api/moral/birthdays/upcoming"
API_BIRTHDAY_TODAY = "/api/moral/birthdays/today"


def _birthday_scope(db, user: User, api_path: str) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['birthday_reminder'],
        own_class_permissions=['birthday_reminder'],
        own_permissions=[],
    )


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

        view_scope = _birthday_scope(db, user, API_BIRTHDAY_UPCOMING)
        append_record_scope_condition(
            conditions,
            params,
            view_scope,
            table_alias="s",
            username=user.username,
        )
        if class_id:
            conditions.append("s.class_id = ?")
            params.append(class_id)

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT s.student_id, s.name, s.birthday, c.class_name, c.leader_name, c.leader_names,
                   strftime('%m-%d', s.birthday) as birthday_md
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE {where_clause}
            AND (
                strftime('%m-%d', s.birthday) BETWEEN strftime('%m-%d', ?)
                AND strftime('%m-%d', ?)
                OR strftime('%m-%d', s.birthday) BETWEEN '01-01'
                AND strftime('%m-%d', ?)
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

            # 支持多人班主任：优先使用 leader_names，否则回退 leader_name
            leader_names_str = student.get('leader_names', '')
            leader_name = student.get('leader_name', '')
            display_leader = leader_names_str if leader_names_str else leader_name

            result.append({
                'student_id': student['student_id'],
                'name': student['name'],
                'birthday': student['birthday'],
                'class_name': student['class_name'],
                'leader_name': display_leader,
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

        view_scope = _birthday_scope(db, user, API_BIRTHDAY_TODAY)
        append_record_scope_condition(
            conditions,
            params,
            view_scope,
            table_alias="s",
            username=user.username,
        )

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT s.student_id, s.name, s.birthday, c.class_name, c.leader_name, c.leader_names
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE {where_clause}
            AND CAST(strftime('%m', s.birthday) AS INTEGER) = ?
            AND CAST(strftime('%d', s.birthday) AS INTEGER) = ?
        """
        params.extend([today.month, today.day])
        students = db.query_all(query, tuple(params))

        # 支持多人班主任显示
        for student in students:
            leader_names_str = student.get('leader_names', '')
            leader_name = student.get('leader_name', '')
            student['leader_name'] = leader_names_str if leader_names_str else leader_name

        return {"success": True, "data": students}
