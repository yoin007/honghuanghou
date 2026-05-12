# -*- coding: utf-8 -*-
"""
数据库完整性检查工具

在应用启动时检查所有必要表是否存在，字段是否完整
"""

import os
import logging
from typing import Dict, List, Tuple
from models.datas_api.repositories.sqlite_base import get_sqlite_connection

logger = logging.getLogger(__name__)

# 数据库目录（lesson/databases）
DATABASES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "databases")

# 必须存在的表
REQUIRED_TABLES = {
    "moral.db": [
        "teacher", "student", "school_year", "semester", "grade", "class",
        "role", "grade_level_config", "moral_config", "moral_operation_log",
        "student_daily_record", "student_school_record", "grade_moral_task",
        "student_task_finish", "punishment_record", "collective_event",
        "api_permission_config", "api_permission_module"
    ],
    "member.db": ["permission"],
    "invigilation.db": ["exam_project", "invigilation_slot"],
    "task.db": ["tasks"],
}

# 必须存在的字段（关键字段）
REQUIRED_COLUMNS = {
    "moral.db": {
        "teacher": ["teacher_id", "name", "role", "password_hash", "is_active"],
        "student": ["student_id", "name", "class_id", "grade_id", "status"],
        "grade_moral_task": ["task_id", "grade_id", "task_name", "score", "task_type", "can_carryover", "is_active"],
        "student_task_finish": ["id", "student_id", "task_id", "year_id", "status", "current_score", "carryover_count"],
        "school_year": ["year_id", "year_name"],
        "semester": ["semester_id", "semester_name", "year_id"],
        "grade": ["grade_id", "grade_name", "enrollment_year"],
        "class": ["class_id", "class_name", "grade_id"],
    },
}


def check_database_integrity_on_startup() -> Dict:
    """
    启动时检查数据库完整性

    Returns:
        Dict: 检查结果 {
            "status": "ok" / "warning" / "error",
            "missing_tables": [...],
            "missing_columns": [...],
            "error_databases": [...]
        }
    """
    result = {
        "status": "ok",
        "missing_tables": [],
        "missing_columns": [],
        "error_databases": []
    }

    for db_name, required_tables in REQUIRED_TABLES.items():
        db_path = os.path.join(DATABASES_DIR, db_name)

        if not os.path.exists(db_path):
            logger.warning(f"数据库文件不存在: {db_name}")
            for table in required_tables:
                result["missing_tables"].append({
                    "database": db_name,
                    "table": table,
                    "reason": "数据库文件不存在"
                })
            result["status"] = "error"
            continue

        try:
            conn = get_sqlite_connection(db_path)
            cursor = conn.cursor()

            # 获取现有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = set(row[0] for row in cursor.fetchall())

            # 检查必要表
            for table in required_tables:
                if table not in existing_tables:
                    result["missing_tables"].append({
                        "database": db_name,
                        "table": table,
                        "reason": "表不存在"
                    })
                    result["status"] = "warning"
                else:
                    # 检查字段完整性
                    expected_columns = REQUIRED_COLUMNS.get(db_name, {}).get(table, [])
                    if expected_columns:
                        missing_cols = check_table_columns(cursor, table, expected_columns)
                        if missing_cols:
                            result["missing_columns"].append({
                                "database": db_name,
                                "table": table,
                                "missing": missing_cols
                            })
                            result["status"] = "warning"

            conn.close()

        except Exception as e:
            logger.error(f"检查数据库 {db_name} 失败: {e}")
            result["error_databases"].append({
                "database": db_name,
                "reason": str(e)
            })
            result["status"] = "error"

    # 输出检查结果
    if result["status"] == "ok":
        logger.info("✅ 数据库完整性检查通过")
    else:
        if result["missing_tables"]:
            logger.warning(f"⚠️ 缺失表: {len(result['missing_tables'])} 个")
            for item in result["missing_tables"][:5]:
                logger.warning(f"   - {item['database']}.{item['table']}: {item['reason']}")
        if result["missing_columns"]:
            logger.warning(f"⚠️ 缺失字段: {len(result['missing_columns'])} 个表")
            for item in result["missing_columns"][:5]:
                logger.warning(f"   - {item['database']}.{item['table']}: 缺失 {item['missing']}")
        if result["error_databases"]:
            logger.error(f"❌ 数据库错误: {len(result['error_databases'])} 个")
            for item in result["error_databases"]:
                logger.error(f"   - {item['database']}: {item['reason']}")

    return result


def check_table_columns(cursor, table_name: str, expected_columns: List[str]) -> List[str]:
    """
    检查表的字段完整性

    Args:
        cursor: SQLite cursor
        table_name: 表名
        expected_columns: 预期字段列表

    Returns:
        List[str]: 缺失的字段列表
    """
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        missing = [col for col in expected_columns if col not in existing_columns]
        return missing
    except Exception as e:
        logger.error(f"检查表 {table_name} 字段失败: {e}")
        return expected_columns  # 返回全部预期字段作为缺失


def get_all_table_columns(db_path: str, table_name: str) -> List[str]:
    """
    获取指定表的所有字段名

    Args:
        db_path: 数据库路径
        table_name: 表名

    Returns:
        List[str]: 字段名列表
    """
    conn = get_sqlite_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    return columns
