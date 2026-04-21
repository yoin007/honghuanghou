# -*- coding: utf-8 -*-
"""
评价查询 API

提供德育评价的查询和计算功能
"""

import logging
from datetime import date
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    check_class_access,
    get_current_semester,
    calculate_moral_level,
    get_current_user,
    get_teacher_class_id,
)
from models.datas_api.auth import User, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations", tags=["评价查询"])


# =============================================================================
# API 路由
# =============================================================================

@router.get("/student/{student_id}", summary="获取学生德育评价")
async def get_student_evaluation(
    student_id: str,
    semester_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    """
    获取学生德育评价

    权限说明：
    - 学生只能查看自己的评价
    - 家长只能查看子女的评价
    - 班主任可查看本班学生
    - xuefa/jiaowu/admin 可查看所有
    """
    with get_moral_db() as db:
        # 权限检查
        if user.role == 'student' and user.username != student_id:
            raise HTTPException(403, "只能查看自己的评价")

        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        # 获取学生信息
        student = db.query_one(
            """SELECT s.*, c.class_name, g.grade_name, c.leader_name
            FROM student s
            JOIN class c ON s.class_id = c.class_id
            JOIN grade g ON s.grade_id = g.grade_id
            WHERE s.student_id = %s""",
            (student_id,)
        )
        if not student:
            raise HTTPException(404, "学生不存在")

        # 班主任权限检查
        if user.role == 'cleader':
            my_class_id = get_teacher_class_id(user, db)
            if my_class_id is None or my_class_id != student['class_id']:
                if not check_moral_permission(user, 'report_view_all'):
                    raise HTTPException(403, "只能查看本班学生")

        # 获取或计算评价
        evaluation = db.query_one(
            """SELECT * FROM moral_evaluation
            WHERE student_id = %s AND semester_id = %s""",
            (student_id, semester_id)
        )

        # 获取基础分配置
        base_score_config = db.query_value(
            "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
        )
        base_score = float(base_score_config or 80)

        if not evaluation:
            # 计算评价
            evaluation = calculate_evaluation(db, student_id, semester_id)
        else:
            # 补充 base_score 和各分项（数据库未存储）
            # 计算各分项得分
            daily_score = db.query_value(
                """SELECT COALESCE(SUM(score), 0)
                FROM student_daily_record
                WHERE student_id = %s AND semester_id = %s AND is_deleted = 0""",
                (student_id, semester_id)
            ) or 0

            school_score = db.query_value(
                """SELECT COALESCE(SUM(score), 0)
                FROM student_school_record
                WHERE student_id = %s AND semester_id = %s AND is_deleted = 0""",
                (student_id, semester_id)
            ) or 0

            task_score = db.query_value(
                """SELECT COALESCE(SUM(current_score), 0)
                FROM student_task_finish stf
                JOIN grade_moral_task gmt ON stf.task_id = gmt.task_id
                JOIN school_year sy ON stf.year_id = sy.year_id
                JOIN semester sem ON sem.year_id = sy.year_id
                WHERE stf.student_id = %s AND sem.semester_id = %s AND stf.status = 1""",
                (student_id, semester_id)
            ) or 0

            evaluation = {
                'total_score': evaluation['total_score'],
                'level': evaluation['level'],
                'base_score': base_score,
                'daily_score': float(daily_score),
                'school_score': float(school_score),
                'task_score': float(task_score)
            }

        # 获取详细统计
        daily_stats = get_daily_statistics(db, student_id, semester_id)
        school_stats = get_school_statistics(db, student_id, semester_id)
        task_stats = get_task_statistics(db, student_id, semester_id)

        return {
            "success": True,
            "data": {
                "student": student,
                "evaluation": evaluation,
                "daily_stats": daily_stats,
                "school_stats": school_stats,
                "task_stats": task_stats
            }
        }


@router.get("/class/{class_id}", summary="获取班级德育评价汇总")
async def get_class_evaluation(
    class_id: int,
    semester_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    """
    获取班级德育评价汇总

    权限要求：
    - cleader 可查看本班
    - xuefa/jiaowu/admin 可查看所有
    """
    with get_moral_db() as db:
        # 权限检查
        if not check_class_access(user, class_id, db):
            raise HTTPException(403, "权限不足")

        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        # 获取班级学生评价列表
        evaluations = db.query_all(
            """SELECT me.*, s.name as student_name, s.student_id
            FROM moral_evaluation me
            JOIN student s ON me.student_id = s.student_id
            WHERE me.class_id = %s AND me.semester_id = %s
            ORDER BY me.total_score DESC""",
            (class_id, semester_id)
        )

        # 统计信息
        stats = db.query_one(
            """SELECT
            COUNT(*) as total_count,
            AVG(total_score) as avg_score,
            SUM(CASE WHEN level = '优秀' THEN 1 ELSE 0 END) as excellent_count,
            SUM(CASE WHEN level = '良好' THEN 1 ELSE 0 END) as good_count,
            SUM(CASE WHEN level = '合格' THEN 1 ELSE 0 END) as pass_count,
            SUM(CASE WHEN level = '不合格' THEN 1 ELSE 0 END) as fail_count
            FROM moral_evaluation
            WHERE class_id = %s AND semester_id = %s""",
            (class_id, semester_id)
        )

        return {
            "success": True,
            "data": {
                "evaluations": evaluations,
                "stats": stats
            }
        }


@router.get("/grade/{grade_id}", summary="获取年级德育评价汇总")
async def get_grade_evaluation(
    grade_id: int,
    semester_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    """
    获取年级德育评价汇总

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        if not check_moral_permission(user, 'report_view_all'):
            raise HTTPException(403, "权限不足")

        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        # 获取各班统计
        class_stats = db.query_all(
            """SELECT
            c.class_id, c.class_name,
            COUNT(me.eval_id) as student_count,
            AVG(me.total_score) as avg_score,
            MAX(me.total_score) as max_score,
            MIN(me.total_score) as min_score,
            SUM(CASE WHEN me.level = '优秀' THEN 1 ELSE 0 END) as excellent_count
            FROM class c
            LEFT JOIN moral_evaluation me ON c.class_id = me.class_id AND me.semester_id = %s
            WHERE c.grade_id = %s AND c.is_active = 1
            GROUP BY c.class_id
            ORDER BY avg_score DESC""",
            (semester_id, grade_id)
        )

        # 年级整体统计
        grade_stats = db.query_one(
            """SELECT
            COUNT(*) as total_count,
            AVG(total_score) as avg_score,
            SUM(CASE WHEN level = '优秀' THEN 1 ELSE 0 END) as excellent_count,
            SUM(CASE WHEN level = '良好' THEN 1 ELSE 0 END) as good_count,
            SUM(CASE WHEN level = '合格' THEN 1 ELSE 0 END) as pass_count,
            SUM(CASE WHEN level = '不合格' THEN 1 ELSE 0 END) as fail_count
            FROM moral_evaluation
            WHERE grade_id = %s AND semester_id = %s""",
            (grade_id, semester_id)
        )

        return {
            "success": True,
            "data": {
                "class_stats": class_stats,
                "grade_stats": grade_stats
            }
        }


@router.post("/calculate", summary="计算德育评价")
async def calculate_evaluation_api(
    student_id: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    semester_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user)
):
    """
    计算德育评价

    权限要求：xuefa/jiaowu/admin
    """
    with get_moral_db() as db:
        if not check_moral_permission(user, 'moral_record_manage'):
            raise HTTPException(403, "权限不足")

        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        # 获取要计算的学生列表
        conditions = ["s.status = '在校'"]
        params = []

        if student_id:
            conditions.append("s.student_id = %s")
            params.append(student_id)

        if class_id:
            conditions.append("s.class_id = %s")
            params.append(class_id)

        if grade_id:
            conditions.append("s.grade_id = %s")
            params.append(grade_id)

        where_clause = " AND ".join(conditions)

        students = db.query_all(
            f"SELECT student_id, class_id, grade_id FROM student s WHERE {where_clause}",
            tuple(params) if params else None
        )

        count = 0
        for student in students:
            evaluation = calculate_evaluation(db, student['student_id'], semester_id, student['class_id'], student['grade_id'])
            if evaluation:
                count += 1

        return {"success": True, "message": f"成功计算 {count} 名学生的德育评价"}


# =============================================================================
# 辅助函数
# =============================================================================

def calculate_evaluation(db, student_id: str, semester_id: int, class_id: int = None, grade_id: int = None) -> dict:
    """
    计算学生德育评价

    Args:
        db: 数据库连接
        student_id: 学号
        semester_id: 学期ID
        class_id: 班级ID（可选）
        grade_id: 级号ID（可选）

    Returns:
        评价结果字典
    """
    # 获取学生班级信息
    if not class_id or not grade_id:
        student = db.query_one(
            "SELECT class_id, grade_id FROM student WHERE student_id = %s",
            (student_id,)
        )
        if student:
            class_id = student['class_id']
            grade_id = student['grade_id']

    # 基础分（从配置读取）
    base_score_config = db.query_value(
        "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
    )
    base_score = Decimal(str(base_score_config or 60))

    # 日常表现分
    daily_score = db.query_value(
        """SELECT COALESCE(SUM(score), 0)
        FROM student_daily_record
        WHERE student_id = %s AND semester_id = %s AND is_deleted = 0""",
        (student_id, semester_id)
    ) or 0

    # 校级事件分
    school_score = db.query_value(
        """SELECT COALESCE(SUM(score), 0)
        FROM student_school_record
        WHERE student_id = %s AND semester_id = %s AND is_deleted = 0""",
        (student_id, semester_id)
    ) or 0

    # 任务完成分
    task_score = db.query_value(
        """SELECT COALESCE(SUM(current_score), 0)
        FROM student_task_finish stf
        JOIN grade_moral_task gmt ON stf.task_id = gmt.task_id
        JOIN school_year sy ON stf.year_id = sy.year_id
        JOIN semester sem ON sem.year_id = sy.year_id
        WHERE stf.student_id = %s AND sem.semester_id = %s AND stf.status = 1""",
        (student_id, semester_id)
    ) or 0

    # 总分
    total_score = Decimal(str(base_score)) + Decimal(str(daily_score)) + Decimal(str(school_score)) + Decimal(str(task_score))

    # 等级
    level = calculate_moral_level(float(total_score))

    # 保存或更新评价
    existing = db.query_one(
        "SELECT eval_id FROM moral_evaluation WHERE student_id = %s AND semester_id = %s",
        (student_id, semester_id)
    )

    if existing:
        db.execute(
            """UPDATE moral_evaluation SET
            total_score = %s, level = %s, class_id = %s, grade_id = %s, update_time = datetime('now','localtime')
            WHERE eval_id = %s""",
            (total_score, level, class_id, grade_id, existing['eval_id'])
        )
    else:
        db.execute(
            """INSERT INTO moral_evaluation
            (student_id, semester_id, class_id, grade_id, total_score, level)
            VALUES (%s, %s, %s, %s, %s, %s)""",
            (student_id, semester_id, class_id, grade_id, total_score, level)
        )

    return {
        'student_id': student_id,
        'semester_id': semester_id,
        'total_score': float(total_score),
        'level': level,
        'base_score': float(base_score),
        'daily_score': float(daily_score),
        'school_score': float(school_score),
        'task_score': float(task_score)
    }


def get_daily_statistics(db, student_id: str, semester_id: int) -> dict:
    """获取日常表现统计"""
    positive = db.query_one(
        """SELECT COUNT(*) as count, SUM(dr.score) as total
        FROM student_daily_record dr
        JOIN daily_event_type de ON dr.event_id = de.event_id
        WHERE dr.student_id = %s AND dr.semester_id = %s AND dr.is_deleted = 0
        AND de.event_type = 1""",
        (student_id, semester_id)
    )

    negative = db.query_one(
        """SELECT COUNT(*) as count, SUM(ABS(dr.score)) as total
        FROM student_daily_record dr
        JOIN daily_event_type de ON dr.event_id = de.event_id
        WHERE dr.student_id = %s AND dr.semester_id = %s AND dr.is_deleted = 0
        AND de.event_type = 2""",
        (student_id, semester_id)
    )

    return {
        'positive': positive or {'count': 0, 'total': 0},
        'negative': negative or {'count': 0, 'total': 0}
    }


def get_school_statistics(db, student_id: str, semester_id: int) -> dict:
    """获取校级事件统计"""
    honors = db.query_one(
        """SELECT COUNT(*) as count, SUM(score) as total
        FROM student_school_record
        WHERE student_id = %s AND semester_id = %s AND is_deleted = 0
        AND score > 0""",
        (student_id, semester_id)
    )

    punishments = db.query_one(
        """SELECT COUNT(*) as count, SUM(ABS(score)) as total
        FROM student_school_record
        WHERE student_id = %s AND semester_id = %s AND is_deleted = 0
        AND score < 0""",
        (student_id, semester_id)
    )

    return {
        'honors': honors or {'count': 0, 'total': 0},
        'punishments': punishments or {'count': 0, 'total': 0}
    }


def get_task_statistics(db, student_id: str, semester_id: int) -> dict:
    """获取任务完成统计"""
    stats = db.query_one(
        """SELECT
        COUNT(*) as total_tasks,
        SUM(CASE WHEN stf.status = 1 THEN 1 ELSE 0 END) as finished_tasks,
        SUM(CASE WHEN stf.status = 1 THEN stf.current_score ELSE 0 END) as total_score
        FROM student_task_finish stf
        JOIN semester sem ON sem.semester_id = %s
        JOIN school_year sy ON sem.year_id = sy.year_id
        WHERE stf.student_id = %s AND stf.year_id = sy.year_id""",
        (semester_id, student_id)
    )

    return stats or {'total_tasks': 0, 'finished_tasks': 0, 'total_score': 0}