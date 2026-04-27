# -*- coding: utf-8 -*-
"""
清空德育系统数据表脚本

可清空的表：
- student_daily_record: 日常表现记录
- student_school_record: 校级事件记录
- grade_moral_task: 德育任务配置
- student_task_finish: 学生任务完成记录
- moment_record: 点滴记录
- tasks: 任务记录（task.db）
"""

import sqlite3
import os
from datetime import datetime

# 获取 lesson 目录（脚本在 lesson/scripts/ 下）
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "databases")

# 表配置：数据库文件 -> [(表名, 中文名)]
TABLE_CONFIG = {
    "moral.db": [
        ("student_daily_record", "日常表现记录"),
        ("student_school_record", "校级事件记录"),
        ("grade_moral_task", "德育任务配置"),
        ("student_task_finish", "学生任务完成记录"),
        ("moment_record", "点滴记录"),
    ],
}


def get_table_count(db_path: str, table: str) -> int:
    """获取表记录数"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def clear_table(db_path: str, table: str) -> int:
    """清空表记录，返回删除数量"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    cursor.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()
    return count


def show_status():
    """显示各表当前状态"""
    print("\n=== 数据表状态 ===")
    print("-" * 40)
    for db_file, tables in TABLE_CONFIG.items():
        db_path = os.path.join(DB_DIR, db_file)
        if not os.path.exists(db_path):
            print(f"数据库不存在: {db_file}")
            continue
        for table, name in tables:
            count = get_table_count(db_path, table)
            print(f"{name} ({table}): {count} 条记录")
    print("-" * 40)


def clear_all():
    """清空所有表"""
    print("\n=== 清空所有数据表 ===")
    total_deleted = 0
    for db_file, tables in TABLE_CONFIG.items():
        db_path = os.path.join(DB_DIR, db_file)
        if not os.path.exists(db_path):
            continue
        for table, name in tables:
            deleted = clear_table(db_path, table)
            if deleted > 0:
                print(f"✓ {name}: 删除 {deleted} 条记录")
                total_deleted += deleted
    print(f"\n总计删除 {total_deleted} 条记录")


def clear_selected(selected_tables: list):
    """清空选定的表"""
    print("\n=== 清空选定数据表 ===")
    total_deleted = 0
    for db_file, tables in TABLE_CONFIG.items():
        db_path = os.path.join(DB_DIR, db_file)
        if not os.path.exists(db_path):
            continue
        for table, name in tables:
            if table in selected_tables or name in selected_tables:
                deleted = clear_table(db_path, table)
                print(f"✓ {name}: 删除 {deleted} 条记录")
                total_deleted += deleted
    print(f"\n总计删除 {total_deleted} 条记录")


def interactive_mode():
    """交互式选择清空"""
    show_status()

    print("\n请选择要清空的表（输入编号，多个用逗号分隔，输入 'all' 清空全部）：")
    print("  1. 日常表现记录")
    print("  2. 校级事件记录")
    print("  3. 德育任务配置")
    print("  4. 学生任务完成记录")
    print("  5. 点滴记录")
    print("  all. 清空全部")
    print("  q. 退出")

    choice = input("\n请输入选择: ").strip().lower()

    if choice == "q":
        print("已退出")
        return

    if choice == "all":
        confirm = input("确认清空所有数据表？(yes/no): ").strip().lower()
        if confirm == "yes":
            clear_all()
        else:
            print("已取消")
        return

    # 解析编号
    table_map = {
        "1": "student_daily_record",
        "2": "student_school_record",
        "3": "grade_moral_task",
        "4": "student_task_finish",
        "5": "moment_record",
    }

    selected = []
    for num in choice.split(","):
        num = num.strip()
        if num in table_map:
            selected.append(table_map[num])

    if selected:
        confirm = input(f"确认清空 {len(selected)} 个表？(yes/no): ").strip().lower()
        if confirm == "yes":
            clear_selected(selected)
        else:
            print("已取消")
    else:
        print("无效选择")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清空德育系统数据表")
    parser.add_argument("--status", action="store_true", help="只显示状态，不执行清空")
    parser.add_argument("--all", action="store_true", help="清空所有表")
    parser.add_argument("--tables", nargs="+", help="指定要清空的表名")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.all:
        confirm = input("确认清空所有数据表？(yes/no): ").strip().lower()
        if confirm == "yes":
            clear_all()
        else:
            print("已取消")
    elif args.tables:
        clear_selected(args.tables)
    else:
        interactive_mode()