# _*_ coding: utf-8 _*_
"""课表业务算法。

该模块负责课表格式化、校验、查询和差异计算；文件落盘交给
ScheduleRepository，人员查询交给 TeacherDirectory。
"""

import os
import re
from datetime import datetime, timedelta

import pandas as pd


class ScheduleService:
    """课表业务服务。"""

    def __init__(
        self,
        cache_getter,
        load_excel_file,
        repository,
        lesson_dir: str,
        create_month_dir,
        notify_admins,
    ):
        self.get_cache_data = cache_getter
        self.load_excel_file = load_excel_file
        self.repository = repository
        self.lesson_dir = lesson_dir
        self.create_month_dir = create_month_dir
        self.notify_admins = notify_admins

    def format_schedule(self, df_schedule: pd.DataFrame, week_flag: str, replace_flag: bool = True, ignore: bool = False):
        replace_dict = self.get_cache_data("replace_dict") if replace_flag else {}
        ignore_subjects = self.get_cache_data("ignore_subjects") if ignore else set()
        week_flag_str = f"({week_flag})"

        def process(x):
            if not isinstance(x, str):
                return x
            result = x.strip().replace("（", "(").replace("）", ")").replace(" ", "")
            result = re.compile(r"[ \s\n\r\t]+").sub("", result)
            subjects = result.split("/")
            if len(subjects) == 2:
                for subject in subjects:
                    if week_flag_str in subject:
                        return subject.replace(week_flag_str, "").strip()
            for k, v in replace_dict.items():
                result = result.replace(k, v)
            if ignore and result in ignore_subjects:
                return "-"
            return result.strip()

        return df_schedule.copy().map(process).fillna("-")

    def schedule_data(self, week_next: int = 0, replace_flag: bool = True, ignore: bool = False):
        schedule_file = self.get_cache_data("schedule_file")[week_next]
        if schedule_file == "":
            return pd.DataFrame()
        week_num = self.get_cache_data("week_info")[week_next][0]
        week_flag = "单" if week_num % 2 == 1 else "双"
        df = self.load_excel_file(schedule_file)
        return self.format_schedule(df, week_flag, replace_flag, ignore)

    def today_schedule(self):
        df = self.get_cache_data("current_schedule")
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.copy()
        if "date" not in df.columns:
            return pd.DataFrame()
        today = self.get_cache_data("now").strftime("%d")
        df["date"] = pd.to_numeric(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["date"] = df["date"].astype(int)
        return df[df["date"] == int(today)]

    def get_weekday_schedule(self, target_date=None):
        df = self.get_cache_data("current_schedule")
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.copy()

        if target_date is None:
            now = self.get_cache_data("now")
            target_day = now.day
            target_weekday = now.weekday() + 1
        elif isinstance(target_date, int):
            target_weekday = target_date
            target_day = None
        else:
            try:
                if isinstance(target_date, str):
                    target_dt = datetime.strptime(target_date, "%Y%m%d")
                else:
                    target_dt = target_date
                target_day = target_dt.day
                target_weekday = target_dt.weekday() + 1
            except Exception:
                now = self.get_cache_data("now")
                target_day = now.day
                target_weekday = now.weekday() + 1

        if "date" not in df.columns:
            return pd.DataFrame()

        df["date"] = pd.to_numeric(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["date"] = df["date"].astype(int)

        if "weekday" in df.columns:
            df["weekday"] = pd.to_numeric(df["weekday"], errors="coerce")
            df = df.dropna(subset=["weekday"])
            df["weekday"] = df["weekday"].astype(int)
            if target_day is not None:
                return df[(df["date"] == target_day) & (df["weekday"] == target_weekday)]
            return df[df["weekday"] == target_weekday]

        return df[df["date"] == target_day]

    @staticmethod
    def split_subjects(subject) -> list:
        if subject is None:
            return []
        try:
            if pd.isna(subject):
                return []
        except (TypeError, ValueError):
            pass
        return [
            item.strip()
            for item in str(subject).split("/")
            if item and item.strip() and item.strip() != "-"
        ]

    def get_subject_teacher(self, subject: str) -> str:
        teacher_template = self.get_cache_data("teacher_template")
        if teacher_template is None:
            return subject
        for _, row in teacher_template.iterrows():
            if subject in self.split_subjects(row.get("subject")):
                return row["name"]
        for _, row in teacher_template.iterrows():
            for s in self.split_subjects(row.get("subject")):
                if len(s) >= 2 and subject.startswith(s):
                    return row["name"]
        return subject

    def replace_subject_teacher(self, df_schedule: pd.DataFrame, teacher_flag: bool = True) -> pd.DataFrame:
        teacher_template = self.get_cache_data("teacher_template")
        if teacher_template is None:
            return df_schedule
        subject_to_teacher = {}
        for _, row in teacher_template.iterrows():
            for subject in self.split_subjects(row.get("subject")):
                subject_to_teacher[subject] = row["name"] if teacher_flag else subject[:2]

        def replace_with_teacher(x):
            if not isinstance(x, str) or x == "-":
                return x
            return subject_to_teacher.get(x, x)

        return df_schedule.map(replace_with_teacher)

    def title_to_week(self, title: str) -> list:
        title_date = re.match(r"(\d+)", title)
        if title_date is None or len(title_date.group(1)) != 8:
            return []
        title_date = title_date.group(1)
        for week in self.get_cache_data("week_info"):
            if title_date == week[1]:
                return week
        return []

    def check_schedule_date(self, df_schedule: pd.DataFrame, title: str) -> str:
        if "date" not in df_schedule.columns:
            return "课表中没有日期列"
        week = self.title_to_week(title)
        if not week:
            return "课表文件名日期错误"
        monday = datetime.strptime(week[1], "%Y%m%d")
        date_list = [int((monday + timedelta(days=i)).strftime("%d")) for i in range(7)]
        df_date = pd.to_numeric(df_schedule["date"], errors="coerce").dropna().astype(int).tolist()
        df_date = list(dict.fromkeys(df_date))
        invalid_dates = [day for day in df_date if day not in date_list]
        if invalid_dates:
            return f"课表中日期 {invalid_dates} 不在当前周内"
        return "ok"

    def check_schedule_class(self, df_schedule: pd.DataFrame) -> str:
        class_template = self.get_cache_data("class_template")
        if class_template.empty:
            return "班级模板为空"
        class_names = class_template["class_name"].tolist()
        missing_classes = [name for name in class_names if name not in df_schedule.columns]
        if missing_classes:
            return f"课表中班级 {missing_classes} 不在班级模板中"
        return "ok"

    def check_repeated_subjects(self, df_schedule: pd.DataFrame) -> str:
        df_teacher = self.replace_subject_teacher(df_schedule)
        class_list = self.get_cache_data("class_template")["class_name"].tolist()
        df_class = df_teacher[class_list]
        repeated = self.get_cache_data("ignore_subjects")
        repeated_lines = []
        for index, row in df_class.iterrows():
            duplicates = row[row.duplicated()].to_dict()
            if duplicates:
                for column, value in duplicates.items():
                    if value != "-" and value:
                        subject = df_schedule.loc[index, column]
                        if subject not in repeated:
                            repeated_lines.append(f"第{index+2}行: {column}:{value}!")
        if repeated_lines:
            return "课表中存在重复学科:" + "\n".join(repeated_lines)
        return "ok"

    def check_schedule(self, df_schedule: pd.DataFrame, title: str) -> str:
        if df_schedule is None or df_schedule.empty:
            return "读取课表失败"
        result = self.check_schedule_date(df_schedule, title)
        if result != "ok":
            return result
        result = self.check_schedule_class(df_schedule)
        if result != "ok":
            return result
        result = self.check_repeated_subjects(df_schedule)
        if result != "ok":
            return result
        return "ok"

    def update_schedule_file(self, schedule_file: str, title: str, new_name: str):
        c_month = self.get_cache_data("c_month")
        schedule_dir = os.path.join(self.lesson_dir, c_month, "class_schedule")
        week = self.title_to_week(title)
        if not os.path.exists(schedule_dir):
            self.create_month_dir()
        schedule_list = self.get_cache_data("schedule_file")
        old_file = schedule_list[1] if week[4] else schedule_list[0]
        try:
            new_file = self.repository.archive_and_replace_schedule(
                schedule_file=schedule_file,
                schedule_dir=schedule_dir,
                new_name=new_name,
                old_file=old_file,
            )
            if old_file:
                self.notify_admins(f"更新课表成功: {new_file}", log_level="info")
            return new_file
        except Exception as exc:
            self.notify_admins(f"更新课表失败: {exc}", log_level="error")
            return None

    def schedule_diff(self, old_df, new_df):
        old_df_teacher = self.replace_subject_teacher(old_df)
        new_df_teacher = self.replace_subject_teacher(new_df)
        class_list = self.get_cache_data("class_template")["class_name"].tolist()
        diff_df = pd.DataFrame(index=new_df.index, columns=new_df.columns)

        for column in class_list:
            for idx in new_df_teacher.index:
                if old_df_teacher.loc[idx, column] != new_df_teacher.loc[idx, column]:
                    diff_df.loc[idx, column] = f"{old_df_teacher.loc[idx, column]} -> {new_df_teacher.loc[idx, column]}"

        changes = []
        for column, row_dict in diff_df.to_dict().items():
            for idx, value in row_dict.items():
                if "->" in str(value):
                    old, new = value.split(" -> ")
                    changes.append([idx, column, new_df.loc[idx, "date"], new_df.loc[idx, "order"], old, new, new_df.loc[idx, "week"]])

        class_changes = []
        for change in changes:
            if change[1] not in class_changes:
                class_changes.append(change[1])

        diff_teachers = []
        for change in changes:
            old_category = change[4]
            new_category = change[5]
            if old_category not in diff_teachers:
                diff_teachers.append(self.get_subject_teacher(old_category))
            if new_category not in diff_teachers:
                diff_teachers.append(self.get_subject_teacher(new_category))

        # 记录每个班级/老师课表中被调整的单元格 (order, week)，供图片渲染高亮
        class_highlights: dict = {}
        teacher_highlights: dict = {}
        for change in changes:
            class_name = change[1]
            order = change[3]
            week = change[6]
            class_highlights.setdefault(class_name, []).append((order, week))
            for category in (change[4], change[5]):
                teacher = self.get_subject_teacher(category)
                cells = teacher_highlights.setdefault(teacher, [])
                if (order, week) not in cells:
                    cells.append((order, week))

        return class_changes, diff_teachers, {"class": class_highlights, "teacher": teacher_highlights}

    def get_class_schedule(self, class_name: str, week_next: bool = False) -> pd.DataFrame:
        schedule_data = self.get_cache_data("next_schedule") if week_next else self.get_cache_data("current_schedule")
        if schedule_data is None:
            return pd.DataFrame()
        required_columns = ["date", "week", "order", class_name]
        df = self.replace_subject_teacher(schedule_data, teacher_flag=False)
        if any(column not in df.columns for column in required_columns):
            return pd.DataFrame()
        df = df[required_columns]
        grouped_df = df.groupby("week")[class_name].apply(list).reset_index()
        new_df = pd.DataFrame(grouped_df[class_name].tolist(), index=grouped_df["week"])
        new_df.columns = df["order"][: new_df.shape[1]]
        new_df.index.name = "星期"
        new_df.columns.name = "节次"
        return new_df.map(lambda x: "-" if x is None else x).T

    def get_teacher_schedule(self, teacher_name: str, week_next: bool = False) -> pd.DataFrame:
        schedule_data = self.get_cache_data("next_schedule") if week_next else self.get_cache_data("current_schedule")
        if schedule_data is None:
            return pd.DataFrame()
        df_subject = self.replace_subject_teacher(schedule_data, teacher_flag=False)
        df = self.replace_subject_teacher(schedule_data, teacher_flag=True)
        if df.empty or "week" not in df.columns or "order" not in df.columns:
            return pd.DataFrame()
        grouped_df = df[["week", "order"]].groupby("week")
        if not grouped_df.groups:
            return pd.DataFrame()

        max_l_group = max(grouped_df, key=lambda x: len(x[1]))
        max_l_week = max_l_group[0]
        schedule_order = df[df["week"] == max_l_week]["order"].tolist()
        week_list = list(grouped_df.groups.keys())
        teacher_df = pd.DataFrame(columns=week_list, index=schedule_order)
        teacher_schedule = df[df.isin([teacher_name]).any(axis=1)]
        for index, row in teacher_schedule.iterrows():
            week = row["week"]
            order = row["order"]
            teacher_columns = row.index[row == teacher_name]
            if len(teacher_columns) == 0:
                continue
            teacher_column = teacher_columns[0]
            teacher_subject = df_subject.loc[index, teacher_column]
            teacher_df.loc[order, week] = f"{teacher_column}-{teacher_subject}" if teacher_subject else teacher_column
        return teacher_df

    def current_teaching(self) -> dict:
        df = self.get_cache_data("today_schedule")
        if df is None or df.empty:
            return {}
        current_time = datetime.now().strftime("%H:%M")
        current_classes = {}
        current_period = None
        time_tables = self.get_cache_data("time_table")
        if time_tables is None or time_tables.empty:
            return {}
        periods = {order: show_time for order, show_time in zip(time_tables["order"], time_tables["show_time"])}
        for period, time_range in periods.items():
            start_time, end_time = time_range.split("-")
            start_minutes = sum(int(x) * 60**i for i, x in enumerate(reversed(start_time.split(":"))))
            end_minutes = sum(int(x) * 60**i for i, x in enumerate(reversed(end_time.split(":"))))
            current_minutes = sum(int(x) * 60**i for i, x in enumerate(reversed(current_time.split(":"))))
            if start_minutes <= current_minutes <= end_minutes:
                current_period = period
                break
        class_list = self.get_cache_data("class_template")["class_name"].tolist()
        if current_period is not None:
            df = df.copy()
            df["order"] = df["order"].astype(str)
            df_current = df[df["order"] == str(current_period)]
            if df_current.empty:
                return current_classes
            for class_name in class_list:
                if class_name in df_current.columns:
                    values = df_current[class_name].values
                    if len(values) > 0:
                        current_classes[class_name] = values[0]
        return current_classes
