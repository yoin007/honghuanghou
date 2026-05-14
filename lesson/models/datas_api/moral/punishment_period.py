# -*- coding: utf-8 -*-
"""
处分期限配置 API

提供处分期限配置的管理功能
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .base import (
    get_moral_db,
    check_moral_permission,
    log_operation,
)
from .api_permission import require_configured_api_permission
from models.datas_api.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/punishment-periods", tags=["处分期限配置"])

API_PERIOD_LIST = "/api/moral/punishment-periods"
API_PERIOD_UPDATE = "/api/moral/punishment-periods/update"


# =============================================================================
# Pydantic 模型
# =============================================================================

class PunishmentPeriodUpdate(BaseModel):
    """更新处分期限配置"""
    period_days: int = Field(..., ge=1, description="期限天数")
    period_description: Optional[str] = Field(None, description="期限描述")
    allow_revoke_apply: int = Field(1, ge=0, le=1, description="是否允许申请撤销")
    min_good_records: int = Field(0, ge=0, description="申请所需最少良好表现记录数")
    is_active: int = Field(1, ge=0, le=1, description="是否启用")


# =============================================================================
# API 路由
# =============================================================================

@router.get("", summary="获取处分期限配置列表")
async def get_punishment_periods(
    user: User = Depends(require_configured_api_permission(API_PERIOD_LIST, "GET", allow_missing=False))
):
    """
    获取处分期限配置列表

    权限：需要 punishment_period_config 权限
    """
    with get_moral_db() as db:
        periods = db.query_all(
            """SELECT id, punishment_type, period_days, period_description,
                      allow_revoke_apply, min_good_records, is_active, created_at
               FROM punishment_period_config
               ORDER BY period_days ASC"""
        )

        return {
            "success": True,
            "data": periods or [],
            "total": len(periods) if periods else 0
        }


@router.put("/{config_id}", summary="更新处分期限配置")
async def update_punishment_period(
    config_id: int,
    config: PunishmentPeriodUpdate,
    request: Request,
    user: User = Depends(require_configured_api_permission(API_PERIOD_UPDATE, "PUT", allow_missing=False))
):
    """
    更新处分期限配置

    权限：需要 punishment_period_config 权限
    """
    with get_moral_db() as db:
        # 检查配置是否存在
        existing = db.query_one(
            "SELECT id, punishment_type, period_days FROM punishment_period_config WHERE id = ?",
            (config_id,)
        )

        if not existing:
            raise HTTPException(status_code=404, detail="处分期限配置不存在")

        old_data = existing

        # 更新配置
        db.execute(
            """UPDATE punishment_period_config
               SET period_days = ?, period_description = ?, allow_revoke_apply = ?,
                   min_good_records = ?, is_active = ?
               WHERE id = ?""",
            (config.period_days, config.period_description, config.allow_revoke_apply,
             config.min_good_records, config.is_active, config_id)
        )

        # 记录操作日志
        log_operation(
            db, user.username, "UPDATE", "punishment_period_config", config_id,
            old_data=old_data,
            new_data=config.dict(),
            reason="更新处分期限配置"
        )

        return {
            "success": True,
            "message": "处分期限配置已更新",
            "data": {
                "id": config_id,
                "punishment_type": existing["punishment_type"],
                "period_days": config.period_days,
                "period_description": config.period_description,
                "allow_revoke_apply": config.allow_revoke_apply,
                "min_good_records": config.min_good_records,
                "is_active": config.is_active
            }
        }


# =============================================================================
# 辅助函数
# =============================================================================

def get_period_config_by_type(db, punishment_type: str) -> Optional[dict]:
    """
    根据处分类型获取期限配置

    Args:
        db: 数据库连接
        punishment_type: 处分类型名称

    Returns:
        期限配置字典，如果不存在返回 None
    """
    return db.query_one(
        """SELECT id, punishment_type, period_days, period_description,
                  allow_revoke_apply, min_good_records
           FROM punishment_period_config
           WHERE punishment_type = ? AND is_active = 1""",
        (punishment_type,)
    )


def calculate_expire_date(punishment_date: str, period_days: int) -> str:
    """
    计算到期日期

    Args:
        punishment_date: 处分日期字符串 (YYYY-MM-DD)
        period_days: 期限天数

    Returns:
        到期日期字符串
    """
    from datetime import datetime, timedelta

    date_obj = datetime.strptime(punishment_date, "%Y-%m-%d")
    expire_date_obj = date_obj + timedelta(days=period_days)
    return expire_date_obj.strftime("%Y-%m-%d")