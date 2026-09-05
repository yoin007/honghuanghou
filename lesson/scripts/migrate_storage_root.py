#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件收集/附件存储根目录迁移脚本

把物理文件从旧的 moral_config 配置根目录迁移到 lesson.yaml 中配置的跨平台根目录。

- 幂等：重复执行安全
- 不覆盖：目标已存在则跳过
- 正确处理 macOS 下 Windows 路径字面量产生的 <lesson>/D:\storage\filegather 目录

使用方式（在 lesson 目录下，用运行后端的 Python）：
    python scripts/migrate_storage_root.py

迁移完成后，可手动删除 moral_config 表中 filegather_storage_dir 这一行，
因为运行时已不再读取它。
"""

import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.paths import get_filegather_storage_root

SUBDIRS = ["attachments", "images", "uploads", "done"]
MORAL_DB = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "databases",
    "moral.db",
)


def _default_root() -> str:
    """旧代码中的默认存储根目录（<lesson>/storage/filegather）。"""
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "storage",
        "filegather",
    )


def _get_legacy_storage_root() -> str:
    """按旧代码规则解析 moral_config.filegather_storage_dir。"""
    if not os.path.exists(MORAL_DB):
        return _default_root()

    conn = sqlite3.connect(MORAL_DB)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT config_value FROM moral_config WHERE config_key = 'filegather_storage_dir'"
    )
    row = cursor.fetchone()
    conn.close()

    legacy = row[0] if row else ""
    if not legacy:
        return _default_root()

    # 旧代码直接把配置值当根目录；Windows 绝对路径在 Unix 上会被当成相对路径，
    # 从而生成 <lesson>/D:\storage\filegather 这种异常目录。
    if os.path.isabs(legacy):
        return legacy

    lesson_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(lesson_dir, legacy)


def _iter_source_files(root: str):
    for subdir in SUBDIRS:
        src_dir = os.path.join(root, subdir)
        if not os.path.isdir(src_dir):
            continue
        for dirpath, _, filenames in os.walk(src_dir):
            for filename in filenames:
                rel = os.path.relpath(
                    os.path.join(dirpath, filename), src_dir
                )
                yield subdir, rel, os.path.join(dirpath, filename)


def main():
    old_root = os.path.normpath(_get_legacy_storage_root())
    new_root = os.path.normpath(get_filegather_storage_root())

    print(f"旧存储根目录: {old_root}")
    print(f"新存储根目录: {new_root}")

    if old_root == new_root:
        print("旧目录与新目录相同，无需迁移")
        return

    moved = 0
    skipped = 0
    errors = []

    for subdir, rel_path, src_abs in _iter_source_files(old_root):
        dst_abs = os.path.join(new_root, subdir, rel_path)
        if os.path.exists(dst_abs):
            print(f"[skip] 目标已存在: {dst_abs}")
            skipped += 1
            continue
        try:
            os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
            shutil.move(src_abs, dst_abs)
            print(f"[move] {src_abs} -> {dst_abs}")
            moved += 1
        except Exception as exc:
            print(f"[error] {src_abs}: {exc}")
            errors.append((src_abs, str(exc)))

    print(
        f"\n迁移完成: 移动 {moved} 个文件, 跳过 {skipped} 个, 失败 {len(errors)} 个"
    )
    if errors:
        print("失败列表:")
        for src, err in errors:
            print(f"  {src}: {err}")
    else:
        print(
            "\n建议：迁移成功后，可手动删除 moral_config 表中 "
            "config_key='filegather_storage_dir' 的记录，避免 stale 数据误导。"
        )


if __name__ == "__main__":
    main()
