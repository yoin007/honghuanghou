# -*- coding: utf-8 -*-
"""
预警处置记录表迁移脚本

新增 warning_handle 表，用于记录预警的处置过程。
幂等：表已存在则跳过。
"""

import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'databases', 'moral.db')

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS warning_handle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warning_id INTEGER NOT NULL,
    handle_type TEXT NOT NULL,
    handle_date TEXT,
    handler_name TEXT,
    handler_id TEXT,
    content TEXT,
    effect TEXT,
    follow_up_date TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (warning_id) REFERENCES warning_log(id) ON DELETE CASCADE
);
"""

INDEX_SQLS = [
    "CREATE INDEX IF NOT EXISTS idx_warning_handle_warning_id ON warning_handle(warning_id)",
    "CREATE INDEX IF NOT EXISTS idx_warning_handle_handler_id ON warning_handle(handler_id)",
    "CREATE INDEX IF NOT EXISTS idx_warning_handle_handle_date ON warning_handle(handle_date)",
]


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 启用外键
    cur.execute("PRAGMA foreign_keys = ON")

    # 建表
    cur.execute(CREATE_TABLE_SQL)
    print("✓ warning_handle 表已就绪")

    # 建索引
    for sql in INDEX_SQLS:
        cur.execute(sql)
    print("✓ 索引已就绪")

    # 统计
    cur.execute("SELECT COUNT(*) FROM warning_handle")
    count = cur.fetchone()[0]
    print(f"  当前处置记录数：{count}")

    conn.commit()
    conn.close()
    print("\n迁移完成。")


if __name__ == '__main__':
    migrate()
