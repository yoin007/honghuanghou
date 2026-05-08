#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一鉴权体系迁移脚本

步骤：
1. 新增 g_leader 角色到 role表
2. 扩展 api_permission_config 表结构（auth_mode等字段）
3. 迁移 api_level.yaml 配置到数据库
4. 标记重叠API的 auth_mode='both'
5. 补齐前端显示字段（frontend_group等）

执行方式：
    python scripts/migrate_unified_auth.py
"""

import sys
import os
import json
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def migrate():
    logger.info("=" * 60)
    logger.info("统一鉴权体系迁移脚本")
    logger.info("=" * 60)

    # 导入依赖
    try:
        from utils.sqlite_moral_db import MoralDatabase
        from models.datas_api.moral.api_permission import ensure_api_permission_schema
        from config.config import Config
    except Exception as e:
        logger.error(f"导入依赖失败: {e}")
        return False

    with MoralDatabase() as db:
        # 步骤1: 新增 g_leader 角色
        logger.info("\n[步骤1] 新增 g_leader 角色...")
        try:
            existing = db.query_one(
                "SELECT role_id FROM role WHERE role_id = 'g_leader'"
            )
            if not existing:
                db.execute("""
                    INSERT INTO role (role_id, role_name, description)
                    VALUES ('g_leader', '年级主任', '年级管理者，管理整个年级多个班级')
                """)
                logger.info("✓ g_leader 角色已添加")
            else:
                logger.info("✓ g_leader 角色已存在，跳过")
        except Exception as e:
            logger.warning(f"role表可能不存在，跳过: {e}")

        # 步骤2: 扩展表结构
        logger.info("\n[步骤2] 扩展 api_permission_config 表结构...")
        try:
            ensure_api_permission_schema(db)
        except Exception as e:
            logger.warning(f"ensure_api_permission_schema失败: {e}")

        # 新增字段
        try:
            columns = {row['name'] for row in db.query_all("PRAGMA table_info(api_permission_config)")}
        except Exception:
            columns = set()

        new_columns = [
            ("auth_mode", "TEXT DEFAULT 'jwt'"),
            ("wechat_token_required", "INTEGER DEFAULT 0"),
            ("frontend_visible", "INTEGER DEFAULT 1"),
            ("frontend_group", "TEXT DEFAULT ''"),
            ("frontend_icon", "TEXT DEFAULT ''"),
            ("frontend_order", "INTEGER DEFAULT 0"),
            ("frontend_parent", "TEXT DEFAULT ''"),
        ]

        for col_name, col_def in new_columns:
            if col_name not in columns:
                try:
                    db.execute(f"ALTER TABLE api_permission_config ADD COLUMN {col_name} {col_def}")
                    logger.info(f"✓ 已添加字段: {col_name}")
                except Exception as e:
                    logger.warning(f"添加字段 {col_name} 失败: {e}")
            else:
                logger.info(f"✓ 字段已存在: {col_name}")

        # 步骤3: 迁移YAML配置
        logger.info("\n[步骤3] 迁移 api_level.yaml 配置...")
        try:
            yaml_rules = Config().get_config_all("api_level.yaml")
            routes = yaml_rules.get("routes", {})
            defaults = yaml_rules.get("defaults", {})
        except Exception as e:
            logger.warning(f"读取YAML配置失败: {e}")
            routes = {}
            defaults = {}

        migrated_count = 0
        for path, rule in routes.items():
            api_path = path if path.startswith("/api/") else f"/api{path}"
            rule = rule or {}

            # 推断前端分组
            frontend_group = infer_frontend_group(path)

            # 推断鉴权模式
            auth_mode = infer_auth_mode(rule)

            # 推断是否公开
            jwt_required = rule.get('jwt_required', defaults.get('jwt_required', True))
            is_public = 1 if jwt_required is False else 0

            # 推断allowed_roles
            allowed_roles = rule.get('allowed_roles', defaults.get('allowed_roles', []))
            if 'all' in allowed_roles:
                allowed_roles = [r for r in allowed_roles if r != 'all']
                is_public = 1

            # 推断min_level
            min_level = int(rule.get('min_level', defaults.get('min_level', 0)))

            try:
                existing = db.query_one(
                    "SELECT id FROM api_permission_config WHERE api_path = %s",
                    (api_path,)
                )

                if existing:
                    db.execute("""
                        UPDATE api_permission_config
                        SET frontend_group = %s,
                            frontend_visible = 1,
                            auth_mode = %s,
                            min_level = %s
                        WHERE id = %s
                    """, (frontend_group, auth_mode, min_level, existing['id']))
                else:
                    db.execute("""
                        INSERT INTO api_permission_config
                        (api_path, api_name, api_group, allowed_roles, min_level,
                         is_public, auth_mode, frontend_group, frontend_visible,
                         enforce_backend)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        api_path, infer_api_name(path), infer_group(path),
                        json.dumps(allowed_roles),
                        min_level,
                        is_public,
                        auth_mode, frontend_group, 1, 1
                    ))
                migrated_count += 1
            except Exception as e:
                logger.warning(f"迁移 {api_path} 失败: {e}")

        logger.info(f"✓ 已迁移 {migrated_count} 条YAML配置")

        # 步骤4: 标记重叠API
        logger.info("\n[步骤4] 标记重叠API的 auth_mode...")
        overlap_apis = [
            "/api/moral/daily-records/create",
            "/api/moral/moment-records/create",
            "/api/homework/",
            "/api/announcement/",
            "/api/moral/school-records/create",
            "/api/moral/collective-events/create",
        ]

        marked_count = 0
        for api_path in overlap_apis:
            try:
                db.execute("""
                    UPDATE api_permission_config
                    SET auth_mode = 'both',
                        wechat_token_required = 1
                    WHERE api_path = %s OR api_path LIKE %s
                """, (api_path, api_path + "%"))
                marked_count += 1
            except Exception as e:
                logger.warning(f"标记 {api_path} 失败: {e}")

        logger.info(f"✓ 已标记 {marked_count} 个重叠API")

        # 步骤5: 补齐德育API前端字段
        logger.info("\n[步骤5] 为德育API补齐前端显示字段...")
        try:
            moral_apis = db.query_all(
                "SELECT id, api_path, api_group FROM api_permission_config WHERE api_path LIKE '/api/moral/%'"
            )

            updated_count = 0
            for api in moral_apis:
                frontend_group = infer_moral_frontend_group(api['api_path'], api.get('api_group', ''))
                frontend_order = infer_frontend_order(api['api_path'])
                try:
                    db.execute("""
                        UPDATE api_permission_config
                        SET frontend_group = %s,
                            frontend_visible = 1,
                            frontend_order = %s
                        WHERE id = %s
                    """, (frontend_group, frontend_order, api['id']))
                    updated_count += 1
                except Exception:
                    pass

            logger.info(f"✓ 已补齐 {updated_count} 个德育API的前端字段")
        except Exception as e:
            logger.warning(f"补齐德育API字段失败: {e}")

        # 提交事务
        try:
            db.commit()
        except Exception:
            pass

    logger.info("\n" + "=" * 60)
    logger.info("迁移完成！")
    logger.info("=" * 60)

    # 输出下一步指引
    logger.info("\n下一步操作：")
    logger.info("1. 在 wechat.yaml 中配置 WECHAT_API_TOKEN 环境变量")
    logger.info("2. 重启后端服务使配置生效")
    logger.info("3. 测试微信token鉴权：curl -H 'X-Wechat-Token: your_token' http://localhost:14600/api/moral/daily-records")

    return True


def infer_frontend_group(path: str) -> str:
    """推断前端分组"""
    if '/dashboard/' in path:
        return 'dashboard'
    if '/moral/' in path:
        return 'moral'
    if '/homework' in path:
        return 'class'
    if '/schedule' in path:
        return 'schedule'
    if '/admin/' in path or '/teacher-manage' in path or '/permission' in path:
        return 'system'
    if '/leave' in path or '/delay' in path:
        return 'class'
    if '/announcement' in path:
        return 'class'
    if '/students' in path or '/class-info' in path:
        return 'class'
    if '/invigilation' in path:
        return 'jiaowu'
    return 'other'


def infer_auth_mode(rule: dict) -> str:
    """推断鉴权模式"""
    jwt_required = rule.get('jwt_required', True)
    if jwt_required is False:
        return 'both'  # 公开API允许微信调用
    return 'jwt'


def infer_api_name(path: str) -> str:
    """推断API名称"""
    parts = path.strip('/').replace('/api/', '').split('/')
    if parts:
        last = parts[-1]
        # 简化路径作为名称
        return last.replace('_', ' ').replace('-', ' ')
    return path


def infer_group(path: str) -> str:
    """推断API分组"""
    parts = path.strip('/api/').split('/')
    if parts:
        first = parts[0]
        if first in ('moral', 'homework', 'schedule', 'admin', 'students', 'teachers'):
            return first
    return 'other'


def infer_moral_frontend_group(api_path: str, api_group: str) -> str:
    """推断德育API的前端分组"""
    if 'daily' in api_path:
        return 'moral_daily'
    if 'moment' in api_path:
        return 'moral_moment'
    if 'school' in api_path:
        return 'moral_school'
    if 'punishment' in api_path:
        return 'moral_punishment'
    if 'collective' in api_path:
        return 'moral_collective'
    if 'task' in api_path:
        return 'moral_task'
    if 'profile' in api_path:
        return 'moral_profile'
    if 'evaluation' in api_path:
        return 'moral_evaluation'
    if 'birthday' in api_path:
        return 'moral_birthday'
    if 'timeline' in api_path or 'lifebook' in api_path:
        return 'moral_lifebook'
    if 'admin' in api_path or 'config' in api_path:
        return 'moral_config'
    return 'moral'


def infer_frontend_order(api_path: str) -> int:
    """推断前端显示顺序"""
    if 'create' in api_path or 'add' in api_path:
        return 10
    if 'update' in api_path or 'edit' in api_path:
        return 20
    if 'delete' in api_path or 'remove' in api_path:
        return 30
    if 'batch' in api_path or 'import' in api_path:
        return 40
    return 50


if __name__ == "__main__":
    migrate()