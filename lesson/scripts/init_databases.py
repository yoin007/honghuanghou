# _*_ coding: utf-8 _*_
# @Time: 2026/03/17
# @Author: Claude
# @Description: 初始化数据库脚本

"""
初始化数据库脚本
用法: python scripts/init_databases.py [--reset]

选项:
  --reset  删除现有数据库并重新创建
"""

import os
import sys
import sqlite3
import argparse

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.log import LogConfig

log = LogConfig().get_logger()

# 数据库目录
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "databases")

# 数据库配置
DATABASES = {
    "daily.db": {
        "tables": {
            "daily": """
                CREATE TABLE IF NOT EXISTS daily(
                    id INTEGER PRIMARY KEY,
                    event TEXT,
                    sid TEXT,
                    note TEXT,
                    recorder TEXT,
                    style TEXT,
                    create_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
    },
    "homework.db": {
        "tables": {
            "homework": """
                CREATE TABLE IF NOT EXISTS homework (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_code INTEGER,
                    subject TEXT,
                    teacher TEXT,
                    content TEXT,
                    deadline TEXT,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status BOOLEAN DEFAULT 0,
                    duration INTEGER,
                    type TEXT,
                    wxid TEXT,
                    deleted INTEGER DEFAULT 0
                )
            """,
            "morning": """
                CREATE TABLE IF NOT EXISTS morning (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_code INTEGER,
                    subject TEXT,
                    teacher TEXT,
                    content TEXT,
                    assigned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    note TEXT,
                    wxid TEXT
                )
            """,
            "announcements": """
                CREATE TABLE IF NOT EXISTS announcements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_code INTEGER,
                    title TEXT,
                    author TEXT,
                    content TEXT,
                    date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    wxid TEXT,
                    deleted INTEGER DEFAULT 0
                )
            """
        }
    },
    "inout.db": {
        "tables": {
            "inout": """
                CREATE TABLE IF NOT EXISTS inout(
                    id INTEGER PRIMARY KEY,
                    sid TEXT,
                    style TEXT,
                    days TEXT,
                    status TEXT,
                    recorder TEXT,
                    guard TEXT DEFAULT "",
                    active BOOLEAN DEFAULT 1,
                    consumer TEXT DEFAULT "",
                    note TEXT,
                    create_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
        }
    },
    "messages.db": {
        "tables": {
            "messages": """
                CREATE TABLE IF NOT EXISTS messages(
                    id INTEGER PRIMARY KEY autoincrement,
                    wxid TEXT,
                    msg_id TEXT,
                    type INTEGER,
                    sender TEXT,
                    roomid TEXT,
                    content TEXT,
                    thumb TEXT,
                    ext TEXT,
                    is_at BOOLEAN,
                    is_self BOOLEAN,
                    is_group BOOLEAN,
                    create_time INTEGER
                )
            """
        }
    },
    "queues.db": {
        "tables": {
            "queues": """
                CREATE TABLE IF NOT EXISTS queues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    status TEXT DEFAULT 'pending',
                    msg_id TEXT,
                    data TEXT,
                    producer TEXT,
                    p_time TEXT,
                    consumer TEXT,
                    c_time TEXT,
                    timestamp INTEGER,
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT
                )
            """
        }
    }
}


def init_database(db_name: str, db_config: dict, reset: bool = False) -> bool:
    """
    初始化单个数据库

    Args:
        db_name: 数据库文件名
        db_config: 数据库配置
        reset: 是否重置数据库

    Returns:
        bool: 是否成功
    """
    db_path = os.path.join(DB_DIR, db_name)

    # 确保 databases 目录存在
    os.makedirs(DB_DIR, exist_ok=True)

    # 如果需要重置，删除现有数据库
    if reset and os.path.exists(db_path):
        try:
            os.remove(db_path)
            log.info(f"已删除现有数据库: {db_name}")
        except Exception as e:
            log.error(f"删除数据库失败 {db_name}: {e}")
            return False

    # 如果数据库已存在且不需要重置
    if os.path.exists(db_path) and not reset:
        log.info(f"数据库已存在，跳过创建: {db_name}")
        return True

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建所有表
        for table_name, create_sql in db_config.get("tables", {}).items():
            try:
                cursor.execute(create_sql)
                log.info(f"  创建表: {table_name}")
            except sqlite3.OperationalError as e:
                if "already exists" in str(e):
                    log.info(f"  表已存在: {table_name}")
                else:
                    raise e

        # 设置 WAL 模式
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")

        conn.commit()
        conn.close()

        log.info(f"数据库初始化成功: {db_name}")
        return True

    except Exception as e:
        log.error(f"初始化数据库失败 {db_name}: {e}")
        return False


def init_all_databases(reset: bool = False) -> dict:
    """
    初始化所有数据库

    Args:
        reset: 是否重置数据库

    Returns:
        dict: 初始化结果
    """
    results = {}

    log.info("=" * 50)
    log.info("开始初始化数据库")
    log.info("=" * 50)

    for db_name, db_config in DATABASES.items():
        log.info(f"\n处理数据库: {db_name}")
        results[db_name] = init_database(db_name, db_config, reset)

    log.info("\n" + "=" * 50)
    log.info("数据库初始化完成")
    log.info("=" * 50)

    # 打印结果摘要
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    log.info(f"\n成功: {success_count}/{total_count}")

    for db_name, success in results.items():
        status = "✓" if success else "✗"
        log.info(f"  {status} {db_name}")

    return results


def main():
    parser = argparse.ArgumentParser(description="初始化数据库")
    parser.add_argument("--reset", action="store_true", help="删除现有数据库并重新创建")
    parser.add_argument("--db", type=str, help="只初始化指定的数据库")
    args = parser.parse_args()

    if args.db:
        # 只初始化指定的数据库
        if args.db in DATABASES:
            log.info(f"只初始化数据库: {args.db}")
            init_database(args.db, DATABASES[args.db], args.reset)
        else:
            log.error(f"未知的数据库: {args.db}")
            log.info(f"可用的数据库: {list(DATABASES.keys())}")
    else:
        # 初始化所有数据库
        init_all_databases(args.reset)


if __name__ == "__main__":
    main()