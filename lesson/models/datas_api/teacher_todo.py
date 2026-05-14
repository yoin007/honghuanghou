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
ROLLING_OCCURRENCE_COUNT = 3

# API 路径常量
API_TODO_LIST = "/api/teacher/todos"
API_TODO_CREATE = "/api/teacher/todos/create"
API_TODO_UPDATE = "/api/teacher/todos/{series_id}"
API_TODO_DELETE = "/api/teacher/todos/{series_id}"
API_OCCURRENCE_COMPLETE = "/api/teacher/todos/occurrences/{occurrence_id}/complete"
API_OCCURRENCE_REOPEN = "/api/teacher/todos/occurrences/{occurrence_id}/reopen"
API_TODO_UPCOMING = "/api/teacher/todos/upcoming"
API_TODO_GROUP_LIST = "/api/teacher/todos/groups"
API_TODO_GROUP_CREATE = "/api/teacher/todos/groups"
API_TODO_GROUP_UPDATE = "/api/teacher/todos/groups/{group_id}"
API_TODO_GROUP_DELETE = "/api/teacher/todos/groups/{group_id}"
API_TODO_GROUP_MEMBER_ADD = "/api/teacher/todos/groups/{group_id}/members"
API_TODO_GROUP_MEMBER_REMOVE = "/api/teacher/todos/groups/{group_id}/members/{teacher_id}"


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
    time_of_day: Optional[str] = Field("08:00", description="时间（HH:mm格式）")
    recurrence_rule: Optional[RecurrenceRule] = Field(None, description="周期规则")
    wechat_notify_enabled: Optional[int] = Field(1, ge=0, le=1, description="微信通知开关")
    remind_before_minutes: Optional[int] = Field(30, ge=0, description="提前提醒分钟数")
    notify_creator: Optional[int] = Field(1, ge=0, le=1, description="提醒创建者")
    notify_assignees: Optional[int] = Field(1, ge=0, le=1, description="提醒协作教师")
    assignee_group_ids: Optional[List[int]] = Field(None, description="协作群组ID列表")
    assignee_teacher_ids: Optional[List[str]] = Field(None, description="关联教师ID列表")


class TodoUpdate(BaseModel):
    """更新待办"""
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    todo_type: Optional[str] = Field(None)
    start_date: Optional[str] = Field(None)
    end_date: Optional[str] = Field(None)
    time_of_day: Optional[str] = Field(None, description="时间（HH:mm格式）")
    recurrence_rule: Optional[RecurrenceRule] = Field(None)
    wechat_notify_enabled: Optional[int] = Field(None, ge=0, le=1)
    remind_before_minutes: Optional[int] = Field(None, ge=0)
    notify_creator: Optional[int] = Field(None, ge=0, le=1)
    notify_assignees: Optional[int] = Field(None, ge=0, le=1)
    assignee_group_ids: Optional[List[int]] = Field(None)
    assignee_teacher_ids: Optional[List[str]] = Field(None)
    is_active: Optional[int] = Field(None, ge=0, le=1)


class GroupCreate(BaseModel):
    """创建协作群组"""
    group_name: str = Field(..., min_length=1, max_length=50, description="群组名称")
    member_teacher_ids: Optional[List[str]] = Field(None, description="初始成员ID列表")


class GroupUpdate(BaseModel):
    """更新协作群组"""
    group_name: Optional[str] = Field(None, min_length=1, max_length=50)


class GroupMemberAdd(BaseModel):
    """添加群组成员"""
    teacher_ids: List[str] = Field(..., min_items=1, description="要添加的教师ID列表")


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="查询待办列表")
async def get_todos(
    view: str = Query("week", description="视图: week/month/year"),
    anchor_date: Optional[str] = Query(None, description="当前周期锚点日期"),
    status: str = Query("all", description="状态筛选: all/pending/completed/overdue"),
    scope: str = Query("all_visible", description="范围: all_visible/created/assigned"),
    user: User = Depends(require_configured_api_permission(API_TODO_LIST, "GET", allow_missing=False))
):
    """
    查询教师可见待办列表

    权限：教师可查看自己创建和关联给自己的待办
    """
    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        ensure_future_occurrences(db)
        # 解析锚点日期
        anchor = datetime.strptime(anchor_date, "%Y-%m-%d") if anchor_date else datetime.now()

        # 计算周期范围
        range_start, range_end = _calc_view_range(anchor, view)

        # 构建查询条件
        conditions = ["t.is_active = 1"]
        params = []

        # 状态筛选
        if status == "pending":
            conditions.append("o.status = 'pending' AND o.is_overdue = 0")
        elif status == "completed":
            conditions.append("o.status = 'completed'")
        elif status == "overdue":
            conditions.append("o.status = 'pending' AND o.is_overdue = 1")

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
            f"""SELECT o.id, o.todo_series_id, o.occurrence_date, o.scheduled_at, o.due_at, o.status,
                       o.completed_at, o.completed_by, o.is_overdue,
                       t.title, t.description, t.todo_type, t.creator_teacher_id, t.creator_name,
                       t.start_date, t.end_date,
                       t.recurrence_rule_json, t.time_of_day, t.wechat_notify_enabled,
                       t.remind_before_minutes, t.notify_creator, t.notify_assignees
                FROM teacher_todo_occurrence o
                JOIN teacher_todo_series t ON o.todo_series_id = t.id
                WHERE {where_clause}
                ORDER BY COALESCE(o.scheduled_at, o.occurrence_date) ASC""",
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
        overdue_count = sum(1 for i in items if i.get("is_overdue") == 1)
        pending_count = sum(1 for i in items if i["status"] == "pending" and i.get("is_overdue") == 0)
        completed_count = sum(1 for i in items if i["status"] == "completed")

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
                    "completed": completed_count,
                    "overdue": overdue_count
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
    time_of_day = _validate_time_of_day(todo.time_of_day)

    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        ensure_future_occurrences(db)
        identity = _get_teacher_identity(db, user.username)
        teacher_id = identity["teacher_id"]
        teacher_name = identity["teacher_name"]

        # 展开群组成员
        group_members = _expand_group_members(db, todo.assignee_group_ids)

        # 插入 series
        db.execute(
            """INSERT INTO teacher_todo_series
               (title, description, creator_teacher_id, creator_name, todo_type,
                start_date, end_date, recurrence_rule_json, time_of_day,
                wechat_notify_enabled, remind_before_minutes, notify_creator, notify_assignees,
                is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (todo.title, todo.description, teacher_id, teacher_name, todo.todo_type,
             todo.start_date, todo.end_date,
             json.dumps(todo.recurrence_rule.dict()) if todo.recurrence_rule else None,
             time_of_day, todo.wechat_notify_enabled, todo.remind_before_minutes,
             todo.notify_creator, todo.notify_assignees)
        )
        series_id = db.lastrowid()

        # 插入 assignee（创建者 + 群组成员 + 手动添加，去重）
        all_assignees = set([teacher_id])
        # 群组成员
        for m in group_members:
            all_assignees.add(m["teacher_id"])
        # 手动添加
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

        # 生成 occurrences（传入 time_of_day）
        _generate_occurrences(db, series_id, todo.todo_type, todo.start_date, todo.end_date, todo.recurrence_rule, time_of_day)

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
        ensure_teacher_todo_schema(db)
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
        if "time_of_day" in payload:
            updates.append("time_of_day = ?")
            params.append(_validate_time_of_day(todo.time_of_day))
        if "wechat_notify_enabled" in payload:
            updates.append("wechat_notify_enabled = ?")
            params.append(todo.wechat_notify_enabled)
        if "remind_before_minutes" in payload:
            updates.append("remind_before_minutes = ?")
            params.append(todo.remind_before_minutes)
        if "notify_creator" in payload:
            updates.append("notify_creator = ?")
            params.append(todo.notify_creator)
        if "notify_assignees" in payload:
            updates.append("notify_assignees = ?")
            params.append(todo.notify_assignees)
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

        # 更新 assignee。编辑时群组按当前成员展开为快照，后续群组变化不影响已建待办。
        if "assignee_teacher_ids" in payload or "assignee_group_ids" in payload:
            db.execute("DELETE FROM teacher_todo_assignee WHERE todo_series_id = ?", (series_id,))
            all_assignees = set([existing["creator_teacher_id"]] + (todo.assignee_teacher_ids or []))
            for member in _expand_group_members(db, todo.assignee_group_ids):
                all_assignees.add(member["teacher_id"])
            for aid in all_assignees:
                assignee = _get_teacher_identity(db, aid)
                aid = assignee["teacher_id"]
                aname = assignee["teacher_name"]
                db.execute(
                    "INSERT OR IGNORE INTO teacher_todo_assignee (todo_series_id, teacher_id, teacher_name) VALUES (?, ?, ?)",
                    (series_id, aid, aname)
                )

        if {"todo_type", "start_date", "end_date", "recurrence_rule", "time_of_day"} & set(payload):
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
            _generate_occurrences(
                db,
                series_id,
                updated["todo_type"],
                updated["start_date"],
                updated.get("end_date"),
                rule,
                _validate_time_of_day(updated.get("time_of_day")),
            )

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
        ensure_teacher_todo_schema(db)
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
        ensure_teacher_todo_schema(db)
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
        ensure_teacher_todo_schema(db)
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
        ensure_teacher_todo_schema(db)
        identity = _get_teacher_identity(db, user.username)

        today = datetime.now().strftime("%Y-%m-%d")
        creator_clause = _sql_in_clause("t.creator_teacher_id", identity["aliases"])
        assignee_clause = _sql_exists_assignee(identity["aliases"])

        items = db.query_all(
            f"""SELECT o.id as occurrence_id, o.todo_series_id as series_id, o.occurrence_date,
                       o.scheduled_at, o.due_at, o.is_overdue,
                       t.title, t.description, t.todo_type, t.creator_teacher_id, t.creator_name,
                       t.time_of_day, t.wechat_notify_enabled, t.remind_before_minutes,
                       t.notify_creator, t.notify_assignees
               FROM teacher_todo_occurrence o
               JOIN teacher_todo_series t ON o.todo_series_id = t.id
               WHERE t.is_active = 1
               AND o.status = 'pending'
               AND o.occurrence_date >= ?
               AND ({creator_clause} OR {assignee_clause})
               ORDER BY COALESCE(o.scheduled_at, o.occurrence_date) ASC
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
# 协作群组 API
# =============================================================================

@router.get("/groups", summary="查询协作群组")
async def get_groups(
    user: User = Depends(require_configured_api_permission(API_TODO_GROUP_LIST, "GET", allow_missing=False))
):
    """
    查询教师创建的协作群组

    权限：教师可查看自己创建的群组
    """
    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        identity = _get_teacher_identity(db, user.username)
        teacher_id = identity["teacher_id"]

        groups = db.query_all(
            """SELECT id, group_name, owner_teacher_id, created_at, updated_at
               FROM teacher_todo_group
               WHERE owner_teacher_id = ? AND is_active = 1
               ORDER BY created_at DESC""",
            (teacher_id,)
        )

        # 为每个群组补充成员列表
        result = []
        for g in groups:
            members = db.query_all(
                """SELECT teacher_id, teacher_name, created_at as added_at
                   FROM teacher_todo_group_member
                   WHERE group_id = ?
                   ORDER BY created_at""",
                (g["id"],)
            )
            result.append({
                "group_id": g["id"],
                "group_name": g["group_name"],
                "creator_teacher_id": g["owner_teacher_id"],
                "members": members or [],
                "created_at": g["created_at"],
                "updated_at": g["updated_at"]
            })

        return {
            "success": True,
            "data": {
                "groups": result,
                "total": len(result)
            }
        }


@router.post("/groups", summary="创建协作群组")
async def create_group(
    group: GroupCreate,
    user: User = Depends(require_configured_api_permission(API_TODO_GROUP_CREATE, "POST", allow_missing=False))
):
    """
    创建协作群组

    权限：教师可创建群组
    """
    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        identity = _get_teacher_identity(db, user.username)
        teacher_id = identity["teacher_id"]

        existing_group = db.query_one(
            "SELECT id, is_active FROM teacher_todo_group WHERE owner_teacher_id = ? AND group_name = ?",
            (teacher_id, group.group_name)
        )
        if existing_group and int(existing_group.get("is_active") or 0) == 1:
            raise HTTPException(status_code=400, detail="群组名称已存在")
        if existing_group:
            group_id = existing_group["id"]
            db.execute(
                """UPDATE teacher_todo_group
                   SET is_active = 1, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (group_id,)
            )
            db.execute("DELETE FROM teacher_todo_group_member WHERE group_id = ?", (group_id,))
        else:
            db.execute(
                """INSERT INTO teacher_todo_group (group_name, owner_teacher_id, is_active)
                   VALUES (?, ?, 1)""",
                (group.group_name, teacher_id)
            )
            group_id = db.lastrowid()

        # 添加初始成员
        if group.member_teacher_ids:
            for mid in group.member_teacher_ids:
                member_identity = _get_teacher_identity(db, mid)
                db.execute(
                    """INSERT OR IGNORE INTO teacher_todo_group_member
                       (group_id, teacher_id, teacher_name)
                       VALUES (?, ?, ?)""",
                    (group_id, member_identity["teacher_id"], member_identity["teacher_name"])
                )

        return {
            "success": True,
            "message": "群组创建成功",
            "data": {"group_id": group_id}
        }


@router.put("/groups/{group_id}", summary="更新协作群组")
async def update_group(
    group_id: int,
    group: GroupUpdate,
    user: User = Depends(require_configured_api_permission(API_TODO_GROUP_UPDATE, "PUT", allow_missing=False))
):
    """
    更新协作群组名称

    权限：仅创建者可更新
    """
    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        existing = db.query_one(
            "SELECT * FROM teacher_todo_group WHERE id = ? AND is_active = 1",
            (group_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="群组不存在")

        identity = _get_teacher_identity(db, user.username)
        if existing["owner_teacher_id"] != identity["teacher_id"]:
            raise HTTPException(status_code=403, detail="仅创建者可更新")

        if group.group_name:
            db.execute(
                """UPDATE teacher_todo_group SET group_name = ?, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (group.group_name, group_id)
            )

        return {
            "success": True,
            "message": "群组更新成功"
        }


@router.delete("/groups/{group_id}", summary="删除协作群组")
async def delete_group(
    group_id: int,
    user: User = Depends(require_configured_api_permission(API_TODO_GROUP_DELETE, "DELETE", allow_missing=False))
):
    """
    软删除协作群组

    权限：仅创建者可删除
    """
    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        existing = db.query_one(
            "SELECT * FROM teacher_todo_group WHERE id = ? AND is_active = 1",
            (group_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="群组不存在")

        identity = _get_teacher_identity(db, user.username)
        if existing["owner_teacher_id"] != identity["teacher_id"]:
            raise HTTPException(status_code=403, detail="仅创建者可删除")

        db.execute(
            """UPDATE teacher_todo_group SET is_active = 0, updated_at = datetime('now', 'localtime')
               WHERE id = ?""",
            (group_id,)
        )
        db.execute(
            "DELETE FROM teacher_todo_group_member WHERE group_id = ?",
            (group_id,)
        )

        return {
            "success": True,
            "message": "群组已删除"
        }


@router.post("/groups/{group_id}/members", summary="添加群组成员")
async def add_group_members(
    group_id: int,
    members: GroupMemberAdd,
    user: User = Depends(require_configured_api_permission(API_TODO_GROUP_MEMBER_ADD, "POST", allow_missing=False))
):
    """
    添加群组成员

    权限：仅创建者可添加成员
    """
    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        existing = db.query_one(
            "SELECT * FROM teacher_todo_group WHERE id = ? AND is_active = 1",
            (group_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="群组不存在")

        identity = _get_teacher_identity(db, user.username)
        if existing["owner_teacher_id"] != identity["teacher_id"]:
            raise HTTPException(status_code=403, detail="仅创建者可添加成员")

        for mid in members.teacher_ids:
            member_identity = _get_teacher_identity(db, mid)
            db.execute(
                """INSERT OR IGNORE INTO teacher_todo_group_member
                   (group_id, teacher_id, teacher_name)
                   VALUES (?, ?, ?)""",
                (group_id, member_identity["teacher_id"], member_identity["teacher_name"])
            )

        # 返回当前成员列表
        current_members = db.query_all(
            """SELECT teacher_id, teacher_name, created_at as added_at
               FROM teacher_todo_group_member
               WHERE group_id = ?
               ORDER BY created_at""",
            (group_id,)
        )

        return {
            "success": True,
            "message": "成员添加成功",
            "data": {"members": current_members or []}
        }


@router.delete("/groups/{group_id}/members/{teacher_id}", summary="移除群组成员")
async def remove_group_member(
    group_id: int,
    teacher_id: str,
    user: User = Depends(require_configured_api_permission(API_TODO_GROUP_MEMBER_REMOVE, "DELETE", allow_missing=False))
):
    """
    移除群组成员

    权限：仅创建者可移除成员
    """
    with get_moral_db() as db:
        ensure_teacher_todo_schema(db)
        existing = db.query_one(
            "SELECT * FROM teacher_todo_group WHERE id = ? AND is_active = 1",
            (group_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="群组不存在")

        identity = _get_teacher_identity(db, user.username)
        if existing["owner_teacher_id"] != identity["teacher_id"]:
            raise HTTPException(status_code=403, detail="仅创建者可移除成员")

        db.execute(
            "DELETE FROM teacher_todo_group_member WHERE group_id = ? AND teacher_id = ?",
            (group_id, teacher_id)
        )

        return {
            "success": True,
            "message": "成员已移除"
        }


# =============================================================================
# 辅助函数
# =============================================================================

def ensure_teacher_todo_schema(db):
    """确保教师待办升级所需表和字段存在，兼容已运行过旧迁移的数据库。"""
    db.execute(
        """CREATE TABLE IF NOT EXISTS teacher_todo_series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            creator_teacher_id TEXT NOT NULL,
            creator_name TEXT,
            todo_type TEXT NOT NULL CHECK (todo_type IN ('one_off', 'weekly', 'monthly', 'yearly')),
            start_date TEXT NOT NULL,
            end_date TEXT,
            recurrence_rule_json TEXT,
            time_of_day TEXT DEFAULT '08:00',
            wechat_notify_enabled INTEGER DEFAULT 1,
            remind_before_minutes INTEGER DEFAULT 30,
            notify_creator INTEGER DEFAULT 1,
            notify_assignees INTEGER DEFAULT 1,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS teacher_todo_assignee (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            todo_series_id INTEGER NOT NULL,
            teacher_id TEXT NOT NULL,
            teacher_name TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE (todo_series_id, teacher_id)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS teacher_todo_occurrence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            todo_series_id INTEGER NOT NULL,
            occurrence_date TEXT NOT NULL,
            scheduled_at TEXT,
            due_at TEXT,
            status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
            completed_at TEXT,
            completed_by TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE (todo_series_id, occurrence_date)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS teacher_todo_reminder_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            occurrence_id INTEGER NOT NULL,
            todo_series_id INTEGER NOT NULL,
            teacher_id TEXT NOT NULL,
            reminder_type TEXT DEFAULT 'scheduled',
            remind_before_minutes INTEGER DEFAULT 30,
            scheduled_remind_time TEXT NOT NULL,
            actual_remind_time TEXT,
            message TEXT,
            is_sent INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE (occurrence_id, teacher_id, reminder_type)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS teacher_todo_group (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_teacher_id TEXT NOT NULL,
            group_name TEXT NOT NULL,
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE (owner_teacher_id, group_name)
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS teacher_todo_group_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            teacher_id TEXT NOT NULL,
            teacher_name TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            UNIQUE (group_id, teacher_id)
        )"""
    )

    for table, column, ddl in [
        ("teacher_todo_series", "time_of_day", "ALTER TABLE teacher_todo_series ADD COLUMN time_of_day TEXT DEFAULT '08:00'"),
        ("teacher_todo_series", "wechat_notify_enabled", "ALTER TABLE teacher_todo_series ADD COLUMN wechat_notify_enabled INTEGER DEFAULT 1"),
        ("teacher_todo_series", "remind_before_minutes", "ALTER TABLE teacher_todo_series ADD COLUMN remind_before_minutes INTEGER DEFAULT 30"),
        ("teacher_todo_series", "notify_creator", "ALTER TABLE teacher_todo_series ADD COLUMN notify_creator INTEGER DEFAULT 1"),
        ("teacher_todo_series", "notify_assignees", "ALTER TABLE teacher_todo_series ADD COLUMN notify_assignees INTEGER DEFAULT 1"),
        ("teacher_todo_occurrence", "scheduled_at", "ALTER TABLE teacher_todo_occurrence ADD COLUMN scheduled_at TEXT"),
        ("teacher_todo_occurrence", "due_at", "ALTER TABLE teacher_todo_occurrence ADD COLUMN due_at TEXT"),
        ("teacher_todo_occurrence", "is_overdue", "ALTER TABLE teacher_todo_occurrence ADD COLUMN is_overdue INTEGER DEFAULT 0"),
        ("teacher_todo_reminder_log", "todo_series_id", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN todo_series_id INTEGER"),
        ("teacher_todo_reminder_log", "teacher_id", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN teacher_id TEXT"),
        ("teacher_todo_reminder_log", "reminder_type", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN reminder_type TEXT DEFAULT 'scheduled'"),
        ("teacher_todo_reminder_log", "remind_before_minutes", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN remind_before_minutes INTEGER DEFAULT 30"),
        ("teacher_todo_reminder_log", "scheduled_remind_time", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN scheduled_remind_time TEXT"),
        ("teacher_todo_reminder_log", "actual_remind_time", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN actual_remind_time TEXT"),
        ("teacher_todo_reminder_log", "message", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN message TEXT"),
        ("teacher_todo_reminder_log", "is_sent", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN is_sent INTEGER DEFAULT 0"),
        ("teacher_todo_reminder_log", "reminder_sequence", "ALTER TABLE teacher_todo_reminder_log ADD COLUMN reminder_sequence INTEGER DEFAULT 1"),
        ("teacher_todo_group", "description", "ALTER TABLE teacher_todo_group ADD COLUMN description TEXT"),
    ]:
        columns = db.query_all(f"PRAGMA table_info({table})")
        if column not in {item["name"] for item in columns}:
            db.execute(ddl)

    db.execute("UPDATE teacher_todo_series SET time_of_day = '08:00' WHERE time_of_day IS NULL OR time_of_day = ''")
    db.execute(
        """UPDATE teacher_todo_occurrence
           SET scheduled_at = occurrence_date || ' 08:00:00'
           WHERE scheduled_at IS NULL OR scheduled_at = ''"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_todo_series_creator ON teacher_todo_series(creator_teacher_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_todo_assignee_series ON teacher_todo_assignee(todo_series_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_todo_assignee_teacher ON teacher_todo_assignee(teacher_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_todo_occurrence_series ON teacher_todo_occurrence(todo_series_id)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_todo_occurrence_scheduled ON teacher_todo_occurrence(scheduled_at)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_todo_group_owner ON teacher_todo_group(owner_teacher_id)")

    # 移除 teacher_todo_reminder_log 的 UNIQUE 约束（支持多次提醒记录）
    # SQLite 不支持 ALTER 删除约束，需要重建表
    try:
        old_schema = db.query_one(
            """SELECT sql FROM sqlite_master
               WHERE type='table' AND name='teacher_todo_reminder_log'"""
        )
        if old_schema and "UNIQUE (occurrence_id, receiver_teacher_id, channel, planned_remind_at)" in old_schema.get("sql", ""):
            # 备份数据
            db.execute("CREATE TABLE IF NOT EXISTS teacher_todo_reminder_log_backup AS SELECT * FROM teacher_todo_reminder_log")
            # 删除旧表
            db.execute("DROP TABLE teacher_todo_reminder_log")
            # 创建新表（无 UNIQUE 约束）
            db.execute(
                """CREATE TABLE teacher_todo_reminder_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    occurrence_id INTEGER NOT NULL,
                    receiver_teacher_id TEXT NOT NULL,
                    channel TEXT DEFAULT 'wechat',
                    planned_remind_at TEXT NOT NULL,
                    sent_at TEXT,
                    send_status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    todo_series_id INTEGER,
                    teacher_id TEXT,
                    reminder_type TEXT DEFAULT 'scheduled',
                    remind_before_minutes INTEGER DEFAULT 30,
                    scheduled_remind_time TEXT,
                    actual_remind_time TEXT,
                    message TEXT,
                    is_sent INTEGER DEFAULT 0,
                    reminder_sequence INTEGER DEFAULT 1
                )"""
            )
            # 恢复数据
            db.execute(
                """INSERT INTO teacher_todo_reminder_log
                   SELECT id, occurrence_id, receiver_teacher_id, channel, planned_remind_at,
                          sent_at, send_status, error_message, created_at, todo_series_id,
                          teacher_id, reminder_type, remind_before_minutes, scheduled_remind_time,
                          actual_remind_time, message, is_sent, reminder_sequence
                   FROM teacher_todo_reminder_log_backup"""
            )
            # 删除备份表
            db.execute("DROP TABLE teacher_todo_reminder_log_backup")
            logger.info("teacher_todo_reminder_log UNIQUE 约束已移除，支持多次提醒记录")
    except Exception as e:
        logger.warning(f"移除 UNIQUE 约束失败（非致命）: {e}")


def ensure_future_occurrences(db, today: Optional[date] = None) -> Dict[str, int]:
    """滚动维护周期待办实例，并清理不符合当前规则的未完成未来实例。"""
    current_date = today or date.today()
    current_str = current_date.strftime("%Y-%m-%d")
    generated = 0
    deleted = 0

    series_rows = db.query_all(
        """SELECT id, todo_type, start_date, end_date, recurrence_rule_json, time_of_day
           FROM teacher_todo_series
           WHERE is_active = 1 AND todo_type IN ('weekly', 'monthly', 'yearly')"""
    )

    for series in series_rows:
        try:
            rule_data = json.loads(series.get("recurrence_rule_json") or "{}")
            rule = RecurrenceRule(**rule_data)
            _validate_todo_dates(
                series["todo_type"],
                series["start_date"],
                series.get("end_date"),
                rule,
            )
        except Exception as exc:
            logger.warning("跳过无效周期待办规则: series_id=%s, error=%s", series.get("id"), exc)
            continue

        window_dates = {
            d.strftime("%Y-%m-%d")
            for d in _calc_recurrence_dates(
                max(
                    datetime.strptime(series["start_date"], "%Y-%m-%d"),
                    datetime.combine(current_date, datetime.min.time()),
                ),
                _calc_generation_end(series["todo_type"], current_date, series.get("end_date")),
                rule,
            )[:ROLLING_OCCURRENCE_COUNT]
        }

        occurrences = db.query_all(
            """SELECT id, occurrence_date
               FROM teacher_todo_occurrence
               WHERE todo_series_id = ?
               AND status = 'pending'
               AND occurrence_date >= ?""",
            (series["id"], current_str)
        )
        for occ in occurrences:
            if occ["occurrence_date"] not in window_dates or not _occurrence_matches_rule(
                occ["occurrence_date"],
                series["todo_type"],
                series["start_date"],
                series.get("end_date"),
                rule,
            ):
                db.execute("DELETE FROM teacher_todo_occurrence WHERE id = ?", (occ["id"],))
                deleted += 1

        before_count = db.query_value(
            "SELECT COUNT(*) FROM teacher_todo_occurrence WHERE todo_series_id = ?",
            (series["id"],)
        ) or 0
        _generate_occurrences(
            db,
            series["id"],
            series["todo_type"],
            series["start_date"],
            series.get("end_date"),
            rule,
            _validate_time_of_day(series.get("time_of_day")),
            from_date=current_str,
            max_occurrences=ROLLING_OCCURRENCE_COUNT,
        )
        after_count = db.query_value(
            "SELECT COUNT(*) FROM teacher_todo_occurrence WHERE todo_series_id = ?",
            (series["id"],)
        ) or 0
        generated += max(0, int(after_count) - int(before_count))

    return {"generated": generated, "deleted": deleted}


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


def _validate_time_of_day(time_of_day: Optional[str]) -> str:
    """校验时间格式 HH:mm"""
    if not time_of_day:
        return "08:00"
    try:
        datetime.strptime(time_of_day, "%H:%M")
        return time_of_day
    except ValueError:
        raise HTTPException(status_code=400, detail=f"时间格式无效: {time_of_day}，应为 HH:mm")


def _expand_group_members(db, group_ids: Optional[List[int]]) -> List[Dict[str, str]]:
    """将群组ID列表展开成教师列表"""
    if not group_ids:
        return []
    members = []
    for gid in group_ids:
        group_members = db.query_all(
            """SELECT gm.teacher_id, gm.teacher_name
               FROM teacher_todo_group_member gm
               JOIN teacher_todo_group g ON gm.group_id = g.id
               WHERE g.id = ? AND g.is_active = 1""",
            (gid,)
        )
        for m in group_members:
            if m["teacher_id"] not in [mem["teacher_id"] for mem in members]:
                members.append({"teacher_id": m["teacher_id"], "teacher_name": m.get("teacher_name")})
    return members


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
                          end_date: Optional[str], rule: Optional[RecurrenceRule],
                          time_of_day: str = "08:00",
                          from_date: Optional[str] = None,
                          max_occurrences: int = ROLLING_OCCURRENCE_COUNT):
    """
    生成待办实例

    Args:
        db: 数据库连接
        series_id: 待办定义 ID
        todo_type: 类型
        start_date: 开始日期
        end_date: 结束日期
        rule: 周期规则
        time_of_day: 时间（HH:mm格式）
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    if from_date:
        start = max(start, datetime.strptime(from_date, "%Y-%m-%d"))

    # 格式化 scheduled_at = occurrence_date + time_of_day
    def make_scheduled_at(date_str: str) -> str:
        return f"{date_str} {time_of_day}:00"

    if todo_type == "one_off":
        # 一次性：生成一个实例
        scheduled_at = make_scheduled_at(start_date)
        db.execute(
            """INSERT INTO teacher_todo_occurrence (todo_series_id, occurrence_date, scheduled_at, status)
               VALUES (?, ?, ?, 'pending')""",
            (series_id, start_date, scheduled_at)
        )
        return

    if not rule:
        return

    # 计算生成范围。范围可以大一些，但最终只取最近 N 次，后续由滚动维护补齐。
    gen_end = _calc_generation_end(todo_type, date.today(), end_date)

    # 按规则生成日期
    dates = _calc_recurrence_dates(start, gen_end, rule)
    if max_occurrences:
        dates = dates[:max_occurrences]

    for d in dates:
        date_str = d.strftime("%Y-%m-%d")
        scheduled_at = make_scheduled_at(date_str)
        db.execute(
            """INSERT OR IGNORE INTO teacher_todo_occurrence (todo_series_id, occurrence_date, scheduled_at, status)
               VALUES (?, ?, ?, 'pending')""",
            (series_id, date_str, scheduled_at)
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


def _calc_generation_end(todo_type: str, today: date, end_date: Optional[str]) -> datetime:
    base = datetime.combine(today, datetime.min.time())
    if todo_type == "weekly":
        gen_end = base + timedelta(weeks=12)
    elif todo_type == "monthly":
        gen_end = _add_months(base, 12)
    elif todo_type == "yearly":
        gen_end = _safe_replace_year(base, base.year + 3)
    else:
        gen_end = base + timedelta(days=30)

    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
        if end < gen_end:
            return end
    return gen_end


def _occurrence_matches_rule(
    occurrence_date: str,
    todo_type: str,
    start_date: str,
    end_date: Optional[str],
    rule: RecurrenceRule,
) -> bool:
    try:
        current = datetime.strptime(occurrence_date, "%Y-%m-%d")
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
    except (TypeError, ValueError):
        return False

    if current < start:
        return False
    if end and current > end:
        return False
    if todo_type == "weekly":
        return rule.unit == "weekly" and rule.weekday is not None and current.weekday() == rule.weekday
    if todo_type == "monthly":
        return rule.unit == "monthly" and rule.day_of_month is not None and current.day == rule.day_of_month
    if todo_type == "yearly":
        return (
            rule.unit == "yearly"
            and rule.month is not None
            and rule.day is not None
            and current.month == rule.month
            and current.day == rule.day
        )
    return False


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _safe_replace_year(value: datetime, year: int) -> datetime:
    day = min(value.day, monthrange(year, value.month)[1])
    return value.replace(year=year, day=day)
