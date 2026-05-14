# -*- coding: utf-8 -*-
"""
处分到期提醒查询 API

提供处分到期提醒的查询功能
"""

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    get_record_data_scope,
    append_record_scope_condition,
)
from .api_permission import require_configured_api_permission
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/punishments", tags=["处分到期提醒"])

# API 路径常量
API_EXPIRING_LIST = "/api/moral/punishments/expiring"


# =============================================================================
# API 路由
# =============================================================================

@router.get("/expiring", summary="获取即将到期处分列表")
async def get_expiring_punishments(
    days: int = Query(7, ge=1, le=90, description="查询未来N天内到期"),
    class_id: Optional[int] = Query(None, description="班级ID"),
    grade_id: Optional[int] = Query(None, description="年级ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_configured_api_permission(API_EXPIRING_LIST, "GET", allow_missing=False))
):
    """
    获取即将到期处分列表（管理员/班主任）

    权限：
    - 管理员可查看全部
    - 班主任仅可查看本班
    """
    with get_moral_db() as db:
        today = date.today()
        expire_end_date = today + timedelta(days=days)
        today_str = today.strftime("%Y-%m-%d")
        expire_end_str = expire_end_date.strftime("%Y-%m-%d")

        conditions = [
            "p.is_revoked = 0",
            "p.expire_date IS NOT NULL",
            "p.expire_date >= ?",
            "p.expire_date <= ?"
        ]
        params = [today_str, expire_end_str]

        if class_id:
            conditions.append("p.class_id = ?")
            params.append(class_id)

        if grade_id:
            conditions.append("p.grade_id = ?")
            params.append(grade_id)

        # 数据范围控制（复用处分记录的范围控制）
        view_scope = get_record_data_scope(
            db,
            user,
            API_EXPIRING_LIST,
            all_permissions=['punishment_manage', 'report_view_all'],
            own_class_permissions=['moral_record_own_class', 'report_view_own_class'],
            own_permissions=['moral_record_input', 'moral_record_view_own'],
        )
        append_record_scope_condition(
            conditions,
            params,
            view_scope,
            table_alias="p",
            username=user.username,
        )

        where_clause = " AND ".join(conditions)

        # 查询总数
        total = db.query_value(
            f"""SELECT COUNT(*) FROM punishment_record p
                WHERE {where_clause}""",
            params
        )

        # 分页查询
        offset = (page - 1) * page_size
        punishments = db.query_all(
            f"""SELECT p.id, p.student_id, p.punishment_date, p.level, p.reason,
                       p.score_deduct, p.expire_date, p.period_days, p.can_apply_revoke,
                       s.name as student_name, c.class_name, c.class_id, g.grade_name,
                       CAST(julianday(p.expire_date) - julianday(?) AS INTEGER) as days_until_expire
                FROM punishment_record p
                JOIN student s ON p.student_id = s.student_id
                JOIN class c ON p.class_id = c.class_id
                JOIN grade g ON p.grade_id = g.grade_id
                WHERE {where_clause}
                ORDER BY p.expire_date ASC
                LIMIT ? OFFSET ?""",
            params + [today_str, page_size, offset]
        )

        # 按到期状态分类
        expiring_soon = []  # 即将到期（未来N天内）
        already_expired = []  # 已到期但未撤销

        for p in punishments:
            days_until = p.get("days_until_expire", 0)
            if days_until <= 0:
                already_expired.append(p)
            else:
                expiring_soon.append(p)

        return {
            "success": True,
            "data": {
                "expiring_soon": expiring_soon,
                "already_expired": already_expired,
                "all": punishments
            },
            "summary": {
                "total": total or 0,
                "expiring_soon_count": len(expiring_soon),
                "already_expired_count": len(already_expired),
                "query_days": days
            },
            "page": page,
            "page_size": page_size
        }


# =============================================================================
# 辅助函数
# =============================================================================

def get_expired_punishments_for_reminder(db, days_threshold: int = 7) -> list:
    """
    获取即将到期处分（用于定时任务）

    Args:
        db: 数据库连接
        days_threshold: 查询未来N天内到期

    Returns:
        处分记录列表
    """
    today = date.today()
    expire_end_date = today + timedelta(days=days_threshold)

    return db.query_all(
        """SELECT p.id, p.student_id, p.punishment_date, p.level, p.expire_date,
                  p.period_days, s.name as student_name, c.class_code, c.class_name,
                  c.leader_name, c.leader_names, c.class_id
           FROM punishment_record p
           JOIN student s ON p.student_id = s.student_id
           JOIN class c ON p.class_id = c.class_id
           WHERE p.is_revoked = 0
           AND p.expire_date IS NOT NULL
           AND p.expire_date BETWEEN ? AND ?
           ORDER BY p.expire_date ASC""",
        (today.strftime("%Y-%m-%d"), expire_end_date.strftime("%Y-%m-%d"))
    )


def get_today_expired_punishments(db) -> list:
    """
    获取今日已到期处分（用于定时任务）

    Args:
        db: 数据库连接

    Returns:
        处分记录列表
    """
    today = date.today().strftime("%Y-%m-%d")

    return db.query_all(
        """SELECT p.id, p.student_id, p.punishment_date, p.level, p.expire_date,
                  p.can_apply_revoke, s.name as student_name, c.class_code, c.class_name,
                  c.leader_name, c.leader_names, c.class_id
           FROM punishment_record p
           JOIN student s ON p.student_id = s.student_id
           JOIN class c ON p.class_id = c.class_id
           WHERE p.is_revoked = 0
           AND p.expire_date = ?""",
        (today,)
    )