#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FileGather 路径验证工具

快速测试路径拼接逻辑，无需启动服务器。
"""

import os
import sys

# 添加 lesson 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.filegather_db import FileGatherDB


def test_path_resolution(file_id: int = None):
    """测试路径解析"""
    db = FileGatherDB()

    print("=" * 60)
    print("FileGather 路径验证")
    print("=" * 60)

    print(f"\n配置信息:")
    print(f"  storage_root: {db.storage_root}")
    print(f"  uploads_dir:  {db.uploads_dir}")
    print(f"  done_dir:     {db.done_dir}")

    if file_id:
        file_info = db.get_file_by_id(file_id)
        if file_info:
            print(f"\n文件 ID {file_id}:")
            print(f"  original_name:  {file_info['original_name']}")
            print(f"  stored_path:    {file_info['stored_path']} (数据库相对路径)")
            print(f"  resolved_path:  {db._resolve_path(file_info['stored_path'])} (完整物理路径)")
            print(f"  文件存在:       {os.path.isfile(db._resolve_path(file_info['stored_path']))}")
        else:
            print(f"\n文件 ID {file_id} 不存在")

    # 测试最近5条记录
    print(f"\n最近5条记录路径验证:")
    files = db.query_files()[:5]
    for f in files:
        resolved = db._resolve_path(f['stored_path'])
        exists = os.path.isfile(resolved)
        status = "✅ 存在" if exists else "❌ 不存在"
        print(f"  ID {f['id']}: {f['stored_path']} -> {resolved} [{status}]")

    print("=" * 60)


if __name__ == "__main__":
    # 从命令行参数获取 file_id
    file_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    test_path_resolution(file_id)