# -*- coding: utf-8 -*-
"""Shared dashboard contract-test scaffolding."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def stub_dashboard_permission_db_for_dashboard_contracts(request, monkeypatch):
    """Keep dashboard contract tests focused on route behavior, not the real permission DB."""
    file_name = Path(str(request.fspath)).name
    if not file_name.startswith("test_dashboard"):
        return

    from models.datas_api import dashboard

    allowed_roles_by_path = {
        dashboard.API_DASHBOARD_OVERVIEW: {"admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"},
        dashboard.API_DASHBOARD_MORAL_SUMMARY: {"admin", "jiaowu", "xuefa", "g_leader", "cleader"},
        dashboard.API_DASHBOARD_TEACHING_SUMMARY: {"admin", "jiaowu"},
        dashboard.API_DASHBOARD_CLASS_SUMMARY: {"admin", "jiaowu", "xuefa", "cleader"},
        dashboard.API_DASHBOARD_GRADE_LIST: {"admin", "jiaowu", "xuefa", "g_leader"},
        dashboard.API_DASHBOARD_GRADE_SUMMARY: {"admin", "jiaowu", "xuefa", "g_leader"},
        dashboard.API_DASHBOARD_TEACHER_WORKBENCH: {"admin", "xuefa", "g_leader", "cleader", "teacher"},
        dashboard.API_DASHBOARD_INVIGILATION_SUMMARY: {"admin", "jiaowu"},
        dashboard.API_DASHBOARD_SYSTEM_SUMMARY: {"admin"},
    }

    def fake_dashboard_permission(user, api_path, http_method="GET", *, allow_missing=False):
        allowed_roles = allowed_roles_by_path.get(api_path)
        if allowed_roles is None:
            return {"allowed": True, "reason": "测试未限制", "policy": {}, "config": None}

        user_roles = {
            role.strip()
            for role in str(getattr(user, "role", "") or "").split("/")
            if role.strip()
        }
        allowed = bool(user_roles & allowed_roles)
        return {
            "allowed": allowed,
            "reason": "允许" if allowed else "测试权限拒绝",
            "policy": {},
            "config": {"api_path": api_path},
        }

    monkeypatch.setattr(dashboard, "check_configured_api_permission", fake_dashboard_permission)
