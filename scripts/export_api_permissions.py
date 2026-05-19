#!/usr/bin/env python3
"""
API权限配置导出脚本
将数据库 api_permission_config 表导出为 YAML 配置文件

用法:
    python scripts/export_api_permissions.py

输出:
    lesson/config/api_permissions.yaml
"""

import sqlite3
import json
import yaml
import sys
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
DB_FILE = PROJECT_ROOT / "lesson" / "databases" / "moral.db"
OUTPUT_FILE = PROJECT_ROOT / "lesson" / "config" / "api_permissions.yaml"


def export_permissions():
    """导出权限配置到 YAML 文件"""
    if not DB_FILE.exists():
        print(f"数据库不存在: {DB_FILE}")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT api_path, api_name, api_group, allowed_roles, min_level,
               http_method, match_type, policy_mode, is_public, enforce_backend,
               resource_type, action_type
        FROM api_permission_config
        WHERE is_active = 1
        ORDER BY api_path
    """)

    rows = cursor.fetchall()
    conn.close()

    permissions = []
    for row in rows:
        item = {
            "api_path": row["api_path"],
            "api_name": row["api_name"] or "",
            "api_group": row["api_group"] or "",
            "allowed_roles": json.loads(row["allowed_roles"]) if row["allowed_roles"] else [],
            "min_level": row["min_level"] or 0,
        }
        # 只保留非默认值
        if row["http_method"] and row["http_method"] != "*":
            item["http_method"] = row["http_method"]
        if row["match_type"] and row["match_type"] != "exact":
            item["match_type"] = row["match_type"]
        if row["policy_mode"] and row["policy_mode"] != "role_and_level":
            item["policy_mode"] = row["policy_mode"]
        if row["is_public"]:
            item["is_public"] = row["is_public"]
        if row["enforce_backend"] != 1:
            item["enforce_backend"] = row["enforce_backend"]
        if row["resource_type"]:
            item["resource_type"] = row["resource_type"]
        if row["action_type"]:
            item["action_type"] = row["action_type"]

        permissions.append(item)

    # 写入 YAML 文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(permissions, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"导出完成: {OUTPUT_FILE}")
    print(f"共导出 {len(permissions)} 个 API 配置")


if __name__ == "__main__":
    print(f"数据库: {DB_FILE}")
    print(f"输出: {OUTPUT_FILE}")
    print()
    export_permissions()