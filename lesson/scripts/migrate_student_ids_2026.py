# -*- coding: utf-8 -*-
"""2026 级新生学号迁移（一次性脚本）

依据《学生导入模板.xlsx》(学号/旧学号两列)：
1. 物理删除不在最新名单中的两名学生（20260016 邓涵语、20260109 张科涵，用户确认）
2. 58 名学生换号：两阶段更新（先加临时前缀，再落到新号），避免连锁换号主键冲突；
   同步更新所有 student_id / current_student_id 引用表及 pending_daily_record.student_ids JSON
3. 插入两名新生（牟紫嫣 20260050、武阮芷 20260085）

全程单事务；执行前需已手工备份 moral.db。
"""
import sqlite3
import json
import datetime
import openpyxl

XLSX = '/Users/yoin/bdsync/program/honghuanghou/学生导入模板.xlsx'
DB = 'databases/moral.db'
DROP_IDS = ('20260016', '20260109')
PREF = 'TMPSWAP__'

wb = openpyxl.load_workbook(XLSX, data_only=True)
rows = list(wb.active.iter_rows(values_only=True))[1:]
pairs, inserts = [], []
for r in rows:
    new = '' if r[0] is None else str(r[0]).strip()
    old = '' if r[1] is None else str(r[1]).strip()
    rec = dict(id=new, old=old, name=r[2], gender=r[3], birthday=r[4],
               room=str(r[5]).strip() if r[5] else None,
               bed=str(r[6]).strip() if r[6] is not None else None,
               cls=r[7])
    if not old:
        inserts.append(rec)
    elif old != new:
        pairs.append((old, new))
olds = [o for o, _ in pairs]
unchanged = {str(r[1]).strip() for r in rows
             if r[1] not in (None, '') and str(r[0]).strip() == str(r[1]).strip()}
name_by_old = {str(r[1]).strip(): r[2] for r in rows if r[1] not in (None, '')}
assert len(pairs) == 58 and len(inserts) == 2

con = sqlite3.connect(DB, timeout=30)
con.execute("PRAGMA foreign_keys=OFF")
try:
    con.execute("BEGIN IMMEDIATE")

    # 0. 前置断言：Excel 旧号 + 待删除号 == 库内全部 2026 学号；姓名逐一匹配
    db_ids = {r[0] for r in con.execute(
        "SELECT student_id FROM student WHERE student_id LIKE '2026%'")}
    assert set(olds) | unchanged | set(DROP_IDS) == db_ids, \
        f"学号集合不一致: 仅库有 {sorted(db_ids - set(olds) - unchanged - set(DROP_IDS))}"
    for sid, nm in con.execute(
            "SELECT student_id,name FROM student WHERE student_id LIKE '2026%'"):
        if sid in name_by_old:
            assert nm == name_by_old[sid], f"{sid}: 库={nm} Excel={name_by_old[sid]}"

    # 1. 删除两名学生（残留仅 student / student_class_history，已事先全表核查）
    c1 = con.execute(
        "DELETE FROM student_class_history WHERE student_id IN (?,?)", DROP_IDS).rowcount
    c2 = con.execute(
        "DELETE FROM student WHERE student_id IN (?,?)", DROP_IDS).rowcount
    print(f"删除: class_history {c1} 行, student {c2} 行")

    # 2. 两阶段换号：动态发现所有引用学号的列
    targets = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]
        for col in ('student_id', 'current_student_id'):
            if col in cols:
                targets.append((t, col))
    qmarks = ",".join("?" * len(olds))
    phase1 = phase2 = 0
    for t, col in targets:
        phase1 += con.execute(
            f'UPDATE "{t}" SET "{col}" = (? || "{col}") WHERE "{col}" IN ({qmarks})',
            (PREF, *olds)).rowcount
    for t, col in targets:
        for o, n in pairs:
            phase2 += con.execute(
                f'UPDATE "{t}" SET "{col}"=? WHERE "{col}"=?', (n, PREF + o)).rowcount
    print(f"换号: 阶段一 {phase1} 行, 阶段二 {phase2} 行")
    assert phase1 == phase2

    # 3. pending_daily_record.student_ids JSON 数组内的学号
    pair_map = dict(pairs)
    json_fixed = 0
    for pid, sids in con.execute(
            "SELECT id, student_ids FROM pending_daily_record WHERE student_ids IS NOT NULL"):
        try:
            arr = json.loads(sids)
        except Exception:
            continue
        new_arr = [pair_map.get(x, x) for x in arr]
        if new_arr != arr:
            con.execute(
                "UPDATE pending_daily_record SET student_ids=? WHERE id=?",
                (json.dumps(new_arr, ensure_ascii=False), pid))
            json_fixed += 1
    print(f"JSON 字段改写: {json_fixed} 行")

    # 4. 插入两名新生（班级/年级按班表解析，建籍信息对齐同批学生）
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for x in inserts:
        cid, gid = con.execute(
            "SELECT class_id, grade_id FROM class WHERE class_name=?", (x['cls'],)).fetchone()
        con.execute("""INSERT INTO student
            (student_id,name,gender,class_id,grade_id,original_grade_id,birthday,enrollment_date,
             roomid,rpid,status,is_active,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,'在校',1,?,?)""",
            (x['id'], x['name'], x['gender'], cid, gid, gid, x['birthday'], '2026-09-01',
             x['room'], x['bed'], now, now))
        con.execute("""INSERT INTO student_class_history
            (student_id,class_id,grade_id,start_date,end_date,change_reason,created_at)
            VALUES (?,?,?,?,NULL,'入学',?)""",
            (x['id'], cid, gid, '2026-09-01', now))
        print(f"插入新生: {x['id']} {x['name']} {x['cls']}(class_id={cid}) "
              f"{x['gender']} {x['birthday']} 宿舍{x['room']}床{x['bed']}")

    con.commit()
    print("已提交。")
except Exception:
    con.rollback()
    raise
finally:
    con.close()
