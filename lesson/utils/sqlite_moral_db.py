# -*- coding: utf-8 -*-
"""
德育系统 SQLite 数据库操作类

特性：
- 兼容 MySQLDatabase 接口，无需修改 API 代码
- 自动将 %s 占位符转换为 ? 占位符
- 启用 WAL 模式提高并发性能
- 启用外键约束
- 上下文管理器支持，自动提交/关闭连接
"""

import sqlite3
import logging
import os
from typing import Optional, Dict, Any, List, Tuple, Union
from decimal import Decimal
import json

from utils.db_config import MORAL_DB, DATABASES_DIR


def _get_sqlite_connection():
    """延迟导入避免循环依赖"""
    from models.datas_api.repositories.sqlite_base import get_sqlite_connection
    return get_sqlite_connection


logger = logging.getLogger(__name__)


class MoralDatabase:
    """
    德育系统 SQLite 数据库操作类

    兼容 MySQLDatabase 接口，API 代码无需修改即可切换
    """

    def __init__(self, db_path: str = None):
        """
        初始化数据库连接

        Args:
            db_path: 数据库文件路径，默认为 databases/moral.db
        """
        self.db_path = db_path or MORAL_DB
        self._connection = None
        self._cursor = None

        # 确保数据库目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def __enter__(self):
        """进入上下文管理器"""
        self._connection = _get_sqlite_connection()(self.db_path)
        try:
            self._connection.row_factory = sqlite3.Row

            # 启用优化设置
            self._connection.execute("PRAGMA foreign_keys=ON")
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA synchronous=NORMAL")
            self._connection.execute("PRAGMA cache_size=-2000")  # 2MB cache

            self._cursor = self._connection.cursor()
            return self
        except Exception:
            self._connection.close()
            self._connection = None
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if exc_type is not None:
            # 发生异常，回滚事务
            if self._connection:
                self._connection.rollback()
            logger.error(f"Database error: {exc_val}")
        else:
            # 正常退出，提交事务
            if self._connection:
                self._connection.commit()

        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()

        return False  # 不抑制异常

    def _convert_sql(self, sql: str) -> str:
        """
        将 MySQL SQL 语句转换为 SQLite SQL

        主要转换：
        - %s 占位符 → ? 占位符
        - NOW() → datetime('now')
        """
        # 转换占位符
        converted = sql.replace('%s', '?')

        # 转换 NOW() 函数
        converted = converted.replace('NOW()', "datetime('now', 'localtime')")

        return converted

    def _convert_params(self, params: Optional[Tuple]) -> Optional[Tuple]:
        """
        转换参数值，处理 Decimal 类型

        Args:
            params: 原始参数

        Returns:
            转换后的参数
        """
        if params is None:
            return None

        converted = []
        for p in params:
            if isinstance(p, Decimal):
                converted.append(float(p))
            elif isinstance(p, (dict, list)):
                converted.append(json.dumps(p, ensure_ascii=False))
            else:
                converted.append(p)

        return tuple(converted) if converted else None

    def execute(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        执行 SQL 语句（INSERT/UPDATE/DELETE）

        Args:
            query: SQL 语句（支持 %s 占位符）
            params: 参数

        Returns:
            int: 影响的行数
        """
        sql = self._convert_sql(query)
        converted_params = self._convert_params(params)
        self._cursor.execute(sql, converted_params or ())
        return self._cursor.rowcount

    def executemany(self, query: str, params_list: List[Tuple]) -> int:
        """
        批量执行 SQL 语句

        Args:
            query: SQL 语句
            params_list: 参数列表

        Returns:
            int: 影响的行数
        """
        sql = self._convert_sql(query)
        converted_list = [self._convert_params(p) for p in params_list]
        self._cursor.executemany(sql, converted_list)
        return self._cursor.rowcount

    def query_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """
        查询单条记录

        Args:
            query: SQL 语句
            params: 参数

        Returns:
            Optional[Dict]: 查询结果（字典形式）或 None
        """
        sql = self._convert_sql(query)
        converted_params = self._convert_params(params)
        self._cursor.execute(sql, converted_params or ())
        row = self._cursor.fetchone()
        return dict(row) if row else None

    def query_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        查询多条记录

        Args:
            query: SQL 语句
            params: 参数

        Returns:
            List[Dict]: 查询结果列表
        """
        sql = self._convert_sql(query)
        converted_params = self._convert_params(params)
        self._cursor.execute(sql, converted_params or ())
        rows = self._cursor.fetchall()
        return [dict(row) for row in rows]

    def query_value(self, query: str, params: Optional[Tuple] = None) -> Optional[Any]:
        """
        查询单个值

        Args:
            query: SQL 语句
            params: 参数

        Returns:
            Optional[Any]: 查询值或 None
        """
        result = self.query_one(query, params)
        if result:
            # 返回第一个值
            return list(result.values())[0]
        return None

    def lastrowid(self) -> Optional[int]:
        """
        获取最后插入的 ID

        Returns:
            Optional[int]: 最后插入的 ID
        """
        return self._cursor.lastrowid

    def commit(self):
        """手动提交事务"""
        if self._connection:
            self._connection.commit()

    def rollback(self):
        """手动回滚事务"""
        if self._connection:
            self._connection.rollback()

    @property
    def cursor(self):
        """获取游标对象"""
        return self._cursor

    @property
    def connection(self):
        """获取连接对象"""
        return self._connection


def get_moral_db_path() -> str:
    """获取德育数据库路径"""
    return MORAL_DB


def init_moral_db():
    """
    初始化德育数据库（应在应用启动时调用）

    确保 WAL 模式已启用
    """
    if not os.path.exists(MORAL_DB):
        logger.warning(f"Moral database not found at {MORAL_DB}")
        return

    conn = _get_sqlite_connection()(MORAL_DB)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    finally:
        conn.close()
    logger.info(f"Moral database initialized: {MORAL_DB}")


__all__ = [
    'MoralDatabase',
    'get_moral_db_path',
    'init_moral_db',
]
