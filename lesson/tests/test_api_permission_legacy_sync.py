# -*- coding: utf-8 -*-
"""api_permissions.yaml 默认权限配置回归测试。"""

from models.datas_api.moral.api_permission import _load_api_permissions_from_yaml


def _permission_map():
    return {item["api_path"]: item for item in _load_api_permissions_from_yaml()}


def test_default_permissions_loaded_from_api_permissions_yaml():
    permissions = _load_api_permissions_from_yaml()

    assert len(permissions) >= 200
    assert all("api_path" in item for item in permissions)


def test_vehicle_permission_default_is_protected_system_api():
    config = _permission_map()["/api/vehicle-inout/{counts}"]

    assert config["allowed_roles"] == ["admin"]
    assert config["min_level"] == 100
    assert config.get("is_public", 0) in (0, None)
    assert config["match_type"] == "pattern"
    assert config["resource_type"] == "legacy_system_admin"


def test_public_legacy_delay_defaults_are_explicit():
    configs = _permission_map()

    for api_path in ["/api/insert_delay/", "/api/delay_infos/{classCode}", "/api/student_info/"]:
        config = configs[api_path]
        assert config["policy_mode"] == "public"
        assert config["is_public"] == 1
        assert config["enforce_backend"] == 0


def test_mentor_system_yaml_entries_exist():
    """导师制 12 个接口已落 yaml，角色与资源类型正确。"""
    configs = _permission_map()
    mentor_paths = [path for path in configs if "/mentor-" in path]

    expected = {
        "/api/moral/mentor-roster",
        "/api/moral/mentor-roster/assign",
        "/api/moral/mentor-roster/batch",
        "/api/moral/mentor-roster/delete",
        "/api/moral/mentor-roster/template",
        "/api/moral/mentor-roster/my-students",
        "/api/moral/mentor-talks",
        "/api/moral/mentor-talks/create",
        "/api/moral/mentor-talks/update",
        "/api/moral/mentor-talks/delete",
        "/api/moral/mentor-talks/statistics",
        "/api/moral/mentor-talks/not-talked",
    }
    assert expected.issubset(set(mentor_paths))
    for path in expected:
        config = configs[path]
        assert config["resource_type"] == "mentor_record"
        assert config["enforce_backend"] == 1
        assert config["match_type"] == "exact"


def test_merge_mentor_scope_rules_is_additive_and_idempotent():
    """老库 timeline 规则追加 teacher: mentor_students，重复执行不重复追加。"""
    import json
    import sqlite3

    from models.datas_api.moral.api_permission import _merge_mentor_scope_rules

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE api_permission_config (id INTEGER PRIMARY KEY, api_path TEXT, data_scope_rules TEXT, allowed_roles TEXT, min_level INTEGER)"
    )
    existing_rules = {"admin": ["all"], "g_leader": ["managed_grades"]}
    conn.execute(
        "INSERT INTO api_permission_config (api_path, data_scope_rules) VALUES (?, ?)",
        ("/api/moral/timeline", json.dumps(existing_rules)),
    )
    # 名单/统计的 allowed_roles 修正目标行
    conn.execute(
        "INSERT INTO api_permission_config (api_path, allowed_roles) VALUES (?, ?)",
        ("/api/moral/mentor-roster", json.dumps(["admin", "jiaowu", "xuefa", "g_leader", "teacher"])),
    )
    conn.execute(
        "INSERT INTO api_permission_config (api_path, allowed_roles, min_level) VALUES (?, ?, ?)",
        ("/api/moral/mentor-talks/statistics", json.dumps(["admin", "jiaowu", "xuefa", "g_leader"]), 30),
    )

    db = type("DB", (), {
        "query_one": lambda self, sql, params=None: dict(
            conn.execute(sql, params or ()).fetchone() or {}
        ) or None,
        "query_all": lambda self, sql, params=None: [],
        "execute": lambda self, sql, params=None: conn.execute(sql, params or ()),
    })()

    _merge_mentor_scope_rules(db)
    row = conn.execute("SELECT data_scope_rules FROM api_permission_config").fetchone()
    rules = json.loads(row["data_scope_rules"])
    assert rules["teacher"] == ["mentor_students"]
    assert rules["admin"] == ["all"]  # 已有角色不受影响

    # allowed_roles 修正：roster 移除 teacher，statistics 追加 teacher
    roster_roles = json.loads(conn.execute(
        "SELECT allowed_roles FROM api_permission_config WHERE api_path = '/api/moral/mentor-roster'"
    ).fetchone()["allowed_roles"])
    assert "teacher" not in roster_roles
    stats_row = conn.execute(
        "SELECT allowed_roles, min_level FROM api_permission_config WHERE api_path = '/api/moral/mentor-talks/statistics'"
    ).fetchone()
    assert "teacher" in json.loads(stats_row["allowed_roles"])
    assert stats_row["min_level"] == 10  # min_level 随 teacher 开放降为教师等级

    # 幂等：重复执行不产生重复 token / 重复角色
    _merge_mentor_scope_rules(db)
    rules = json.loads(
        conn.execute("SELECT data_scope_rules FROM api_permission_config WHERE api_path = '/api/moral/timeline'").fetchone()["data_scope_rules"]
    )
    assert rules["teacher"].count("mentor_students") == 1
    roster_roles = json.loads(conn.execute(
        "SELECT allowed_roles FROM api_permission_config WHERE api_path = '/api/moral/mentor-roster'"
    ).fetchone()["allowed_roles"])
    assert roster_roles.count("teacher") == 0
    stats_roles = json.loads(conn.execute(
        "SELECT allowed_roles FROM api_permission_config WHERE api_path = '/api/moral/mentor-talks/statistics'"
    ).fetchone()["allowed_roles"])
    assert stats_roles.count("teacher") == 1
