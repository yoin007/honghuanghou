# _*_ coding :utf-8 _*_
# @Time : 2026/01/27 16:05
# @Author : Tech_T

from datetime import datetime
import os
import sqlite3
import pandas as pd
from sendqueue import send_text
from config.config import Config
from config.log import LogConfig
from models.lesson.lesson import Lesson

config = Config()
log = LogConfig().get_logger()
event_list = config.get_config("event_list", "event.yaml")

# send_text = print

class Daily:
    def __init__(self):
        self.admin = config.get_config("daily_admin", "event.yaml")

    def __enter__(self, db="databases/daily.db"):
        self.__conn__ = sqlite3.connect(db)
        self.__cursor__ = self.__conn__.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__conn__.close()

    def __create_table__(self):
        try:
            self.__cursor__.execute(
                """
            CREATE TABLE daily(
            id INTEGER PRIMARY KEY,
            event TEXT,
            sid TEXT,
            note TEXT,
            recorder TEXT,
            style TEXT,
            create_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
            )
            self.__conn__.commit()
            log.info("表：daily 创建成功")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                log.info("表：daily 已存在, 跳过创建")
            else:
                log.error("表：daily 创建失败")
                raise e

    def insert_daily(self, event, sid, style, recorder, note=""):
        self.__cursor__.execute(
            "INSERT INTO daily (event, sid, style, recorder, note, create_at) VALUES (?, ?, ?, ?, ?, ?)",
            (event, sid, style, recorder, note, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        self.__conn__.commit()
        return self.__cursor__.lastrowid

    def get_dailies(self, date=None, sids=None):
        sql = "SELECT * FROM daily WHERE 1=1"
        params = []

        if date:
            if len(date) == 7: # YYYY-MM
                sql += " AND strftime('%Y-%m', create_at) = ?"
                params.append(date)
            elif len(date) == 10: # YYYY-MM-DD
                sql += " AND strftime('%Y-%m-%d', create_at) = ?"
                params.append(date)
            else: # YYYYMMDD
                sql += " AND strftime('%Y%m%d', create_at) = ?"
                params.append(date)
        
        if sids is not None:
            if not sids:
                return []
            if not isinstance(sids, list):
                sids = [sids]
            
            placeholders = ','.join(['?'] * len(sids))
            sql += f" AND sid IN ({placeholders})"
            params.extend(sids)
            
        self.__cursor__.execute(sql, tuple(params))
        return self.__cursor__.fetchall()
    
    def daily_columns(self):
        self.__cursor__.execute("SELECT * FROM daily LIMIT 0")
        return [description[0] for description in self.__cursor__.description]
    
    def del_daily(self, id):
        self.__cursor__.execute("DELETE FROM daily WHERE id = ?", (id,))
        self.__conn__.commit()
        return self.__cursor__.rowcount

    def get_recorder(self, id):
        self.__cursor__.execute("SELECT recorder FROM daily WHERE id = ?", (id,))
        return self.__cursor__.fetchone()[0]


async def insert_daily(record: any):
    """
    触发条件 睡觉-(.*)
    添加课时记录碎片
    """
    # text = "睡觉-高二1班-张三/李四-学科-备注(可选)"
    text = record.content
    groups = text.split("-")
    if len(groups) < 4:
        send_text("格式错误，请按照 睡觉-高二1班-张三/李四-学科-备注(可选) 格式输入", record.roomid)
        return
    event = groups[0]
    if event not in event_list:
        send_text(f"事件 {event} 错误，请检查输入", record.roomid)
        return
    c_name = groups[1]
    names = groups[2]
    style = groups[3]
    note = ""
    l = Lesson()
    recorder = l.get_alias(record.sender)
    if len(groups) > 4:
        note = groups[4]
    n = Daily()
    n.__enter__()
    for name in names.split("/"):
        sid = l.get_sid(c_name, name)
        if sid == '':
            send_text(f"班级或姓名 {name} 错误，请检查输入", record.roomid)
            return
        record_id = n.insert_daily(event, sid, style, recorder, note)
        send_text(f"记录{record_id}: {name} {event} {style} {note}", record.roomid)
    n.__exit__(None, None, None)


async def get_dailies(record: any):
    """
    触发条件 
    查询常规记录碎片
    常规-20260127-睡觉
    """
    contents = record.content.split('-')
    if len(contents)>3:
        return send_text("格式错误，请按照 常规-20260127-事件 格式输入", record.roomid)
    date = contents[1]
    event = ""
    if len(contents) == 3:
        event = contents[2]
    n = Daily()
    n.__enter__()
    dailies = n.get_dailies(date, event)
    columns = n.daily_columns()
    if not dailies:
        send_text(f"{date} {event} 记录为空", record.roomid)
        return 0
    df = pd.DataFrame(dailies, columns=columns)
    if "id" in columns:
        df.set_index("id", inplace=True)
    n.__exit__(None, None, None)
    l = Lesson()
    students_df = l.get_cache_data("students")
    students_df['sid'] = students_df['sid'].astype(str)
    df['sid'] = df['sid'].astype(str)
    if "sid" in df.columns:
        df = pd.merge(df, students_df, on="sid", how="left")
        df.drop(columns=['active'], inplace=True)
        df['rpid'] = df['rpid'].astype(str)
    cnt = 1
    rsp = f"{date} {event} 记录:\n"
    for _, row in df.iterrows():
        rsp += f"{cnt}. {row['cname']} {row['name']} {row['event']} {row['style']} {row['roomid']} {row['rpid']}号床 {row['note']}\n"
        cnt += 1
    send_text(rsp, record.roomid)
    return 1

async def export_dailies(record: any):
    contents = record.content.split('-')
    if len(contents)>3:
        return send_text("格式错误，请按照 常规-20260127-事件 格式输入", record.roomid)
    date = contents[1]
    event = ""
    if len(contents) == 3:
        event = contents[2]
    n = Daily()
    n.__enter__()
    dailies = n.get_dailies(date, event)
    columns = n.daily_columns()
    if not dailies:
        send_text(f"{date} {event} 记录为空", record.roomid)
        return 0
    df = pd.DataFrame(dailies, columns=columns)
    if "id" in columns:
        df.set_index("id", inplace=True)
    n.__exit__(None, None, None)
    l = Lesson()
    students_df = l.get_cache_data("students")
    students_df['sid'] = students_df['sid'].astype(str)
    df['sid'] = df['sid'].astype(str)
    if "sid" in df.columns:
        df = pd.merge(df, students_df, on="sid", how="left")
        df.drop(columns=['active'], inplace=True)
        df['rpid'] = df['rpid'].astype(str)
    ldir = l.lesson_dir
    static_url = config.get_config("static_url", "wechat.yaml")
    file_path = f"{ldir}/temp/{date}_{event}.xlsx"
    if os.path.exists(file_path):
        os.remove(file_path)
    df.to_excel(file_path, index=False)
    send_text(f"{date} {event} 记录导出成功", record.roomid)
    send_text(f"{static_url}/temp/{date}_{event}.xlsx", record.roomid, "lesson")
    return 1


async def del_daily(record: any):
    """
    触发条件 删常规-1
    删除指定记录碎片
    """
    contents = record.content.split('-')
    if len(contents) != 2:
        send_text("格式错误，请按照 删常规-1 格式输入", record.roomid)
        return 0
    id = contents[1]
    l = Lesson()
    recorder = l.get_alias(record.sender)
    n = Daily()
    del_flag = False
    if recorder in n.admin:
        del_flag = True
    elif recorder == n.get_recorder(id):
        del_flag = True
    if not del_flag:
        send_text(f"记录ID {id} 不是您创建的，不能删除", record.roomid)
        return 
    n.__enter__()
    cnt = n.del_daily(id)
    n.__exit__(None, None, None)
    if cnt == 0:
        send_text(f"记录ID {id} 不存在", record.roomid)
        return 0
    send_text(f"记录ID {id} 删除成功", record.roomid)
    return 1


    