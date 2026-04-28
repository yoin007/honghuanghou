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
    check_moral_permission,
    require_permission,
    log_operation,
    get_current_semester,
    get_student_class_snapshot,
)
from models.datas_api.auth import User

router = APIRouter(prefix="/moment-records", tags=["点滴记录"])


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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    user: User = Depends(get_current_user)
):
    """
    获取点滴记录列表

    权限说明：
    - teacher/cleader: 只能查看自己创建的记录
    - admin/jiaowu: 可以查看所有记录
    """
    with get_moral_db() as db:
        conditions = ["is_private = 1"]
        params = []

        # 核心权限过滤：只能看自己创建的记录
        if not check_moral_permission(user, 'moment_view_all'):
            conditions.append("recorder = %s")
            params.append(user.username)

        if student_id:
            conditions.append("student_id = %s")
            params.append(student_id)

        if start_date:
            conditions.append("record_date >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("record_date <= %s")
            params.append(end_date)

        if record_type:
            conditions.append("record_type = %s")
            params.append(record_type)

        where_clause = " AND ".join(conditions)

        # 查询总数
        count_query = f"SELECT COUNT(*) FROM moment_record WHERE {where_clause}"
        total = db.query_value(count_query, tuple(params))

        # 分页查询
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT mr.*, s.name as student_name, c.class_name, g.grade_name
            FROM moment_record mr
            JOIN student s ON mr.student_id = s.student_id
            JOIN class c ON mr.class_id = c.class_id
            JOIN grade g ON mr.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY mr.record_date DESC, mr.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        records = db.query_all(data_query, tuple(params))

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
    user: User = Depends(require_permission('moment_create'))
):
    """
    创建点滴记录

    权限要求：
    - teacher/cleader/xuefa/jiaowu/admin 可创建
    """
    with get_moral_db() as db:
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
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        if not check_moral_permission(user, 'moment_create') and not check_moral_permission(user, 'moment_view_all'):
            raise HTTPException(403, "权限不足：需要点滴记录权限")

        # 查询记录
        record = db.query_one(
            "SELECT * FROM moment_record WHERE record_id = %s",
            (record_id,)
        )
        if not record:
            raise HTTPException(404, "记录不存在")

        # 普通教师/班主任只能更新自己的记录，管理角色可更新全部记录
        if not check_moral_permission(user, 'moment_view_all') and record['recorder'] != user.username:
            raise HTTPException(403, "只能编辑自己创建的记录")

        # 构建更新
        updates = []
        params = []

        if update_data.content is not None:
            updates.append("content = %s")
            params.append(update_data.content)

        if update_data.record_date is not None:
            updates.append("record_date = %s")
            params.append(update_data.record_date)

        if update_data.record_type is not None:
            updates.append("record_type = %s")
            params.append(update_data.record_type)

        if update_data.tags is not None:
            import json
            updates.append("tags = %s")
            params.append(json.dumps(update_data.tags))

        if not updates:
            return {"success": True, "message": "无需更新"}

        updates.append("updated_at = datetime('now', 'localtime')")
        params.append(record_id)

        sql = f"UPDATE moment_record SET {', '.join(updates)} WHERE record_id = %s"
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
        if not check_moral_permission(user, 'moment_create') and not check_moral_permission(user, 'moment_view_all'):
            raise HTTPException(403, "权限不足：需要点滴记录权限")

        # 查询记录
        record = db.query_one(
            "SELECT * FROM moment_record WHERE record_id = %s",
            (record_id,)
        )
        if not record:
            raise HTTPException(404, "记录不存在")

        # 普通教师/班主任只能删除自己的记录，管理角色可删除全部记录
        if not check_moral_permission(user, 'moment_view_all') and record['recorder'] != user.username:
            raise HTTPException(403, "只能删除自己创建的记录")

        db.execute("DELETE FROM moment_record WHERE record_id = %s", (record_id,))

        log_operation(
            db, user.username, user.role, 'DELETE', 'moment_record', record_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "记录删除成功"}
