# -*- coding: utf-8 -*-
"""Dashboard 趋势图 API。

提供学生得分趋势、班级/年级平均趋势、教师德育记录趋势等 API。
"""

from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models.datas_api.auth import User, get_current_user
from models.datas_api.moral.base import (
    get_moral_db,
    get_teacher_class_id,
    has_user_role,
)
from models.datas_api.dashboard_common import (
    is_moral_manager as _is_moral_manager,
    is_jiaowu as _is_jiaowu,
    now_text as _now_text,
)

router = APIRouter(prefix="/dashboard", tags=["数据驾驶舱趋势图"])


def _get_period_format(unit: str) -> str:
    """获取时间聚合格式。

    Args:
        unit: 'week' 或 'month'

    Returns:
        SQLite strftime 格式字符串
    """
    if unit == 'month':
        return '%Y-%m'
    return '%Y-W%W'


def _format_period_label(period: str, unit: str) -> str:
    """格式化周期显示标签。

    Args:
        period: strftime 返回的周期字符串
        unit: 'week' 或 'month'

    Returns:
        可读的周期标签，如 '第1周' 或 '2026年1月'
    """
    if unit == 'month':
        year, month = period.split('-')
        return f'{year}年{int(month)}月'
    else:
        year, week = period.split('-W')
        return f'{year}年第{int(week)}周'


def _build_empty_trend_response(unit: str) -> Dict:
    """构建空趋势响应。

    Args:
        unit: 聚合单位

    Returns:
        空趋势数据结构
    """
    return {
        "periods": [],
        "labels": [],
        "task_scores": [],
        "record_scores": [],
        "total_scores": [],
    }


def _merge_trend_data(
    task_data: List[Dict],
    record_data: List[Dict],
    unit: str
) -> Dict:
    """合并任务得分和加减分记录趋势数据。

    Args:
        task_data: 任务得分趋势数据
        record_data: 加减分记录趋势数据
        unit: 聚合单位

    Returns:
        合并后的趋势数据
    """
    # 合并所有周期
    all_periods = set()
    task_map = {}
    record_map = {}

    for row in task_data:
        period = row.get('period', '')
        all_periods.add(period)
        task_map[period] = row.get('score', 0) or 0

    for row in record_data:
        period = row.get('period', '')
        all_periods.add(period)
        record_map[period] = row.get('score', 0) or 0

    # 按周期排序
    sorted_periods = sorted(all_periods)

    # 构建结果
    periods = []
    labels = []
    task_scores = []
    record_scores = []
    total_scores = []

    for period in sorted_periods:
        if period:
            periods.append(period)
            labels.append(_format_period_label(period, unit))
            ts = task_map.get(period, 0)
            rs = record_map.get(period, 0)
            task_scores.append(ts)
            record_scores.append(rs)
            total_scores.append(ts + rs)

    return {
        "periods": periods,
        "labels": labels,
        "task_scores": task_scores,
        "record_scores": record_scores,
        "total_scores": total_scores,
    }


@router.get("/score-trend/student/{student_id}", summary="学生个人得分趋势")
async def get_student_score_trend(
    student_id: str,
    unit: str = Query('week', description="聚合单位：week 或 month"),
    semester_id: Optional[int] = Query(None, description="学期ID，默认当前学期"),
    user: User = Depends(get_current_user),
):
    """学生个人得分趋势图数据。

    数据来源：
    - student_task_finish：任务得分
    - student_school_record：加减分记录

    Args:
        student_id: 学生学号
        unit: 聚合单位，'week' 或 'month'
        semester_id: 学期ID
        user: 当前用户

    Returns:
        趋势数据：周期标签、任务得分、加减分、总分
    """
    # 权限检查：班主任、年级主任、德育管理员
    with get_moral_db() as db:
        # 检查学生是否存在
        student = db.query_one(
            "SELECT student_id, name, class_id FROM student WHERE student_id = %s",
            (student_id,)
        )
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")

        class_id = student.get('class_id')

        # 权限判断
        if not _is_moral_manager(user):
            if has_user_role(user, 'cleader'):
                my_class_id = get_teacher_class_id(user, db)
                if my_class_id != class_id:
                    raise HTTPException(status_code=403, detail="只能查看本班学生")
            elif has_user_role(user, 'g_leader'):
                # 年级主任：检查学生是否在自己年级
                my_classes = db.query_all(
                    "SELECT class_id FROM class WHERE grade_id = (SELECT grade_id FROM class WHERE class_id = %s)",
                    (class_id,)
                )
                my_class_ids = [c['class_id'] for c in my_classes]
                if class_id not in my_class_ids:
                    raise HTTPException(status_code=403, detail="只能查看本年级学生")
            else:
                raise HTTPException(status_code=403, detail="无查看权限")

        # 获取学期信息
        if not semester_id:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE status = 1"
            )
        else:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = %s",
                (semester_id,)
            )

        if not semester:
            return {"success": True, "data": _build_empty_trend_response(unit)}

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        # 任务得分趋势
        task_data = db.query_all(
            f"""SELECT strftime('{period_format}', finish_date) as period, SUM(current_score) as score
                FROM student_task_finish
                WHERE student_id = %s AND status = 1
                AND finish_date >= %s AND finish_date <= %s
                GROUP BY period ORDER BY period""",
            (student_id, start_date, end_date)
        )

        # 加减分记录趋势
        record_data = db.query_all(
            f"""SELECT strftime('{period_format}', get_date) as period, SUM(score) as score
                FROM student_school_record
                WHERE student_id = %s AND is_deleted = 0
                AND get_date >= %s AND get_date <= %s
                GROUP BY period ORDER BY period""",
            (student_id, start_date, end_date)
        )

        # 合并数据
        trend_data = _merge_trend_data(task_data or [], record_data or [], unit)

    return {
        "success": True,
        "data": {
            "student_id": student_id,
            "student_name": student.get('name'),
            "unit": unit,
            "semester_id": semester.get('semester_id') if semester else None,
            "trend": trend_data,
            "updated_at": _now_text(),
        },
    }


@router.get("/score-trend/class/{class_id}", summary="班级平均得分趋势")
async def get_class_score_trend(
    class_id: int,
    unit: str = Query('week', description="聚合单位：week 或 month"),
    semester_id: Optional[int] = Query(None, description="学期ID，默认当前学期"),
    user: User = Depends(get_current_user),
):
    """班级平均得分趋势图数据。

    Args:
        class_id: 班级ID
        unit: 聚合单位
        semester_id: 学期ID
        user: 当前用户

    Returns:
        班级平均得分趋势数据
    """
    with get_moral_db() as db:
        # 检查班级是否存在
        class_info = db.query_one(
            "SELECT class_id, class_name FROM class WHERE class_id = %s AND is_active = 1",
            (class_id,)
        )
        if not class_info:
            raise HTTPException(status_code=404, detail="班级不存在")

        # 权限检查
        if not (_is_moral_manager(user) or _is_jiaowu(user)):
            if has_user_role(user, 'cleader'):
                my_class_id = get_teacher_class_id(user, db)
                if my_class_id != class_id:
                    raise HTTPException(status_code=403, detail="只能查看本班数据")
            else:
                raise HTTPException(status_code=403, detail="无查看权限")

        # 获取学期信息
        if not semester_id:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE status = 1"
            )
        else:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = %s",
                (semester_id,)
            )

        if not semester:
            return {"success": True, "data": _build_empty_trend_response(unit)}

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        # 班级任务得分平均趋势
        task_data = db.query_all(
            f"""SELECT strftime('{period_format}', stf.finish_date) as period,
                       AVG(stf.current_score) as avg_score
                FROM student_task_finish stf
                JOIN student s ON stf.student_id = s.student_id
                WHERE s.class_id = %s AND stf.status = 1
                AND stf.finish_date >= %s AND stf.finish_date <= %s
                GROUP BY period ORDER BY period""",
            (class_id, start_date, end_date)
        )

        # 班级加减分平均趋势
        record_data = db.query_all(
            f"""SELECT strftime('{period_format}', ssr.get_date) as period,
                       AVG(ssr.score) as avg_score
                FROM student_school_record ssr
                JOIN student s ON ssr.student_id = s.student_id
                WHERE s.class_id = %s AND ssr.is_deleted = 0
                AND ssr.get_date >= %s AND ssr.get_date <= %s
                GROUP BY period ORDER BY period""",
            (class_id, start_date, end_date)
        )

        # 合并数据（班级用平均值）
        trend_data = _merge_trend_data(task_data or [], record_data or [], unit)

    return {
        "success": True,
        "data": {
            "class_id": class_id,
            "class_name": class_info.get('class_name'),
            "unit": unit,
            "semester_id": semester.get('semester_id') if semester else None,
            "trend": trend_data,
            "updated_at": _now_text(),
        },
    }


@router.get("/score-trend/grade/{grade_id}", summary="年级平均得分趋势")
async def get_grade_score_trend(
    grade_id: str,
    unit: str = Query('week', description="聚合单位：week 或 month"),
    semester_id: Optional[int] = Query(None, description="学期ID，默认当前学期"),
    user: User = Depends(get_current_user),
):
    """年级平均得分趋势图数据。

    Args:
        grade_id: 年级ID（如高一、高二、高三）
        unit: 聚合单位
        semester_id: 学期ID
        user: 当前用户

    Returns:
        年级平均得分趋势数据
    """
    with get_moral_db() as db:
        # 权限检查：年级主任、教务、德育管理员
        if not (_is_moral_manager(user) or _is_jiaowu(user) or has_user_role(user, 'g_leader')):
            raise HTTPException(status_code=403, detail="无年级驾驶舱权限")

        # 年级名称映射
        grade_names = {"高一": "高一年级", "高二": "高二年级", "高三": "高三年级"}
        grade_name = grade_names.get(grade_id, grade_id)

        # 获取年级下所有班级
        grade_filter = f"%{grade_id}%"
        classes = db.query_all(
            "SELECT class_id, class_name FROM class WHERE is_active = 1 AND class_name LIKE %s",
            (grade_filter,)
        )
        class_ids = [c['class_id'] for c in classes]

        if not class_ids:
            raise HTTPException(status_code=404, detail="年级不存在或无班级")

        # 获取学期信息
        if not semester_id:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE status = 1"
            )
        else:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = %s",
                (semester_id,)
            )

        if not semester:
            return {"success": True, "data": _build_empty_trend_response(unit)}

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        class_ids_str = ','.join(map(str, class_ids))

        # 年级任务得分平均趋势
        task_data = db.query_all(
            f"""SELECT strftime('{period_format}', stf.finish_date) as period,
                       AVG(stf.current_score) as avg_score
                FROM student_task_finish stf
                JOIN student s ON stf.student_id = s.student_id
                WHERE s.class_id IN ({class_ids_str}) AND stf.status = 1
                AND stf.finish_date >= %s AND stf.finish_date <= %s
                GROUP BY period ORDER BY period""",
            (start_date, end_date)
        )

        # 年级加减分平均趋势
        record_data = db.query_all(
            f"""SELECT strftime('{period_format}', ssr.get_date) as period,
                       AVG(ssr.score) as avg_score
                FROM student_school_record ssr
                JOIN student s ON ssr.student_id = s.student_id
                WHERE s.class_id IN ({class_ids_str}) AND ssr.is_deleted = 0
                AND ssr.get_date >= %s AND ssr.get_date <= %s
                GROUP BY period ORDER BY period""",
            (start_date, end_date)
        )

        # 合并数据
        trend_data = _merge_trend_data(task_data or [], record_data or [], unit)

    return {
        "success": True,
        "data": {
            "grade_id": grade_id,
            "grade_name": grade_name,
            "class_count": len(class_ids),
            "unit": unit,
            "semester_id": semester.get('semester_id') if semester else None,
            "trend": trend_data,
            "updated_at": _now_text(),
        },
    }


@router.get("/teacher-record-trend", summary="教师德育记录趋势")
async def get_teacher_record_trend(
    teacher_name: Optional[str] = Query(None, description="教师姓名，默认当前教师"),
    unit: str = Query('week', description="聚合单位：week 或 month"),
    semester_id: Optional[int] = Query(None, description="学期ID，默认当前学期"),
    user: User = Depends(get_current_user),
):
    """教师德育记录数量趋势图数据。

    数据来源：
    - student_daily_record：日常记录
    - student_moment_record：点滴记录

    Args:
        teacher_name: 教师姓名（德育管理员可查看其他教师）
        unit: 聚合单位
        semester_id: 学期ID
        user: 当前用户

    Returns:
        教师德育记录趋势数据
    """
    with get_moral_db() as db:
        # 权限判断
        if teacher_name and teacher_name != user.username:
            # 查看其他教师需要德育管理员权限
            if not _is_moral_manager(user):
                raise HTTPException(status_code=403, detail="只能查看自己的记录")
            target_teacher = teacher_name
        else:
            target_teacher = user.username

        # 获取学期信息
        if not semester_id:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE status = 1"
            )
        else:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = %s",
                (semester_id,)
            )

        if not semester:
            return {
                "success": True,
                "data": {
                    "teacher_name": target_teacher,
                    "unit": unit,
                    "trend": {"periods": [], "labels": [], "daily_count": [], "moment_count": [], "total_count": []},
                    "updated_at": _now_text(),
                }
            }

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        # 日常记录趋势
        daily_data = db.query_all(
            f"""SELECT strftime('{period_format}', record_date) as period, COUNT(*) as count
                FROM student_daily_record
                WHERE recorder = %s AND is_deleted = 0
                AND record_date >= %s AND record_date <= %s
                GROUP BY period ORDER BY period""",
            (target_teacher, start_date, end_date)
        )

        # 点滴记录趋势
        moment_data = db.query_all(
            f"""SELECT strftime('{period_format}', record_date) as period, COUNT(*) as count
                FROM moment_record
                WHERE recorder = %s
                AND record_date >= %s AND record_date <= %s
                GROUP BY period ORDER BY period""",
            (target_teacher, start_date, end_date)
        )

        # 合并数据
        all_periods = set()
        daily_map = {}
        moment_map = {}

        for row in daily_data or []:
            period = row.get('period', '')
            all_periods.add(period)
            daily_map[period] = row.get('count', 0) or 0

        for row in moment_data or []:
            period = row.get('period', '')
            all_periods.add(period)
            moment_map[period] = row.get('count', 0) or 0

        sorted_periods = sorted(all_periods)

        periods = []
        labels = []
        daily_counts = []
        moment_counts = []
        total_counts = []

        for period in sorted_periods:
            if period:
                periods.append(period)
                labels.append(_format_period_label(period, unit))
                dc = daily_map.get(period, 0)
                mc = moment_map.get(period, 0)
                daily_counts.append(dc)
                moment_counts.append(mc)
                total_counts.append(dc + mc)

    return {
        "success": True,
        "data": {
            "teacher_name": target_teacher,
            "unit": unit,
            "semester_id": semester.get('semester_id') if semester else None,
            "trend": {
                "periods": periods,
                "labels": labels,
                "daily_count": daily_counts,
                "moment_count": moment_counts,
                "total_count": total_counts,
            },
            "updated_at": _now_text(),
        },
    }