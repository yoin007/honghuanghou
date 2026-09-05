#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
附件缩略图重建脚本

背景：缩略图规格从 200px / JPEG q75 提升到 400px / JPEG q85（Retina 屏与
打印 PDF 下 200px 物理像素不足，图片发虚）。新上传的附件自动使用新规格；
本脚本把已有图片附件的缩略图从存储的原图（1280px 标准化 JPEG）按新规格
批量重建。缩略图路径不变，数据库无需改动；脚本可重复执行。

使用方式（在 lesson 目录下，用运行后端的 Python）：
    python scripts/regen_attachment_thumbnails.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.datas_api.moral.base import get_moral_db
from models.datas_api.moral.attachments import (
    _make_thumbnail,
    _resolve_stored_path,
)


def main():
    regenerated = 0
    skipped = 0

    with get_moral_db() as db:
        rows = db.query_all(
            "SELECT id, stored_path, thumbnail_path FROM record_attachment "
            "WHERE file_type = 'image' AND thumbnail_path IS NOT NULL"
        )
        total = len(rows)
        for row in rows:
            src = _resolve_stored_path(row["stored_path"])
            thumb = _resolve_stored_path(row["thumbnail_path"])
            if not os.path.exists(src):
                print(f"[skip] 原图缺失 id={row['id']}: {src}")
                skipped += 1
                continue
            with open(src, "rb") as f:
                content = f.read()
            new_thumb = _make_thumbnail(content)
            with open(thumb, "wb") as f:
                f.write(new_thumb)
            regenerated += 1
            print(f"[ok] id={row['id']} 缩略图已重建（{len(new_thumb)} bytes）")

    print(f"\n完成：共 {total} 条图片附件，重建 {regenerated}，跳过 {skipped}")


if __name__ == "__main__":
    main()
