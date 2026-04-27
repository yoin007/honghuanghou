# -*- coding: utf-8 -*-
"""
德育评价系统测试数据生成脚本（简化版）

生成完整测试数据并验证数据流转
"""

import sqlite3
import random
from datetime import date, timedelta

DB_PATH = "/Users/yoin/bdsync/program/honghuanghou/lesson/databases/moral.db"

def generate_test_data():
    """生成测试数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("=" * 60)
    print("德育评价系统测试数据生成")
    print("=" * 60)

    # 获取当前学期
    semester = conn.execute(
        "SELECT semester_id FROM semester WHERE status=1"
    ).fetchone()
    semester_id = semester['semester_id'] if semester else 20

    # 获取学生列表（包含grade_id）
    students = conn.execute(
        "SELECT student_id, name, class_id, grade_id FROM student WHERE status='在校' LIMIT 30"
    ).fetchall()

    # 获取事件类型
    positive_events = conn.execute(
        "SELECT event_id, event_name, score FROM daily_event_type WHERE event_type=1"
    ).fetchall()
    negative_events = conn.execute(
        "SELECT event_id, event_name, score FROM daily_event_type WHERE event_type=2"
    ).fetchall()

    # 获取校级事件类型
    school_events = conn.execute(
        "SELECT event_id, event_name, score FROM school_event_type"
    ).fetchall()

    # 获取教师列表
    teachers = conn.execute(
        "SELECT teacher_id, name FROM teacher WHERE is_active=1 LIMIT 10"
    ).fetchall()

    print(f"\n当前学期: {semester_id}")
    print(f"学生数: {len(students)}")

    # 1. 生成日常表现记录
    print("\n【生成日常表现记录】")
    daily_count = 0
    for student in students:
        # 每个学生随机3-5条记录
        num_records = random.randint(3, 5)
        for _ in range(num_records):
            # 70%积极，30%消极
            if random.random() < 0.7:
                event = random.choice(positive_events)
            else:
                event = random.choice(negative_events)

            teacher = random.choice(teachers)
            record_date = date.today() - timedelta(days=random.randint(1, 30))

            conn.execute("""
                INSERT INTO student_daily_record
                (student_id, event_id, score, class_id, grade_id, semester_id, record_date, recorder, remark, is_deleted)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (student['student_id'], event['event_id'], event['score'],
                  student['class_id'], student['grade_id'], semester_id, str(record_date),
                  teacher['teacher_id'], f"测试-{event['event_name']}"))
            daily_count += 1

    conn.commit()
    print(f"  ✅ 生成 {daily_count} 条日常记录")

    # 2. 生成校级事件记录
    print("\n【生成校级事件记录】")
    school_count = 0
    for i, student in enumerate(students[:15]):
        event = random.choice(school_events)
        get_date = date.today() - timedelta(days=random.randint(1, 60))

        conn.execute("""
            INSERT INTO student_school_record
            (student_id, event_id, score, class_id, grade_id, semester_id, get_date, proof, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (student['student_id'], event['event_id'], event['score'],
              student['class_id'], student['grade_id'], semester_id, str(get_date),
              f"PROOF-{i}-{random.randint(1000,9999)}"))
        school_count += 1

    conn.commit()
    print(f"  ✅ 生成 {school_count} 条校级事件")

    # 3. 生成德育任务（使用正确字段）
    print("\n【生成德育任务】")
    task_count = 0
    for grade_id in [1, 2, 3]:
        conn.execute("""
            INSERT INTO grade_moral_task
            (grade_id, task_name, task_desc, score, deadline_type, is_required, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (grade_id, f"{grade_id}年级劳动实践", "劳动实践任务", 10, 'semester', 1))
        task_count += 1

    conn.commit()
    print(f"  ✅ 生成 {task_count} 条德育任务")

    # 4. 生成处分记录
    print("\n【生成处分记录】")
    punishment_levels = [('警告', 5), ('严重警告', 10), ('通报批评', 15)]

    punish_count = 0
    for i, student in enumerate(students[:5]):
        level, p_deduct = random.choice(punishment_levels)
        punishment_date = date.today() - timedelta(days=random.randint(30, 90))
        teacher = random.choice(teachers)

        conn.execute("""
            INSERT INTO punishment_record
            (student_id, event_id, semester_id, punishment_date, class_id, grade_id, score_deduct, level, reason, recorder, is_revoked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (student['student_id'], 1, semester_id, str(punishment_date),
              student['class_id'], student['grade_id'], p_deduct, level,
              f"测试处分-{level}", teacher['teacher_id']))
        punish_count += 1

    conn.commit()
    print(f"  ✅ 生成 {punish_count} 条处分记录")

    # 5. 生成点滴记录
    print("\n【生成点滴记录】")
    moment_count = 0
    for i, student in enumerate(students[:20]):
        teacher = random.choice(teachers)
        record_date = date.today() - timedelta(days=random.randint(1, 30))

        conn.execute("""
            INSERT INTO moment_record
            (student_id, class_id, grade_id, recorder, content, record_date, record_type, semester_id)
            VALUES (?, ?, ?, ?, ?, ?, 'moment', ?)
        """, (student['student_id'], student['class_id'], student['grade_id'],
              teacher['teacher_id'], f"点滴：{student['name']}表现优秀",
              str(record_date), semester_id))
        moment_count += 1

    conn.commit()
    print(f"  ✅ 生成 {moment_count} 条点滴记录")

    conn.close()
    print("\n" + "=" * 60)
    print("测试数据生成完成")
    print("=" * 60)

def verify_data_flow():
    """验证数据流转"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("\n" + "=" * 60)
    print("数据流转验证")
    print("=" * 60)

    # 验证各表数据量
    print("\n【各表数据量】")
    tables_data = {
        'student_daily_record': '日常记录',
        'student_school_record': '校级事件',
        'grade_moral_task': '德育任务',
        'punishment_record': '处分记录',
        'moment_record': '点滴记录',
        'moral_evaluation': '德育评价',
        'student_profile': '学生画像',
        'warning_log': '预警记录'
    }

    for table, name in tables_data.items():
        count = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()['c']
        status = "✅" if count > 0 else "⚠️"
        print(f"  {status} {name}: {count}条")

    # 验证流转：计算德育评价
    print("\n【验证德育评价计算】")

    student = conn.execute(
        "SELECT student_id, name FROM student WHERE status='在校' LIMIT 1"
    ).fetchone()

    if student:
        print(f"\n学生: {student['name']} ({student['student_id']})")

        # 日常记录
        daily = conn.execute(
            "SELECT COUNT(*) as c, SUM(score) as s FROM student_daily_record WHERE student_id=? AND is_deleted=0",
            (student['student_id'],)
        ).fetchone()
        print(f"  日常记录: {daily['c']}条, 累计分数: {daily['s'] or 0}")

        # 校级事件
        school = conn.execute(
            "SELECT COUNT(*) as c, SUM(score) as s FROM student_school_record WHERE student_id=? AND is_deleted=0",
            (student['student_id'],)
        ).fetchone()
        print(f"  校级事件: {school['c']}条, 累计分数: {school['s'] or 0}")

        # 处分
        punish = conn.execute(
            "SELECT COUNT(*) as c, SUM(score_deduct) as s FROM punishment_record WHERE student_id=? AND is_revoked=0",
            (student['student_id'],)
        ).fetchone()
        print(f"  处分记录: {punish['c']}条, 累计扣分: {punish['s'] or 0}")

        # 计算总分
        base_score = 60
        total_score = base_score + (daily['s'] or 0) + (school['s'] or 0) - (punish['s'] or 0)
        print(f"\n  计算公式: 60 + {daily['s'] or 0} + {school['s'] or 0} - {punish['s'] or 0}")
        print(f"  ✅ 德育总分: {total_score}")

        # 等级判定
        if total_score >= 90:
            level = "优秀"
        elif total_score >= 80:
            level = "良好"
        elif total_score >= 60:
            level = "合格"
        else:
            level = "不合格"
        print(f"  ✅ 德育等级: {level}")

    conn.close()

    print("\n" + "=" * 60)
    print("验证完成 ✅")
    print("=" * 60)

if __name__ == "__main__":
    generate_test_data()
    verify_data_flow()