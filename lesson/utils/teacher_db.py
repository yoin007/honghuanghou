# -*- coding: utf-8 -*-
"""
教师数据库操作类

从 SQLite 读取教师数据，替代 Excel 存储
"""

import sqlite3
import logging
import os
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from utils.db_config import AUTH_DB, DATABASES_DIR

logger = logging.getLogger(__name__)


class TeacherDB:
    """教师数据库操作类"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or AUTH_DB
        self._connection = None

    def __enter__(self):
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
        return False

    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        """查询单条记录"""
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def query_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        """查询多条记录"""
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def query_value(self, sql: str, params: tuple = ()) -> Any:
        """查询单个值"""
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row else None

    def execute(self, sql: str, params: tuple = ()) -> None:
        """执行SQL"""
        cursor = self._connection.cursor()
        cursor.execute(sql, params)

    def lastrowid(self) -> int:
        """获取最后插入的ID"""
        return self._connection.cursor().lastrowid


@contextmanager
def get_teacher_db():
    """获取教师数据库连接"""
    with TeacherDB() as db:
        yield db


def get_all_teachers() -> List[Dict]:
    """获取所有教师列表"""
    with get_teacher_db() as db:
        return db.query_all("SELECT * FROM teacher ORDER BY name")


def get_teacher_by_name(name: str) -> Optional[Dict]:
    """根据姓名获取教师"""
    with get_teacher_db() as db:
        return db.query_one("SELECT * FROM teacher WHERE name = ?", (name,))


def get_teachers_by_role(role: str) -> List[Dict]:
    """根据角色获取教师列表（支持多角色匹配）"""
    with get_teacher_db() as db:
        return db.query_all(
            "SELECT * FROM teacher WHERE role LIKE ? AND active = 1",
            (f'%{role}%',)
        )


def get_teachers_dataframe():
    """获取教师数据（返回 DataFrame 格式，兼容旧代码）"""
    import pandas as pd
    teachers = get_all_teachers()
    if not teachers:
        return pd.DataFrame()
    df = pd.DataFrame(teachers)
    # 保持列名兼容
    column_mapping = {
        'name': 'name',
        'pwd': 'pwd',
        'role': 'role',
        'level': 'level',
        'subject': 'subject',
        'course': 'course',
        'notice': 'notice',
        'active': 'active',
        'raw_pwd': 'raw_pwd',
        'is_password_changed': 'is_password_changed'
    }
    return df[[col for col in column_mapping.keys() if col in df.columns]]