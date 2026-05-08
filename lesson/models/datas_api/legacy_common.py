# -*- coding: utf-8 -*-
"""Shared helpers for legacy API modules.

Batch72: 权限检查函数统一迁移。
"""

import os
import jwt
import logging
from fastapi import HTTPException, Request
from config.config import Config

logger = logging.getLogger(__name__)

# JWT 配置（从 datas_api_legacy.py 迁移）
config = Config()
try:
    config_data = config.get_config("auth", "token.yaml")
except Exception as e:
    logger.warning(f"Failed to load token.yaml config: {e}")
    config_data = {}

SECRET_KEY = os.getenv("JWT_SECRET_KEY") or config_data.get("jwt_secret")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is not set! Please set it in .env or system environment.")

ALGORITHM = "HS256"


# ============================================================
# 路由匹配与权限规则（Batch72 从 datas_api_legacy.py 迁移）
# ============================================================

def _match_route(path: str, pattern: str) -> bool:
    """匹配路由模式，支持 {param} 通配符"""
    path_parts = [p for p in path.strip("/").split("/") if p != ""]
    pattern_parts = [p for p in pattern.strip("/").split("/") if p != ""]
    if len(path_parts) != len(pattern_parts):
        return False
    for pp, tp in zip(path_parts, pattern_parts):
        if tp.startswith("{") and tp.endswith("}"):
            continue
        if pp != tp:
            return False
    return True


def _get_api_rule(path: str):
    """基于 api_level.yaml 获取路由权限规则"""
    # 兼容带有 /api 前缀的路由
    norm_path = path
    if norm_path.startswith("/api/"):
        norm_path = norm_path[4:]
    cfg_all = Config().get_config_all("api_level.yaml")
    defaults = cfg_all.get("defaults", {})
    routes = cfg_all.get("routes", {})
    for patt, conf in routes.items():
        if _match_route(norm_path, patt):
            merged = dict(defaults)
            merged.update(conf or {})
            return merged
    return defaults


async def check_api_permission(request: Request):
    """检查 API 权限（基于 YAML 规则 + JWT）"""
    rule = _get_api_rule(request.url.path)
    allowed_roles = rule.get("allowed_roles", [])
    min_level = int(rule.get("min_level", 0))

    # 无限制：允许所有访问
    if "all" in allowed_roles and min_level == 0:
        return

    # JWT 不要求：直接返回
    jwt_required = rule.get("jwt_required", True)
    if not jwt_required:
        return

    # JWT 验证
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

    roles = user.get("role", "").split('/')
    level = int(user.get("level") or 0)

    if allowed_roles and not any(role in allowed_roles for role in roles):
        raise HTTPException(status_code=403, detail="Forbidden: role not allowed")
    if level < min_level:
        raise HTTPException(status_code=403, detail="Forbidden: level too low")
    return


async def check_legacy_api_permission(request: Request):
    """Alias used by older legacy modules and tests."""
    return await check_api_permission(request)
