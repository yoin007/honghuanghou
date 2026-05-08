# -*- coding: utf-8 -*-
"""require_configured_api_permission 契约测试。

Batch77: 锁定权限工厂行为，验证未配置和 enforce_backend 语义。
"""

import pytest
from fastapi import HTTPException

from models.datas_api.auth import User
from models.datas_api.moral import api_permission


class FakePermissionDB:
    """模拟 api_permission_config 表"""

    def __init__(self, configs=None):
        self.configs = configs or []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def query_one(self, sql, params=None):
        if "FROM api_permission_config" in sql and "api_path" in sql:
            api_path = params[0] if params else None
            for cfg in self.configs:
                if cfg.get("api_path") == api_path:
                    return cfg
        return None


def test_require_configured_api_permission_missing_allow_true(monkeypatch):
    """未配置且 allow_missing=True → 允许已登录用户"""
    fake_db = FakePermissionDB(configs=[])
    monkeypatch.setattr(api_permission, "get_moral_db", lambda: fake_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(api_permission, "_get_matching_config", lambda db, path, method: None)

    user = User(username="teacher", role="teacher")
    decision = api_permission.check_configured_api_permission(
        user, "/api/unknown", "GET", allow_missing=True
    )

    assert decision["allowed"] is True
    assert "无权限配置，默认允许" in decision["reason"]


def test_require_configured_api_permission_missing_allow_false(monkeypatch):
    """未配置且 allow_missing=False → 拒绝"""
    fake_db = FakePermissionDB(configs=[])
    monkeypatch.setattr(api_permission, "get_moral_db", lambda: fake_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(api_permission, "_get_matching_config", lambda db, path, method: None)

    user = User(username="teacher", role="teacher")
    decision = api_permission.check_configured_api_permission(
        user, "/api/unknown", "GET", allow_missing=False
    )

    assert decision["allowed"] is False
    assert "无权限配置" in decision["reason"]


def test_require_configured_api_permission_enforce_backend_0(monkeypatch):
    """配置 enforce_backend=0 → 允许（不强制后端鉴权）"""
    config = {
        "api_path": "/api/test",
        "enforce_backend": 0,
        "allowed_roles": '["admin"]',
        "min_level": 100,
    }
    fake_db = FakePermissionDB(configs=[config])
    monkeypatch.setattr(api_permission, "get_moral_db", lambda: fake_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(
        api_permission,
        "_get_matching_config",
        lambda db, path, method: config if path == "/api/test" else None,
    )

    user = User(username="teacher", role="teacher")
    decision = api_permission.check_configured_api_permission(
        user, "/api/test", "GET", allow_missing=True
    )

    assert decision["allowed"] is True
    assert "未启用后端配置鉴权" in decision["reason"]


def test_require_configured_api_permission_enforce_backend_1_role_mismatch(monkeypatch):
    """配置 enforce_backend=1 且角色不匹配 → 拒绝"""
    config = {
        "api_path": "/api/test",
        "enforce_backend": 1,
        "allowed_roles": '["admin"]',
        "min_level": 0,
        "policy_mode": "role_and_level",
    }
    fake_db = FakePermissionDB(configs=[config])
    monkeypatch.setattr(api_permission, "get_moral_db", lambda: fake_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(
        api_permission,
        "_get_matching_config",
        lambda db, path, method: config if path == "/api/test" else None,
    )
    monkeypatch.setattr(api_permission, "get_user_roles", lambda user: [user.role])
    monkeypatch.setattr(api_permission, "get_user_role_level", lambda user: 0)

    user = User(username="teacher", role="teacher")
    decision = api_permission.check_configured_api_permission(
        user, "/api/test", "GET", allow_missing=True
    )

    assert decision["allowed"] is False


def test_require_configured_api_permission_fastapi_dep_raises_403(monkeypatch):
    """require_configured_api_permission FastAPI 依赖在权限不足时抛出 403"""
    config = {
        "api_path": "/api/test",
        "enforce_backend": 1,
        "allowed_roles": '["admin"]',
        "min_level": 100,
        "policy_mode": "role_and_level",
    }
    fake_db = FakePermissionDB(configs=[config])
    monkeypatch.setattr(api_permission, "get_moral_db", lambda: fake_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(
        api_permission,
        "_get_matching_config",
        lambda db, path, method: config if path == "/api/test" else None,
    )
    monkeypatch.setattr(api_permission, "get_user_roles", lambda user: ["teacher"])
    monkeypatch.setattr(api_permission, "get_user_role_level", lambda user: 10)

    checker = api_permission.require_configured_api_permission("/api/test", "GET")
    user = User(username="teacher", role="teacher")

    with pytest.raises(HTTPException) as exc:
        # checker 是 async 函数，需要 await
        import asyncio
        asyncio.run(checker(user))

    assert exc.value.status_code == 403