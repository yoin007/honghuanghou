# -*- coding: utf-8 -*-
"""
班主任代申请撤销处分 API

提供班主任代学生申请撤销处分的管理功能
"""

import logging
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    check_moral_permission_for_roles,
    get_current_semester,
    get_student_class_snapshot,
    log_operation,
    get_api_scoped_user_roles,
    get_record_data_scope,
    append_record_scope_condition,
    record_in_scope,
    target_student_in_scope,
)
from .api_permission import require_configured_api_permission
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/punishment-revoke-applications", tags=["处分撤销申请"])

# API 路径常量
API_REVOKE_APPLY_CREATE = "/api/moral/punishment-revoke-applications/create"
API_REVOKE_APPLY_LIST = "/api/moral/punishment-revoke-applications"
API_REVOKE_APPROVE = "/api/moral/punishment-revoke-applications/approve"
API_REVOKE_REJECT = "/api/moral/punishment-revoke-applications/reject"


def _revoke_application_view_scope(db, user: User, api_path: str) -> dict:
    """获取申请查看范围"""
    return get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=['punishment_revoke_approve'],
        own_class_permissions=['punishment_revoke_apply'],
        own_permissions=[],
    )


# =============================================================================
# Pydantic 模型
# =============================================================================

class RevokeApplicationCreate(BaseModel):
    """班主任代学生提交撤销申请"""
    punishment_id: int = Field(..., description="处分记录ID")
    student_id: str = Field(..., description="学生学号")
    apply_reason: Optional[str] = Field(None, description="申请理由")
    observation_proof: Optional[str] = Field(None, description="观察期表现证明")
    good_record_count: int = Field(0, ge=0, description="良好表现记录数")


class RevokeApprove(BaseModel):
    """管理员审批通过"""
    opinion: Optional[str] = Field(None, description="审批意见")


class RevokeReject(BaseModel):
    """管理员审批拒绝"""
    opinion: str = Field(..., description="拒绝原因")


# =============================================================================
# API 路由
# =============================================================================

@router.post("/create", summary="班主任代学生提交撤销申请")
async def create_revoke_application(
    application: RevokeApplicationCreate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_REVOKE_APPLY_CREATE, "POST", allow_missing=False))
):
    """
    班主任代学生提交撤销处分申请

    权限：班主任需要 punishment_revoke_apply 权限，仅可为本班学生申请
    """
    with get_moral_db() as db:
        # 检查处分记录是否存在且未撤销
        punishment = db.query_one(
            """SELECT p.id, p.student_id, p.punishment_date, p.level, p.expire_date,
                      p.is_revoked, p.can_apply_revoke, p.class_id, p.grade_id,
                      s.name as student_name, c.class_name
               FROM punishment_record p
               JOIN student s ON p.student_id = s.student_id
               JOIN class c ON p.class_id = c.class_id
               WHERE p.id = ?""",
            (application.punishment_id,)
        )

        if not punishment:
            raise HTTPException(status_code=404, detail="处分记录不存在")

        if punishment["is_revoked"] == 1:
            raise HTTPException(status_code=400, detail="该处分已被撤销")

        if punishment["can_apply_revoke"] == 0:
            raise HTTPException(status_code=400, detail="该处分不允许申请撤销")

        # 检查学生是否在班主任可申请范围内
        if not target_student_in_scope(db, user, application.student_id, API_REVOKE_APPLY_CREATE):
            raise HTTPException(status_code=403, detail="仅可为本班学生提交申请")

        # 检查是否已到期
        today = date.today().strftime("%Y-%m-%d")
        if punishment["expire_date"] and punishment["expire_date"] > today:
            raise HTTPException(status_code=400, detail="处分尚未到期，无法申请撤销")

        # 检查是否已有申请记录
        existing_application = db.query_one(
            "SELECT id, status FROM punishment_revoke_application WHERE punishment_id = ?",
            (application.punishment_id,)
        )

        if existing_application:
            if existing_application["status"] == 0:
                raise HTTPException(status_code=400, detail="该处分已有待审批的申请")
            elif existing_application["status"] == 1:
                raise HTTPException(status_code=400, detail="该处分申请已被通过")
            # status=2 表示被拒绝，可以重新申请

        # 创建申请记录
        apply_date = today
        applicant_type = "cleader"
        applicant_id = user.username

        db.execute(
            """INSERT INTO punishment_revoke_application
               (punishment_id, student_id, apply_date, apply_reason, observation_proof,
                good_record_count, applicant_type, applicant_id, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (application.punishment_id, application.student_id, apply_date,
             application.apply_reason, application.observation_proof,
             application.good_record_count, applicant_type, applicant_id)
        )

        application_id = db.query_value("SELECT last_insert_rowid()")

        # 更新处分记录的关联申请ID
        db.execute(
            "UPDATE punishment_record SET revoke_application_id = ? WHERE id = ?",
            (application_id, application.punishment_id)
        )

        # 记录操作日志
        log_operation(
            db, user.username, "INSERT", "punishment_revoke_application", application_id,
            new_data={
                "punishment_id": application.punishment_id,
                "student_id": application.student_id,
                "apply_reason": application.apply_reason,
                "applicant_type": applicant_type,
                "applicant_id": applicant_id
            },
            reason="班主任代学生提交撤销处分申请"
        )

        return {
            "success": True,
            "message": "撤销申请已提交，等待管理员审批",
            "data": {
                "application_id": application_id,
                "punishment_id": application.punishment_id,
                "student_id": application.student_id,
                "student_name": punishment["student_name"],
                "class_name": punishment["class_name"],
                "punishment_level": punishment["level"],
                "apply_date": apply_date,
                "status": 0
            }
        }


@router.get("", summary="获取撤销申请列表")
async def get_revoke_applications(
    status: Optional[int] = Query(None, description="申请状态: 0=待审批, 1=已通过, 2=已拒绝"),
    class_id: Optional[int] = Query(None, description="班级ID"),
    grade_id: Optional[int] = Query(None, description="年级ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_configured_api_permission(API_REVOKE_APPLY_LIST, "GET", allow_missing=False))
):
    """
    获取撤销申请列表

    权限：
    - 管理员可查看全部申请
    - 班主任仅可查看本班申请
    """
    with get_moral_db() as db:
        conditions = ["1=1"]
        params = []

        if status is not None:
            conditions.append("a.status = ?")
            params.append(status)

        if class_id:
            conditions.append("p.class_id = ?")
            params.append(class_id)

        if grade_id:
            conditions.append("p.grade_id = ?")
            params.append(grade_id)

        # 数据范围控制
        view_scope = _revoke_application_view_scope(db, user, API_REVOKE_APPLY_LIST)
        append_record_scope_condition(
            conditions,
            params,
            view_scope,
            table_alias="p",
            username=user.username,
        )

        where_clause = " AND ".join(conditions)

        # 查询总数
        total = db.query_value(
            f"""SELECT COUNT(*) FROM punishment_revoke_application a
                JOIN punishment_record p ON a.punishment_id = p.id
                WHERE {where_clause}""",
            params
        )

        # 分页查询
        offset = (page - 1) * page_size
        applications = db.query_all(
            f"""SELECT a.id, a.punishment_id, a.student_id, a.apply_date, a.apply_reason,
                       a.observation_proof, a.good_record_count, a.applicant_type, a.applicant_id,
                       a.status, a.admin_opinion, a.admin_approve_date, a.admin_id, a.created_at,
                       p.punishment_date, p.level, p.expire_date, p.score_deduct,
                       s.name as student_name, c.class_name, c.class_id, g.grade_name
                FROM punishment_revoke_application a
                JOIN punishment_record p ON a.punishment_id = p.id
                JOIN student s ON a.student_id = s.student_id
                JOIN class c ON p.class_id = c.class_id
                JOIN grade g ON p.grade_id = g.grade_id
                WHERE {where_clause}
                ORDER BY a.apply_date DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        )

        return {
            "success": True,
            "data": applications or [],
            "total": total or 0,
            "page": page,
            "page_size": page_size
        }


@router.post("/{app_id}/approve", summary="管理员审批通过")
async def approve_revoke_application(
    app_id: int,
    approve: RevokeApprove,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_REVOKE_APPROVE, "POST", allow_missing=False))
):
    """
    管理员审批通过撤销申请

    权限：需要 punishment_revoke_approve 权限
    """
    with get_moral_db() as db:
        # 检查申请是否存在且待审批
        application = db.query_one(
            """SELECT a.id, a.punishment_id, a.student_id, a.status,
                       p.level, p.score_deduct
               FROM punishment_revoke_application a
               JOIN punishment_record p ON a.punishment_id = p.id
               WHERE a.id = ?""",
            (app_id,)
        )

        if not application:
            raise HTTPException(status_code=404, detail="申请记录不存在")

        if application["status"] != 0:
            raise HTTPException(status_code=400, detail="该申请已处理，无法再次审批")

        today = date.today().strftime("%Y-%m-%d")

        # 更新申请状态
        db.execute(
            """UPDATE punishment_revoke_application
               SET status = 1, admin_opinion = ?, admin_approve_date = ?, admin_id = ?
               WHERE id = ?""",
            (approve.opinion, today, user.username, app_id)
        )

        # 撤销处分记录（revoke_type=2 表示期满申请撤销，扣分保留）
        db.execute(
            """UPDATE punishment_record
               SET is_revoked = 1, revoke_date = ?, revoke_by = ?, revoke_reason = ?, revoke_type = 2
               WHERE id = ?""",
            (today, user.username, f"期满申请撤销: {approve.opinion or '审批通过'}", application["punishment_id"])
        )

        # 记录操作日志
        log_operation(
            db, user.username, "UPDATE", "punishment_revoke_application", app_id,
            old_data={"status": 0},
            new_data={"status": 1, "admin_opinion": approve.opinion, "admin_id": user.username},
            reason="管理员审批通过撤销申请"
        )

        log_operation(
            db, user.username, "REVOKE", "punishment_record", application["punishment_id"],
            new_data={
                "revoke_type": 2,
                "revoke_reason": f"期满申请撤销: {approve.opinion or '审批通过'}"
            },
            reason="通过撤销申请后撤销处分"
        )

        return {
            "success": True,
            "message": "审批通过，处分已撤销",
            "data": {
                "application_id": app_id,
                "punishment_id": application["punishment_id"],
                "student_id": application["student_id"],
                "status": 1,
                "admin_opinion": approve.opinion,
                "admin_approve_date": today
            }
        }


@router.post("/{app_id}/reject", summary="管理员审批拒绝")
async def reject_revoke_application(
    app_id: int,
    reject: RevokeReject,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_REVOKE_REJECT, "POST", allow_missing=False))
):
    """
    管理员审批拒绝撤销申请

    权限：需要 punishment_revoke_approve 权限
    """
    with get_moral_db() as db:
        # 检查申请是否存在且待审批
        application = db.query_one(
            "SELECT id, punishment_id, student_id, status FROM punishment_revoke_application WHERE id = ?",
            (app_id,)
        )

        if not application:
            raise HTTPException(status_code=404, detail="申请记录不存在")

        if application["status"] != 0:
            raise HTTPException(status_code=400, detail="该申请已处理，无法再次审批")

        today = date.today().strftime("%Y-%m-%d")

        # 更新申请状态为拒绝
        db.execute(
            """UPDATE punishment_revoke_application
               SET status = 2, admin_opinion = ?, admin_approve_date = ?, admin_id = ?
               WHERE id = ?""",
            (reject.opinion, today, user.username, app_id)
        )

        # 清除处分记录的关联申请ID（允许重新申请）
        db.execute(
            "UPDATE punishment_record SET revoke_application_id = NULL WHERE id = ?",
            (application["punishment_id"])
        )

        # 记录操作日志
        log_operation(
            db, user.username, "UPDATE", "punishment_revoke_application", app_id,
            old_data={"status": 0},
            new_data={"status": 2, "admin_opinion": reject.opinion, "admin_id": user.username},
            reason=f"管理员拒绝撤销申请: {reject.opinion}"
        )

        return {
            "success": True,
            "message": "审批拒绝",
            "data": {
                "application_id": app_id,
                "punishment_id": application["punishment_id"],
                "student_id": application["student_id"],
                "status": 2,
                "admin_opinion": reject.opinion,
                "admin_approve_date": today
            }
        }