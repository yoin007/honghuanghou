# -*- coding: utf-8 -*-
"""
点滴记录 API - 教师私人记录，只能查看自己的记录
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime, timezone, timedelta

# 东八区时区
GMT8 = timezone(timedelta(hours=8))

from .base import (
    get_moral_db,
    get_current_user,
    log_operation,
    get_current_semester,
    get_student_class_snapshot,
    check_moral_permission_for_roles,
    get_api_scoped_user_roles,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
    record_action_flags,
    target_student_in_scope,
)
from models.datas_api.auth import User

router = APIRouter(prefix="/moment-records", tags=["点滴记录"])

API_MOMENT_LIST = "/api/moral/moment-records"
API_MOMENT_CREATE = "/api/moral/moment-records/create"
API_MOMENT_UPDATE = "/api/moral/moment-records/update"
API_MOMENT_DELETE = "/api/moral/moment-records/delete"


def _has_scoped_permission(db, user: User, api_path: str, permission: str) -> bool:
    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    return check_moral_permission_for_roles(scoped_roles, permission)


def _has_scoped_any_permission(db, user: User, api_path: str, permissions: List[str]) -> bool:
    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    return any(check_moral_permission_for_roles(scoped_roles, permission) for permission in permissions)


MOMENT_ALL_PERMISSIONS = ['moment_view_all', 'moral_record_manage', 'report_view_all']
MOMENT_OWN_CLASS_PERMISSIONS = ['moral_record_own_class', 'report_view_own_class']
MOMENT_OWN_PERMISSIONS = ['moment_create', 'moment_view_own']


def _moment_view_scope(db, user: User, api_path: str = API_MOMENT_LIST) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=MOMENT_ALL_PERMISSIONS,
        own_class_permissions=MOMENT_OWN_CLASS_PERMISSIONS,
        own_permissions=MOMENT_OWN_PERMISSIONS,
    )


def _moment_own_action_scope(db, user: User, api_path: str) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['moment_view_all', 'moral_record_manage'],
        own_class_permissions=[],
        own_permissions=['moment_create', 'moment_view_own'],
    )


class MomentRecordCreate(BaseModel):
    """创建点滴记录"""
    student_id: str = Field(..., description="学生学号")
    content: str = Field(..., description="记录内容")
    record_date: Optional[date] = Field(None, description="记录日期，不传则默认今天")
    record_type: str = Field(default="moment", description="记录类型")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")

    def validate_record_date(self, current_date: date) -> date:
        """验证记录日期不能超过今天"""
        record_date = self.record_date or current_date
        if record_date > current_date:
            raise ValueError("记录日期不能超过今天")
        return record_date


class MomentRecordUpdate(BaseModel):
    """更新点滴记录"""
    content: Optional[str] = Field(None, description="记录内容")
    record_date: Optional[date] = Field(None, description="记录日期")
    record_type: Optional[str] = Field(None, description="记录类型")
    tags: Optional[List[str]] = Field(None, description="标签列表")


@router.get("", summary="获取点滴记录列表")
async def get_moment_records(
    student_id: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    record_type: Optional[str] = Query(None),
    scope: Optional[str] = Query(None, description="数据范围: own(我创建的), own_class(我的班级), own_grade(我的年级), all(全校)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    user: User = Depends(get_current_user)
):
    """
    获取点滴记录列表

    权限说明：
    - teacher: 只能查看自己创建的记录 (scope=own)
    - cleader: 可以查看自己创建的和本班记录 (scope=own/own_class)
    - g_leader: 可以查看自己创建的和本年级记录 (scope=own/own_grade)
    - admin/jiaowu/xuefa: 可以查看全部记录 (scope=all)

    scope参数用于主动切换数据范围，后端会校验越权。
    """
    with get_moral_db() as db:
        conditions = ["mr.is_private = 1"]
        params = []

        view_scope = _moment_view_scope(db, user)

        # 如果指定了 scope 参数，进行越权校验并调整数据范围
        if scope:
            # 越权校验
            scope_allowed = False
            if scope == "own" and view_scope.get("can_own"):
                scope_allowed = True
            elif scope == "own_class" and view_scope.get("can_own_class"):
                scope_allowed = True
            elif scope == "own_grade" and view_scope.get("can_own_grade"):
                scope_allowed = True
            elif scope == "all" and view_scope.get("can_all"):
                scope_allowed = True

            if not scope_allowed:
                raise HTTPException(403, f"无权访问 scope={scope} 的数据")

            # 构造仅包含指定 scope 的过滤条件
            scope_conditions = []
            scope_params = []

            if scope == "own":
                scope_conditions.append("mr.recorder = ?")
                scope_params.append(user.username)
            elif scope == "own_class" and view_scope.get("my_class_id"):
                scope_conditions.append("mr.class_id = ?")
                scope_params.append(view_scope["my_class_id"])
            elif scope == "own_grade":
                my_grade_class_ids = view_scope.get("my_grade_class_ids") or []
                if my_grade_class_ids:
                    placeholders = ", ".join(["?"] * len(my_grade_class_ids))
                    scope_conditions.append(f"mr.class_id IN ({placeholders})")
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
                table_alias="mr",
                username=user.username,
            )

        if student_id:
            conditions.append("mr.student_id = ?")
            params.append(student_id)

        if start_date:
            conditions.append("mr.record_date >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("mr.record_date <= ?")
            params.append(end_date)

        if record_type:
            conditions.append("mr.record_type = ?")
            params.append(record_type)

        where_clause = " AND ".join(conditions)

        # 查询总数
        count_query = f"SELECT COUNT(*) FROM moment_record mr WHERE {where_clause}"
        total = db.query_value(count_query, tuple(params))

        # 分页查询
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT mr.*, s.name as student_name, c.class_name, g.grade_name,
                   t.name as recorder_name
            FROM moment_record mr
            JOIN student s ON mr.student_id = s.student_id
            JOIN class c ON mr.class_id = c.class_id
            JOIN grade g ON mr.grade_id = g.grade_id
            LEFT JOIN teacher t ON mr.recorder = t.name
            WHERE {where_clause}
            ORDER BY mr.record_date DESC, mr.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        records = db.query_all(data_query, tuple(params))
        edit_scope = _moment_own_action_scope(db, user, API_MOMENT_UPDATE)
        delete_scope = _moment_own_action_scope(db, user, API_MOMENT_DELETE)
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
                "page_size": page_size
            }
        }


@router.post("", summary="创建点滴记录")
async def create_moment_record(
    record: MomentRecordCreate,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    创建点滴记录

    权限要求：
    - teacher/cleader/xuefa/jiaowu/admin 可创建
    """
    with get_moral_db() as db:
        if not _has_scoped_permission(db, user, API_MOMENT_CREATE, 'moment_create'):
            raise HTTPException(403, "权限不足：需要点滴记录创建权限")

        # 获取当前东八区日期
        current_date_gmt8 = datetime.now(GMT8).date()

        # 验证并设置记录日期（默认今天，不能超过今天）
        try:
            record_date = record.validate_record_date(current_date_gmt8)
        except ValueError as e:
            raise HTTPException(400, str(e))

        # 获取学生班级信息
        student_info = get_student_class_snapshot(db, record.student_id)
        if not student_info:
            raise HTTPException(404, f"学生 {record.student_id} 不存在或不在校")
        if not target_student_in_scope(db, user, API_MOMENT_CREATE, student_info):
            raise HTTPException(403, "不能给授权范围外的学生创建点滴记录")

        # 获取当前学期
        current_semester = get_current_semester(db)
        semester_id = current_semester['semester_id'] if current_semester else None

        # 处理标签
        tags_json = None
        if record.tags:
            import json
            tags_json = json.dumps(record.tags)

        # 创建记录
        db.execute("""
            INSERT INTO moment_record
            (student_id, class_id, grade_id, recorder, record_type, content, record_date, tags, semester_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.student_id,
            student_info['class_id'],
            student_info['grade_id'],
            user.username,
            record.record_type,
            record.content,
            record_date,
            tags_json,
            semester_id
        ))

        log_operation(
            db, user.username, user.role, 'CREATE', 'moment_record',
            record.student_id,
            new_data=record.dict(),
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "点滴记录创建成功"}


@router.put("/{record_id}", summary="更新点滴记录")
async def update_moment_record(
    record_id: int,
    update_data: MomentRecordUpdate,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    更新点滴记录

    权限说明：
    - 只能更新自己创建的记录
    """
    with get_moral_db() as db:
        action_scope = _moment_own_action_scope(db, user, API_MOMENT_UPDATE)
        if not action_scope.get("can_all") and not action_scope.get("can_own"):
            raise HTTPException(403, "权限不足：需要点滴记录权限")

        # 查询记录
        record = db.query_one(
            "SELECT * FROM moment_record WHERE record_id = ?",
            (record_id,)
        )
        if not record:
            raise HTTPException(404, "记录不存在")

        if not record_in_scope(record, action_scope, username=user.username):
            raise HTTPException(403, "只能编辑自己创建的记录")

        # 构建更新
        updates = []
        params = []

        if update_data.content is not None:
            updates.append("content = ?")
            params.append(update_data.content)

        if update_data.record_date is not None:
            updates.append("record_date = ?")
            params.append(update_data.record_date)

        if update_data.record_type is not None:
            updates.append("record_type = ?")
            params.append(update_data.record_type)

        if update_data.tags is not None:
            import json
            updates.append("tags = ?")
            params.append(json.dumps(update_data.tags))

        if not updates:
            return {"success": True, "message": "无需更新"}

        updates.append("updated_at = datetime('now', 'localtime')")
        params.append(record_id)

        sql = f"UPDATE moment_record SET {', '.join(updates)} WHERE record_id = ?"
        db.execute(sql, tuple(params))

        log_operation(
            db, user.username, user.role, 'UPDATE', 'moment_record', record_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "记录更新成功"}


@router.delete("/{record_id}", summary="删除点滴记录")
async def delete_moment_record(
    record_id: int,
    request: Request,
    user: User = Depends(get_current_user)
):
    """
    删除点滴记录

    权限说明：
    - 只能删除自己创建的记录
    """
    with get_moral_db() as db:
        action_scope = _moment_own_action_scope(db, user, API_MOMENT_DELETE)
        if not action_scope.get("can_all") and not action_scope.get("can_own"):
            raise HTTPException(403, "权限不足：需要点滴记录权限")

        # 查询记录
        record = db.query_one(
            "SELECT * FROM moment_record WHERE record_id = ?",
            (record_id,)
        )
        if not record:
            raise HTTPException(404, "记录不存在")

        if not record_in_scope(record, action_scope, username=user.username):
            raise HTTPException(403, "只能删除自己创建的记录")

        db.execute("DELETE FROM moment_record WHERE record_id = ?", (record_id,))

        log_operation(
            db, user.username, user.role, 'DELETE', 'moment_record', record_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "记录删除成功"}
