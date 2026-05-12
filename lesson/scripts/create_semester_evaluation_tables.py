# -*- coding: utf-8 -*-
"""
学期末德育评价功能 - 数据库表创建脚本

仅创建 semester_evaluation_record 和 ai_model_config 两张新表

运行方式:
    python scripts/create_semester_evaluation_tables.py --sqlite
"""

import sys
import os
import sqlite3
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# SQLite 表定义
SQLite_TABLES = {
    # 学期末评价记录表
    "semester_evaluation_record": """
CREATE TABLE IF NOT EXISTS semester_evaluation_record (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    semester_id INTEGER NOT NULL,
    class_id INTEGER,
    grade_id INTEGER,

    -- 评价结果
    total_score DECIMAL(5,2),
    level TEXT,

    -- 分项得分(JSON)
    score_details TEXT,

    -- 统计详情(JSON)
    statistics TEXT,

    -- 关键事件(JSON)
    key_events TEXT,

    -- AI生成的总结(JSON)
    ai_summary TEXT,

    -- 元信息
    generated_by TEXT,
    generated_at TEXT,
    ai_generated_at TEXT,
    template_version TEXT DEFAULT 'v1.0',

    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE (student_id, semester_id)
);
""",
    # AI模型配置表
    "ai_model_config": """
CREATE TABLE IF NOT EXISTS ai_model_config (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    current_model TEXT NOT NULL,
    description TEXT,
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_by TEXT
);
""",
}

# SQLite 初始数据
SQLite_INITIAL_DATA = [
    # AI模型配置初始数据
    """INSERT OR IGNORE INTO ai_model_config (module_name, display_name, current_model, description) VALUES
    ('ai_diagnosis', 'AI诊疗', 'kimi-k2.5', 'AI诊疗结案报告生成'),
    ('profile_generate', '学生画像生成', 'kimi-k2.5', '学生德育画像生成'),
    ('remind_ai', '定时提醒', 'deepseek-chat', '定时任务AI提醒'),
    ('bailian_general', '百炼通用', 'kimi-k2.5', '百炼通用模型调用'),
    ('semester_evaluation', '学期末评价生成', 'kimi-k2.5', '学期末德育评价总结生成');""",
]


def create_tables(db_path: str = None):
    """创建SQLite表"""
    from utils.sqlite_moral_db import get_moral_db_path

    db_path = db_path or get_moral_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        # 创建表
        for table_name, sql in SQLite_TABLES.items():
            conn.execute(sql)
            logger.info(f"Created SQLite table: {table_name}")

        # 插入初始数据
        for sql in SQLite_INITIAL_DATA:
            conn.execute(sql)
        conn.commit()
        logger.info("Initial data inserted")

        # 验证
        for table_name in SQLite_TABLES.keys():
            count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            logger.info(f"Table '{table_name}': {count} records")

    finally:
        conn.close()

    logger.info(f"Database setup completed at: {db_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create semester evaluation tables")
    parser.add_argument("--sqlite", action="store_true", help="Use SQLite")
    parser.add_argument("--db-path", type=str, help="SQLite database path")
    args = parser.parse_args()

    if args.sqlite:
        create_tables(args.db_path)
    else:
        print("Use --sqlite flag for SQLite database")
        sys.exit(1)


if __name__ == "__main__":
    main()