import os
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "databases")
# _*_ coding :utf-8 _*_
# @Time : 2026/01/31 16:05
# @Author : Tech_T

import sqlite3
import pandas as pd
from sendqueue import send_text, send_image
from config.config import Config
from config.log import LogConfig
from models.lesson.lesson import Lesson
from datetime import datetime


def _get_sqlite_connection():
    """延迟导入 get_sqlite_connection，避免循环依赖"""
    from models.datas_api.repositories.sqlite_base import get_sqlite_connection
    return get_sqlite_connection

config = Config()
log = LogConfig().get_logger()
event_list = config.get_config("event_list", "event.yaml")

class InOut:
    def __enter__(self, db=os.path.join(DB_DIR, "inout.db")):
        get_sqlite_connection = _get_sqlite_connection()
        self.__conn__ = get_sqlite_connection(db)
        self.__cursor__ = self.__conn__.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__conn__.close()

    def __create_table__(self):
        try:
            self.__cursor__.execute(
                """
            CREATE TABLE inout(
            id INTEGER PRIMARY KEY,
            sid TEXT,
            style TEXT,
            days TEXT DEFAULT "1",
            status TEXT,
            recorder TEXT,
            guard TEXT DEFAULT "",
            active BOOLEAN DEFAULT 1,
            consumer TEXT DEFAULT "",
            note TEXT,
            create_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
            )
            self.__conn__.commit()
            log.info("表：inout 创建成功")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                log.info("表：inout 已存在, 跳过创建")
            else:
                log.error("表：inout 创建失败")
                raise e

    def insert_inout(self, sid, style, recorder, status="已请假", days="1", note=""):
        self.__cursor__.execute(
            "INSERT INTO inout (sid, style, days, status, recorder, note, create_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now','+8 hours'))",
            (sid, style, days, status, recorder, note),
        )
        self.__conn__.commit()
        return self.__cursor__.lastrowid

    def get_inouts(self, activate=1, recorder="", date=""):
        sql = "SELECT * FROM inout WHERE active = ?"
        params = [activate]
        if recorder:
            sql += " AND recorder = ?"
            params.append(recorder)
        if date:
            sql += " AND create_at LIKE ?"
            params.append(f"{date}%")
        self.__cursor__.execute(sql, tuple(params))
        return self.__cursor__.fetchall()
    
    def out_inout(self, id, guard=""):
        self.__cursor__.execute("UPDATE inout SET active = 1, status = '已出校', guard = ? WHERE id = ?", (guard, id))
        self.__conn__.commit()

    def in_inout(self, id, consumer=""):
        self.__cursor__.execute("UPDATE inout SET active = 0, status = '已销假', consumer = ? WHERE id = ?", (consumer, id))
        self.__conn__.commit()

    def del_delay(self, id):
        self.__cursor__.execute("UPDATE inout SET active = 0, status = '已取消' WHERE id = ?", (id,))
        self.__conn__.commit()

    def consume_delay(self, id, consumer="auto"):
        self.__cursor__.execute("UPDATE inout SET active = 0, status = '已完成', consumer = ? WHERE id = ?", (consumer, id))
        self.__conn__.commit()
    
    def inout_columns(self):
        self.__cursor__.execute("SELECT * FROM inout LIMIT 0")
        return [description[0] for description in self.__cursor__.description]
    
    def get_recorder(self, id):
        self.__cursor__.execute("SELECT recorder FROM inout WHERE id = ?", (id,))
        return self.__cursor__.fetchone()[0]
    
    def get_id(self, sid):
        self.__cursor__.execute("SELECT * FROM inout WHERE sid = ? and active = 1", (sid,))
        return self.__cursor__.fetchall()


async def insert_inout(record):
    """
    触发条件 事假-高二1班-张三-2-备注(可选)
    添加记录碎片
    """
    contents = record.content.split('-')
    style = contents[0]
    cname = contents[1]
    name = contents[2]
    days = contents[3]
    note = ""
    if len(contents) == 5:
        note = contents[4]
    l = Lesson()
    sid = l.get_sid(cname, name)
    if sid == '':
        send_text(f"班级或姓名 {name} 错误，请检查输入", record.roomid)
        return 0
    recorder = l.get_alias(record.sender)
    i = InOut()
    i.__enter__()
    record_id = i.insert_inout(sid, style, recorder, days, note)
    send_text(f"记录ID: {record_id} {name} {style} {days} {note}\n 请假学生照片如下：", record.roomid)
    send_image(f"/static/inout/{sid}.jpg", record.roomid)
    i.__exit__(None, None, None)
    return record_id

async def get_inout(record):
    """
    触发条件 请假-高二1班-张三
    查询记录碎片
    """
    contents = record.content.split('-')
    if len(contents) != 3:
        send_text("格式错误，请按照 请假-高二1班-张三 格式输入", record.roomid)
        return 0
    cname = contents[1]
    name = contents[2]
    l = Lesson()
    sid = l.get_sid(cname, name)
    if sid == '':
        send_text(f"班级或姓名 {name} 错误，请检查输入", record.roomid)
        return 0
    i = InOut()
    i.__enter__()
    inout = i.get_id(sid)
    if not inout:
        send_text(f"{cname} {name} 请假记录为空", record.roomid)
        return 0
    columns = i.inout_columns()
    df = pd.DataFrame(inout, columns=columns)
    if "id" in columns:
        df.set_index("id", inplace=True)
    i.__exit__(None, None, None)
    l = Lesson()
    students_df = l.get_cache_data("students")
    students_df['sid'] = students_df['sid'].astype(str)
    df['sid'] = df['sid'].astype(str)
    if "sid" in df.columns:
        df = pd.merge(df, students_df, on="sid", how="left")
        df.drop(columns=['active'], inplace=True)
    cnt = 1
    rsp = f"{cname} {name} 记录:\n"
    for _, row in df.iterrows():
        rsp += f"{cnt}. {row['cname']} {row['name']} {row['style']} {row['days']} {row['status']} {row['recorder']} {row['guard']} {row['note']}\n"
        cnt += 1
    send_text(rsp, record.roomid)
    return 1

async def out_inout(record):
    """
    触发条件 出校-高二1班-张三
    出校记录碎片
    """
    contents = record.content.split('-')
    if len(contents) != 3:
        send_text("格式错误，请按照 出校-高二1班-张三 格式输入", record.roomid)
        return 0
    cname = contents[1]
    name = contents[2]
    l = Lesson()
    sid = l.get_sid(cname, name)
    if sid == '':
        send_text(f"班级或姓名 {name} 错误，请检查输入", record.roomid)
        return 0
    i = InOut()
    i.__enter__()
    inout = i.get_id(sid)
    if not inout:
        send_text(f"{cname} {name} 请假记录为空", record.roomid)
        return 0
    guard = l.get_alias(record.sender)
    i.out_inout(inout[0][0], guard)
    send_text(f"{cname} {name} 请假记录已更新", record.roomid)

async def in_inout(record):
    """
    触发条件 销假-高二1班-张三
    销假记录碎片
    """
    contents = record.content.split('-')
    if len(contents) != 3:
        send_text("格式错误，请按照 销假-高二1班-张三 格式输入", record.roomid)
        return 0
    cname = contents[1]
    name = contents[2]
    l = Lesson()
    sid = l.get_sid(cname, name)
    if sid == '':
        send_text(f"班级或姓名 {name} 错误，请检查输入", record.roomid)
        return 0
    i = InOut()
    i.__enter__()
    inout = i.get_id(sid)
    if not inout:
        send_text(f"{cname} {name} 请假记录为空", record.roomid)
        return 0
    i.in_inout(inout[0][0], consumer=l.get_alias(record.sender))
    send_text(f"{cname} {name} 销假记录已更新", record.roomid)

def get_stu_dict(sid):
    l = Lesson()
    students_df = l.get_cache_data("students")
     # 转换 roomid 和 rpid 为整数再转字符串，去除小数点
    def safe_int_str(x):
        try:
            if pd.isna(x):
                return ""
            if isinstance(x, (int, float)):
                return str(int(x))
            return str(x)
        except:
            return str(x)

    for col in ['roomid', 'rpid', 'sid']:
        if col in students_df.columns:
            students_df[col] = students_df[col].apply(safe_int_str)
    students_df = students_df[(students_df["sid"] == sid) & (students_df['active'] == 1)].copy()
    if students_df.empty:
        return {}
    else:
        student = students_df.iloc[0].to_dict()
        return student

def check_inout_days():
    """
    检查所有请假记录的天数是否已经到达时限
    """
    i = InOut()
    i.__enter__()
    inouts = i.get_inouts()
    today = datetime.now().date()
    l = Lesson()
    for inout in inouts:
        create_time = inout[-1]
        create_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S").date()
        if inout[2] == '延时':
            if create_time < today:
                i.consume_delay(inout[0])
            continue
        days = inout[3]
        if days and (today - create_time).days > int(days):
            recorder = l.member_wxid(inout[5])
            if recorder:
                student = get_stu_dict(inout[1])
                send_text(f"{student['cname']}-{student['name']}", recorder)
                send_text(f"{inout[-1]}的{inout[2]}记录已过期,未销假，请及时处理", recorder)
