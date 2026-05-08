# -*- coding: utf-8 -*-
"""
raw_pwd 存量审计脚本

Batch 7 第一阶段：统计 teacher 表中 raw_pwd 明文密码存量
- 只读，不修改数据库
- 不输出真实明文值

用法：
    python lesson/scripts/audit_raw_pwd.py
    或
    python -m pytest lesson/tests/test_audit_raw_pwd.py -q
"""
import sqlite3
import os
import sys
from typing import Dict, Any

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_config import MORAL_DB


def audit_raw_pwd_status(db_path: str = MORAL_DB) -> Dict[str, Any]:
    """
    审计 teacher 表中 raw_pwd 字段存量

    Args:
        db_path: 数据库路径（默认 moral.db）

    Returns:
        统计结果字典，包含：
        - teacher_total: 教师总数
        - raw_pwd_non_empty: raw_pwd 非空数量
        - changed_with_raw_pwd: is_password_changed=1 且 raw_pwd 非空（应清理）
        - unchanged_with_raw_pwd: is_password_changed=0 且 raw_pwd 非空（保留兼容）
        - changed_without_raw_pwd: is_password_changed=1 且 raw_pwd 为空（正常）
        - unchanged_without_raw_pwd: is_password_changed=0 且 raw_pwd 为空（正常）
        - db_exists: 数据库是否存在
        - table_exists: teacher 表是否存在
        - has_required_columns: 审计所需字段是否存在
    """
    result = {
        "teacher_total": 0,
        "raw_pwd_non_empty": 0,
        "changed_with_raw_pwd": 0,
        "unchanged_with_raw_pwd": 0,
        "changed_without_raw_pwd": 0,
        "unchanged_without_raw_pwd": 0,
        "db_exists": False,
        "table_exists": False,
        "has_required_columns": False,
    }

    # 检查数据库是否存在
    if not os.path.exists(db_path):
        return result

    result["db_exists"] = True

    try:
        with sqlite3.connect(db_path) as conn:
            # 检查 teacher 表是否存在
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='teacher'"
            )
            if cursor.fetchone() is None:
                return result

            result["table_exists"] = True

            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(teacher)").fetchall()
            }
            required_columns = {"raw_pwd", "is_password_changed"}
            missing_columns = sorted(required_columns - columns)
            if missing_columns:
                result["error"] = f"teacher 表缺少审计字段: {', '.join(missing_columns)}"
                return result

            result["has_required_columns"] = True

            # 统计总数
            cursor = conn.execute("SELECT COUNT(*) FROM teacher")
            result["teacher_total"] = cursor.fetchone()[0]

            # 统计 raw_pwd 非空数量
            cursor = conn.execute(
                "SELECT COUNT(*) FROM teacher WHERE raw_pwd IS NOT NULL AND raw_pwd != ''"
            )
            result["raw_pwd_non_empty"] = cursor.fetchone()[0]

            # 统计 is_password_changed=1 且 raw_pwd 非空（应该清理）
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM teacher
                WHERE is_password_changed = 1
                AND raw_pwd IS NOT NULL
                AND raw_pwd != ''
                """
            )
            result["changed_with_raw_pwd"] = cursor.fetchone()[0]

            # 统计 is_password_changed=0 且 raw_pwd 非空（历史兼容，保留）
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM teacher
                WHERE is_password_changed = 0
                AND raw_pwd IS NOT NULL
                AND raw_pwd != ''
                """
            )
            result["unchanged_with_raw_pwd"] = cursor.fetchone()[0]

            # 统计 is_password_changed=1 且 raw_pwd 为空（正常）
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM teacher
                WHERE is_password_changed = 1
                AND (raw_pwd IS NULL OR raw_pwd = '')
                """
            )
            result["changed_without_raw_pwd"] = cursor.fetchone()[0]

            # 统计 is_password_changed=0 且 raw_pwd 为空（正常）
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM teacher
                WHERE is_password_changed = 0
                AND (raw_pwd IS NULL OR raw_pwd = '')
                """
            )
            result["unchanged_without_raw_pwd"] = cursor.fetchone()[0]

    except Exception as e:
        # 异常时返回部分结果，不抛错
        result["error"] = str(e)

    return result


def print_audit_report(result: Dict[str, Any]) -> None:
    """打印审计报告"""
    print("=" * 60)
    print("raw_pwd 存量审计报告")
    print("=" * 60)

    if not result["db_exists"]:
        print("⚠️  数据库不存在: moral.db")
        return

    if not result["table_exists"]:
        print("⚠️  teacher 表不存在")
        return

    if not result.get("has_required_columns", False):
        print(f"⚠️  {result.get('error', 'teacher 表缺少 raw_pwd 审计字段')}")
        return

    print(f"数据库状态: 存在 ✅")
    print(f"teacher 表: 存在 ✅")
    print()
    print("-" * 40)
    print("统计结果:")
    print("-" * 40)
    print(f"教师总数:                    {result['teacher_total']}")
    print(f"raw_pwd 非空数量:            {result['raw_pwd_non_empty']}")
    print()
    print("按 is_password_changed 分组:")
    print(f"  changed=1 且 raw_pwd 非空: {result['changed_with_raw_pwd']} (应清理)")
    print(f"  changed=0 且 raw_pwd 非空: {result['unchanged_with_raw_pwd']} (保留兼容)")
    print(f"  changed=1 且 raw_pwd 为空: {result['changed_without_raw_pwd']} (正常)")
    print(f"  changed=0 且 raw_pwd 为空: {result['unchanged_without_raw_pwd']} (正常)")
    print()
    print("-" * 40)
    print("风险评估:")
    print("-" * 40)

    if result['changed_with_raw_pwd'] > 0:
        print(f"⚠️  存在 {result['changed_with_raw_pwd']} 条已改密账号仍有明文密码")
        print("   建议: 清理这些记录的 raw_pwd 字段")

    if result['unchanged_with_raw_pwd'] > 0:
        print(f"⚠️  存在 {result['unchanged_with_raw_pwd']} 条未改密账号使用明文验证")
        print("   建议: 保留兼容，但应逐步推动用户改密")

    if result['raw_pwd_non_empty'] == 0:
        print("✅ 无 raw_pwd 明文存储，安全状态良好")

    print("=" * 60)


if __name__ == "__main__":
    result = audit_raw_pwd_status()
    print_audit_report(result)
