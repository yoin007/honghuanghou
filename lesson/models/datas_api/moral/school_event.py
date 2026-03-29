# -*- coding: utf-8 -*-
"""
校级事件记录 API

提供校级荣誉/处分事件的增删改查功能
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    get_current_semester,
    get_student_class_snapshot,
    log_operation,
    require_permission,
)
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/school-records", tags=["校级事件"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class SchoolRecordCreate(BaseModel):
    """创建校级事件记录"""
    student_id: str = Field(..., description="学号")
    event_id: int = Field(..., description="事件类型ID")
    get_date: date = Field(..., description="获得日期")
    proof: Optional[str] = Field(None, description="证书编号")
    score: Optional[int] = Field(None, description="分值（可选，默认使用事件类型分值）")


class SchoolRecordUpdate(BaseModel):
    """更新校级事件记录"""
    get_date: Optional[date] = None
    proof: Optional[str] = None
    score: Optional[int] = None
    is_deleted: Optional[int] = None


# =============================================================================
# API 路由
# =============================================================================

@router.get("/types", summary="获取校级事件类型列表")
async def get_school_event_types(
    event_type: Optional[int] = Query(None, description="事件类型：1=荣誉，2=处分"),
    event_level: Optional[str] = Query(None, description="事件级别"),
    is_active: Optional[int] = Query(1),
    user: User = Depends(get_current_user)
):
    """获取校级事件类型列表"""
    with get_moral_db() as db:
        query = "SELECT * FROM school_event_type WHERE 1=1"
        params = []

        if event_type is not None:
            query += " AND event_type = %s"
            params.append(event_type)

        if event_level:
            query += " AND event_level = %s"
            params.append(event_level)

        if is_active is not None:
            query += " AND is_active = %s"
            params.append(is_active)

        query += " ORDER BY event_type, score DESC"

        events = db.query_all(query, tuple(params) if params else None)

        return {"success": True, "data": events}


@router.get("", summary="获取校级事件记录列表")
async def get_school_records(
    student_id: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    semester_id: Optional[int] = Query(None),
    event_type: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """获取校级事件记录列表"""
    with get_moral_db() as db:
        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        conditions = ["sr.is_deleted = 0"]
        params = []

        if student_id:
            conditions.append("sr.student_id = %s")
            params.append(student_id)

        if class_id:
            conditions.append("sr.class_id = %s")
            params.append(class_id)

        if grade_id:
            conditions.append("sr.grade_id = %s")
            params.append(grade_id)

        if semester_id:
            conditions.append("sr.semester_id = %s")
            params.append(semester_id)

        if event_type is not None:
            conditions.append("se.event_type = %s")
            params.append(event_type)

        where_clause = " AND ".join(conditions)

        # 查询总数
        count_query = f"""
            SELECT COUNT(*) as total
            FROM student_school_record sr
            JOIN school_event_type se ON sr.event_id = se.event_id
            WHERE {where_clause}
        """
        total = db.query_value(count_query, tuple(params))

        # 分页查询
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT sr.*, s.name as student_name, se.event_name, se.event_type, se.event_level,
                   c.class_name, g.grade_name
            FROM student_school_record sr
            JOIN student s ON sr.student_id = s.student_id
            JOIN school_event_type se ON sr.event_id = se.event_id
            JOIN class c ON sr.class_id = c.class_id
            JOIN grade g ON sr.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY sr.get_date DESC, sr.created_at DESC
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
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }


@router.post("", summary="创建校级事件记录")
async def create_school_record(
    record: SchoolRecordCreate,
    request: Request,
    user: User = Depends(require_permission('moral_record_manage'))
):
    """创建校级事件记录"""
    with get_moral_db() as db:
        current_semester = get_current_semester(db)
        if not current_semester:
            raise HTTPException(400, "当前学期未配置")

        semester_id = current_semester['semester_id']

        # 获取学生班级信息
        student_info = get_student_class_snapshot(db, record.student_id)
        if not student_info:
            raise HTTPException(404, f"学生 {record.student_id} 不存在或不在校")

        # 获取事件类型
        event = db.query_one(
            "SELECT * FROM school_event_type WHERE event_id = %s AND is_active = 1",
            (record.event_id,)
        )
        if not event:
            raise HTTPException(404, f"事件类型 {record.event_id} 不存在")

        # 检查证书编号唯一性
        if record.proof:
            existing = db.query_one(
                "SELECT record_id FROM student_school_record WHERE proof = %s",
                (record.proof,)
            )
            if existing:
                raise HTTPException(400, f"证书编号 {record.proof} 已存在")

        # 计算分值
        score = record.score if record.score is not None else event['score']

        # 插入记录
        db.execute(
            """INSERT INTO student_school_record
            (student_id, event_id, semester_id, get_date, class_id, grade_id, score, proof)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                record.student_id,
                record.event_id,
                semester_id,
                record.get_date,
                student_info['class_id'],
                student_info['grade_id'],
                score,
                record.proof
            )
        )

        record_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'student_school_record',
            record_id, semester_id,
            new_data={'student_id': record.student_id, 'event_id': record.event_id},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "记录创建成功", "data": {"record_id": record_id}}


@router.put("/{record_id}", summary="更新校级事件记录")
async def update_school_record(
    record_id: int,
    update_data: SchoolRecordUpdate,
    request: Request,
    user: User = Depends(require_permission('moral_record_manage'))
):
    """更新校级事件记录"""
    with get_moral_db() as db:
        old_record = db.query_one(
            "SELECT * FROM student_school_record WHERE record_id = %s",
            (record_id,)
        )
        if not old_record:
            raise HTTPException(404, "记录不存在")

        updates = []
        params = []

        if update_data.get_date is not None:
            updates.append("get_date = %s")
            params.append(update_data.get_date)

        if update_data.proof is not None:
            updates.append("proof = %s")
            params.append(update_data.proof)

        if update_data.score is not None:
            updates.append("score = %s")
            params.append(update_data.score)

        if update_data.is_deleted is not None:
            updates.append("is_deleted = %s")
            params.append(update_data.is_deleted)

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(record_id)
        db.execute(
            f"UPDATE student_school_record SET {', '.join(updates)} WHERE record_id = %s",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'student_school_record',
            record_id, old_record['semester_id'],
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "记录更新成功"}


@router.delete("/{record_id}", summary="删除校级事件记录")
async def delete_school_record(
    record_id: int,
    request: Request,
    user: User = Depends(require_permission('moral_record_manage'))
):
    """删除校级事件记录（软删除）"""
    with get_moral_db() as db:
        old_record = db.query_one(
            "SELECT * FROM student_school_record WHERE record_id = %s",
            (record_id,)
        )
        if not old_record:
            raise HTTPException(404, "记录不存在")

        db.execute(
            "UPDATE student_school_record SET is_deleted = 1 WHERE record_id = %s",
            (record_id,)
        )

        log_operation(
            db, user.username, user.role, 'DELETE', 'student_school_record',
            record_id, old_record['semester_id'],
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "记录已删除"}