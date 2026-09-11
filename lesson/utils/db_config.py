# -*- coding: utf-8 -*-
"""
数据库路径配置

统一管理所有数据库路径，确保一致性
"""

import os

# lesson 目录
LESSON_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _detect_demo_mode() -> bool:
    """从 lesson.yaml 读取 demo_mode 配置（演示模式开关）。

    配置读取失败时默认关闭，保证生产环境安全。
    """
    try:
        import yaml
        config_path = os.path.join(LESSON_DIR, "config", "lesson.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        val = cfg.get("demo_mode", False)
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        return str(val).strip().lower() in ("1", "true", "yes", "on")
    except Exception:
        return False


# 演示模式：lesson.yaml 中 demo_mode: true 时，所有数据库指向 databases/demo/
# 由 scripts/generate_demo_data.py 生成的全合成演示数据，用于录制教程，不含真实数据
DEMO_MODE = _detect_demo_mode()

# 数据库目录
if DEMO_MODE:
    DATABASES_DIR = os.path.join(LESSON_DIR, "databases", "demo")
else:
    DATABASES_DIR = os.path.join(LESSON_DIR, "databases")

# 各数据库路径
AUTH_DB = os.path.join(DATABASES_DIR, "auth.db")
TASK_DB = os.path.join(DATABASES_DIR, "task.db")
MORAL_DB = os.path.join(DATABASES_DIR, "moral.db")
MEMBER_DB = os.path.join(DATABASES_DIR, "member.db")
HOMEWORK_DB = os.path.join(DATABASES_DIR, "homework.db")
DAILY_DB = os.path.join(DATABASES_DIR, "daily.db")
INOUT_DB = os.path.join(DATABASES_DIR, "inout.db")
MESSAGES_DB = os.path.join(DATABASES_DIR, "messages.db")
FILEGATHER_DB = os.path.join(DATABASES_DIR, "filegather.db")
NOTES_DB = os.path.join(DATABASES_DIR, "notes.db")
COLLEGES_DB = os.path.join(DATABASES_DIR, "colleges.db")
QUEUES_DB = os.path.join(DATABASES_DIR, "queues.db")
INVIGILATION_DB = os.path.join(DATABASES_DIR, "invigilation.db")

def get_db_path(db_name: str) -> str:
    """获取数据库路径"""
    return os.path.join(DATABASES_DIR, f"{db_name}.db")
