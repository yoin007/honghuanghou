"""
数据库迁移脚本：为 class 和 grade 表添加 leader_ids/leader_names 字段
支持多人班主任和多人年级主任功能
"""
import sqlite3


def ensure_sqlite_schema(conn: sqlite3.Connection):
    """
    确保数据库表结构包含 leader_ids 和 leader_names 字段

    Args:
        conn: SQLite 数据库连接对象
    """
    cursor = conn.cursor()

    # 检查 class 表是否有 leader_ids 字段
    cursor.execute("PRAGMA table_info(class)")
    class_columns = [col[1] for col in cursor.fetchall()]

    if 'leader_ids' not in class_columns:
        cursor.execute("ALTER TABLE class ADD COLUMN leader_ids TEXT DEFAULT ''")
        print("已为 class 表添加 leader_ids 字段")

    if 'leader_names' not in class_columns:
        cursor.execute("ALTER TABLE class ADD COLUMN leader_names TEXT DEFAULT ''")
        print("已为 class 表添加 leader_names 字段")

    # 检查 grade 表是否有 leader_ids 字段
    cursor.execute("PRAGMA table_info(grade)")
    grade_columns = [col[1] for col in cursor.fetchall()]

    if 'leader_ids' not in grade_columns:
        cursor.execute("ALTER TABLE grade ADD COLUMN leader_ids TEXT DEFAULT ''")
        print("已为 grade 表添加 leader_ids 字段")

    if 'leader_names' not in grade_columns:
        cursor.execute("ALTER TABLE grade ADD COLUMN leader_names TEXT DEFAULT ''")
        print("已为 grade 表添加 leader_names 字段")

    conn.commit()
    print("数据库迁移完成")
