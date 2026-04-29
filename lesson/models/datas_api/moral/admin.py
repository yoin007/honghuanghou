# -*- coding: utf-8 -*-
"""
系统管理 API

提供级号、学年、学期等系统配置的管理功能
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    require_permission,
    require_role_level,
    log_operation,
    check_moral_permission,
    check_class_access,
    get_teacher_class_id,
    has_user_role,
    check_moral_permission_for_roles,
    get_api_scoped_user_roles,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
)
from models.datas_api.auth import User, get_current_user, is_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["系统管理"])

API_STUDENT_LIST = "/api/moral/admin/students"
API_STUDENT_CREATE = "/api/moral/admin/students/create"
API_STUDENT_BATCH = "/api/moral/admin/students/batch"
API_STUDENT_UPDATE = "/api/moral/admin/students/update"


def _has_scoped_permission(db, user: User, api_path: str, permission: str) -> bool:
    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    return check_moral_permission_for_roles(scoped_roles, permission)


def _has_scoped_any_permission(db, user: User, api_path: str, permissions: List[str]) -> bool:
    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    return any(check_moral_permission_for_roles(scoped_roles, permission) for permission in permissions)


def _student_manage_scope(db, user: User, api_path: str) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['student_manage', 'student_manage_all', 'report_view_all'],
        own_class_permissions=['student_manage_own_class'],
        own_permissions=[],
    )


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


class ClassUpdate(BaseModel):
    """更新班级"""
    class_code: Optional[str] = Field(None, description="班级代码")
    grade_id: Optional[int] = Field(None, description="级号ID")
    class_number: Optional[int] = Field(None, description="班号")
    class_name: Optional[str] = Field(None, description="班级名称")
    leader_name: Optional[str] = Field(None, description="班主任姓名")
    leader_wxid: Optional[str] = Field(None, description="班主任微信ID")
    roomid: Optional[str] = Field(None, description="微信群ID")
    established: Optional[str] = Field(None, description="成立时间")
    motto: Optional[str] = Field(None, description="班级口号")
    location: Optional[str] = Field(None, description="教室位置")


class StudentCreate(BaseModel):
    """创建学生"""
    student_id: str = Field(..., description="学号")
    name: str = Field(..., description="姓名")
    gender: Optional[str] = Field(None, description="性别")
    class_id: int = Field(..., description="班级ID")
    birthday: Optional[date] = Field(None, description="出生日期")


class StudentBatchItem(BaseModel):
    """批量导入学生单项"""
    student_id: str = Field(..., description="学号")
    name: str = Field(..., description="姓名")
    gender: Optional[str] = Field(None, description="性别")
    class_name: str = Field(..., description="班级名称")
    birthday: Optional[str] = Field(None, description="出生日期 YYYY-MM-DD")


class StudentBatchImport(BaseModel):
    """批量导入学生"""
    students: List[StudentBatchItem] = Field(..., description="学生列表")


class StudentUpdate(BaseModel):
    """更新学生信息"""
    name: Optional[str] = Field(None, description="姓名")
    gender: Optional[str] = Field(None, description="性别")
    class_id: Optional[int] = Field(None, description="班级ID")
    birthday: Optional[date] = Field(None, description="出生日期")
    roomid: Optional[str] = Field(None, description="宿舍号")
    rpid: Optional[str] = Field(None, description="床位号")


class SchoolYearCreate(BaseModel):
    """创建学年"""
    school_year_name: str = Field(..., description="学年名称，如：2025-2026学年")
    start_year: int = Field(..., description="起始年份")


class SemesterCreate(BaseModel):
    """创建学期"""
    school_year_id: int = Field(..., description="学年ID")
    semester_type: int = Field(1, description="学期类型：1=上学期，2=下学期")
    semester_name: str = Field(..., description="学期名称，如：2025-2026上")
    start_date: date = Field(..., description="开始日期")
    end_date: date = Field(..., description="结束日期")


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
    cls: ClassUpdate,
    request: Request,
    user: User = Depends(require_permission('class_manage'))
):
    """更新班级"""
    with get_moral_db() as db:
        # 构建动态更新
        updates = []
        params = []

        if cls.class_code is not None:
            updates.append("class_code = %s")
            params.append(cls.class_code)
        if cls.grade_id is not None:
            updates.append("grade_id = %s")
            params.append(cls.grade_id)
        if cls.class_number is not None:
            updates.append("class_number = %s")
            params.append(cls.class_number)
        if cls.class_name is not None:
            updates.append("class_name = %s")
            params.append(cls.class_name)
        if cls.leader_name is not None:
            updates.append("leader_name = %s")
            params.append(cls.leader_name)
        if cls.leader_wxid is not None:
            updates.append("leader_wxid = %s")
            params.append(cls.leader_wxid)
        if cls.roomid is not None:
            updates.append("roomid = %s")
            params.append(cls.roomid)
        if cls.established is not None:
            updates.append("established = %s")
            params.append(cls.established)
        if cls.motto is not None:
            updates.append("motto = %s")
            params.append(cls.motto)
        if cls.location is not None:
            updates.append("location = %s")
            params.append(cls.location)

        if not updates:
            return {"success": True, "message": "无需更新"}

        params.append(class_id)
        sql = f"UPDATE class SET {', '.join(updates)} WHERE class_id = %s"
        db.execute(sql, tuple(params))

        log_operation(
            db, user.username, user.role, 'UPDATE', 'class', class_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "班级更新成功"}


@router.delete("/classes/{class_id}", summary="删除班级")
async def delete_class(
    class_id: int,
    request: Request,
    user: User = Depends(require_permission('class_manage'))
):
    """删除班级"""
    with get_moral_db() as db:
        # 检查是否有学生
        student_count = db.query_value(
            "SELECT COUNT(*) FROM student WHERE class_id = %s AND status = '在校'",
            (class_id,)
        )
        if student_count > 0:
            raise HTTPException(400, f"该班级下有 {student_count} 名在校生，无法删除")

        db.execute("DELETE FROM class WHERE class_id = %s", (class_id,))

        log_operation(
            db, user.username, user.role, 'DELETE', 'class', class_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "班级已删除"}


# =============================================================================
# API 路由 - 学年学期管理
# =============================================================================

@router.get("/school-years", summary="获取学年列表")
async def get_school_years(user: User = Depends(get_current_user)):
    """获取学年列表"""
    with get_moral_db() as db:
        years = db.query_all(
            """SELECT sy.year_id as school_year_id, sy.year_name as school_year_name,
                sy.start_date, sy.end_date, sy.is_current,
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
        # 根据起始年份自动计算开始和结束日期
        start_date = date(year.start_year, 9, 1)
        end_date = date(year.start_year + 1, 7, 15)

        db.execute(
            """INSERT INTO school_year
            (year_name, start_date, end_date, is_current)
            VALUES (%s, %s, %s, %s)""",
            (year.school_year_name, start_date, end_date, 0)
        )

        year_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'school_year', year_id,
            new_data={'year_name': year.school_year_name},
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
            f"""SELECT sem.semester_id, sem.semester_name, sem.year_id, sem.start_date, sem.end_date,
                sem.status,
                sy.year_name as school_year_name,
                CASE
                    WHEN sem.semester_name LIKE '%上%' THEN 1
                    WHEN sem.semester_name LIKE '%下%' THEN 2
                    ELSE 1
                END as semester_type,
                CASE WHEN sem.status = 1 THEN 1 ELSE 0 END as is_current
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
        # 根据学期类型判断是否设为当前学期（下学期默认为当前）
        status = 1 if semester.semester_type == 2 else 0

        db.execute(
            """INSERT INTO semester
            (semester_name, year_id, start_date, end_date, status)
            VALUES (%s, %s, %s, %s, %s)""",
            (semester.semester_name, semester.school_year_id, semester.start_date,
             semester.end_date, status)
        )

        semester_id = db.lastrowid()

        # 如果是当前学期，更新学年的 is_current
        if status == 1:
            db.execute("UPDATE semester SET status = 0 WHERE semester_id != %s", (semester_id,))
            db.execute("UPDATE school_year SET is_current = 1 WHERE year_id = %s", (semester.school_year_id,))

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
    for_record_input: int = Query(0, description="1=德育录入选择学生，仅返回最小字段"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=10000),  # 放开上限支持导出全量数据
    user: User = Depends(get_current_user)
):
    """
    获取学生列表

    权限说明：
    - admin/jiaowu/xuefa: 可查看所有学生
    - cleader: 只能查看自己班级的学生
    """
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        manage_scope = _student_manage_scope(db, user, API_STUDENT_LIST)
        is_record_input_lookup = bool(for_record_input) and (
            check_moral_permission(user, 'moral_record_input')
            or check_moral_permission(user, 'moment_create')
        )

        if (
            not manage_scope.get("can_all")
            and not manage_scope.get("can_own_class")
            and not is_record_input_lookup
        ):
            raise HTTPException(403, "权限不足：需要学生查看权限")

        if not is_record_input_lookup:
            append_record_scope_condition(
                conditions,
                params,
                manage_scope,
                table_alias="s",
                username=user.username,
                recorder_field="student_id",
            )

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
        fields = (
            "s.student_id, s.name, s.class_id, s.grade_id, s.status, c.class_name, g.grade_name"
            if is_record_input_lookup
            else "s.*, c.class_name, g.grade_name"
        )
        data_query = f"""
            SELECT {fields}
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            JOIN grade g ON s.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY s.student_id
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        students = db.query_all(data_query, tuple(params))
        update_scope = _student_manage_scope(db, user, API_STUDENT_UPDATE)
        for student in students:
            can_edit = record_in_scope(
                student,
                update_scope,
                username=user.username,
                recorder_field="student_id",
            )
            student["can_edit"] = can_edit
            student["can_update_status"] = update_scope.get("can_all", False)

        return {
            "success": True,
            "data": {
                "items": students,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


def check_student_manage_permission(api_path: str):
    """
    学生管理权限检查

    允许有 student_manage 或 student_manage_own_class 权限的用户访问
    """
    async def check(user: User = Depends(get_current_user)):
        with get_moral_db() as db:
            has_full_permission = _has_scoped_permission(db, user, api_path, 'student_manage')
            has_own_class_permission = _has_scoped_permission(db, user, api_path, 'student_manage_own_class')

            if not has_full_permission and not has_own_class_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足：需要学生管理权限"
                )
        return user
    return check


@router.post("/students", summary="创建学生")
async def create_student(
    student: StudentCreate,
    request: Request,
    user: User = Depends(check_student_manage_permission(API_STUDENT_CREATE))
):
    """
    创建学生

    权限说明：
    - admin/jiaowu/xuefa (student_manage): 可创建任意班级学生
    - cleader (student_manage_own_class): 只能创建自己班级的学生
    """
    with get_moral_db() as db:
        create_scope = _student_manage_scope(db, user, API_STUDENT_CREATE)
        if not create_scope.get("can_all"):
            my_class_id = create_scope.get("my_class_id")
            if not create_scope.get("can_own_class") or my_class_id is None:
                raise HTTPException(403, "未分配班级，无法创建学生")
            if student.class_id != my_class_id:
                raise HTTPException(403, "只能创建本班学生")

        # 检查学号是否已存在
        existing = db.query_one(
            "SELECT student_id FROM student WHERE student_id = %s",
            (student.student_id,)
        )
        if existing:
            raise HTTPException(400, f"学号 {student.student_id} 已存在")

        # 从班级获取年级ID
        class_info = db.query_one(
            "SELECT grade_id FROM class WHERE class_id = %s",
            (student.class_id,)
        )
        if not class_info:
            raise HTTPException(400, "班级不存在")

        grade_id = class_info["grade_id"]

        # 从学号提取入学年份，设置入学日期
        enrollment_date = date.today()
        if len(student.student_id) >= 4:
            try:
                year = int(student.student_id[:4])
                enrollment_date = date(year, 9, 1)
            except ValueError:
                pass

        db.execute(
            """INSERT INTO student
            (student_id, name, gender, class_id, grade_id, original_grade_id, birthday, enrollment_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '在校')""",
            (student.student_id, student.name, student.gender, student.class_id,
             grade_id, grade_id, student.birthday, enrollment_date)
        )

        # 创建班级履历
        db.execute(
            """INSERT INTO student_class_history
            (student_id, class_id, grade_id, start_date, change_reason)
            VALUES (%s, %s, %s, %s, '入学')""",
            (student.student_id, student.class_id, grade_id, enrollment_date)
        )

        log_operation(
            db, user.username, user.role, 'INSERT', 'student', None,
            new_data={'student_id': student.student_id, 'name': student.name},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "学生创建成功"}


@router.post("/students/batch", summary="批量导入学生")
async def batch_import_students(
    data: StudentBatchImport,
    request: Request,
    user: User = Depends(check_student_manage_permission(API_STUDENT_BATCH))
):
    """
    批量导入学生

    通过班级名称匹配班级ID，支持大量学生快速导入。

    权限说明：
    - admin/jiaowu/xuefa (student_manage): 可导入任意班级学生
    - cleader (student_manage_own_class): 只能导入自己班级的学生
    """
    with get_moral_db() as db:
        # 获取班级映射
        classes = db.query_all("SELECT class_id, class_name, grade_id FROM class")
        class_map = {c['class_name']: c for c in classes}

        create_scope = _student_manage_scope(db, user, API_STUDENT_BATCH)
        my_class_id = create_scope.get("my_class_id")

        success_count = 0
        skip_count = 0
        errors = []

        for item in data.students:
            try:
                # 检查学号是否已存在
                existing = db.query_one(
                    "SELECT student_id FROM student WHERE student_id = %s",
                    (item.student_id,)
                )
                if existing:
                    skip_count += 1
                    continue

                # 匹配班级
                class_info = class_map.get(item.class_name)
                if not class_info:
                    errors.append(f"学号 {item.student_id}: 班级 '{item.class_name}' 不存在")
                    continue

                class_id = class_info['class_id']
                grade_id = class_info['grade_id']

                # 班主任只能导入自己班级的学生
                if not create_scope.get("can_all") and (
                    not create_scope.get("can_own_class") or class_id != my_class_id
                ):
                    errors.append(f"学号 {item.student_id}: 班主任只能导入本班学生")
                    continue

                # 解析生日
                birthday = None
                if item.birthday:
                    try:
                        birthday = datetime.strptime(item.birthday, '%Y-%m-%d').date()
                    except:
                        pass

                # 从学号提取入学年份
                enrollment_date = date.today()
                if len(item.student_id) >= 4:
                    try:
                        year = int(item.student_id[:4])
                        enrollment_date = date(year, 9, 1)
                    except ValueError:
                        pass

                # 插入学生
                db.execute(
                    """INSERT INTO student
                    (student_id, name, gender, class_id, grade_id, original_grade_id, birthday, enrollment_date, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '在校')""",
                    (item.student_id, item.name, item.gender, class_id, grade_id, grade_id, birthday, enrollment_date)
                )

                # 创建班级履历
                db.execute(
                    """INSERT INTO student_class_history
                    (student_id, class_id, grade_id, start_date, change_reason)
                    VALUES (%s, %s, %s, %s, '入学')""",
                    (item.student_id, class_id, grade_id, enrollment_date)
                )

                success_count += 1

            except Exception as e:
                errors.append(f"学号 {item.student_id}: {str(e)}")

        log_operation(
            db, user.username, user.role, 'BATCH_INSERT', 'student', None,
            new_data={'success': success_count, 'skip': skip_count, 'errors': len(errors)},
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "data": {
                "success_count": success_count,
                "skip_count": skip_count,
                "error_count": len(errors),
                "errors": errors[:10] if errors else []  # 只返回前10条错误
            },
            "message": f"导入完成：成功 {success_count} 条，跳过 {skip_count} 条已存在"
        }


@router.put("/students/{student_id}", summary="更新学生信息")
async def update_student(
    student_id: str,
    update_data: StudentUpdate,
    request: Request,
    user: User = Depends(check_student_manage_permission(API_STUDENT_UPDATE))
):
    """
    更新学生基本信息

    权限说明：
    - admin/jiaowu/xuefa (student_manage): 可编辑所有学生
    - cleader (student_manage_own_class): 只能编辑自己班级的学生
    - teacher: 无编辑权限
    """
    with get_moral_db() as db:
        # 获取学生信息
        student = db.query_one(
            """SELECT s.*, c.leader_name
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            WHERE s.student_id = %s""",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        update_scope = _student_manage_scope(db, user, API_STUDENT_UPDATE)
        if not record_in_scope(student, update_scope, username=user.username, recorder_field="student_id"):
            raise HTTPException(403, "只能编辑授权范围内学生信息")

        # 构建更新语句
        updates = []
        params = []

        if update_data.name is not None:
            updates.append("name = %s")
            params.append(update_data.name)

        if update_data.gender is not None:
            updates.append("gender = %s")
            params.append(update_data.gender)

        if update_data.birthday is not None:
            updates.append("birthday = %s")
            params.append(update_data.birthday)

        if update_data.roomid is not None:
            updates.append("roomid = %s")
            params.append(update_data.roomid)

        if update_data.rpid is not None:
            updates.append("rpid = %s")
            params.append(update_data.rpid)

        if update_data.class_id is not None:
            # 获取新班级的年级ID
            new_class = db.query_one(
                "SELECT grade_id FROM class WHERE class_id = %s",
                (update_data.class_id,)
            )
            if not new_class:
                raise HTTPException(400, "班级不存在")

            # 班主任不能把学生转到其他班级
            if not update_scope.get("can_all") and update_data.class_id != student['class_id']:
                raise HTTPException(403, "班主任不能调整学生班级")

            updates.append("class_id = %s")
            params.append(update_data.class_id)
            updates.append("grade_id = %s")
            params.append(new_class['grade_id'])

        if not updates:
            return {"success": True, "message": "无需更新"}

        params.append(student_id)
        update_query = f"UPDATE student SET {', '.join(updates)} WHERE student_id = %s"
        db.execute(update_query, tuple(params))

        log_operation(
            db, user.username, user.role, 'UPDATE', 'student', student_id,
            old_data={'name': student['name'], 'class_id': student['class_id']},
            new_data=update_data.dict(exclude_unset=True),
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "学生信息更新成功"}


@router.put("/students/{student_id}/status", summary="更新学生状态")
async def update_student_status(
    student_id: str,
    status: str = Query(..., description="状态：在校/休学/转出/毕业"),
    request: Request = None,
    user: User = Depends(get_current_user)
):
    """更新学生状态"""
    with get_moral_db() as db:
        status_scope = _student_manage_scope(db, user, API_STUDENT_UPDATE)
        if not status_scope.get("can_all"):
            raise HTTPException(403, "权限不足：需要学生管理权限")

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


# =============================================================================
# API 路由 - 操作日志查询
# =============================================================================

@router.get("/logs", summary="获取操作日志列表")
async def get_operation_logs(
    operator: Optional[str] = Query(None, description="操作人"),
    operation: Optional[str] = Query(None, description="操作类型：INSERT/UPDATE/DELETE"),
    table_name: Optional[str] = Query(None, description="表名"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_permission('report_view_all'))
):
    """
    获取操作日志列表

    权限要求：admin/jiaowu/xuefa
    """
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if operator:
            conditions.append("operator LIKE %s")
            params.append(f"%{operator}%")

        if operation:
            conditions.append("operation = %s")
            params.append(operation)

        if table_name:
            conditions.append("table_name = %s")
            params.append(table_name)

        if start_date:
            conditions.append("DATE(created_at) >= %s")
            params.append(start_date)

        if end_date:
            conditions.append("DATE(created_at) <= %s")
            params.append(end_date)

        where_clause = " AND ".join(conditions)

        # 查询总数
        count_query = f"SELECT COUNT(*) FROM moral_operation_log WHERE {where_clause}"
        total = db.query_value(count_query, tuple(params))

        # 分页查询
        offset = (page - 1) * page_size
        data_query = f"""
            SELECT * FROM moral_operation_log
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        logs = db.query_all(data_query, tuple(params))

        return {
            "success": True,
            "data": {
                "items": logs,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size
            }
        }


# =============================================================================
# API 路由 - 系统配置
# =============================================================================

# 默认系统配置
DEFAULT_CONFIG = {
    "evaluation_base_score": 100,
    "evaluation_weights": {
        "daily": 0.3,
        "school_event": 0.3,
        "task": 0.2,
        "punishment": -0.2
    },
    "birthday_reminder_days": 7,
    "semester_start_month": 9,
    "punishment_types": [
        {"action": "warning", "name": "警告", "level": None},
        {"action": "serious_warning", "name": "严重警告", "level": "一级"},
        {"action": "criticism", "name": "通报", "level": "二级"},
        {"action": "demerit", "name": "记过", "level": "三级"},
        {"action": "observation", "name": "留校查看", "level": "四级"}
    ]
}


@router.get("/config", summary="获取系统配置")
async def get_system_config(
    user: User = Depends(require_permission('report_view_all'))
):
    """
    获取系统配置

    权限要求：admin/jiaowu/xuefa
    """
    with get_moral_db() as db:
        # 查询配置表
        configs = db.query_all(
            "SELECT config_key, config_value FROM moral_config"
        )

        if configs:
            config_dict = {c['config_key']: c['config_value'] for c in configs}
            # 解析JSON配置
            import json
            result = {}
            for key, value in DEFAULT_CONFIG.items():
                if key in config_dict:
                    try:
                        result[key] = json.loads(config_dict[key])
                    except:
                        result[key] = config_dict[key]
                else:
                    result[key] = value
            return {"success": True, "data": result}
        else:
            return {"success": True, "data": DEFAULT_CONFIG}


class ConfigUpdate(BaseModel):
    """更新系统配置"""
    evaluation_base_score: Optional[int] = Field(None, description="评价基础分", ge=0, le=200)
    evaluation_weights: Optional[dict] = Field(None, description="评价权重配置")
    birthday_reminder_days: Optional[int] = Field(None, description="生日提前提醒天数", ge=1, le=30)
    semester_start_month: Optional[int] = Field(None, description="学期开始月份", ge=1, le=12)
    punishment_types: Optional[List[dict]] = Field(None, description="处罚类型配置")


@router.put("/config", summary="更新系统配置")
async def update_system_config(
    config: ConfigUpdate,
    request: Request,
    user: User = Depends(require_permission('semester_manage'))
):
    """
    更新系统配置

    权限要求：admin/jiaowu
    """
    import json

    with get_moral_db() as db:
        update_data = config.dict(exclude_unset=True)

        for key, value in update_data.items():
            if value is not None:
                json_value = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)

                # 检查是否存在
                existing = db.query_one(
                    "SELECT config_id FROM moral_config WHERE config_key = %s",
                    (key,)
                )

                if existing:
                    db.execute(
                        "UPDATE moral_config SET config_value = %s, updated_at = datetime('now','localtime') WHERE config_key = %s",
                        (json_value, key)
                    )
                else:
                    db.execute(
                        "INSERT INTO moral_config (config_key, config_value) VALUES (%s, %s)",
                        (key, json_value)
                    )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'moral_config', None,
            new_data=update_data,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "配置更新成功"}
