# -*- coding: utf-8 -*-
"""
系统管理 API

提供级号、学年、学期等系统配置的管理功能
"""

import json
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, ConfigDict, field_validator

from .api_permission import require_configured_api_permission
from .base import (
    get_moral_db,
    require_permission,
    require_role_level,
    log_operation,
    check_moral_permission,
    check_class_access,
    get_teacher_class_id,
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
API_GRADE_PROMOTE_ROLLBACK = "/api/moral/admin/grades/promote/rollback"
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


def _visible_class_ids_for_lookup(db, user: User, *, include_teaching: bool = True) -> Optional[List[int]]:
    """返回基础选择器可见班级；None 表示全校可见。"""
    scope = get_record_data_scope(
        db,
        user,
        API_CLASSES,
        all_permissions=['class_manage', 'report_view_all'],
        own_class_permissions=[],
        own_permissions=[],
    )
    if scope.get("can_all"):
        return None

    class_ids = set()
    class_ids.update(scope.get("my_class_ids") or [])
    class_ids.update(scope.get("my_grade_class_ids") or [])
    if include_teaching:
        class_ids.update(scope.get("teaching_class_ids") or [])
    return sorted(class_ids)


def _append_visible_class_condition(
    conditions: List[str],
    params: List,
    class_ids: Optional[List[int]],
    *,
    field: str,
) -> bool:
    """把可见班级范围追加到查询条件；返回 False 表示无可见数据。"""
    if class_ids is None:
        return True
    if not class_ids:
        return False
    placeholders = ", ".join(["?"] * len(class_ids))
    conditions.append(f"{field} IN ({placeholders})")
    params.extend(class_ids)
    return True


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
    roomid: Optional[str] = Field(None, description="宿舍号")
    rpid: Optional[str] = Field(None, description="床位号")


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
        visible_class_ids = _visible_class_ids_for_lookup(db, user, include_teaching=True)
        if visible_class_ids is None:
            grades = db.query_all(
                "SELECT g.*, "
                "(SELECT COUNT(*) FROM class WHERE grade_id = g.grade_id) as class_count, "
                "(SELECT COUNT(*) FROM student WHERE grade_id = g.grade_id AND status = '在校') as student_count "
                "FROM grade g ORDER BY g.enrollment_year DESC"
            )
        elif not visible_class_ids:
            grades = []
        else:
            placeholders = ", ".join(["?"] * len(visible_class_ids))
            grades = db.query_all(
                f"""SELECT g.*,
                    COUNT(DISTINCT c.class_id) as class_count,
                    COUNT(DISTINCT CASE WHEN s.status = '在校' THEN s.student_id END) as student_count
                   FROM grade g
                   JOIN class c ON c.grade_id = g.grade_id
                   LEFT JOIN student s ON s.class_id = c.class_id
                   WHERE c.class_id IN ({placeholders})
                   GROUP BY g.grade_id
                   ORDER BY g.enrollment_year DESC""",
                tuple(visible_class_ids),
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

def _get_promotion_base_year(db) -> int:
    """
    升年级判断的基准年：取当前学年的起始年（start_date 的年份），而非自然年。

    例：当前学年 2025-2026（start_date=2025-xx-xx）时基准年为 2025，
    enrollment_year 距基准年满 2 年（高三）的年级毕业。
    自然年在 8 月已翻年但学年未切换，直接用 datetime.now().year 会把
    高二（如 2024 级）误判为毕业。
    """
    from datetime import date

    start_date = db.query_value(
        "SELECT start_date FROM school_year WHERE is_current = 1"
    )
    if start_date:
        return int(str(start_date)[:4])
    # 无当前学年配置时按学年惯例推算：9 月及以后视为新学年
    today = date.today()
    return today.year if today.month >= 9 else today.year - 1


def _get_level_mapping(db) -> Dict[int, str]:
    """读取 grade_level_config，返回 {years_after_enrollment: level_name}。"""
    rows = db.query_all(
        "SELECT years_after_enrollment, level_name FROM grade_level_config"
    )
    return {r['years_after_enrollment']: r['level_name'] for r in rows} if rows else {}


def _compute_class_rename(
    old_name: str,
    current_level: str,
    next_level: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    仅当 old_name 以 current_level 开头时，才替换为 next_level。
    返回 (new_name, skip_reason)。
    """
    if not old_name:
        return None, "班级名称为空"
    if old_name.startswith(current_level):
        new_name = next_level + old_name[len(current_level):]
        return new_name, None
    return None, f"名称不以'{current_level}'开头"


def _build_class_rename_plan(
    db,
    promoting_grades: List[Dict[str, Any]],
    graduating_grades: Optional[List[Dict[str, Any]]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    根据需升级和毕业的年级列表，计算班级名称变更计划。
    - 升级年级：current_level -> next_level
    - 毕业年级：current_level -> {enrollment_year}级
    返回 (class_renames, skipped_renames)。
    """
    class_renames: List[Dict[str, Any]] = []
    skipped_renames: List[Dict[str, Any]] = []

    grade_targets: Dict[int, Dict[str, Any]] = {}

    for g in promoting_grades or []:
        grade_targets[g['grade_id']] = {
            'current_level': g['current_level'],
            'target_level': g['next_level'],
            'grade_name': g['grade_name']
        }

    for g in graduating_grades or []:
        grade_targets[g['grade_id']] = {
            'current_level': g['current_level'],
            'target_level': f"{g['enrollment_year']}级",
            'grade_name': g['grade_name']
        }

    if not grade_targets:
        return class_renames, skipped_renames

    grade_ids = list(grade_targets.keys())
    placeholders = ','.join('?' * len(grade_ids))
    classes = db.query_all(
        f"""SELECT c.class_id, c.class_name, c.grade_id, g.grade_name
            FROM class c
            JOIN grade g ON c.grade_id = g.grade_id
            WHERE c.grade_id IN ({placeholders})
            ORDER BY g.enrollment_year DESC, c.class_number""",
        tuple(grade_ids)
    )

    for cls in classes:
        target = grade_targets.get(cls['grade_id'])
        if not target:
            continue
        new_name, reason = _compute_class_rename(
            cls['class_name'], target['current_level'], target['target_level']
        )
        if new_name is not None:
            class_renames.append({
                'class_id': cls['class_id'],
                'grade_id': cls['grade_id'],
                'grade_name': cls['grade_name'],
                'old_name': cls['class_name'],
                'new_name': new_name
            })
        else:
            skipped_renames.append({
                'class_id': cls['class_id'],
                'grade_id': cls['grade_id'],
                'grade_name': cls['grade_name'],
                'old_name': cls['class_name'],
                'reason': reason
            })

    return class_renames, skipped_renames


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
        # 基准年取当前学年起始年，而非自然年（8 月学年未切换时自然年已翻年）
        current_year = _get_promotion_base_year(db)

        # 获取配置的年级层级映射（如果有）
        # grade_level_config 按 years_after_enrollment（0=高一，1=高二，2=高三）映射层级名称
        level_config = db.query_all(
            "SELECT years_after_enrollment, level_name FROM grade_level_config"
        )
        level_map = {c['years_after_enrollment']: c['level_name'] for c in level_config} if level_config else {}

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
            grade['current_level'] = level_map.get(years_after, f"{years_after+1}年级")

            if years_after >= 2:
                # 高三，即将毕业
                graduating_grades.append(grade)
            else:
                # 高一/高二，即将升年级
                grade['next_level'] = level_map.get(years_after + 1, f"{years_after+2}年级")
                promoting_grades.append(grade)

        # 计算班级名称升级计划
        class_renames, skipped_renames = _build_class_rename_plan(db, promoting_grades, graduating_grades)

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
                "class_renames": class_renames,
                "skipped_renames": skipped_renames,
                "rename_count": len(class_renames),
                "skip_count": len(skipped_renames),
                "has_next_year": next_school_year is not None
            }
        }


class PromoteExecuteRequest(BaseModel):
    """执行升年级请求"""
    next_year_id: Optional[int] = Field(None, description="下一学年ID（可选，用于结转）")


def _build_promotion_snapshot(
    db,
    graduating_grade_ids: List[int],
    class_renames: List[Dict[str, Any]],
    next_year_id: Optional[int]
) -> Dict[str, Any]:
    """
    在执行升年级前生成旧状态快照，用于后续回滚。

    快照包含：
    - 被归档的年级旧状态
    - 被毕业的学生旧状态
    - 被结束的班级履历
    - 切换学年前的当前学年
    - 任务结转前的 student_task_finish 记录
    """
    snapshot: Dict[str, Any] = {
        'graduating_grade_ids': graduating_grade_ids,
        'archived_grades': [],
        'graduated_students': [],
        'class_histories': [],
        'school_year_before': None,
        'school_year_after': next_year_id,
        'task_snapshot': [],
        'class_name_changes': class_renames or [],
    }

    if not graduating_grade_ids:
        return snapshot

    placeholders = ','.join('?' * len(graduating_grade_ids))

    # 1. 年级归档前的状态（含年级主任，用于回滚时恢复）
    snapshot['archived_grades'] = db.query_all(
        f"""SELECT grade_id, is_archived, archived_at, leader_ids, leader_names
            FROM grade WHERE grade_id IN ({placeholders})""",
        tuple(graduating_grade_ids)
    )

    # 2. 学生毕业前的状态（仅在校）
    snapshot['graduated_students'] = db.query_all(
        f"""SELECT student_id, status, status_date
            FROM student
            WHERE grade_id IN ({placeholders}) AND status = '在校'""",
        tuple(graduating_grade_ids)
    )

    # 3. 班级履历（未结束）
    snapshot['class_histories'] = db.query_all(
        f"""SELECT id, student_id, grade_id, end_date
            FROM student_class_history
            WHERE grade_id IN ({placeholders}) AND end_date IS NULL""",
        tuple(graduating_grade_ids)
    )

    # 4. 切换学年前的当前学年
    if next_year_id:
        snapshot['school_year_before'] = db.query_one(
            "SELECT year_id, year_name FROM school_year WHERE is_current = 1"
        )

        # 5. 可能被结转的任务快照
        from_year = snapshot['school_year_before']
        if from_year:
            snapshot['task_snapshot'] = db.query_all(
                """SELECT stf.id, stf.student_id, stf.task_id, stf.year_id,
                          stf.is_carried_over, stf.carryover_count, stf.current_score,
                          stf.status, stf.original_task_id, stf.original_year_id
                   FROM student_task_finish stf
                   JOIN grade_moral_task t ON stf.task_id = t.task_id
                   JOIN student s ON stf.student_id = s.student_id
                   WHERE stf.year_id = ?
                     AND stf.status = 0
                     AND t.can_carryover = 1
                     AND t.is_active = 1
                     AND s.status = '在校'""",
                (from_year['year_id'],)
            )

    return snapshot


def _restore_promotion_snapshot(db, snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    根据快照回滚最近一次升年级操作。

    回滚内容：
    - 恢复学生状态为在校
    - 恢复班级履历 end_date 为 NULL
    - 恢复年级 is_archived=0
    - 恢复学年 is_current 标记
    - 恢复被结转的任务状态（year_id、score、carryover_count 等）
    """
    result = {
        'restored_students': 0,
        'restored_histories': 0,
        'restored_grades': 0,
        'restored_school_year': False,
        'restored_tasks': 0,
        'restored_class_names': 0,
        'errors': []
    }

    # 1. 恢复学生状态
    students = snapshot.get('graduated_students') or []
    if students:
        rows = [
            (s.get('status', '在校'), s.get('status_date'), s['student_id'])
            for s in students
        ]
        db.executemany(
            "UPDATE student SET status = ?, status_date = ? WHERE student_id = ?",
            rows
        )
        result['restored_students'] = len(students)

    # 2. 恢复班级履历
    histories = snapshot.get('class_histories') or []
    if histories:
        rows = [(h['end_date'], h['id']) for h in histories]
        db.executemany(
            "UPDATE student_class_history SET end_date = ? WHERE id = ?",
            rows
        )
        result['restored_histories'] = len(histories)

    # 3. 恢复年级归档状态
    grades = snapshot.get('archived_grades') or []
    if grades:
        rows = [
            (
                g.get('is_archived', 0),
                g.get('archived_at'),
                g.get('leader_ids', ''),
                g.get('leader_names', ''),
                g['grade_id']
            )
            for g in grades
        ]
        db.executemany(
            "UPDATE grade SET is_archived = ?, archived_at = ?, leader_ids = ?, leader_names = ? WHERE grade_id = ?",
            rows
        )
        result['restored_grades'] = len(grades)

    # 4. 恢复学年 current 标记
    school_year_before = snapshot.get('school_year_before')
    school_year_after = snapshot.get('school_year_after')
    if school_year_before and school_year_after:
        db.execute("UPDATE school_year SET is_current = 0")
        db.execute(
            "UPDATE school_year SET is_current = 1 WHERE year_id = ?",
            (school_year_before['year_id'],)
        )
        result['restored_school_year'] = True

    # 5. 恢复任务结转
    task_snapshot = snapshot.get('task_snapshot') or []
    if task_snapshot:
        rows = [
            (
                t['year_id'],
                t.get('is_carried_over', 0),
                t.get('carryover_count', 0),
                t.get('current_score'),
                t.get('status', 0),
                t['id']
            )
            for t in task_snapshot
        ]
        db.executemany(
            """UPDATE student_task_finish
               SET year_id = ?, is_carried_over = ?, carryover_count = ?,
                   current_score = ?, status = ?
               WHERE id = ?""",
            rows
        )
        result['restored_tasks'] = len(task_snapshot)

        # 删除由本次结转产生的结转日志
        if school_year_before and school_year_after:
            db.execute(
                """DELETE FROM task_carryover_log
                   WHERE from_year_id = ? AND to_year_id = ?""",
                (school_year_before['year_id'], school_year_after)
            )

    # 6. 恢复班级名称
    class_name_changes = snapshot.get('class_name_changes') or []
    if class_name_changes:
        rows = [(c['old_name'], c['class_id']) for c in class_name_changes]
        db.executemany(
            "UPDATE class SET class_name = ? WHERE class_id = ?",
            rows
        )
        result['restored_class_names'] = len(class_name_changes)

    return result



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
    4. 记录完整快照，用于回滚

    注意：grade_id 不变，年级层级由 enrollment_year 动态计算
    """
    with get_moral_db() as db:
        # 基准年取当前学年起始年，避免 8 月学年未切换时误把高二判为毕业
        current_year = _get_promotion_base_year(db)
        today = date.today()
        archive_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        result = {
            'graduated_students': 0,
            'archived_grades': 0,
            'renamed_classes': 0,
            'errors': []
        }

        # 查询所有未归档的年级，并确定即将毕业和升级的年级
        grades = db.query_all(
            """SELECT g.grade_id, g.grade_name, g.enrollment_year
               FROM grade g
               WHERE g.is_archived = 0
               ORDER BY g.enrollment_year"""
        )

        level_map = _get_level_mapping(db)
        graduating_grade_ids = []
        graduating_grades = []
        promoting_grades = []
        for grade in grades:
            years_after = current_year - grade['enrollment_year']
            grade['years_after_enrollment'] = years_after
            grade['current_level'] = level_map.get(years_after, f"{years_after+1}年级")
            if years_after >= 2:
                graduating_grade_ids.append(grade['grade_id'])
                graduating_grades.append(grade)
            else:
                grade['next_level'] = level_map.get(years_after + 1, f"{years_after+2}年级")
                promoting_grades.append(grade)

        # 计算班级名称升级计划（在修改前）
        class_renames, skipped_renames = _build_class_rename_plan(db, promoting_grades, graduating_grades)

        # 生成旧状态快照（在修改前）
        snapshot = _build_promotion_snapshot(
            db, graduating_grade_ids, class_renames, request_data.next_year_id
        )

        # 执行毕业和归档
        for grade_id in graduating_grade_ids:
            grade = next((g for g in grades if g['grade_id'] == grade_id), None)
            if not grade:
                continue

            try:
                graduated_count = db.query_value(
                    """SELECT COUNT(*) FROM student
                       WHERE grade_id = ? AND status = '在校'""",
                    (grade_id,)
                )

                db.execute(
                    """UPDATE student SET status = '毕业', status_date = ?
                       WHERE grade_id = ? AND status = '在校'""",
                    (today, grade_id)
                )

                db.execute(
                    """UPDATE student_class_history SET end_date = ?
                       WHERE grade_id = ? AND end_date IS NULL""",
                    (today, grade_id)
                )

                db.execute(
                    """UPDATE grade SET is_archived = 1, archived_at = ?,
                       leader_ids = '', leader_names = ''
                       WHERE grade_id = ?""",
                    (archive_time, grade_id)
                )

                result['graduated_students'] += graduated_count
                result['archived_grades'] += 1

                logger.info(
                    f"年级归档：{grade['grade_name']}，毕业学生 {graduated_count} 人"
                )

            except Exception as e:
                result['errors'].append(f"{grade['grade_name']}: {str(e)}")
                logger.error(f"年级归档失败：{grade['grade_name']} - {e}")

        # 升级班级名称
        for rename in class_renames:
            try:
                db.execute(
                    "UPDATE class SET class_name = ? WHERE class_id = ?",
                    (rename['new_name'], rename['class_id'])
                )
                logger.info(f"班级名称升级：{rename['old_name']} -> {rename['new_name']}")
            except Exception as e:
                result['errors'].append(f"班级名称升级 {rename['old_name']}: {str(e)}")
                logger.error(f"班级名称升级失败：{rename['old_name']} - {e}")
        result['renamed_classes'] = len(class_renames)

        # 更新学年标记（如果提供了下一学年ID）
        if request_data.next_year_id:
            next_year = db.query_one(
                "SELECT * FROM school_year WHERE year_id = ?",
                (request_data.next_year_id,)
            )
            if next_year:
                db.execute("UPDATE school_year SET is_current = 0")
                db.execute(
                    "UPDATE school_year SET is_current = 1 WHERE year_id = ?",
                    (request_data.next_year_id,)
                )

                # 执行任务结转（旧学年取切换前的当前学年，见快照）
                old_year = snapshot.get('school_year_before')
                if old_year and old_year['year_id'] != request_data.next_year_id:
                    try:
                        from .carryover import execute_task_carryover
                        carryover_result = execute_task_carryover(
                            db, old_year['year_id'], request_data.next_year_id
                        )
                        result['carryover'] = carryover_result
                        logger.info(f"任务结转完成：{carryover_result}")
                    except Exception as e:
                        result['errors'].append(f"任务结转: {str(e)}")
                        logger.error(f"任务结转失败：{e}")

        # 记录操作日志，快照放入 old_data 供回滚使用
        log_operation(
            db, user.username, user.role, 'PROMOTE', 'grade', None,
            old_data=snapshot,
            new_data={
                'graduated_students': result['graduated_students'],
                'archived_grades': result['archived_grades'],
                'renamed_classes': result['renamed_classes'],
                'skipped_renames': skipped_renames,
                'next_year_id': request_data.next_year_id
            },
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "message": f"升年级完成：毕业 {result['graduated_students']} 名学生，归档 {result['archived_grades']} 个年级，变更 {result['renamed_classes']} 个班级名称",
            "data": result
        }


@router.post("/grades/promote/rollback", summary="撤销最近一次升年级")
async def rollback_grade_promotion(
    request: Request,
    user: User = Depends(require_configured_api_permission(API_GRADE_PROMOTE_ROLLBACK, allow_missing=False))
):
    """
    撤销最近一次升年级操作

    权限要求：xuefa/admin

    回滚内容：
    - 恢复毕业学生为在校状态
    - 恢复班级履历 end_date
    - 恢复年级 is_archived=0
    - 恢复学年 is_current 标记
    - 恢复被结转的任务状态并删除结转日志

    注意：若升年级后已发生大量新数据变更，回滚可能覆盖这些变更，请谨慎使用。
    """
    with get_moral_db() as db:
        # 查找最近一次升年级操作日志
        log = db.query_one(
            """SELECT id, old_data, new_data, operator, operator_role
               FROM moral_operation_log
               WHERE operation = 'PROMOTE' AND table_name = 'grade'
               ORDER BY id DESC LIMIT 1"""
        )

        if not log:
            raise HTTPException(400, "未找到可回滚的升年级记录")

        old_data_raw = log.get('old_data')
        if not old_data_raw:
            raise HTTPException(400, "升年级记录缺少快照，无法回滚")

        try:
            snapshot = json.loads(old_data_raw)
        except Exception as e:
            logger.error(f"解析升年级快照失败：{e}")
            raise HTTPException(500, "升年级快照解析失败")

        if snapshot.get('rolled_back_at'):
            raise HTTPException(400, "最近一次升年级已被回滚，不能重复回滚")

        # 执行回滚
        rollback_result = _restore_promotion_snapshot(db, snapshot)

        # 标记原快照已回滚
        snapshot['rolled_back_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        snapshot['rolled_back_by'] = user.username
        db.execute(
            "UPDATE moral_operation_log SET old_data = ? WHERE id = ?",
            (json.dumps(snapshot, ensure_ascii=False), log['id'])
        )

        # 记录回滚操作日志
        log_operation(
            db, user.username, user.role, 'PROMOTE_ROLLBACK', 'grade', None,
            old_data={
                'promote_log_id': log['id'],
                'promote_operator': log.get('operator'),
                'promote_new_data': log.get('new_data')
            },
            new_data=rollback_result,
            ip_address=request.client.host if request.client else None
        )

        return {
            "success": True,
            "message": (
                f"升年级已撤销：恢复 {rollback_result['restored_students']} 名学生、"
                f"{rollback_result['restored_grades']} 个年级、"
                f"{rollback_result['restored_class_names']} 个班级名称、"
                f"{rollback_result['restored_tasks']} 条任务结转"
            ),
            "data": rollback_result
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
    with get_moral_db() as db:
        conditions = ["c.is_active = 1"]
        params = []

        visible_class_ids = _visible_class_ids_for_lookup(
            db,
            user,
            include_teaching=(for_evaluation != 1),
        )
        if not _append_visible_class_condition(conditions, params, visible_class_ids, field="c.class_id"):
            return {"success": True, "data": []}

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

        has_read_scope = any([
            manage_scope.get("can_all"),
            manage_scope.get("can_own_class"),
            manage_scope.get("can_own_grade"),
            manage_scope.get("can_teaching_classes"),
            manage_scope.get("can_own"),
        ])
        if not has_read_scope:
            raise HTTPException(403, "权限不足：需要学生查看权限")

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

        # 德育录入场景：强制只显示在校学生（排除转出/休学/毕业）
        if is_record_input_lookup:
            conditions.append("s.status = '在校'")
        elif status:
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
                        name = ?, gender = ?, class_id = ?, grade_id = ?, birthday = ?, roomid = ?, rpid = ?
                        WHERE student_id = ?""",
                        (item.name, item.gender, class_id, grade_id, birthday, item.roomid, item.rpid, item.student_id)
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
                        (student_id, name, gender, class_id, grade_id, original_grade_id, birthday, enrollment_date, roomid, rpid, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '在校')""",
                        (item.student_id, item.name, item.gender, class_id, grade_id, grade_id, birthday, enrollment_date, item.roomid, item.rpid)
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
    user: User = Depends(require_configured_api_permission(API_LOGS, "*", allow_missing=False))
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
    "semester_start_month": 9
    # punishment_types 已废弃，统一使用 punishment_period_config
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

            # punishment_types 从 punishment_period_config 动态读取
            result["punishment_types"] = db.query_all(
                """SELECT punishment_type as name, period_days, period_description,
                          allow_revoke_apply, min_good_records
                   FROM punishment_period_config
                   WHERE is_active = 1
                   ORDER BY period_days ASC"""
            ) or []

            return {"success": True, "data": result}
        else:
            # DEFAULT_CONFIG 无 punishment_types，动态补充
            result = dict(DEFAULT_CONFIG)
            result["punishment_types"] = db.query_all(
                """SELECT punishment_type as name, period_days, period_description,
                          allow_revoke_apply, min_good_records
                   FROM punishment_period_config
                   WHERE is_active = 1
                   ORDER BY period_days ASC"""
            ) or []
            return {"success": True, "data": result}


class ConfigUpdate(BaseModel):
    """更新系统配置"""
    model_config = ConfigDict(extra='allow')

    evaluation_base_score: Optional[int] = Field(None, description="评价基础分", ge=0, le=200)
    evaluation_excellent_line: Optional[int] = Field(None, description="优秀分数线", ge=0, le=100)
    evaluation_good_line: Optional[int] = Field(None, description="良好分数线", ge=0, le=100)
    evaluation_pass_line: Optional[int] = Field(None, description="及格分数线", ge=0, le=100)
    evaluation_weights: Optional[dict] = Field(None, description="评价权重配置")
    birthday_reminder_days: Optional[int] = Field(None, description="生日提前提醒天数", ge=1, le=30)
    semester_start_month: Optional[int] = Field(None, description="学期开始月份", ge=1, le=12)
    # punishment_types 已废弃，请使用 /punishment-periods API 管理
    daily_record_roles: Optional[str] = Field(None, description="日常记录角色（逗号分隔）")
    student_profile_roles: Optional[str] = Field(None, description="学生画像角色（逗号分隔）")
    ai_consultation_roles: Optional[str] = Field(None, description="AI诊疗角色（逗号分隔）")
    filegather_storage_dir: Optional[str] = Field(None, description="文件收集系统存储根目录（自动创建 uploads 和 done 子目录）")


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
