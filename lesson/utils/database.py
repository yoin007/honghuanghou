# _*_ coding: utf-8 _*_
# SQLite 数据库优化工具

import sqlite3
from contextlib import contextmanager
from functools import wraps
import logging

from utils.db_config import DATABASES_DIR

logger = logging.getLogger(__name__)


class DatabaseOptimized:
    """SQLite 数据库优化类"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = False

    def initialize(self):
        """初始化数据库优化设置"""
        if self._initialized:
            return
        self._initialized = True
        # 启用 WAL 模式，提高并发性能
        self._set_pragmas()
        logger.info("SQLite database optimization initialized")

    def _set_pragmas(self):
        """设置数据库优化参数"""
        common_dbs = [
            "databases/member.db",
            "databases/lesson.db",
            "databases/homework.db",
            "databases/daily.db"
        ]

        for db_path in common_dbs:
            try:
                conn = sqlite3.connect(db_path)
                # 启用 WAL 模式
                conn.execute("PRAGMA journal_mode=WAL")
                # 启用外键约束
                conn.execute("PRAGMA foreign_keys=ON")
                # 设置同步模式为 NORMAL（平衡性能和数据安全）
                conn.execute("PRAGMA synchronous=NORMAL")
                # 增大缓存大小（负数表示 KB）
                conn.execute("PRAGMA cache_size=-2000")
                # 启用内存映射 I/O
                conn.execute("PRAGMA mmap_size=268435456")
                conn.close()
                logger.info(f"Optimized database: {db_path}")
            except Exception as e:
                logger.warning(f"Could not optimize {db_path}: {e}")


# 全局数据库优化实例
db_optimizer = DatabaseOptimized()


def init_db_optimization():
    """初始化数据库优化（应在应用启动时调用）"""
    db_optimizer.initialize()


@contextmanager
def get_db_connection(db_path: str):
    """
    获取优化后的数据库连接

    用法:
    with get_db_connection("databases/member.db") as conn:
        conn.execute("SELECT * FROM member")
    """
    conn = sqlite3.connect(db_path)
    # 每次获取连接时设置优化参数
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
