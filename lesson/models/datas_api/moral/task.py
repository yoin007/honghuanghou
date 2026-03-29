# -*- coding: utf-8 -*-
"""
德育任务管理 API

提供年级德育任务的增删改查功能
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    get_current_school_year,
    get_student_class_snapshot,
    log_operation,
    require_permission,
)
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["德育任务"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class MoralTaskCreate(BaseModel):
    """创建德育任务"""
    grade_id: int = Field(..., description="级号ID")
    task_name: str = Field(..., description="任务名称")
    task_desc: Optional[str] = Field(None, description="任务描述")
    score: int = Field(..., description="完成得分")
    deadline_type: Optional[str] = Field("year", description="截止类型：semester/year/open")
    is_required: Optional[int] = Field(1, description="是否必修")


class TaskFinishCreate(BaseModel):
    """完成任务记录"""
    student_id: str = Field(..., description="学号")
    task_id: int = Field(..., description="任务ID")
    finish_date: Optional[date] = Field(None, description="完成日期")
    proof: Optional[str] = Field(None, description="证明材料")


# =============================================================================
# API 路由 - 任务管理
# =============================================================================

@router.get("", summary="获取德育任务列表")
async def get_moral_tasks(
    grade_id: Optional[int] = Query(None),
    is_active: Optional[int] = Query(1),
    user: User = Depends(get_current_user)
):
    """获取德育任务列表"""
    with get_moral_db() as db:
        query = "SELECT t.*, g.grade_name FROM grade_moral_task t JOIN grade g ON t.grade_id = g.grade_id WHERE 1=1"
        params = []

        if grade_id:
            query += " AND t.grade_id = %s"
            params.append(grade_id)

        if is_active is not None:
            query += " AND t.is_active = %s"
            params.append(is_active)

        query += " ORDER BY g.enrollment_year DESC, t.score DESC"

        tasks = db.query_all(query, tuple(params) if params else None)

        return {"success": True, "data": tasks}


@router.post("", summary="创建德育任务")
async def create_moral_task(
    task: MoralTaskCreate,
    request: Request,
    user: User = Depends(require_permission('event_type_manage'))
):
    """创建德育任务"""
    with get_moral_db() as db:
        db.execute(
            """INSERT INTO grade_moral_task
            (grade_id, task_name, task_desc, score, deadline_type, is_required)
            VALUES (%s, %s, %s, %s, %s, %s)""",
            (task.grade_id, task.task_name, task.task_desc, task.score,
             task.deadline_type, task.is_required)
        )

        task_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'grade_moral_task', task_id,
            new_data={'task_name': task.task_name, 'score': task.score},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "任务创建成功", "data": {"task_id": task_id}}


@router.put("/{task_id}", summary="更新德育任务")
async def update_moral_task(
    task_id: int,
    task: MoralTaskCreate,
    request: Request,
    user: User = Depends(require_permission('event_type_manage'))
):
    """更新德育任务"""
    with get_moral_db() as db:
        old_task = db.query_one(
            "SELECT * FROM grade_moral_task WHERE task_id = %s",
            (task_id,)
        )
        if not old_task:
            raise HTTPException(404, "任务不存在")

        db.execute(
            """UPDATE grade_moral_task SET
            grade_id = %s, task_name = %s, task_desc = %s, score = %s,
            deadline_type = %s, is_required = %s
            WHERE task_id = %s""",
            (task.grade_id, task.task_name, task.task_desc, task.score,
             task.deadline_type, task.is_required, task_id)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'grade_moral_task', task_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "任务更新成功"}


@router.delete("/{task_id}", summary="删除德育任务")
async def delete_moral_task(
    task_id: int,
    request: Request,
    user: User = Depends(require_permission('event_type_manage'))
):
    """删除德育任务（软删除）"""
    with get_moral_db() as db:
        db.execute(
            "UPDATE grade_moral_task SET is_active = 0 WHERE task_id = %s",
            (task_id,)
        )

        log_operation(
            db, user.username, user.role, 'DELETE', 'grade_moral_task', task_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "任务已删除"}


# =============================================================================
# API 路由 - 任务完成
# =============================================================================

@router.get("/finish", summary="获取任务完成记录列表")
async def get_task_finish_records(
    student_id: Optional[str] = Query(None),
    grade_id: Optional[int] = Query(None),
    status: Optional[int] = Query(None, description="0=未完成 1=已完成 2=已作废"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user)
):
    """获取任务完成记录列表"""
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if student_id:
            conditions.append("stf.student_id = %s")
            params.append(student_id)

        if grade_id:
            conditions.append("t.grade_id = %s")
            params.append(grade_id)

        if status is not None:
            conditions.append("stf.status = %s")
            params.append(status)

        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*) FROM student_task_finish stf
            JOIN grade_moral_task t ON stf.task_id = t.task_id
            WHERE {where_clause}
        """
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT stf.*, s.name as student_name, t.task_name, t.score as original_score,
                   c.class_name, g.grade_name
            FROM student_task_finish stf
            JOIN student s ON stf.student_id = s.student_id
            JOIN grade_moral_task t ON stf.task_id = t.task_id
            JOIN class c ON s.class_id = c.class_id
            JOIN grade g ON s.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY stf.created_at DESC
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


@router.post("/finish", summary="记录任务完成")
async def finish_task(
    record: TaskFinishCreate,
    request: Request,
    user: User = Depends(require_permission('moral_record_own_class'))
):
    """记录任务完成"""
    with get_moral_db() as db:
        current_year = get_current_school_year(db)
        if not current_year:
            raise HTTPException(400, "当前学年未配置")

        year_id = current_year['year_id']

        # 获取任务信息
        task = db.query_one(
            "SELECT * FROM grade_moral_task WHERE task_id = %s AND is_active = 1",
            (record.task_id,)
        )
        if not task:
            raise HTTPException(404, "任务不存在")

        # 检查学生是否存在
        student = db.query_one(
            "SELECT * FROM student WHERE student_id = %s AND status = '在校'",
            (record.student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在或不在校")

        # 检查是否已有记录
        existing = db.query_one(
            """SELECT * FROM student_task_finish
            WHERE student_id = %s AND task_id = %s AND year_id = %s""",
            (record.student_id, record.task_id, year_id)
        )

        if existing:
            if existing['status'] == 1:
                raise HTTPException(400, "该任务已完成")

            # 更新状态
            finish_date = record.finish_date or date.today()
            db.execute(
                """UPDATE student_task_finish SET
                status = 1, finish_date = %s, finish_year_id = %s, proof = %s
                WHERE id = %s""",
                (finish_date, year_id, record.proof, existing['id'])
            )

            log_operation(
                db, user.username, user.role, 'UPDATE', 'student_task_finish',
                existing['id'], new_data={'status': 1},
                ip_address=request.client.host if request.client else None
            )
        else:
            # 创建新记录
            finish_date = record.finish_date or date.today()
            db.execute(
                """INSERT INTO student_task_finish
                (student_id, task_id, year_id, status, finish_date, finish_year_id, proof, current_score)
                VALUES (%s, %s, %s, 1, %s, %s, %s, %s)""",
                (record.student_id, record.task_id, year_id, finish_date, year_id, record.proof, task['score'])
            )

        return {"success": True, "message": "任务完成记录已更新"}