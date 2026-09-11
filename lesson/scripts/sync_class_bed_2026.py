# -*- coding: utf-8 -*-
"""2026 级名单附带差异同步（一次性脚本，用户确认）：
1. 朱姿羽 20260119：高一4班(22) -> 高一3班(21)，按既有惯例新增"调班" history 行
2. 陈海慧 20260005 与 陈梓涵 20260011 宿舍床号对调
"""
import sqlite3
import datetime

DB = 'databases/moral.db'
con = sqlite3.connect(DB, timeout=30)
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
try:
    con.execute("BEGIN IMMEDIATE")
    con.execute(
        "UPDATE student SET class_id=21, updated_at=? "
        "WHERE student_id='20260119' AND class_id=22", (now,))
    con.execute(
        "INSERT INTO student_class_history "
        "(student_id,class_id,grade_id,start_date,end_date,change_reason,created_at) "
        "VALUES ('20260119',21,4,date('now','localtime'),NULL,'调班',?)", (now,))
    con.execute(
        "UPDATE student SET roomid='B503', rpid='8', updated_at=? "
        "WHERE student_id='20260005' AND roomid='B504' AND rpid='6'", (now,))
    con.execute(
        "UPDATE student SET roomid='B504', rpid='6', updated_at=? "
        "WHERE student_id='20260011' AND roomid='B503' AND rpid='8'", (now,))
    con.commit()
    print("已提交")
except Exception:
    con.rollback()
    raise
finally:
    con.close()

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
for r in con.execute(
        """SELECT s.student_id,s.name,c.class_name,s.roomid,s.rpid FROM student s
           JOIN class c ON c.class_id=s.class_id
           WHERE s.student_id IN ('20260119','20260005','20260011')
           ORDER BY s.student_id"""):
    print(dict(r))
for r in con.execute(
        "SELECT * FROM student_class_history WHERE student_id='20260119' ORDER BY id"):
    print("history:", dict(r))
con.close()
