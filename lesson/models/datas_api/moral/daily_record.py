# -*- coding: utf-8 -*-
"""
日常表现记录 API

提供日常表现记录的增删改查功能
"""

import logging
from datetime import date, datetime, timezone, timedelta
from typing import Optional, List
import json

# 东八区时区
GMT8 = timezone(timedelta(hours=8))

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .api_permission import require_configured_api_permission
from .base import (
    get_moral_db,
    check_moral_permission,
    check_class_access,
    get_current_semester,
    get_student_class_snapshot,
    log_operation,
    BaseResponse,
    PaginationParams,
    PaginatedResponse,
        check_moral_permission_for_roles,
    get_api_scoped_user_roles,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
    record_action_flags,
    target_student_in_scope,
)
from .evaluation import calculate_evaluation
from .escalation import check_and_trigger_escalation
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/daily-records", tags=["日常表现"])

API_DAILY_LIST = "/api/moral/daily-records"
API_DAILY_CREATE = "/api/moral/daily-records/create"
API_DAILY_BATCH = "/api/moral/daily-records/batch"
API_DAILY_UPDATE = "/api/moral/daily-records/update"
API_DAILY_DELETE = "/api/moral/daily-records/delete"
API_DAILY_STATS = "/api/moral/daily-records/statistics/student/{student_id}"


def _has_scoped_permission(db, user: User, api_path: str, permission: str) -> bool:
    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    return check_moral_permission_for_roles(scoped_roles, permission)


def _has_scoped_any_permission(db, user: User, api_path: str, permissions: List[str]) -> bool:
    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    return any(check_moral_permission_for_roles(scoped_roles, permission) for permission in permissions)


DAILY_ALL_PERMISSIONS = ['report_view_all', 'moral_record_manage']
DAILY_OWN_CLASS_PERMISSIONS = ['moral_record_own_class', 'report_view_own_class']
DAILY_OWN_PERMISSIONS = ['moral_record_input', 'moral_record_view_own']


def _daily_view_scope(db, user: User, api_path: str = API_DAILY_LIST) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=DAILY_ALL_PERMISSIONS,
        own_class_permissions=DAILY_OWN_CLASS_PERMISSIONS,
        own_permissions=DAILY_OWN_PERMISSIONS,
    )


def _daily_own_action_scope(db, user: User, api_path: str) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['moral_record_manage'],
        own_class_permissions=[],
        own_permissions=['moral_record_input', 'moral_record_view_own'],
    )


# =============================================================================
# Pydantic 模型
# =============================================================================

class DailyRecordCreate(BaseModel):
    """创建日常表现记录"""
    student_id: str = Field(..., description="学号")
    event_id: int = Field(..., description="事件类型ID")
    record_date: Optional[datetime] = Field(None, description="记录时间（精确到分钟），不传则默认当前时间")
    remark: Optional[str] = Field(None, description="备注")

    def validate_record_date(self, current_time: datetime) -> datetime:
        """验证记录时间不能超过当前时间"""
        record_date = self.record_date or current_time
        if record_date > current_time:
            raise ValueError("记录时间不能超过当前时间")
        return record_date


class DailyRecordUpdate(BaseModel):
    """更新日常表现记录"""
    event_id: Optional[int] = Field(None, description="事件类型ID")
    record_date: Optional[datetime] = Field(None, description="记录时间")
    remark: Optional[str] = Field(None, description="备注")
    is_deleted: Optional[int] = Field(None, description="是否删除")


class DailyRecordResponse(BaseModel):
    """日常表现记录响应"""
    record_id: int
    student_id: str
    student_name: str
    event_name: str
    event_type: int
    score: int
    record_date: str  # 存储格式：YYYY-MM-DD HH:MM
    class_name: str
    remark: Optional[str]
    recorder: Optional[str]
    created_at: datetime


class DailyEventTypeCreate(BaseModel):
    """创建日常事件类型"""
    event_name: str = Field(..., description="事件名称", max_length=50)
    event_type: int = Field(..., description="事件类型：1=积极，2=消极", ge=1, le=2)
    score: int = Field(..., description="分值（正数加分，负数扣分）")
    description: Optional[str] = Field(None, description="描述", max_length=200)


class DailyEventTypeUpdate(BaseModel):
    """更新日常事件类型"""
    event_name: Optional[str] = Field(None, description="事件名称", max_length=50)
    event_type: Optional[int] = Field(None, description="事件类型：1=积极，2=消极")
    score: Optional[int] = Field(None, description="分值")
    description: Optional[str] = Field(None, description="描述", max_length=200)
    is_active: Optional[int] = Field(None, description="是否启用：1=启用，0=禁用")


# =============================================================================
# API 路由
# =============================================================================

@router.get("/types", summary="获取日常事件类型列表")
async def get_daily_event_types(
    event_type: Optional[int] = Query(None, description="事件类型：1=积极，2=消极"),
    is_active: Optional[int] = Query(None, description="是否启用：不传返回全部，1=启用，0=禁用"),
    user: User = Depends(require_configured_api_permission("/api/moral/daily-records/types", "GET", allow_missing=False))
):
    """获取日常事件类型列表"""
    with get_moral_db() as db:
        query = "SELECT * FROM daily_event_type WHERE 1=1"
        params = []

        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)

        if is_active is not None:
            query += " AND is_active = ?"
            params.append(is_active)

        query += " ORDER BY event_type, score DESC"

        events = db.query_all(query, tuple(params) if params else None)

        return {"success": True, "data": events}


@router.get("", summary="获取日常表现记录列表")
async def get_daily_records(
    student_id: Optional[str] = Query(None, description="学号"),
    class_id: Optional[int] = Query(None, description="班级ID"),
    grade_id: Optional[int] = Query(None, description="级号ID"),
    semester_id: Optional[int] = Query(None, description="学期ID"),
    event_type: Optional[int] = Query(None, description="事件类型"),
    event_id: Optional[int] = Query(None, description="具体事件ID"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    remark: Optional[str] = Query(None, description="备注模糊过滤"),
    scope: Optional[str] = Query(None, description="数据范围: own(我创建的), managed_classes(管理班级), managed_grades(管理年级), all(全校)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    user: User = Depends(require_configured_api_permission(API_DAILY_LIST, "GET", allow_missing=False))
):
    """
    获取日常表现记录列表

    权限说明：
    - teacher: 只能查看自己创建的记录 (scope=own)
    - cleader: 可以查看自己创建的和管理班级记录 (scope=own/managed_classes)
    - g_leader: 可以查看自己创建的和管理年级记录 (scope=own/managed_grades)
    - admin/jiaowu/xuefa: 可以查看全部记录 (scope=all)

    scope参数用于主动切换数据范围，后端会校验越权。
    """
    with get_moral_db() as db:
        # 获取当前学期
        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        # 构建查询条件
        conditions = ["dr.is_deleted = 0"]
        params = []

        if student_id:
            conditions.append("dr.student_id = ?")
            params.append(student_id)

        if class_id:
            conditions.append("dr.class_id = ?")
            params.append(class_id)

        if grade_id:
            conditions.append("dr.grade_id = ?")
            params.append(grade_id)

        if semester_id:
            conditions.append("dr.semester_id = ?")
            params.append(semester_id)

        if event_type is not None:
            conditions.append("de.event_type = ?")
            params.append(event_type)

        if event_id is not None:
            conditions.append("dr.event_id = ?")
            params.append(event_id)

        if start_date:
            conditions.append("dr.record_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("dr.record_date <= ?")
            params.append(end_date)

        if remark:
            conditions.append("dr.remark LIKE ?")
            params.append(f"%{remark}%")

        # 权限过滤：API 控制入口，数据范围控制能查看哪些记录。
        view_scope = _daily_view_scope(db, user)

        # 如果指定了 scope 参数，进行越权校验并调整数据范围
        if scope:
            # 越权校验
            scope_allowed = False
            if scope == "own" and view_scope.get("can_own"):
                scope_allowed = True
            elif scope in ("own_class", "managed_classes") and view_scope.get("can_own_class"):
                scope_allowed = True
            elif scope in ("own_grade", "managed_grades") and view_scope.get("can_own_grade"):
                scope_allowed = True
            elif scope == "all" and view_scope.get("can_all"):
                scope_allowed = True

            if not scope_allowed:
                raise HTTPException(403, f"无权访问 scope={scope} 的数据")

            # 构造仅包含指定 scope 的过滤条件
            scope_conditions = []
            scope_params = []

            if scope == "own":
                scope_conditions.append("dr.recorder = ?")
                scope_params.append(user.username)
            elif scope in ("own_class", "managed_classes"):
                my_class_ids = view_scope.get("my_class_ids") or []
                if my_class_ids:
                    placeholders = ", ".join(["?"] * len(my_class_ids))
                    scope_conditions.append(f"dr.class_id IN ({placeholders})")
                    scope_params.extend(my_class_ids)
                elif view_scope.get("my_class_id"):
                    scope_conditions.append("dr.class_id = ?")
                    scope_params.append(view_scope["my_class_id"])
                else:
                    scope_conditions.append("1 = 0")
            elif scope in ("own_grade", "managed_grades"):
                my_grade_class_ids = view_scope.get("my_grade_class_ids") or []
                if my_grade_class_ids:
                    placeholders = ", ".join(["?"] * len(my_grade_class_ids))
                    scope_conditions.append(f"dr.class_id IN ({placeholders})")
                    scope_params.extend(my_grade_class_ids)
                else:
                    scope_conditions.append("1 = 0")
            elif scope == "all":
                # 全部权限，不加限制
                pass

            if scope_conditions:
                conditions.append("(" + " OR ".join(scope_conditions) + ")")
                params.extend(scope_params)
        else:
            # 未指定 scope，使用默认权限范围
            append_record_scope_condition(
                conditions,
                params,
                view_scope,
                table_alias="dr",
                username=user.username,
            )

        where_clause = " AND ".join(conditions)

        # 查询总数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM student_daily_record dr
            JOIN student s ON dr.student_id = s.student_id
            JOIN daily_event_type de ON dr.event_id = de.event_id
            JOIN class c ON dr.class_id = c.class_id
            WHERE {where_clause}
        """
        total = db.query_value(count_query, tuple(params))

        # 分页查询
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT dr.*, s.name as student_name, de.event_name, de.event_type,
                   c.class_name, g.grade_name, t.name as recorder_name
            FROM student_daily_record dr
            JOIN student s ON dr.student_id = s.student_id
            JOIN daily_event_type de ON dr.event_id = de.event_id
            JOIN class c ON dr.class_id = c.class_id
            JOIN grade g ON dr.grade_id = g.grade_id
            LEFT JOIN teacher t ON dr.recorder = t.name
            WHERE {where_clause}
            ORDER BY dr.record_date DESC, dr.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        records = db.query_all(data_query, tuple(params))
        edit_scope = _daily_own_action_scope(db, user, API_DAILY_UPDATE)
        delete_scope = _daily_own_action_scope(db, user, API_DAILY_DELETE)
        for record_item in records:
            record_item.update(record_action_flags(
                record_item,
                edit_scope,
                delete_scope,
                username=user.username,
            ))

        return {
            "success": True,
            "data": {
                "items": records,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }


@router.post("", summary="创建日常表现记录")
async def create_daily_record(
    record: DailyRecordCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_DAILY_CREATE, "POST", allow_missing=False))
):
    """
    创建日常表现记录

    权限要求：
    - teacher/cleader/xuefa/jiaowu/admin 可录入
    """
    with get_moral_db() as db:
        if not _has_scoped_permission(db, user, API_DAILY_CREATE, 'moral_record_input'):
            raise HTTPException(403, "权限不足：需要日常表现录入权限")

        # 获取当前东八区时间
        current_time_gmt8 = datetime.now(GMT8).replace(tzinfo=None)

        # 验证并设置记录时间（默认当前时间，不能超过当前时间）
        try:
            record_date = record.validate_record_date(current_time_gmt8)
        except ValueError as e:
            raise HTTPException(400, str(e))

        # 获取当前学期
        current_semester = get_current_semester(db)
        if not current_semester:
            raise HTTPException(400, "当前学期未配置")

        semester_id = current_semester['semester_id']

        # 获取学生班级信息
        student_info = get_student_class_snapshot(db, record.student_id)
        if not student_info:
            raise HTTPException(404, f"学生 {record.student_id} 不存在或不在校")
        if not target_student_in_scope(db, user, API_DAILY_CREATE, student_info):
            raise HTTPException(403, "不能给授权范围外的学生录入日常表现")

        class_id = student_info['class_id']
        grade_id = student_info['grade_id']

        # 获取事件类型
        event = db.query_one(
            "SELECT * FROM daily_event_type WHERE event_id = ? AND is_active = 1",
            (record.event_id,)
        )
        if not event:
            raise HTTPException(404, f"事件类型 {record.event_id} 不存在或已禁用")

        # 插入记录
        db.execute(
            """INSERT INTO student_daily_record
            (student_id, event_id, semester_id, record_date, class_id, grade_id, score, remark, recorder)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.student_id,
                record.event_id,
                semester_id,
                record_date.strftime('%Y-%m-%d %H:%M'),
                class_id,
                grade_id,
                event['score'],
                record.remark,
                user.username
            )
        )

        record_id = db.lastrowid()

        # 检查累进处罚（仅对消极事件）
        escalation_result = None
        if event['event_type'] == 2:
            escalation_result = check_and_trigger_escalation(
                db=db,
                student_id=record.student_id,
                event_id=record.event_id,
                record_id=record_id,
                record_date=record_date,
                semester_id=semester_id
            )

        # 记录操作日志
        log_operation(
            db, user.username, user.role, 'INSERT', 'student_daily_record',
            record_id, semester_id, new_data={
                'student_id': record.student_id,
                'event_id': record.event_id,
                'record_date': str(record.record_date),
                'remark': record.remark,
                'escalation_triggered': escalation_result.triggered if escalation_result else False
            },
            ip_address=request.client.host if request.client else None
        )

        # 重新计算德育评价总分
        calculate_evaluation(db, record.student_id, semester_id, class_id, grade_id)

        # 构建返回数据
        response_data = {"record_id": record_id}
        response_message = "记录创建成功"

        if escalation_result and escalation_result.triggered:
            response_data["escalation"] = {
                "triggered": True,
                "action": escalation_result.action,
                "description": escalation_result.description,
                "threshold": escalation_result.threshold,
                "current_count": escalation_result.current_count,
                "score_penalty": escalation_result.score_penalty,
                "message": escalation_result.message,
                "punishment_id": escalation_result.punishment_id,
                "student_name": student_info.get('name', record.student_id),
                "event_name": event['event_name']
            }
            response_message = f"记录创建成功，触发累进处罚：{student_info.get('name', record.student_id)}（{record.student_id}）{event['event_name']} → {escalation_result.description}"

        return {"success": True, "message": response_message, "data": response_data}


@router.post("/batch", summary="批量创建日常表现记录")
async def batch_create_daily_records(
    records: List[DailyRecordCreate],
    request: Request,
    user: User = Depends(require_configured_api_permission(API_DAILY_BATCH, "POST", allow_missing=False))
):
    """
    批量创建日常表现记录

    权限要求：cleader/xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        if not _has_scoped_permission(db, user, API_DAILY_BATCH, 'moral_record_manage'):
            raise HTTPException(403, "权限不足：需要日常表现批量录入权限")

        # 获取当前东八区时间
        current_time_gmt8 = datetime.now(GMT8).replace(tzinfo=None)

        current_semester = get_current_semester(db)
        if not current_semester:
            raise HTTPException(400, "当前学期未配置")

        semester_id = current_semester['semester_id']
        success_count = 0
        errors = []
        escalation_results = []  # 收集累进结果
        affected_students = {}

        for i, record in enumerate(records):
            try:
                # 验证并设置记录时间
                try:
                    record_date = record.validate_record_date(current_time_gmt8)
                except ValueError as e:
                    errors.append(f"第{i+1}条：{str(e)}")
                    continue

                # 获取学生班级信息
                student_info = get_student_class_snapshot(db, record.student_id)
                if not student_info:
                    errors.append(f"第{i+1}条：学生 {record.student_id} 不存在")
                    continue
                if not target_student_in_scope(db, user, API_DAILY_BATCH, student_info):
                    errors.append(f"第{i+1}条：不能给授权范围外的学生录入日常表现")
                    continue

                # 获取事件类型
                event = db.query_one(
                    "SELECT * FROM daily_event_type WHERE event_id = ? AND is_active = 1",
                    (record.event_id,)
                )
                if not event:
                    errors.append(f"第{i+1}条：事件类型不存在")
                    continue

                # 插入记录
                db.execute(
                    """INSERT INTO student_daily_record
                    (student_id, event_id, semester_id, record_date, class_id, grade_id, score, remark, recorder)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record.student_id,
                        record.event_id,
                        semester_id,
                        record_date.strftime('%Y-%m-%d %H:%M'),
                        student_info['class_id'],
                        student_info['grade_id'],
                        event['score'],
                        record.remark,
                        user.username
                    )
                )
                record_id = db.lastrowid()
                success_count += 1
                affected_students[record.student_id] = (
                    student_info['class_id'],
                    student_info['grade_id'],
                )

                # 检查累进处罚（仅对消极事件）
                if event['event_type'] == 2:
                    escalation_result = check_and_trigger_escalation(
                        db=db,
                        student_id=record.student_id,
                        event_id=record.event_id,
                        record_id=record_id,
                        record_date=record_date,
                        semester_id=semester_id
                    )
                    if escalation_result.triggered:
                        escalation_results.append({
                            "student_id": record.student_id,
                            "student_name": student_info.get('name', ''),
                            "event_name": event['event_name'],
                            "action": escalation_result.action,
                            "description": escalation_result.description,
                            "threshold": escalation_result.threshold,
                            "current_count": escalation_result.current_count,
                            "message": f"{student_info.get('name', record.student_id)}（{record.student_id}）{event['event_name']} → {escalation_result.description}"
                        })

            except Exception as e:
                errors.append(f"第{i+1}条：{str(e)}")

        for student_id, (class_id, grade_id) in affected_students.items():
            calculate_evaluation(db, student_id, semester_id, class_id, grade_id)

        message = f"成功创建 {success_count} 条记录"
        if escalation_results:
            message += f"，触发 {len(escalation_results)} 次累进处罚"

        return {
            "success": True,
            "message": message,
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "errors": errors[:20],
                "escalations": escalation_results[:20]  # 返回触发信息
            }
        }


@router.put("/{record_id}", summary="更新日常表现记录")
async def update_daily_record(
    record_id: int,
    update_data: DailyRecordUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_DAILY_UPDATE, "PUT", allow_missing=False))
):
    """更新日常表现记录"""
    with get_moral_db() as db:
        action_scope = _daily_own_action_scope(db, user, API_DAILY_UPDATE)
        if not action_scope.get("can_all") and not action_scope.get("can_own"):
            raise HTTPException(403, "权限不足：需要日常表现记录权限")

        # 获取原记录
        old_record = db.query_one(
            "SELECT * FROM student_daily_record WHERE record_id = ?",
            (record_id,)
        )
        if not old_record:
            raise HTTPException(404, "记录不存在")

        if not record_in_scope(old_record, action_scope, username=user.username):
            raise HTTPException(403, "只能编辑自己创建的记录")

        # 构建更新语句
        updates = []
        params = []
        new_event = None

        if update_data.event_id is not None:
            # 获取新事件类型
            new_event = db.query_one(
                "SELECT * FROM daily_event_type WHERE event_id = ? AND is_active = 1",
                (update_data.event_id,)
            )
            if not new_event:
                raise HTTPException(404, f"事件类型 {update_data.event_id} 不存在或已禁用")
            updates.append("event_id = ?")
            params.append(update_data.event_id)
            updates.append("score = ?")
            params.append(new_event['score'])

        if update_data.record_date is not None:
            # 验证记录时间不能超过当前时间
            current_time_gmt8 = datetime.now(GMT8).replace(tzinfo=None)
            if update_data.record_date > current_time_gmt8:
                raise HTTPException(400, "记录时间不能超过当前时间")
            updates.append("record_date = ?")
            params.append(update_data.record_date.strftime('%Y-%m-%d %H:%M'))

        if update_data.remark is not None:
            updates.append("remark = ?")
            params.append(update_data.remark)

        if update_data.is_deleted is not None:
            updates.append("is_deleted = ?")
            params.append(update_data.is_deleted)

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(record_id)
        db.execute(
            f"UPDATE student_daily_record SET {', '.join(updates)} WHERE record_id = ?",
            tuple(params)
        )

        # 记录操作日志
        old_data = {'remark': old_record['remark']}
        new_data = {'remark': update_data.remark}
        if update_data.event_id is not None:
            old_data['event_id'] = old_record['event_id']
            new_data['event_id'] = update_data.event_id
        if update_data.record_date is not None:
            old_data['record_date'] = old_record['record_date']
            new_data['record_date'] = str(update_data.record_date)
        log_operation(
            db, user.username, user.role, 'UPDATE', 'student_daily_record',
            record_id, old_record['semester_id'],
            old_data=old_data,
            new_data=new_data,
            ip_address=request.client.host if request.client else None
        )

        # 重新计算德育评价总分
        calculate_evaluation(db, old_record['student_id'], old_record['semester_id'],
                             old_record['class_id'], old_record['grade_id'])

        return {"success": True, "message": "记录更新成功"}


@router.delete("/{record_id}", summary="删除日常表现记录")
async def delete_daily_record(
    record_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_DAILY_DELETE, "DELETE", allow_missing=False))
):
    """
    删除日常表现记录（软删除）

    删除后会重新计算德育评价总分
    """
    with get_moral_db() as db:
        action_scope = _daily_own_action_scope(db, user, API_DAILY_DELETE)
        if not action_scope.get("can_all") and not action_scope.get("can_own"):
            raise HTTPException(403, "权限不足：需要日常表现记录权限")

        # 获取原记录
        old_record = db.query_one(
            "SELECT * FROM student_daily_record WHERE record_id = ?",
            (record_id,)
        )

        if not old_record:
            raise HTTPException(404, "记录不存在")

        if not record_in_scope(old_record, action_scope, username=user.username):
            raise HTTPException(403, "只能删除自己创建的记录")

        # 软删除
        db.execute(
            "UPDATE student_daily_record SET is_deleted = 1 WHERE record_id = ?",
            (record_id,)
        )

        # 重新计算德育评价总分（替代手动回退）
        calculate_evaluation(db, old_record['student_id'], old_record['semester_id'],
                             old_record['class_id'], old_record['grade_id'])

        # 检查关联处分是否需要复核
        check_related_punishments(db, record_id, old_record['student_id'], old_record['event_id'], old_record['semester_id'])

        # 记录操作日志
        log_operation(
            db, user.username, user.role, 'DELETE', 'student_daily_record',
            record_id, old_record['semester_id'],
            old_data=old_record,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "记录已删除，总分已重新计算"}


@router.get("/statistics/student/{student_id}", summary="获取学生日常表现统计")
async def get_student_daily_statistics(
    student_id: str,
    semester_id: Optional[int] = Query(None),
    user: User = Depends(require_configured_api_permission(API_DAILY_STATS, "GET", allow_missing=False))
):
    """获取学生日常表现统计"""
    with get_moral_db() as db:
        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        scope = _daily_view_scope(db, user, API_DAILY_STATS)
        conditions = ["dr.student_id = ?", "dr.semester_id = ?", "dr.is_deleted = 0"]
        params = [student_id, semester_id]
        append_record_scope_condition(
            conditions,
            params,
            scope,
            table_alias="dr",
            username=user.username,
        )
        where_clause = " AND ".join(conditions)

        # 统计积极事件
        positive = db.query_one(
            f"""SELECT COUNT(*) as count, SUM(dr.score) as total_score
            FROM student_daily_record dr
            JOIN daily_event_type de ON dr.event_id = de.event_id
            WHERE {where_clause}
            AND de.event_type = 1""",
            tuple(params)
        )

        # 统计消极事件
        negative = db.query_one(
            f"""SELECT COUNT(*) as count, SUM(ABS(dr.score)) as total_score
            FROM student_daily_record dr
            JOIN daily_event_type de ON dr.event_id = de.event_id
            WHERE {where_clause}
            AND de.event_type = 2""",
            tuple(params)
        )

        # 按事件类型统计
        event_stats = db.query_all(
            f"""SELECT de.event_name, de.event_type, COUNT(*) as count, SUM(dr.score) as total_score
            FROM student_daily_record dr
            JOIN daily_event_type de ON dr.event_id = de.event_id
            WHERE {where_clause}
            GROUP BY de.event_id
            ORDER BY count DESC""",
            tuple(params)
        )

        return {
            "success": True,
            "data": {
                "positive": positive or {"count": 0, "total_score": 0},
                "negative": negative or {"count": 0, "total_score": 0},
                "by_event": event_stats
            }
        }


# =============================================================================
# 事件类型管理 API
# =============================================================================

@router.post("/types", summary="创建日常事件类型")
async def create_daily_event_type(
    event_type: DailyEventTypeCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission("/api/moral/daily-records/types", "GET", allow_missing=False))
):
    """
    创建日常事件类型

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        # 检查是否已存在同名事件
        existing = db.query_one(
            "SELECT event_id FROM daily_event_type WHERE event_name = ?",
            (event_type.event_name,)
        )
        if existing:
            raise HTTPException(400, f"事件类型 '{event_type.event_name}' 已存在")

        # 根据事件类型确定分值正负
        score = abs(event_type.score) if event_type.event_type == 1 else -abs(event_type.score)

        db.execute(
            """INSERT INTO daily_event_type (event_name, event_type, score, description, is_active)
            VALUES (?, ?, ?, ?, 1)""",
            (event_type.event_name, event_type.event_type, score, event_type.description)
        )

        event_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'daily_event_type', event_id,
            new_data={'event_name': event_type.event_name, 'score': score},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "事件类型创建成功", "data": {"event_id": event_id}}


@router.put("/types/{type_id}", summary="更新日常事件类型")
async def update_daily_event_type(
    type_id: int,
    update_data: DailyEventTypeUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission("/api/moral/daily-records/types", "GET", allow_missing=False))
):
    """
    更新日常事件类型

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        # 获取原记录
        old_type = db.query_one(
            "SELECT * FROM daily_event_type WHERE event_id = ?",
            (type_id,)
        )
        if not old_type:
            raise HTTPException(404, "事件类型不存在")

        # 构建更新语句
        updates = []
        params = []

        if update_data.event_name is not None:
            # 检查名称是否重复
            existing = db.query_one(
                "SELECT event_id FROM daily_event_type WHERE event_name = ? AND event_id != ?",
                (update_data.event_name, type_id)
            )
            if existing:
                raise HTTPException(400, f"事件类型 '{update_data.event_name}' 已存在")
            updates.append("event_name = ?")
            params.append(update_data.event_name)

        # 获取最终的事件类型（新值或原值）
        final_event_type = update_data.event_type if update_data.event_type is not None else old_type['event_type']

        if update_data.event_type is not None:
            updates.append("event_type = ?")
            params.append(update_data.event_type)

        if update_data.score is not None:
            # 分值正负与事件类型一致
            score = abs(update_data.score) if final_event_type == 1 else -abs(update_data.score)
            updates.append("score = ?")
            params.append(score)

        if update_data.description is not None:
            updates.append("description = ?")
            params.append(update_data.description)

        if update_data.is_active is not None:
            updates.append("is_active = ?")
            params.append(update_data.is_active)

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(type_id)
        db.execute(
            f"UPDATE daily_event_type SET {', '.join(updates)} WHERE event_id = ?",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'daily_event_type', type_id,
            old_data={'event_name': old_type['event_name']},
            new_data=update_data.dict(exclude_unset=True),
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "事件类型更新成功"}


@router.delete("/types/{type_id}", summary="删除日常事件类型")
async def delete_daily_event_type(
    type_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission("/api/moral/daily-records/types", "GET", allow_missing=False))
):
    """
    删除日常事件类型（软删除，设为禁用状态）

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        # 获取原记录
        old_type = db.query_one(
            "SELECT * FROM daily_event_type WHERE event_id = ?",
            (type_id,)
        )
        if not old_type:
            raise HTTPException(404, "事件类型不存在")

        # 检查是否有关联记录
        record_count = db.query_value(
            "SELECT COUNT(*) FROM student_daily_record WHERE event_id = ?",
            (type_id,)
        )

        if record_count > 0:
            # 有关联记录，只禁用不删除
            db.execute(
                "UPDATE daily_event_type SET is_active = 0 WHERE event_id = ?",
                (type_id,)
            )
            log_operation(
                db, user.username, user.role, 'DISABLE', 'daily_event_type', type_id,
                old_data={'event_name': old_type['event_name']},
                ip_address=request.client.host if request.client else None
            )
            return {"success": True, "message": f"该事件类型有 {record_count} 条关联记录，已禁用"}
        else:
            # 无关联记录，直接删除
            db.execute(
                "DELETE FROM daily_event_type WHERE event_id = ?",
                (type_id,)
            )
            log_operation(
                db, user.username, user.role, 'DELETE', 'daily_event_type', type_id,
                old_data={'event_name': old_type['event_name']},
                ip_address=request.client.host if request.client else None
            )
            return {"success": True, "message": "事件类型已删除"}


class DailyEventImportItem(BaseModel):
    """批量导入日常事件类型项"""
    event_name: str
    event_type: str  # "积极" or "消极"
    score: int
    description: Optional[str] = ""


@router.post("/types/batch-import", summary="批量导入日常事件类型")
async def batch_import_daily_event_types(
    items: List[DailyEventImportItem],
    request: Request,
    user: User = Depends(require_configured_api_permission("/api/moral/daily-records/types", "GET", allow_missing=False))
):
    """
    批量导入日常事件类型

    权限要求：xuefa/jiaowu/admin

    CSV格式：
    事件名称,事件类型,分值,描述
    拾金不昧,积极,3,主动上交拾得物品
    """
    with get_moral_db() as db:
        success_count = 0
        skip_count = 0
        errors = []

        for i, item in enumerate(items):
            try:
                # 转换事件类型
                event_type_num = 1 if item.event_type == "积极" else 2

                # 检查是否已存在
                existing = db.query_one(
                    "SELECT event_id FROM daily_event_type WHERE event_name = ?",
                    (item.event_name,)
                )
                if existing:
                    skip_count += 1
                    continue

                # 根据事件类型确定分值正负
                score = abs(item.score) if event_type_num == 1 else -abs(item.score)

                db.execute(
                    """INSERT INTO daily_event_type (event_name, event_type, score, description, is_active)
                    VALUES (?, ?, ?, ?, 1)""",
                    (item.event_name, event_type_num, score, item.description or "")
                )
                success_count += 1

            except Exception as e:
                errors.append(f"第{i+1}条: {str(e)}")

        log_operation(
            db, user.username, user.role, 'BATCH_IMPORT', 'daily_event_type', None,
            new_data={'success_count': success_count, 'skip_count': skip_count},
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "message": f"成功导入 {success_count} 条，跳过 {skip_count} 条已存在记录",
            "data": {
                "success_count": success_count,
                "skip_count": skip_count,
                "error_count": len(errors),
                "errors": errors[:10]
            }
        }


# =============================================================================
# 处分复核检查函数
# =============================================================================

def check_related_punishments(db, record_id: int, student_id: str, event_id: int, semester_id: int):
    """
    检查记录删除后关联处分是否需要复核

    Args:
        db: 数据库连接
        record_id: 被删除的记录ID
        student_id: 学生ID
        event_id: 事件ID
        semester_id: 学期ID
    """
    import json

    # 1. 查找关联的处分记录（source_record_ids 包含该记录ID）
    punishments = db.query_all(
        """SELECT id, student_id, event_id, semester_id, source_record_ids, reason, is_revoked
        FROM punishment_record
        WHERE student_id = ? AND event_id = ? AND semester_id = ?
        AND is_revoked = 0 AND source_record_ids IS NOT NULL""",
        (student_id, event_id, semester_id)
    )

    for p in punishments:
        try:
            source_ids = json.loads(p['source_record_ids']) if p['source_record_ids'] else []
        except:
            source_ids = []

        if record_id not in source_ids:
            continue  # 该处分不关联此记录

        # 2. 从累进规则获取阈值
        rule = db.query_one(
            """SELECT escalation_rules FROM violation_escalation_rule WHERE event_id = ?""",
            (event_id,)
        )

        if not rule:
            continue

        try:
            rules_data = json.loads(rule['escalation_rules'])
            # 找到触发该处分的阈值（从reason解析或匹配action）
            threshold = None
            for r in rules_data.get('rules', []):
                # 匹配处分原因中的阈值描述
                if f"累计{r['threshold']}次" in p['reason'] or r.get('threshold'):
                    threshold = r['threshold']
                    break
        except:
            continue

        if not threshold:
            continue

        # 3. 计算当前有效累计次数（不含已删除记录）
        time_window_days = rule.get('time_window_days', 90) if rule else 90

        # 获取处分日期作为基准
        punishment_date = db.query_value(
            "SELECT punishment_date FROM punishment_record WHERE id = ?",
            (p['id'],)
        )

        if punishment_date:
            from datetime import datetime, timedelta
            try:
                base_date = datetime.strptime(punishment_date, '%Y-%m-%d').date()
            except:
                base_date = datetime.now().date()

            window_start = base_date - timedelta(days=time_window_days)

            valid_count = db.query_value(
                """SELECT COUNT(*) FROM student_daily_record
                WHERE student_id = ? AND event_id = ?
                AND strftime('%Y-%m-%d', record_date) >= ?
                AND strftime('%Y-%m-%d', record_date) <= ?
                AND is_deleted = 0""",
                (student_id, event_id, window_start.strftime('%Y-%m-%d'), base_date.strftime('%Y-%m-%d'))
            ) or 0
        else:
            valid_count = 0

        # 4. 判断是否仍达标
        if valid_count < threshold:
            # 标记待复核
            db.execute(
                """UPDATE punishment_record SET review_status = 1 WHERE id = ?""",
                (p['id'],)
            )
            logger.info(f"处分 {p['id']} 已标记待复核：有效次数 {valid_count} < 阈值 {threshold}")

            # 5. 发送通知给学发部（可选）
            # notify_xuefa_review_needed(db, p)
