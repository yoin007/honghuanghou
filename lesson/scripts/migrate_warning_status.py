#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预警状态迁移脚本

为 warning_log 表增加 status / resolved_at / resolved_reason 字段，
并对历史数据做一次"现状对齐"：当前已恢复的预警标记为 resolved。

用法：
    python scripts/migrate_warning_status.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.datas_api.moral.base import get_moral_db


def column_exists(db, table: str, column: str) -> bool:
    rows = db.query_all(f"PRAGMA table_info({table})")
    return any(row.get("name") == column for row in (rows or []))


def add_columns(db):
    """新增字段（幂等）。"""
    if not column_exists(db, "warning_log", "status"):
        db.execute("ALTER TABLE warning_log ADD COLUMN status TEXT DEFAULT 'active'")
        print("[+] 新增字段: status")
    else:
        print("[=] 字段已存在: status，跳过")

    if not column_exists(db, "warning_log", "resolved_at"):
        db.execute("ALTER TABLE warning_log ADD COLUMN resolved_at TEXT")
        print("[+] 新增字段: resolved_at")
    else:
        print("[=] 字段已存在: resolved_at，跳过")

    if not column_exists(db, "warning_log", "resolved_reason"):
        db.execute("ALTER TABLE warning_log ADD COLUMN resolved_reason TEXT")
        print("[+] 新增字段: resolved_reason")
    else:
        print("[=] 字段已存在: resolved_reason，跳过")


def get_current_semester_id(db):
    row = db.query_one("SELECT semester_id FROM semester WHERE status = 1 LIMIT 1")
    return row["semester_id"] if row else None


def get_base_score(db) -> float:
    val = db.query_value(
        "SELECT config_value FROM moral_config WHERE config_key = 'evaluation_base_score'"
    )
    try:
        return float(val) if val is not None else 80.0
    except (ValueError, TypeError):
        return 80.0


def real_time_score_cte(semester_id: int, base_score: float) -> str:
    """与 dashboard_moral.py 一致的实时分数 CTE。"""
    return f"""
    student_score AS (
        SELECT
            s.student_id,
            ( {base_score}
              + COALESCE((SELECT SUM(score) FROM student_daily_record dr
                          WHERE dr.student_id = s.student_id
                            AND dr.semester_id = {semester_id}
                            AND dr.is_deleted = 0), 0)
              + COALESCE((SELECT SUM(score) FROM student_school_record sr
                          WHERE sr.student_id = s.student_id
                            AND sr.semester_id = {semester_id}
                            AND sr.is_deleted = 0), 0)
              + COALESCE((SELECT SUM(stf.current_score)
                            FROM student_task_finish stf
                            JOIN semester sem ON sem.semester_id = {semester_id}
                           WHERE stf.student_id = s.student_id
                             AND stf.status = 1
                             AND stf.finish_date >= sem.start_date
                             AND stf.finish_date <= sem.end_date), 0)
              + COALESCE((SELECT SUM(ced.score_assigned)
                            FROM collective_event_distribution ced
                            JOIN collective_event ce ON ced.event_id = ce.event_id
                           WHERE ced.student_id = s.student_id
                             AND ce.semester_id = {semester_id}
                             AND ced.is_participant = 1), 0)
              - COALESCE((SELECT SUM(ABS(score_deduct))
                            FROM punishment_record pr
                           WHERE pr.student_id = s.student_id
                             AND pr.semester_id = {semester_id}
                             AND pr.is_revoked = 0), 0)
            ) AS total_score
        FROM student s
        WHERE s.status = '在校'
    )
    """


def align_history(db, semester_id: int):
    """对当前学期的活跃预警做一次现状对齐：已恢复的标记为 resolved。"""
    if not semester_id:
        print("[!] 未找到当前学期，跳过历史对齐")
        return

    base_score = get_base_score(db)
    cte = real_time_score_cte(semester_id, base_score)

    configs = db.query_all("SELECT * FROM warning_config WHERE is_active = 1")
    if not configs:
        print("[!] 无启用的预警规则，跳过历史对齐")
        return

    total_resolved = 0

    for config in configs:
        trigger_type = config["trigger_type"]
        trigger_value = config["trigger_value"]
        rule_id = config["id"]

        # 跳过累进处罚类型（escalation_* 不自动消除）
        if trigger_type.startswith("escalation_"):
            continue

        if trigger_type == "score_threshold":
            if trigger_value < 0:
                # 扣分过多：日常分 >= 阈值 即已恢复
                # 活跃预警中，当前日常分 >= trigger_value 的 → resolved
                sql = f"""
                    WITH {cte}
                    SELECT wl.id
                    FROM warning_log wl
                    JOIN student_score ss ON wl.student_id = ss.student_id
                    WHERE wl.rule_id = ?
                      AND wl.semester_id = ?
                      AND wl.status = 'active'
                      AND (ss.total_score - {base_score}) >= ?
                """
                # 日常分 = total_score - base_score，日常分 >= -20 即恢复
                params = [rule_id, semester_id, trigger_value]
            else:
                # 低分预警：总分 >= 阈值 即已恢复
                sql = f"""
                    WITH {cte}
                    SELECT wl.id
                    FROM warning_log wl
                    JOIN student_score ss ON wl.student_id = ss.student_id
                    WHERE wl.rule_id = ?
                      AND wl.semester_id = ?
                      AND wl.status = 'active'
                      AND ss.total_score >= ?
                """
                params = [rule_id, semester_id, trigger_value]

            rows = db.query_all(sql, params)
            ids = [r["id"] for r in (rows or [])]

        elif trigger_type == "count_threshold":
            # 违纪次数：消极记录数 < 阈值 即已恢复
            sql = """
                SELECT wl.id
                FROM warning_log wl
                WHERE wl.rule_id = ?
                  AND wl.semester_id = ?
                  AND wl.status = 'active'
                  AND (
                    SELECT COUNT(*)
                    FROM student_daily_record dr
                    JOIN daily_event_type det ON dr.event_id = det.event_id
                    WHERE dr.student_id = wl.student_id
                      AND dr.semester_id = ?
                      AND det.event_type = 2
                      AND dr.is_deleted = 0
                  ) < ?
            """
            rows = db.query_all(sql, [rule_id, semester_id, semester_id, trigger_value])
            ids = [r["id"] for r in (rows or [])]
        else:
            continue

        if ids:
            placeholders = ",".join(["?"] * len(ids))
            db.execute(
                f"""UPDATE warning_log
                    SET status = 'resolved',
                        resolved_at = datetime('now', 'localtime'),
                        resolved_reason = 'auto_recovered'
                    WHERE id IN ({placeholders})""",
                ids,
            )
            total_resolved += len(ids)
            rule_name = config.get("rule_name", trigger_type)
            print(f"  [-] 规则 '{rule_name}': 标记 {len(ids)} 条为已消除")

    print(f"\n[✓] 历史对齐完成，共标记 {total_resolved} 条预警为已消除")


def main():
    print("=" * 50)
    print("预警状态字段迁移")
    print("=" * 50)

    with get_moral_db() as db:
        # 1. 新增字段
        print("\n第 1 步：新增字段")
        add_columns(db)

        # 2. 历史数据对齐
        print("\n第 2 步：历史数据现状对齐")
        semester_id = get_current_semester_id(db)
        align_history(db, semester_id)

        # 3. 统计
        print("\n第 3 步：结果统计")
        total = db.query_value("SELECT COUNT(*) FROM warning_log")
        active = db.query_value("SELECT COUNT(*) FROM warning_log WHERE status = 'active'")
        resolved = db.query_value("SELECT COUNT(*) FROM warning_log WHERE status = 'resolved'")
        print(f"  总计: {total}")
        print(f"  活跃: {active}")
        print(f"  已消除: {resolved}")

        db.commit()

    print("\n[✓] 迁移完成")


if __name__ == "__main__":
    main()
