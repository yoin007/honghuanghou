#!/usr/bin/env python3
"""
API权限配置导入脚本
将 api_permissions.yaml 导入到数据库 api_permission_config 表

用法:
    python scripts/import_api_permissions.py [--dry-run]

参数:
    --dry-run: 仅预览变更，不实际执行
"""

import argparse
import json
import sqlite3
import sys
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
CONFIG_FILE = PROJECT_ROOT / "lesson" / "config" / "api_permissions.yaml"
DB_FILE = PROJECT_ROOT / "lesson" / "databases" / "moral.db"


def load_yaml_config():
    """加载YAML配置文件"""
    import yaml
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def import_permissions(dry_run=False):
    """导入权限配置到数据库"""
    permissions = load_yaml_config()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    inserted = 0
    updated = 0
    skipped = 0

    for config in permissions:
        api_path = config["api_path"]

        # 检查是否存在
        cursor.execute("SELECT id FROM api_permission_config WHERE api_path = ?", (api_path,))
        existing = cursor.fetchone()

        allowed_roles = json.dumps(config.get("allowed_roles", []))
        min_level = config.get("min_level", 0)
        http_method = config.get("http_method", "*")
        match_type = config.get("match_type", "exact")
        policy_mode = config.get("policy_mode", "role_and_level")
        is_public = config.get("is_public", 0)
        enforce_backend = config.get("enforce_backend", 1)
        resource_type = config.get("resource_type", "")
        action_type = config.get("action_type", "")

        if existing:
            # 更新已存在的记录
            sql = """
                UPDATE api_permission_config SET
                    api_name = ?,
                    api_group = ?,
                    allowed_roles = ?,
                    min_level = ?,
                    http_method = ?,
                    match_type = ?,
                    policy_mode = ?,
                    is_public = ?,
                    enforce_backend = ?,
                    resource_type = ?,
                    action_type = ?,
                    updated_at = datetime('now', 'localtime')
                WHERE api_path = ?
            """
            params = (
                config.get("api_name", ""),
                config.get("api_group", ""),
                allowed_roles,
                min_level,
                http_method,
                match_type,
                policy_mode,
                is_public,
                enforce_backend,
                resource_type,
                action_type,
                api_path
            )
            if not dry_run:
                cursor.execute(sql, params)
            updated += 1
            print(f"[UPDATE] {api_path}")
        else:
            # 插入新记录
            sql = """
                INSERT INTO api_permission_config (
                    api_path, api_name, api_group, allowed_roles, min_level,
                    http_method, match_type, policy_mode, is_active, is_public,
                    enforce_backend, resource_type, action_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """
            params = (
                api_path,
                config.get("api_name", ""),
                config.get("api_group", ""),
                allowed_roles,
                min_level,
                http_method,
                match_type,
                policy_mode,
                is_public,
                enforce_backend,
                resource_type,
                action_type
            )
            if not dry_run:
                cursor.execute(sql, params)
            inserted += 1
            print(f"[INSERT] {api_path}")

    if not dry_run:
        conn.commit()

    conn.close()

    print(f"\n导入完成: 新增 {inserted} 条, 更新 {updated} 条")
    if dry_run:
        print("(dry-run模式，未实际执行)")


def main():
    parser = argparse.ArgumentParser(description="导入API权限配置")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不执行")
    args = parser.parse_args()

    if not CONFIG_FILE.exists():
        print(f"配置文件不存在: {CONFIG_FILE}")
        sys.exit(1)

    if not DB_FILE.exists():
        print(f"数据库不存在: {DB_FILE}")
        sys.exit(1)

    print(f"配置文件: {CONFIG_FILE}")
    print(f"数据库: {DB_FILE}")
    print()

    import_permissions(dry_run=args.dry_run)


if __name__ == "__main__":
    main()