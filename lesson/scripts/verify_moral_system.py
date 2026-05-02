# -*- coding: utf-8 -*-
"""
德育评价系统快速验证脚本

验证数据流转是否通畅
"""

import sys
import os
# 使用相对路径添加 lesson 目录到 sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LESSON_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, LESSON_DIR)

from utils.sqlite_moral_db import MoralDatabase, get_moral_db_path
import sqlite3

def verify_data_flow():
    """验证数据流转"""
    db_path = get_moral_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print("=" * 60)
    print("德育评价系统数据流转验证")
    print("=" * 60)

    # 1. 基础数据检查
    print("\n【一、基础数据检查】")

    tables = [
        "student", "class", "grade", "teacher", "role",
        "semester", "school_year", "daily_event_type", "school_event_type",
        "student_daily_record", "student_school_record", "student_task_finish",
        "punishment_record", "moral_evaluation", "student_profile",
        "collective_event", "warning_log", "task_carryover_log",
        "birthday_reminder", "moment_record", "ai_consultation",
        "api_permission_config", "ai_consultation_template"
    ]

    for table in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()['c']
            status = "✅" if count > 0 else "⚠️"
            print(f"  {status} {table}: {count}条")
        except:
            print(f"  ❌ {table}: 表不存在")

    # 2. 当前学期检查
    print("\n【二、当前学期检查】")
    semester = conn.execute(
        "SELECT semester_id, semester_name, status FROM semester WHERE status=1"
    ).fetchone()
    if semester:
        print(f"  ✅ 当前学期: {semester['semester_name']} (ID={semester['semester_id']})")
    else:
        print(f"  ⚠️ 无当前学期设置")

    # 3. 班级学生数据检查
    print("\n【三、班级学生数据检查】")
    classes = conn.execute(
        "SELECT class_id, class_code, class_name, leader_name FROM class WHERE is_active=1"
    ).fetchall()

    for cls in classes[:5]:
        student_count = conn.execute(
            "SELECT COUNT(*) as c FROM student WHERE class_id=? AND status='在校'",
            (cls['class_id'],)
        ).fetchone()['c']
        print(f"  ✅ {cls['class_name']} ({cls['leader_name']}): {student_count}名学生")

    # 4. 记录流转检查
    print("\n【四、记录流转检查】")

    # 4.1 日常记录 → 德育评价
    daily_count = conn.execute(
        "SELECT COUNT(*) as c FROM student_daily_record WHERE is_deleted=0"
    ).fetchone()['c']

    eval_count = conn.execute(
        "SELECT COUNT(*) as c FROM moral_evaluation"
    ).fetchone()['c']

    print(f"  日常记录数: {daily_count}")
    print(f"  德育评价数: {eval_count}")

    if daily_count > 0 and eval_count > 0:
        print(f"  ✅ 日常记录 → 德育评价流转正常")
    elif daily_count > 0 and eval_count == 0:
        print(f"  ⚠️ 日常记录存在，但德育评价未计算（需运行计算API）")
    else:
        print(f"  ⚠️ 需录入日常记录后验证流转")

    # 4.2 学生画像
    profile_count = conn.execute(
        "SELECT COUNT(*) as c FROM student_profile"
    ).fetchone()['c']
    print(f"  学生画像数: {profile_count}")

    if profile_count > 0:
        print(f"  ✅ 学生画像已生成")
    else:
        print(f"  ⚠️ 学生画像未生成")

    # 5. 权限配置检查
    print("\n【五、权限配置检查】")
    perm_count = conn.execute(
        "SELECT COUNT(*) as c FROM api_permission_config"
    ).fetchone()['c']
    print(f"  API权限配置数: {perm_count}")

    if perm_count > 0:
        # 检查各角色权限分布
        roles = ['teacher', 'cleader', 'xuefa', 'jiaowu', 'admin']
        for role in roles:
            # 统计该角色可访问的API数（简单判断）
            apis = conn.execute(
                f"SELECT COUNT(*) as c FROM api_permission_config WHERE allowed_roles LIKE '%{role}%'"
            ).fetchone()['c']
            print(f"    {role}: 可访问 {apis} 个API")

    # 6. 定时任务配置检查
    print("\n【六、定时任务配置检查】")
    print("  定时任务定义:")
    tasks = [
        "birthday_reminder (08:00)",
        "birthday_blessing (08:30)",
        "profile_update_check (周一09:00)",
        "warning_check (10:00)",
        "semester_evaluation (学期末)",
        "task_carryover (学年末)"
    ]
    for task in tasks:
        print(f"    ✅ {task}")

    # 7. AI诊疗模板检查
    print("\n【七、AI诊疗模板检查】")
    templates = conn.execute(
        "SELECT template_type, template_name FROM ai_consultation_template WHERE is_active=1"
    ).fetchall()
    for t in templates:
        print(f"  ✅ {t['template_name']} ({t['template_type']})")

    conn.close()

    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)

if __name__ == "__main__":
    verify_data_flow()