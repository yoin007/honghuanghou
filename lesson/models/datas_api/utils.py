# -*- coding: utf-8 -*-
"""
DataS API 公共工具模块
包含通用的辅助函数和数据处理函数
"""

import os
import shutil
import logging
import pandas as pd
from typing import Optional

from config.config import Config
from models.lesson.lesson import Lesson
from utils.cache import cache

logger = logging.getLogger(__name__)


def refresh_teacher_cache():
    """刷新教师相关缓存"""
    try:
        # 使用细粒度刷新，只删除教师相关的缓存
        cache.delete("teacher_template")
        l = Lesson()
        l.refresh_cache()
    except Exception as e:
        logger.error(f"刷新教师缓存失败: {e}")


def refresh_schedule_cache(class_name: str = None):
    """
    细粒度刷新课程表缓存

    Args:
        class_name: 指定班级名称，如果为 None 则刷新所有课程表缓存
    """
    try:
        if class_name:
            # 只刷新指定班级的缓存
            cache.delete(f"schedule:{class_name}")
        else:
            # 刷新所有课程表缓存
            cache.clear_pattern("schedule:*")
    except Exception as e:
        logger.error(f"刷新课程表缓存失败: {e}")


def backup_excel_file(file_path: str) -> str:
    """备份 Excel 文件"""
    if not os.path.exists(file_path):
        return None
    backup_path = f"{file_path}.bak"
    shutil.copy2(file_path, backup_path)
    return backup_path


# Weekdays 映射
WEEKDAYS = {
    "1": "monday",
    "2": "tuesday",
    "3": "wednesday",
    "4": "thursday",
    "5": "friday",
    "6": "sat",
    "7": "sun",
}


def get_schedule_data(next_week: bool = False, weekdays: dict = WEEKDAYS):
    """获取课程表数据"""
    l = Lesson()
    class_template = l.get_cache_data("class_template")
    if next_week:
        df_schedule = l.get_cache_data("next_schedule")
    else:
        df_schedule = l.get_cache_data("current_schedule")
    schedule_data = {}
    for class_name in df_schedule.columns[4:]:
        if class_name not in class_template["class_name"].tolist():
            continue
        schedule_data[class_name] = {}
        for week, group in df_schedule[[class_name, "week"]].groupby("week"):
            schedule_data[class_name][weekdays[str(week)]] = group[class_name].tolist()
    return schedule_data


def get_teacher_data():
    """获取教师数据"""
    l = Lesson()
    subject_teacher = l.get_cache_data("teacher_template")
    teachers_data = {}
    for teacher in subject_teacher["name"].tolist():
        teachers_data[teacher] = (
            subject_teacher[subject_teacher["name"] == teacher]["subject"]
            .values[0]
            .split("/")
        )
    return teachers_data


def get_time_table():
    """获取作息时间表"""
    l = Lesson()
    time_table = {}
    time_periods = l.get_cache_data("time_table")
    for index, row in time_periods.iterrows():
        order = row["label"]
        time_table[order] = row["show_time"]
    return time_table
