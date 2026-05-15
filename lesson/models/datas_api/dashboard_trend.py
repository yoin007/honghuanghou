# -*- coding: utf-8 -*-
"""Dashboard 趋势图 API。

提供学生得分趋势、班级/年级平均趋势、教师德育记录趋势等 API。
"""

from datetime import date
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from models.datas_api.auth import User
from models.datas_api.moral.base import (
    get_moral_db,
    has_user_role,
    get_record_data_scope,
)
from models.datas_api.moral.api_permission import require_configured_api_permission
from models.datas_api.dashboard_common import (
    is_moral_manager as _is_moral_manager,
    is_jiaowu as _is_jiaowu,
    now_text as _now_text,
)

router = APIRouter(prefix="/dashboard", tags=["数据驾驶舱趋势图"])

API_DASHBOARD_STUDENT_TREND = "/api/dashboard/score-trend/student/{student_id}"
API_DASHBOARD_CLASS_TREND = "/api/dashboard/score-trend/class/{class_id}"
API_DASHBOARD_GRADE_TREND = "/api/dashboard/score-trend/grade/{grade_id}"
API_DASHBOARD_TEACHER_RECORD_TREND = "/api/dashboard/teacher-record-trend"


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


def _merge_class_moral_trend(
    daily_data, school_data, task_data, collective_data, punishment_data,
    base_score, unit, student_count
):
    """合并班级德育总分各组成部分的平均变化趋势（累计）。

    计算逻辑：每周期总得分 / 班级学生数 = 班级平均得分变化

    Args:
        daily_data: 日常记录总得分趋势
        school_data: 校级事件总得分趋势
        task_data: 任务完成总得分趋势
        collective_data: 集体活动总得分趋势
        punishment_data: 处分扣分总得分趋势
        base_score: 基础分
        unit: 聚合单位
        student_count: 班级学生数

    Returns:
        班级平均德育总分累计趋势数据
    """
    # 合并所有周期
    all_periods = set()
    maps = {
        'daily': {},
        'school': {},
        'task': {},
        'collective': {},
        'punishment': {},
    }

    for row in daily_data:
        period = row.get('period', '')
        all_periods.add(period)
        # 总得分 / 学生数 = 班级平均得分变化
        maps['daily'][period] = (row.get('total_score', 0) or 0) / student_count

    for row in school_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['school'][period] = (row.get('total_score', 0) or 0) / student_count

    for row in task_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['task'][period] = (row.get('total_score', 0) or 0) / student_count

    for row in collective_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['collective'][period] = (row.get('total_score', 0) or 0) / student_count

    for row in punishment_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['punishment'][period] = (row.get('total_score', 0) or 0) / student_count

    # 按周期排序
    sorted_periods = sorted(all_periods)

    # 构建累计结果
    periods = []
    labels = []
    daily_cumulative = []
    school_cumulative = []
    task_cumulative = []
    collective_cumulative = []
    punishment_cumulative = []
    total_cumulative = []

    # 累计平均分
    daily_sum = 0
    school_sum = 0
    task_sum = 0
    collective_sum = 0
    punishment_sum = 0

    for period in sorted_periods:
        if period:
            periods.append(period)
            labels.append(_format_period_label(period, unit))

            # 累计各分项平均分
            daily_sum += maps['daily'].get(period, 0)
            school_sum += maps['school'].get(period, 0)
            task_sum += maps['task'].get(period, 0)
            collective_sum += maps['collective'].get(period, 0)
            punishment_sum += maps['punishment'].get(period, 0)

            # 记录累计平均分
            daily_cumulative.append(round(daily_sum, 2))
            school_cumulative.append(round(school_sum, 2))
            task_cumulative.append(round(task_sum, 2))
            collective_cumulative.append(round(collective_sum, 2))
            punishment_cumulative.append(round(punishment_sum, 2))

            # 计算累计班级平均德育总分
            total_score = base_score + daily_sum + school_sum + task_sum + collective_sum - punishment_sum
            total_cumulative.append(round(total_score, 1))

    # 如果没有数据，返回基础分作为学期起点（而不是空结构）
    if not periods:
        # 德育分从基础分开始，显示起点让用户知道班级分数状态
        return {
            "periods": ["baseline"],
            "labels": ["学期起点"],
            "daily_scores": [0],
            "school_scores": [0],
            "task_scores": [0],
            "collective_scores": [0],
            "punishment_scores": [0],
            "total_scores": [base_score],  # 基础分作为起点
            "has_changes": False,  # 标记无变化记录
        }

    return {
        "periods": periods,
        "labels": labels,
        "daily_scores": daily_cumulative,
        "school_scores": school_cumulative,
        "task_scores": task_cumulative,
        "collective_scores": collective_cumulative,
        "punishment_scores": punishment_cumulative,
        "total_scores": total_cumulative,
        "has_changes": True,  # 标记有变化记录
    }


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
        "daily_scores": [],
        "school_scores": [],
        "task_scores": [],
        "collective_scores": [],
        "punishment_scores": [],
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
        # 兼容 'score' 和 'avg_score' 字段名
        score = row.get('score') or row.get('avg_score') or 0
        task_map[period] = score

    for row in record_data:
        period = row.get('period', '')
        all_periods.add(period)
        # 兼容 'score' 和 'avg_score' 字段名
        score = row.get('score') or row.get('avg_score') or 0
        record_map[period] = score

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


def _merge_moral_score_trend(daily_data, school_data, task_data, collective_data, punishment_data, base_score, unit, start_date, end_date):
    """合并德育总分各组成部分的累计变化趋势。

    Args:
        daily_data: 日常记录得分趋势
        school_data: 校级事件得分趋势
        task_data: 任务完成得分趋势
        collective_data: 集体活动得分趋势
        punishment_data: 处分扣分趋势
        base_score: 基础分（60分）
        unit: 聚合单位
        start_date: 学期开始日期
        end_date: 学期结束日期

    Returns:
        累计德育总分趋势数据
    """
    # 合并所有周期
    all_periods = set()
    maps = {
        'daily': {},
        'school': {},
        'task': {},
        'collective': {},
        'punishment': {},
    }

    for row in daily_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['daily'][period] = row.get('score', 0) or 0

    for row in school_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['school'][period] = row.get('score', 0) or 0

    for row in task_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['task'][period] = row.get('score', 0) or 0

    for row in collective_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['collective'][period] = row.get('score', 0) or 0

    for row in punishment_data:
        period = row.get('period', '')
        all_periods.add(period)
        maps['punishment'][period] = row.get('score', 0) or 0

    # 按周期排序
    sorted_periods = sorted(all_periods)

    # 构建累计结果
    periods = []
    labels = []
    daily_cumulative = []
    school_cumulative = []
    task_cumulative = []
    collective_cumulative = []
    punishment_cumulative = []
    total_cumulative = []

    # 累计值
    daily_sum = 0
    school_sum = 0
    task_sum = 0
    collective_sum = 0
    punishment_sum = 0

    for period in sorted_periods:
        if period:
            periods.append(period)
            labels.append(_format_period_label(period, unit))

            # 累计各分项
            daily_sum += maps['daily'].get(period, 0)
            school_sum += maps['school'].get(period, 0)
            task_sum += maps['task'].get(period, 0)
            collective_sum += maps['collective'].get(period, 0)
            punishment_sum += maps['punishment'].get(period, 0)

            # 记录累计值
            daily_cumulative.append(daily_sum)
            school_cumulative.append(school_sum)
            task_cumulative.append(task_sum)
            collective_cumulative.append(collective_sum)
            punishment_cumulative.append(punishment_sum)

            # 计算累计德育总分
            total_score = base_score + daily_sum + school_sum + task_sum + collective_sum - punishment_sum
            total_cumulative.append(round(total_score, 1))

    # 如果没有数据，返回基础分作为学期起点（而不是空结构）
    if not periods:
        # 德育分从基础分开始，显示起点让用户知道学生分数状态
        return {
            "periods": ["baseline"],
            "labels": ["学期起点"],
            "daily_scores": [0],
            "school_scores": [0],
            "task_scores": [0],
            "collective_scores": [0],
            "punishment_scores": [0],
            "total_scores": [base_score],  # 基础分作为起点
            "has_changes": False,  # 标记无变化记录
        }

    return {
        "periods": periods,
        "labels": labels,
        "daily_scores": daily_cumulative,
        "school_scores": school_cumulative,
        "task_scores": task_cumulative,
        "collective_scores": collective_cumulative,
        "punishment_scores": punishment_cumulative,
        "total_scores": total_cumulative,
        "has_changes": True,  # 标记有变化记录
    }


@router.get("/score-trend/student/{student_id}", summary="学生个人得分趋势")
async def get_student_score_trend(
    student_id: str,
    unit: str = Query('week', description="聚合单位：week 或 month"),
    semester_id: Optional[int] = Query(None, description="学期ID，默认当前学期"),
    user: User = Depends(require_configured_api_permission(API_DASHBOARD_STUDENT_TREND, "GET", allow_missing=False)),
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
            "SELECT student_id, name, class_id, grade_id FROM student WHERE student_id = ?",
            (student_id,)
        )
        if not student:
            raise HTTPException(status_code=404, detail="学生不存在")

        class_id = student.get('class_id')
        grade_id = student.get('grade_id')

        # 权限检查：配置驱动数据范围
        scope = get_record_data_scope(
            db, user, API_DASHBOARD_STUDENT_TREND,
            all_permissions=['report_view_all'],
            own_class_permissions=['report_view_own_class'],
            own_permissions=[]
        )

        if not scope.get('can_all'):
            allowed_class_ids = scope.get('my_class_ids', []) + scope.get('my_grade_class_ids', [])
            if class_id not in allowed_class_ids:
                raise HTTPException(status_code=403, detail="只能查看授权范围内的学生")

        # 获取学期信息
        if not semester_id:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE status = 1"
            )
        else:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = ?",
                (semester_id,)
            )

        if not semester:
            return {"success": True, "data": _build_empty_trend_response(unit)}

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        # 德育总分累计变化趋势
        # 1. 日常记录得分累计（正向/需改进）
        daily_data = db.query_all(
            f"""SELECT strftime('{period_format}', record_date) as period, SUM(score) as score
                FROM student_daily_record
                WHERE student_id = ? AND is_deleted = 0
                AND record_date >= ? AND record_date <= ?
                GROUP BY period ORDER BY period""",
            (student_id, start_date, end_date)
        )

        # 2. 校级事件得分累计
        school_data = db.query_all(
            f"""SELECT strftime('{period_format}', get_date) as period, SUM(score) as score
                FROM student_school_record
                WHERE student_id = ? AND is_deleted = 0
                AND get_date >= ? AND get_date <= ?
                GROUP BY period ORDER BY period""",
            (student_id, start_date, end_date)
        )

        # 3. 任务完成得分累计
        task_data = db.query_all(
            f"""SELECT strftime('{period_format}', finish_date) as period, SUM(current_score) as score
                FROM student_task_finish
                WHERE student_id = ? AND status = 1
                AND finish_date >= ? AND finish_date <= ?
                GROUP BY period ORDER BY period""",
            (student_id, start_date, end_date)
        )

        # 4. 集体活动得分累计
        collective_data = db.query_all(
            f"""SELECT strftime('{period_format}', ce.event_date) as period, SUM(ced.score_assigned) as score
                FROM collective_event_distribution ced
                JOIN collective_event ce ON ced.event_id = ce.event_id
                WHERE ced.student_id = ? AND ced.is_participant = 1
                AND ce.event_date >= ? AND ce.event_date <= ?
                GROUP BY period ORDER BY period""",
            (student_id, start_date, end_date)
        )

        # 5. 处分扣分累计（取负数）
        punishment_data = db.query_all(
            f"""SELECT strftime('{period_format}', punishment_date) as period, SUM(ABS(score_deduct)) as score
                FROM punishment_record
                WHERE student_id = ? AND is_revoked = 0
                AND punishment_date >= ? AND punishment_date <= ?
                GROUP BY period ORDER BY period""",
            (student_id, start_date, end_date)
        )

        # 从配置表读取基础分（与评价模块保持一致）
        base_score_config = db.query_value(
            "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
        )
        base_score = float(base_score_config or 80)

        # 合并所有数据，计算累计德育总分
        trend_data = _merge_moral_score_trend(
            daily_data or [], school_data or [], task_data or [],
            collective_data or [], punishment_data or [],
            base_score, unit, start_date, end_date
        )

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
    user: User = Depends(require_configured_api_permission(API_DASHBOARD_CLASS_TREND, "GET", allow_missing=False)),
):
    """班级平均得分趋势图数据。

    实时聚合班级所有学生的德育总分变化，包含：
    - 基础分
    - 日常记录得分
    - 校级事件得分
    - 任务完成得分
    - 集体活动得分
    - 处分扣分

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
            "SELECT class_id, class_name FROM class WHERE class_id = ? AND is_active = 1",
            (class_id,)
        )
        if not class_info:
            raise HTTPException(status_code=404, detail="班级不存在")

        # 权限检查：配置驱动数据范围
        scope = get_record_data_scope(
            db, user, API_DASHBOARD_CLASS_TREND,
            all_permissions=['report_view_all'],
            own_class_permissions=['report_view_own_class'],
            own_permissions=[]
        )

        if not scope.get('can_all'):
            allowed_class_ids = scope.get('my_class_ids', []) + scope.get('my_grade_class_ids', [])
            if class_id not in allowed_class_ids:
                raise HTTPException(status_code=403, detail="只能查看授权范围内的班级")

        # 获取学期信息
        if not semester_id:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE status = 1"
            )
        else:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = ?",
                (semester_id,)
            )

        if not semester:
            return {"success": True, "data": _build_empty_trend_response(unit)}

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        # 从配置表读取基础分
        base_score_config = db.query_value(
            "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
        )
        base_score = float(base_score_config or 80)

        # 班级学生数
        student_count = db.query_value(
            "SELECT COUNT(*) FROM student WHERE class_id = ?",
            (class_id,)
        ) or 1

        # 实时聚合班级各分项总得分趋势（后续除以学生数得到平均）
        # 1. 日常记录总得分趋势
        daily_data = db.query_all(
            f"""SELECT strftime('{period_format}', record_date) as period,
                       SUM(score) as total_score
                FROM student_daily_record
                WHERE class_id = ? AND is_deleted = 0
                AND record_date >= ? AND record_date <= ?
                GROUP BY period ORDER BY period""",
            (class_id, start_date, end_date)
        )

        # 2. 校级事件总得分趋势
        school_data = db.query_all(
            f"""SELECT strftime('{period_format}', get_date) as period,
                       SUM(score) as total_score
                FROM student_school_record
                WHERE class_id = ? AND is_deleted = 0
                AND get_date >= ? AND get_date <= ?
                GROUP BY period ORDER BY period""",
            (class_id, start_date, end_date)
        )

        # 3. 任务完成总得分趋势
        task_data = db.query_all(
            f"""SELECT strftime('{period_format}', stf.finish_date) as period,
                       SUM(stf.current_score) as total_score
                FROM student_task_finish stf
                JOIN student s ON stf.student_id = s.student_id
                WHERE s.class_id = ? AND stf.status = 1
                AND stf.finish_date >= ? AND stf.finish_date <= ?
                GROUP BY period ORDER BY period""",
            (class_id, start_date, end_date)
        )

        # 4. 集体活动总得分趋势
        collective_data = db.query_all(
            f"""SELECT strftime('{period_format}', ce.event_date) as period,
                       SUM(ced.score_assigned) as total_score
                FROM collective_event_distribution ced
                JOIN collective_event ce ON ced.event_id = ce.event_id
                WHERE ced.class_id = ? AND ced.is_participant = 1
                AND ce.event_date >= ? AND ce.event_date <= ?
                GROUP BY period ORDER BY period""",
            (class_id, start_date, end_date)
        )

        # 5. 处分扣分总得分趋势
        punishment_data = db.query_all(
            f"""SELECT strftime('{period_format}', punishment_date) as period,
                       SUM(ABS(score_deduct)) as total_score
                FROM punishment_record
                WHERE class_id = ? AND is_revoked = 0
                AND punishment_date >= ? AND punishment_date <= ?
                GROUP BY period ORDER BY period""",
            (class_id, start_date, end_date)
        )

        # 合并数据，计算班级平均德育总分变化（累计）
        trend_data = _merge_class_moral_trend(
            daily_data or [], school_data or [], task_data or [],
            collective_data or [], punishment_data or [],
            base_score, unit, student_count
        )

    return {
        "success": True,
        "data": {
            "class_id": class_id,
            "class_name": class_info.get('class_name'),
            "unit": unit,
            "semester_id": semester.get('semester_id') if semester else None,
            "student_count": student_count,
            "trend": trend_data,
            "updated_at": _now_text(),
        },
    }


@router.get("/score-trend/grade/{grade_id}", summary="年级平均得分趋势")
async def get_grade_score_trend(
    grade_id: str,
    unit: str = Query('week', description="聚合单位：week 或 month"),
    semester_id: Optional[int] = Query(None, description="学期ID，默认当前学期"),
    user: User = Depends(require_configured_api_permission(API_DASHBOARD_GRADE_TREND, "GET", allow_missing=False)),
):
    """年级平均得分趋势图数据。

    Args:
        grade_id: 年级ID（如高一、高二、高三）或年级数据库ID
        unit: 聚合单位
        semester_id: 学期ID
        user: 当前用户

    Returns:
        年级平均得分趋势数据
    """
    with get_moral_db() as db:
        # 年级名称映射
        grade_names = {"高一": "高一年级", "高二": "高二年级", "高三": "高三年级"}
        grade_name = grade_names.get(grade_id, grade_id)

        # 获取年级ID
        grade_row = db.query_one(
            "SELECT grade_id, grade_name FROM grade WHERE grade_name = ? OR grade_name = ? OR grade_id = ?",
            (grade_name, grade_id + "年级", grade_id)
        )
        grade_id_int = grade_row["grade_id"] if grade_row else None

        if not grade_id_int:
            raise HTTPException(status_code=404, detail="年级不存在")

        # 权限检查：配置驱动数据范围
        scope = get_record_data_scope(
            db, user, API_DASHBOARD_GRADE_TREND,
            all_permissions=['report_view_all'],
            own_class_permissions=['report_view_own_class'],
            own_permissions=[]
        )
        if not scope.get('can_all'):
            managed_grade_ids = set(scope.get('my_grade_ids', []))
            if grade_id_int not in managed_grade_ids:
                raise HTTPException(status_code=403, detail="只能查看授权范围内的年级")

        # 获取年级下所有班级（通过 grade_id 关联）
        if grade_id_int:
            classes = db.query_all(
                "SELECT class_id, class_name FROM class WHERE is_active = 1 AND grade_id = ?",
                (grade_id_int,)
            )
        else:
            # 兜底：用班级名匹配
            grade_filter = f"%{grade_id}%"
            classes = db.query_all(
                "SELECT class_id, class_name FROM class WHERE is_active = 1 AND class_name LIKE ?",
                (grade_filter,)
            )
        class_ids = [c['class_id'] for c in classes]

        if not class_ids:
            raise HTTPException(status_code=404, detail="年级不存在或无班级")
        if not scope.get('can_all'):
            managed_grade_class_ids = set(scope.get('my_grade_class_ids', []))
            if not managed_grade_class_ids or not set(class_ids).issubset(managed_grade_class_ids):
                raise HTTPException(status_code=403, detail="只能查看授权范围内的年级")

        # 获取学期信息
        if not semester_id:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE status = 1"
            )
        else:
            semester = db.query_one(
                "SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = ?",
                (semester_id,)
            )

        if not semester:
            return {"success": True, "data": _build_empty_trend_response(unit)}

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        class_ids_str = ','.join(map(str, class_ids))

        # 年级学生总数（用于计算平均）
        student_count = db.query_value(
            f"SELECT COUNT(*) FROM student WHERE class_id IN ({class_ids_str})"
        ) or 1

        # 1. 年级日常记录平均趋势
        daily_data = db.query_all(
            f"""SELECT strftime('{period_format}', record_date) as period,
                       SUM(score) as total_score
                FROM student_daily_record
                WHERE class_id IN ({class_ids_str}) AND is_deleted = 0
                AND record_date >= ? AND record_date <= ?
                GROUP BY period ORDER BY period""",
            (start_date, end_date)
        )

        # 2. 年级校级事件平均趋势
        school_data = db.query_all(
            f"""SELECT strftime('{period_format}', get_date) as period,
                       SUM(score) as total_score
                FROM student_school_record
                WHERE class_id IN ({class_ids_str}) AND is_deleted = 0
                AND get_date >= ? AND get_date <= ?
                GROUP BY period ORDER BY period""",
            (start_date, end_date)
        )

        # 3. 年级任务得分平均趋势
        task_data = db.query_all(
            f"""SELECT strftime('{period_format}', stf.finish_date) as period,
                       SUM(stf.current_score) as total_score
                FROM student_task_finish stf
                JOIN student s ON stf.student_id = s.student_id
                WHERE s.class_id IN ({class_ids_str}) AND stf.status = 1
                AND stf.finish_date >= ? AND stf.finish_date <= ?
                GROUP BY period ORDER BY period""",
            (start_date, end_date)
        )

        # 4. 年级集体活动平均趋势
        collective_data = db.query_all(
            f"""SELECT strftime('{period_format}', ce.event_date) as period,
                       SUM(ced.score_assigned) as total_score
                FROM collective_event_distribution ced
                JOIN collective_event ce ON ced.event_id = ce.event_id
                WHERE ced.class_id IN ({class_ids_str}) AND ced.is_participant = 1
                AND ce.event_date >= ? AND ce.event_date <= ?
                GROUP BY period ORDER BY period""",
            (start_date, end_date)
        )

        # 5. 年级处分扣分平均趋势
        punishment_data = db.query_all(
            f"""SELECT strftime('{period_format}', punishment_date) as period,
                       SUM(ABS(score_deduct)) as total_score
                FROM punishment_record
                WHERE class_id IN ({class_ids_str}) AND is_revoked = 0
                AND punishment_date >= ? AND punishment_date <= ?
                GROUP BY period ORDER BY period""",
            (start_date, end_date)
        )

        # 从配置表读取基础分
        base_score_config = db.query_value(
            "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
        )
        base_score = float(base_score_config or 80)

        # 合并数据（使用班级合并函数，计算平均）
        trend_data = _merge_class_moral_trend(
            daily_data or [], school_data or [], task_data or [],
            collective_data or [], punishment_data or [],
            base_score, unit, student_count
        )

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
    user: User = Depends(require_configured_api_permission(API_DASHBOARD_TEACHER_RECORD_TREND, "GET", allow_missing=False)),
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
        # 权限判断：管理员/年级主任可查看其他教师
        if teacher_name and teacher_name != user.username:
            if not (_is_moral_manager(user) or has_user_role(user, 'g_leader')):
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
                "SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = ?",
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
                WHERE recorder = ? AND is_deleted = 0
                AND record_date >= ? AND record_date <= ?
                GROUP BY period ORDER BY period""",
            (target_teacher, start_date, end_date)
        )

        # 点滴记录趋势
        moment_data = db.query_all(
            f"""SELECT strftime('{period_format}', record_date) as period, COUNT(*) as count
                FROM moment_record
                WHERE recorder = ?
                AND record_date >= ? AND record_date <= ?
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


# 新增 API 常量
API_DASHBOARD_GRADE_CLASSES_TREND = "/api/dashboard/score-trend/grade/{grade_id}/classes"
API_DASHBOARD_ALL_CLASSES_TREND = "/api/dashboard/score-trend/all-classes"


@router.get("/score-trend/grade/{grade_id}/classes", summary="年级班级对比趋势")
async def get_grade_classes_score_trend(
    grade_id: str,
    unit: str = Query('week', description="聚合单位：week 或 month"),
    semester_id: Optional[int] = Query(None, description="学期ID，默认当前学期"),
    user: User = Depends(require_configured_api_permission(API_DASHBOARD_GRADE_CLASSES_TREND, "GET", allow_missing=False)),
):
    """年级下各班级德育总分对比趋势图数据。

    按班级 class_code 排序，返回每个班级在各周期的德育总分变化。

    Args:
        grade_id: 年级ID或年级名称（如高一）
        unit: 聚合单位
        semester_id: 学期ID
        user: 当前用户

    Returns:
        各班级趋势数据，按 class_code 排序
    """
    with get_moral_db() as db:
        # 年级名称映射
        grade_names = {"高一": "高一年级", "高二": "高二年级", "高三": "高三年级"}
        grade_name = grade_names.get(grade_id, grade_id)

        # 获取年级ID
        grade_row = db.query_one(
            "SELECT grade_id, grade_name FROM grade WHERE grade_name = ? OR grade_name = ? OR grade_id = ?",
            (grade_name, grade_id + "年级", grade_id)
        )
        grade_id_int = grade_row["grade_id"] if grade_row else None

        if not grade_id_int:
            raise HTTPException(status_code=404, detail="年级不存在")

        # 权限检查
        scope = get_record_data_scope(
            db, user, API_DASHBOARD_GRADE_CLASSES_TREND,
            all_permissions=['report_view_all'],
            own_class_permissions=['report_view_own_class'],
            own_permissions=[]
        )
        if not scope.get('can_all'):
            managed_grade_ids = set(scope.get('my_grade_ids', []))
            if grade_id_int not in managed_grade_ids:
                raise HTTPException(status_code=403, detail="只能查看授权范围内的年级")

        # 获取年级下所有班级，按 class_code 排序
        classes = db.query_all(
            "SELECT class_id, class_code, class_name, grade_id FROM class WHERE is_active = 1 AND grade_id = ? ORDER BY class_code",
            (grade_id_int,)
        )

        if not classes:
            raise HTTPException(status_code=404, detail="年级下无班级")

        # 获取学期信息
        if not semester_id:
            semester = db.query_one("SELECT semester_id, start_date, end_date FROM semester WHERE status = 1")
        else:
            semester = db.query_one("SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = ?", (semester_id,))

        if not semester:
            return {"success": True, "data": {"periods": [], "labels": [], "classes": [], "unit": unit}}

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        # 基础分
        base_score_config = db.query_value(
            "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
        )
        base_score = float(base_score_config or 80)

        # 批量查询所有班级的趋势数据
        class_ids = [c['class_id'] for c in classes]
        class_ids_str = ','.join(map(str, class_ids))

        # 批量查询各分项趋势
        # 1. 日常记录
        daily_data = db.query_all(
            f"""SELECT class_id, strftime('{period_format}', record_date) as period, SUM(score) as total_score
                FROM student_daily_record
                WHERE class_id IN ({class_ids_str}) AND is_deleted = 0
                AND record_date >= ? AND record_date <= ?
                GROUP BY class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        # 2. 校级事件
        school_data = db.query_all(
            f"""SELECT class_id, strftime('{period_format}', get_date) as period, SUM(score) as total_score
                FROM student_school_record
                WHERE class_id IN ({class_ids_str}) AND is_deleted = 0
                AND get_date >= ? AND get_date <= ?
                GROUP BY class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        # 3. 任务完成
        task_data = db.query_all(
            f"""SELECT s.class_id, strftime('{period_format}', stf.finish_date) as period, SUM(stf.current_score) as total_score
                FROM student_task_finish stf
                JOIN student s ON stf.student_id = s.student_id
                WHERE s.class_id IN ({class_ids_str}) AND stf.status = 1
                AND stf.finish_date >= ? AND stf.finish_date <= ?
                GROUP BY s.class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        # 4. 集体活动
        collective_data = db.query_all(
            f"""SELECT ced.class_id, strftime('{period_format}', ce.event_date) as period, SUM(ced.score_assigned) as total_score
                FROM collective_event_distribution ced
                JOIN collective_event ce ON ced.event_id = ce.event_id
                WHERE ced.class_id IN ({class_ids_str}) AND ced.is_participant = 1
                AND ce.event_date >= ? AND ce.event_date <= ?
                GROUP BY ced.class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        # 5. 处分扣分
        punishment_data = db.query_all(
            f"""SELECT class_id, strftime('{period_format}', punishment_date) as period, SUM(ABS(score_deduct)) as total_score
                FROM punishment_record
                WHERE class_id IN ({class_ids_str}) AND is_revoked = 0
                AND punishment_date >= ? AND punishment_date <= ?
                GROUP BY class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        # 班级学生数
        class_student_counts = {}
        for c in classes:
            count = db.query_value("SELECT COUNT(*) FROM student WHERE class_id = ?", (c['class_id'],)) or 1
            class_student_counts[c['class_id']] = count

        # 为每个班级构建趋势数据
        class_trends = []
        all_periods = set()

        for cls in classes:
            class_id = cls['class_id']
            student_count = class_student_counts[class_id]

            # 过滤该班级的数据
            cls_daily = [r for r in daily_data if r['class_id'] == class_id]
            cls_school = [r for r in school_data if r['class_id'] == class_id]
            cls_task = [r for r in task_data if r['class_id'] == class_id]
            cls_collective = [r for r in collective_data if r['class_id'] == class_id]
            cls_punishment = [r for r in punishment_data if r['class_id'] == class_id]

            # 合并趋势
            trend = _merge_class_moral_trend(
                cls_daily, cls_school, cls_task, cls_collective, cls_punishment,
                base_score, unit, student_count
            )

            # 只收集有实际数据变化的周期（过滤 baseline 占位符）
            for p in trend['periods']:
                if p and p != "baseline":
                    all_periods.add(p)

            # 所有班级都显示（空数据班级显示基础分）
            class_trends.append({
                "class_id": class_id,
                "class_code": cls['class_code'],
                "class_name": cls['class_name'],
                "trend": {
                    "total_scores": trend['total_scores']
                }
            })

        # 统一周期排序
        sorted_periods = sorted(all_periods)
        labels = [_format_period_label(p, unit) for p in sorted_periods]

    return {
        "success": True,
        "data": {
            "grade_id": grade_id_int,
            "grade_name": grade_row.get('grade_name'),
            "unit": unit,
            "periods": sorted_periods,
            "labels": labels,
            "classes": class_trends,
            "updated_at": _now_text(),
        },
    }


@router.get("/score-trend/all-classes", summary="全校班级对比趋势")
async def get_all_classes_score_trend(
    unit: str = Query('week', description="聚合单位：week 或 month"),
    semester_id: Optional[int] = Query(None, description="学期ID，默认当前学期"),
    top_n: int = Query(50, ge=1, le=100, description="返回班级数量限制"),
    user: User = Depends(require_configured_api_permission(API_DASHBOARD_ALL_CLASSES_TREND, "GET", allow_missing=False)),
):
    """全校各班级德育总分对比趋势图数据。

    按 grade_id + class_code 排序，返回每个班级在各周期的德育总分变化。

    Args:
        unit: 聚合单位
        semester_id: 学期ID
        top_n: 班级数量限制
        user: 当前用户

    Returns:
        全校班级趋势数据，按年级+班级排序
    """
    with get_moral_db() as db:
        # 权限检查
        scope = get_record_data_scope(
            db, user, API_DASHBOARD_ALL_CLASSES_TREND,
            all_permissions=['report_view_all'],
            own_class_permissions=['report_view_own_class'],
            own_permissions=[]
        )

        # 获取班级列表（权限过滤）
        if scope.get('can_all'):
            classes = db.query_all(
                """SELECT c.class_id, c.class_code, c.class_name, c.grade_id, g.grade_name
                   FROM class c
                   JOIN grade g ON c.grade_id = g.grade_id
                   WHERE c.is_active = 1
                   ORDER BY g.grade_id, c.class_code
                   LIMIT ?""",
                (top_n,)
            )
        else:
            # 年级主任只能查看本年级班级
            my_grade_ids = scope.get('my_grade_ids', [])
            if my_grade_ids:
                grade_ids_str = ','.join(map(str, my_grade_ids))
                classes = db.query_all(
                    f"""SELECT c.class_id, c.class_code, c.class_name, c.grade_id, g.grade_name
                        FROM class c
                        JOIN grade g ON c.grade_id = g.grade_id
                        WHERE c.is_active = 1 AND c.grade_id IN ({grade_ids_str})
                        ORDER BY g.grade_id, c.class_code
                        LIMIT {top_n}"""
                )
            else:
                raise HTTPException(status_code=403, detail="无全校班级数据权限")

        if not classes:
            return {"success": True, "data": {"periods": [], "labels": [], "classes": [], "unit": unit}}

        # 获取学期信息
        if not semester_id:
            semester = db.query_one("SELECT semester_id, start_date, end_date FROM semester WHERE status = 1")
        else:
            semester = db.query_one("SELECT semester_id, start_date, end_date FROM semester WHERE semester_id = ?", (semester_id,))

        if not semester:
            return {"success": True, "data": {"periods": [], "labels": [], "classes": [], "unit": unit}}

        start_date = semester.get('start_date')
        end_date = semester.get('end_date')
        period_format = _get_period_format(unit)

        # 基础分
        base_score_config = db.query_value(
            "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
        )
        base_score = float(base_score_config or 80)

        # 批量查询所有班级的趋势数据
        class_ids = [c['class_id'] for c in classes]
        class_ids_str = ','.join(map(str, class_ids))

        # 批量查询各分项趋势
        daily_data = db.query_all(
            f"""SELECT class_id, strftime('{period_format}', record_date) as period, SUM(score) as total_score
                FROM student_daily_record
                WHERE class_id IN ({class_ids_str}) AND is_deleted = 0
                AND record_date >= ? AND record_date <= ?
                GROUP BY class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        school_data = db.query_all(
            f"""SELECT class_id, strftime('{period_format}', get_date) as period, SUM(score) as total_score
                FROM student_school_record
                WHERE class_id IN ({class_ids_str}) AND is_deleted = 0
                AND get_date >= ? AND get_date <= ?
                GROUP BY class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        task_data = db.query_all(
            f"""SELECT s.class_id, strftime('{period_format}', stf.finish_date) as period, SUM(stf.current_score) as total_score
                FROM student_task_finish stf
                JOIN student s ON stf.student_id = s.student_id
                WHERE s.class_id IN ({class_ids_str}) AND stf.status = 1
                AND stf.finish_date >= ? AND stf.finish_date <= ?
                GROUP BY s.class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        collective_data = db.query_all(
            f"""SELECT ced.class_id, strftime('{period_format}', ce.event_date) as period, SUM(ced.score_assigned) as total_score
                FROM collective_event_distribution ced
                JOIN collective_event ce ON ced.event_id = ce.event_id
                WHERE ced.class_id IN ({class_ids_str}) AND ced.is_participant = 1
                AND ce.event_date >= ? AND ce.event_date <= ?
                GROUP BY ced.class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        punishment_data = db.query_all(
            f"""SELECT class_id, strftime('{period_format}', punishment_date) as period, SUM(ABS(score_deduct)) as total_score
                FROM punishment_record
                WHERE class_id IN ({class_ids_str}) AND is_revoked = 0
                AND punishment_date >= ? AND punishment_date <= ?
                GROUP BY class_id, period ORDER BY period""",
            (start_date, end_date)
        )

        # 班级学生数
        class_student_counts = {}
        for c in classes:
            count = db.query_value("SELECT COUNT(*) FROM student WHERE class_id = ?", (c['class_id'],)) or 1
            class_student_counts[c['class_id']] = count

        # 为每个班级构建趋势数据
        class_trends = []
        all_periods = set()

        for cls in classes:
            class_id = cls['class_id']
            student_count = class_student_counts[class_id]

            # 过滤该班级的数据
            cls_daily = [r for r in daily_data if r['class_id'] == class_id]
            cls_school = [r for r in school_data if r['class_id'] == class_id]
            cls_task = [r for r in task_data if r['class_id'] == class_id]
            cls_collective = [r for r in collective_data if r['class_id'] == class_id]
            cls_punishment = [r for r in punishment_data if r['class_id'] == class_id]

            # 合并趋势
            trend = _merge_class_moral_trend(
                cls_daily, cls_school, cls_task, cls_collective, cls_punishment,
                base_score, unit, student_count
            )

            # 只收集有实际数据变化的周期（过滤 baseline 占位符）
            for p in trend['periods']:
                if p and p != "baseline":
                    all_periods.add(p)

            # 所有班级都显示（空数据班级显示基础分）
            class_trends.append({
                "class_id": class_id,
                "class_code": cls['class_code'],
                "class_name": cls['class_name'],
                "grade_name": cls['grade_name'],
                "trend": {
                    "total_scores": trend['total_scores']
                }
            })

        sorted_periods = sorted(all_periods)
        labels = [_format_period_label(p, unit) for p in sorted_periods]

    return {
        "success": True,
        "data": {
            "unit": unit,
            "periods": sorted_periods,
            "labels": labels,
            "classes": class_trends,
            "class_count": len(class_trends),
            "updated_at": _now_text(),
        },
    }
