# -*- coding: utf-8 -*-
"""
监考安排数据库表创建脚本

创建 invigilation.db 及核心表：
- exam_project: 考试项目
- invigilation_slot: 监考安排
- invigilation_notification_log: 通知日志
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "databases", "invigilation.db")


def create_tables():
    """创建监考安排数据库表"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")

    cursor = conn.cursor()

    # 1. 考试项目表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_project (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            school_year TEXT,
            semester TEXT,
            start_date TEXT,
            end_date TEXT,
            grade_ids TEXT,
            status TEXT DEFAULT 'draft',
            version_no INTEGER DEFAULT 0,
            first_saved_at TEXT,
            notified_at TEXT,
            created_by TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 2. 监考安排表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invigilation_slot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            grade_id INTEGER NOT NULL,
            grade_name TEXT,
            exam_date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            subject TEXT NOT NULL,
            room_name TEXT NOT NULL,
            room_order INTEGER DEFAULT 0,
            teacher_id TEXT,
            teacher_name TEXT,
            teacher_wxid TEXT,
            source TEXT DEFAULT 'manual',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (project_id) REFERENCES exam_project(id)
        )
    """)

    # 唯一索引：同一项目、年级、日期、开始时间、考场不能重复
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_slot_unique
        ON invigilation_slot(project_id, grade_id, exam_date, start_time, room_name)
    """)

    # 查询索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_slot_project
        ON invigilation_slot(project_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_slot_grade
        ON invigilation_slot(project_id, grade_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_slot_teacher
        ON invigilation_slot(teacher_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_slot_date
        ON invigilation_slot(exam_date)
    """)

    # 3. 通知日志表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invigilation_notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            version_no INTEGER NOT NULL,
            teacher_name TEXT,
            teacher_id TEXT,
            receiver TEXT,
            message TEXT,
            change_type TEXT,
            slots_json TEXT,
            sent_status TEXT DEFAULT 'pending',
            error_message TEXT,
            sent_at TEXT,
            FOREIGN KEY (project_id) REFERENCES exam_project(id)
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_notification_project
        ON invigilation_notification_log(project_id)
    """)

    conn.commit()
    conn.close()

    print(f"✅ 监考安排数据库创建成功: {DB_PATH}")
    return DB_PATH


def init_test_data():
    """初始化测试数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 创建测试考试项目
    cursor.execute("""
        INSERT INTO exam_project (name, school_year, semester, start_date, end_date, grade_ids, status, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "2026春季期中考试",
        "2025-2026",
        "下学期",
        "2026-05-10",
        "2026-05-12",
        json.dumps([1, 2, 3]),
        "draft",
        "admin"
    ))

    project_id = cursor.lastrowid

    # 创建测试监考安排
    test_slots = [
        (project_id, 1, "高一", "2026-05-10", "08:00", "10:00", "语文", "第1考场", 1, "T_张三", "张三", None),
        (project_id, 1, "高一", "2026-05-10", "08:00", "10:00", "语文", "第2考场", 2, "T_李四", "李四", None),
        (project_id, 1, "高一", "2026-05-10", "10:20", "12:00", "数学", "第1考场", 1, "T_王五", "王五", None),
        (project_id, 2, "高二", "2026-05-10", "08:00", "10:00", "语文", "第1考场", 1, "T_赵六", "赵六", None),
    ]

    for slot in test_slots:
        cursor.execute("""
            INSERT INTO invigilation_slot
            (project_id, grade_id, grade_name, exam_date, start_time, end_time, subject, room_name, room_order, teacher_id, teacher_name, teacher_wxid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, slot)

    conn.commit()
    conn.close()

    print(f"✅ 测试数据初始化成功: 项目ID={project_id}")


if __name__ == "__main__":
    create_tables()
    init_test_data()