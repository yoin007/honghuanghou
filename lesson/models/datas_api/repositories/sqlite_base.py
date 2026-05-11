"""
SQLite 连接基础模块

为后续 repository 层统一数据库访问做准备。
提供轻量级连接工具，避免散落 20+ 处 sqlite3.connect。

Batch 5 第三阶段：基础设施准备
"""
import sqlite3
import os
from typing import Optional, Callable


def ensure_parent_dir(path: str) -> str:
    """
    确保父目录存在，自动创建。

    Args:
        path: 目标文件路径

    Returns:
        原路径（不变）
    """
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    return path


def get_sqlite_connection(
    db_path: str,
    *,
    timeout: float = 30.0,
    row_factory: Optional[Callable] = None,
    check_same_thread: bool = True,
    wal_mode: bool = True  # 默认启用 WAL 模式
) -> sqlite3.Connection:
    """
    获取 SQLite 连接，统一参数和初始化。

    Args:
        db_path: 数据库文件路径
        timeout: 连接超时秒数（默认 30）
        row_factory: 可选行工厂函数，如 sqlite3.Row
        check_same_thread: 多线程访问控制（默认 True，单线程安全）
        wal_mode: 是否启用 WAL 模式（默认 True）

    Returns:
        sqlite3.Connection 对象

    Example:
        >>> conn = get_sqlite_connection("/path/to/db.sqlite")
        >>> conn.execute("SELECT * FROM table")
        >>> conn.close()

        >>> # 使用 Row 工厂
        >>> conn = get_sqlite_connection(db_path, row_factory=sqlite3.Row)
        >>> row = conn.execute("SELECT * FROM table").fetchone()
        >>> print(row["column_name"])

        >>> # 多线程场景
        >>> conn = get_sqlite_connection(db_path, check_same_thread=False)
    """
    # 确保父目录存在（用于新数据库）
    ensure_parent_dir(db_path)

    conn = sqlite3.connect(
        db_path,
        timeout=timeout,
        check_same_thread=check_same_thread
    )

    # 设置行工厂
    if row_factory:
        conn.row_factory = row_factory

    # 启用 WAL 模式和优化设置（提高并发写入性能）
    if wal_mode:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-2000")
        conn.execute("PRAGMA busy_timeout=30000")  # 30秒忙等待超时

    return conn


class SQLiteConnectionManager:
    """
    SQLite 连接管理器，支持上下文管理。

    Example:
        >>> with SQLiteConnectionManager("/path/to/db.sqlite") as conn:
        >>>     conn.execute("INSERT INTO table VALUES (?)", (value,))
    """

    def __init__(
        self,
        db_path: str,
        *,
        timeout: float = 30.0,
        row_factory: Optional[Callable] = None,
        wal_mode: bool = False
    ):
        self.db_path = db_path
        self.timeout = timeout
        self.row_factory = row_factory
        self.wal_mode = wal_mode
        self._conn: Optional[sqlite3.Connection] = None

    def __enter__(self) -> sqlite3.Connection:
        self._conn = get_sqlite_connection(
            self.db_path,
            timeout=self.timeout,
            row_factory=self.row_factory,
            wal_mode=self.wal_mode
        )
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
            self._conn.close()
        return False  # 不抑制异常