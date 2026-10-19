# -*- coding: utf-8 -*-
"""回填 announcements.class_id。

历史公告的 class_code 列混杂了班级编码（202501）和班级名（高一1班）两种写法，
且升年级改名后旧班级名无法对应。本脚本按 moral.db class 表把 class_id 回填到
homework.db announcements.class_id，未匹配的历史值保持 NULL（读取接口有兼容回退）。

用法：
    python scripts/migrate_announcement_class_id.py           # 预览（不写入）
    python scripts/migrate_announcement_class_id.py --apply   # 执行回填
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db_config import DATABASES_DIR as DB_DIR


def build_class_lookup(moral_path):
    """返回 {identifier: class_id}，identifier 含 class_code 与 class_name 两种键"""
    lookup = {}
    conn = sqlite3.connect(moral_path)
    try:
        rows = conn.execute(
            "SELECT class_id, class_code, class_name FROM class"
        ).fetchall()
        for class_id, class_code, class_name in rows:
            if class_code:
                lookup.setdefault(str(class_code), class_id)
            if class_name:
                lookup.setdefault(str(class_name), class_id)
    finally:
        conn.close()
    return lookup


def main():
    apply = "--apply" in sys.argv
    homework_path = os.path.join(DB_DIR, "homework.db")
    moral_path = os.path.join(DB_DIR, "moral.db")

    lookup = build_class_lookup(moral_path)

    conn = sqlite3.connect(homework_path)
    try:
        # 确保列存在（与 Homework.__create_table__ 的迁移逻辑一致）
        cols = [r[1] for r in conn.execute("PRAGMA table_info(announcements)")]
        has_class_id = "class_id" in cols
        if not has_class_id:
            if not apply:
                print("announcements 表缺少 class_id 列，--apply 时将先创建")
            else:
                conn.execute("ALTER TABLE announcements ADD COLUMN class_id INTEGER")
                conn.commit()
                print("已添加 class_id 列")

        if has_class_id or apply:
            rows = conn.execute(
                "SELECT id, class_code FROM announcements WHERE class_id IS NULL"
            ).fetchall()
        else:
            rows = conn.execute("SELECT id, class_code FROM announcements").fetchall()

        matched = 0
        unmatched = {}
        updates = []
        for ann_id, class_code in rows:
            class_id = lookup.get(str(class_code))
            if class_id is not None:
                updates.append((class_id, ann_id))
                matched += 1
            else:
                unmatched[str(class_code)] = unmatched.get(str(class_code), 0) + 1

        print(f"待回填公告：{len(rows)} 条")
        print(f"可匹配：{matched} 条")
        if unmatched:
            print(f"未匹配（保持 NULL）：{sum(unmatched.values())} 条，分布：")
            for code, count in sorted(unmatched.items()):
                print(f"  {code!r}: {count} 条")

        if apply:
            conn.executemany(
                "UPDATE announcements SET class_id = ? WHERE id = ?", updates
            )
            conn.commit()
            print(f"已回填 {matched} 条")
        else:
            print("\n预览模式：未写入。确认无误后加 --apply 执行。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
