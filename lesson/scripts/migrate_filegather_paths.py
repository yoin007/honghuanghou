#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库路径迁移脚本

功能：
1. 将 filegather.files 表中的绝对路径转换为相对路径
2. 更新 moral_config 表的配置项
"""

import os
import re
import sqlite3

# 数据库路径
FILEGATHER_DB = "databases/filegather.db"
MORAL_DB = "databases/moral.db"


def get_filegather_db_path():
    """获取 filegather 数据库完整路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, FILEGATHER_DB)


def get_moral_db_path():
    """获取 moral 数据库完整路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, MORAL_DB)


def convert_to_relative_path(abs_path: str) -> str:
    """
    将绝对路径转换为相对路径

    识别 uploads 或 done 目录，提取相对部分

    Args:
        abs_path: 绝对路径（Windows 或 macOS 格式）

    Returns:
        相对路径（uploads/YYYYMM/xxx 或 done/YYYYMM/xxx）
    """
    # 统一使用正斜杠
    normalized = abs_path.replace("\\", "/")

    # 查找 uploads 或 done 目录
    match = re.search(r"(uploads|done)/(\d{6})/([^/]+)$", normalized)
    if match:
        subdir = match.group(1)  # uploads 或 done
        month = match.group(2)   # YYYYMM
        filename = match.group(3)  # 文件名
        return os.path.join(subdir, month, filename)

    # 如果无法匹配，保留原路径（可能已经是相对路径）
    return abs_path


def migrate_file_paths():
    """迁移 filegather.files 表中的路径"""
    db_path = get_filegather_db_path()

    if not os.path.exists(db_path):
        print(f"数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 获取所有文件记录
    cursor.execute("SELECT id, stored_path FROM files")
    rows = cursor.fetchall()

    updated_count = 0
    for row in rows:
        file_id = row[0]
        stored_path = row[1]

        if stored_path:
            relative_path = convert_to_relative_path(stored_path)

            # 只更新需要变化的路径
            if relative_path != stored_path:
                cursor.execute(
                    "UPDATE files SET stored_path = ? WHERE id = ?",
                    (relative_path, file_id)
                )
                updated_count += 1
                print(f"ID {file_id}: {stored_path} -> {relative_path}")

    conn.commit()
    conn.close()
    print(f"\n已更新 {updated_count} 条记录")


def migrate_config():
    """迁移 moral_config 表的配置项"""
    db_path = get_moral_db_path()

    if not os.path.exists(db_path):
        print(f"数据库不存在: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 删除旧配置项
    cursor.execute("DELETE FROM moral_config WHERE config_key = 'filegather_upload_dir'")
    cursor.execute("DELETE FROM moral_config WHERE config_key = 'filegather_done_dir'")
    print("已删除旧配置项: filegather_upload_dir, filegather_done_dir")

    # 添加新配置项（使用默认路径）
    default_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "storage", "filegather"
    )

    cursor.execute(
        "INSERT OR REPLACE INTO moral_config (config_key, config_value) VALUES (?, ?)",
        ("filegather_storage_dir", default_path)
    )
    print(f"已添加新配置项: filegather_storage_dir = {default_path}")

    conn.commit()
    conn.close()


def main():
    print("=" * 60)
    print("FileGather 路径迁移脚本")
    print("=" * 60)
    print()

    print("步骤 1: 迁移文件路径...")
    migrate_file_paths()
    print()

    print("步骤 2: 迁移配置项...")
    migrate_config()
    print()

    print("=" * 60)
    print("迁移完成")
    print("=" * 60)


if __name__ == "__main__":
    main()