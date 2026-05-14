# -*- coding: utf-8 -*-
"""
教师待办 API

提供教师个人及协作型待办事项的管理功能
"""

import logging
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from calendar import monthrange

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .moral.base import get_moral_db
from .moral.api_permission import require_configured_api_permission
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teacher/todos", tags=["教师待办"])

# API 路径常量
API_TODO_LIST = "/api/teacher/todos"
API_TODO_CREATE = "/api/teacher/todos/create"
API_TODO_UPDATE = "/api/teacher/todos/{series_id}"
API_TODO_DELETE = "/api/teacher/todos/{series_id}"
API_OCCURRENCE_COMPLETE = "/api/teacher/todos/occurrences/{occurrence_id}/complete"
API_OCCURRENCE_REOPEN = "/api/teacher/todos/occurrences/{occurrence_id}/reopen"
API_TODO_UPCOMING = "/api/teacher/todos/upcoming"


# =============================================================================
# Pydantic 模型
# =============================================================================

class RecurrenceRule(BaseModel):
    """周期规则"""
    unit: str = Field(..., description="周期单位: weekly/monthly/yearly")
    weekday: Optional[int] = Field(None, ge=0, le=6, description="星期几 (0=周一, 6=周日)")
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="每月几号")
    month: Optional[int] = Field(None, ge=1, le=12, description="每年几月")
    day: Optional[int] = Field(None, ge=1, le=31, description="每年几日")


class TodoCreate(BaseModel):
    """创建待办"""
    title: str = Field(..., min_length=1, max_length=100, description="标题")
    description: Optional[str] = Field(None, max_length=500, description="描述")
    todo_type: str = Field(..., description="类型: one_off/weekly/monthly/yearly")
    start_date: str = Field(..., description="生效开始日期")
    end_date: Optional[str] = Field(None, description="生效结束日期")
    recurrence_rule: Optional[RecurrenceRule] = Field(None, description="周期规则")
    assignee_teacher_ids: Optional[List[str]] = Field(None, description="关联教师ID列表")


class TodoUpdate(BaseModel):
    """更新待办"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    todo_type: Optional[str] = Field(None)
    start_date: Optional[str] = Field(None)
    end_date: Optional[str] = Field(None)
    recurrence_rule: Optional[RecurrenceRule] = Field(None)
    assignee_teacher_ids: Optional[List[str]] = Field(None)
    is_active: Optional[int] = Field(None, ge=0, le=1)


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="查询待办列表")
async def get_todos(
    view: str = Query("week", description="视图: week/month/year"),
    anchor_date: Optional[str] = Query(None, description="当前周期锚点日期"),
    status: str = Query("all", description="状态筛选: all/pending/completed"),
    scope: str = Query("all_visible", description="范围: all_visible/created/assigned"),
    user: User = Depends(require_configured_api_permission(API_TODO_LIST, "GET", allow_missing=False))
):
    """
    查询教师可见待办列表

    权限：教师可查看自己创建和关联给自己的待办
    """
    with get_moral_db() as db:
        # 解析锚点日期
        anchor = datetime.strptime(anchor_date, "%Y-%m-%d") if anchor_date else datetime.now()

        # 计算周期范围
        range_start, range_end = _calc_view_range(anchor, view)

        # 构建查询条件
        conditions = ["t.is_active = 1"]
        params = []

        # 状态筛选
        if status == "pending":
            conditions.append("o.status = 'pending'")
        elif status == "completed":
            conditions.append("o.status = 'completed'")

        # 日期范围
        conditions.append("o.occurrence_date >= ?")
        conditions.append("o.occurrence_date <= ?")
        params.extend([range_start.strftime("%Y-%m-%d"), range_end.strftime("%Y-%m-%d")])

        identity = _get_teacher_identity(db, user.username)

        # 范围筛选：兼容历史数据中 creator/assignee 存 name 或 teacher_id 的情况
        if scope == "created":
            conditions.append(_sql_in_clause("t.creator_teacher_id", identity["aliases"]))
            params.extend(identity["aliases"])
        elif scope == "assigned":
            conditions.append(_sql_exists_assignee(identity["aliases"]))
            params.extend(identity["aliases"])
        else:  # all_visible
            conditions.append(f"({_sql_in_clause('t.creator_teacher_id', identity['aliases'])} OR {_sql_exists_assignee(identity['aliases'])})")
            params.extend(identity["aliases"])
            params.extend(identity["aliases"])

        where_clause = " AND ".join(conditions)

        # 查询待办实例
        occurrences = db.query_all(
            f"""SELECT o.id, o.todo_series_id, o.occurrence_date, o.due_at, o.status,
                       o.completed_at, o.completed_by,
                       t.title, t.description, t.todo_type, t.creator_teacher_id, t.creator_name,
                       t.start_date, t.end_date,
                       t.recurrence_rule_json
                FROM teacher_todo_occurrence o
                JOIN teacher_todo_series t ON o.todo_series_id = t.id
                WHERE {where_clause}
                ORDER BY o.occurrence_date ASC""",
            params
        )

        # 为每个 occurrence 补充关联教师列表
        items = []
        for occ in occurrences:
            assignees = db.query_all(
                """SELECT teacher_id, teacher_name
                   FROM teacher_todo_assignee
                   WHERE todo_series_id = ?""",
                (occ["todo_series_id"],)
            )
            occ["assignees"] = assignees or []
            occ["is_creator"] = occ["creator_teacher_id"] in identity["aliases"]
            items.append(occ)

        # 统计
        total = len(items)
        pending_count = sum(1 for i in items if i["status"] == "pending")
        completed_count = total - pending_count

        return {
            "success": True,
            "data": {
                "range": {
                    "view": view,
                    "start_date": range_start.strftime("%Y-%m-%d"),
                    "end_date": range_end.strftime("%Y-%m-%d")
                },
                "summary": {
                    "total": total,
                    "pending": pending_count,
                    "completed": completed_count
                },
                "items": items
            }
        }


@router.post("/create", summary="创建待办")
async def create_todo(
    todo: TodoCreate,
    user: User = Depends(require_configured_api_permission(API_TODO_CREATE, "POST", allow_missing=False))
):
    """
    创建教师待办

    权限：教师可创建待办
    """
    _validate_todo_dates(todo.todo_type, todo.start_date, todo.end_date, todo.recurrence_rule)
    with get_moral_db() as db:
        identity = _get_teacher_identity(db, user.username)
        teacher_id = identity["teacher_id"]
        teacher_name = identity["teacher_name"]

        # 插入 series
        series_id = db.execute(
            """INSERT INTO teacher_todo_series
               (title, description, creator_teacher_id, creator_name, todo_type,
                start_date, end_date, recurrence_rule_json, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (todo.title, todo.description, teacher_id, teacher_name, todo.todo_type,
             todo.start_date, todo.end_date,
             json.dumps(todo.recurrence_rule.dict()) if todo.recurrence_rule else None)
        )

        # 插入 assignee（创建者也加入，去重）
        all_assignees = set([teacher_id])
        if todo.assignee_teacher_ids:
            all_assignees.update(todo.assignee_teacher_ids)

        for aid in all_assignees:
            assignee = _get_teacher_identity(db, aid)
            aid = assignee["teacher_id"]
            aname = assignee["teacher_name"]

            db.execute(
                """INSERT OR IGNORE INTO teacher_todo_assignee (todo_series_id, teacher_id, teacher_name)
                   VALUES (?, ?, ?)""",
                (series_id, aid, aname)
            )

        # 生成 occurrences
        _generate_occurrences(db, series_id, todo.todo_type, todo.start_date, todo.end_date, todo.recurrence_rule)

        return {
            "success": True,
            "message": "待办创建成功",
            "data": {"series_id": series_id}
        }


@router.put("/{series_id}", summary="更新待办")
async def update_todo(
    series_id: int,
    todo: TodoUpdate,
    user: User = Depends(require_configured_api_permission(API_TODO_UPDATE, "PUT", allow_missing=False))
):
    """
    更新待办定义

    权限：仅创建者可编辑
    """
    with get_moral_db() as db:
        # 检查权限
        existing = db.query_one(
            "SELECT * FROM teacher_todo_series WHERE id = ?",
            (series_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="待办不存在")

        identity = _get_teacher_identity(db, user.username)
        if existing["creator_teacher_id"] not in identity["aliases"]:
            raise HTTPException(status_code=403, detail="仅创建者可编辑")

        # 更新 series
        updates = []
        params = []
        payload = todo.dict(exclude_unset=True)
        next_todo_type = payload.get("todo_type", existing["todo_type"])
        next_start_date = payload.get("start_date", existing["start_date"])
        next_end_date = payload.get("end_date", existing.get("end_date"))
        next_rule = payload.get("recurrence_rule")
        if isinstance(next_rule, dict):
            next_rule = RecurrenceRule(**next_rule) if next_rule else None
        if "recurrence_rule" not in payload:
            rule_json = existing.get("recurrence_rule_json")
            next_rule = RecurrenceRule(**json.loads(rule_json)) if rule_json else None
        _validate_todo_dates(next_todo_type, next_start_date, next_end_date, next_rule)

        if "title" in payload:
            updates.append("title = ?")
            params.append(todo.title)
        if "description" in payload:
            updates.append("description = ?")
            params.append(todo.description)
        if "todo_type" in payload:
            updates.append("todo_type = ?")
            params.append(todo.todo_type)
        if "start_date" in payload:
            updates.append("start_date = ?")
            params.append(todo.start_date)
        if "end_date" in payload:
            updates.append("end_date = ?")
            params.append(todo.end_date)
        if "recurrence_rule" in payload:
            updates.append("recurrence_rule_json = ?")
            params.append(json.dumps(todo.recurrence_rule.dict()) if todo.recurrence_rule else None)
        elif next_todo_type == "one_off":
            updates.append("recurrence_rule_json = ?")
            params.append(None)
        if "is_active" in payload:
            updates.append("is_active = ?")
            params.append(todo.is_active)

        if updates:
            params.append(series_id)
            db.execute(
                f"""UPDATE teacher_todo_series SET {", ".join(updates)}, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                params
            )

        # 更新 assignee
        if "assignee_teacher_ids" in payload:
            db.execute("DELETE FROM teacher_todo_assignee WHERE todo_series_id = ?", (series_id,))
            all_assignees = set([existing["creator_teacher_id"]] + (todo.assignee_teacher_ids or []))
            for aid in all_assignees:
                assignee = _get_teacher_identity(db, aid)
                aid = assignee["teacher_id"]
                aname = assignee["teacher_name"]
                db.execute(
                    "INSERT OR IGNORE INTO teacher_todo_assignee (todo_series_id, teacher_id, teacher_name) VALUES (?, ?, ?)",
                    (series_id, aid, aname)
                )

        if {"todo_type", "start_date", "end_date", "recurrence_rule"} & set(payload):
            updated = db.query_one("SELECT * FROM teacher_todo_series WHERE id = ?", (series_id,))
            rule_data = updated.get("recurrence_rule_json") if updated else None
            rule = RecurrenceRule(**json.loads(rule_data)) if rule_data else None
            db.execute(
                """DELETE FROM teacher_todo_occurrence
                   WHERE todo_series_id = ?
                   AND status = 'pending'
                   AND occurrence_date >= date('now', 'localtime')""",
                (series_id,)
            )
            _generate_occurrences(db, series_id, updated["todo_type"], updated["start_date"], updated.get("end_date"), rule)

        return {
            "success": True,
            "message": "待办更新成功"
        }


@router.delete("/{series_id}", summary="删除待办")
async def delete_todo(
    series_id: int,
    user: User = Depends(require_configured_api_permission(API_TODO_DELETE, "DELETE", allow_missing=False))
):
    """
    软删除待办

    权限：仅创建者可删除
    """
    with get_moral_db() as db:
        existing = db.query_one(
            "SELECT * FROM teacher_todo_series WHERE id = ?",
            (series_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="待办不存在")

        identity = _get_teacher_identity(db, user.username)
        if existing["creator_teacher_id"] not in identity["aliases"]:
            raise HTTPException(status_code=403, detail="仅创建者可删除")

        db.execute(
            "UPDATE teacher_todo_series SET is_active = 0, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (series_id,)
        )

        return {
            "success": True,
            "message": "待办已删除"
        }


@router.post("/occurrences/{occurrence_id}/complete", summary="完成待办实例")
async def complete_occurrence(
    occurrence_id: int,
    user: User = Depends(require_configured_api_permission(API_OCCURRENCE_COMPLETE, "POST", allow_missing=False))
):
    """
    标记待办实例为已完成

    权限：创建者和关联教师均可完成
    """
    with get_moral_db() as db:
        occ = db.query_one(
            """SELECT o.*, t.creator_teacher_id
               FROM teacher_todo_occurrence o
               JOIN teacher_todo_series t ON o.todo_series_id = t.id
               WHERE o.id = ?""",
            (occurrence_id,)
        )
        if not occ:
            raise HTTPException(status_code=404, detail="待办实例不存在")

        identity = _get_teacher_identity(db, user.username)

        # 检查是否为创建者或关联教师
        is_assignee = db.query_one(
            f"SELECT 1 FROM teacher_todo_assignee WHERE todo_series_id = ? AND {_sql_in_clause('teacher_id', identity['aliases'])}",
            [occ["todo_series_id"], *identity["aliases"]]
        )

        if occ["creator_teacher_id"] not in identity["aliases"] and not is_assignee:
            raise HTTPException(status_code=403, detail="仅创建者和关联教师可完成")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            """UPDATE teacher_todo_occurrence
               SET status = 'completed', completed_at = ?, completed_by = ?, updated_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (now, identity["teacher_id"], occurrence_id)
        )

        return {
            "success": True,
            "message": "待办已完成"
        }


@router.post("/occurrences/{occurrence_id}/reopen", summary="恢复待办实例")
async def reopen_occurrence(
    occurrence_id: int,
    user: User = Depends(require_configured_api_permission(API_OCCURRENCE_REOPEN, "POST", allow_missing=False))
):
    """
    恢复待办实例为未完成

    权限：创建者和关联教师均可恢复
    """
    with get_moral_db() as db:
        occ = db.query_one(
            """SELECT o.*, t.creator_teacher_id
               FROM teacher_todo_occurrence o
               JOIN teacher_todo_series t ON o.todo_series_id = t.id
               WHERE o.id = ?""",
            (occurrence_id,)
        )
        if not occ:
            raise HTTPException(status_code=404, detail="待办实例不存在")

        identity = _get_teacher_identity(db, user.username)

        is_assignee = db.query_one(
            f"SELECT 1 FROM teacher_todo_assignee WHERE todo_series_id = ? AND {_sql_in_clause('teacher_id', identity['aliases'])}",
            [occ["todo_series_id"], *identity["aliases"]]
        )

        if occ["creator_teacher_id"] not in identity["aliases"] and not is_assignee:
            raise HTTPException(status_code=403, detail="仅创建者和关联教师可恢复")

        db.execute(
            """UPDATE teacher_todo_occurrence
               SET status = 'pending', completed_at = NULL, completed_by = NULL, updated_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (occurrence_id,)
        )

        return {
            "success": True,
            "message": "待办已恢复"
        }


@router.get("/upcoming", summary="近期待办")
async def get_upcoming_todos(
    limit: int = Query(5, ge=1, le=20, description="返回数量"),
    user: User = Depends(require_configured_api_permission(API_TODO_UPCOMING, "GET", allow_missing=False))
):
    """
    获取教师最近未完成待办

    用于教师工作台展示
    """
    with get_moral_db() as db:
        identity = _get_teacher_identity(db, user.username)

        today = datetime.now().strftime("%Y-%m-%d")
        creator_clause = _sql_in_clause("t.creator_teacher_id", identity["aliases"])
        assignee_clause = _sql_exists_assignee(identity["aliases"])

        items = db.query_all(
            f"""SELECT o.id as occurrence_id, o.todo_series_id as series_id, o.occurrence_date, o.due_at,
                       t.title, t.description, t.todo_type, t.creator_teacher_id, t.creator_name
               FROM teacher_todo_occurrence o
               JOIN teacher_todo_series t ON o.todo_series_id = t.id
               WHERE t.is_active = 1
               AND o.status = 'pending'
               AND o.occurrence_date >= ?
               AND ({creator_clause} OR {assignee_clause})
               ORDER BY o.occurrence_date ASC
               LIMIT ?""",
            [today, *identity["aliases"], *identity["aliases"], limit]
        )

        # 补充关联教师
        for item in items:
            assignees = db.query_all(
                "SELECT teacher_id, teacher_name FROM teacher_todo_assignee WHERE todo_series_id = ?",
                (item["series_id"],)
            )
            item["assignees"] = assignees or []
            item["is_creator"] = item["creator_teacher_id"] in identity["aliases"]

        return {
            "success": True,
            "data": {
                "todos": items,
                "total": len(items)
            }
        }


# =============================================================================
# 辅助函数
# =============================================================================

def _get_teacher_identity(db, username: str) -> Dict[str, Any]:
    """返回当前教师的规范 teacher_id、姓名以及历史兼容别名。"""
    teacher = db.query_one(
        "SELECT teacher_id, name FROM teacher WHERE name = ? OR teacher_id = ?",
        (username, username)
    )
    teacher_id = str((teacher or {}).get("teacher_id") or username)
    teacher_name = str((teacher or {}).get("name") or username)
    aliases = []
    for value in (username, teacher_id, teacher_name):
        if value and value not in aliases:
            aliases.append(str(value))
    return {"teacher_id": teacher_id, "teacher_name": teacher_name, "aliases": aliases}


def _validate_todo_dates(
    todo_type: str,
    start_date: str,
    end_date: Optional[str],
    rule: Optional[RecurrenceRule],
):
    if todo_type not in {"one_off", "weekly", "monthly", "yearly"}:
        raise HTTPException(status_code=400, detail="待办类型无效")
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="开始日期格式无效")
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="结束日期格式无效")
        if end < start:
            raise HTTPException(status_code=400, detail="结束日期不能早于开始日期")
    if todo_type == "one_off":
        return
    if not rule or rule.unit != todo_type:
        raise HTTPException(status_code=400, detail="周期规则缺失或不匹配")
    if todo_type == "weekly" and rule.weekday is None:
        raise HTTPException(status_code=400, detail="每周任务必须选择星期")
    if todo_type == "monthly" and not rule.day_of_month:
        raise HTTPException(status_code=400, detail="每月任务必须选择日期")
    if todo_type == "yearly" and (not rule.month or not rule.day):
        raise HTTPException(status_code=400, detail="每年任务必须选择月份和日期")


def _sql_in_clause(field: str, values: List[str]) -> str:
    placeholders = ",".join(["?"] * len(values))
    return f"{field} IN ({placeholders})"


def _sql_exists_assignee(values: List[str]) -> str:
    return (
        "EXISTS (SELECT 1 FROM teacher_todo_assignee a "
        f"WHERE a.todo_series_id = t.id AND {_sql_in_clause('a.teacher_id', values)})"
    )

def _calc_view_range(anchor: datetime, view: str) -> tuple:
    """
    计算视图的日期范围

    Args:
        anchor: 锚点日期
        view: 视图类型

    Returns:
        (range_start, range_end)
    """
    if view == "week":
        # 本周周一到周日
        weekday = anchor.weekday()
        range_start = anchor - timedelta(days=weekday)
        range_end = range_start + timedelta(days=6)
    elif view == "month":
        # 本月第一天到最后一天
        range_start = anchor.replace(day=1)
        last_day = monthrange(anchor.year, anchor.month)[1]
        range_end = anchor.replace(day=last_day)
    elif view == "year":
        # 本年第一天到最后一天
        range_start = anchor.replace(month=1, day=1)
        range_end = anchor.replace(month=12, day=31)
    else:
        range_start = anchor
        range_end = anchor

    return range_start, range_end


def _generate_occurrences(db, series_id: int, todo_type: str, start_date: str,
                          end_date: Optional[str], rule: Optional[RecurrenceRule]):
    """
    生成待办实例

    Args:
        db: 数据库连接
        series_id: 待办定义 ID
        todo_type: 类型
        start_date: 开始日期
        end_date: 结束日期
        rule: 周期规则
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

    if todo_type == "one_off":
        # 一次性：生成一个实例
        db.execute(
            """INSERT INTO teacher_todo_occurrence (todo_series_id, occurrence_date, status)
               VALUES (?, ?, 'pending')""",
            (series_id, start_date)
        )
        return

    if not rule:
        return

    # 计算生成范围
    today = datetime.now()
    if todo_type == "weekly":
        gen_end = today + timedelta(weeks=12)
    elif todo_type == "monthly":
        gen_end = _add_months(today, 12)
    elif todo_type == "yearly":
        gen_end = _safe_replace_year(today, today.year + 3)
    else:
        gen_end = today + timedelta(days=30)

    if end and end < gen_end:
        gen_end = end

    # 按规则生成日期
    dates = _calc_recurrence_dates(start, gen_end, rule)

    for d in dates:
        db.execute(
            """INSERT OR IGNORE INTO teacher_todo_occurrence (todo_series_id, occurrence_date, status)
               VALUES (?, ?, 'pending')""",
            (series_id, d.strftime("%Y-%m-%d"))
        )


def _calc_recurrence_dates(start: datetime, end: datetime, rule: RecurrenceRule) -> list:
    """
    计算周期日期列表

    Args:
        start: 开始日期
        end: 结束日期
        rule: 周期规则

    Returns:
        日期列表
    """
    dates = []
    current = start

    if rule.unit == "weekly" and rule.weekday is not None:
        # 找到第一个符合 weekday 的日期
        days_ahead = rule.weekday - current.weekday()
        if days_ahead < 0:
            days_ahead += 7
        current = current + timedelta(days=days_ahead)

        while current <= end:
            dates.append(current)
            current = current + timedelta(days=7)

    elif rule.unit == "monthly" and rule.day_of_month:
        current = current.replace(day=1)
        while current <= end:
            # 尝试设置到指定日期
            try:
                target = current.replace(day=rule.day_of_month)
                if target >= start and target <= end:
                    dates.append(target)
            except ValueError:
                # 日期不存在（如 2月30日），跳过
                pass
            current = _add_months(current, 1)

    elif rule.unit == "yearly" and rule.month and rule.day:
        current = current.replace(month=1, day=1)
        while current <= end:
            try:
                target = current.replace(month=rule.month, day=rule.day)
                if target >= start and target <= end:
                    dates.append(target)
            except ValueError:
                pass
            current = _safe_replace_year(current, current.year + 1)

    return dates


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _safe_replace_year(value: datetime, year: int) -> datetime:
    day = min(value.day, monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)
