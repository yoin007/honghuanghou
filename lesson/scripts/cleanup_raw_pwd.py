# -*- coding: utf-8 -*-
"""
raw_pwd 清理脚本

Batch 8-9: 安全清理已改密账号的 raw_pwd 明文密码
- 默认 dry-run，不修改数据库
- 只清理 is_password_changed=1 的 raw_pwd
- 不清理 is_password_changed=0 的 raw_pwd（历史兼容）
- 执行前必须备份
- 不输出真实明文值
- --apply 必须配合 --yes 确认（防止误操作）

用法：
    # dry-run（默认，无需确认）
    python lesson/scripts/cleanup_raw_pwd.py

    # 查看可清理记录
    python lesson/scripts/cleanup_raw_pwd.py --db-path /path/to/moral.db

    # 真正执行清理（必须双重确认）
    python lesson/scripts/cleanup_raw_pwd.py --apply --yes

    # 自定义备份目录
    python lesson/scripts/cleanup_raw_pwd.py --apply --yes --backup-dir /path/to/backups
"""
import sqlite3
import os
import shlex
import shutil
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_config import MORAL_DB as DEFAULT_MORAL_DB


def get_cleanup_candidates(db_path: str) -> Dict[str, Any]:
    """
    获取可清理的 raw_pwd 记录候选（只读查询）

    Args:
        db_path: 数据库路径

    Returns:
        统计结果字典：
        - db_exists: 数据库是否存在
        - table_exists: teacher 表是否存在
        - has_required_columns: 是否有 raw_pwd 和 is_password_changed 字段
        - has_updated_at: 是否有 updated_at 字段
        - teacher_total: 教师总数
        - changed_with_raw_pwd: is_password_changed=1 且 raw_pwd 非空（可清理）
        - unchanged_with_raw_pwd: is_password_changed=0 且 raw_pwd 非空（不清理）
        - raw_pwd_non_empty: raw_pwd 非空总数
        - cleanup_candidates: 可清理记录的 teacher_id 列表（不含 raw_pwd 明文）
    """
    result = {
        "db_exists": False,
        "table_exists": False,
        "has_required_columns": False,
        "has_updated_at": False,
        "teacher_total": 0,
        "changed_with_raw_pwd": 0,
        "unchanged_with_raw_pwd": 0,
        "raw_pwd_non_empty": 0,
        "cleanup_candidates": [],
    }

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

            # 检查必要字段是否存在
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(teacher)").fetchall()
            }
            required_columns = {"raw_pwd", "is_password_changed"}
            if not required_columns.issubset(columns):
                result["error"] = f"teacher 表缺少审计字段: {', '.join(sorted(required_columns - columns))}"
                return result

            result["has_required_columns"] = True
            result["has_updated_at"] = "updated_at" in columns

            # 统计总数
            cursor = conn.execute("SELECT COUNT(*) FROM teacher")
            result["teacher_total"] = cursor.fetchone()[0]

            # 统计 raw_pwd 非空数量
            cursor = conn.execute(
                "SELECT COUNT(*) FROM teacher WHERE raw_pwd IS NOT NULL AND raw_pwd != ''"
            )
            result["raw_pwd_non_empty"] = cursor.fetchone()[0]

            # 统计可清理数量（is_password_changed=1）
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM teacher
                WHERE is_password_changed = 1
                AND raw_pwd IS NOT NULL
                AND raw_pwd != ''
                """
            )
            result["changed_with_raw_pwd"] = cursor.fetchone()[0]

            # 统计不可清理数量（is_password_changed=0）
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM teacher
                WHERE is_password_changed = 0
                AND raw_pwd IS NOT NULL
                AND raw_pwd != ''
                """
            )
            result["unchanged_with_raw_pwd"] = cursor.fetchone()[0]

            # 获取可清理候选的 teacher_id（不含明文）
            cursor = conn.execute(
                """
                SELECT teacher_id FROM teacher
                WHERE is_password_changed = 1
                AND raw_pwd IS NOT NULL
                AND raw_pwd != ''
                """
            )
            result["cleanup_candidates"] = [row[0] for row in cursor.fetchall()]

    except Exception as e:
        result["error"] = str(e)

    return result


def create_backup(db_path: str, backup_dir: Optional[str] = None) -> str:
    """
    创建数据库备份

    Args:
        db_path: 数据库路径
        backup_dir: 备份目录（默认为数据库同目录）

    Returns:
        备份文件路径

    Raises:
        ValueError: 数据库不存在
        OSError: 备份失败
    """
    if not os.path.exists(db_path):
        raise ValueError(f"数据库不存在: {db_path}")

    # 确定备份目录
    if backup_dir is None:
        backup_dir = os.path.dirname(db_path)

    # 确保备份目录存在
    os.makedirs(backup_dir, exist_ok=True)

    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_name = os.path.basename(db_path)
    backup_name = f"{db_name}.raw_pwd_backup.{timestamp}"
    backup_path = os.path.join(backup_dir, backup_name)
    counter = 1
    while os.path.exists(backup_path):
        backup_path = os.path.join(backup_dir, f"{backup_name}.{counter}")
        counter += 1

    # 复制数据库文件
    shutil.copy2(db_path, backup_path)

    return backup_path


def build_recovery_command(backup_path: str, db_path: str) -> str:
    """
    构建恢复命令

    Args:
        backup_path: 备份文件路径
        db_path: 原数据库路径

    Returns:
        恢复命令字符串（cp 命令）
    """
    return f"cp {shlex.quote(backup_path)} {shlex.quote(db_path)}"


def cleanup_changed_raw_pwd(
    db_path: str,
    apply: bool = False,
    backup_dir: Optional[str] = None,
    confirm: bool = False
) -> Dict[str, Any]:
    """
    清理已改密账号的 raw_pwd

    Args:
        db_path: 数据库路径
        apply: 是否真正执行清理（False 为 dry-run）
        backup_dir: 备份目录
        confirm: 是否已确认执行（apply=True 时必须 confirm=True）

    Returns:
        结果字典：
        - mode: 'dry-run' 或 'apply-needs-confirm' 或 'apply'
        - db_exists: 数据库是否存在
        - candidates_count: 可清理候选数量
        - cleanup_count: 实际清理数量（apply 时）
        - backup_path: 备份文件路径（apply 时）
        - recovery_command: 恢复命令（apply 时）
        - remaining_changed_with_raw_pwd: 清理后剩余数量（apply 时）
        - unchanged_with_raw_pwd: 未清理数量（is_password_changed=0）
        - teacher_ids_cleaned: 清理的 teacher_id 列表（apply 时）
    """
    result = {
        "mode": "dry-run" if not apply else ("apply" if confirm else "apply-needs-confirm"),
        "db_exists": False,
        "candidates_count": 0,
        "cleanup_count": 0,
        "backup_path": None,
        "recovery_command": None,
        "remaining_changed_with_raw_pwd": 0,
        "unchanged_with_raw_pwd": 0,
        "teacher_ids_cleaned": [],
    }

    # 获取候选统计
    candidates = get_cleanup_candidates(db_path)

    if not candidates["db_exists"]:
        result["error"] = "数据库不存在"
        return result

    if not candidates["table_exists"]:
        result["error"] = "teacher 表不存在"
        return result

    if not candidates["has_required_columns"]:
        result["error"] = candidates.get("error", "缺少必要字段")
        return result

    result["db_exists"] = True
    result["candidates_count"] = candidates["changed_with_raw_pwd"]
    result["unchanged_with_raw_pwd"] = candidates["unchanged_with_raw_pwd"]

    # dry-run：只返回统计，不执行清理
    if not apply:
        result["cleanup_candidates"] = candidates["cleanup_candidates"]
        return result

    # apply：需要确认
    if not confirm:
        result["needs_confirm"] = True
        result["confirm_hint"] = "请添加 --yes 参数确认执行清理"
        return result

    # apply + confirm：执行清理
    if candidates["changed_with_raw_pwd"] == 0:
        # 无需清理
        return result

    # 创建备份
    try:
        backup_path = create_backup(db_path, backup_dir)
        result["backup_path"] = backup_path
        result["recovery_command"] = build_recovery_command(backup_path, db_path)
    except Exception as e:
        result["error"] = f"备份失败: {str(e)}"
        return result

    # 执行清理
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # 获取待清理的 teacher_id
            teacher_ids = candidates["cleanup_candidates"]
            result["teacher_ids_cleaned"] = teacher_ids

            if candidates.get("has_updated_at"):
                cursor.execute(
                    """
                    UPDATE teacher
                    SET raw_pwd = NULL,
                        updated_at = datetime('now', 'localtime')
                    WHERE is_password_changed = 1
                    AND raw_pwd IS NOT NULL
                    AND raw_pwd != ''
                    """
                )
            else:
                cursor.execute(
                    """
                    UPDATE teacher
                    SET raw_pwd = NULL
                    WHERE is_password_changed = 1
                    AND raw_pwd IS NOT NULL
                    AND raw_pwd != ''
                    """
                )

            result["cleanup_count"] = cursor.rowcount
            conn.commit()

            # 验证清理结果
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM teacher
                WHERE is_password_changed = 1
                AND raw_pwd IS NOT NULL
                AND raw_pwd != ''
                """
            )
            result["remaining_changed_with_raw_pwd"] = cursor.fetchone()[0]

    except Exception as e:
        result["error"] = f"清理失败: {str(e)}"
        # 如果清理失败，提示恢复备份
        if result["backup_path"]:
            result["recovery_hint"] = f"可恢复备份: {build_recovery_command(result['backup_path'], db_path)}"

    return result


def print_cleanup_report(result: Dict[str, Any]) -> None:
    """打印清理报告"""
    print("=" * 60)
    print("raw_pwd 清理报告")
    print("=" * 60)
    print(f"模式: {result['mode']}")
    print()

    if "error" in result:
        print(f"⚠️  错误: {result['error']}")
        if "recovery_hint" in result:
            print(f"   {result['recovery_hint']}")
        return

    print(f"数据库状态: 存在 ✅")
    print()
    print("-" * 40)
    print("统计结果:")
    print("-" * 40)
    print(f"可清理候选数量:        {result['candidates_count']}")
    print(f"不可清理数量 (changed=0): {result['unchanged_with_raw_pwd']}")
    print()

    if result["mode"] == "dry-run":
        print("🔍 dry-run 模式：以下记录可清理（不显示明文）")
        if result.get("cleanup_candidates"):
            for teacher_id in result["cleanup_candidates"][:10]:
                print(f"   - {teacher_id}")
            if len(result["cleanup_candidates"]) > 10:
                print(f"   ... 还有 {len(result['cleanup_candidates']) - 10} 条")
        print()
        print("⚠️  dry-run 不修改数据库")
        print("   如需执行清理，请使用: --apply --yes")

    elif result["mode"] == "apply-needs-confirm":
        print("⚠️  apply 模式需要确认")
        print(f"   可清理记录数: {result['candidates_count']}")
        print()
        print("⚠️  未添加 --yes 参数，不执行清理")
        print("   如需执行，请添加: --yes")

    else:
        print("-" * 40)
        print("执行结果:")
        print("-" * 40)
        if result["backup_path"]:
            print(f"备份路径:              {result['backup_path']}")
        if result.get("recovery_command"):
            print(f"恢复命令:              {result['recovery_command']}")
        print(f"实际清理数量:          {result['cleanup_count']}")
        print(f"清理后剩余可清理数量:  {result['remaining_changed_with_raw_pwd']}")
        print(f"未清理数量 (changed=0): {result['unchanged_with_raw_pwd']}")
        print()

        if result["cleanup_count"] > 0:
            print("✅ 清理完成")
            print(f"   已清理 teacher_id: {len(result['teacher_ids_cleaned'])} 条")
            if result.get("recovery_command"):
                print()
                print("如需恢复，执行:")
                print(f"   {result['recovery_command']}")
        else:
            print("✅ 无需清理")

    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="raw_pwd 清理脚本")
    parser.add_argument(
        "--db-path",
        default=DEFAULT_MORAL_DB,
        help="数据库路径（默认 lesson/databases/moral.db）"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正执行清理（默认 dry-run，必须配合 --yes）"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="确认执行清理（--apply 时必须）"
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="备份目录（默认数据库同目录）"
    )

    args = parser.parse_args()

    result = cleanup_changed_raw_pwd(
        args.db_path,
        apply=args.apply,
        backup_dir=args.backup_dir,
        confirm=args.yes
    )

    print_cleanup_report(result)
