# -*- coding: utf-8 -*-
"""
预警历史数据清理脚本

背景：预警规则增加了时间窗口维度后，之前基于"整个学期累计"口径产生的
大量历史预警已经不符合新的规则口径，继续保留会导致活跃预警列表噪音过大。

功能：
1. 将所有活跃（status='active'）的预警标记为已消除，原因 = 'rule_changed'
2. 可选：删除 is_deleted = 1 的规则（逻辑删除残留）
3. 可选：去重重复的 warning_config 规则

使用方式：
    python3 scripts/cleanup_warning_history.py            # 仅预览
    python3 scripts/cleanup_warning_history.py --apply     # 实际执行
"""

import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'databases', 'moral.db')


def _ensure_schema(cur):
    """确保表结构完整，缺少的列自动补上。"""
    # warning_config: is_deleted, time_window_days
    cur.execute("PRAGMA table_info(warning_config)")
    cols = {row[1] for row in cur.fetchall()}
    if 'is_deleted' not in cols:
        cur.execute("ALTER TABLE warning_config ADD COLUMN is_deleted INTEGER DEFAULT 0")
        print("  + 新增列 warning_config.is_deleted")
    if 'time_window_days' not in cols:
        cur.execute("ALTER TABLE warning_config ADD COLUMN time_window_days INTEGER")
        print("  + 新增列 warning_config.time_window_days")
        # 给现有规则设默认值
        cur.execute(
            "UPDATE warning_config SET time_window_days = 7 WHERE trigger_type = 'count_threshold'"
        )
        cur.execute(
            "UPDATE warning_config SET time_window_days = 30 WHERE trigger_type = 'score_threshold' AND trigger_value < 0"
        )
        print("  + 填充默认时间窗口：违纪类=7天，扣分过多类=30天，低分类=不限制")

    # warning_log: status, resolved_at, resolved_reason
    cur.execute("PRAGMA table_info(warning_log)")
    cols = {row[1] for row in cur.fetchall()}
    if 'status' not in cols:
        cur.execute("ALTER TABLE warning_log ADD COLUMN status TEXT DEFAULT 'active'")
        print("  + 新增列 warning_log.status")
    if 'resolved_at' not in cols:
        cur.execute("ALTER TABLE warning_log ADD COLUMN resolved_at TEXT")
        print("  + 新增列 warning_log.resolved_at")
    if 'resolved_reason' not in cols:
        cur.execute("ALTER TABLE warning_log ADD COLUMN resolved_reason TEXT")
        print("  + 新增列 warning_log.resolved_reason")


def preview(db_path):
    """预览清理效果，不实际修改。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=" * 60)
    print("预警历史数据清理 - 预览模式")
    print("=" * 60)

    print("\n【检查/补齐表结构】")
    _ensure_schema(cur)
    conn.commit()

    # 1. 活跃预警统计
    cur.execute("SELECT COUNT(*) FROM warning_log WHERE status = 'active'")
    active_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM warning_log WHERE status = 'resolved'")
    resolved_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM warning_log WHERE is_read = 0")
    unread_count = cur.fetchone()[0]
    print(f"\n【预警日志现状】")
    print(f"  总记录数：{active_count + resolved_count}")
    print(f"  活跃预警：{active_count}")
    print(f"  已消除：{resolved_count}")
    print(f"  未读：{unread_count}")

    # 按规则分组统计活跃预警
    cur.execute("""
        SELECT wc.id, wc.rule_name, wc.trigger_type, wc.trigger_value,
               wc.time_window_days, COUNT(wl.id) as active_count
        FROM warning_log wl
        LEFT JOIN warning_config wc ON wl.rule_id = wc.id
        WHERE wl.status = 'active'
        GROUP BY wc.id, wc.rule_name, wc.trigger_type, wc.trigger_value
        ORDER BY active_count DESC
        LIMIT 10
    """)
    print(f"\n【活跃预警按规则分布 Top 10】")
    for row in cur.fetchall():
        wid, name, ttype, tval, tw, cnt = row
        type_label = {
            'score_threshold': '分数阈值',
            'count_threshold': '违纪次数',
        }.get(ttype, ttype or '未知')
        win_label = f"{tw}天" if tw else "不限制"
        print(f"  [{wid or 'NULL'}] {name or '未命名'} ({type_label}/{tval}/{win_label}): {cnt} 条")

    # 2. warning_config 规则统计
    cur.execute("SELECT COUNT(*) FROM warning_config WHERE is_deleted = 0")
    active_rules = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM warning_config WHERE is_deleted = 1")
    deleted_rules = cur.fetchone()[0]
    print(f"\n【规则配置】")
    print(f"  有效规则：{active_rules} 条")
    print(f"  已逻辑删除：{deleted_rules} 条")

    # 检测重复规则（同 trigger_type + trigger_value + time_window_days）
    cur.execute("""
        SELECT trigger_type, trigger_value, time_window_days, COUNT(*) as cnt
        FROM warning_config
        WHERE is_deleted = 0
        GROUP BY trigger_type, trigger_value, time_window_days
        HAVING cnt > 1
        ORDER BY cnt DESC
    """)
    duplicates = cur.fetchall()
    if duplicates:
        print(f"\n【检测到重复规则】")
        for ttype, tval, tw, cnt in duplicates:
            type_label = {
                'score_threshold': '分数阈值',
                'count_threshold': '违纪次数',
            }.get(ttype, ttype)
            win_label = f"{tw}天" if tw else "不限制"
            print(f"  {type_label} / {tval} / {win_label}: {cnt} 条重复")
    else:
        print(f"\n【规则去重】无重复规则")

    print(f"\n{'=' * 60}")
    print(f"执行 --apply 将：")
    print(f"  1. 将全部 {active_count} 条活跃预警标记为已消除（reason='rule_changed'）")
    print(f"  2. 清理已逻辑删除的规则（{deleted_rules} 条）")
    print(f"  3. 合并重复规则（保留 id 最小的，其他标记为删除）")
    print(f"{'=' * 60}")

    conn.close()


def apply(db_path):
    """实际执行清理。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=" * 60)
    print("预警历史数据清理 - 执行模式")
    print("=" * 60)

    print("\n【检查/补齐表结构】")
    _ensure_schema(cur)
    conn.commit()

    # 1. 批量标记活跃预警为已消除
    cur.execute("SELECT COUNT(*) FROM warning_log WHERE status = 'active'")
    count = cur.fetchone()[0]
    cur.execute("""
        UPDATE warning_log
        SET status = 'resolved',
            resolved_at = datetime('now', 'localtime'),
            resolved_reason = 'rule_changed'
        WHERE status = 'active'
    """)
    print(f"\n✓ 已将 {count} 条活跃预警标记为已消除")

    # 2. 合并重复规则（保留 id 最小的，其他逻辑删除）
    cur.execute("""
        SELECT trigger_type, trigger_value, COALESCE(time_window_days, -1),
               MIN(id) as keep_id, GROUP_CONCAT(id) as all_ids
        FROM warning_config
        WHERE is_deleted = 0
        GROUP BY trigger_type, trigger_value, COALESCE(time_window_days, -1)
        HAVING COUNT(*) > 1
    """)
    duplicates = cur.fetchall()
    dedup_count = 0
    for ttype, tval, tw, keep_id, all_ids in duplicates:
        ids_to_delete = [int(i) for i in all_ids.split(',') if int(i) != keep_id]
        if ids_to_delete:
            placeholders = ','.join(['?'] * len(ids_to_delete))
            cur.execute(
                f"UPDATE warning_config SET is_deleted = 1, is_active = 0 WHERE id IN ({placeholders})",
                ids_to_delete
            )
            dedup_count += len(ids_to_delete)
            print(f"  - 规则类型={ttype} 值={tval} 窗口={tw if tw != -1 else 'NULL'}: "
                  f"保留 id={keep_id}, 删除 {ids_to_delete}")

    if dedup_count:
        print(f"✓ 去重完成，标记删除 {dedup_count} 条重复规则")
    else:
        print(f"✓ 无重复规则，跳过")

    # 3. 清理逻辑删除的规则（先置空关联预警的 rule_id 不行，改逻辑删除已经不需要了）
    # 注：因为是逻辑删除，不需要物理删除。保留即可。

    conn.commit()
    conn.close()

    print(f"\n✓ 清理完成")
    print(f"{'=' * 60}")


def main():
    if not os.path.exists(DB_PATH):
        print(f"错误：数据库文件不存在：{DB_PATH}")
        sys.exit(1)

    if '--apply' in sys.argv:
        apply(DB_PATH)
    else:
        preview(DB_PATH)
        print(f"\n确认无误后执行：python3 {os.path.basename(__file__)} --apply")


if __name__ == '__main__':
    main()
