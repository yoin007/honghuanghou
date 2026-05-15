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

from .api_permission import require_configured_api_permission
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
from models.datas_api.auth import User, is_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["系统管理"])


def parse_birthday(birthday_str) -> Optional[date]:
    """
    解析生日字段，兼容多种格式：
    - YYYY-MM-DD（标准格式）
    - YYYY/MM/DD
    - MM/DD/YYYY（美国格式）
    - Excel 数字日期（如 45321 表示 2023-03-15）
    - 中文格式 YYYY年MM月DD日

    Args:
        birthday_str: 生日字符串或数字

    Returns:
        date 对象或 None
    """
    if not birthday_str:
        return None

    # 尝试数字类型（Excel 日期）
    if isinstance(birthday_str, (int, float)):
        try:
            # Excel 日期序列号：从 1900-01-01 开始（注意 Excel bug：1900-02-29 不存在）
            # 序列号 1 = 1900-01-01
            from datetime import timedelta
            base_date = date(1899, 12, 30)  # Excel 基准日期（修正 bug）
            return base_date + timedelta(days=int(birthday_str))
        except (ValueError, OverflowError):
            pass

    # 转为字符串处理
    birthday_str = str(birthday_str).strip()

    # 尝试多种日期格式
    date_formats = [
        '%Y-%m-%d',       # 2008-05-15
        '%Y/%m/%d',       # 2008/05/15
        '%m/%d/%Y',       # 05/15/2008（美国格式）
        '%d/%m/%Y',       # 15/05/2008（欧洲格式）
        '%Y.%m.%d',       # 2008.05.15
        '%Y年%m月%d日',   # 2008年05月15日
        '%Y%m%d',         # 20080515（无分隔符）
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(birthday_str, fmt).date()
        except ValueError:
            continue

    # 尝试解析为数字（可能是字符串形式的 Excel 日期）
    try:
        num = int(float(birthday_str))
        from datetime import timedelta
        base_date = date(1899, 12, 30)
        return base_date + timedelta(days=num)
    except (ValueError, TypeError):
        pass

    return None

API_STUDENT_LIST = "/api/moral/admin/students"
API_STUDENT_CREATE = "/api/moral/admin/students/create"
API_STUDENT_BATCH = "/api/moral/admin/students/batch"
API_STUDENT_UPDATE = "/api/moral/admin/students/update"

API_TEACHERS = "/api/moral/admin/teachers"
API_GRADES = "/api/moral/admin/grades"
API_GRADE_CREATE = "/api/moral/admin/grades/create"
API_GRADE_UPDATE = "/api/moral/admin/grades/{grade_id}"
API_GRADE_PROMOTE_PREVIEW = "/api/moral/admin/grades/promote/preview"
API_GRADE_PROMOTE_EXECUTE = "/api/moral/admin/grades/promote/execute"
API_GRADES_ARCHIVED = "/api/moral/admin/grades/archived"
API_CLASSES = "/api/moral/admin/classes"
API_CLASS_CREATE = "/api/moral/admin/classes/create"
API_CLASS_UPDATE = "/api/moral/admin/classes/{class_id}"
API_SCHOOL_YEARS = "/api/moral/admin/school-years"
API_SCHOOL_YEAR_CREATE = "/api/moral/admin/school-years/create"
API_SEMESTERS = "/api/moral/admin/semesters"
API_SEMESTER_CREATE = "/api/moral/admin/semesters/create"
API_SEMESTER_UPDATE = "/api/moral/admin/semesters/{semester_id}"
API_SEMESTER_SET_CURRENT = "/api/moral/admin/semesters/{semester_id}/set-current"
API_LOGS = "/api/moral/admin/logs"
API_CONFIG = "/api/moral/admin/config"



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
    leader_name: Optional[str] = Field(None, description="班主任姓名（单值，兼容旧数据）")
    leader_names: Optional[str] = Field(None, max_length=200, description="班主任姓名列表（多人，逗号分隔）")
    leader_wxid: Optional[str] = Field(None, description="班主任微信ID")
    roomid: Optional[str] = Field(None, description="微信群ID")


class ClassUpdate(BaseModel):
    """更新班级"""
    class_code: Optional[str] = Field(None, description="班级代码")
    grade_id: Optional[int] = Field(None, description="级号ID")
    class_number: Optional[int] = Field(None, description="班号")
    class_name: Optional[str] = Field(None, description="班级名称")
    leader_name: Optional[str] = Field(None, description="班主任姓名（单值，兼容旧数据）")
    leader_names: Optional[str] = Field(None, max_length=200, description="班主任姓名列表（多人，逗号分隔）")
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


class SemesterUpdate(BaseModel):
    """更新学期"""
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")
    semester_name: Optional[str] = Field(None, description="学期名称")


# =============================================================================
# API 路由 - 级号管理
# =============================================================================

@router.get("/teachers", summary="获取教师列表")
async def get_teachers_for_config(user: User = Depends(require_configured_api_permission(API_TEACHERS, allow_missing=False))):
    """获取教师列表用于级号/班级配置（选择年级主任/班主任）"""
    with get_moral_db() as db:
        teachers = db.query_all(
            """SELECT teacher_id, name, subject
            FROM teacher
            WHERE is_active = 1 AND COALESCE(identity_type, 'teacher') = 'teacher'
            ORDER BY name"""
        )
        return {"success": True, "data": {"items": teachers, "total": len(teachers)}}


@router.get("/grades", summary="获取级号列表")
async def get_grades(user: User = Depends(require_configured_api_permission(API_GRADES, allow_missing=False))):
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
    user: User = Depends(require_configured_api_permission(API_GRADE_CREATE, allow_missing=False))
):
    """创建级号"""
    with get_moral_db() as db:
        # 检查是否已存在
        existing = db.query_one(
            "SELECT grade_id FROM grade WHERE enrollment_year = ?",
            (grade.enrollment_year,)
        )
        if existing:
            raise HTTPException(400, f"{grade.enrollment_year}年级已存在")

        db.execute(
            "INSERT INTO grade (grade_name, enrollment_year) VALUES (?, ?)",
            (grade.grade_name, grade.enrollment_year)
        )

        grade_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'grade', grade_id,
            new_data={'grade_name': grade.grade_name},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "级号创建成功", "data": {"grade_id": grade_id}}


class GradeUpdate(BaseModel):
    """级号更新请求"""
    grade_name: Optional[str] = Field(None, max_length=50)
    enrollment_year: Optional[int] = Field(None)
    leader_names: Optional[str] = Field(None, max_length=200)


@router.put("/grades/{grade_id}", summary="更新级号")
async def update_grade(
    grade_id: int,
    data: GradeUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_GRADE_UPDATE, allow_missing=False))
):
    """更新级号信息，包括年级主任（支持多人）"""
    with get_moral_db() as db:
        # 检查级号是否存在
        existing = db.query_one(
            "SELECT grade_id FROM grade WHERE grade_id = ?",
            (grade_id,)
        )
        if not existing:
            raise HTTPException(404, "级号不存在")

        # 构建更新字段
        updates = []
        params = []
        if data.grade_name:
            updates.append("grade_name = ?")
            params.append(data.grade_name)
        if data.enrollment_year:
            updates.append("enrollment_year = ?")
            params.append(data.enrollment_year)
        if data.leader_names is not None:
            updates.append("leader_names = ?")
            params.append(data.leader_names)
            # 同时更新 leader_ids（通过教师姓名查找 teacher_id）
            if data.leader_names:
                leader_names_list = [n.strip() for n in data.leader_names.split(',') if n.strip()]
                leader_ids_list = []
                for name in leader_names_list:
                    teacher = db.query_one(
                        "SELECT teacher_id FROM teacher WHERE name = ?",
                        (name,)
                    )
                    if teacher:
                        leader_ids_list.append(teacher['teacher_id'])
                updates.append("leader_ids = ?")
                params.append(','.join(leader_ids_list) if leader_ids_list else '')
            else:
                updates.append("leader_ids = ?")
                params.append('')

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(grade_id)
        db.execute(
            f"UPDATE grade SET {', '.join(updates)} WHERE grade_id = ?",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'grade', grade_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "级号更新成功"}


@router.delete("/grades/{grade_id}", summary="删除级号")
async def delete_grade(
    grade_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_GRADE_UPDATE, allow_missing=False))
):
    """删除级号"""
    with get_moral_db() as db:
        # 检查是否有关联班级
        class_count = db.query_value(
            "SELECT COUNT(*) FROM class WHERE grade_id = ?",
            (grade_id,)
        )
        if class_count > 0:
            raise HTTPException(400, "该级号下存在班级，无法删除")

        db.execute("DELETE FROM grade WHERE grade_id = ?", (grade_id,))

        log_operation(
            db, user.username, user.role, 'DELETE', 'grade', grade_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "级号已删除"}


# =============================================================================
# API 路由 - 升年级管理
# =============================================================================

@router.get("/grades/promote/preview", summary="预览升年级情况")
async def preview_grade_promotion(
    user: User = Depends(require_configured_api_permission(API_GRADE_PROMOTE_PREVIEW, allow_missing=False))
):
    """
    预览升年级情况

    权限要求：xuefa/admin

    返回：
    - 即将毕业的学生列表（years_after_enrollment >= 2）
    - 即将归档的年级列表
    - 当前学年信息
    - 下一学年信息（如已创建）
    """
    import json
    from datetime import datetime

    with get_moral_db() as db:
        # 获取当前年份
        current_year = datetime.now().year

        # 获取配置的年级层级映射（如果有）
        level_config = db.query_all(
            "SELECT grade_id, level_name FROM grade_level_config"
        )
        level_map = {c['grade_id']: c['level_name'] for c in level_config} if level_config else {}

        # 计算各年级的 years_after_enrollment
        grades = db.query_all(
            """SELECT g.grade_id, g.grade_name, g.enrollment_year, g.is_archived,
                (SELECT COUNT(*) FROM student WHERE grade_id = g.grade_id AND status = '在校') as student_count
               FROM grade g
               WHERE g.is_archived = 0
               ORDER BY g.enrollment_year DESC"""
        )

        # 标记即将毕业的年级（高三）
        graduating_grades = []
        promoting_grades = []

        for grade in grades:
            years_after = current_year - grade['enrollment_year']
            grade['years_after_enrollment'] = years_after
            grade['current_level'] = level_map.get(grade['grade_id'], f"{years_after+1}年级")

            if years_after >= 2:
                # 高三，即将毕业
                graduating_grades.append(grade)
            else:
                # 高一/高二，即将升年级
                grade['next_level'] = level_map.get(grade['grade_id'], f"{years_after+2}年级")
                promoting_grades.append(grade)

        # 获取即将毕业的学生详情
        graduating_students = []
        for grade in graduating_grades:
            students = db.query_all(
                """SELECT s.student_id, s.name, s.class_id, s.grade_id,
                   c.class_name, g.grade_name
                   FROM student s
                   JOIN class c ON s.class_id = c.class_id
                   JOIN grade g ON s.grade_id = g.grade_id
                   WHERE s.grade_id = ? AND s.status = '在校'
                   ORDER BY c.class_number, s.student_id""",
                (grade['grade_id'],)
            )
            graduating_students.extend(students)

        # 获取当前学年
        current_school_year = db.query_one(
            "SELECT * FROM school_year WHERE is_current = 1"
        )

        # 获取下一学年（根据 start_date 提取年份 + 1 查找）
        next_school_year = None
        if current_school_year and current_school_year.get('start_date'):
            try:
                # 从 start_date 提取年份（如 '2025-09-01' → 2025）
                start_date_str = current_school_year['start_date']
                if isinstance(start_date_str, str):
                    start_year = int(start_date_str.split('-')[0])
                elif isinstance(start_date_str, date):
                    start_year = start_date_str.year
                else:
                    start_year = None

                if start_year:
                    next_start_year = start_year + 1
                    # 从 year_name 查找下一学年（如 '2026-2027学年'）
                    next_school_year = db.query_one(
                        "SELECT * FROM school_year WHERE year_name LIKE ?",
                        (f"%{next_start_year}%",)
                    )
            except Exception as e:
                logger.warning(f"解析学年日期失败: {e}")

        return {
            "success": True,
            "data": {
                "current_year": current_year,
                "current_school_year": current_school_year,
                "next_school_year": next_school_year,
                "graduating_grades": graduating_grades,
                "graduating_students": graduating_students,
                "graduating_count": len(graduating_students),
                "promoting_grades": promoting_grades,
                "has_next_year": next_school_year is not None
            }
        }


class PromoteExecuteRequest(BaseModel):
    """执行升年级请求"""
    next_year_id: Optional[int] = Field(None, description="下一学年ID（可选，用于结转）")


@router.post("/grades/promote/execute", summary="执行升年级")
async def execute_grade_promotion(
    request_data: PromoteExecuteRequest,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_GRADE_PROMOTE_EXECUTE, allow_missing=False))
):
    """
    执行升年级

    权限要求：xuefa/admin

    流程：
    1. 高三学生（years_after_enrollment >= 2）→ status='毕业'
    2. 对应 grade 记录 → is_archived=1, archived_at=now()
    3. 更新学年 is_current 标记（如有下一学年）

    注意：grade_id 不变，年级层级由 enrollment_year 动态计算
    """
    from datetime import datetime

    with get_moral_db() as db:
        current_year = datetime.now().year
        today = date.today()
        archive_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        result = {
            'graduated_students': 0,
            'archived_grades': 0,
            'errors': []
        }

        # 查询所有未归档的年级
        grades = db.query_all(
            """SELECT g.grade_id, g.grade_name, g.enrollment_year
               FROM grade g
               WHERE g.is_archived = 0
               ORDER BY g.enrollment_year"""
        )

        for grade in grades:
            years_after = current_year - grade['enrollment_year']

            if years_after >= 2:
                # 高三，执行毕业和归档
                try:
                    # 标记该年级所有在校生为毕业
                    graduated_count = db.query_value(
                        """SELECT COUNT(*) FROM student
                           WHERE grade_id = ? AND status = '在校'""",
                        (grade['grade_id'],)
                    )

                    db.execute(
                        """UPDATE student SET status = '毕业', status_date = ?
                           WHERE grade_id = ? AND status = '在校'""",
                        (today, grade['grade_id'])
                    )

                    # 结束班级履历
                    db.execute(
                        """UPDATE student_class_history SET end_date = ?
                           WHERE grade_id = ? AND end_date IS NULL""",
                        (today, grade['grade_id'])
                    )

                    # 归档年级
                    db.execute(
                        """UPDATE grade SET is_archived = 1, archived_at = ?
                           WHERE grade_id = ?""",
                        (archive_time, grade['grade_id'])
                    )

                    result['graduated_students'] += graduated_count
                    result['archived_grades'] += 1

                    logger.info(
                        f"年级归档：{grade['grade_name']}，毕业学生 {graduated_count} 人"
                    )

                except Exception as e:
                    result['errors'].append(f"{grade['grade_name']}: {str(e)}")
                    logger.error(f"年级归档失败：{grade['grade_name']} - {e}")

        # 更新学年标记（如果提供了下一学年ID）
        if request_data.next_year_id:
            next_year = db.query_one(
                "SELECT * FROM school_year WHERE year_id = ?",
                (request_data.next_year_id,)
            )
            if next_year:
                # 取消当前学年标记
                db.execute("UPDATE school_year SET is_current = 0")
                # 设置新学年为当前
                db.execute(
                    "UPDATE school_year SET is_current = 1 WHERE year_id = ?",
                    (request_data.next_year_id,)
                )

                # 执行任务结转（如果有未完成任务）
                try:
                    # 获取旧学年ID
                    old_year = db.query_one("SELECT year_id FROM school_year WHERE is_current = 0 ORDER BY start_date DESC LIMIT 1")
                    if old_year and old_year['year_id'] != request_data.next_year_id:
                        from .carryover import execute_task_carryover
                        carryover_result = execute_task_carryover(db, old_year['year_id'], request_data.next_year_id)
                        result['carryover'] = carryover_result
                        logger.info(f"任务结转完成：{carryover_result}")
                except Exception as e:
                    result['errors'].append(f"任务结转: {str(e)}")
                    logger.error(f"任务结转失败：{e}")

        # 记录操作日志
        log_operation(
            db, user.username, user.role, 'PROMOTE', 'grade', None,
            new_data={
                'graduated_students': result['graduated_students'],
                'archived_grades': result['archived_grades'],
                'next_year_id': request_data.next_year_id
            },
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "message": f"升年级完成：毕业 {result['graduated_students']} 名学生，归档 {result['archived_grades']} 个年级",
            "data": result
        }


@router.get("/grades/archived", summary="获取已归档年级列表")
async def get_archived_grades(
    user: User = Depends(require_configured_api_permission(API_GRADES_ARCHIVED, allow_missing=False))
):
    """
    获取已归档年级列表

    权限要求：admin/jiaowu/xuefa

    用于查看历史年级（已毕业）
    """
    with get_moral_db() as db:
        grades = db.query_all(
            """SELECT g.*,
                (SELECT COUNT(*) FROM class WHERE grade_id = g.grade_id) as class_count,
                (SELECT COUNT(*) FROM student WHERE grade_id = g.grade_id) as total_student_count,
                (SELECT COUNT(*) FROM student WHERE grade_id = g.grade_id AND status = '毕业') as graduated_count
               FROM grade g
               WHERE g.is_archived = 1
               ORDER BY g.enrollment_year DESC"""
        )

        return {"success": True, "data": grades}


# =============================================================================
# API 路由 - 班级管理
# =============================================================================

@router.get("/classes", summary="获取班级列表")
async def get_classes(
    grade_id: Optional[int] = Query(None),
    is_active: Optional[int] = Query(None),
    for_record_input: Optional[int] = Query(None, description="是否用于录入记录场景（1=任教+管理班级）"),
    for_evaluation: Optional[int] = Query(None, description="是否用于德育评价场景（1=只管理班级）"),
    user: User = Depends(require_configured_api_permission(API_CLASSES, allow_missing=False))
):
    """获取班级列表

    场景说明：
    - for_record_input=1：日常事件/点滴记录，班主任看任教+管理班级
    - for_evaluation=1：德育评价，班主任只看管理班级
    - admin/jiaowu/xuefa/g_leader：始终看相应范围班级
    """
    from .base import (
        get_teacher_teaching_class_ids,
        get_teacher_class_ids,
        get_teacher_grade_ids,
        has_user_role,
        is_admin_user,
    )

    with get_moral_db() as db:
        conditions = ["c.is_active = 1"]
        params = []

        # 按场景过滤班级
        if for_record_input == 1 or for_evaluation == 1:
            # admin/jiaowu/xuefa 可以看所有班级
            if is_admin_user(user) or has_user_role(user, 'jiaowu') or has_user_role(user, 'xuefa'):
                # 不额外过滤
                pass
            else:
                # 计算可见班级ID列表
                visible_class_ids = set()

                # 年级主任管理的年级班级
                if has_user_role(user, 'g_leader'):
                    grade_ids = get_teacher_grade_ids(user, db)
                    if grade_ids:
                        grade_classes = db.query_all(
                            f"SELECT class_id FROM class WHERE grade_id IN ({','.join(map(str, grade_ids))}) AND is_active = 1"
                        )
                        visible_class_ids.update(c['class_id'] for c in grade_classes)

                # 班主任班级
                if has_user_role(user, 'cleader'):
                    own_class_ids = get_teacher_class_ids(user, db)
                    visible_class_ids.update(own_class_ids)

                # 任教班级（只在 for_record_input 场景添加）
                if for_record_input == 1:
                    teaching_ids = get_teacher_teaching_class_ids(user, db)
                    visible_class_ids.update(teaching_ids)

                if not visible_class_ids:
                    return {"success": True, "data": []}

                conditions.append(f"c.class_id IN ({','.join(map(str, visible_class_ids))})")

        if grade_id:
            conditions.append("c.grade_id = ?")
            params.append(grade_id)

        if is_active is not None:
            conditions.append("c.is_active = ?")
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
    user: User = Depends(require_configured_api_permission(API_CLASS_CREATE, allow_missing=False))
):
    """创建班级"""
    with get_moral_db() as db:
        # 检查班级代码是否已存在
        existing = db.query_one(
            "SELECT class_id FROM class WHERE class_code = ?",
            (cls.class_code,)
        )
        if existing:
            raise HTTPException(400, f"班级代码 {cls.class_code} 已存在")

        # 处理 leader_names → leader_ids
        leader_ids = ''
        if cls.leader_names:
            leader_names_list = [n.strip() for n in cls.leader_names.split(',') if n.strip()]
            leader_ids_list = []
            for name in leader_names_list:
                teacher = db.query_one(
                    "SELECT teacher_id FROM teacher WHERE name = ?",
                    (name,)
                )
                if teacher:
                    leader_ids_list.append(teacher['teacher_id'])
            leader_ids = ','.join(leader_ids_list) if leader_ids_list else ''

        db.execute(
            """INSERT INTO class
            (class_code, grade_id, class_number, class_name, leader_name, leader_names, leader_ids, leader_wxid, roomid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cls.class_code, cls.grade_id, cls.class_number, cls.class_name,
             cls.leader_name, cls.leader_names or '', leader_ids, cls.leader_wxid, cls.roomid)
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
    user: User = Depends(require_configured_api_permission(API_CLASS_UPDATE, allow_missing=False))
):
    """更新班级"""
    with get_moral_db() as db:
        # 构建动态更新
        updates = []
        params = []

        if cls.class_code is not None:
            updates.append("class_code = ?")
            params.append(cls.class_code)
        if cls.grade_id is not None:
            updates.append("grade_id = ?")
            params.append(cls.grade_id)
        if cls.class_number is not None:
            updates.append("class_number = ?")
            params.append(cls.class_number)
        if cls.class_name is not None:
            updates.append("class_name = ?")
            params.append(cls.class_name)
        if cls.leader_name is not None:
            updates.append("leader_name = ?")
            params.append(cls.leader_name)
        if cls.leader_names is not None:
            updates.append("leader_names = ?")
            params.append(cls.leader_names)
            # 同时更新 leader_ids（通过教师姓名查找 teacher_id）
            if cls.leader_names:
                leader_names_list = [n.strip() for n in cls.leader_names.split(',') if n.strip()]
                leader_ids_list = []
                for name in leader_names_list:
                    teacher = db.query_one(
                        "SELECT teacher_id FROM teacher WHERE name = ?",
                        (name,)
                    )
                    if teacher:
                        leader_ids_list.append(teacher['teacher_id'])
                updates.append("leader_ids = ?")
                params.append(','.join(leader_ids_list) if leader_ids_list else '')
            else:
                updates.append("leader_ids = ?")
                params.append('')
        if cls.leader_wxid is not None:
            updates.append("leader_wxid = ?")
            params.append(cls.leader_wxid)
        if cls.roomid is not None:
            updates.append("roomid = ?")
            params.append(cls.roomid)
        if cls.established is not None:
            updates.append("established = ?")
            params.append(cls.established)
        if cls.motto is not None:
            updates.append("motto = ?")
            params.append(cls.motto)
        if cls.location is not None:
            updates.append("location = ?")
            params.append(cls.location)

        if not updates:
            return {"success": True, "message": "无需更新"}

        params.append(class_id)
        sql = f"UPDATE class SET {', '.join(updates)} WHERE class_id = ?"
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
    user: User = Depends(require_configured_api_permission(API_CLASS_UPDATE, allow_missing=False))
):
    """删除班级"""
    with get_moral_db() as db:
        # 检查是否有学生
        student_count = db.query_value(
            "SELECT COUNT(*) FROM student WHERE class_id = ? AND status = '在校'",
            (class_id,)
        )
        if student_count > 0:
            raise HTTPException(400, f"该班级下有 {student_count} 名在校生，无法删除")

        db.execute("DELETE FROM class WHERE class_id = ?", (class_id,))

        log_operation(
            db, user.username, user.role, 'DELETE', 'class', class_id,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "班级已删除"}


# =============================================================================
# API 路由 - 学年学期管理
# =============================================================================

@router.get("/school-years", summary="获取学年列表")
async def get_school_years(user: User = Depends(require_configured_api_permission(API_SCHOOL_YEARS, allow_missing=False))):
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
    user: User = Depends(require_configured_api_permission(API_SCHOOL_YEAR_CREATE, allow_missing=False))
):
    """创建学年"""
    with get_moral_db() as db:
        # 根据起始年份自动计算开始和结束日期
        start_date = date(year.start_year, 9, 1)
        end_date = date(year.start_year + 1, 7, 15)

        db.execute(
            """INSERT INTO school_year
            (year_name, start_date, end_date, is_current)
            VALUES (?, ?, ?, ?)""",
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
    user: User = Depends(require_configured_api_permission(API_SEMESTERS, allow_missing=False))
):
    """获取学期列表"""
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if year_id:
            conditions.append("sem.year_id = ?")
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
    user: User = Depends(require_configured_api_permission(API_SEMESTER_CREATE, allow_missing=False))
):
    """创建学期"""
    with get_moral_db() as db:
        # 根据学期类型判断是否设为当前学期（下学期默认为当前）
        status = 1 if semester.semester_type == 2 else 0

        db.execute(
            """INSERT INTO semester
            (semester_name, year_id, start_date, end_date, status)
            VALUES (?, ?, ?, ?, ?)""",
            (semester.semester_name, semester.school_year_id, semester.start_date,
             semester.end_date, status)
        )

        semester_id = db.lastrowid()

        # 如果是当前学期，更新学年的 is_current
        if status == 1:
            db.execute("UPDATE semester SET status = 0 WHERE semester_id != ?", (semester_id,))
            db.execute("UPDATE school_year SET is_current = 1 WHERE year_id = ?", (semester.school_year_id,))

        log_operation(
            db, user.username, user.role, 'INSERT', 'semester', semester_id,
            new_data={'semester_name': semester.semester_name},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "学期创建成功", "data": {"semester_id": semester_id}}


@router.put("/semesters/{semester_id}", summary="更新学期")
async def update_semester(
    semester_id: int,
    semester_update: SemesterUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_SEMESTER_UPDATE, allow_missing=False))
):
    """更新学期信息（起始时间、结束时间、名称）"""
    with get_moral_db() as db:
        # 检查学期是否存在
        semester = db.query_one(
            "SELECT * FROM semester WHERE semester_id = ?",
            (semester_id,)
        )
        if not semester:
            raise HTTPException(404, "学期不存在")

        # 构建更新字段
        update_fields = []
        update_values = []
        old_data = {}

        if semester_update.start_date is not None:
            update_fields.append("start_date = ?")
            update_values.append(semester_update.start_date)
            old_data['start_date'] = semester['start_date']

        if semester_update.end_date is not None:
            update_fields.append("end_date = ?")
            update_values.append(semester_update.end_date)
            old_data['end_date'] = semester['end_date']

        if semester_update.semester_name is not None:
            update_fields.append("semester_name = ?")
            update_values.append(semester_update.semester_name)
            old_data['semester_name'] = semester['semester_name']

        if not update_fields:
            return {"success": True, "message": "无更新内容"}

        # 执行更新
        update_values.append(semester_id)
        db.execute(
            f"UPDATE semester SET {', '.join(update_fields)} WHERE semester_id = ?",
            tuple(update_values)
        )

        # 记录操作日志
        log_operation(
            db, user.username, user.role, 'UPDATE', 'semester', semester_id,
            old_data=old_data,
            new_data={
                'start_date': semester_update.start_date,
                'end_date': semester_update.end_date,
                'semester_name': semester_update.semester_name
            },
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "学期更新成功"}


@router.post("/semesters/{semester_id}/set-current", summary="设置当前学期")
async def set_current_semester(
    semester_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_SEMESTER_SET_CURRENT, allow_missing=False))
):
    """设置当前学期"""
    with get_moral_db() as db:
        semester = db.query_one(
            "SELECT * FROM semester WHERE semester_id = ?",
            (semester_id,)
        )
        if not semester:
            raise HTTPException(404, "学期不存在")

        # 取消其他学期的当前状态
        db.execute("UPDATE semester SET status = 0")

        # 设置当前学期
        db.execute(
            "UPDATE semester SET status = 1 WHERE semester_id = ?",
            (semester_id,)
        )

        # 同时设置学年为当前
        db.execute(
            "UPDATE school_year SET is_current = 0"
        )
        db.execute(
            "UPDATE school_year SET is_current = 1 WHERE year_id = ?",
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
    user: User = Depends(require_configured_api_permission(API_STUDENT_LIST, allow_missing=False))
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
            conditions.append("s.class_id = ?")
            params.append(class_id)

        if grade_id:
            conditions.append("s.grade_id = ?")
            params.append(grade_id)

        if status:
            conditions.append("s.status = ?")
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
            LIMIT ? OFFSET ?
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
    async def check(user: User = Depends(require_configured_api_permission(api_path, allow_missing=False))):
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
            "SELECT student_id FROM student WHERE student_id = ?",
            (student.student_id,)
        )
        if existing:
            raise HTTPException(400, f"学号 {student.student_id} 已存在")

        # 从班级获取年级ID
        class_info = db.query_one(
            "SELECT grade_id FROM class WHERE class_id = ?",
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, '在校')""",
            (student.student_id, student.name, student.gender, student.class_id,
             grade_id, grade_id, student.birthday, enrollment_date)
        )

        # 创建班级履历
        db.execute(
            """INSERT INTO student_class_history
            (student_id, class_id, grade_id, start_date, change_reason)
            VALUES (?, ?, ?, ?, '入学')""",
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

                # 解析生日（兼容多种格式）
                birthday = parse_birthday(item.birthday)

                # 从学号提取入学年份
                enrollment_date = date.today()
                if len(item.student_id) >= 4:
                    try:
                        year = int(item.student_id[:4])
                        enrollment_date = date(year, 9, 1)
                    except ValueError:
                        pass

                # 检查学号是否已存在
                existing = db.query_one(
                    "SELECT student_id, class_id FROM student WHERE student_id = ?",
                    (item.student_id,)
                )

                if existing:
                    # 学生已存在，更新信息
                    old_class_id = existing['class_id']

                    db.execute(
                        """UPDATE student SET
                        name = ?, gender = ?, class_id = ?, grade_id = ?, birthday = ?
                        WHERE student_id = ?""",
                        (item.name, item.gender, class_id, grade_id, birthday, item.student_id)
                    )

                    # 如果班级变更，记录班级履历
                    if old_class_id != class_id:
                        db.execute(
                            """INSERT INTO student_class_history
                            (student_id, class_id, grade_id, start_date, change_reason)
                            VALUES (?, ?, ?, ?, '批量导入更新班级')""",
                            (item.student_id, class_id, grade_id, enrollment_date)
                        )

                    skip_count += 1  # 更新计数
                else:
                    # 新学生，插入
                    db.execute(
                        """INSERT INTO student
                        (student_id, name, gender, class_id, grade_id, original_grade_id, birthday, enrollment_date, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, '在校')""",
                        (item.student_id, item.name, item.gender, class_id, grade_id, grade_id, birthday, enrollment_date)
                    )

                    # 创建班级履历
                    db.execute(
                        """INSERT INTO student_class_history
                        (student_id, class_id, grade_id, start_date, change_reason)
                        VALUES (?, ?, ?, ?, '入学')""",
                        (item.student_id, class_id, grade_id, enrollment_date)
                    )

                    success_count += 1

            except Exception as e:
                errors.append(f"学号 {item.student_id}: {str(e)}")

        log_operation(
            db, user.username, user.role, 'BATCH_IMPORT', 'student', None,
            new_data={'created': success_count, 'updated': skip_count, 'errors': len(errors)},
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "data": {
                "success_count": success_count,
                "update_count": skip_count,  # rename for clarity
                "skip_count": skip_count,  # keep for backward compatibility
                "error_count": len(errors),
                "errors": errors[:10] if errors else []  # 只返回前10条错误
            },
            "message": f"导入完成：新增 {success_count} 条，更新 {skip_count} 条"
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
            WHERE s.student_id = ?""",
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
            updates.append("name = ?")
            params.append(update_data.name)

        if update_data.gender is not None:
            updates.append("gender = ?")
            params.append(update_data.gender)

        if update_data.birthday is not None:
            updates.append("birthday = ?")
            params.append(update_data.birthday)

        if update_data.roomid is not None:
            updates.append("roomid = ?")
            params.append(update_data.roomid)

        if update_data.rpid is not None:
            updates.append("rpid = ?")
            params.append(update_data.rpid)

        if update_data.class_id is not None:
            # 获取新班级的年级ID
            new_class = db.query_one(
                "SELECT grade_id FROM class WHERE class_id = ?",
                (update_data.class_id,)
            )
            if not new_class:
                raise HTTPException(400, "班级不存在")

            # 班主任不能把学生转到其他班级
            if not update_scope.get("can_all") and update_data.class_id != student['class_id']:
                raise HTTPException(403, "班主任不能调整学生班级")

            updates.append("class_id = ?")
            params.append(update_data.class_id)
            updates.append("grade_id = ?")
            params.append(new_class['grade_id'])

        if not updates:
            return {"success": True, "message": "无需更新"}

        params.append(student_id)
        update_query = f"UPDATE student SET {', '.join(updates)} WHERE student_id = ?"
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
    user: User = Depends(require_configured_api_permission(API_STUDENT_UPDATE, allow_missing=False))
):
    """更新学生状态"""
    with get_moral_db() as db:
        status_scope = _student_manage_scope(db, user, API_STUDENT_UPDATE)
        if not status_scope.get("can_all"):
            raise HTTPException(403, "权限不足：需要学生管理权限")

        student = db.query_one(
            "SELECT * FROM student WHERE student_id = ?",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        db.execute(
            "UPDATE student SET status = ?, status_date = ? WHERE student_id = ?",
            (status, date.today(), student_id)
        )

        # 结束当前班级履历
        if status in ['转出', '毕业']:
            db.execute(
                """UPDATE student_class_history SET end_date = ?
                WHERE student_id = ? AND end_date IS NULL""",
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
    user: User = Depends(require_configured_api_permission(API_LOGS, allow_missing=False))
):
    """
    获取操作日志列表

    权限要求：admin/jiaowu/xuefa
    """
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if operator:
            conditions.append("operator LIKE ?")
            params.append(f"%{operator}%")

        if operation:
            conditions.append("operation = ?")
            params.append(operation)

        if table_name:
            conditions.append("table_name = ?")
            params.append(table_name)

        if start_date:
            conditions.append("DATE(created_at) >= ?")
            params.append(start_date)

        if end_date:
            conditions.append("DATE(created_at) <= ?")
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
            LIMIT ? OFFSET ?
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
    user: User = Depends(require_configured_api_permission(API_CONFIG, allow_missing=False))
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
    filegather_upload_dir: Optional[str] = Field(None, description="文件上传保存目录")
    filegather_done_dir: Optional[str] = Field(None, description="已完成文件归档目录")


@router.put("/config", summary="更新系统配置")
async def update_system_config(
    config: ConfigUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_CONFIG, allow_missing=False))
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
                    "SELECT config_id FROM moral_config WHERE config_key = ?",
                    (key,)
                )

                if existing:
                    db.execute(
                        "UPDATE moral_config SET config_value = ?, updated_at = datetime('now','localtime') WHERE config_key = ?",
                        (json_value, key)
                    )
                else:
                    db.execute(
                        "INSERT INTO moral_config (config_key, config_value) VALUES (?, ?)",
                        (key, json_value)
                    )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'moral_config', None,
            new_data=update_data,
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "配置更新成功"}
