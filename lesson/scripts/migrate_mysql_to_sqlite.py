# -*- coding: utf-8 -*-
"""
MySQL 到 SQLite 数据迁移脚本

将德育评价系统的 MySQL 数据库数据迁移到 SQLite

运行方式：
    python scripts/migrate_mysql_to_sqlite.py [--batch-size 100]

依赖：
    - MySQL 连接参数已硬编码（原配置已切换到 SQLite）
    - SQLite 表结构已通过 create_moral_tables.py --sqlite 创建
"""

import sys
import os
import logging
from decimal import Decimal
from typing import List, Dict, Any, Tuple
import json

# 添加 lesson 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import mysql.connector
from mysql.connector import pooling
from utils.sqlite_moral_db import MoralDatabase, get_moral_db_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MySQL 连接配置（硬编码，因为 moral.yaml 已切换到 SQLite）
MYSQL_CONFIG = {
    "host": "172.31.25.228",
    "user": "root",
    "password": "tlzx2003",
    "database": "moral_evaluation",
    "charset": "utf8mb4",
}


class MySQLConnection:
    """MySQL 连接类（迁移专用，不依赖配置文件）"""

    def __init__(self, config: dict = None):
        self.config = config or MYSQL_CONFIG
        self._connection = None
        self._cursor = None

    def __enter__(self):
        self._connection = mysql.connector.connect(**self.config)
        self._cursor = self._connection.cursor(dictionary=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None and self._connection:
            self._connection.rollback()
        elif self._connection:
            self._connection.commit()
        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()
        return False

    def query_one(self, sql: str, params: tuple = None) -> dict:
        self._cursor.execute(sql, params)
        return self._cursor.fetchone()

    def query_all(self, sql: str, params: tuple = None) -> list:
        self._cursor.execute(sql, params)
        return self._cursor.fetchall()

    def query_value(self, sql: str, params: tuple = None):
        result = self.query_one(sql, params)
        return list(result.values())[0] if result else None


# 表迁移顺序（按外键依赖顺序）
TABLE_ORDER = [
    'school_year',
    'semester',
    'grade',
    'grade_level_config',
    'class',
    'student',
    'teacher',
    'role',
    'student_class_history',
    'student_status_change',
    'daily_event_type',
    'school_event_type',
    'grade_moral_task',
    'student_daily_record',
    'student_school_record',
    'student_task_finish',
    'punishment_record',
    'collective_event',
    'collective_event_distribution',
    'moral_evaluation',
    'violation_escalation_rule',
    'semester_carryover_config',
    'data_visibility_config',
    'warning_config',
    'warning_log',
    'task_carryover_log',
    'moral_operation_log',
    'student_profile',
    'student_profile_history',
    'profile_config',
    'ai_consultation',
    'ai_consultation_message',
    'birthday_reminder',
    'birthday_reminder_config',
    'moral_config',
]


def convert_value(value: Any) -> Any:
    """
    转换 MySQL 值到 SQLite 兼容格式

    Args:
        value: MySQL 值

    Returns:
        SQLite 兼容值
    """
    if value is None:
        return None

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, bytes):
        return value.decode('utf-8')

    return value


def convert_row(row: Dict[str, Any]) -> Tuple:
    """
    转换 MySQL 行数据到 SQLite 兼容格式

    Args:
        row: MySQL 行数据字典

    Returns:
        SQLite 兼容的元组
    """
    return tuple(convert_value(v) for v in row.values())


def get_table_columns(mysql_db: MySQLConnection, table_name: str) -> List[str]:
    """
    获取 MySQL 表的列名列表

    Args:
        mysql_db: MySQL 数据库连接
        table_name: 表名

    Returns:
        列名列表
    """
    result = mysql_db.query_all(
        """SELECT COLUMN_NAME FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = 'moral_evaluation' AND TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION""",
        (table_name,)
    )
    return [r['COLUMN_NAME'] for r in result]


def migrate_table(mysql_db: MySQLConnection, sqlite_db: MoralDatabase,
                  table_name: str, batch_size: int = 100) -> int:
    """
    迁移单个表的数据

    Args:
        mysql_db: MySQL 数据库连接
        sqlite_db: SQLite 数据库连接
        table_name: 表名
        batch_size: 批量插入大小

    Returns:
        迁移的记录数
    """
    # 获取列名
    columns = get_table_columns(mysql_db, table_name)
    if not columns:
        logger.warning(f"Table '{table_name}' not found in MySQL")
        return 0

    column_list = ', '.join(columns)
    placeholders = ', '.join(['?'] * len(columns))

    # 从 MySQL 读取数据
    logger.info(f"Reading data from MySQL table '{table_name}'...")
    rows = mysql_db.query_all(f"SELECT {column_list} FROM {table_name}")

    if not rows:
        logger.info(f"Table '{table_name}' is empty, skipping")
        return 0

    # 批量插入到 SQLite
    logger.info(f"Inserting {len(rows)} rows into SQLite table '{table_name}'...")

    insert_sql = f"INSERT OR REPLACE INTO {table_name} ({column_list}) VALUES ({placeholders})"
    converted_rows = [convert_row(row) for row in rows]

    # 批量插入
    total = 0
    for i in range(0, len(converted_rows), batch_size):
        batch = converted_rows[i:i + batch_size]
        sqlite_db._cursor.executemany(insert_sql, batch)
        total += len(batch)
        logger.debug(f"Inserted batch {i//batch_size + 1}: {len(batch)} rows")

    sqlite_db._connection.commit()
    logger.info(f"Migrated {total} rows from '{table_name}'")

    return total


def verify_migration(mysql_db: MySQLConnection, sqlite_db: MoralDatabase,
                     table_name: str) -> bool:
    """
    验证迁移结果

    Args:
        mysql_db: MySQL 数据库连接
        sqlite_db: SQLite 数据库连接
        table_name: 表名

    Returns:
        是否验证通过
    """
    mysql_count = mysql_db.query_value(f"SELECT COUNT(*) FROM {table_name}")
    sqlite_count = sqlite_db.query_value(f"SELECT COUNT(*) FROM {table_name}")

    if mysql_count == sqlite_count:
        logger.info(f"✓ '{table_name}': MySQL={mysql_count}, SQLite={sqlite_count}")
        return True
    else:
        logger.warning(f"✗ '{table_name}': MySQL={mysql_count}, SQLite={sqlite_count} (mismatch)")
        return False


def run_migration(batch_size: int = 100, verify: bool = True):
    """
    执行完整迁移

    Args:
        batch_size: 批量插入大小
        verify: 是否验证迁移结果
    """
    db_path = get_moral_db_path()

    # 检查 SQLite 数据库是否存在
    if not os.path.exists(db_path):
        logger.error(f"SQLite database not found at {db_path}")
        logger.error("Please run: python scripts/create_moral_tables.py --sqlite")
        sys.exit(1)

    logger.info("Starting MySQL to SQLite migration...")
    logger.info(f"SQLite database: {db_path}")

    # 连接 MySQL（使用硬编码配置）
    mysql_db = MySQLConnection()
    mysql_db.__enter__()

    # 连接 SQLite
    sqlite_conn = sqlite3.connect(db_path)
    sqlite_conn.execute("PRAGMA foreign_keys=OFF")  # 迁移时暂时关闭外键约束
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    try:
        total_rows = 0
        success_tables = 0

        for table_name in TABLE_ORDER:
            try:
                count = migrate_table_mysql_sqlite_direct(
                    mysql_db, sqlite_conn, sqlite_cursor, table_name, batch_size
                )
                total_rows += count
                success_tables += 1
            except Exception as e:
                logger.error(f"Failed to migrate '{table_name}': {e}")
                continue

        logger.info(f"\nMigration completed!")
        logger.info(f"Total rows migrated: {total_rows}")
        logger.info(f"Tables migrated successfully: {success_tables}/{len(TABLE_ORDER)}")

        if verify:
            logger.info("\nVerifying migration results...")
            verify_count = 0
            for table_name in TABLE_ORDER:
                if verify_migration_direct(mysql_db, sqlite_conn, table_name):
                    verify_count += 1

            logger.info(f"Verification passed: {verify_count}/{len(TABLE_ORDER)} tables")

    finally:
        mysql_db.__exit__(None, None, None)
        sqlite_conn.execute("PRAGMA foreign_keys=ON")
        sqlite_conn.close()


def migrate_table_mysql_sqlite_direct(mysql_db: MySQLConnection, sqlite_conn: sqlite3.Connection,
                                       sqlite_cursor: sqlite3.Cursor, table_name: str,
                                       batch_size: int = 100) -> int:
    """
    直接迁移单个表（使用已建立的连接）

    Args:
        mysql_db: MySQL 数据库连接
        sqlite_conn: SQLite 连接
        sqlite_cursor: SQLite 游标
        table_name: 表名
        batch_size: 批量插入大小

    Returns:
        迁移的记录数
    """
    # 获取列名
    columns = get_table_columns(mysql_db, table_name)
    if not columns:
        logger.warning(f"Table '{table_name}' not found in MySQL")
        return 0

    column_list = ', '.join(columns)
    placeholders = ', '.join(['?'] * len(columns))

    # 从 MySQL 读取数据
    rows = mysql_db.query_all(f"SELECT {column_list} FROM {table_name}")

    if not rows:
        logger.info(f"Table '{table_name}' is empty, skipping")
        return 0

    # 批量插入到 SQLite
    insert_sql = f"INSERT OR REPLACE INTO {table_name} ({column_list}) VALUES ({placeholders})"
    converted_rows = [convert_row(row) for row in rows]

    total = 0
    for i in range(0, len(converted_rows), batch_size):
        batch = converted_rows[i:i + batch_size]
        sqlite_cursor.executemany(insert_sql, batch)
        sqlite_conn.commit()
        total += len(batch)

    logger.info(f"Migrated {total} rows from '{table_name}'")
    return total


def verify_migration_direct(mysql_db: MySQLConnection, sqlite_conn: sqlite3.Connection,
                            table_name: str) -> bool:
    """
    直接验证迁移结果

    Args:
        mysql_db: MySQL 数据库连接
        sqlite_conn: SQLite 连接
        table_name: 表名

    Returns:
        是否验证通过
    """
    try:
        mysql_count = mysql_db.query_value(f"SELECT COUNT(*) FROM {table_name}")
        sqlite_cursor = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        sqlite_count = sqlite_cursor.fetchone()[0]

        if mysql_count == sqlite_count:
            logger.info(f"✓ '{table_name}': MySQL={mysql_count}, SQLite={sqlite_count}")
            return True
        else:
            logger.warning(f"✗ '{table_name}': MySQL={mysql_count}, SQLite={sqlite_count} (mismatch)")
            return False
    except Exception as e:
        logger.warning(f"✗ '{table_name}' verification failed: {e}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate moral evaluation data from MySQL to SQLite")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch insert size (default: 100)")
    parser.add_argument("--no-verify", action="store_true", help="Skip verification after migration")
    args = parser.parse_args()

    try:
        run_migration(batch_size=args.batch_size, verify=not args.no_verify)
        logger.info("Migration script completed successfully!")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()