# -*- coding: utf-8 -*-
"""
德育评价系统数据库表创建脚本

创建37张表:
- 基础表:school_year, semester, grade, grade_level_config, class, student, teacher, role, student_class_history, student_status_change
- 德育核心表:daily_event_type, school_event_type, grade_moral_task, student_daily_record, student_school_record, student_task_finish, punishment_record, collective_event, collective_event_distribution, moral_evaluation
- 扩展表:student_profile, student_profile_history, profile_config, ai_consultation, ai_consultation_message, birthday_reminder, birthday_reminder_config, violation_escalation_rule, warning_config, warning_log
- 配置表:semester_carryover_config, data_visibility_config, task_carryover_log, moral_operation_log

运行方式:
    # MySQL 建表(默认)
    python scripts/create_moral_tables.py [--drop-existing]

    # SQLite 建表
    python scripts/create_moral_tables.py --sqlite [--drop-existing]
"""

import sys
import os
import logging
from typing import List

# 添加 lesson 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
import mysql.connector
from mysql.connector import Error
from utils.mysql_db import get_connection_pool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# SQLite 表定义 SQL
# =============================================================================

SQLite_TABLES_SQL = {
    # 1. 学年表
    "school_year": """
CREATE TABLE IF NOT EXISTS school_year (
    year_id INTEGER PRIMARY KEY AUTOINCREMENT,
    year_name TEXT NOT NULL UNIQUE,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    is_current INTEGER DEFAULT 0
);
""",
    # 2. 学期表
    "semester": """
CREATE TABLE IF NOT EXISTS semester (
    semester_id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_name TEXT NOT NULL,
    year_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status INTEGER DEFAULT 1,
    FOREIGN KEY (year_id) REFERENCES school_year(year_id),
    UNIQUE (semester_name, year_id)
);
CREATE INDEX IF NOT EXISTS idx_semester_year ON semester(year_id);
""",
    # 3. 级号表
    "grade": """
CREATE TABLE IF NOT EXISTS grade (
    grade_id INTEGER PRIMARY KEY AUTOINCREMENT,
    grade_name TEXT NOT NULL,
    enrollment_year INTEGER NOT NULL UNIQUE,
    is_archived INTEGER DEFAULT 0,
    archived_at TEXT,
    leader_ids TEXT DEFAULT '',
    leader_names TEXT DEFAULT ''
);
""",
    # 4. 年级等级配置表
    "grade_level_config": """
CREATE TABLE IF NOT EXISTS grade_level_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    years_after_enrollment INTEGER NOT NULL UNIQUE,
    level_name TEXT NOT NULL
);
""",
    # 5. 班级表
    "class": """
CREATE TABLE IF NOT EXISTS class (
    class_id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_code TEXT NOT NULL UNIQUE,
    grade_id INTEGER NOT NULL,
    class_number INTEGER NOT NULL,
    class_name TEXT NOT NULL,
    leader_wxid TEXT,
    leader_name TEXT,
    leader_ids TEXT DEFAULT '',
    leader_names TEXT DEFAULT '',
    roomid TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id),
    UNIQUE (grade_id, class_number)
);
"",
    # 6. 学生表
    "student": """
CREATE TABLE IF NOT EXISTS student (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    gender TEXT CHECK (gender IN ('男', '女')),
    class_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    original_grade_id INTEGER,
    roomid TEXT,
    status TEXT DEFAULT '在校' CHECK (status IN ('在校', '休学', '转出', '毕业')),
    status_date TEXT,
    enrollment_date TEXT,
    is_active INTEGER DEFAULT 1,
    birthday TEXT,
    phone TEXT,
    email TEXT,
    entrance_score NUMERIC(6,2),
    entrance_rank INTEGER,
    gaokao_score NUMERIC(6,2),
    gaokao_year INTEGER,
    gaokao_rank INTEGER,
    middle_school TEXT,
    middle_school_city TEXT,
    university_name TEXT,
    university_type TEXT,
    university_major TEXT,
    university_city TEXT,
    profile_summary TEXT,
    profile_tags TEXT,
    profile_updated_at TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id),
    FOREIGN KEY (original_grade_id) REFERENCES grade(grade_id)
);
CREATE INDEX IF NOT EXISTS idx_student_birthday ON student(birthday);
CREATE INDEX IF NOT EXISTS idx_student_grade_status ON student(grade_id, status);
""",
    # 7. 教师表
    "teacher": """
CREATE TABLE IF NOT EXISTS teacher (
    teacher_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    wxid TEXT,
    subject TEXT,
    course TEXT,
    password_hash TEXT,
    raw_pwd TEXT,
    role TEXT DEFAULT 'teacher',
    level INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    notice_enabled INTEGER DEFAULT 1,
    is_password_changed INTEGER DEFAULT 0,
    score INTEGER DEFAULT 50,
    balance INTEGER DEFAULT 0,
    model TEXT DEFAULT 'basic',
    ai_flag INTEGER DEFAULT 0,
    birthday TEXT,
    note TEXT,
    identity_type TEXT DEFAULT 'teacher',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_teacher_wxid ON teacher(wxid);
""",
    # 8. 教师任教班级映射表
    "teacher_teaching_class": """
CREATE TABLE IF NOT EXISTS teacher_teaching_class (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id TEXT NOT NULL,
    teacher_name TEXT,
    class_id INTEGER NOT NULL,
    subject TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    UNIQUE(teacher_id, class_id, subject)
);
CREATE INDEX IF NOT EXISTS idx_teacher_teaching_teacher ON teacher_teaching_class(teacher_id);
CREATE INDEX IF NOT EXISTS idx_teacher_teaching_class ON teacher_teaching_class(class_id);
""",
    # 8. 角色表
    "role": """
CREATE TABLE IF NOT EXISTS role (
    role_id TEXT PRIMARY KEY,
    role_name TEXT,
    description TEXT
);
""",
    # 9. 学生班级履历表
    "student_class_history": """
CREATE TABLE IF NOT EXISTS student_class_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    change_reason TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
);
CREATE INDEX IF NOT EXISTS idx_student_class_history_date ON student_class_history(student_id, start_date, end_date);
""",
    # 10. 学籍变动记录表
    "student_status_change": """
CREATE TABLE IF NOT EXISTS student_status_change (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    from_class_id INTEGER,
    to_class_id INTEGER,
    from_grade_id INTEGER,
    to_grade_id INTEGER,
    effective_date TEXT NOT NULL,
    reason TEXT,
    approver TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (from_class_id) REFERENCES class(class_id),
    FOREIGN KEY (to_class_id) REFERENCES class(class_id),
    FOREIGN KEY (from_grade_id) REFERENCES grade(grade_id),
    FOREIGN KEY (to_grade_id) REFERENCES grade(grade_id)
);
""",
    # 11. 日常事件类型表
    "daily_event_type": """
CREATE TABLE IF NOT EXISTS daily_event_type (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    event_type INTEGER NOT NULL CHECK (event_type IN (1, 2)),
    score INTEGER NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    CHECK (
        (event_type = 1 AND score > 0) OR
        (event_type = 2 AND score < 0)
    )
);
""",
    # 12. 校级事件类型表
    "school_event_type": """
CREATE TABLE IF NOT EXISTS school_event_type (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    event_level TEXT,
    event_type INTEGER NOT NULL CHECK (event_type IN (1, 2)),
    score INTEGER NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1
);
""",
    # 13. 年级德育任务表
    "grade_moral_task": """
CREATE TABLE IF NOT EXISTS grade_moral_task (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    grade_id INTEGER NOT NULL,
    task_name TEXT NOT NULL,
    task_desc TEXT,
    score INTEGER NOT NULL,
    start_date TEXT,
    end_date TEXT,
    deadline_type TEXT,
    can_carryover INTEGER DEFAULT 1,
    is_required INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
);
""",
    # 14. 学生日常表现记录表
    "student_daily_record": """
CREATE TABLE IF NOT EXISTS student_daily_record (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    semester_id INTEGER NOT NULL,
    record_date TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    score INTEGER,
    remark TEXT,
    is_deleted INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (event_id) REFERENCES daily_event_type(event_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
);
CREATE INDEX IF NOT EXISTS idx_student_daily_semester ON student_daily_record(student_id, semester_id);
CREATE INDEX IF NOT EXISTS idx_student_daily_date ON student_daily_record(record_date);
CREATE INDEX IF NOT EXISTS idx_student_daily_event ON student_daily_record(event_id);
""",
    # 15. 学生校级事件记录表
    "student_school_record": """
CREATE TABLE IF NOT EXISTS student_school_record (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    semester_id INTEGER NOT NULL,
    get_date TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    score INTEGER,
    proof TEXT,
    recorder TEXT,
    is_deleted INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (event_id) REFERENCES school_event_type(event_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
);
""",
    # 16. 学生任务完成记录表
    "student_task_finish": """
CREATE TABLE IF NOT EXISTS student_task_finish (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    task_id INTEGER NOT NULL,
    year_id INTEGER NOT NULL,
    original_task_id INTEGER,
    original_year_id INTEGER,
    is_carried_over INTEGER DEFAULT 0,
    carryover_count INTEGER DEFAULT 0,
    current_score NUMERIC(6,2),
    status INTEGER DEFAULT 0 CHECK (status IN (0, 1, 2)),
    finish_date TEXT,
    finish_year_id INTEGER,
    proof TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (task_id) REFERENCES grade_moral_task(task_id),
    FOREIGN KEY (year_id) REFERENCES school_year(year_id),
    FOREIGN KEY (original_task_id) REFERENCES grade_moral_task(task_id),
    FOREIGN KEY (original_year_id) REFERENCES school_year(year_id),
    FOREIGN KEY (finish_year_id) REFERENCES school_year(year_id),
    UNIQUE (student_id, task_id, year_id)
);
""",
    # 17. 处分记录表
    "punishment_record": """
CREATE TABLE IF NOT EXISTS punishment_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    semester_id INTEGER NOT NULL,
    punishment_date TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    score_deduct INTEGER NOT NULL,
    level TEXT,
    reason TEXT,
    recorder TEXT,
    is_revoked INTEGER DEFAULT 0,
    revoke_date TEXT,
    revoke_by TEXT,
    revoke_reason TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (event_id) REFERENCES school_event_type(event_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
);
""",
    # 18. 集体事件表
    "collective_event": """
CREATE TABLE IF NOT EXISTS collective_event (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    event_type TEXT NOT NULL,
    semester_id INTEGER NOT NULL,
    event_date TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id)
);
""",
    # 19. 集体事件分配表
    "collective_event_distribution": """
CREATE TABLE IF NOT EXISTS collective_event_distribution (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    student_id TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    score_assigned INTEGER,
    is_participant INTEGER DEFAULT 1,
    remark TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (event_id) REFERENCES collective_event(event_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    UNIQUE (event_id, student_id)
);
""",
    # 20. 德育评价表
    "moral_evaluation": """
CREATE TABLE IF NOT EXISTS moral_evaluation (
    eval_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    semester_id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    grade_id INTEGER NOT NULL,
    total_score NUMERIC(6,2) DEFAULT 0,
    level TEXT,
    update_time TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id),
    UNIQUE (student_id, semester_id)
);
""",
    # 21. 违纪累进规则表
    "violation_escalation_rule": """
CREATE TABLE IF NOT EXISTS violation_escalation_rule (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    time_window_days INTEGER DEFAULT 90,
    escalation_rules TEXT,
    FOREIGN KEY (event_id) REFERENCES daily_event_type(event_id)
);
""",
    # 22. 学期结转配置表
    "semester_carryover_config": """
CREATE TABLE IF NOT EXISTS semester_carryover_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,
    can_carryover INTEGER DEFAULT 1,
    score_factor NUMERIC(3,2) DEFAULT 1.00,
    description TEXT
);
""",
    # 23. 数据可见性配置表
    "data_visibility_config": """
CREATE TABLE IF NOT EXISTS data_visibility_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,
    visible_roles TEXT NOT NULL,
    description TEXT
);
""",
    # 24. 预警配置表
    "warning_config": """
CREATE TABLE IF NOT EXISTS warning_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    trigger_value INTEGER NOT NULL,
    notify_roles TEXT,
    is_active INTEGER DEFAULT 1
);
""",
    # 25. 预警日志表
    "warning_log": """
CREATE TABLE IF NOT EXISTS warning_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    rule_id INTEGER NOT NULL,
    semester_id INTEGER NOT NULL,
    warning_level TEXT DEFAULT 'warning',
    message TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (rule_id) REFERENCES warning_config(id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id)
);
""",
    # 26. 任务结转日志表
    "task_carryover_log": """
CREATE TABLE IF NOT EXISTS task_carryover_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    original_task_id INTEGER NOT NULL,
    from_year_id INTEGER NOT NULL,
    to_year_id INTEGER NOT NULL,
    carryover_index INTEGER NOT NULL,
    score_before NUMERIC(6,2),
    score_after NUMERIC(6,2),
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (original_task_id) REFERENCES grade_moral_task(task_id),
    FOREIGN KEY (from_year_id) REFERENCES school_year(year_id),
    FOREIGN KEY (to_year_id) REFERENCES school_year(year_id)
);
""",
    # 27. 操作日志表
    "moral_operation_log": """
CREATE TABLE IF NOT EXISTS moral_operation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operator TEXT NOT NULL,
    operator_role TEXT,
    operation TEXT NOT NULL,
    table_name TEXT NOT NULL,
    record_id INTEGER,
    semester_id INTEGER,
    old_data TEXT,
    new_data TEXT,
    reason TEXT,
    ip_address TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_operation_log_operator ON moral_operation_log(operator);
CREATE INDEX IF NOT EXISTS idx_operation_log_table_record ON moral_operation_log(table_name, record_id);
""",
    # 28. 学生画像表
    "student_profile": """
CREATE TABLE IF NOT EXISTS student_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    profile_version INTEGER DEFAULT 1,
    profile_summary TEXT,
    profile_tags TEXT,
    strength_tags TEXT,
    improvement_tags TEXT,
    risk_level TEXT,
    moral_score NUMERIC(5,2),
    attitude_score NUMERIC(5,2),
    social_score NUMERIC(5,2),
    growth_score NUMERIC(5,2),
    suggestions TEXT,
    intervention_priority TEXT,
    data_source_summary TEXT,
    generated_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    UNIQUE (student_id, profile_version)
);
""",
    # 29. 画像历史表
    "student_profile_history": """
CREATE TABLE IF NOT EXISTS student_profile_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    profile_version INTEGER NOT NULL,
    profile_data TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);
""",
    # 30. 画像配置表
    "profile_config": """
CREATE TABLE IF NOT EXISTS profile_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT,
    description TEXT
);
""",
    # 31. AI诊疗会话表
    "ai_consultation": """
CREATE TABLE IF NOT EXISTS ai_consultation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    consultation_type TEXT NOT NULL,
    title TEXT,
    description TEXT,
    status TEXT DEFAULT 'active',
    priority TEXT DEFAULT 'normal',
    creator TEXT,
    assignee TEXT,
    participants TEXT,
    ai_analysis TEXT,
    ai_suggestions TEXT,
    ai_risk_assessment TEXT,
    solution TEXT,
    outcome TEXT,
    follow_up_date TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    closed_at TEXT,
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);
CREATE INDEX IF NOT EXISTS idx_consultation_student_status ON ai_consultation(student_id, status);
""",
    # 32. AI诊疗对话记录表
    "ai_consultation_message": """
CREATE TABLE IF NOT EXISTS ai_consultation_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consultation_id INTEGER NOT NULL,
    message_type TEXT NOT NULL,
    content TEXT NOT NULL,
    sender TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (consultation_id) REFERENCES ai_consultation(id)
);
CREATE INDEX IF NOT EXISTS idx_consultation_message ON ai_consultation_message(consultation_id);
""",
    # 33. 生日提醒表
    "birthday_reminder": """
CREATE TABLE IF NOT EXISTS birthday_reminder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    reminder_date TEXT NOT NULL,
    reminder_type TEXT DEFAULT 'birthday',
    message TEXT,
    is_sent INTEGER DEFAULT 0,
    sent_at TEXT,
    recipient_type TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);
CREATE INDEX IF NOT EXISTS idx_birthday_reminder_date ON birthday_reminder(reminder_date);
""",
    # 34. 生日提醒配置表
    "birthday_reminder_config": """
CREATE TABLE IF NOT EXISTS birthday_reminder_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT,
    description TEXT
);
""",
    # 35. 系统配置表
    "moral_config": """
CREATE TABLE IF NOT EXISTS moral_config (
    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key TEXT NOT NULL UNIQUE,
    config_value TEXT,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
""",
    # 36. API权限配置表
    "api_permission_module": """
CREATE TABLE IF NOT EXISTS api_permission_module (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_key TEXT NOT NULL UNIQUE,
    module_name TEXT NOT NULL,
    parent_id INTEGER,
    allowed_roles TEXT NOT NULL DEFAULT '[]',
    min_level INTEGER DEFAULT 0,
    policy_mode TEXT DEFAULT 'role_and_level',
    description TEXT,
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_api_permission_module_key ON api_permission_module(module_key);
CREATE INDEX IF NOT EXISTS idx_api_permission_module_parent ON api_permission_module(parent_id);
""",
    "api_permission_config": """
CREATE TABLE IF NOT EXISTS api_permission_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_path TEXT NOT NULL UNIQUE,
    api_name TEXT NOT NULL,
    api_group TEXT NOT NULL,
    allowed_roles TEXT NOT NULL,
    min_level INTEGER DEFAULT 0,
    module_id INTEGER,
    http_method TEXT DEFAULT '*',
    match_type TEXT DEFAULT 'exact',
    policy_mode TEXT DEFAULT 'role_and_level',
    inherit_from_module INTEGER DEFAULT 0,
    is_public INTEGER DEFAULT 0,
    enforce_backend INTEGER DEFAULT 1,
    data_scope_rules TEXT DEFAULT '{}',
    target_scope_rules TEXT DEFAULT '{}',
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_api_permission_path ON api_permission_config(api_path);
CREATE INDEX IF NOT EXISTS idx_api_permission_group ON api_permission_config(api_group);
CREATE INDEX IF NOT EXISTS idx_api_permission_module_id ON api_permission_config(module_id);
""",
    # 37. AI诊疗模板表
    "ai_consultation_template": """
CREATE TABLE IF NOT EXISTS ai_consultation_template (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_type TEXT NOT NULL,
    template_name TEXT NOT NULL,
    prompt_template TEXT NOT NULL,
    suggested_questions TEXT,
    response_format TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
""",
    # 38. 点滴记录表(一生一册)
    "moment_record": """
CREATE TABLE IF NOT EXISTS moment_record (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    recorder TEXT NOT NULL,
    record_type TEXT DEFAULT 'moment',
    content TEXT NOT NULL,
    record_date TEXT NOT NULL,
    is_private INTEGER DEFAULT 1,
    tags TEXT,
    semester_id INTEGER,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id)
);
CREATE INDEX IF NOT EXISTS idx_moment_student ON moment_record(student_id);
CREATE INDEX IF NOT EXISTS idx_moment_date ON moment_record(record_date);
""",
    # 39. 菜单权限配置表
    "menu_permission_config": """
CREATE TABLE IF NOT EXISTS menu_permission_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_key TEXT NOT NULL UNIQUE,
    menu_label TEXT NOT NULL,
    menu_route TEXT NOT NULL,
    menu_group TEXT NOT NULL,
    allowed_roles TEXT NOT NULL DEFAULT '[]',
    is_public INTEGER DEFAULT 0,
    requires_auth INTEGER DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_menu_permission_key ON menu_permission_config(menu_key);
CREATE INDEX IF NOT EXISTS idx_menu_permission_group ON menu_permission_config(menu_group);
""",
}


# =============================================================================
# 表定义 SQL
# =============================================================================

TABLES_SQL = {
    # 1. 学年表
    "school_year": """
CREATE TABLE IF NOT EXISTS school_year (
    year_id INT PRIMARY KEY AUTO_INCREMENT,
    year_name VARCHAR(20) NOT NULL COMMENT '如:2025-2026学年',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current TINYINT DEFAULT 0 COMMENT '是否当前学年',
    UNIQUE KEY uk_year_name (year_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学年配置表';
""",
    # 2. 学期表
    "semester": """
CREATE TABLE IF NOT EXISTS semester (
    semester_id INT PRIMARY KEY AUTO_INCREMENT,
    semester_name VARCHAR(20) NOT NULL COMMENT '如:2025-2026上',
    year_id INT NOT NULL COMMENT '所属学年',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TINYINT DEFAULT 1 COMMENT '1=当前学期 0=已结束',
    FOREIGN KEY (year_id) REFERENCES school_year(year_id),
    INDEX idx_year (year_id),
    UNIQUE KEY uk_semester_name_year (semester_name, year_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学期配置表';
""",
    # 3. 级号表
    "grade": """
CREATE TABLE IF NOT EXISTS grade (
    grade_id INT PRIMARY KEY AUTO_INCREMENT,
    grade_name VARCHAR(10) NOT NULL COMMENT '如:2025级',
    enrollment_year INT NOT NULL COMMENT '入学年份',
    is_archived TINYINT DEFAULT 0 COMMENT '是否已归档(毕业)',
    archived_at DATETIME COMMENT '归档时间',
    UNIQUE KEY uk_enrollment_year (enrollment_year)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='级号配置表';
""",
    # 4. 年级等级配置表
    "grade_level_config": """
CREATE TABLE IF NOT EXISTS grade_level_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    years_after_enrollment INT NOT NULL COMMENT '入学后第几年',
    level_name VARCHAR(10) NOT NULL COMMENT '高一/高二/高三',
    UNIQUE KEY uk_years (years_after_enrollment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='年级等级配置表';
""",
    # 5. 班级表
    "class": """
CREATE TABLE IF NOT EXISTS class (
    class_id INT PRIMARY KEY AUTO_INCREMENT,
    class_code VARCHAR(10) NOT NULL COMMENT '班级代码,如:202501(兼容现有系统)',
    grade_id INT NOT NULL COMMENT '所属级号',
    class_number INT NOT NULL COMMENT '班号',
    class_name VARCHAR(20) NOT NULL COMMENT '班级名称,如:2025级1班',
    leader_wxid VARCHAR(50) COMMENT '班主任微信ID',
    leader_name VARCHAR(20) COMMENT '班主任姓名',
    roomid VARCHAR(50) COMMENT '微信班级群ID',
    is_active TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT NOW(),
    UNIQUE KEY uk_class_code (class_code),
    UNIQUE KEY uk_grade_class (grade_id, class_number),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='班级信息表';
""",
    # 6. 学生表
    "student": """
CREATE TABLE IF NOT EXISTS student (
    student_id VARCHAR(20) PRIMARY KEY COMMENT '学号',
    name VARCHAR(20) NOT NULL,
    gender ENUM('男', '女'),
    class_id INT NOT NULL COMMENT '当前班级ID',
    grade_id INT NOT NULL COMMENT '当前级号(留级时会变)',
    original_grade_id INT COMMENT '入学时级号(不变)',
    roomid VARCHAR(50) COMMENT '微信ID',
    status ENUM('在校', '休学', '转出', '毕业') DEFAULT '在校' COMMENT '学生状态',
    status_date DATE COMMENT '状态变更日期',
    enrollment_date DATE COMMENT '入学日期',
    is_active TINYINT DEFAULT 1,
    birthday DATE COMMENT '出生日期',
    phone VARCHAR(20) COMMENT '联系电话',
    email VARCHAR(50) COMMENT '电子邮箱',
    entrance_score DECIMAL(6,2) COMMENT '入学成绩(中考成绩)',
    entrance_rank INT COMMENT '入学排名',
    gaokao_score DECIMAL(6,2) COMMENT '高考成绩',
    gaokao_year INT COMMENT '高考年份',
    gaokao_rank INT COMMENT '高考排名',
    middle_school VARCHAR(100) COMMENT '初中学校名称',
    middle_school_city VARCHAR(50) COMMENT '初中学校所在城市',
    university_name VARCHAR(100) COMMENT '大学院校名称',
    university_type VARCHAR(20) COMMENT '院校类型:985/211/一本/二本/专科',
    university_major VARCHAR(50) COMMENT '录取专业',
    university_city VARCHAR(50) COMMENT '大学所在城市',
    profile_summary TEXT COMMENT '学生画像摘要(AI生成)',
    profile_tags JSON COMMENT '画像标签数组',
    profile_updated_at DATETIME COMMENT '画像更新时间',
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id),
    FOREIGN KEY (original_grade_id) REFERENCES grade(grade_id),
    INDEX idx_birthday (birthday) COMMENT '生日索引',
    INDEX idx_grade_status (grade_id, status) COMMENT '年级状态索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生信息表';
""",
    # 7. 教师表
    "teacher": """
CREATE TABLE IF NOT EXISTS teacher (
    teacher_id VARCHAR(20) PRIMARY KEY COMMENT '工号',
    name VARCHAR(20) NOT NULL,
    wxid VARCHAR(50) COMMENT '微信ID',
    subject VARCHAR(20) COMMENT '任教学科',
    course VARCHAR(50) COMMENT '课程',
    password_hash VARCHAR(255) COMMENT '密码哈希',
    raw_pwd VARCHAR(255) COMMENT '原始密码(历史兼容)',
    role VARCHAR(50) DEFAULT 'teacher' COMMENT '角色:admin/jiaowu/xuefa/cleader/teacher',
    level INT DEFAULT 0 COMMENT '权限等级',
    is_active TINYINT DEFAULT 1 COMMENT '登录权限',
    notice_enabled TINYINT DEFAULT 1 COMMENT '通知开关',
    is_password_changed TINYINT DEFAULT 0,
    score INT DEFAULT 50 COMMENT '会员积分',
    balance INT DEFAULT 0 COMMENT '会员余额',
    model VARCHAR(100) DEFAULT 'basic' COMMENT '会员模块',
    ai_flag TINYINT DEFAULT 0 COMMENT 'AI标记',
    birthday VARCHAR(20) COMMENT '生日',
    note TEXT COMMENT '会员备注',
    identity_type VARCHAR(20) DEFAULT 'teacher' COMMENT '身份类型:teacher/member',
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    INDEX idx_wxid (wxid) COMMENT '微信ID索引'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='教师信息表';
""",
    # 8. 教师任教班级映射表
    "teacher_teaching_class": """
CREATE TABLE IF NOT EXISTS teacher_teaching_class (
    id INT PRIMARY KEY AUTO_INCREMENT,
    teacher_id VARCHAR(20) NOT NULL COMMENT '教师ID',
    teacher_name VARCHAR(20) COMMENT '教师姓名',
    class_id INT NOT NULL COMMENT '任教班级ID',
    subject VARCHAR(20) COMMENT '任教学科',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    UNIQUE KEY uk_teacher_class_subject (teacher_id, class_id, subject),
    INDEX idx_teacher (teacher_id),
    INDEX idx_class (class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='教师任教班级映射表';
""",
    # 8. 角色表
    "role": """
CREATE TABLE IF NOT EXISTS role (
    role_id VARCHAR(20) PRIMARY KEY,
    role_name VARCHAR(50),
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色配置表';
""",
    # 9. 学生班级履历表
    "student_class_history": """
CREATE TABLE IF NOT EXISTS student_class_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    class_id INT NOT NULL COMMENT '班级ID',
    grade_id INT NOT NULL COMMENT '当时的级号',
    start_date DATE NOT NULL COMMENT '生效开始日期',
    end_date DATE COMMENT '生效结束日期,NULL=当前',
    change_reason VARCHAR(50) COMMENT '入学/调班/留级/复学/转入',
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id),
    INDEX idx_student_date (student_id, start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生班级履历表';
""",
    # 10. 学籍变动记录表
    "student_status_change": """
CREATE TABLE IF NOT EXISTS student_status_change (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    change_type VARCHAR(20) NOT NULL COMMENT '休学/复学/转入/转出/毕业',
    from_class_id INT,
    to_class_id INT,
    from_grade_id INT,
    to_grade_id INT,
    effective_date DATE NOT NULL,
    reason TEXT,
    approver VARCHAR(20),
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (from_class_id) REFERENCES class(class_id),
    FOREIGN KEY (to_class_id) REFERENCES class(class_id),
    FOREIGN KEY (from_grade_id) REFERENCES grade(grade_id),
    FOREIGN KEY (to_grade_id) REFERENCES grade(grade_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学籍变动记录表';
""",
    # 11. 日常事件类型表
    "daily_event_type": """
CREATE TABLE IF NOT EXISTS daily_event_type (
    event_id INT PRIMARY KEY AUTO_INCREMENT,
    event_name VARCHAR(50) NOT NULL,
    event_type TINYINT NOT NULL COMMENT '1=积极 2=消极',
    score INT NOT NULL COMMENT '加分/扣分',
    description TEXT,
    is_active TINYINT DEFAULT 1,
    CONSTRAINT chk_score_type CHECK (
        (event_type = 1 AND score > 0) OR
        (event_type = 2 AND score < 0)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='日常事件类型表';
""",
    # 12. 校级事件类型表
    "school_event_type": """
CREATE TABLE IF NOT EXISTS school_event_type (
    event_id INT PRIMARY KEY AUTO_INCREMENT,
    event_name VARCHAR(100) NOT NULL,
    event_level VARCHAR(20) COMMENT '校级/市级/省级/国家级',
    event_type TINYINT NOT NULL COMMENT '1=荣誉 2=处分',
    score INT NOT NULL,
    description TEXT,
    is_active TINYINT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='校级事件类型表';
""",
    # 13. 年级德育任务表
    "grade_moral_task": """
CREATE TABLE IF NOT EXISTS grade_moral_task (
    task_id INT PRIMARY KEY AUTO_INCREMENT,
    grade_id INT NOT NULL COMMENT '适用级号',
    task_name VARCHAR(100) NOT NULL,
    task_desc TEXT,
    score INT NOT NULL COMMENT '完成后获得分数',
    start_date DATE COMMENT '任务开始日期',
    end_date DATE COMMENT '任务结束日期',
    deadline_type VARCHAR(20) COMMENT 'semester/year/open',
    can_carryover TINYINT DEFAULT 1 COMMENT '是否允许结转',
    is_required TINYINT DEFAULT 1 COMMENT '是否必修',
    is_active TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='年级德育任务表';
""",
    # 14. 学生日常表现记录表
    "student_daily_record": """
CREATE TABLE IF NOT EXISTS student_daily_record (
    record_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    event_id INT NOT NULL,
    semester_id INT NOT NULL,
    record_date DATE NOT NULL,
    class_id INT NOT NULL COMMENT '记录时所属班级(快照)',
    grade_id INT NOT NULL COMMENT '记录时所属级号(快照)',
    score INT COMMENT '得分/扣分(冗余)',
    remark TEXT,
    recorder VARCHAR(20),
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (event_id) REFERENCES daily_event_type(event_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id),
    INDEX idx_student_semester (student_id, semester_id),
    UNIQUE KEY uk_student_event_date (student_id, event_id, record_date, semester_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生日常表现记录表';
""",
    # 15. 学生校级事件记录表
    "student_school_record": """
CREATE TABLE IF NOT EXISTS student_school_record (
    record_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    event_id INT NOT NULL,
    semester_id INT NOT NULL,
    get_date DATE NOT NULL,
    class_id INT NOT NULL COMMENT '记录时所属班级',
    grade_id INT NOT NULL COMMENT '记录时所属级号',
    score INT,
    proof VARCHAR(255) COMMENT '证书/文件编号',
    is_deleted TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (event_id) REFERENCES school_event_type(event_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生校级事件记录表';
""",
    # 16. 学生任务完成记录表
    "student_task_finish": """
CREATE TABLE IF NOT EXISTS student_task_finish (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    task_id INT NOT NULL COMMENT '任务ID',
    year_id INT NOT NULL COMMENT '当前所属学年',
    original_task_id INT COMMENT '原始任务ID',
    original_year_id INT COMMENT '原始学年',
    is_carried_over TINYINT DEFAULT 0 COMMENT '是否为结转任务',
    carryover_count INT DEFAULT 0 COMMENT '已结转次数',
    current_score DECIMAL(6,2) COMMENT '当前可得分数',
    status TINYINT DEFAULT 0 COMMENT '0=未完成 1=已完成 2=已作废',
    finish_date DATE,
    finish_year_id INT COMMENT '完成时学年',
    proof TEXT,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (task_id) REFERENCES grade_moral_task(task_id),
    FOREIGN KEY (year_id) REFERENCES school_year(year_id),
    FOREIGN KEY (original_task_id) REFERENCES grade_moral_task(task_id),
    FOREIGN KEY (original_year_id) REFERENCES school_year(year_id),
    FOREIGN KEY (finish_year_id) REFERENCES school_year(year_id),
    UNIQUE KEY uk_student_task_year (student_id, task_id, year_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生任务完成记录表';
""",
    # 17. 处分记录表
    "punishment_record": """
CREATE TABLE IF NOT EXISTS punishment_record (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    event_id INT NOT NULL COMMENT '处分事件类型',
    semester_id INT NOT NULL,
    punishment_date DATE NOT NULL,
    class_id INT NOT NULL,
    grade_id INT NOT NULL,
    score_deduct INT NOT NULL COMMENT '扣分',
    level VARCHAR(20) COMMENT '警告/严重警告/记过/留校察看',
    reason TEXT,
    recorder VARCHAR(20),
    is_revoked TINYINT DEFAULT 0 COMMENT '是否已撤销',
    revoke_date DATE,
    revoke_by VARCHAR(20),
    revoke_reason TEXT,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (event_id) REFERENCES school_event_type(event_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='处分记录表';
""",
    # 18. 集体事件表
    "collective_event": """
CREATE TABLE IF NOT EXISTS collective_event (
    event_id INT PRIMARY KEY AUTO_INCREMENT,
    event_name VARCHAR(100) NOT NULL COMMENT '事件名称',
    event_type VARCHAR(20) NOT NULL COMMENT '班级荣誉/集体活动/集体违纪',
    semester_id INT NOT NULL COMMENT '所属学期',
    event_date DATE NOT NULL COMMENT '事件日期',
    class_id INT NOT NULL COMMENT '班级ID',
    score INT NOT NULL COMMENT '每人得分/扣分',
    description TEXT COMMENT '事件描述',
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集体事件表';
""",
    # 19. 集体事件分配表
    "collective_event_distribution": """
CREATE TABLE IF NOT EXISTS collective_event_distribution (
    id INT PRIMARY KEY AUTO_INCREMENT,
    event_id INT NOT NULL COMMENT '集体事件ID',
    student_id VARCHAR(20) NOT NULL COMMENT '学生ID',
    class_id INT NOT NULL COMMENT '学生所属班级',
    score_assigned INT COMMENT '分配分数',
    is_participant TINYINT DEFAULT 1 COMMENT '是否实际参与',
    remark TEXT COMMENT '备注',
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (event_id) REFERENCES collective_event(event_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    UNIQUE KEY uk_event_student (event_id, student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='集体事件分配表';
""",
    # 20. 德育评价表
    "moral_evaluation": """
CREATE TABLE IF NOT EXISTS moral_evaluation (
    eval_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    semester_id INT NOT NULL,
    class_id INT NOT NULL COMMENT '评价时所属班级',
    grade_id INT NOT NULL COMMENT '评价时所属级号',
    total_score DECIMAL(6,2) DEFAULT 0 COMMENT '总分(可超100)',
    level VARCHAR(10) COMMENT '优秀/良好/合格/不合格',
    update_time DATETIME DEFAULT NOW(),
    UNIQUE KEY uk_student_semester (student_id, semester_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (grade_id) REFERENCES grade(grade_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='德育评价表';
""",
    # 21. 违纪累进规则表
    "violation_escalation_rule": """
CREATE TABLE IF NOT EXISTS violation_escalation_rule (
    rule_id INT PRIMARY KEY AUTO_INCREMENT,
    event_id INT NOT NULL COMMENT '违纪事件类型',
    time_window_days INT DEFAULT 90 COMMENT '统计时间窗口',
    escalation_rules JSON COMMENT '累进规则',
    FOREIGN KEY (event_id) REFERENCES daily_event_type(event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='违纪累进规则表';
""",
    # 22. 学期结转配置表
    "semester_carryover_config": """
CREATE TABLE IF NOT EXISTS semester_carryover_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    data_type VARCHAR(20) NOT NULL COMMENT 'honor/punishment/task',
    can_carryover TINYINT DEFAULT 1,
    score_factor DECIMAL(3,2) DEFAULT 1.00 COMMENT '结转分值系数',
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学期结转配置表';
""",
    # 23. 数据可见性配置表
    "data_visibility_config": """
CREATE TABLE IF NOT EXISTS data_visibility_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    data_type VARCHAR(50) NOT NULL,
    visible_roles JSON NOT NULL COMMENT '["admin", "xuefa"]',
    description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='数据可见性配置表';
""",
    # 24. 预警配置表
    "warning_config": """
CREATE TABLE IF NOT EXISTS warning_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    rule_name VARCHAR(50) NOT NULL,
    trigger_type VARCHAR(20) NOT NULL COMMENT 'score_threshold/count_threshold',
    trigger_value INT NOT NULL,
    notify_roles JSON COMMENT '["cleader", "xuefa"]',
    is_active TINYINT DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警配置表';
""",
    # 25. 预警日志表
    "warning_log": """
CREATE TABLE IF NOT EXISTS warning_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    rule_id INT NOT NULL,
    semester_id INT NOT NULL,
    warning_level VARCHAR(20) DEFAULT 'warning',
    message TEXT,
    is_read TINYINT DEFAULT 0,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (rule_id) REFERENCES warning_config(id),
    FOREIGN KEY (semester_id) REFERENCES semester(semester_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='预警日志表';
""",
    # 26. 任务结转日志表
    "task_carryover_log": """
CREATE TABLE IF NOT EXISTS task_carryover_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    original_task_id INT NOT NULL COMMENT '原始任务ID',
    from_year_id INT NOT NULL,
    to_year_id INT NOT NULL,
    carryover_index INT NOT NULL COMMENT '第几次结转',
    score_before DECIMAL(6,2),
    score_after DECIMAL(6,2),
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (original_task_id) REFERENCES grade_moral_task(task_id),
    FOREIGN KEY (from_year_id) REFERENCES school_year(year_id),
    FOREIGN KEY (to_year_id) REFERENCES school_year(year_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='任务结转日志表';
""",
    # 27. 操作日志表
    "moral_operation_log": """
CREATE TABLE IF NOT EXISTS moral_operation_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    operator VARCHAR(20) NOT NULL,
    operator_role VARCHAR(20),
    operation VARCHAR(20) NOT NULL COMMENT 'INSERT/UPDATE/DELETE/REVOKE',
    table_name VARCHAR(50) NOT NULL,
    record_id INT,
    semester_id INT,
    old_data JSON,
    new_data JSON,
    reason TEXT,
    ip_address VARCHAR(50),
    created_at DATETIME DEFAULT NOW(),
    INDEX idx_operator (operator),
    INDEX idx_table_record (table_name, record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='德育操作日志表';
""",
    # 28. 学生画像表
    "student_profile": """
CREATE TABLE IF NOT EXISTS student_profile (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    profile_version INT DEFAULT 1,
    profile_summary TEXT COMMENT '画像摘要',
    profile_tags JSON COMMENT '画像标签数组',
    strength_tags JSON COMMENT '优势标签',
    improvement_tags JSON COMMENT '待改进标签',
    risk_level VARCHAR(10) COMMENT '风险等级:low/medium/high',
    moral_score DECIMAL(5,2) COMMENT '品德评分',
    attitude_score DECIMAL(5,2) COMMENT '态度评分',
    social_score DECIMAL(5,2) COMMENT '社交评分',
    growth_score DECIMAL(5,2) COMMENT '成长评分',
    suggestions TEXT COMMENT '个性化建议',
    intervention_priority VARCHAR(10) COMMENT '干预优先级',
    data_source_summary JSON COMMENT '数据来源统计',
    generated_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    UNIQUE KEY uk_student_version (student_id, profile_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='学生画像表';
""",
    # 29. 画像历史表
    "student_profile_history": """
CREATE TABLE IF NOT EXISTS student_profile_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    profile_version INT NOT NULL,
    profile_data JSON COMMENT '完整画像数据快照',
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='画像历史表';
""",
    # 30. 画像配置表
    "profile_config": """
CREATE TABLE IF NOT EXISTS profile_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(50) NOT NULL,
    config_value JSON,
    description TEXT,
    UNIQUE KEY uk_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='画像配置表';
""",
    # 31. AI诊疗会话表
    "ai_consultation": """
CREATE TABLE IF NOT EXISTS ai_consultation (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    consultation_type VARCHAR(20) NOT NULL COMMENT 'academic/behavior/psychological/comprehensive',
    title VARCHAR(100),
    description TEXT,
    status VARCHAR(20) DEFAULT 'active' COMMENT 'active/resolved/closed',
    priority VARCHAR(10) DEFAULT 'normal' COMMENT 'urgent/high/normal/low',
    creator VARCHAR(20),
    assignee VARCHAR(20),
    participants JSON,
    ai_analysis TEXT COMMENT 'AI分析报告',
    ai_suggestions JSON COMMENT 'AI建议列表',
    ai_risk_assessment TEXT COMMENT '风险评估',
    solution TEXT,
    outcome VARCHAR(20),
    follow_up_date DATE,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    closed_at DATETIME,
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    INDEX idx_student_status (student_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI诊疗会话表';
""",
    # 32. AI诊疗对话记录表
    "ai_consultation_message": """
CREATE TABLE IF NOT EXISTS ai_consultation_message (
    id INT PRIMARY KEY AUTO_INCREMENT,
    consultation_id INT NOT NULL,
    message_type VARCHAR(20) NOT NULL COMMENT 'user/ai/system',
    content TEXT NOT NULL,
    sender VARCHAR(20),
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (consultation_id) REFERENCES ai_consultation(id),
    INDEX idx_consultation (consultation_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI诊疗对话记录表';
""",
    # 33. 生日提醒表
    "birthday_reminder": """
CREATE TABLE IF NOT EXISTS birthday_reminder (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id VARCHAR(20) NOT NULL,
    reminder_date DATE NOT NULL COMMENT '提醒日期',
    reminder_type VARCHAR(20) DEFAULT 'birthday' COMMENT 'birthday/special',
    message TEXT COMMENT '祝福内容',
    is_sent TINYINT DEFAULT 0 COMMENT '是否已发送',
    sent_at DATETIME,
    recipient_type VARCHAR(20) COMMENT 'student/parent/teacher',
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    INDEX idx_reminder_date (reminder_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='生日提醒表';
""",
    # 34. 生日提醒配置表
    "birthday_reminder_config": """
CREATE TABLE IF NOT EXISTS birthday_reminder_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(50) NOT NULL,
    config_value JSON,
    description TEXT,
    UNIQUE KEY uk_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='生日提醒配置表';
""",
    # 35. 系统配置表
    "moral_config": """
CREATE TABLE IF NOT EXISTS moral_config (
    config_id INT PRIMARY KEY AUTO_INCREMENT,
    config_key VARCHAR(50) NOT NULL,
    config_value TEXT,
    description TEXT,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    UNIQUE KEY uk_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='德育系统配置表';
""",
    # 36. API权限模块表
    "api_permission_module": """
CREATE TABLE IF NOT EXISTS api_permission_module (
    id INT PRIMARY KEY AUTO_INCREMENT,
    module_key VARCHAR(80) NOT NULL COMMENT '模块标识',
    module_name VARCHAR(80) NOT NULL COMMENT '模块名称',
    parent_id INT COMMENT '父模块ID',
    allowed_roles JSON NOT NULL COMMENT '模块默认允许角色',
    min_level INT DEFAULT 0 COMMENT '模块默认最低等级',
    policy_mode VARCHAR(30) DEFAULT 'role_and_level' COMMENT '鉴权策略',
    description TEXT,
    sort_order INT DEFAULT 0,
    is_active TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    UNIQUE KEY uk_module_key (module_key),
    INDEX idx_module_parent (parent_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API权限模块表';
""",
    # 37. API权限配置表
    "api_permission_config": """
CREATE TABLE IF NOT EXISTS api_permission_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    api_path VARCHAR(100) NOT NULL COMMENT 'API路径',
    api_name VARCHAR(50) NOT NULL COMMENT 'API名称',
    api_group VARCHAR(30) NOT NULL COMMENT 'API分组',
    allowed_roles JSON NOT NULL COMMENT '允许访问的角色列表',
    min_level INT DEFAULT 0 COMMENT '最低等级要求',
    module_id INT COMMENT '所属模块ID',
    http_method VARCHAR(10) DEFAULT '*' COMMENT 'HTTP方法',
    match_type VARCHAR(20) DEFAULT 'exact' COMMENT '路径匹配方式',
    policy_mode VARCHAR(30) DEFAULT 'role_and_level' COMMENT '鉴权策略',
    inherit_from_module TINYINT DEFAULT 0 COMMENT '是否继承模块权限',
    is_public TINYINT DEFAULT 0 COMMENT '是否无需鉴权',
    enforce_backend TINYINT DEFAULT 1 COMMENT '是否用于后端鉴权',
    data_scope_rules JSON COMMENT '角色数据范围规则',
    target_scope_rules JSON COMMENT '角色目标对象范围规则',
    description TEXT,
    is_active TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    UNIQUE KEY uk_api_path (api_path),
    INDEX idx_api_group (api_group),
    INDEX idx_api_module (module_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='API权限配置表';
""",
    # 38. AI诊疗模板表
    "ai_consultation_template": """
CREATE TABLE IF NOT EXISTS ai_consultation_template (
    id INT PRIMARY KEY AUTO_INCREMENT,
    template_type VARCHAR(20) NOT NULL COMMENT 'academic/behavior/psychological',
    template_name VARCHAR(50) NOT NULL COMMENT '模板名称',
    prompt_template TEXT NOT NULL COMMENT 'AI提示词模板',
    suggested_questions JSON COMMENT '建议提问列表',
    response_format JSON COMMENT '回复格式配置',
    is_active TINYINT DEFAULT 1,
    created_at DATETIME DEFAULT NOW()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI诊疗模板表';
""",
}

# 初始数据插入SQL
INITIAL_DATA_SQL = [
    # 年级等级配置
    "INSERT IGNORE INTO grade_level_config VALUES (1, 0, '高一'), (2, 1, '高二'), (3, 2, '高三');",
    # 角色配置
    """INSERT IGNORE INTO role VALUES
    ('admin', '管理员', '系统管理员'),
    ('jiaowu', '教发部', '教师发展部,负责教学质量、教师管理'),
    ('xuefa', '学发部', '学生发展部,负责德育评价'),
    ('cleader', '班主任', '班级管理者'),
    ('teacher', '教师', '普通教师'),
    ('student', '学生', '学生'),
    ('parent', '家长', '学生家长');""",
    # 学期结转配置
    """INSERT IGNORE INTO semester_carryover_config (data_type, can_carryover, score_factor, description) VALUES
    ('honor', 0, 1.00, '荣誉不结转,记录保留在原学期'),
    ('punishment', 0, 1.00, '处分不结转,记录保留在原学期'),
    ('task_unfinished', 1, 0.60, '未完成任务可结转,每次×60%');""",
    # 数据可见性配置
    """INSERT IGNORE INTO data_visibility_config (data_type, visible_roles, description) VALUES
    ('punishment_record', '["admin", "xuefa", "jiaowu"]', '处分记录'),
    ('daily_negative', '["admin", "xuefa", "jiaowu", "cleader"]', '消极事件'),
    ('daily_positive', '["admin", "xuefa", "jiaowu", "cleader", "teacher"]', '积极事件'),
    ('honor_record', '["admin", "xuefa", "jiaowu", "cleader", "teacher", "student", "parent"]', '荣誉记录'),
    ('evaluation_score', '["admin", "xuefa", "jiaowu", "cleader", "student", "parent"]', '评价得分');""",
    # 预警配置
    """INSERT IGNORE INTO warning_config (rule_name, trigger_type, trigger_value, notify_roles) VALUES
    ('德育分过低', 'score_threshold', 50, '["cleader", "xuefa", "jiaowu"]'),
    ('扣分过多', 'score_threshold', -20, '["cleader", "xuefa", "jiaowu"]'),
    ('违纪次数过多', 'count_threshold', 5, '["cleader", "xuefa", "jiaowu"]');""",
    # 累进预警配置
    """INSERT IGNORE INTO warning_config (rule_name, trigger_type, trigger_value, notify_roles, is_active) VALUES
    ('累进警告', 'escalation_warning', 3, '["cleader"]', 1),
    ('累进通报批评', 'escalation_criticism', 5, '["cleader", "xuefa"]', 1),
    ('累进记过', 'escalation_demerit', 10, '["cleader", "xuefa"]', 1);""",
    # 累进规则示例(需要根据实际event_id调整)
    """INSERT IGNORE INTO violation_escalation_rule (rule_id, event_id, time_window_days, escalation_rules) VALUES
    (1, 1, 90, '{"rules": [{"threshold": 3, "action": "warning", "description": "警告", "notify_roles": ["cleader"], "score_penalty": 0}, {"threshold": 5, "action": "criticism", "description": "通报批评", "notify_roles": ["cleader", "xuefa"], "score_penalty": -5}, {"threshold": 10, "action": "demerit", "description": "记过", "notify_roles": ["cleader", "xuefa"], "score_penalty": -10, "auto_create_punishment": true, "punishment_level": 2}], "reset_on_action": false}');""",
    # 画像配置
    """INSERT IGNORE INTO profile_config VALUES
    (1, 'tag_definitions', '["责任担当", "诚实守信", "乐于助人", "勤奋刻苦", "积极进取", "团结协作", "遵纪守法", "文明礼貌", "关爱他人", "勇于创新"]', '画像标签定义'),
    (2, 'update_frequency', '{"type": "semester", "min_records": 5}', '更新频率配置'),
    (3, 'risk_thresholds', '{"high": {"negative_count": 10, "punishment_count": 2}, "medium": {"negative_count": 5, "punishment_count": 1}}', '风险阈值配置'),
    (4, 'scoring_weights', '{"moral": {"base": 80, "positive_weight": 2, "negative_weight": 3}, "attitude": {"base": 80, "completion_weight": 40}, "social": {"base": 75, "collective_weight": 2}, "growth": {"base": 75, "honor_weight": 5}}', '评分权重配置'),
    (5, 'tag_rules', '{"积极进取": {"positive_count_min": 5}, "遵纪守法": {"negative_count_max": 2}, "勤奋刻苦": {"positive_negative_ratio_min": 2}, "责任担当": {"task_completion_rate_min": 0.8}, "诚实守信": {"negative_count_max": 0}, "乐于助人": {"collective_count_min": 3}, "团结协作": {"collective_count_min": 5}, "文明礼貌": {"positive_rate_min": 0.8}}', '标签生成规则');""",
    # 生日提醒配置
    """INSERT IGNORE INTO birthday_reminder_config VALUES
    (1, 'reminder_days_before', '3', '提前多少天提醒'),
    (2, 'reminder_time', '{"hour": 8, "minute": 0}', '提醒时间'),
    (3, 'message_template', '{"student": "祝你生日快乐！愿你学业进步,前程似锦！", "parent": "您的孩子即将迎来生日,祝家庭幸福美满！"}', '祝福模板');""",
    # AI诊疗模板
    """INSERT IGNORE INTO ai_consultation_template (template_type, template_name, prompt_template, suggested_questions, response_format, is_active) VALUES
    ('academic', '学业问题诊断', '学生{student_name}近期出现学业问题:{description}.请分析可能的原因并提供解决方案.', '["学习成绩下降", "作业完成困难", "课堂注意力不集中"]', '{}', 1),
    ('behavior', '行为问题诊断', '学生{student_name}出现行为问题:{description}.请分析原因并提供干预建议.', '["迟到早退", "违纪行为", "人际关系冲突"]', '{}', 1),
    ('psychological', '心理问题诊断', '学生{student_name}可能出现心理困扰:{description}.请提供初步评估和建议.', '["情绪波动", "社交退缩", "压力过大"]', '{}', 1);""",
]


def create_database_if_not_exists():
    """创建数据库(如果不存在)"""
    from config.config import Config
    config = Config()
    db_config = config.get_config("moral_db", "moral.yaml")

    # 连接MySQL服务器(不指定数据库)
    connection = mysql.connector.connect(
        host=db_config["host"],
        user=db_config["user"],
        password=db_config["password"]
    )
    cursor = connection.cursor()

    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        logger.info(f"Database '{db_config['database']}' created or already exists")
    finally:
        cursor.close()
        connection.close()


def create_tables(drop_existing: bool = False):
    """
    创建所有表

    Args:
        drop_existing: 是否先删除现有表
    """
    # 先创建数据库
    create_database_if_not_exists()

    # 获取连接池
    pool = get_connection_pool("moral", "moral.yaml")
    connection = pool.get_connection()
    cursor = connection.cursor()

    try:
        if drop_existing:
            logger.warning("Dropping existing tables...")
            # 按相反顺序删除(避免外键约束问题)
            table_order_reverse = list(TABLES_SQL.keys())[::-1]
            for table_name in table_order_reverse:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"Table '{table_name}' dropped")

        # 按定义顺序创建表
        logger.info("Creating tables...")
        for table_name, sql in TABLES_SQL.items():
            cursor.execute(sql)
            logger.info(f"Table '{table_name}' created")

        # 插入初始数据
        logger.info("Inserting initial data...")
        for sql in INITIAL_DATA_SQL:
            cursor.execute(sql)

        connection.commit()
        logger.info("All tables created successfully!")

        # 显示创建的表数量
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        logger.info(f"Total tables in database: {len(tables)}")

    except Error as e:
        connection.rollback()
        logger.error(f"Error creating tables: {e}")
        raise
    finally:
        cursor.close()
        connection.close()


def verify_tables():
    """验证MySQL表创建结果"""
    from utils.mysql_db import MySQLDatabase

    with MySQLDatabase() as db:
        # 检查表数量
        result = db.query_value("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'moral_evaluation'")
        logger.info(f"Tables count: {result}")

        # 检查各表记录数
        for table_name in TABLES_SQL.keys():
            try:
                count = db.query_value(f"SELECT COUNT(*) FROM {table_name}")
                logger.info(f"Table '{table_name}': {count} records")
            except Error as e:
                logger.warning(f"Table '{table_name}' check failed: {e}")


# SQLite 初始数据插入SQL
SQLite_INITIAL_DATA_SQL = [
    # 年级等级配置
    "INSERT OR IGNORE INTO grade_level_config VALUES (1, 0, '高一'), (2, 1, '高二'), (3, 2, '高三');",
    # 角色配置
    """INSERT OR IGNORE INTO role VALUES
    ('admin', '管理员', '系统管理员'),
    ('jiaowu', '教发部', '教师发展部,负责教学质量、教师管理'),
    ('xuefa', '学发部', '学生发展部,负责德育评价'),
    ('cleader', '班主任', '班级管理者'),
    ('teacher', '教师', '普通教师'),
    ('student', '学生', '学生'),
    ('parent', '家长', '学生家长');""",
    # 学期结转配置
    """INSERT OR IGNORE INTO semester_carryover_config (id, data_type, can_carryover, score_factor, description) VALUES
    (1, 'honor', 0, 1.00, '荣誉不结转,记录保留在原学期'),
    (2, 'punishment', 0, 1.00, '处分不结转,记录保留在原学期'),
    (3, 'task_unfinished', 1, 0.60, '未完成任务可结转,每次×60%');""",
    # 数据可见性配置
    """INSERT OR IGNORE INTO data_visibility_config (id, data_type, visible_roles, description) VALUES
    (1, 'punishment_record', '["admin", "xuefa", "jiaowu"]', '处分记录'),
    (2, 'daily_negative', '["admin", "xuefa", "jiaowu", "cleader"]', '消极事件'),
    (3, 'daily_positive', '["admin", "xuefa", "jiaowu", "cleader", "teacher"]', '积极事件'),
    (4, 'honor_record', '["admin", "xuefa", "jiaowu", "cleader", "teacher", "student", "parent"]', '荣誉记录'),
    (5, 'evaluation_score', '["admin", "xuefa", "jiaowu", "cleader", "student", "parent"]', '评价得分');""",
    # 预警配置
    """INSERT OR IGNORE INTO warning_config (id, rule_name, trigger_type, trigger_value, notify_roles, is_active) VALUES
    (1, '德育分过低', 'score_threshold', 50, '["cleader", "xuefa", "jiaowu"]', 1),
    (2, '扣分过多', 'score_threshold', -20, '["cleader", "xuefa", "jiaowu"]', 1),
    (3, '违纪次数过多', 'count_threshold', 5, '["cleader", "xuefa", "jiaowu"]', 1);""",
    # 累进预警配置
    """INSERT OR IGNORE INTO warning_config (id, rule_name, trigger_type, trigger_value, notify_roles, is_active) VALUES
    (4, '累进警告', 'escalation_warning', 3, '["cleader"]', 1),
    (5, '累进通报批评', 'escalation_criticism', 5, '["cleader", "xuefa"]', 1),
    (6, '累进记过', 'escalation_demerit', 10, '["cleader", "xuefa"]', 1);""",
    # 累进规则示例(需要根据实际event_id调整)
    """INSERT OR IGNORE INTO violation_escalation_rule (rule_id, event_id, time_window_days, escalation_rules) VALUES
    (1, 1, 90, '{"rules": [{"threshold": 3, "action": "warning", "description": "警告", "notify_roles": ["cleader"], "score_penalty": 0}, {"threshold": 5, "action": "criticism", "description": "通报批评", "notify_roles": ["cleader", "xuefa"], "score_penalty": -5}, {"threshold": 10, "action": "demerit", "description": "记过", "notify_roles": ["cleader", "xuefa"], "score_penalty": -10, "auto_create_punishment": true, "punishment_level": 2}], "reset_on_action": false}');""",
    # 画像配置
    """INSERT OR IGNORE INTO profile_config VALUES
    (1, 'tag_definitions', '["责任担当", "诚实守信", "乐于助人", "勤奋刻苦", "积极进取", "团结协作", "遵纪守法", "文明礼貌", "关爱他人", "勇于创新"]', '画像标签定义'),
    (2, 'update_frequency', '{"type": "semester", "min_records": 5}', '更新频率配置'),
    (3, 'risk_thresholds', '{"high": {"negative_count": 10, "punishment_count": 2}, "medium": {"negative_count": 5, "punishment_count": 1}}', '风险阈值配置'),
    (4, 'scoring_weights', '{"moral": {"base": 80, "positive_weight": 2, "negative_weight": 3}, "attitude": {"base": 80, "completion_weight": 40}, "social": {"base": 75, "collective_weight": 2}, "growth": {"base": 75, "honor_weight": 5}}', '评分权重配置'),
    (5, 'tag_rules', '{"积极进取": {"positive_count_min": 5}, "遵纪守法": {"negative_count_max": 2}, "勤奋刻苦": {"positive_negative_ratio_min": 2}, "责任担当": {"task_completion_rate_min": 0.8}, "诚实守信": {"negative_count_max": 0}, "乐于助人": {"collective_count_min": 3}, "团结协作": {"collective_count_min": 5}, "文明礼貌": {"positive_rate_min": 0.8}}', '标签生成规则');""",
    # 生日提醒配置
    """INSERT OR IGNORE INTO birthday_reminder_config VALUES
    (1, 'reminder_days_before', '3', '提前多少天提醒'),
    (2, 'reminder_time', '{"hour": 8, "minute": 0}', '提醒时间'),
    (3, 'message_template', '{"student": "祝你生日快乐！愿你学业进步,前程似锦！", "parent": "您的孩子即将迎来生日,祝家庭幸福美满！"}', '祝福模板');""",
    # AI诊疗模板
    """INSERT OR IGNORE INTO ai_consultation_template (id, template_type, template_name, prompt_template, suggested_questions, response_format, is_active) VALUES
    (1, 'academic', '学业问题诊断', '学生{student_name}近期出现学业问题:{description}.请分析可能的原因并提供解决方案.', '["学习成绩下降", "作业完成困难", "课堂注意力不集中"]', '{}', 1),
    (2, 'behavior', '行为问题诊断', '学生{student_name}出现行为问题:{description}.请分析原因并提供干预建议.', '["迟到早退", "违纪行为", "人际关系冲突"]', '{}', 1),
    (3, 'psychological', '心理问题诊断', '学生{student_name}可能出现心理困扰:{description}.请提供初步评估和建议.', '["情绪波动", "社交退缩", "压力过大"]', '{}', 1);""",
]


def ensure_sqlite_schema(conn: sqlite3.Connection):
    """补齐已有 SQLite 数据库的增量字段."""
    collective_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(collective_event)").fetchall()
    }
    if collective_columns and "class_id" not in collective_columns:
        logger.info("Adding missing SQLite column: collective_event.class_id")
        conn.execute("ALTER TABLE collective_event ADD COLUMN class_id INTEGER")

    teacher_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(teacher)").fetchall()
    }
    if "alias" in teacher_columns:
        conn.execute(
            "UPDATE teacher SET name = alias WHERE (name IS NULL OR name = '') AND alias IS NOT NULL AND alias != ''"
        )
        try:
            logger.info("Dropping obsolete SQLite column: teacher.alias")
            conn.execute("ALTER TABLE teacher DROP COLUMN alias")
            teacher_columns.remove("alias")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not drop obsolete teacher.alias column: {e}")
    if "member_active" in teacher_columns:
        conn.execute(
            "UPDATE teacher SET is_active = COALESCE(is_active, member_active) WHERE is_active IS NULL"
        )
        try:
            logger.info("Dropping obsolete SQLite column: teacher.member_active")
            conn.execute("ALTER TABLE teacher DROP COLUMN member_active")
            teacher_columns.remove("member_active")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not drop obsolete teacher.member_active column: {e}")
    if "uuid" in teacher_columns:
        conn.execute(
            "UPDATE teacher SET wxid = uuid WHERE (wxid IS NULL OR wxid = '') AND uuid IS NOT NULL AND uuid != ''"
        )
        conn.execute("DROP INDEX IF EXISTS idx_teacher_uuid")
        try:
            logger.info("Dropping obsolete SQLite column: teacher.uuid")
            conn.execute("ALTER TABLE teacher DROP COLUMN uuid")
            teacher_columns.remove("uuid")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not drop obsolete teacher.uuid column: {e}")
    if "priority" in teacher_columns:
        try:
            logger.info("Dropping obsolete SQLite column: teacher.priority")
            conn.execute("ALTER TABLE teacher DROP COLUMN priority")
            teacher_columns.remove("priority")
        except sqlite3.OperationalError as e:
            logger.warning(f"Could not drop obsolete teacher.priority column: {e}")

    teacher_additions = {
        "course": "TEXT",
        "raw_pwd": "TEXT",
        "score": "INTEGER DEFAULT 50",
        "balance": "INTEGER DEFAULT 0",
        "model": "TEXT DEFAULT 'basic'",
        "ai_flag": "INTEGER DEFAULT 0",
        "birthday": "TEXT",
        "note": "TEXT",
        "identity_type": "TEXT DEFAULT 'teacher'",
    }
    for column, definition in teacher_additions.items():
        if teacher_columns and column not in teacher_columns:
            logger.info(f"Adding missing SQLite column: teacher.{column}")
            conn.execute(f"ALTER TABLE teacher ADD COLUMN {column} {definition}")

    if teacher_columns:
        conn.execute("UPDATE teacher SET identity_type = 'teacher' WHERE identity_type IS NULL")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_teacher_identity_type ON teacher(identity_type)")

        member_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "databases", "member.db")
        if os.path.exists(member_db_path):
            try:
                legacy_conn = sqlite3.connect(member_db_path)
                legacy_conn.row_factory = sqlite3.Row
                has_member_table = legacy_conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='member'"
                ).fetchone()
                if not has_member_table:
                    legacy_conn.close()
                    legacy_conn = None
                    raise FileNotFoundError("legacy member table removed")
                legacy_rows = legacy_conn.execute("SELECT * FROM member").fetchall()
                migrated = 0
                for row in legacy_rows:
                    member = dict(row)
                    uuid = member.get("uuid") or member.get("wxid")
                    wxid = member.get("wxid") or uuid
                    alias = member.get("alias") or uuid
                    if not uuid:
                        continue
                    existing = conn.execute(
                        "SELECT teacher_id FROM teacher WHERE wxid = ? OR name = ?",
                        (wxid, alias),
                    ).fetchone()
                    if existing:
                        conn.execute(
                            """UPDATE teacher
                            SET wxid = COALESCE(NULLIF(wxid, ''), ?),
                                name = CASE WHEN identity_type = 'teacher' THEN name ELSE ? END,
                                score = ?, balance = ?,
                                level = CASE WHEN level IS NULL OR level = 0 THEN ? ELSE level END,
                                model = ?, ai_flag = ?, birthday = ?,
                                is_active = CASE WHEN identity_type = 'member' THEN ? ELSE is_active END,
                                note = COALESCE(NULLIF(note, ''), ?),
                                updated_at = datetime('now', 'localtime')
                            WHERE teacher_id = ?""",
                            (
                                wxid, alias,
                                member.get("score", 50), member.get("balance", 0), member.get("level", 1),
                                member.get("model", "basic"), member.get("ai_flag", 0), member.get("birthday", ""),
                                member.get("active", 1), member.get("note", ""),
                                existing[0],
                            ),
                        )
                    else:
                        safe_uuid = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(uuid))[:120]
                        conn.execute(
                            """INSERT INTO teacher
                            (teacher_id, name, wxid, role, level, is_active, notice_enabled,
                             score, balance, model, ai_flag, birthday,
                             note, identity_type, created_at)
                            VALUES (?, ?, ?, 'member', ?, ?, 1, ?, ?, ?, ?, ?, ?, 'member',
                                    COALESCE(?, datetime('now', 'localtime')))""",
                            (
                                f"M_{safe_uuid}", alias, wxid,
                                member.get("level", 1), member.get("active", 1),
                                member.get("score", 50), member.get("balance", 0),
                                member.get("model", "basic"), member.get("ai_flag", 0), member.get("birthday", ""),
                                member.get("note", ""),
                                member.get("create_at"),
                            ),
                        )
                    migrated += 1
                legacy_conn.close()
                if migrated:
                    logger.info(f"Migrated legacy member rows into teacher: {migrated}")
            except FileNotFoundError:
                pass
            except Exception as e:
                if 'legacy_conn' in locals() and legacy_conn:
                    legacy_conn.close()
                logger.warning(f"Skip legacy member migration: {e}")

        auth_db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "databases", "auth.db")
        if os.path.exists(auth_db_path):
            try:
                auth_conn = sqlite3.connect(auth_db_path)
                auth_conn.row_factory = sqlite3.Row
                auth_rows = auth_conn.execute("SELECT * FROM teacher").fetchall()
                migrated = 0
                for row in auth_rows:
                    teacher = dict(row)
                    name = teacher.get("name")
                    if not name:
                        continue
                    existing = conn.execute(
                        "SELECT teacher_id FROM teacher WHERE name = ? AND COALESCE(identity_type, 'teacher') = 'teacher'",
                        (name,),
                    ).fetchone()
                    teacher_id = existing[0] if existing else f"T_{''.join(ch if ch.isalnum() or ch in '_-' else '_' for ch in str(name))[:120]}"
                    conn.execute(
                        """INSERT INTO teacher
                        (teacher_id, name, subject, course, password_hash, raw_pwd, role, level,
                         is_active, notice_enabled, is_password_changed, identity_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'teacher')
                        ON CONFLICT(teacher_id) DO UPDATE SET
                            name = COALESCE(NULLIF(teacher.name, ''), excluded.name),
                            subject = COALESCE(NULLIF(teacher.subject, ''), excluded.subject),
                            course = COALESCE(NULLIF(teacher.course, ''), excluded.course),
                            password_hash = COALESCE(NULLIF(teacher.password_hash, ''), excluded.password_hash),
                            raw_pwd = COALESCE(NULLIF(teacher.raw_pwd, ''), excluded.raw_pwd),
                            role = COALESCE(NULLIF(teacher.role, ''), excluded.role),
                            level = COALESCE(teacher.level, excluded.level),
                            is_active = COALESCE(teacher.is_active, excluded.is_active),
                            notice_enabled = COALESCE(teacher.notice_enabled, excluded.notice_enabled),
                            is_password_changed = COALESCE(teacher.is_password_changed, excluded.is_password_changed),
                            identity_type = 'teacher',
                            updated_at = datetime('now', 'localtime')""",
                        (
                            teacher_id,
                            name,
                            teacher.get("subject", ""),
                            teacher.get("course", ""),
                            teacher.get("pwd", ""),
                            teacher.get("raw_pwd", ""),
                            teacher.get("role", "teacher"),
                            teacher.get("level", 10),
                            teacher.get("active", 1),
                            teacher.get("notice", 1),
                            teacher.get("is_password_changed", 0),
                        ),
                    )
                    migrated += 1
                auth_conn.close()
                if migrated:
                    logger.info(f"Migrated auth teacher rows into moral.teacher: {migrated}")
            except Exception as e:
                logger.warning(f"Skip auth teacher migration: {e}")

    # grade 表新增 leader_ids, leader_names 字段(支持年级主任多人)
    grade_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(grade)").fetchall()
    }
    grade_additions = {
        "leader_ids": "TEXT DEFAULT ''",
        "leader_names": "TEXT DEFAULT ''",
    }
    for column, definition in grade_additions.items():
        if grade_columns and column not in grade_columns:
            logger.info(f"Adding missing SQLite column: grade.{column}")
            conn.execute(f"ALTER TABLE grade ADD COLUMN {column} {definition}")

    # class 表新增 leader_ids, leader_names 字段(支持班主任多人)
    class_columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info(class)").fetchall()
    }
    class_additions = {
        "leader_ids": "TEXT DEFAULT ''",
        "leader_names": "TEXT DEFAULT ''",
    }
    for column, definition in class_additions.items():
        if class_columns and column not in class_columns:
            logger.info(f"Adding missing SQLite column: class.{column}")
            conn.execute(f"ALTER TABLE class ADD COLUMN {column} {definition}")

    permission_rows = [
        (
            "/api/moral/daily-records/update",
            "更新日常记录",
            "日常表现",
            '["admin", "jiaowu", "xuefa", "cleader", "teacher"]',
            10,
            "更新自己创建的日常表现记录",
        ),
        (
            "/api/moral/daily-records/delete",
            "删除日常记录",
            "日常表现",
            '["admin", "jiaowu", "xuefa", "cleader", "teacher"]',
            10,
            "删除自己创建的日常表现记录",
        ),
        (
            "/api/moral/collective-events",
            "集体事件管理",
            "集体事件",
            '["admin", "jiaowu", "xuefa", "cleader"]',
            30,
            "集体事件列表、详情和分配管理",
        ),
        (
            "/api/moral/collective-events/create",
            "创建集体事件",
            "集体事件",
            '["admin", "jiaowu", "xuefa", "cleader"]',
            30,
            "创建班级集体事件并分配到学生",
        ),
        (
            "/api/moral/collective-events/update",
            "更新集体事件",
            "集体事件",
            '["admin", "jiaowu", "xuefa", "cleader"]',
            30,
            "更新集体事件基本信息",
        ),
        (
            "/api/moral/collective-events/delete",
            "删除集体事件",
            "集体事件",
            '["admin", "jiaowu", "xuefa", "cleader"]',
            30,
            "删除集体事件及分配记录",
        ),
        (
            "/api/moral/collective-events/distributions/update",
            "调整集体事件分配",
            "集体事件",
            '["admin", "jiaowu", "xuefa", "cleader"]',
            30,
            "调整学生是否参与集体事件及实际得分",
        ),
        (
            "/api/moral/moment-records/update",
            "更新点滴记录",
            "点滴记录",
            '["admin", "jiaowu", "xuefa", "cleader", "teacher"]',
            10,
            "更新自己创建的点滴记录",
        ),
        (
            "/api/moral/moment-records/delete",
            "删除点滴记录",
            "点滴记录",
            '["admin", "jiaowu", "xuefa", "cleader", "teacher"]',
            10,
            "删除自己创建的点滴记录",
        ),
        (
            "/api/moral/profiles/student",
            "获取学生画像",
            "学生画像",
            '["admin", "jiaowu", "xuefa", "cleader"]',
            30,
            "获取学生画像",
        ),
        (
            "/api/moral/evaluations/class",
            "班级评价查询",
            "评价查询",
            '["admin", "jiaowu", "xuefa", "cleader"]',
            30,
            "获取班级德育评价汇总",
        ),
    ]
    conn.executemany(
        """INSERT OR IGNORE INTO api_permission_config
        (api_path, api_name, api_group, allowed_roles, min_level, description)
        VALUES (?, ?, ?, ?, ?, ?)""",
        permission_rows,
    )
    conn.execute(
        """UPDATE api_permission_config
        SET allowed_roles = ?, min_level = ?, description = ?
        WHERE api_path = ?""",
        (
            '["admin", "jiaowu", "xuefa", "cleader", "teacher"]',
            10,
            "更新自己创建的日常表现记录",
            "/api/moral/daily-records/update",
        ),
    )
    conn.execute(
        """UPDATE api_permission_config
        SET allowed_roles = ?, min_level = ?, description = ?
        WHERE api_path = ?""",
        (
            '["admin", "jiaowu", "xuefa", "cleader", "teacher"]',
            10,
            "删除自己创建的日常表现记录",
            "/api/moral/daily-records/delete",
        ),
    )
    conn.execute(
        """UPDATE api_permission_config
        SET allowed_roles = ?, min_level = ?, description = ?
        WHERE api_path = ?""",
        (
            '["admin", "jiaowu", "xuefa", "cleader", "teacher"]',
            10,
            "更新自己创建的点滴记录",
            "/api/moral/moment-records/update",
        ),
    )
    conn.execute(
        """UPDATE api_permission_config
        SET allowed_roles = ?, min_level = ?, description = ?
        WHERE api_path = ?""",
        (
            '["admin", "jiaowu", "xuefa", "cleader", "teacher"]',
            10,
            "删除自己创建的点滴记录",
            "/api/moral/moment-records/delete",
        ),
    )
    conn.execute(
        """UPDATE api_permission_config
        SET allowed_roles = ?, min_level = ?
        WHERE api_path = ?""",
        ('["admin", "jiaowu", "xuefa", "cleader"]', 30, "/api/moral/tasks"),
    )
    conn.execute(
        """UPDATE api_permission_config
        SET allowed_roles = ?, min_level = ?
        WHERE api_path = ?""",
        ('["admin", "jiaowu", "xuefa", "cleader"]', 30, "/api/moral/tasks/finish"),
    )
    conn.execute(
        """UPDATE api_permission_config
        SET allowed_roles = ?, min_level = ?
        WHERE api_path = ?""",
        ('["admin", "jiaowu", "xuefa", "cleader"]', 30, "/api/moral/evaluations/class"),
    )


def create_sqlite_tables(db_path: str = None, drop_existing: bool = False):
    """
    创建SQLite表

    Args:
        db_path: 数据库文件路径,默认为 databases/moral.db
        drop_existing: 是否先删除现有表
    """
    from utils.sqlite_moral_db import MoralDatabase, get_moral_db_path

    db_path = db_path or get_moral_db_path()

    # 确保数据库目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        if drop_existing:
            logger.warning("Dropping existing SQLite tables...")
            # 按相反顺序删除(避免外键约束问题)
            table_order_reverse = list(SQLite_TABLES_SQL.keys())[::-1]
            for table_name in table_order_reverse:
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                logger.info(f"SQLite table '{table_name}' dropped")

        # 按定义顺序创建表
        logger.info("Creating SQLite tables...")
        for table_name, sql in SQLite_TABLES_SQL.items():
            # SQLite 每条 CREATE 语句需要分开执行(包含 CREATE INDEX)
            statements = sql.strip().split(';')
            for stmt in statements:
                stmt = stmt.strip()
                if stmt:
                    conn.execute(stmt)
            logger.info(f"SQLite table '{table_name}' created")

        ensure_sqlite_schema(conn)

        # 插入初始数据
        logger.info("Inserting SQLite initial data...")
        for sql in SQLite_INITIAL_DATA_SQL:
            conn.execute(sql)

        conn.commit()
        logger.info("All SQLite tables created successfully!")

        # 显示创建的表数量
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()
        logger.info(f"Total SQLite tables: {len(tables)}")

    except Exception as e:
        conn.rollback()
        logger.error(f"Error creating SQLite tables: {e}")
        raise
    finally:
        conn.close()


def verify_sqlite_tables(db_path: str = None):
    """验证SQLite表创建结果"""
    from utils.sqlite_moral_db import MoralDatabase, get_moral_db_path

    db_path = db_path or get_moral_db_path()

    with MoralDatabase(db_path) as db:
        # 检查表数量
        result = db.query_value(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        logger.info(f"SQLite tables count: {result}")

        # 检查各表记录数
        for table_name in SQLite_TABLES_SQL.keys():
            try:
                count = db.query_value(f"SELECT COUNT(*) FROM {table_name}")
                logger.info(f"SQLite table '{table_name}': {count} records")
            except Exception as e:
                logger.warning(f"SQLite table '{table_name}' check failed: {e}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Create moral evaluation system database tables")
    parser.add_argument("--sqlite", action="store_true", help="Use SQLite instead of MySQL")
    parser.add_argument("--drop-existing", action="store_true", help="Drop existing tables before creating")
    parser.add_argument("--verify", action="store_true", help="Verify tables after creation")
    parser.add_argument("--db-path", type=str, help="SQLite database path (optional)")
    args = parser.parse_args()

    try:
        if args.sqlite:
            create_sqlite_tables(db_path=args.db_path, drop_existing=args.drop_existing)

            if args.verify:
                verify_sqlite_tables(db_path=args.db_path)
        else:
            create_tables(drop_existing=args.drop_existing)

            if args.verify:
                verify_tables()

        logger.info("Database setup completed!")
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
