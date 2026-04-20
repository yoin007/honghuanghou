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
    event_date: date = Field(..., description="事件日期")
    description: Optional[str] = Field(None, description="事件描述")
    evidence: Optional[str] = Field(None, description="证明材料")


class SchoolRecordUpdate(BaseModel):
    """更新校级事件记录"""
    event_date: Optional[date] = None
    description: Optional[str] = None
    evidence: Optional[str] = None
    is_deleted: Optional[int] = None


class SchoolEventTypeCreate(BaseModel):
    """创建校级事件类型"""
    event_name: str = Field(..., description="事件名称", max_length=50)
    event_type: int = Field(..., description="事件类型：1=荣誉，2=处分", ge=1, le=2)
    event_level: Optional[str] = Field(None, description="事件级别：国家级/省级/市级/校级", max_length=20)
    score: int = Field(..., description="分值（正数加分，负数扣分）")
    description: Optional[str] = Field(None, description="描述", max_length=200)


class SchoolEventTypeUpdate(BaseModel):
    """更新校级事件类型"""
    event_name: Optional[str] = Field(None, description="事件名称", max_length=50)
    event_type: Optional[int] = Field(None, description="事件类型：1=荣誉，2=处分")
    event_level: Optional[str] = Field(None, description="事件级别", max_length=20)
    score: Optional[int] = Field(None, description="分值")
    description: Optional[str] = Field(None, description="描述", max_length=200)
    is_active: Optional[int] = Field(None, description="是否启用：1=启用，0=禁用")


# =============================================================================
# API 路由
# =============================================================================

@router.get("/types", summary="获取校级事件类型列表")
async def get_school_event_types(
    event_type: Optional[int] = Query(None, description="事件类型：1=荣誉，2=处分"),
    event_level: Optional[str] = Query(None, description="事件级别"),
    is_active: Optional[int] = Query(None, description="是否启用：不传返回全部，1=启用，0=禁用"),
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
            SELECT sr.record_id, sr.student_id, sr.event_id, sr.semester_id,
                   sr.get_date as event_date, sr.score, sr.proof as evidence,
                   sr.proof as description,
                   s.name as student_name, se.event_name, se.event_type, se.event_level,
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

        # 组合证明材料：description + evidence
        proof = record.evidence or ''
        if record.description:
            proof = f"{record.description}" if not proof else f"{record.description} | {record.evidence}"

        # 检查证书编号唯一性
        if proof:
            existing = db.query_one(
                "SELECT record_id FROM student_school_record WHERE proof = %s",
                (proof,)
            )
            if existing:
                raise HTTPException(400, f"该证明材料已存在")

        # 插入记录（使用 event_date 映射到 get_date）
        db.execute(
            """INSERT INTO student_school_record
            (student_id, event_id, semester_id, get_date, class_id, grade_id, score, proof)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                record.student_id,
                record.event_id,
                semester_id,
                record.event_date,
                student_info['class_id'],
                student_info['grade_id'],
                event['score'],
                proof or None
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

        if update_data.event_date is not None:
            updates.append("get_date = %s")
            params.append(update_data.event_date)

        # 组合 description 和 evidence 到 proof 字段
        if update_data.description is not None or update_data.evidence is not None:
            proof_value = update_data.evidence or ''
            if update_data.description:
                proof_value = update_data.description if not proof_value else f"{update_data.description} | {update_data.evidence}"
            updates.append("proof = %s")
            params.append(proof_value or None)

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


# =============================================================================
# 事件类型管理 API
# =============================================================================

@router.post("/types", summary="创建校级事件类型")
async def create_school_event_type(
    event_type: SchoolEventTypeCreate,
    request: Request,
    user: User = Depends(require_permission('event_type_manage'))
):
    """
    创建校级事件类型

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        # 检查是否已存在同名事件
        existing = db.query_one(
            "SELECT event_id FROM school_event_type WHERE event_name = %s",
            (event_type.event_name,)
        )
        if existing:
            raise HTTPException(400, f"事件类型 '{event_type.event_name}' 已存在")

        # 根据事件类型确定分值正负
        score = abs(event_type.score) if event_type.event_type == 1 else -abs(event_type.score)

        db.execute(
            """INSERT INTO school_event_type (event_name, event_type, event_level, score, description, is_active)
            VALUES (%s, %s, %s, %s, %s, 1)""",
            (event_type.event_name, event_type.event_type, event_type.event_level, score, event_type.description)
        )

        event_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'school_event_type', event_id,
            new_data={'event_name': event_type.event_name, 'score': score},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "事件类型创建成功", "data": {"event_id": event_id}}


@router.put("/types/{type_id}", summary="更新校级事件类型")
async def update_school_event_type(
    type_id: int,
    update_data: SchoolEventTypeUpdate,
    request: Request,
    user: User = Depends(require_permission('event_type_manage'))
):
    """
    更新校级事件类型

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        # 获取原记录
        old_type = db.query_one(
            "SELECT * FROM school_event_type WHERE event_id = %s",
            (type_id,)
        )
        if not old_type:
            raise HTTPException(404, "事件类型不存在")

        # 构建更新语句
        updates = []
        params = []

        if update_data.event_name is not None:
            existing = db.query_one(
                "SELECT event_id FROM school_event_type WHERE event_name = %s AND event_id != %s",
                (update_data.event_name, type_id)
            )
            if existing:
                raise HTTPException(400, f"事件类型 '{update_data.event_name}' 已存在")
            updates.append("event_name = %s")
            params.append(update_data.event_name)

        # 获取最终的事件类型
        final_event_type = update_data.event_type if update_data.event_type is not None else old_type['event_type']

        if update_data.event_type is not None:
            updates.append("event_type = %s")
            params.append(update_data.event_type)

        if update_data.event_level is not None:
            updates.append("event_level = %s")
            params.append(update_data.event_level)

        if update_data.score is not None:
            score = abs(update_data.score) if final_event_type == 1 else -abs(update_data.score)
            updates.append("score = %s")
            params.append(score)

        if update_data.description is not None:
            updates.append("description = %s")
            params.append(update_data.description)

        if update_data.is_active is not None:
            updates.append("is_active = %s")
            params.append(update_data.is_active)

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(type_id)
        db.execute(
            f"UPDATE school_event_type SET {', '.join(updates)} WHERE event_id = %s",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'school_event_type', type_id,
            old_data={'event_name': old_type['event_name']},
            new_data=update_data.dict(exclude_unset=True),
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "事件类型更新成功"}


@router.delete("/types/{type_id}", summary="删除校级事件类型")
async def delete_school_event_type(
    type_id: int,
    request: Request,
    user: User = Depends(require_permission('event_type_manage'))
):
    """
    删除校级事件类型（软删除，设为禁用状态）

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        old_type = db.query_one(
            "SELECT * FROM school_event_type WHERE event_id = %s",
            (type_id,)
        )
        if not old_type:
            raise HTTPException(404, "事件类型不存在")

        # 检查是否有关联记录
        record_count = db.query_value(
            "SELECT COUNT(*) FROM student_school_record WHERE event_id = %s",
            (type_id,)
        )

        if record_count > 0:
            db.execute(
                "UPDATE school_event_type SET is_active = 0 WHERE event_id = %s",
                (type_id,)
            )
            log_operation(
                db, user.username, user.role, 'DISABLE', 'school_event_type', type_id,
                old_data={'event_name': old_type['event_name']},
                ip_address=request.client.host if request.client else None
            )
            return {"success": True, "message": f"该事件类型有 {record_count} 条关联记录，已禁用"}
        else:
            db.execute(
                "DELETE FROM school_event_type WHERE event_id = %s",
                (type_id,)
            )
            log_operation(
                db, user.username, user.role, 'DELETE', 'school_event_type', type_id,
                old_data={'event_name': old_type['event_name']},
                ip_address=request.client.host if request.client else None
            )
            return {"success": True, "message": "事件类型已删除"}


class SchoolEventImportItem(BaseModel):
    """批量导入校级事件类型项"""
    event_name: str
    event_type: str  # "荣誉奖励" or "违纪处分"
    event_level: str  # "国家级"/"省级"/"市级"/"校级"
    score: int
    description: Optional[str] = ""


@router.post("/types/batch-import", summary="批量导入校级事件类型")
async def batch_import_school_event_types(
    items: List[SchoolEventImportItem],
    request: Request,
    user: User = Depends(require_permission('event_type_manage'))
):
    """
    批量导入校级事件类型

    权限要求：xuefa/jiaowu/admin

    CSV格式：
    事件名称,事件类型,事件级别,分值,描述
    三好学生,荣誉奖励,校级,10,校级三好学生称号
    """
    with get_moral_db() as db:
        success_count = 0
        skip_count = 0
        errors = []

        for i, item in enumerate(items):
            try:
                # 转换事件类型
                event_type_num = 1 if "荣誉" in item.event_type else 2

                # 检查是否已存在
                existing = db.query_one(
                    "SELECT event_id FROM school_event_type WHERE event_name = %s",
                    (item.event_name,)
                )
                if existing:
                    skip_count += 1
                    continue

                # 根据事件类型确定分值正负
                score = abs(item.score) if event_type_num == 1 else -abs(item.score)

                db.execute(
                    """INSERT INTO school_event_type (event_name, event_type, event_level, score, description, is_active)
                    VALUES (%s, %s, %s, %s, %s, 1)""",
                    (item.event_name, event_type_num, item.event_level, score, item.description or "")
                )
                success_count += 1

            except Exception as e:
                errors.append(f"第{i+1}条: {str(e)}")

        log_operation(
            db, user.username, user.role, 'BATCH_IMPORT', 'school_event_type', None,
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