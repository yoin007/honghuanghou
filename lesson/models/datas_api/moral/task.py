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
    get_current_semester,
    get_student_class_snapshot,
    log_operation,
    require_permission,
    check_moral_permission,
    get_teacher_class_id,
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
    task_type: Optional[int] = Field(1, description="任务类型：1=个人任务 2=集体任务")
    score: int = Field(5, description="完成得分")
    start_date: Optional[str] = Field(None, description="开始日期")
    end_date: Optional[str] = Field(None, description="结束日期")
    can_carryover: Optional[int] = Field(1, description="是否允许结转：1=允许 0=不允许")
    description: Optional[str] = Field(None, description="任务描述")


class TaskFinishCreate(BaseModel):
    """完成任务记录"""
    student_id: str = Field(..., description="学号")
    task_id: int = Field(..., description="任务ID")
    finish_date: Optional[date] = Field(None, description="完成日期")
    remark: Optional[str] = Field(None, description="备注")


# =============================================================================
# API 路由 - 任务管理
# =============================================================================

@router.get("", summary="获取德育任务列表")
async def get_moral_tasks(
    grade_id: Optional[int] = Query(None),
    is_active: Optional[int] = Query(None),  # 不传参数时不过滤，传1查活跃，传0查已结束
    user: User = Depends(get_current_user)
):
    """获取德育任务列表"""
    with get_moral_db() as db:
        query = """SELECT t.task_id, t.grade_id, t.task_name, t.task_desc as description,
                   t.score, t.task_type, t.start_date, t.end_date, t.deadline_type, t.can_carryover,
                   t.is_required, t.is_active, t.created_at,
                   g.grade_name
                   FROM grade_moral_task t JOIN grade g ON t.grade_id = g.grade_id WHERE 1=1"""
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
    """
    创建德育任务

    创建后会自动为该年级所有在校学生初始化未完成记录
    """
    with get_moral_db() as db:
        # 获取当前学年
        current_year = get_current_school_year(db)
        if not current_year:
            raise HTTPException(400, "当前学年未配置，无法创建任务")
        year_id = current_year['year_id']

        # 根据结束日期判断截止类型
        deadline_type = "open"
        if task.end_date:
            deadline_type = "year"

        # 插入任务记录
        db.execute(
            """INSERT INTO grade_moral_task
            (grade_id, task_name, task_desc, score, task_type, start_date, end_date,
             deadline_type, can_carryover, is_required)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (task.grade_id, task.task_name, task.description, task.score, task.task_type or 1,
             task.start_date, task.end_date, deadline_type, task.can_carryover or 1, 1)
        )

        task_id = db.lastrowid()

        # 查询该年级所有在校学生
        students = db.query_all(
            """SELECT student_id, class_id FROM student
               WHERE grade_id = %s AND status = '在校'""",
            (task.grade_id,)
        )

        # 为每个学生初始化未完成记录
        initialized_count = 0
        for student in students:
            try:
                db.execute(
                    """INSERT INTO student_task_finish
                    (student_id, task_id, year_id, status, current_score,
                     carryover_count, is_carried_over)
                    VALUES (%s, %s, %s, 0, %s, 0, 0)""",
                    (student['student_id'], task_id, year_id, task.score)
                )
                initialized_count += 1
            except Exception as e:
                logger.warning(f"初始化学生任务记录失败: {student['student_id']} - {e}")

        log_operation(
            db, user.username, user.role, 'INSERT', 'grade_moral_task', task_id,
            new_data={
                'task_name': task.task_name,
                'score': task.score,
                'initialized_students': initialized_count
            },
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "message": f"任务创建成功，已为 {initialized_count} 名学生初始化未完成记录",
            "data": {"task_id": task_id, "initialized_count": initialized_count}
        }


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

        # 根据结束日期判断截止类型
        deadline_type = "open"
        if task.end_date:
            deadline_type = "year"

        db.execute(
            """UPDATE grade_moral_task SET
            grade_id = %s, task_name = %s, task_desc = %s, score = %s, task_type = %s,
            start_date = %s, end_date = %s, deadline_type = %s, can_carryover = %s
            WHERE task_id = %s""",
            (task.grade_id, task.task_name, task.description, task.score, task.task_type or old_task['task_type'] or 1,
             task.start_date, task.end_date, deadline_type, task.can_carryover or old_task['can_carryover'],
             task_id)
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
    user: User = Depends(get_current_user)
):
    """记录任务完成"""
    with get_moral_db() as db:
        can_manage_all = check_moral_permission(user, 'moral_record_manage')
        can_manage_own_class = check_moral_permission(user, 'moral_record_own_class')
        if not can_manage_all and not can_manage_own_class:
            raise HTTPException(403, "权限不足：需要德育任务完成记录权限")

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

        if not can_manage_all:
            my_class_id = get_teacher_class_id(user, db)
            if my_class_id is None or my_class_id != student['class_id']:
                raise HTTPException(403, "只能记录本班学生任务完成情况")

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
                (finish_date, year_id, record.remark, existing['id'])
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
                (record.student_id, record.task_id, year_id, finish_date, year_id, record.remark, task['score'])
            )
            finish_id = db.lastrowid()

            log_operation(
                db, user.username, user.role, 'INSERT', 'student_task_finish',
                finish_id, new_data={'student_id': record.student_id, 'task_id': record.task_id, 'status': 1},
                ip_address=request.client.host if request.client else None
            )

        current_semester = get_current_semester(db)
        if current_semester:
            from .evaluation import calculate_evaluation
            calculate_evaluation(
                db,
                record.student_id,
                current_semester['semester_id'],
                student['class_id'],
                student['grade_id'],
            )

        return {"success": True, "message": "任务完成记录已更新"}


class BatchFinishRequest(BaseModel):
    """批量完成请求"""
    task_id: int = Field(..., description="任务ID")
    class_id: Optional[int] = Field(None, description="班级ID（全班完成时使用）")
    student_ids: Optional[List[str]] = Field(None, description="学生ID列表（指定学生时使用）")
    finish_date: Optional[date] = Field(None, description="完成日期")
    remark: Optional[str] = Field(None, description="备注")


@router.post("/batch-finish", summary="批量标记任务完成")
async def batch_finish_task(
    request: BatchFinishRequest,
    req: Request,
    user: User = Depends(require_permission('moral_record_manage'))
):
    """
    批量标记任务完成

    权限要求：admin/xuefa（需要 moral_record_manage 权限）

    使用方式：
    1. 全班完成：传 class_id，自动标记该班级所有未完成学生
    2. 指定学生：传 student_ids 数组，批量标记指定学生

    只更新 status=0（未完成）的记录，已完成的不会重复更新
    """
    with get_moral_db() as db:
        current_year = get_current_school_year(db)
        if not current_year:
            raise HTTPException(400, "当前学年未配置")
        year_id = current_year['year_id']

        # 获取任务信息
        task = db.query_one(
            "SELECT * FROM grade_moral_task WHERE task_id = %s AND is_active = 1",
            (request.task_id,)
        )
        if not task:
            raise HTTPException(404, "任务不存在")

        # 确定要更新的学生列表
        if request.class_id:
            # 全班完成：查询该班级所有未完成的学生
            unfinished = db.query_all(
                """SELECT stf.id, stf.student_id, s.class_id, s.grade_id
                   FROM student_task_finish stf
                   JOIN student s ON stf.student_id = s.student_id
                   WHERE stf.task_id = %s AND stf.status = 0 AND s.class_id = %s""",
                (request.task_id, request.class_id)
            )
        elif request.student_ids:
            # 指定学生：查询这些学生中未完成的
            unfinished = db.query_all(
                """SELECT stf.id, stf.student_id, s.class_id, s.grade_id
                   FROM student_task_finish stf
                   JOIN student s ON stf.student_id = s.student_id
                   WHERE stf.task_id = %s AND stf.status = 0
                   AND stf.student_id IN (%s)""",
                (request.task_id, ','.join(request.student_ids))
            )
        else:
            raise HTTPException(400, "请指定 class_id 或 student_ids")

        if not unfinished:
            return {"success": True, "message": "没有待完成的学生", "data": {"updated_count": 0}}

        # 批量更新
        finish_date = request.finish_date or date.today()
        updated_count = 0

        for record in unfinished:
            db.execute(
                """UPDATE student_task_finish SET
                status = 1, finish_date = %s, finish_year_id = %s, proof = %s
                WHERE id = %s""",
                (finish_date, year_id, request.remark, record['id'])
            )
            updated_count += 1

        # 重新计算德育评价（批量）
        current_semester = get_current_semester(db)
        if current_semester:
            from .evaluation import calculate_evaluation
            for record in unfinished:
                calculate_evaluation(
                    db,
                    record['student_id'],
                    current_semester['semester_id'],
                    record['class_id'],
                    record['grade_id'],
                )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'student_task_finish', request.task_id,
            new_data={'action': 'batch_finish', 'updated_count': updated_count},
            ip_address=req.client.host if req.client else None
        )

        return {
            "success": True,
            "message": f"已批量标记 {updated_count} 名学生完成任务",
            "data": {"updated_count": updated_count}
        }


class MoralTaskImportItem(BaseModel):
    """批量导入德育任务项"""
    grade_name: str  # 级号名称，如 "2023级"
    task_name: str
    task_desc: Optional[str] = ""
    score: int
    deadline_type: str  # "学期截止"/"学年截止"/"无截止"
    is_required: str  # "是"/"否"


@router.post("/batch-import", summary="批量导入德育任务")
async def batch_import_moral_tasks(
    items: List[MoralTaskImportItem],
    request: Request,
    user: User = Depends(require_permission('event_type_manage'))
):
    """
    批量导入德育任务

    权限要求：xuefa/jiaowu/admin

    CSV格式：
    级号名称,任务名称,任务描述,分值,截止类型,是否必修
    2023级,志愿服务,参加志愿服务活动,5,学年截止,是
    """
    with get_moral_db() as db:
        success_count = 0
        skip_count = 0
        errors = []

        # 获取级号映射
        grades = db.query_all("SELECT grade_id, grade_name FROM grade")
        grade_map = {g['grade_name']: g['grade_id'] for g in grades}

        for i, item in enumerate(items):
            try:
                # 查找级号ID
                grade_id = grade_map.get(item.grade_name)
                if not grade_id:
                    errors.append(f"第{i+1}条: 级号 '{item.grade_name}' 不存在")
                    continue

                # 转换截止类型
                deadline_map = {
                    "学期截止": "semester",
                    "学年截止": "year",
                    "无截止": "open"
                }
                deadline_type = deadline_map.get(item.deadline_type, "year")

                # 转换是否必修
                is_required = 1 if item.is_required == "是" else 0

                # 检查是否已存在相同任务
                existing = db.query_one(
                    """SELECT task_id FROM grade_moral_task
                    WHERE grade_id = %s AND task_name = %s AND is_active = 1""",
                    (grade_id, item.task_name)
                )
                if existing:
                    skip_count += 1
                    continue

                db.execute(
                    """INSERT INTO grade_moral_task
                    (grade_id, task_name, task_desc, score, deadline_type, is_required, is_active)
                    VALUES (%s, %s, %s, %s, %s, %s, 1)""",
                    (grade_id, item.task_name, item.task_desc or "", item.score, deadline_type, is_required)
                )
                success_count += 1

            except Exception as e:
                errors.append(f"第{i+1}条: {str(e)}")

        log_operation(
            db, user.username, user.role, 'BATCH_IMPORT', 'grade_moral_task', None,
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
