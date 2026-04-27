# -*- coding: utf-8 -*-
"""
任务结转执行模块

实现学年末未完成任务的结转逻辑
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from .base import (
    get_moral_db,
    get_current_school_year,
    get_next_school_year,
    log_operation,
)

logger = logging.getLogger(__name__)

# 结转配置
CARRYOVER_FACTOR = 0.60  # 每次结转 ×60%
MAX_CARRYOVER_TIMES = 2   # 最大结转次数（高一→高二→高三）


# =============================================================================
# 核心结转函数
# =============================================================================

def execute_task_carryover(db, from_year_id: int, to_year_id: int) -> Dict[str, Any]:
    """
    执行学年末任务结转

    Args:
        db: 数据库连接
        from_year_id: 结转源学年ID（即将结束的学年）
        to_year_id: 结转目标学年ID（即将开始的学年）

    Returns:
        Dict: 结转结果统计
    """
    logger.info(f"开始执行任务结转：从学年 {from_year_id} 到学年 {to_year_id}")

    result = {
        'total_unfinished': 0,
        'carryover_success': 0,
        'carryover_skipped': 0,  # 超过最大次数，作废
        'carryover_failed': 0,
        'details': []
    }

    # 1. 查询所有未完成任务
    unfinished_tasks = db.query_all(
        """SELECT stf.id, stf.student_id, stf.task_id, stf.year_id,
           stf.is_carried_over, stf.carryover_count, stf.current_score,
           stf.status, stf.original_task_id, stf.original_year_id,
           t.task_name, t.score as original_task_score, t.can_carryover,
           s.name as student_name, c.class_name
        FROM student_task_finish stf
        JOIN grade_moral_task t ON stf.task_id = t.task_id
        JOIN student s ON stf.student_id = s.student_id
        JOIN class c ON s.class_id = c.class_id
        WHERE stf.year_id = %s
        AND stf.status = 0  -- 未完成
        AND t.can_carryover = 1  -- 允许结转
        AND t.is_active = 1""",
        (from_year_id,)
    )

    result['total_unfinished'] = len(unfinished_tasks)
    logger.info(f"发现 {len(unfinished_tasks)} 个未完成且可结转的任务")

    # 2. 遍历每个任务执行结转
    for task in unfinished_tasks:
        try:
            carryover_count = task['carryover_count'] or 0

            # 检查是否超过最大结转次数
            if carryover_count >= MAX_CARRYOVER_TIMES:
                # 任务作废
                db.execute(
                    """UPDATE student_task_finish SET status = 2 -- 已作废
                    WHERE id = %s""",
                    (task['id'],)
                )

                result['carryover_skipped'] += 1
                result['details'].append({
                    'student_id': task['student_id'],
                    'student_name': task['student_name'],
                    'task_name': task['task_name'],
                    'action': 'expired',
                    'reason': f'已结转{carryover_count}次，超过最大限制'
                })

                logger.info(f"任务作废：{task['student_name']} - {task['task_name']}，已结转{carryover_count}次")
                continue

            # 计算结转后分值
            current_score = Decimal(str(task['current_score'] or task['original_task_score']))
            new_score = current_score * Decimal(str(CARRYOVER_FACTOR))
            new_score = new_score.quantize(Decimal('0.01'))  # 保留两位小数

            new_carryover_count = carryover_count + 1

            # 更新任务状态
            db.execute(
                """UPDATE student_task_finish SET
                year_id = %s,
                is_carried_over = 1,
                carryover_count = %s,
                current_score = %s
                WHERE id = %s""",
                (to_year_id, new_carryover_count, float(new_score), task['id'])
            )

            # 记录结转日志
            db.execute(
                """INSERT INTO task_carryover_log
                (student_id, original_task_id, from_year_id, to_year_id,
                 carryover_index, score_before, score_after)
                VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (task['student_id'], task['original_task_id'] or task['task_id'],
                 from_year_id, to_year_id, new_carryover_count,
                 float(current_score), float(new_score))
            )

            result['carryover_success'] += 1
            result['details'].append({
                'student_id': task['student_id'],
                'student_name': task['student_name'],
                'task_name': task['task_name'],
                'action': 'carryover',
                'carryover_count': new_carryover_count,
                'score_before': float(current_score),
                'score_after': float(new_score)
            })

            logger.info(
                f"任务结转成功：{task['student_name']} - {task['task_name']}，"
                f"分值 {current_score} → {new_score}，第{new_carryover_count}次结转"
            )

        except Exception as e:
            result['carryover_failed'] += 1
            logger.error(f"任务结转失败：{task['student_id']} - {task['task_name']}，错误：{e}")

    logger.info(
        f"任务结转完成：总数 {result['total_unfinished']}, "
        f"成功 {result['carryover_success']}, "
        f"作废 {result['carryover_skipped']}, "
        f"失败 {result['carryover_failed']}"
    )

    return result


def get_next_school_year(db, current_year_id: int) -> Optional[Dict]:
    """
    获取下一个学年

    Args:
        db: 数据库连接
        current_year_id: 当前学年ID

    Returns:
        Dict: 下一个学年信息，若无则返回None
    """
    current_year = db.query_one(
        "SELECT year_id, year_name, start_year FROM school_year WHERE year_id = %s",
        (current_year_id,)
    )

    if not current_year:
        return None

    # 根据起始年份查找下一个学年
    next_start_year = current_year['start_year'] + 1
    next_year = db.query_one(
        "SELECT year_id, year_name, start_year FROM school_year WHERE start_year = %s",
        (next_start_year,)
    )

    return next_year


def manual_carryover_trigger(from_year_id: int, to_year_id: int, operator: str = 'system') -> Dict[str, Any]:
    """
    手动触发任务结转（用于API调用）

    Args:
        from_year_id: 源学年ID
        to_year_id: 目标学年ID
        operator: 操作者

    Returns:
        Dict: 结转结果
    """
    with get_moral_db() as db:
        # 验证学年有效性
        from_year = db.query_one(
            "SELECT * FROM school_year WHERE year_id = %s",
            (from_year_id,)
        )
        to_year = db.query_one(
            "SELECT * FROM school_year WHERE year_id = %s",
            (to_year_id,)
        )

        if not from_year or not to_year:
            raise ValueError("学年ID无效")

        # 执行结转
        result = execute_task_carryover(db, from_year_id, to_year_id)

        # 记录操作日志
        log_operation(
            db, operator, 'system', 'CARRYOVER', 'student_task_finish', None, None,
            new_data={
                'from_year_id': from_year_id,
                'to_year_id': to_year_id,
                'total': result['total_unfinished'],
                'success': result['carryover_success'],
                'skipped': result['carryover_skipped']
            }
        )

        return result


# =============================================================================
# API路由（用于手动触发结转）
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from models.datas_api.auth import User, get_current_user
from .base import require_permission

router = APIRouter(prefix="/carryover", tags=["任务结转"])


class CarryoverRequest(BaseModel):
    """结转请求"""
    from_year_id: int = Field(..., description="源学年ID")
    to_year_id: int = Field(..., description="目标学年ID")


@router.post("/execute", summary="执行任务结转")
async def api_execute_carryover(
    request: CarryoverRequest,
    req: Request,
    user: User = Depends(require_permission('semester_manage'))
):
    """
    手动执行任务结转

    权限要求：admin/jiaowu

    流程：
    1. 查询源学年所有未完成任务
    2. 检查结转次数（超过2次的作废）
    3. 计算新分值（×60%）
    4. 更新任务所属学年
    5. 记录结转日志
    """
    try:
        result = manual_carryover_trigger(
            request.from_year_id,
            request.to_year_id,
            user.username
        )

        return {
            "success": True,
            "message": f"结转完成：成功 {result['carryover_success']} 个，作废 {result['carryover_skipped']} 个",
            "data": result
        }

    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"任务结转执行失败：{e}")
        raise HTTPException(500, f"结转执行失败：{str(e)}")


@router.get("/preview", summary="预览结转情况")
async def api_preview_carryover(
    year_id: int,
    user: User = Depends(require_permission('semester_manage'))
):
    """
    预览某学年待结转任务情况

    返回：
    - 未完成任务列表
    - 各任务的当前分值和结转后分值
    - 将作废的任务列表
    """
    with get_moral_db() as db:
        # 获取下一个学年
        next_year = get_next_school_year(db, year_id)
        if not next_year:
            return {
                "success": True,
                "data": {
                    "has_next_year": False,
                    "message": "未找到下一学年，无法结转"
                }
            }

        # 查询待结转任务
        unfinished_tasks = db.query_all(
            """SELECT stf.id, stf.student_id, stf.task_id, stf.carryover_count,
               stf.current_score, stf.status,
               t.task_name, t.score as original_task_score, t.can_carryover,
               s.name as student_name, c.class_name
            FROM student_task_finish stf
            JOIN grade_moral_task t ON stf.task_id = t.task_id
            JOIN student s ON stf.student_id = s.student_id
            JOIN class c ON s.class_id = c.class_id
            WHERE stf.year_id = %s
            AND stf.status = 0
            AND t.can_carryover = 1
            AND t.is_active = 1""",
            (year_id,)
        )

        # 分类统计
        to_carryover = []
        to_expire = []

        for task in unfinished_tasks:
            carryover_count = task['carryover_count'] or 0
            current_score = Decimal(str(task['current_score'] or task['original_task_score']))

            if carryover_count >= MAX_CARRYOVER_TIMES:
                to_expire.append({
                    'student_id': task['student_id'],
                    'student_name': task['student_name'],
                    'task_name': task['task_name'],
                    'carryover_count': carryover_count,
                    'current_score': float(current_score),
                    'reason': '超过最大结转次数'
                })
            else:
                new_score = current_score * Decimal(str(CARRYOVER_FACTOR))
                to_carryover.append({
                    'student_id': task['student_id'],
                    'student_name': task['student_name'],
                    'task_name': task['task_name'],
                    'carryover_count': carryover_count,
                    'new_carryover_count': carryover_count + 1,
                    'score_before': float(current_score),
                    'score_after': float(new_score.quantize(Decimal('0.01')))
                })

        return {
            "success": True,
            "data": {
                "has_next_year": True,
                "next_year": next_year,
                "from_year_id": year_id,
                "to_year_id": next_year['year_id'],
                "carryover_factor": CARRYOVER_FACTOR,
                "max_carryover_times": MAX_CARRYOVER_TIMES,
                "total_unfinished": len(unfinished_tasks),
                "to_carryover": to_carryover,
                "to_expire": to_expire,
                "carryover_count": len(to_carryover),
                "expire_count": len(to_expire)
            }
        }


@router.get("/logs", summary="获取结转日志")
async def api_get_carryover_logs(
    student_id: Optional[str] = None,
    year_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user)
):
    """
    获取任务结转日志列表
    """
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if student_id:
            conditions.append("tcl.student_id = %s")
            params.append(student_id)

        if year_id:
            conditions.append("tcl.from_year_id = %s OR tcl.to_year_id = %s")
            params.extend([year_id, year_id])

        where_clause = " AND ".join(conditions)

        count_query = f"SELECT COUNT(*) FROM task_carryover_log tcl WHERE {where_clause}"
        total = db.query_value(count_query, tuple(params) if params else None)

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT tcl.*, s.name as student_name, t.task_name,
                   sy_from.year_name as from_year_name,
                   sy_to.year_name as to_year_name
            FROM task_carryover_log tcl
            JOIN student s ON tcl.student_id = s.student_id
            JOIN grade_moral_task t ON tcl.original_task_id = t.task_id
            JOIN school_year sy_from ON tcl.from_year_id = sy_from.year_id
            JOIN school_year sy_to ON tcl.to_year_id = sy_to.year_id
            WHERE {where_clause}
            ORDER BY tcl.created_at DESC
            LIMIT %s OFFSET %s
        """
        params.extend([page_size, offset])
        logs = db.query_all(data_query, tuple(params) if params else None)

        return {
            "success": True,
            "data": {
                "items": logs,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }