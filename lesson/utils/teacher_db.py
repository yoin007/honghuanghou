# -*- coding: utf-8 -*-
"""
教师数据库操作类

统一教师身份数据到 moral.db 的 teacher 表。auth.db.teacher 仅作为历史
迁移来源保留，不再作为登录、教师管理和通知查询的主表。
"""

import sqlite3
import logging
import os
import re
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from utils.db_config import AUTH_DB, MORAL_DB

logger = logging.getLogger(__name__)
_AUTH_MIGRATED = False


def _teacher_id_from_name(name: str) -> str:
    safe_name = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]", "_", str(name or ""))
    return f"T_{safe_name[:120]}"


class TeacherDB:
    """教师数据库操作类，默认连接 moral.db。"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or MORAL_DB
        self._connection = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._connection = sqlite3.connect(self.db_path)
        self._connection.row_factory = sqlite3.Row
        if self.db_path == MORAL_DB:
            ensure_teacher_schema(self._connection)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self._connection.close()
        return False

    def query_one(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def query_all(self, sql: str, params: tuple = ()) -> List[Dict]:
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def query_value(self, sql: str, params: tuple = ()) -> Any:
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return row[0] if row else None

    def execute(self, sql: str, params: tuple = ()) -> int:
        cursor = self._connection.cursor()
        cursor.execute(sql, params)
        return cursor.rowcount

    def lastrowid(self) -> int:
        return self._connection.cursor().lastrowid


@contextmanager
def get_teacher_db():
    """获取教师数据库连接"""
    with TeacherDB() as db:
        yield db


def ensure_teacher_schema(conn: sqlite3.Connection = None):
    """确保 moral.teacher 具备登录、教师档案和会员身份字段。"""
    should_close = conn is None
    if conn is None:
        os.makedirs(os.path.dirname(MORAL_DB), exist_ok=True)
        conn = sqlite3.connect(MORAL_DB)

    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS teacher (
            teacher_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            wxid TEXT,
            subject TEXT,
            password_hash TEXT,
            role TEXT DEFAULT 'teacher',
            level INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            notice_enabled INTEGER DEFAULT 1,
            is_password_changed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )

    columns = {row[1] for row in cursor.execute("PRAGMA table_info(teacher)").fetchall()}
    if "alias" in columns:
        cursor.execute(
            "UPDATE teacher SET name = alias WHERE (name IS NULL OR name = '') AND alias IS NOT NULL AND alias != ''"
        )
        try:
            cursor.execute("ALTER TABLE teacher DROP COLUMN alias")
            columns.remove("alias")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not drop obsolete teacher.alias column: {e}")
    if "member_active" in columns:
        cursor.execute(
            "UPDATE teacher SET is_active = COALESCE(is_active, member_active) WHERE is_active IS NULL"
        )
        try:
            cursor.execute("ALTER TABLE teacher DROP COLUMN member_active")
            columns.remove("member_active")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not drop obsolete teacher.member_active column: {e}")
    if "uuid" in columns:
        cursor.execute(
            "UPDATE teacher SET wxid = uuid WHERE (wxid IS NULL OR wxid = '') AND uuid IS NOT NULL AND uuid != ''"
        )
        cursor.execute("DROP INDEX IF EXISTS idx_teacher_uuid")
        try:
            cursor.execute("ALTER TABLE teacher DROP COLUMN uuid")
            columns.remove("uuid")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not drop obsolete teacher.uuid column: {e}")
    if "priority" in columns:
        try:
            cursor.execute("ALTER TABLE teacher DROP COLUMN priority")
            columns.remove("priority")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not drop obsolete teacher.priority column: {e}")

    additions = {
        "course": "TEXT",
        "raw_pwd": "TEXT",
        "score": "INTEGER DEFAULT 50",
        "balance": "INTEGER DEFAULT 0",
        "model": "TEXT DEFAULT 'basic'",
        "ai_flag": "INTEGER DEFAULT 0",
        "birthday": "TEXT",
        "note": "TEXT",
        "identity_type": "TEXT DEFAULT 'teacher'",
    }
    for column, definition in additions.items():
        if column not in columns:
            cursor.execute(f"ALTER TABLE teacher ADD COLUMN {column} {definition}")

    cursor.execute("UPDATE teacher SET identity_type = 'teacher' WHERE identity_type IS NULL")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher_name ON teacher(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher_identity_type ON teacher(identity_type)")
    conn.commit()

    if should_close:
        conn.close()


def migrate_auth_teachers_to_moral() -> int:
    """把 auth.db.teacher 缺失的教师档案补齐到 moral.db.teacher。"""
    global _AUTH_MIGRATED
    if _AUTH_MIGRATED:
        return 0
    if not os.path.exists(AUTH_DB):
        return 0

    ensure_teacher_schema()
    auth_conn = sqlite3.connect(AUTH_DB)
    auth_conn.row_factory = sqlite3.Row
    moral_conn = sqlite3.connect(MORAL_DB)
    moral_conn.row_factory = sqlite3.Row
    ensure_teacher_schema(moral_conn)

    try:
        rows = auth_conn.execute("SELECT * FROM teacher").fetchall()
    except sqlite3.OperationalError:
        auth_conn.close()
        moral_conn.close()
        return 0

    migrated = 0
    for row in rows:
        teacher = dict(row)
        name = teacher.get("name")
        if not name:
            continue

        existing = moral_conn.execute(
            "SELECT teacher_id FROM teacher WHERE name = ? AND COALESCE(identity_type, 'teacher') = 'teacher'",
            (name,),
        ).fetchone()
        teacher_id = existing["teacher_id"] if existing else _teacher_id_from_name(name)

        moral_conn.execute(
            """
            INSERT INTO teacher
            (teacher_id, name, subject, course, password_hash, raw_pwd, role, level,
             is_active, notice_enabled, is_password_changed, identity_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'teacher')
            ON CONFLICT(teacher_id) DO UPDATE SET
                name = COALESCE(NULLIF(teacher.name, ''), excluded.name),
                subject = COALESCE(NULLIF(teacher.subject, ''), excluded.subject),
                course = COALESCE(NULLIF(teacher.course, ''), excluded.course),
                password_hash = COALESCE(NULLIF(teacher.password_hash, ''), excluded.password_hash),
                raw_pwd = COALESCE(NULLIF(teacher.raw_pwd, ''), excluded.raw_pwd),
                role = COALESCE(NULLIF(teacher.role, ''), excluded.role),
                level = COALESCE(teacher.level, excluded.level),
                is_active = COALESCE(teacher.is_active, excluded.is_active),
                notice_enabled = COALESCE(teacher.notice_enabled, excluded.notice_enabled),
                is_password_changed = COALESCE(teacher.is_password_changed, excluded.is_password_changed),
                identity_type = 'teacher',
                updated_at = datetime('now', 'localtime')
            """,
            (
                teacher_id,
                name,
                teacher.get("subject", ""),
                teacher.get("course", ""),
                teacher.get("pwd", ""),
                teacher.get("raw_pwd", ""),
                teacher.get("role", "teacher"),
                teacher.get("level", 10),
                teacher.get("active", 1),
                teacher.get("notice", 1),
                teacher.get("is_password_changed", 0),
            ),
        )
        migrated += 1

    moral_conn.commit()
    auth_conn.close()
    moral_conn.close()
    _AUTH_MIGRATED = True
    return migrated


def _teacher_select_sql(where: str = "", teacher_only: bool = True) -> str:
    identity_filter = "WHERE COALESCE(identity_type, 'teacher') = 'teacher'" if teacher_only else "WHERE 1 = 1"
    return f"""
        SELECT
            teacher_id,
            name,
            subject,
            COALESCE(course, '') AS course,
            COALESCE(notice_enabled, 1) AS notice,
            COALESCE(password_hash, '') AS pwd,
            COALESCE(role, 'teacher') AS role,
            COALESCE(level, 10) AS level,
            COALESCE(raw_pwd, '') AS raw_pwd,
            COALESCE(is_active, 1) AS active,
            COALESCE(is_password_changed, 0) AS is_password_changed,
            wxid,
            name AS alias,
            COALESCE(score, 50) AS score,
            COALESCE(balance, 0) AS balance,
            COALESCE(model, 'basic') AS model,
            COALESCE(ai_flag, 0) AS ai_flag,
            COALESCE(birthday, '') AS birthday,
            COALESCE(note, '') AS note,
            COALESCE(identity_type, 'teacher') AS identity_type,
            created_at,
            updated_at
        FROM teacher
        {identity_filter}
        {where}
    """


def get_all_teachers() -> List[Dict]:
    """获取所有教师列表"""
    with get_teacher_db() as db:
        return db.query_all(_teacher_select_sql("ORDER BY name"))


def get_all_teacher_records() -> List[Dict]:
    """获取 teacher 表全部身份记录。仅供管理员维护统一身份表。"""
    with get_teacher_db() as db:
        return db.query_all(
            _teacher_select_sql(
                "ORDER BY CASE COALESCE(identity_type, 'teacher') WHEN 'teacher' THEN 0 WHEN 'member' THEN 1 ELSE 2 END, name",
                teacher_only=False,
            )
        )


def get_teacher_by_name(name: str) -> Optional[Dict]:
    """根据姓名获取教师"""
    with get_teacher_db() as db:
        return db.query_one(_teacher_select_sql("AND name = ?"), (name,))


def get_teachers_by_role(role: str) -> List[Dict]:
    """根据角色获取教师列表（支持多角色匹配）"""
    with get_teacher_db() as db:
        return db.query_all(
            _teacher_select_sql("AND role LIKE ? AND is_active = 1 ORDER BY name"),
            (f"%{role}%",),
        )


def create_teacher_record(
    name: str,
    subject: str,
    course: str,
    password_hash: str,
    raw_pwd: str,
    role: str = "teacher",
    level: int = 5,
    notice: int = 1,
    active: int = 1,
    is_password_changed: int = 1,
) -> None:
    """创建教师账号。"""
    with get_teacher_db() as db:
        existing = db.query_one(
            _teacher_select_sql("AND name = ?"),
            (name,),
        )
        if existing:
            raise ValueError("教师已存在")

        db.execute(
            """
            INSERT INTO teacher
            (teacher_id, name, subject, course, notice_enabled, password_hash, raw_pwd,
             role, level, is_active, is_password_changed, identity_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'teacher')
            """,
            (
                _teacher_id_from_name(name),
                name,
                subject,
                course,
                notice,
                password_hash,
                raw_pwd,
                role,
                level,
                active,
                is_password_changed,
            ),
        )


def update_teacher_record(current_name: str, **kwargs) -> int:
    """按教师姓名更新教师字段。"""
    allowed = {
        "subject": "subject",
        "course": "course",
        "notice": "notice_enabled",
        "active": "is_active",
        "role": "role",
        "level": "level",
        "pwd": "password_hash",
        "password_hash": "password_hash",
        "raw_pwd": "raw_pwd",
        "is_password_changed": "is_password_changed",
        "wxid": "wxid",
        "name": "name",
        "score": "score",
        "balance": "balance",
        "model": "model",
        "ai_flag": "ai_flag",
        "birthday": "birthday",
        "note": "note",
        "identity_type": "identity_type",
    }
    updates = []
    params = []
    for key, value in kwargs.items():
        if key in allowed and value is not None:
            updates.append(f"{allowed[key]} = ?")
            params.append(value)

    if not updates:
        return 0

    all_records = bool(kwargs.pop("all_records", False))
    params.append(current_name)
    with get_teacher_db() as db:
        identity_condition = "" if all_records else "AND COALESCE(identity_type, 'teacher') = 'teacher'"
        rowcount = db.execute(
            f"""UPDATE teacher
            SET {', '.join(updates)}, updated_at = datetime('now', 'localtime')
            WHERE name = ? {identity_condition}""",
            tuple(params),
        )
        if rowcount == 0:
            raise ValueError("教师不存在")
        return rowcount


def delete_teacher_record(name: str, all_records: bool = False) -> int:
    """删除教师账号。为保留历史引用，实际改为非教师身份并禁用登录。"""
    with get_teacher_db() as db:
        identity_condition = "" if all_records else "AND COALESCE(identity_type, 'teacher') = 'teacher'"
        rowcount = db.execute(
            f"""UPDATE teacher
            SET is_active = 0,
                identity_type = 'deleted_teacher',
                updated_at = datetime('now', 'localtime')
            WHERE name = ? {identity_condition}""",
            (name,),
        )
        if rowcount == 0:
            raise ValueError("教师不存在")
        return rowcount


def get_teachers_dataframe():
    """获取教师数据（返回 DataFrame 格式，兼容旧课表代码）"""
    import pandas as pd
    teachers = get_all_teachers()
    if not teachers:
        return pd.DataFrame()
    df = pd.DataFrame(teachers)
    columns = [
        "name",
        "pwd",
        "role",
        "level",
        "subject",
        "course",
        "notice",
        "active",
        "raw_pwd",
        "is_password_changed",
    ]
    return df[[col for col in columns if col in df.columns]]
