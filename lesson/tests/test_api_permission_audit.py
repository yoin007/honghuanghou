# -*- coding: utf-8 -*-
"""API 权限配置巡检测试。"""

from models.datas_api.moral.api_permission import _build_permission_audit
from models.datas_api.moral.api_permission import _permission_risk_flags


def test_build_permission_audit_groups_risks():
    report = _build_permission_audit(
        [
            {
                "id": 1,
                "module_id": 7,
                "api_name": "学生趋势",
                "api_path": "/api/dashboard/score-trend/student/{student_id}",
                "api_group": "驾驶舱",
                "http_method": "GET",
                "match_type": "exact",
                "enforce_backend": 1,
                "is_public": 0,
                "data_scope_rules": "{}",
                "target_scope_rules": "{}",
                "operation_scope_rules": "{}",
            },
            {
                "id": 2,
                "api_name": "更新日常记录",
                "api_path": "/api/moral/daily-records/update",
                "api_group": "日常表现",
                "http_method": "PUT",
                "match_type": "exact",
                "enforce_backend": 0,
                "is_public": 0,
                "allowed_roles": '["admin", "xuefa"]',
                "data_scope_rules": '{"teacher": ["own_created"]}',
                "target_scope_rules": "{}",
                "operation_scope_rules": '{"admin": ["all"]}',
            },
        ]
    )

    assert report["summary"] == {"total": 2, "risky": 2, "healthy": 0}
    risk_counts = {item["label"]: item["count"] for item in report["risk_counts"]}
    assert risk_counts["动态路径建议使用参数模式"] == 1
    assert risk_counts["查看动作未配置数据范围"] == 1
    assert risk_counts["未参与后端统一鉴权"] == 1
    assert risk_counts["数据范围存在未授权角色：teacher"] == 1
    assert risk_counts["允许角色缺少对应范围：xuefa"] == 1
    assert len(report["items"]) == 2
    assert report["items"][0]["module_id"] == 7


def test_expected_public_token_is_not_reported_as_risk():
    risks = _permission_risk_flags(
        {
            "api_path": "/api/token",
            "is_public": 1,
            "enforce_backend": 1,
            "allowed_roles": [],
            "data_scope_rules": {},
            "target_scope_rules": {},
            "operation_scope_rules": {},
        }
    )

    assert "公开接口" not in risks
