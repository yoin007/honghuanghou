# _*_ coding: utf-8 _*_
"""课表通知发送。

该模块集中处理课表图片发送、课表变更提醒和今日上课教师提醒。
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sendqueue import send_image, send_text


class ScheduleNotifier:
    """课表通知服务。"""

    def __init__(self, lesson):
        self.lesson = lesson

    async def process_and_send_image(self, df, png_name: str, title: str, wxid: str, producer: str, tips=False):
        with ThreadPoolExecutor() as executor:
            df_png = await asyncio.get_event_loop().run_in_executor(
                executor,
                self.lesson.df_to_png,
                df,
                png_name,
                title,
            )
            if df_png:
                pic_path = df_png[0][len(self.lesson.lesson_dir):].replace("\\", "/")
                if tips:
                    send_text("你的课有调整，请注意查看！", wxid)
                send_image(pic_path, wxid, producer)
                return True

            self.lesson.notify_admins(f"生成课表图片失败: {title}", log_level="error")
            return False

    async def process_class_schedule(self, df, png_name: str, title: str, class_name: str, producer: str, tips=False):
        with ThreadPoolExecutor() as executor:
            class_pic = await asyncio.get_event_loop().run_in_executor(
                executor,
                self.lesson.df_to_png,
                df,
                png_name,
                title,
            )
            if class_pic:
                pic_path = class_pic[0][len(self.lesson.lesson_dir):].replace("\\", "/")
                for wxid in self.lesson.get_wxids(class_name):
                    if tips:
                        send_text(f"{class_name}的课有调整，请注意查看！", wxid)
                    send_image(pic_path, wxid, producer)
                return True

            self.lesson.notify_admins(f"生成班级课表图片失败: {title}", log_level="error")
            return False

    async def send_all_schedules(self, content: str):
        s_name = content.removesuffix("的课表").strip()
        if s_name == "更新本周":
            df = self.lesson.get_cache_data("current_schedule")
            if df.empty:
                self.lesson.notify_admins("当前周的课表为空", log_level="error")
                return False
            week_next = False
        elif s_name == "更新下周":
            df = self.lesson.get_cache_data("next_schedule")
            if df.empty:
                self.lesson.notify_admins("下周的课表为空", log_level="error")
                return False
            week_next = True
        else:
            self.lesson.notify_admins(f"未知的课表更新请求：{content}", log_level="error")
            return False

        teacher_template = self.lesson.get_cache_data("teacher_template")
        class_template = self.lesson.get_cache_data("class_template")
        teachers = teacher_template[teacher_template["notice"] == True]["name"].tolist()
        classes = class_template[class_template["active"] == True]["class_name"].tolist()
        tasks = []

        for teacher in teachers:
            wxids = self.lesson.get_wxids(teacher)
            if not wxids:
                self.lesson.notify_admins(f"未找到老师 {teacher} 的微信ID", log_level="error")
                continue
            teacher_df = self.lesson.get_teacher_schedule(teacher, week_next)
            if teacher_df.empty:
                self.lesson.notify_admins(f"老师 {teacher} 的课表为空", log_level="info")
                continue
            title = f"{teacher}{'下周' if week_next else '本周'}的课表"
            tasks.append(self.process_and_send_image(teacher_df, f"{wxids[0]}.png", title, wxids[0], "lesson"))

        for class_name in classes:
            class_df = self.lesson.get_class_schedule(class_name, week_next)
            if class_df.empty:
                self.lesson.notify_admins(f"班级 {class_name} 的课表为空", log_level="info")
                continue
            title = f"{class_name}{'下周' if week_next else '本周'}的课表"
            tasks.append(self.process_class_schedule(class_df, f"{class_name}.png", title, class_name, "lesson"))

        if tasks:
            await asyncio.gather(*tasks)
        return True

    def today_teachers(self):
        now = datetime.now().strftime("%Y%m%d")
        schedule_now = self.lesson.get_cache_data("now").strftime("%Y%m%d")
        if schedule_now != now:
            self.lesson.notify_admins("今日课表尚未更新，请检查配置", log_level="error")
            return

        today_df = self.lesson.get_cache_data("today_schedule")
        if today_df.empty:
            self.lesson.notify_admins("今日无课！", log_level="info")
            return

        today_df = today_df.copy()
        time_table = self.lesson.get_cache_data("time_table")
        class_order = time_table["order"].tolist()
        today_df["order"] = today_df["order"].astype(str)
        teachers = {}

        for order in class_order:
            for class_name in self.lesson.get_cache_data("class_template")["class_name"].tolist():
                class_df = today_df[[class_name, "order"]]
                try:
                    subject = class_df[class_df["order"] == str(order)][class_name].values[0]
                    teacher = self.lesson.get_subject_teacher(subject)
                    order_label = time_table[time_table["order"] == order]["label"].values[0]
                    teachers.setdefault(teacher, []).append(f"{order_label}:{class_name} {subject[:2]}")
                except Exception as exc:
                    print(exc, order, class_name)

        if not teachers:
            self.lesson.notify_admins("今日无课！", log_level="info")
            return

        errors = []
        for teacher, items in teachers.items():
            wxids = self.lesson.get_wxids(teacher)
            if wxids:
                tips = f"您今天有{len(items)}节课："
                for item in items:
                    tips += f"\n{item}"
                send_text(tips, wxids[0], "", "lesson")
            elif teacher not in ["早读", "-", "专业课", "英语", "活动", "自习", "校本"]:
                errors.append(teacher)

        if errors:
            self.lesson.notify_admins(f"以下教师没有微信ID：{', '.join(errors)}", log_level="warning")
        else:
            self.lesson.notify_admins("今日上课老师已经通知", log_level="info")
