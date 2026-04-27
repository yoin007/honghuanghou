# -*- coding: utf-8 -*-
"""
删除 student_daily_record 表的 UNIQUE 约束

SQLite 不支持 ALTER TABLE DROP CONSTRAINT，需要重建表。
此脚本保留所有现有数据。

执行方式：python scripts/remove_daily_record_unique_constraint.py
"""

import sqlite3
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.sqlite_moral_db import DB_PATH

def migrate():
    """执行迁移"""
    print(f"数据库路径: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print("数据库文件不存在，无需迁移")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='student_daily_record'
        """)
        if not cursor.fetchone():
            print("student_daily_record 表不存在，无需迁移")
            return

        # 2. 检查是否有 UNIQUE 约束
        cursor.execute("PRAGMA index_list(student_daily_record)")
        indexes = cursor.fetchall()
        print(f"现有索引: {indexes}")

        # 3. 创建临时表备份数据
        print("步骤1: 备份现有数据到临时表...")
        cursor.execute("""
            CREATE TABLE student_daily_record_backup AS
            SELECT * FROM student_daily_record
        """)

        # 4. 统计数据量
        cursor.execute("SELECT COUNT(*) FROM student_daily_record")
        count = cursor.fetchone()[0]
        print(f"现有记录数: {count}")

        # 5. 删除原表
        print("步骤2: 删除原表...")
        cursor.execute("DROP TABLE student_daily_record")

        # 6. 创建新表（无 UNIQUE 约束）
        print("步骤3: 创建新表（无 UNIQUE 约束）...")
        cursor.execute("""
            CREATE TABLE student_daily_record (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                event_id INTEGER NOT NULL,
                semester_id INTEGER NOT NULL,
                record_date TEXT NOT NULL,
                class_id INTEGER NOT NULL,
                grade_id INTEGER NOT NULL,
                score INTEGER,
                remark TEXT,
                recorder TEXT,
                is_deleted INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                FOREIGN KEY (student_id) REFERENCES student(student_id),
                FOREIGN KEY (event_id) REFERENCES daily_event_type(event_id),
                FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
                FOREIGN KEY (class_id) REFERENCES class(class_id),
                FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
            )
        """)

        # 7. 恢复数据
        print("步骤4: 恢复数据...")
        cursor.execute("""
            INSERT INTO student_daily_record
            SELECT * FROM student_daily_record_backup
        """)

        # 8. 创建索引（恢复性能）
        print("步骤5: 创建索引...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_daily_semester
            ON student_daily_record(student_id, semester_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_daily_date
            ON student_daily_record(record_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_student_daily_event
            ON student_daily_record(event_id)
        """)

        # 9. 删除备份表
        print("步骤6: 清理备份表...")
        cursor.execute("DROP TABLE student_daily_record_backup")

        # 10. 提交事务
        conn.commit()

        # 验证
        cursor.execute("SELECT COUNT(*) FROM student_daily_record")
        new_count = cursor.fetchone()[0]
        print(f"迁移后记录数: {new_count}")

        if new_count == count:
            print("✅ 迁移成功！已删除 UNIQUE 约束，数据完整保留")
        else:
            print(f"⚠️ 数据数量不一致: 原始 {count} -> 新 {new_count}")

        # 显示新表结构
        cursor.execute("PRAGMA table_info(student_daily_record)")
        print("\n新表结构:")
        for col in cursor.fetchall():
            print(f"  {col}")

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("student_daily_record 表 UNIQUE 约束删除迁移")
    print("=" * 60)
    migrate()