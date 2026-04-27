# -*- coding: utf-8 -*-
"""
数据库路径配置

统一管理所有数据库路径，确保一致性
"""

import os

# lesson 目录
LESSON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据库目录
DATABASES_DIR = os.path.join(LESSON_DIR, "databases")

# 各数据库路径
AUTH_DB = os.path.join(DATABASES_DIR, "auth.db")
TASK_DB = os.path.join(DATABASES_DIR, "task.db")
MORAL_DB = os.path.join(DATABASES_DIR, "moral.db")
MEMBER_DB = os.path.join(DATABASES_DIR, "member.db")
LESSON_DB = os.path.join(DATABASES_DIR, "lesson.db")
HOMEWORK_DB = os.path.join(DATABASES_DIR, "homework.db")
DAILY_DB = os.path.join(DATABASES_DIR, "daily.db")
INOUT_DB = os.path.join(DATABASES_DIR, "inout.db")
MESSAGES_DB = os.path.join(DATABASES_DIR, "messages.db")
MAIN_DB = os.path.join(DATABASES_DIR, "main.db")
FILEGATHER_DB = os.path.join(DATABASES_DIR, "filegather.db")
NOTES_DB = os.path.join(DATABASES_DIR, "notes.db")
COLLEGES_DB = os.path.join(DATABASES_DIR, "colleges.db")
QUEUES_DB = os.path.join(DATABASES_DIR, "queues.db")

def get_db_path(db_name: str) -> str:
    """获取数据库路径"""
    return os.path.join(DATABASES_DIR, f"{db_name}.db")