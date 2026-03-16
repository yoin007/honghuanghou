# -*- coding: utf-8 -*-
"""
DataS API 模块

按功能区域划分:
- 认证相关: /token, /admin/users, /admin/reset-password, /admin/set-password
- 教师管理: /teachers
- 课程表: /schedule, /todays, /schedules, /periods, /current-classes
- 作业公告: /homework, /announcement
- 学生管理: /students
- 请假记录: /leave-records
- 日常记录: /insert_daily, /get_dailies
- 成员权限: /members, /permissions
- 任务管理: /tasks
"""

from .utils import (
    refresh_teacher_cache,
    refresh_schedule_cache,
    backup_excel_file,
    get_schedule_data,
    get_teacher_data,
    get_time_table,
    WEEKDAYS
)

__all__ = [
    'refresh_teacher_cache',
    'refresh_schedule_cache',
    'backup_excel_file',
    'get_schedule_data',
    'get_teacher_data',
    'get_time_table',
    'WEEKDAYS'
]
