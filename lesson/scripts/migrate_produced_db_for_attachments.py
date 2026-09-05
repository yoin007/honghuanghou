#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为旧生产数据库补齐当前系统所需的附件表结构。

当前系统依赖 `record_attachment` 表存储德育事件/教师待办的通用附件。
旧生产库（moral-produced.db）与新库相比只缺少该表及索引，本脚本幂等地创建它们。
"""

import os
import sqlite3
import sys


def migrate(db_path: str) -> None:
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"数据库不存在: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS record_attachment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_type TEXT NOT NULL,
            record_id INTEGER NOT NULL DEFAULT 0,
            uploader TEXT NOT NULL,
            original_name TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            thumbnail_path TEXT,
            file_size INTEGER NOT NULL,
            file_type TEXT NOT NULL,
            mime_type TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
        """
    )

    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_attachment_record ON record_attachment(record_type, record_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_attachment_uploader ON record_attachment(uploader)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_attachment_created ON record_attachment(created_at)"
    )

    conn.commit()
    conn.close()
    print(f"已补齐 record_attachment 表及索引: {db_path}")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "databases/moral-produced.db"
    migrate(db_path)
