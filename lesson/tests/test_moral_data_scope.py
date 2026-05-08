# -*- coding: utf-8 -*-
"""德育数据范围权限测试。"""

import json
import os
import sys
from contextlib import contextmanager
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import HTTPException, Request

from models.datas_api.auth import User
from models.datas_api.auth import is_admin_user
from models.datas_api.moral import api_permission
from models.datas_api.moral.base import (
    append_record_scope_condition,
    get_record_data_scope,
    record_action_flags,
    record_in_scope,
    target_student_in_scope,
)


def _mock_request():
    """创建用于测试的 mock Request 对象"""
    mock = MagicMock(spec=Request)
    mock.headers = {}
    mock.query_params = {}
    return mock


def test_teacher_xuefa_is_not_admin_role():
    user = User(username="苏子腾", role="teacher/xuefa")

    assert is_admin_user(user) is False


def test_api_policy_rejects_multi_role_when_level_is_too_low(monkeypatch):
    monkeypatch.setattr(api_permission, "get_user_role_level", lambda user: 5)
    user = User(username="苏子腾", role="teacher/xuefa")
    config = {
        "allowed_roles": json.dumps(["admin", "xuefa"], ensure_ascii=False),
        "min_level": 20,
        "policy_mode": "role_and_level",
        "is_public": 0,
        "inherit_from_module": 0,
    }

    decision = api_permission.is_api_allowed(user, config)

    assert decision["allowed"] is False
    assert "最低等级=20" in decision["reason"]


@contextmanager
def fake_permission_db():
    yield object()


@pytest.mark.asyncio
async def test_unified_api_permission_allows_public_yaml_without_user(monkeypatch):
    """数据库无配置时，YAML 公开规则不应强制登录。"""
    monkeypatch.setattr(api_permission, "get_moral_db", fake_permission_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(api_permission, "_get_matching_config", lambda db, path, method: None)
    monkeypatch.setattr(
        api_permission,
        "_get_yaml_rule",
        lambda path: {"allowed_roles": ["all"], "min_level": 0, "jwt_required": True},
    )

    checker = api_permission.unified_api_permission("/api/public")
    request = _mock_request()

    assert await checker(request, None) is None


@pytest.mark.asyncio
async def test_unified_api_permission_rejects_private_yaml_without_user(monkeypatch):
    """数据库无配置时，YAML 私有规则应拒绝未登录访问。"""
    monkeypatch.setattr(api_permission, "get_moral_db", fake_permission_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(api_permission, "_get_matching_config", lambda db, path, method: None)
    monkeypatch.setattr(
        api_permission,
        "_get_yaml_rule",
        lambda path: {"allowed_roles": ["xuefa"], "min_level": 0, "jwt_required": True},
    )

    checker = api_permission.unified_api_permission("/api/private")
    request = _mock_request()

    with pytest.raises(HTTPException) as exc:
        await checker(request, None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_unified_api_permission_allows_matching_yaml_role(monkeypatch):
    """数据库无配置时，YAML fallback 应按角色和等级放行。"""
    monkeypatch.setattr(api_permission, "get_moral_db", fake_permission_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(api_permission, "_get_matching_config", lambda db, path, method: None)
    monkeypatch.setattr(
        api_permission,
        "_get_yaml_rule",
        lambda path: {"allowed_roles": ["xuefa"], "min_level": 20, "jwt_required": True},
    )
    monkeypatch.setattr(api_permission, "get_user_role_level", lambda user: 50)
    user = User(username="苏子腾", role="teacher/xuefa")

    checker = api_permission.unified_api_permission("/api/private")
    request = _mock_request()

    assert await checker(request, user) is user


@pytest.mark.asyncio
async def test_unified_api_permission_allows_public_db_config_without_user(monkeypatch):
    """数据库配置为公开接口时，不应强制登录。"""
    monkeypatch.setattr(api_permission, "get_moral_db", fake_permission_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(
        api_permission,
        "_get_matching_config",
        lambda db, path, method: {"is_public": 1, "allowed_roles": "[]", "min_level": 0, "policy_mode": "role_and_level"},
    )

    checker = api_permission.unified_api_permission("/api/db-public")
    request = _mock_request()

    assert await checker(request, None) is None


@pytest.mark.asyncio
async def test_unified_api_permission_rejects_private_db_config_without_user(monkeypatch):
    """数据库私有配置应拒绝未登录访问。"""
    monkeypatch.setattr(api_permission, "get_moral_db", fake_permission_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(
        api_permission,
        "_get_matching_config",
        lambda db, path, method: {"is_public": 0, "allowed_roles": "[\"xuefa\"]", "min_level": 0, "policy_mode": "role_and_level"},
    )

    checker = api_permission.unified_api_permission("/api/db-private")
    request = _mock_request()

    with pytest.raises(HTTPException) as exc:
        await checker(request, None)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_unified_api_permission_rejects_db_role_mismatch(monkeypatch):
    """数据库私有配置应按角色和等级策略拒绝不匹配用户。"""
    monkeypatch.setattr(api_permission, "get_moral_db", fake_permission_db)
    monkeypatch.setattr(api_permission, "ensure_api_permission_schema", lambda db: None)
    monkeypatch.setattr(
        api_permission,
        "_get_matching_config",
        lambda db, path, method: {
            "is_public": 0,
            "allowed_roles": "[\"xuefa\"]",
            "min_level": 0,
            "policy_mode": "role_and_level",
            "inherit_from_module": 0,
        },
    )
    user = User(username="普通教师", role="teacher")

    checker = api_permission.unified_api_permission("/api/db-private")
    request = _mock_request()

    with pytest.raises(HTTPException) as exc:
        await checker(request, user)
    assert exc.value.status_code == 403


class FakeScopeDB:
    def __init__(
        self,
        api_roles=None,
        class_id=101,
        data_scope_rules=None,
        target_scope_rules=None,
        teaching_class_ids=None,
    ):
        self.api_roles = api_roles or {}
        self.class_id = class_id
        self.data_scope_rules = data_scope_rules or {}
        self.target_scope_rules = target_scope_rules or {}
        self.teaching_class_ids = teaching_class_ids or []

    def query_one(self, sql, params=None):
        if "FROM api_permission_config" in sql:
            api_path = params[0]
            if "data_scope_rules" in sql:
                return {"data_scope_rules": json.dumps(self.data_scope_rules.get(api_path, {}), ensure_ascii=False)}
            if "target_scope_rules" in sql:
                return {"target_scope_rules": json.dumps(self.target_scope_rules.get(api_path, {}), ensure_ascii=False)}
            roles = self.api_roles.get(api_path, [])
            return {
                "allowed_roles": json.dumps(roles, ensure_ascii=False),
                "inherit_from_module": 0,
                "is_public": 0,
                "module_allowed_roles": None,
            }
        if "sqlite_master" in sql and "teacher_teaching_class" in sql:
            return {"name": "teacher_teaching_class"} if self.teaching_class_ids else None
        if "SELECT name FROM teacher" in sql:
            return {"name": "王老师"}
        if "SELECT class_id FROM class WHERE leader_name" in sql:
            return {"class_id": self.class_id}
        if "SELECT class_id FROM class WHERE leader_wxid" in sql:
            return None
        return None

    def query_all(self, sql, params=None):
        if "FROM teacher_teaching_class" in sql:
            return [{"class_id": class_id} for class_id in self.teaching_class_ids]
        return []


def test_teacher_multi_role_is_narrowed_to_api_allowed_role():
    db = FakeScopeDB(api_roles={"/api/moral/daily-records": ["teacher"]})
    user = User(username="liyuanlu", role="teacher/jiaowu")

    scope = get_record_data_scope(
        db,
        user,
        "/api/moral/daily-records",
        all_permissions=["moral_record_manage", "report_view_all"],
        own_class_permissions=["moral_record_own_class", "report_view_own_class"],
        own_permissions=["moral_record_input", "moral_record_view_own"],
    )

    assert scope["can_all"] is False
    assert scope["can_own_class"] is False
    assert scope["can_own"] is True
    assert record_in_scope({"recorder": "liyuanlu", "class_id": 999}, scope, username="liyuanlu")
    assert not record_in_scope({"recorder": "other", "class_id": 999}, scope, username="liyuanlu")


def test_class_teacher_can_view_own_class_records_but_edit_only_own_records():
    user = User(username="cleader1", role="cleader")
    db = FakeScopeDB(api_roles={
        "/api/moral/daily-records": ["cleader"],
        "/api/moral/daily-records/update": ["cleader"],
    }, class_id=101)

    view_scope = get_record_data_scope(
        db,
        user,
        "/api/moral/daily-records",
        all_permissions=["moral_record_manage", "report_view_all"],
        own_class_permissions=["moral_record_own_class", "report_view_own_class"],
        own_permissions=["moral_record_input", "moral_record_view_own"],
    )
    edit_scope = get_record_data_scope(
        db,
        user,
        "/api/moral/daily-records/update",
        all_permissions=["moral_record_manage"],
        own_class_permissions=[],
        own_permissions=["moral_record_input", "moral_record_view_own"],
    )

    classmate_record = {"recorder": "other", "class_id": 101}
    own_record = {"recorder": "cleader1", "class_id": 999}

    assert record_in_scope(classmate_record, view_scope, username="cleader1")
    assert record_in_scope(own_record, view_scope, username="cleader1")
    assert not record_in_scope(classmate_record, edit_scope, username="cleader1")
    assert record_in_scope(own_record, edit_scope, username="cleader1")


def test_record_scope_sql_and_row_action_flags_are_consistent():
    db = FakeScopeDB(api_roles={"/api/moral/moment-records": ["cleader"]}, class_id=101)
    user = User(username="cleader1", role="cleader")
    scope = get_record_data_scope(
        db,
        user,
        "/api/moral/moment-records",
        all_permissions=["moment_view_all", "moral_record_manage", "report_view_all"],
        own_class_permissions=["moral_record_own_class", "report_view_own_class"],
        own_permissions=["moment_create", "moment_view_own"],
    )

    conditions = ["mr.is_private = 1"]
    params = []
    append_record_scope_condition(conditions, params, scope, table_alias="mr", username=user.username)

    assert conditions[-1] == "(mr.recorder = %s OR mr.class_id = %s)"
    assert params == ["cleader1", 101]

    edit_scope = {
        "can_all": False,
        "can_own": True,
        "can_own_class": False,
        "my_class_id": None,
    }
    flags = record_action_flags(
        {"recorder": "other", "class_id": 101},
        edit_scope,
        username="cleader1",
    )
    assert flags == {"can_edit": False, "can_delete": False}


def test_configured_scope_rules_override_permission_defaults():
    api_path = "/api/moral/daily-records"
    db = FakeScopeDB(
        api_roles={api_path: ["cleader"]},
        class_id=101,
        data_scope_rules={api_path: {"cleader": ["own_created"]}},
    )
    user = User(username="cleader1", role="cleader")

    scope = get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=["moral_record_manage"],
        own_class_permissions=["moral_record_own_class"],
        own_permissions=["moral_record_input"],
    )

    assert scope["can_own"] is True
    assert scope["can_own_class"] is False
    assert not record_in_scope({"recorder": "other", "class_id": 101}, scope, username="cleader1")


def test_target_scope_rules_can_limit_record_input_to_own_class():
    api_path = "/api/moral/daily-records/create"
    db = FakeScopeDB(
        api_roles={api_path: ["cleader"]},
        class_id=101,
        target_scope_rules={api_path: {"cleader": ["own_class"]}},
    )
    user = User(username="cleader1", role="cleader")

    assert target_student_in_scope(db, user, api_path, {"student_id": "S1", "class_id": 101})
    assert not target_student_in_scope(db, user, api_path, {"student_id": "S2", "class_id": 102})


def test_target_scope_rules_can_limit_record_input_to_teaching_classes():
    api_path = "/api/moral/daily-records/create"
    db = FakeScopeDB(
        api_roles={api_path: ["teacher"]},
        target_scope_rules={api_path: {"teacher": ["teaching_classes"]}},
        teaching_class_ids=[201, 202],
    )
    user = User(username="teacher1", role="teacher")

    assert target_student_in_scope(db, user, api_path, {"student_id": "S1", "class_id": 201})
    assert not target_student_in_scope(db, user, api_path, {"student_id": "S2", "class_id": 101})


def test_teaching_classes_defaults_to_all_when_no_mapping_exists():
    api_path = "/api/moral/daily-records/create"
    db = FakeScopeDB(
        api_roles={api_path: ["teacher"]},
        target_scope_rules={api_path: {"teacher": ["teaching_classes"]}},
        teaching_class_ids=[],
    )
    user = User(username="teacher1", role="teacher")

    assert target_student_in_scope(db, user, api_path, {"student_id": "S1", "class_id": 201})
    assert target_student_in_scope(db, user, api_path, {"student_id": "S2", "class_id": 101})


def test_record_teaching_classes_defaults_to_all_when_no_mapping_exists():
    api_path = "/api/moral/daily-records"
    db = FakeScopeDB(
        api_roles={api_path: ["teacher"]},
        data_scope_rules={api_path: {"teacher": ["teaching_classes"]}},
        teaching_class_ids=[],
    )
    user = User(username="teacher1", role="teacher")

    scope = get_record_data_scope(
        db,
        user,
        api_path,
        all_permissions=[],
        own_class_permissions=[],
        own_permissions=[],
    )

    assert record_in_scope({"recorder": "other", "class_id": 201}, scope, username="teacher1")
    conditions = ["dr.is_deleted = 0"]
    params = []
    append_record_scope_condition(conditions, params, scope, table_alias="dr", username="teacher1")
    assert conditions == ["dr.is_deleted = 0"]
    assert params == []
