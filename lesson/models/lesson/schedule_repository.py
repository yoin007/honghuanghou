# _*_ coding: utf-8 _*_
"""课表文件和模板数据访问。

该模块只处理 Excel、模板文件和课表文件落盘，不包含课表业务算法。
"""

import os
import shutil
import time
from datetime import datetime

import pandas as pd


class ScheduleRepository:
    """课表文件仓储。"""

    def __init__(self, lesson_dir: str, logger=None):
        self.lesson_dir = lesson_dir
        self.logger = logger

    def create_month_dir(self, month: str = "") -> str:
        if month == "":
            month = datetime.now().strftime("%Y%m")
        month_dir = os.path.join(self.lesson_dir, month)
        if os.path.exists(month_dir):
            return ""
        os.makedirs(month_dir, exist_ok=True)
        os.makedirs(os.path.join(month_dir, "class_schedule"), exist_ok=True)
        os.makedirs(os.path.join(month_dir, "schedule_history"), exist_ok=True)
        os.makedirs(os.path.join(month_dir, "temp"), exist_ok=True)
        return month_dir

    def load_excel_file(self, file_path, sheet_name=0, index_col=None) -> pd.DataFrame:
        try:
            return pd.read_excel(file_path, sheet_name=sheet_name, index_col=index_col)
        except Exception as exc:
            if self.logger:
                self.logger.error(f"加载Excel文件失败: {exc}")
            return pd.DataFrame()

    def load_template(self, sheet_name: str, index_col=None) -> pd.DataFrame:
        return self.load_excel_file(
            os.path.join(self.lesson_dir, "checkTemplate.xlsx"),
            sheet_name=sheet_name,
            index_col=index_col,
        )

    def get_schedule_files(self, c_month: str, week_info: list) -> list:
        current_file = ""
        next_file = ""
        schedule_dir = os.path.join(self.lesson_dir, c_month, "class_schedule")
        if not os.path.exists(schedule_dir):
            return [current_file, next_file]
        for file_name in os.listdir(schedule_dir):
            if week_info[0][1] in file_name:
                current_file = os.path.join(schedule_dir, file_name)
            if week_info[1][1] in file_name:
                next_file = os.path.join(schedule_dir, file_name)
        return [current_file, next_file]

    def archive_and_replace_schedule(self, schedule_file: str, schedule_dir: str, new_name: str, old_file: str):
        new_file = os.path.join(schedule_dir, new_name).replace("课表", "schedule")
        history_file = old_file.replace("class_schedule", "schedule_history") if old_file else ""
        temp_new_file = f"{new_file}.tmp"

        try:
            os.makedirs(schedule_dir, exist_ok=True)
            if old_file:
                os.makedirs(os.path.dirname(history_file), exist_ok=True)
                if os.path.exists(history_file):
                    history_file = f"{history_file}.{int(time.time())}"
                shutil.move(old_file, history_file)
                if self.logger:
                    self.logger.info(f"已归档旧课表文件: {old_file} -> {history_file}")

            shutil.copy2(schedule_file, temp_new_file)
            os.replace(temp_new_file, new_file)
            if self.logger:
                self.logger.info(f"已更新课表文件: {new_file}")
            return new_file
        except Exception:
            if os.path.exists(temp_new_file):
                os.remove(temp_new_file)
            if old_file and history_file and os.path.exists(history_file) and not os.path.exists(old_file):
                shutil.move(history_file, old_file)
            raise
