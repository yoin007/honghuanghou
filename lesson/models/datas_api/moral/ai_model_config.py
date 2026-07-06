# -*- coding: utf-8 -*-
"""
大模型配置管理 API

功能：统一管理各模块的大模型调用配置
"""

import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .api_permission import require_configured_api_permission
from .base import get_moral_db, require_permission
from models.datas_api.auth import User, get_current_user

router = APIRouter(prefix="/ai-model-config", tags=["大模型配置"])
logger = logging.getLogger(__name__)

API_AI_CONFIG = "/api/moral/ai-model-config"


# =============================================================================
# 可用模型列表
# =============================================================================

AVAILABLE_MODELS = {
    "千问": [
        {"name": "qwen3.6-plus", "capabilities": ["文本生成", "深度思考", "视觉理解"]},
        {"name": "qwen3.5-plus", "capabilities": ["文本生成", "深度思考", "视觉理解"]},
        {"name": "qwen3-max-2026-01-23", "capabilities": ["文本生成", "深度思考"]},
        {"name": "qwen3-coder-next", "capabilities": ["文本生成"]},
        {"name": "qwen3-coder-plus", "capabilities": ["文本生成"]},
    ],
    "智谱": [
        {"name": "glm-4.7-flash", "capabilities": ["文本生成", "快速响应"]},
        {"name": "glm-4.7", "capabilities": ["文本生成", "深度思考"]},
        {"name": "glm-5", "capabilities": ["文本生成", "深度思考"]},
    ],
    "Kimi": [
        {"name": "kimi-k2.5", "capabilities": ["文本生成", "深度思考", "视觉理解"]},
    ],
    "MiniMax": [
        {"name": "MiniMax-M2.5", "capabilities": ["文本生成", "深度思考"]},
    ],
    "DeepSeek": [
        {"name": "deepseek-v4-pro", "capabilities": ["文本生成", "深度思考", "视觉理解"]},
        {"name": "deepseek-v4-flash", "capabilities": ["文本生成", "快速响应"]},
    ],
}


# =============================================================================
# Pydantic 模型
# =============================================================================

class ModelConfigUpdate(BaseModel):
    current_model: str = Field(..., description="新的模型名称")


class ModelConfigResponse(BaseModel):
    module_name: str
    display_name: str
    current_model: str
    description: Optional[str]
    updated_at: Optional[str]
    updated_by: Optional[str]


# =============================================================================
# API 路由
# =============================================================================

@router.get("/list", summary="获取所有配置")
async def get_all_configs(
    user: User = Depends(require_configured_api_permission(API_AI_CONFIG, allow_missing=False))
):
    """获取所有模块的大模型配置"""
    with get_moral_db() as db:
        configs = db.query_all(
            "SELECT module_name, display_name, current_model, description, updated_at, updated_by FROM ai_model_config ORDER BY module_name"
        )
        return {"success": True, "data": configs}


@router.get("/models", summary="获取可用模型列表")
async def get_available_models(
    user: User = Depends(require_configured_api_permission(API_AI_CONFIG, allow_missing=False))
):
    """获取所有可用的大模型列表"""
    return {"success": True, "data": AVAILABLE_MODELS}


@router.put("/{module_name}", summary="更新模块模型配置")
async def update_model_config(
    module_name: str,
    update: ModelConfigUpdate,
    user: User = Depends(require_configured_api_permission(API_AI_CONFIG, allow_missing=False))
):
    """更新指定模块的大模型配置"""
    # 验证模型名称是否在可用列表中
    all_models = []
    for vendor_models in AVAILABLE_MODELS.values():
        all_models.extend([m["name"] for m in vendor_models])

    if update.current_model not in all_models:
        raise HTTPException(400, f"模型 {update.current_model} 不在可用列表中")

    with get_moral_db() as db:
        # 检查模块是否存在
        existing = db.query_one(
            "SELECT module_name FROM ai_model_config WHERE module_name = ?",
            (module_name,)
        )
        if not existing:
            raise HTTPException(404, f"模块 {module_name} 不存在")

        # 更新配置
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.execute(
            "UPDATE ai_model_config SET current_model = ?, updated_at = ?, updated_by = ? WHERE module_name = ?",
            (update.current_model, now, user.username, module_name)
        )

        logger.info(f"大模型配置已更新: {module_name} → {update.current_model} (by {user.username})")

        return {"success": True, "message": f"已将 {module_name} 的模型更新为 {update.current_model}"}


@router.post("/init", summary="初始化默认配置")
async def init_default_configs(
    user: User = Depends(require_configured_api_permission(API_AI_CONFIG, allow_missing=False))
):
    """初始化默认的大模型配置（如果表为空）"""
    with get_moral_db() as db:
        count = db.query_value("SELECT COUNT(*) FROM ai_model_config")
        if count > 0:
            return {"success": True, "message": "配置已存在，无需初始化"}

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        configs = [
            ('ai_diagnosis', 'AI诊疗', 'kimi-k2.5', '学生德育问题的AI诊断分析'),
            ('profile_generate', '学生画像生成', 'kimi-k2.5', '生成学生德育画像'),
            ('remind_ai', '定时提醒', 'glm-4.7-flash', '定时提醒文本AI处理'),
            ('bailian_general', '百炼通用', 'glm-4.7-flash', '百炼平台通用AI调用'),
            ('semester_evaluation', '学期末评价生成', 'kimi-k2.5', '学期末德育评价总结生成'),
        ]
        for cfg in configs:
            db.execute(
                "INSERT INTO ai_model_config (module_name, display_name, current_model, description, updated_at) VALUES (?, ?, ?, ?, ?)",
                (cfg[0], cfg[1], cfg[2], cfg[3], now)
            )

        return {"success": True, "message": "已初始化5条默认配置"}


# =============================================================================
# 统一的模型读取函数（供其他模块调用）
# =============================================================================

def get_current_model(module_name: str, default: str = "kimi-k2.5") -> str:
    """
    从数据库读取指定模块当前配置的模型名称

    Args:
        module_name: 模块名称（ai_diagnosis, profile_generate, remind_ai, bailian_general）
        default: 默认模型名称（配置不存在或读取失败时使用）

    Returns:
        当前配置的模型名称
    """
    try:
        with get_moral_db() as db:
            config = db.query_one(
                "SELECT current_model FROM ai_model_config WHERE module_name = ?",
                (module_name,)
            )
            if config and config['current_model']:
                return config['current_model']
    except Exception as e:
        logger.warning(f"读取大模型配置失败 ({module_name}): {e}")

    return default
