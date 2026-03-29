# -*- coding: utf-8 -*-
"""
系统管理 API

提供级号、学年、学期等系统配置的管理功能
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    require_permission,
    require_role_level,
    log_operation,
)
from models.datas_api.auth import User, get_current_user, is_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["系统管理"])


# =============================================================================
# Pydantic 模型
# =============================================================================

class GradeCreate(BaseModel):
    """创建级号"""
    grade_name: str = Field(..., description="级号名称，如：2025级")
    enrollment_year: int = Field(..., description="入学年份")


class ClassCreate(BaseModel):
    """创建班级"""
    class_code: str = Field(..., description="班级代码")
    grade_id: int = Field(..., description="级号ID")
    class_number: int = Field(..., description="班号")
    class_name: str = Field(..., description="班级名称")
    leader_name: Optional[str] = Field(None, description="班主任姓名")
    leader_wxid: Optional[str] = Field(None, description="班主任微信ID")
    roomid: Optional[str] = Field(None, description="微信群ID")


class StudentCreate(BaseModel):
    """创建学生"""
    student_id: str = Field(..., description="学号")
    name: str = Field(..., description="姓名")
    gender: Optional[str] = Field(None, description="性别")
    class_id: int = Field(..., description="班级ID")
    grade_id: int = Field(..., description="级号ID")
    birthday: Optional[date] = Field(None, description="出生日期")
    enrollment_date: Optional[date] = Field(None, description="入学日期")


class SchoolYearCreate(BaseModel):
    """创建学年"""
    year_name: str = Field(..., description="学年名称，如：2025-2026学年")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    is_current: Optional[int] = Field(0, description="是否当前学年")


class SemesterCreate(BaseModel):
    """创建学期"""
    semester_name: str = Field(..., description="学期名称，如：2025-2026上")
    year_id: int = Field(..., description="学年ID")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")
    status: Optional[int] = Field(0, description="是否当前学期")


# =============================================================================
# API 路由 - 级号管理
# =============================================================================

@router.get("/grades", summary="获取级号列表")
async def get_grades(user: User = Depends(get_current_user)):
    """获取级号列表"""
    with get_moral_db() as db:
        grades = db.query_all(
            "SELECT g.*, "
            "(SELECT COUNT(*) FROM class WHERE grade_id = g.grade_id) as class_count, "
            "(SELECT COUNT(*) FROM student WHERE grade_id = g.grade_id AND status = '在校') as student_count "
            "FROM grade g ORDER BY g.enrollment_year DESC"
        )
        return {"success": True, "data": grades}


@router.post("/grades", summary="创建级号")
async def create_grade(
    grade: GradeCreate,
    request: Request,
    user: User = Depends(require_permission('grade_manage'))
):
    """创建级号"""
    with get_moral_db() as db:
        # 检查是否已存在
        existing = db.query_one(
            "SELECT grade_id FROM grade WHERE enrollment_year = %s",
            (grade.enrollment_year,)
        )
        if existing:
            raise HTTPException(400, f"{grade.enrollment_year}年级已存在")

        db.execute(
            "INSERT INTO grade (grade_name, enrollment_year) VALUES (%s, %s)",
            (grade.grade_name, grade.enrollment_year)
        )

        grade_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'grade', grade_id,
            new_data={'grade_name': grade.grade_name},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "级号创建成功", "data": {"grade_id": grade_id}}


@router.delete("/grades/{grade_id}", summary="删除级号")
async def delete_grade(
    grade_id: int,
    request: Request,
    user: User = Depends(require_permission('grade_manage'))
):
    """删除级号"""
    with get_moral_db() as db:
        # 检查是否有关联班级
        class_count = db.query_value(
            "SELECT COUNT(*) FROM class WHERE grade_id = %s",
            (grade_id,)
        )
        if class_count > 0:
            raise HTTPException(400, "该级号下存在班级，无法删除")

        db.execute("DELETE FROM grade WHERE grade_id = %s", (grade_id,))

        log_operation(
            db, user.username, user.role, 'DELETE', 'grade', grade_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "级号已删除"}


# =============================================================================
# API 路由 - 班级管理
# =============================================================================

@router.get("/classes", summary="获取班级列表")
async def get_classes(
    grade_id: Optional[int] = Query(None),
    is_active: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    """获取班级列表"""
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if grade_id:
            conditions.append("c.grade_id = %s")
            params.append(grade_id)

        if is_active is not None:
            conditions.append("c.is_active = %s")
            params.append(is_active)

        where_clause = " AND ".join(conditions)

        classes = db.query_all(
            f"""SELECT c.*, g.grade_name,
                (SELECT COUNT(*) FROM student WHERE class_id = c.class_id AND status = '在校') as student_count
                FROM class c
                JOIN grade g ON c.grade_id = g.grade_id
                WHERE {where_clause}
                ORDER BY g.enrollment_year DESC, c.class_number""",
            tuple(params) if params else None
        )

        return {"success": True, "data": classes}


@router.post("/classes", summary="创建班级")
async def create_class(
    cls: ClassCreate,
    request: Request,
    user: User = Depends(require_permission('class_manage'))
):
    """创建班级"""
    with get_moral_db() as db:
        # 检查班级代码是否已存在
        existing = db.query_one(
            "SELECT class_id FROM class WHERE class_code = %s",
            (cls.class_code,)
        )
        if existing:
            raise HTTPException(400, f"班级代码 {cls.class_code} 已存在")

        db.execute(
            """INSERT INTO class
            (class_code, grade_id, class_number, class_name, leader_name, leader_wxid, roomid)
            VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (cls.class_code, cls.grade_id, cls.class_number, cls.class_name,
             cls.leader_name, cls.leader_wxid, cls.roomid)
        )

        class_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'class', class_id,
            new_data={'class_name': cls.class_name},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "班级创建成功", "data": {"class_id": class_id}}


@router.put("/classes/{class_id}", summary="更新班级")
async def update_class(
    class_id: int,
    cls: ClassCreate,
    request: Request,
    user: User = Depends(require_permission('class_manage'))
):
    """更新班级"""
    with get_moral_db() as db:
        db.execute(
            """UPDATE class SET
            class_code = %s, grade_id = %s, class_number = %s, class_name = %s,
            leader_name = %s, leader_wxid = %s, roomid = %s
            WHERE class_id = %s""",
            (cls.class_code, cls.grade_id, cls.class_number, cls.class_name,
             cls.leader_name, cls.leader_wxid, cls.roomid, class_id)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'class', class_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "班级更新成功"}


# =============================================================================
# API 路由 - 学年学期管理
# =============================================================================

@router.get("/school-years", summary="获取学年列表")
async def get_school_years(user: User = Depends(get_current_user)):
    """获取学年列表"""
    with get_moral_db() as db:
        years = db.query_all(
            """SELECT sy.*,
                (SELECT COUNT(*) FROM semester WHERE year_id = sy.year_id) as semester_count
                FROM school_year sy
                ORDER BY sy.start_date DESC"""
        )
        return {"success": True, "data": years}


@router.post("/school-years", summary="创建学年")
async def create_school_year(
    year: SchoolYearCreate,
    request: Request,
    user: User = Depends(require_permission('semester_manage'))
):
    """创建学年"""
    with get_moral_db() as db:
        if year.is_current == 1:
            # 取消其他学年的当前状态
            db.execute("UPDATE school_year SET is_current = 0")

        db.execute(
            """INSERT INTO school_year
            (year_name, start_date, end_date, is_current)
            VALUES (%s, %s, %s, %s)""",
            (year.year_name, year.start_date, year.end_date, year.is_current)
        )

        year_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'school_year', year_id,
            new_data={'year_name': year.year_name},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "学年创建成功", "data": {"year_id": year_id}}


@router.get("/semesters", summary="获取学期列表")
async def get_semesters(
    year_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    """获取学期列表"""
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if year_id:
            conditions.append("sem.year_id = %s")
            params.append(year_id)

        where_clause = " AND ".join(conditions)

        semesters = db.query_all(
            f"""SELECT sem.*, sy.year_name
                FROM semester sem
                JOIN school_year sy ON sem.year_id = sy.year_id
                WHERE {where_clause}
                ORDER BY sem.start_date DESC""",
            tuple(params) if params else None
        )

        return {"success": True, "data": semesters}


@router.post("/semesters", summary="创建学期")
async def create_semester(
    semester: SemesterCreate,
    request: Request,
    user: User = Depends(require_permission('semester_manage'))
):
    """创建学期"""
    with get_moral_db() as db:
        if semester.status == 1:
            # 取消其他学期的当前状态
            db.execute("UPDATE semester SET status = 0")

        db.execute(
            """INSERT INTO semester
            (semester_name, year_id, start_date, end_date, status)
            VALUES (%s, %s, %s, %s, %s)""",
            (semester.semester_name, semester.year_id, semester.start_date,
             semester.end_date, semester.status)
        )

        semester_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'semester', semester_id,
            new_data={'semester_name': semester.semester_name},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "学期创建成功", "data": {"semester_id": semester_id}}


@router.post("/semesters/{semester_id}/set-current", summary="设置当前学期")
async def set_current_semester(
    semester_id: int,
    request: Request,
    user: User = Depends(require_permission('semester_manage'))
):
    """设置当前学期"""
    with get_moral_db() as db:
        semester = db.query_one(
            "SELECT * FROM semester WHERE semester_id = %s",
            (semester_id,)
        )
        if not semester:
            raise HTTPException(404, "学期不存在")

        # 取消其他学期的当前状态
        db.execute("UPDATE semester SET status = 0")

        # 设置当前学期
        db.execute(
            "UPDATE semester SET status = 1 WHERE semester_id = %s",
            (semester_id,)
        )

        # 同时设置学年为当前
        db.execute(
            "UPDATE school_year SET is_current = 0"
        )
        db.execute(
            "UPDATE school_year SET is_current = 1 WHERE year_id = %s",
            (semester['year_id'],)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'semester', semester_id,
            new_data={'status': 1},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "已设置为当前学期"}


# =============================================================================
# API 路由 - 学生管理
# =============================================================================

@router.get("/students", summary="获取学生列表")
async def get_students(
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user)
):
    """获取学生列表"""
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if class_id:
            conditions.append("s.class_id = %s")
            params.append(class_id)

        if grade_id:
            conditions.append("s.grade_id = %s")
            params.append(grade_id)

        if status:
            conditions.append("s.status = %s")
            params.append(status)

        where_clause = " AND ".join(conditions)

        count_query = f"SELECT COUNT(*) FROM student s WHERE {where_clause}"
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT s.*, c.class_name, g.grade_name
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            JOIN grade g ON s.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY s.student_id
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        students = db.query_all(data_query, tuple(params))

        return {
            "success": True,
            "data": {
                "items": students,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


@router.post("/students", summary="创建学生")
async def create_student(
    student: StudentCreate,
    request: Request,
    user: User = Depends(require_permission('student_manage'))
):
    """创建学生"""
    with get_moral_db() as db:
        # 检查学号是否已存在
        existing = db.query_one(
            "SELECT student_id FROM student WHERE student_id = %s",
            (student.student_id,)
        )
        if existing:
            raise HTTPException(400, f"学号 {student.student_id} 已存在")

        # 入学日期默认为9月1日
        enrollment_date = student.enrollment_date or date.today()

        db.execute(
            """INSERT INTO student
            (student_id, name, gender, class_id, grade_id, original_grade_id, birthday, enrollment_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '在校')""",
            (student.student_id, student.name, student.gender, student.class_id,
             student.grade_id, student.grade_id, student.birthday, enrollment_date)
        )

        # 创建班级履历
        db.execute(
            """INSERT INTO student_class_history
            (student_id, class_id, grade_id, start_date, change_reason)
            VALUES (%s, %s, %s, %s, '入学')""",
            (student.student_id, student.class_id, student.grade_id, enrollment_date)
        )

        log_operation(
            db, user.username, user.role, 'INSERT', 'student', None,
            new_data={'student_id': student.student_id, 'name': student.name},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "学生创建成功"}


@router.put("/students/{student_id}/status", summary="更新学生状态")
async def update_student_status(
    student_id: str,
    status: str = Query(..., description="状态：在校/休学/转出/毕业"),
    request: Request = None,
    user: User = Depends(require_permission('student_manage'))
):
    """更新学生状态"""
    with get_moral_db() as db:
        student = db.query_one(
            "SELECT * FROM student WHERE student_id = %s",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        db.execute(
            "UPDATE student SET status = %s, status_date = %s WHERE student_id = %s",
            (status, date.today(), student_id)
        )

        # 结束当前班级履历
        if status in ['转出', '毕业']:
            db.execute(
                """UPDATE student_class_history SET end_date = %s
                WHERE student_id = %s AND end_date IS NULL""",
                (date.today(), student_id)
            )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'student', None,
            new_data={'status': status},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": f"学生状态已更新为 {status}"}