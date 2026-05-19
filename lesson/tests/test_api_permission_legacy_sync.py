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
