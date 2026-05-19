# -*- coding: utf-8 -*-
"""Shared helpers for legacy API modules.

Batch72: 权限检查函数统一迁移。
Batch73: 改用数据库权限配置（api_permissions.yaml）。
"""

import os
import jwt
import json
import logging
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)

# JWT 配置（从 datas_api_legacy.py 迁移）
try:
    from config.config import Config
    config = Config()
    config_data = config.get_config("auth", "token.yaml")
except Exception as e:
    logger.warning(f"Failed to load token.yaml config: {e}")
    config_data = {}

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or config_data.get("jwt_secret")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is not set! Please set it in .env or system environment.")

ALGORITHM = "HS256"


def _match_route(path: str, pattern: str) -> bool:
    """兼容旧入口的参数路由匹配。"""
    path_parts = [p for p in path.strip("/").split("/") if p]
    pattern_parts = [p for p in pattern.strip("/").split("/") if p]
    if len(path_parts) != len(pattern_parts):
        return False
    return all(pp == tp or (tp.startswith("{") and tp.endswith("}")) for pp, tp in zip(path_parts, pattern_parts))


def _get_api_rule(path: str):
    """兼容旧入口：从数据库返回简化权限规则。"""
    from models.datas_api.moral.api_permission import _get_matching_config
    from models.datas_api.moral.base import get_moral_db

    with get_moral_db() as db:
        config = _get_matching_config(db, path, "*")
    if not config:
        return {"allowed_roles": [], "min_level": 0, "jwt_required": True}
    try:
        allowed_roles = json.loads(config.get("allowed_roles") or "[]")
    except Exception:
        allowed_roles = []
    return {
        "allowed_roles": allowed_roles,
        "min_level": config.get("min_level") or 0,
        "jwt_required": not bool(config.get("is_public")),
    }


async def check_api_permission(request: Request):
    """检查 API 权限（统一读取数据库 api_permission_config）。"""
    from models.datas_api.auth import User
    from models.datas_api.moral.api_permission import check_configured_api_permission

    api_path = request.url.path
    http_method = request.method

    public_decision = check_configured_api_permission(
        None,
        api_path,
        http_method,
        allow_missing=False,
    )
    if public_decision.get("allowed"):
        return

    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # 延迟导入避免循环依赖
    from models.datas_api_legacy import get_users_dict
    users_data = get_users_dict()
    user = users_data.get(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    decision = check_configured_api_permission(
        User(username=username, role=str(user.get("role") or "")),
        api_path,
        http_method,
        allow_missing=False,
    )
    if not decision.get("allowed"):
        raise HTTPException(status_code=403, detail=decision.get("reason") or "Forbidden")
    return


async def check_legacy_api_permission(request: Request):
    """Alias used by older legacy modules and tests."""
    return await check_api_permission(request)
