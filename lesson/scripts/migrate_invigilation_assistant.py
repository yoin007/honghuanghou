#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监考副监字段迁移

给 invigilation.db.invigilation_slot 表新增三列：
- assistant_teacher_id
- assistant_teacher_name
- assistant_teacher_wxid
以及配套索引 idx_slot_assistant_teacher。

幂等：可重复执行；已存在的列/索引会被跳过。
"""

import os
import sqlite3
import sys

INVIGILATION_DB_REL = "databases/invigilation.db"


def get_db_path() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, INVIGILATION_DB_REL)


def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())


def index_exists(cursor: sqlite3.Cursor, index_name: str) -> bool:
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name = ?",
        (index_name,),
    )
    return cursor.fetchone() is not None


def migrate(db_path: str) -> None:
    if not os.path.exists(db_path):
        print(f"❌ 数据库不存在：{db_path}")
        sys.exit(1)

    print(f"→ 迁移目标：{db_path}")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        # 表必须存在
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='invigilation_slot'"
        )
        if not cur.fetchone():
            print("❌ invigilation_slot 表不存在，无法迁移")
            sys.exit(1)

        added = []
        for col in (
            "assistant_teacher_id",
            "assistant_teacher_name",
            "assistant_teacher_wxid",
        ):
            if column_exists(cur, "invigilation_slot", col):
                print(f"  跳过（已存在）：{col}")
                continue
            cur.execute(f"ALTER TABLE invigilation_slot ADD COLUMN {col} TEXT")
            added.append(col)
            print(f"  ✅ 新增列：{col}")

        if not index_exists(cur, "idx_slot_assistant_teacher"):
            cur.execute(
                "CREATE INDEX idx_slot_assistant_teacher "
                "ON invigilation_slot(assistant_teacher_id)"
            )
            print("  ✅ 新增索引：idx_slot_assistant_teacher")
        else:
            print("  跳过（已存在）：idx_slot_assistant_teacher")

        conn.commit()

        # 简单校验：老数据 assistant_teacher_id 应全部为 NULL
        cur.execute("SELECT COUNT(*) FROM invigilation_slot")
        total = cur.fetchone()[0]
        cur.execute(
            "SELECT COUNT(*) FROM invigilation_slot WHERE assistant_teacher_id IS NULL"
        )
        null_cnt = cur.fetchone()[0]
        print(f"→ 完成。总行数 {total}，assistant_teacher_id 为 NULL 的行 {null_cnt}")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate(get_db_path())
