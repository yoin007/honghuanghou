# -*- coding: utf-8 -*-
"""
处分管理 API

提供处分记录的管理功能
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    get_current_semester,
    get_student_class_snapshot,
    log_operation,
    check_moral_permission_for_roles,
    get_api_scoped_user_roles,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
    record_action_flags,
    target_student_in_scope,
)
from .api_permission import require_configured_api_permission
from .punishment_period import get_period_config_by_type, calculate_expire_date
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/punishments", tags=["处分管理"])

API_PUNISHMENT_LIST = "/api/moral/punishments"
API_PUNISHMENT_CREATE = "/api/moral/punishments/create"
API_PUNISHMENT_UPDATE = "/api/moral/punishments/update"
API_PUNISHMENT_REVOKE = "/api/moral/punishments/revoke"
API_PUNISHMENT_REVIEW = "/api/moral/punishments/review"

def _has_scoped_any_permission(db, user: User, api_path: str, permissions: List[str]) -> bool:
    scoped_roles = get_api_scoped_user_roles(db, user, api_path)
    return any(check_moral_permission_for_roles(scoped_roles, permission) for permission in permissions)


PUNISHMENT_ALL_PERMISSIONS = ['punishment_manage', 'report_view_all']
PUNISHMENT_OWN_CLASS_PERMISSIONS = ['moral_record_own_class', 'report_view_own_class']
PUNISHMENT_OWN_PERMISSIONS = ['moral_record_input', 'moral_record_view_own']


def _punishment_view_scope(db, user: User, api_path: str = API_PUNISHMENT_LIST) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=PUNISHMENT_ALL_PERMISSIONS,
        own_class_permissions=PUNISHMENT_OWN_CLASS_PERMISSIONS,
        own_permissions=PUNISHMENT_OWN_PERMISSIONS,
    )


def _punishment_action_scope(db, user: User, api_path: str) -> dict:
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['punishment_manage'],
        own_class_permissions=[],
        own_permissions=['moral_record_input', 'moral_record_view_own'],
    )


# =============================================================================
# Pydantic 模型
# =============================================================================

class PunishmentCreate(BaseModel):
    """创建处分记录"""
    student_id: str = Field(..., description="学号")
    punishment_type: str = Field(..., description="处分类型")
    punishment_level: int = Field(2, description="处分等级")
    punishment_date: date = Field(..., description="处分日期")
    punishment_reason: Optional[str] = Field(None, description="处分原因")
    evidence: Optional[str] = Field(None, description="证据材料")
    score_deduct: Optional[int] = Field(None, description="扣分")


class PunishmentRevoke(BaseModel):
    """撤销处分"""
    revoke_reason: str = Field(..., description="撤销原因")
    revoke_type: int = Field(2, description="撤销类型: 1=源记录错误, 2=期满申请, 3=复核误处分")


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="获取处分记录列表")
async def get_punishments(
    student_id: Optional[str] = Query(None),
    class_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    semester_id: Optional[int] = Query(None),
    is_revoked: Optional[int] = Query(None, description="是否已撤销"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=10000),
    user: User = Depends(require_configured_api_permission(API_PUNISHMENT_LIST, "GET", allow_missing=False))
):
    """
    获取处分记录列表

    权限：入口已由 require_configured_api_permission 检查。
    """
    with get_moral_db() as db:
        if not semester_id:
            current_semester = get_current_semester(db)
            semester_id = current_semester['semester_id'] if current_semester else None

        conditions = ["1=1"]
        params = []

        if student_id:
            conditions.append("p.student_id = ?")
            params.append(student_id)

        if class_id:
            conditions.append("p.class_id = ?")
            params.append(class_id)

        if grade_id:
            conditions.append("p.grade_id = ?")
            params.append(grade_id)

        if semester_id:
            conditions.append("p.semester_id = ?")
            params.append(semester_id)

        if is_revoked is not None:
            conditions.append("p.is_revoked = ?")
            params.append(is_revoked)

        view_scope = _punishment_view_scope(db, user)
        append_record_scope_condition(
            conditions,
            params,
            view_scope,
            table_alias="p",
            username=user.username,
        )

        where_clause = " AND ".join(conditions)

        count_query = f"""
            SELECT COUNT(*) FROM punishment_record p WHERE {where_clause}
        """
        total = db.query_value(count_query, tuple(params))

        offset = (page - 1) * page_size
        data_query = f"""
            SELECT p.id as record_id, p.student_id, p.punishment_date, p.score_deduct,
                   p.level as punishment_type, p.reason as punishment_reason,
                   p.is_revoked, p.revoke_date, p.revoke_reason, p.revoke_type, p.revoke_category,
                   p.review_status, p.recorder, p.expire_date, p.period_days, p.can_apply_revoke,
                   p.revoke_application_id,
                   COALESCE(de.event_name, se.event_name, '累进扣分') as trigger_event,
                   s.name as student_name, c.class_name, g.grade_name
            FROM punishment_record p
            JOIN student s ON p.student_id = s.student_id
            LEFT JOIN daily_event_type de ON p.event_id = de.event_id
            LEFT JOIN school_event_type se ON p.event_id = se.event_id
            JOIN class c ON p.class_id = c.class_id
            JOIN grade g ON p.grade_id = g.grade_id
            WHERE {where_clause}
            ORDER BY p.punishment_date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        records = db.query_all(data_query, tuple(params))
        update_scope = _punishment_action_scope(db, user, API_PUNISHMENT_UPDATE)
        revoke_scope = _punishment_action_scope(db, user, API_PUNISHMENT_REVOKE)
        for record_item in records:
            flags = record_action_flags(
                record_item,
                update_scope,
                revoke_scope,
                username=user.username,
            )
            record_item["can_edit"] = flags["can_edit"]
            record_item["can_revoke"] = flags["can_delete"]

        return {
            "success": True,
            "data": {
                "items": records,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        }


@router.post("", summary="创建处分记录")
async def create_punishment(
    punishment: PunishmentCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PUNISHMENT_CREATE, "POST", allow_missing=False))
):
    """创建处分记录"""
    with get_moral_db() as db:
        if not _has_scoped_any_permission(db, user, API_PUNISHMENT_CREATE, ['punishment_manage', 'moral_record_input']):
            raise HTTPException(403, "权限不足：需要处分录入权限")

        current_semester = get_current_semester(db)
        if not current_semester:
            raise HTTPException(400, "当前学期未配置")

        semester_id = current_semester['semester_id']

        # 获取学生班级信息
        student_info = get_student_class_snapshot(db, punishment.student_id)
        if not student_info:
            raise HTTPException(404, f"学生 {punishment.student_id} 不存在或不在校")
        if not target_student_in_scope(db, user, API_PUNISHMENT_CREATE, student_info):
            raise HTTPException(403, "不能给授权范围外的学生创建处分记录")

        # 根据处分类型名称查找或创建事件类型
        event = db.query_one(
            "SELECT * FROM school_event_type WHERE event_name = ? AND event_type = 2",
            (punishment.punishment_type,)
        )
        if not event:
            # 如果不存在，创建一个新的事件类型
            level_score_map = {1: 5, 2: 10, 3: 20, 4: 30}
            score = abs(punishment.score_deduct) if punishment.score_deduct else level_score_map.get(punishment.punishment_level, 10)
            db.execute(
                """INSERT INTO school_event_type (event_name, event_type, score, is_active)
                VALUES (?, 2, ?, 1)""",
                (punishment.punishment_type, score)
            )
            event_id = db.lastrowid()
        else:
            event_id = event['event_id']

        # 计算扣分
        level_score_map = {1: 5, 2: 10, 3: 20, 4: 30}
        score_deduct = abs(punishment.score_deduct) if punishment.score_deduct else level_score_map.get(punishment.punishment_level, 10)

        # 处分等级文本
        level_map = {1: '一级', 2: '二级', 3: '三级', 4: '四级'}
        level_text = level_map.get(punishment.punishment_level, '二级')

        # 获取处分期限配置并计算到期日期
        period_config = get_period_config_by_type(db, punishment.punishment_type)
        period_days = period_config['period_days'] if period_config else 90
        can_apply_revoke = period_config['allow_revoke_apply'] if period_config else 1
        expire_date = calculate_expire_date(str(punishment.punishment_date), period_days)

        # 插入记录
        db.execute(
            """INSERT INTO punishment_record
            (student_id, event_id, semester_id, punishment_date, class_id, grade_id,
             score_deduct, level, reason, recorder, expire_date, period_days, can_apply_revoke)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                punishment.student_id,
                event_id,
                semester_id,
                punishment.punishment_date,
                student_info['class_id'],
                student_info['grade_id'],
                score_deduct,
                level_text,
                punishment.punishment_reason,
                user.username,
                expire_date,
                period_days,
                can_apply_revoke
            )
        )

        record_id = db.lastrowid()

        log_operation(
            db, user.username, user.role, 'INSERT', 'punishment_record',
            record_id, semester_id,
            new_data={'student_id': punishment.student_id, 'reason': punishment.punishment_reason},
            ip_address=request.client.host if request.client else None
        )

        from .evaluation import calculate_evaluation
        calculate_evaluation(
            db,
            punishment.student_id,
            semester_id,
            student_info['class_id'],
            student_info['grade_id'],
        )

        return {"success": True, "message": "处分记录创建成功", "data": {"id": record_id}}


@router.put("/{record_id}", summary="更新处分记录")
async def update_punishment(
    record_id: int,
    punishment: PunishmentCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PUNISHMENT_UPDATE, "PUT", allow_missing=False))
):
    """更新处分记录"""
    with get_moral_db() as db:
        action_scope = _punishment_action_scope(db, user, API_PUNISHMENT_UPDATE)
        if not action_scope.get("can_all") and not action_scope.get("can_own"):
            raise HTTPException(403, "权限不足：需要处分记录权限")

        old_record = db.query_one(
            "SELECT * FROM punishment_record WHERE id = ?",
            (record_id,)
        )
        if not old_record:
            raise HTTPException(404, "记录不存在")
        if not record_in_scope(old_record, action_scope, username=user.username):
            raise HTTPException(403, "只能编辑授权范围内的处分记录")

        # 处分等级文本
        level_map = {1: '一级', 2: '二级', 3: '三级', 4: '四级'}
        level_text = level_map.get(punishment.punishment_level, '二级')
        level_score_map = {1: 5, 2: 10, 3: 20, 4: 30}
        score_deduct = abs(punishment.score_deduct) if punishment.score_deduct else level_score_map.get(punishment.punishment_level, 10)

        db.execute(
            """UPDATE punishment_record SET
            punishment_date = ?, level = ?, reason = ?, score_deduct = ?
            WHERE id = ?""",
            (punishment.punishment_date, level_text, punishment.punishment_reason,
             score_deduct, record_id)
        )

        log_operation(
            db, user.username, user.role, 'UPDATE', 'punishment_record',
            record_id, old_record['semester_id'],
            ip_address=request.client.host if request.client else None
        )

        from .evaluation import calculate_evaluation
        calculate_evaluation(
            db,
            old_record['student_id'],
            old_record['semester_id'],
            old_record.get('class_id'),
            old_record.get('grade_id'),
        )

        return {"success": True, "message": "处分记录更新成功"}


@router.post("/{record_id}/revoke", summary="撤销处分")
async def revoke_punishment(
    record_id: int,
    revoke_data: PunishmentRevoke,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PUNISHMENT_REVOKE, "POST", allow_missing=False))
):
    """
    撤销处分

    revoke_type 说明：
    - 1: 源记录错误撤销（归还分数）
    - 2: 期满申请撤销（不归还分数）
    - 3: 复核误处分撤销（归还分数）
    """
    from .evaluation import calculate_evaluation

    # 撤销类型对应的显示文本
    revoke_category_map = {
        1: "源记录错误撤销",
        2: "期满申请撤销",
        3: "复核误处分撤销"
    }

    with get_moral_db() as db:
        action_scope = _punishment_action_scope(db, user, API_PUNISHMENT_REVOKE)
        if not action_scope.get("can_all") and not action_scope.get("can_own"):
            raise HTTPException(403, "权限不足：需要处分撤销权限")

        old_record = db.query_one(
            "SELECT * FROM punishment_record WHERE id = ?",
            (record_id,)
        )
        if not old_record:
            raise HTTPException(404, "记录不存在")
        if not record_in_scope(old_record, action_scope, username=user.username):
            raise HTTPException(403, "只能撤销授权范围内的处分记录")

        if old_record['is_revoked'] == 1:
            raise HTTPException(400, "该处分已撤销")

        revoke_type = revoke_data.revoke_type
        revoke_category = revoke_category_map.get(revoke_type, "期满申请撤销")

        db.execute(
            """UPDATE punishment_record SET
            is_revoked = 1, revoke_date = ?, revoke_by = ?, revoke_reason = ?,
            revoke_type = ?, revoke_category = ?
            WHERE id = ?""",
            (date.today(), user.username, revoke_data.revoke_reason,
             revoke_type, revoke_category, record_id)
        )

        # 归还分数逻辑：type=1 或 type=3 时归还
        score_returned = revoke_type in [1, 3]
        if score_returned:
            calculate_evaluation(db, old_record['student_id'], old_record['semester_id'])

        log_operation(
            db, user.username, user.role, 'REVOKE', 'punishment_record',
            record_id, old_record['semester_id'],
            new_data={'revoke_reason': revoke_data.revoke_reason, 'revoke_type': revoke_type, 'score_returned': score_returned},
            ip_address=request.client.host if request.client else None
        )

        message = f"处分已撤销（{revoke_category}）"
        if score_returned:
            message += f"，扣分已归还（+{abs(old_record['score_deduct'])}分）"

        return {"success": True, "message": message, "score_returned": score_returned}


# =============================================================================
# 处分复核 API
# =============================================================================

@router.get("/{record_id}/review-info", summary="获取处分复核信息")
async def get_punishment_review_info(
    record_id: int,
    user: User = Depends(require_configured_api_permission(API_PUNISHMENT_REVIEW, "GET", allow_missing=False))
):
    """
    获取处分复核所需信息

    返回：源记录状态、累计次数、阈值等
    """
    import json
    from datetime import datetime, timedelta

    with get_moral_db() as db:
        punishment = db.query_one(
            """SELECT id, student_id, event_id, semester_id, source_record_ids, reason,
                   score_deduct, level, punishment_date, review_status
            FROM punishment_record WHERE id = ?""",
            (record_id,)
        )

        if not punishment:
            raise HTTPException(404, "处分记录不存在")

        # 解析源记录ID列表
        try:
            source_ids = json.loads(punishment['source_record_ids']) if punishment['source_record_ids'] else []
        except:
            source_ids = []

        # 获取每条源记录的状态
        source_records = []
        for sid in source_ids:
            record = db.query_one(
                """SELECT record_id, record_date, is_deleted FROM student_daily_record WHERE record_id = ?""",
                (sid,)
            )
            if record:
                source_records.append({
                    "record_id": sid,
                    "record_date": record['record_date'],
                    "is_deleted": record['is_deleted'],
                    "status": "有效" if record['is_deleted'] == 0 else "已删除"
                })

        # 获取累进规则阈值和时间窗口
        rule = db.query_one(
            """SELECT escalation_rules, time_window_days FROM violation_escalation_rule WHERE event_id = ?""",
            (punishment['event_id'],)
        )

        threshold = None
        time_window_days = 90
        if rule:
            time_window_days = rule.get('time_window_days', 90)
            try:
                rules_data = json.loads(rule['escalation_rules'])
                for r in rules_data.get('rules', []):
                    if f"累计{r['threshold']}次" in punishment['reason']:
                        threshold = r['threshold']
                        break
                    threshold = r.get('threshold')  # 取第一个阈值作为参考
            except:
                pass

        # 计算当前有效累计次数
        try:
            base_date = datetime.strptime(punishment['punishment_date'], '%Y-%m-%d').date()
        except:
            base_date = datetime.now().date()

        window_start = base_date - timedelta(days=time_window_days)

        valid_count = db.query_value(
            """SELECT COUNT(*) FROM student_daily_record
            WHERE student_id = ? AND event_id = ?
            AND strftime('%Y-%m-%d', record_date) >= ?
            AND strftime('%Y-%m-%d', record_date) <= ?
            AND is_deleted = 0""",
            (punishment['student_id'], punishment['event_id'],
             window_start.strftime('%Y-%m-%d'), base_date.strftime('%Y-%m-%d'))
        ) or 0

        # 学生信息
        student = db.query_one(
            "SELECT name FROM student WHERE student_id = ?",
            (punishment['student_id'],)
        )
        student_name = student['name'] if student else punishment['student_id']

        # 事件信息
        event = db.query_one(
            "SELECT event_name FROM daily_event_type WHERE event_id = ?",
            (punishment['event_id'],)
        )
        event_name = event['event_name'] if event else "未知事件"

        return {
            "success": True,
            "data": {
                "punishment_id": record_id,
                "student_id": punishment['student_id'],
                "student_name": student_name,
                "event_name": event_name,
                "score_deduct": punishment['score_deduct'],
                "level": punishment['level'],
                "reason": punishment['reason'],
                "punishment_date": punishment['punishment_date'],
                "review_status": punishment['review_status'],
                "threshold": threshold,
                "time_window_days": time_window_days,
                "valid_count": valid_count,
                "source_records": source_records,
                "recommendation": "撤销处分" if valid_count < threshold else "复核通过（保留处分）" if threshold else "无阈值信息"
            }
        }


class PunishmentReview(BaseModel):
    """复核决定"""
    action: str = Field(..., description="操作: revoke(撤销) 或 approve(通过)")
    reason: Optional[str] = Field(None, description="复核说明")


@router.post("/{record_id}/review", summary="复核处分")
async def review_punishment(
    record_id: int,
    review_data: PunishmentReview,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PUNISHMENT_REVIEW, "POST", allow_missing=False))
):
    """
    复核处分（撤销或通过）

    - revoke: 撤销处分，回滚扣分，重新计算评价
    - approve: 标记复核通过，处分保持有效
    """
    from .evaluation import calculate_evaluation

    with get_moral_db() as db:
        punishment = db.query_one(
            "SELECT * FROM punishment_record WHERE id = ?",
            (record_id,)
        )

        if not punishment:
            raise HTTPException(404, "处分记录不存在")

        if punishment['is_revoked'] == 1:
            raise HTTPException(400, "处分已撤销，无法复核")

        if review_data.action == "revoke":
            # 撤销处分（源记录错误，归还分数）
            db.execute(
                """UPDATE punishment_record SET
                is_revoked = 1, revoke_date = ?, revoke_by = ?, revoke_reason = ?,
                revoke_type = 1, revoke_category = '源记录错误撤销',
                review_status = 2, review_by = ?, review_time = datetime('now','localtime')
                WHERE id = ?""",
                (date.today(), user.username, review_data.reason or "复核撤销-源记录错误",
                 user.username, record_id)
            )

            # 重新计算德育评价（回滚扣分）
            calculate_evaluation(db, punishment['student_id'], punishment['semester_id'])

            log_operation(
                db, user.username, user.role, 'REVIEW_REVOKE', 'punishment_record',
                record_id, punishment['semester_id'],
                new_data={'review_reason': review_data.reason, 'revoke_type': 1, 'score_returned': True},
                ip_address=request.client.host if request.client else None
            )

            return {"success": True, "message": "处分已撤销（源记录错误），扣分已归还"}

        elif review_data.action == "approve":
            # 复核通过
            db.execute(
                """UPDATE punishment_record SET
                review_status = 2, review_by = ?, review_time = datetime('now','localtime')
                WHERE id = ?""",
                (user.username, record_id)
            )

            log_operation(
                db, user.username, user.role, 'REVIEW_APPROVE', 'punishment_record',
                record_id, punishment['semester_id'],
                new_data={'review_reason': review_data.reason},
                ip_address=request.client.host if request.client else None
            )

            return {"success": True, "message": "复核通过，处分保持有效"}

        else:
            raise HTTPException(400, "无效操作，必须是 revoke 或 approve")
