# -*- coding: utf-8 -*-
"""
迁移脚本：为 grade_moral_task 表添加时间字段和结转控制字段

添加字段：
- start_date: 任务开始日期
- end_date: 任务结束日期
- can_carryover: 是否允许结转（默认1）

修复问题：carryover.py 查询 t.can_carryover 字段但表不存在此字段

使用方式：
    cd lesson && python scripts/migrate_add_task_fields.py [--sqlite]
"""

import argparse
import sys
import os

# 添加 lesson 目录到 Python 路径
lesson_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, lesson_dir)

from utils.mysql_db import MySQLDatabase
from utils.sqlite_moral_db import MoralDatabase as SQLiteMoralDatabase


def migrate_mysql():
    """MySQL 数据库迁移"""
    print("=" * 60)
    print("开始 MySQL 数据库迁移...")
    print("=" * 60)

    with MySQLDatabase() as db:
        # 检查字段是否已存在
        existing_columns = db.query_all(
            """SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'grade_moral_task'"""
        )
        existing_names = [col['COLUMN_NAME'] for col in existing_columns]

        # 添加 start_date
        if 'start_date' not in existing_names:
            print("添加 start_date 字段...")
            db.execute(
                """ALTER TABLE grade_moral_task
                   ADD COLUMN start_date DATE COMMENT '任务开始日期'
                   AFTER score"""
            )
            print("  ✓ start_date 字段已添加")
        else:
            print("  - start_date 字段已存在，跳过")

        # 添加 end_date
        if 'end_date' not in existing_names:
            print("添加 end_date 字段...")
            db.execute(
                """ALTER TABLE grade_moral_task
                   ADD COLUMN end_date DATE COMMENT '任务结束日期'
                   AFTER start_date"""
            )
            print("  ✓ end_date 字段已添加")
        else:
            print("  - end_date 字段已存在，跳过")

        # 添加 can_carryover
        if 'can_carryover' not in existing_names:
            print("添加 can_carryover 字段...")
            db.execute(
                """ALTER TABLE grade_moral_task
                   ADD COLUMN can_carryover TINYINT DEFAULT 1 COMMENT '是否允许结转'
                   AFTER deadline_type"""
            )
            print("  ✓ can_carryover 字段已添加")
        else:
            print("  - can_carryover 字段已存在，跳过")

    print("\n迁移完成！")


def migrate_sqlite():
    """SQLite 数据库迁移"""
    print("=" * 60)
    print("开始 SQLite 数据库迁移...")
    print("=" * 60)

    # SQLite 不支持 ALTER TABLE ADD COLUMN 的 AFTER 语法，直接添加
    with SQLiteMoralDatabase() as db:
        # 检查字段是否已存在 - grade_moral_task 表
        table_info = db.query_all("PRAGMA table_info(grade_moral_task)")
        existing_names = [col['name'] for col in table_info]

        # SQLite 添加列的方式
        columns_to_add = [
            ('start_date', 'TEXT'),
            ('end_date', 'TEXT'),
            ('can_carryover', 'INTEGER DEFAULT 1'),
        ]

        for col_name, col_def in columns_to_add:
            if col_name not in existing_names:
                print(f"添加 {col_name} 字段...")
                db.execute(f"ALTER TABLE grade_moral_task ADD COLUMN {col_name} {col_def}")
                print(f"  ✓ {col_name} 字段已添加")
            else:
                print(f"  - {col_name} 字段已存在，跳过")

        # 检查 grade 表字段
        grade_info = db.query_all("PRAGMA table_info(grade)")
        grade_existing = [col['name'] for col in grade_info]

        grade_columns_to_add = [
            ('is_archived', 'INTEGER DEFAULT 0'),
            ('archived_at', 'TEXT'),
        ]

        for col_name, col_def in grade_columns_to_add:
            if col_name not in grade_existing:
                print(f"添加 grade.{col_name} 字段...")
                db.execute(f"ALTER TABLE grade ADD COLUMN {col_name} {col_def}")
                print(f"  ✓ grade.{col_name} 字段已添加")
            else:
                print(f"  - grade.{col_name} 字段已存在，跳过")

    print("\n迁移完成！")


def main():
    parser = argparse.ArgumentParser(description='迁移 grade_moral_task 表字段')
    parser.add_argument('--sqlite', action='store_true', help='使用 SQLite 数据库')
    args = parser.parse_args()

    if args.sqlite:
        migrate_sqlite()
    else:
        migrate_mysql()


if __name__ == '__main__':
    main()