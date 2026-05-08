"""
Repository 基础设施层

Batch 5 新增：为后续数据库访问统一做准备
"""
from .sqlite_base import (
    get_sqlite_connection,
    ensure_parent_dir,
    SQLiteConnectionManager
)

__all__ = [
    "get_sqlite_connection",
    "ensure_parent_dir",
    "SQLiteConnectionManager"
]