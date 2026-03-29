# -*- coding: utf-8 -*-
"""
MySQL数据库连接池管理模块
用于德育评价系统的MySQL数据库连接

特性：
- 连接池管理，避免频繁创建/销毁连接
- 上下文管理器支持，自动关闭连接
- 支持事务操作
- 兼容现有 parking.py 的连接方式
"""

import mysql.connector
from mysql.connector import pooling, Error
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager
import logging
from config.config import Config

logger = logging.getLogger(__name__)

# 全局连接池缓存
_connection_pools: Dict[str, pooling.MySQLConnectionPool] = {}


def get_connection_pool(pool_name: str = "moral", config_file: str = "moral.yaml") -> pooling.MySQLConnectionPool:
    """
    获取或创建MySQL连接池

    Args:
        pool_name: 连接池名称
        config_file: 配置文件名

    Returns:
        MySQLConnectionPool: 连接池对象
    """
    global _connection_pools

    if pool_name not in _connection_pools:
        config = Config()
        try:
            db_config = config.get_config("moral_db", config_file)
        except Exception as e:
            logger.error(f"Failed to load database config from {config_file}: {e}")
            raise ValueError(f"Database configuration not found in {config_file}")

        # 连接池配置
        pool_config = {
            "pool_name": pool_name,
            "pool_size": db_config.get("pool_size", 5),
            "host": db_config["host"],
            "user": db_config["user"],
            "password": db_config["password"],
            "database": db_config["database"],
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
            "autocommit": False,  # 手动事务管理
        }

        try:
            _connection_pools[pool_name] = pooling.MySQLConnectionPool(**pool_config)
            logger.info(f"MySQL connection pool '{pool_name}' created successfully")
        except Error as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise

    return _connection_pools[pool_name]


@contextmanager
def get_db_connection(pool_name: str = "moral", config_file: str = "moral.yaml"):
    """
    获取数据库连接的上下文管理器

    使用方式:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM student")
            results = cursor.fetchall()

    Args:
        pool_name: 连接池名称
        config_file: 配置文件名

    Yields:
        mysql.connector.connection: MySQL连接对象
    """
    pool = get_connection_pool(pool_name, config_file)
    connection = None

    try:
        connection = pool.get_connection()
        yield connection
    except Error as e:
        logger.error(f"Database connection error: {e}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            connection.close()


class MySQLDatabase:
    """
    MySQL数据库操作类
    提供便捷的数据库操作方法
    """

    def __init__(self, pool_name: str = "moral", config_file: str = "moral.yaml"):
        self.pool_name = pool_name
        self.config_file = config_file
        self._connection = None
        self._cursor = None

    def __enter__(self):
        """进入上下文管理器"""
        pool = get_connection_pool(self.pool_name, self.config_file)
        self._connection = pool.get_connection()
        self._cursor = self._connection.cursor(dictionary=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if exc_type is not None:
            # 发生异常，回滚事务
            if self._connection:
                self._connection.rollback()
        else:
            # 正常退出，提交事务
            if self._connection:
                self._connection.commit()

        if self._cursor:
            self._cursor.close()
        if self._connection:
            self._connection.close()

        return False  # 不抑制异常

    def execute(self, query: str, params: Optional[Tuple] = None) -> int:
        """
        执行SQL语句（INSERT/UPDATE/DELETE）

        Args:
            query: SQL语句
            params: 参数

        Returns:
            int: 影响的行数
        """
        self._cursor.execute(query, params)
        return self._cursor.rowcount

    def executemany(self, query: str, params_list: List[Tuple]) -> int:
        """
        批量执行SQL语句

        Args:
            query: SQL语句
            params_list: 参数列表

        Returns:
            int: 影响的行数
        """
        self._cursor.executemany(query, params_list)
        return self._cursor.rowcount

    def query_one(self, query: str, params: Optional[Tuple] = None) -> Optional[Dict[str, Any]]:
        """
        查询单条记录

        Args:
            query: SQL语句
            params: 参数

        Returns:
            Optional[Dict]: 查询结果（字典形式）或 None
        """
        self._cursor.execute(query, params)
        return self._cursor.fetchone()

    def query_all(self, query: str, params: Optional[Tuple] = None) -> List[Dict[str, Any]]:
        """
        查询多条记录

        Args:
            query: SQL语句
            params: 参数

        Returns:
            List[Dict]: 查询结果列表
        """
        self._cursor.execute(query, params)
        return self._cursor.fetchall()

    def query_value(self, query: str, params: Optional[Tuple] = None) -> Optional[Any]:
        """
        查询单个值

        Args:
            query: SQL语句
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
        获取最后插入的ID

        Returns:
            Optional[int]: 最后插入的ID
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
        """获取游标对象（用于高级操作）"""
        return self._cursor

    @property
    def connection(self):
        """获取连接对象（用于高级操作）"""
        return self._connection


def execute_query(
    query: str,
    params: Optional[Tuple] = None,
    pool_name: str = "moral",
    config_file: str = "moral.yaml",
    fetch_all: bool = False
) -> Optional[Any]:
    """
    快捷查询函数（自动管理连接）

    Args:
        query: SQL语句
        params: 参数
        pool_name: 连接池名称
        config_file: 配置文件名
        fetch_all: 是否获取所有结果

    Returns:
        查询结果
    """
    with MySQLDatabase(pool_name, config_file) as db:
        if fetch_all:
            return db.query_all(query, params)
        return db.query_one(query, params)


def execute_insert(
    query: str,
    params: Optional[Tuple] = None,
    pool_name: str = "moral",
    config_file: str = "moral.yaml"
) -> Optional[int]:
    """
    快捷插入函数（自动管理连接和事务）

    Args:
        query: SQL语句
        params: 参数
        pool_name: 连接池名称
        config_file: 配置文件名

    Returns:
        Optional[int]: 插入的记录ID
    """
    with MySQLDatabase(pool_name, config_file) as db:
        db.execute(query, params)
        return db.lastrowid()


def execute_update(
    query: str,
    params: Optional[Tuple] = None,
    pool_name: str = "moral",
    config_file: str = "moral.yaml"
) -> int:
    """
    快捷更新函数（自动管理连接和事务）

    Args:
        query: SQL语句
        params: 参数
        pool_name: 连接池名称
        config_file: 配置文件名

    Returns:
        int: 影响的行数
    """
    with MySQLDatabase(pool_name, config_file) as db:
        return db.execute(query, params)


def execute_batch(
    query: str,
    params_list: List[Tuple],
    pool_name: str = "moral",
    config_file: str = "moral.yaml"
) -> int:
    """
    快捷批量执行函数（自动管理连接和事务）

    Args:
        query: SQL语句
        params_list: 参数列表
        pool_name: 连接池名称
        config_file: 配置文件名

    Returns:
        int: 影响的行数
    """
    with MySQLDatabase(pool_name, config_file) as db:
        return db.executemany(query, params_list)


# 导出
__all__ = [
    'get_connection_pool',
    'get_db_connection',
    'MySQLDatabase',
    'execute_query',
    'execute_insert',
    'execute_update',
    'execute_batch',
]