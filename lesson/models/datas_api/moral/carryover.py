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

# 默认结转配置（当数据库配置不存在时使用）
DEFAULT_CARRYOVER_FACTOR = 0.60
DEFAULT_MAX_CARRYOVER_TIMES = 2


def get_carryover_config(db) -> Dict[str, Any]:
    """
    获取结转配置参数

    从 moral_config 表读取配置，不存在时使用默认值

    Returns:
        Dict: {carryover_factor, max_carryover_times}
    """
    config = db.query_one(
        "SELECT config_value FROM moral_config WHERE config_key = 'carryover_config'"
    )

    if config:
        try:
            import json
            data = json.loads(config['config_value'])
            return {
                'carryover_factor': float(data.get('carryover_factor', DEFAULT_CARRYOVER_FACTOR)),
                'max_carryover_times': int(data.get('max_carryover_times', DEFAULT_MAX_CARRYOVER_TIMES))
            }
        except Exception as e:
            logger.warning(f"解析结转配置失败: {e}")

    # 返回默认值
    return {
        'carryover_factor': DEFAULT_CARRYOVER_FACTOR,
        'max_carryover_times': DEFAULT_MAX_CARRYOVER_TIMES
    }


def save_carryover_config(db, carryover_factor: float, max_carryover_times: int) -> None:
    """
    保存结转配置参数

    Args:
        db: 数据库连接
        carryover_factor: 结转系数（0-1）
        max_carryover_times: 最大结转次数
    """
    import json
    config_value = json.dumps({
        'carryover_factor': carryover_factor,
        'max_carryover_times': max_carryover_times
    })

    existing = db.query_one(
        "SELECT config_id FROM moral_config WHERE config_key = 'carryover_config'"
    )

    if existing:
        db.execute(
            "UPDATE moral_config SET config_value = ? WHERE config_key = 'carryover_config'",
            (config_value,)
        )
    else:
        db.execute(
            "INSERT INTO moral_config (config_key, config_value) VALUES ('carryover_config', ?)",
            (config_value,)
        )


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

    # 获取结转配置
    config = get_carryover_config(db)
    CARRYOVER_FACTOR = config['carryover_factor']
    MAX_CARRYOVER_TIMES = config['max_carryover_times']

    result = {
        'total_unfinished': 0,
        'carryover_success': 0,
        'carryover_skipped': 0,  # 超过最大次数，作废
        'carryover_failed': 0,
        'details': [],
        'config': config  # 返回配置参数供前端显示
    }

    # 1. 查询所有未完成任务（仅在校学生）
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
        WHERE stf.year_id = ?
        AND stf.status = 0  -- 未完成
        AND t.can_carryover = 1  -- 允许结转
        AND t.is_active = 1
        AND s.status = '在校'  -- 仅处理在校学生""",
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
                    WHERE id = ?""",
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
                year_id = ?,
                is_carried_over = 1,
                carryover_count = ?,
                current_score = ?
                WHERE id = ?""",
                (to_year_id, new_carryover_count, float(new_score), task['id'])
            )

            # 记录结转日志
            db.execute(
                """INSERT INTO task_carryover_log
                (student_id, original_task_id, from_year_id, to_year_id,
                 carryover_index, score_before, score_after)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
        "SELECT year_id, year_name FROM school_year WHERE year_id = ?",
        (current_year_id,)
    )

    if not current_year:
        return None

    # 从 year_name 提取起始年份（如 "2025-2026学年" -> 2025）
    import re
    match = re.match(r'(\d{4})', current_year['year_name'])
    if not match:
        return None

    start_year = int(match.group(1))
    next_year_name = f"{start_year + 1}-{start_year + 2}学年"

    next_year = db.query_one(
        "SELECT year_id, year_name FROM school_year WHERE year_name = ?",
        (next_year_name,)
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
            "SELECT * FROM school_year WHERE year_id = ?",
            (from_year_id,)
        )
        to_year = db.query_one(
            "SELECT * FROM school_year WHERE year_id = ?",
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
    - 当前结转配置参数
    """
    with get_moral_db() as db:
        # 获取结转配置
        config = get_carryover_config(db)
        CARRYOVER_FACTOR = config['carryover_factor']
        MAX_CARRYOVER_TIMES = config['max_carryover_times']

        # 获取下一个学年
        next_year = get_next_school_year(db, year_id)
        if not next_year:
            return {
                "success": True,
                "data": {
                    "has_next_year": False,
                    "message": "未找到下一学年，无法结转",
                    "config": config
                }
            }

        # 查询待结转任务（仅在校学生）
        unfinished_tasks = db.query_all(
            """SELECT stf.id, stf.student_id, stf.task_id, stf.carryover_count,
               stf.current_score, stf.status,
               t.task_name, t.score as original_task_score, t.can_carryover,
               s.name as student_name, c.class_name
            FROM student_task_finish stf
            JOIN grade_moral_task t ON stf.task_id = t.task_id
            JOIN student s ON stf.student_id = s.student_id
            JOIN class c ON s.class_id = c.class_id
            WHERE stf.year_id = ?
            AND stf.status = 0
            AND t.can_carryover = 1
            AND t.is_active = 1
            AND s.status = '在校'""",
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
                "config": config,
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
            conditions.append("tcl.student_id = ?")
            params.append(student_id)

        if year_id:
            conditions.append("tcl.from_year_id = ? OR tcl.to_year_id = ?")
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
            LIMIT ? OFFSET ?
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


@router.get("/config", summary="获取结转配置")
async def api_get_carryover_config(
    user: User = Depends(require_permission('semester_manage'))
):
    """
    获取结转配置参数

    返回：
    - carryover_factor: 结转系数（0-1）
    - max_carryover_times: 最大结转次数
    """
    with get_moral_db() as db:
        config = get_carryover_config(db)
        return {
            "success": True,
            "data": config
        }


class CarryoverConfigUpdate(BaseModel):
    """更新结转配置"""
    carryover_factor: float = Field(..., ge=0, le=1, description="结转系数（0-1）")
    max_carryover_times: int = Field(..., ge=1, le=5, description="最大结转次数（1-5）")


@router.put("/config", summary="更新结转配置")
async def api_update_carryover_config(
    config: CarryoverConfigUpdate,
    req: Request,
    user: User = Depends(require_permission('semester_manage'))
):
    """
    更新结转配置参数

    权限要求：xuefa/admin

    参数：
    - carryover_factor: 结转系数（例如 0.6 表示每次结转分值衰减为60%）
    - max_carryover_times: 最大结转次数（例如 2 表示最多结转2次）
    """
    with get_moral_db() as db:
        save_carryover_config(db, config.carryover_factor, config.max_carryover_times)

        log_operation(
            db, user.username, user.role, 'UPDATE', 'moral_config', None,
            new_data={
                'config_key': 'carryover_config',
                'carryover_factor': config.carryover_factor,
                'max_carryover_times': config.max_carryover_times
            },
            ip_address=req.client.host if req.client else None
        )

        return {
            "success": True,
            "message": "结转配置已更新",
            "data": {
                "carryover_factor": config.carryover_factor,
                "max_carryover_times": config.max_carryover_times
            }
        }