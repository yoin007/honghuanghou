#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移脚本：将 moral-old.db 中指定表的数据迁移到 moral.db

执行逻辑：
1. 清空 moral.db 中目标表的现有数据
2. 从 moral-old.db 读取数据并插入到 moral.db
3. 记录迁移日志

用法：
    python scripts/migrate_moral_data.py
"""

import sqlite3
import os
import sys
from datetime import datetime

# 要迁移的表列表
MIGRATE_TABLES = [
    "collective_event",
    "collective_event_distribution",
    "daily_event_type",
    "moment_record",
    "moral_evaluation",
    "moral_operation_log",
    "punishment_record",
    "school_event_type",
    "school_year",
    "semester",
    "semester_carryover_config",
    "student_daily_record",
    "teacher",
    "teacher_teaching_class",
    "teacher_todo_assignee",
    "teacher_todo_group",
    "teacher_todo_group_member",
    "teacher_todo_series",
    "teacher_todo_occurrence",
    "violation_escalation_rule",
    "warning_config",
]

# 数据库路径
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "databases")
SOURCE_DB = os.path.join(DB_DIR, "moral-old.db")
TARGET_DB = os.path.join(DB_DIR, "moral.db")


def get_table_columns(conn, table_name):
    """获取表的列名列表"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return columns


def get_row_count(conn, table_name):
    """获取表的记录数"""
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def clear_table(conn, table_name):
    """清空表数据"""
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name}")
    conn.commit()
    return cursor.rowcount


def migrate_table(source_conn, target_conn, table_name):
    """迁移单个表的数据"""
    # 获取列名
    columns = get_table_columns(source_conn, table_name)
    if not columns:
        print(f"  [WARN] 表 {table_name} 在源数据库中不存在或无列信息")
        return 0

    columns_str = ", ".join(columns)
    placeholders = ", ".join(["?" for _ in columns])

    # 从源数据库读取所有数据
    source_cursor = source_conn.cursor()
    source_cursor.execute(f"SELECT {columns_str} FROM {table_name}")
    rows = source_cursor.fetchall()

    if not rows:
        print(f"  [INFO] 表 {table_name} 无数据需要迁移")
        return 0

    # 清空目标表
    clear_count = clear_table(target_conn, table_name)
    print(f"  [CLEAR] 清空 {table_name}: {clear_count} 条")

    # 插入数据到目标表
    target_cursor = target_conn.cursor()
    target_cursor.executemany(
        f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})",
        rows
    )
    target_conn.commit()

    return len(rows)


def main():
    """主函数"""
    print("=" * 60)
    print("数据迁移脚本")
    print("=" * 60)
    print(f"源数据库: {SOURCE_DB}")
    print(f"目标数据库: {TARGET_DB}")
    print(f"迁移表数: {len(MIGRATE_TABLES)}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 检查源数据库是否存在
    if not os.path.exists(SOURCE_DB):
        print(f"[ERROR] 源数据库不存在: {SOURCE_DB}")
        sys.exit(1)

    # 检查目标数据库是否存在
    if not os.path.exists(TARGET_DB):
        print(f"[ERROR] 目标数据库不存在: {TARGET_DB}")
        sys.exit(1)

    # 连接数据库
    source_conn = sqlite3.connect(SOURCE_DB)
    target_conn = sqlite3.connect(TARGET_DB)

    # 统计
    total_migrated = 0
    failed_tables = []

    print("\n开始迁移...")
    print("-" * 60)

    for table_name in MIGRATE_TABLES:
        print(f"\n迁移表: {table_name}")

        try:
            # 检查源表是否存在
            source_cursor = source_conn.cursor()
            source_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not source_cursor.fetchone():
                print(f"  [WARN] 源数据库中不存在表 {table_name}")
                failed_tables.append(table_name)
                continue

            # 检查目标表是否存在
            target_cursor = target_conn.cursor()
            target_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not target_cursor.fetchone():
                print(f"  [WARN] 目标数据库中不存在表 {table_name}")
                failed_tables.append(table_name)
                continue

            # 迁移数据
            migrated_count = migrate_table(source_conn, target_conn, table_name)
            print(f"  [OK] 迁移 {table_name}: {migrated_count} 条")
            total_migrated += migrated_count

        except Exception as e:
            print(f"  [ERROR] 迁移 {table_name} 失败: {e}")
            failed_tables.append(table_name)

    print("\n" + "=" * 60)
    print("迁移完成")
    print("=" * 60)
    print(f"总迁移记录数: {total_migrated}")
    print(f"成功表数: {len(MIGRATE_TABLES) - len(failed_tables)}")
    print(f"失败表数: {len(failed_tables)}")
    if failed_tables:
        print(f"失败表列表: {failed_tables}")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 关闭连接
    source_conn.close()
    target_conn.close()

    # 返回状态
    if failed_tables:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()