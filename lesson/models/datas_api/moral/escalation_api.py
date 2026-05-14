# -*- coding: utf-8 -*-
"""
累进规则管理 API

提供累进规则的配置和管理功能
"""

import logging
import json
from datetime import date
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .api_permission import require_configured_api_permission
from .base import (
    get_moral_db,
    get_current_semester,
    log_operation,
    get_record_data_scope,
    record_in_scope,
    )
from .escalation import (
    get_student_escalation_history,
    get_student_event_count_in_window,
    get_next_threshold_info,
    check_and_trigger_escalation,
)
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/escalation-rules", tags=["累进规则管理"])

API_ESCALATION_STUDENT_HISTORY = "/api/moral/escalation-rules/student/{student_id}/history"
API_ESCALATION_STUDENT_COUNT = "/api/moral/escalation-rules/student/{student_id}/count"
API_ESCALATION_STUDENT_PROGRESS = "/api/moral/escalation-rules/student/{student_id}/progress"


def _ensure_student_escalation_access(db, user: User, student_id: str, api_path: str) -> None:
    student = db.query_one(
        "SELECT student_id, class_id, grade_id FROM student WHERE student_id = ?",
        (student_id,),
    )
    if not student:
        raise HTTPException(404, "学生不存在")

    scope = get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=["report_view_all"],
        own_class_permissions=["report_view_own_class"],
        own_permissions=[],
    )
    if not record_in_scope(student, scope, username=user.username, recorder_field="student_id"):
        raise HTTPException(403, "无权查看该学生的累进信息")


# =============================================================================
# Pydantic 模型
# =============================================================================

class EscalationRuleItem(BaseModel):
    """单个处罚阶梯"""
    threshold: int = Field(..., description="次数阈值", ge=1)
    action: str = Field(..., description="触发类型: warning/criticism/demerit/serious_demerit")
    description: str = Field(..., description="处罚描述")
    notify_roles: List[str] = Field(["cleader"], description="通知角色")
    score_penalty: int = Field(0, description="额外扣分")


class EscalationRuleCreate(BaseModel):
    """创建累进规则"""
    event_id: int = Field(..., description="违纪事件类型ID")
    time_window_days: int = Field(90, description="统计时间窗口（天）", ge=1, le=365)
    rules: List[EscalationRuleItem] = Field(..., description="处罚阶梯列表")


class EscalationRuleUpdate(BaseModel):
    """更新累进规则"""
    time_window_days: Optional[int] = Field(None, description="时间窗口", ge=1, le=365)
    rules: Optional[List[EscalationRuleItem]] = Field(None, description="处罚阶梯列表")


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="获取累进规则列表")
async def get_escalation_rules(
    event_id: Optional[int] = Query(None, description="事件ID"),
    user: User = Depends(require_configured_api_permission("/api/moral/escalation-rules", "GET", allow_missing=False))
):
    """获取累进规则列表"""
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if event_id:
            conditions.append("ver.event_id = ?")
            params.append(event_id)

        query = f"""
            SELECT ver.*, de.event_name, de.event_type
            FROM violation_escalation_rule ver
            JOIN daily_event_type de ON ver.event_id = de.event_id
            WHERE {' AND '.join(conditions)}
            ORDER BY ver.event_id
        """

        rules = db.query_all(query, tuple(params) if params else None)

        # 解析JSON规则
        result_list = []
        for rule in rules or []:
            rule_dict = dict(rule)
            try:
                rule_dict['rules_parsed'] = json.loads(rule_dict['escalation_rules'])
            except:
                rule_dict['rules_parsed'] = {'rules': []}
            result_list.append(rule_dict)

        return {"success": True, "data": result_list}


@router.post("", summary="创建累进规则")
async def create_escalation_rule(
    rule_data: EscalationRuleCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission("/api/moral/escalation-rules", "GET", allow_missing=False))
):
    """创建累进规则"""
    with get_moral_db() as db:
        # 检查事件是否存在且为消极类型
        event = db.query_one(
            "SELECT * FROM daily_event_type WHERE event_id = ?",
            (rule_data.event_id,)
        )
        if not event:
            raise HTTPException(404, "事件类型不存在")
        if event['event_type'] != 2:
            raise HTTPException(400, "只能为消极事件配置累进规则")

        # 检查是否已存在规则
        existing = db.query_one(
            "SELECT rule_id FROM violation_escalation_rule WHERE event_id = ?",
            (rule_data.event_id,)
        )
        if existing:
            raise HTTPException(400, "该事件已有累进规则，请使用更新接口")

        # 构建规则JSON
        rules_json = {
            "rules": [r.dict() for r in rule_data.rules],
            "reset_on_action": False
        }

        db.execute(
            """INSERT INTO violation_escalation_rule
            (event_id, time_window_days, escalation_rules)
            VALUES (?, ?, ?)""",
            (rule_data.event_id, rule_data.time_window_days, json.dumps(rules_json))
        )

        rule_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'violation_escalation_rule',
            rule_id, new_data={'event_id': rule_data.event_id, 'time_window_days': rule_data.time_window_days},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "累进规则创建成功", "data": {"rule_id": rule_id}}


@router.put("/{rule_id}", summary="更新累进规则")
async def update_escalation_rule(
    rule_id: int,
    update_data: EscalationRuleUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission("/api/moral/escalation-rules", "GET", allow_missing=False))
):
    """更新累进规则"""
    with get_moral_db() as db:
        old_rule = db.query_one(
            "SELECT * FROM violation_escalation_rule WHERE rule_id = ?",
            (rule_id,)
        )
        if not old_rule:
            raise HTTPException(404, "规则不存在")

        updates = []
        params = []

        if update_data.time_window_days is not None:
            updates.append("time_window_days = ?")
            params.append(update_data.time_window_days)

        if update_data.rules is not None:
            rules_json = {
                "rules": [r.dict() for r in update_data.rules],
                "reset_on_action": False
            }
            updates.append("escalation_rules = ?")
            params.append(json.dumps(rules_json))

        if not updates:
            return {"success": True, "message": "无更新内容"}

        params.append(rule_id)
        db.execute(
            f"UPDATE violation_escalation_rule SET {', '.join(updates)} WHERE rule_id = ?",
            tuple(params)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'violation_escalation_rule',
            rule_id, old_data={'event_id': old_rule['event_id']},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "累进规则更新成功"}


@router.delete("/{rule_id}", summary="删除累进规则")
async def delete_escalation_rule(
    rule_id: int,
    request: Request,
    user: User = Depends(require_configured_api_permission("/api/moral/escalation-rules", "GET", allow_missing=False))
):
    """删除累进规则"""
    with get_moral_db() as db:
        old_rule = db.query_one(
            "SELECT * FROM violation_escalation_rule WHERE rule_id = ?",
            (rule_id,)
        )
        if not old_rule:
            raise HTTPException(404, "规则不存在")

        db.execute(
            "DELETE FROM violation_escalation_rule WHERE rule_id = ?",
            (rule_id,)
        )

        log_operation(
            db, user.username, user.role, 'DELETE', 'violation_escalation_rule',
            rule_id, old_data={'event_id': old_rule['event_id']},
            ip_address=request.client.host if request.client else None
        )

        return {"success": True, "message": "累进规则已删除"}


@router.get("/student/{student_id}/history", summary="获取学生累进处罚历史")
async def get_escalation_history(
    student_id: str,
    semester_id: Optional[int] = Query(None),
    user: User = Depends(require_configured_api_permission(API_ESCALATION_STUDENT_HISTORY, "GET", allow_missing=False))
):
    """获取学生累进处罚历史"""
    with get_moral_db() as db:
        _ensure_student_escalation_access(db, user, student_id, API_ESCALATION_STUDENT_HISTORY)
        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        history = get_student_escalation_history(db, student_id, semester_id)

        return {"success": True, "data": history}


@router.get("/student/{student_id}/count", summary="获取学生事件累计次数")
async def get_event_count(
    student_id: str,
    event_id: int = Query(..., description="事件ID"),
    time_window_days: int = Query(90, description="时间窗口"),
    user: User = Depends(require_configured_api_permission(API_ESCALATION_STUDENT_COUNT, "GET", allow_missing=False))
):
    """获取学生在时间窗口内某事件的累计次数"""
    with get_moral_db() as db:
        _ensure_student_escalation_access(db, user, student_id, API_ESCALATION_STUDENT_COUNT)
        count = get_student_event_count_in_window(
            db, student_id, event_id, date.today(), time_window_days
        )

        # 获取下一阈值信息
        next_info = get_next_threshold_info(
            db, student_id, event_id, date.today()
        )

        return {
            "success": True,
            "data": {
                "current_count": count,
                "time_window_days": time_window_days,
                "next_threshold": next_info.get('next_threshold'),
                "next_action": next_info.get('next_action'),
                "remaining": next_info.get('remaining'),
                "progress_percent": next_info.get('progress_percent')
            }
        }


@router.get("/student/{student_id}/progress", summary="获取学生所有消极事件累计进度")
async def get_student_all_progress(
    student_id: str,
    user: User = Depends(require_configured_api_permission(API_ESCALATION_STUDENT_PROGRESS, "GET", allow_missing=False))
):
    """获取学生所有消极事件的累计进度"""
    with get_moral_db() as db:
        _ensure_student_escalation_access(db, user, student_id, API_ESCALATION_STUDENT_PROGRESS)
        # 获取所有消极事件类型
        negative_events = db.query_all(
            """SELECT de.event_id, de.event_name, de.score
            FROM daily_event_type de
            WHERE de.event_type = 2 AND de.is_active = 1
            ORDER BY de.event_id"""
        )

        progress_list = []
        for event in negative_events or []:
            next_info = get_next_threshold_info(
                db, student_id, event['event_id'], date.today()
            )

            if next_info.get('has_rule'):
                progress_list.append({
                    'event_id': event['event_id'],
                    'event_name': event['event_name'],
                    'current_count': next_info['current_count'],
                    'time_window_days': next_info['time_window_days'],
                    'next_threshold': next_info['next_threshold'],
                    'next_action': next_info['next_action'],
                    'remaining': next_info['remaining'],
                    'progress_percent': next_info['progress_percent']
                })

        return {"success": True, "data": progress_list}


@router.get("/events", summary="获取可配置累进规则的消极事件列表")
async def get_configurable_events(
    user: User = Depends(require_configured_api_permission("/api/moral/escalation-rules", "GET", allow_missing=False))
):
    """获取可配置累进规则的消极事件列表"""
    with get_moral_db() as db:
        events = db.query_all(
            """SELECT de.event_id, de.event_name, de.score, de.description,
            CASE WHEN ver.rule_id IS NOT NULL THEN 1 ELSE 0 END as has_rule
            FROM daily_event_type de
            LEFT JOIN violation_escalation_rule ver ON de.event_id = ver.event_id
            WHERE de.event_type = 2 AND de.is_active = 1
            ORDER BY de.event_id"""
        )

        return {"success": True, "data": events or []}
