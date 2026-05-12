# -*- coding: utf-8 -*-
"""
微信token鉴权模块

提供：
- 微信API token验证
- 微信身份提取和解析
- 微信通道权限检查（复用member.py的等级+模块逻辑）
"""

import logging
import json
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException

try:
    from config.config import Config
except Exception:
    Config = None

logger = logging.getLogger(__name__)


def get_wechat_api_token() -> str:
    """获取微信API token配置"""
    if Config is None:
        return ""
    try:
        token = Config().get_config("wechat_api_token", "wechat.yaml")
        return token or ""
    except Exception:
        return ""


def verify_wechat_token(request: Request) -> Optional[str]:
    """
    验证微信API token

    支持两种方式：
    1. Header: X-Wechat-Token
    2. Query参数: wechat_token

    Args:
        request: FastAPI请求对象

    Returns:
        str: 验证成功返回 "wechat_verified"，失败返回 None
    """
    expected_token = get_wechat_api_token()
    if not expected_token:
        logger.warning("微信API token未配置，跳过验证")
        return None

    # 方式1：Header中携带
    token = request.headers.get("X-Wechat-Token")

    # 方式2：Query参数携带
    if not token:
        token = request.query_params.get("wechat_token")

    if token and token == expected_token:
        return "wechat_verified"

    return None


def get_wechat_identity(request: Request) -> Optional[Dict[str, Any]]:
    """
    从微信请求中提取身份信息

    流程：
    1. 验证微信token
    2. 提取wxid
    3. 查询teacher表获取用户信息

    Args:
        request: FastAPI请求对象

    Returns:
        Dict: 包含身份信息的字典，失败返回 None
    """
    verified = verify_wechat_token(request)
    if not verified:
        return None

    # 从请求中提取wxid
    wxid = request.headers.get("X-Wxid") or request.query_params.get("wxid")

    if not wxid:
        logger.warning("微信请求缺少wxid标识")
        return {"identity_type": "wechat", "wxid": None, "level": 0, "model": ""}

    # 查询teacher表获取用户信息
    try:
        from .moral.base import get_moral_db

        with get_moral_db() as db:
            teacher = db.query_one(
                "SELECT teacher_id, name, level, model, role FROM teacher WHERE wxid = ? AND is_active = 1",
                (wxid,)
            )

            if teacher:
                return {
                    "identity_type": "wechat",
                    "wxid": wxid,
                    "teacher_id": teacher.get("teacher_id"),
                    "name": teacher.get("name"),
                    "level": int(teacher.get("level") or 0),
                    "model": teacher.get("model") or "",
                    "roles": parse_roles_from_teacher(teacher)
                }
    except Exception as e:
        logger.warning(f"查询teacher表失败: {e}")

    # 未在teacher表中找到，返回基础身份
    return {
        "identity_type": "wechat",
        "wxid": wxid,
        "level": 0,
        "model": ""
    }


def parse_roles_from_teacher(teacher: Dict) -> list:
    """从teacher记录中解析角色列表"""
    role = teacher.get("role") or ""
    return [r for r in str(role).split("/") if r]


def check_wechat_permission(wechat_identity: Dict, config: Dict) -> Dict[str, Any]:
    """
    微信通道权限检查

    复用 member.py 的 check_permission 装饰器逻辑：
    1. 检查等级 (level)
    2. 检查模块 (module)

    Args:
        wechat_identity: 微信身份信息
        config: API权限配置

    Returns:
        Dict: {allowed: bool, reason: str}
    """
    if not wechat_identity:
        return {"allowed": False, "reason": "微信身份未识别"}

    # 公开API直接放行
    if int(config.get("is_public") or 0) == 1:
        return {"allowed": True, "reason": "公开API无需鉴权"}

    user_level = wechat_identity.get("level", 0)
    required_level = int(config.get("min_level") or 0)

    # 检查等级
    if user_level < required_level:
        return {"allowed": False, "reason": f"等级不足: {user_level} < {required_level}"}

    # 检查角色（如果配置中有allowed_roles）
    allowed_roles_raw = config.get("allowed_roles") or "[]"
    try:
        allowed_roles = json.loads(allowed_roles_raw) if isinstance(allowed_roles_raw, str) else allowed_roles_raw
    except Exception:
        allowed_roles = []

    if allowed_roles:
        user_roles = wechat_identity.get("roles") or []
        # admin 角色拥有所有权限
        if "admin" in user_roles:
            return {"allowed": True, "reason": "admin拥有所有权限"}

        # 检查角色匹配
        if not any(role in allowed_roles for role in user_roles):
            return {"allowed": False, "reason": f"角色不允许: {user_roles} vs {allowed_roles}"}

    # 检查模块（如果配置中指定了module_id）
    # 注意：微信通道的模块检查需要额外实现，这里暂时跳过
    # 后续可通过扩展 api_permission_config 表添加 module 字段

    return {"allowed": True, "reason": "微信鉴权通过"}


def require_wechat_token():
    """
    FastAPI依赖：仅微信token鉴权

    用于 auth_mode='wechat_token' 的API
    """
    async def check(request: Request):
        identity = get_wechat_identity(request)
        if not identity:
            raise HTTPException(status_code=401, detail="微信token无效")

        # 验证wxid存在
        if not identity.get("wxid"):
            raise HTTPException(status_code=401, detail="微信身份未识别")

        return identity

    return check


def require_jwt_or_wechat():
    """
    FastAPI依赖：JWT或微信token双通道鉴权

    用于 auth_mode='both' 的API
    """
    async def check(request: Request):
        # 优先尝试JWT
        try:
            from .auth import get_current_user_optional
            authorization = request.headers.get("Authorization", "")
            scheme, _, token = authorization.partition(" ")
            bearer_token = token if scheme.lower() == "bearer" and token else None
            user = await get_current_user_optional(bearer_token)
            if user:
                return {"identity_type": "jwt", "user": user}
        except Exception:
            pass

        # 尝试微信token
        identity = get_wechat_identity(request)
        if identity and identity.get("wxid"):
            return identity

        raise HTTPException(status_code=401, detail="JWT或微信token认证失败")

    return check


__all__ = [
    'verify_wechat_token',
    'get_wechat_identity',
    'check_wechat_permission',
    'require_wechat_token',
    'require_jwt_or_wechat',
]
