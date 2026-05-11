import os
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "databases")
# _*_ coding:utf-8 _*_
# @Time:2025/05/20
# @Author: Tech_T

import re
import sqlite3
from datetime import datetime
from config.log import LogConfig
from config.config import Config
from client import Client
from sendqueue import send_text
from utils.db_config import MORAL_DB


MEMBER_COLUMNS = [
    "id",
    "uuid",
    "wxid",
    "alias",
    "active",
    "score",
    "balance",
    "level",
    "model",
    "ai_flag",
    "birthday",
    "create_at",
    "note",
]


def _get_sqlite_connection_manager():
    """延迟导入 SQLiteConnectionManager，避免循环导入"""
    from models.datas_api.repositories.sqlite_base import SQLiteConnectionManager
    return SQLiteConnectionManager


def _get_member_db_path():
    """获取 member.db 路径"""
    return os.path.join(DB_DIR, "member.db")


def _member_teacher_id(uuid: str) -> str:
    safe_uuid = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]", "_", str(uuid or ""))
    return f"M_{safe_uuid[:120]}"


class Member:
    def __init__(self):
        self.__conn__ = None
        self.__cursor__ = None
        self.__conn_wrapper__ = None  # sqlite_base 连接包装器
        self.log = LogConfig().get_logger()

    def __enter__(self, db=None):
        """使用 sqlite_base 获取连接，避免散落的 sqlite3.connect"""
        if db is None:
            db = _get_member_db_path()

        # 使用 sqlite_base 连接管理器，确保 with 退出时提交/回滚并关闭连接。
        self.__conn_wrapper__ = _get_sqlite_connection_manager()(db, row_factory=sqlite3.Row)
        self.__conn__ = self.__conn_wrapper__.__enter__()
        self.__cursor__ = self.__conn__.cursor()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        # 通过 sqlite_base wrapper 管理连接释放
        if self.__conn_wrapper__:
            self.__conn_wrapper__.__exit__(exc_type, exc_val, exc_tb)
            self.__conn_wrapper__ = None
            self.__conn__ = None
            self.__cursor__ = None

    def __create_table__(self):
        self.ensure_unified_member_schema()
        self.migrate_legacy_members_to_teacher()

        try:
            self.__cursor__.execute(
                """
                CREATE TABLE IF NOT EXISTS contacts(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wxid TEXT,
                    wxid_re TEXT,
                    remark TEXT,
                    nick_name TEXT,
                    phone TEXT,
                    sex TEXT,
                    city TEXT,
                    province TEXT,
                    country TEXT,
                    notes TEXT
                )
            """
            )
            self.__conn__.commit()
            self.log.info("Contacts table created successfully.")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                self.log.warning("Contacts table already exists.")
            else:
                self.log.error(f"Error creating Contacts table: {e}")
                raise e

        try:
            self.__cursor__.execute(
                """
                CREATE TABLE IF NOT EXISTS permission(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    func TEXT,
                    func_name TEXT,
                    activate BOOLEAN DEFAULT 1,
                    black_list TEXT,
                    white_list TEXT,
                    type TEXT,
                    pattern TEXT,
                    keywords TEXT,
                    ai_flag BOOLEAN DEFAULT 0,
                    need_at BOOLEAN DEFAULT 0,
                    reply TEXT,
                    module TEXT,
                    level INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 99,
                    example TEXT,
                    check_permission BOOLEAN DEFAULT 0,
                    score INTEGER DEFAULT 0,
                    balance INTEGER DEFAULT 0,
                    create_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """
            )
            self.__conn__.commit()
            self.log.info("Permission table created successfully.")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                self.log.warning("Permission table already exists.")
            else:
                self.log.error(f"Error creating Permission table: {e}")
                raise e

        try:
            self.__cursor__.execute("PRAGMA table_info(permission)")
            columns = [col[1] for col in self.__cursor__.fetchall()]
            if "priority" not in columns:
                self.__cursor__.execute("ALTER TABLE permission ADD COLUMN priority INTEGER DEFAULT 99")
                self.__conn__.commit()
                self.log.info("Added priority column to permission table.")
        except Exception as e:
            self.log.warning(f"Migration for priority column: {e}")

        try:
            self.__cursor__.execute(
                """
                CREATE TABLE IF NOT EXISTS chatroom(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    roomid TEXT,
                    room_name TEXT
                )
            """
            )
            self.__conn__.commit()
            self.log.info("Chatroom table created successfully.")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                self.log.warning("Chatroom table already exists.")
            else:
                self.log.error(f"Error creating Chatroom table: {e}")
                raise e
        
        try:
            self.__cursor__.execute(
                """
                CREATE TABLE IF NOT EXISTS chatroom_member (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_room_id TEXT NOT NULL,
                    member_wx_id TEXT NOT NULL,
                    name TEXT,
                    avatar TEXT,
                    unique_code TEXT,
                    join_timestamp TEXT,
                    status TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    create_time TEXT,
                    update_time TEXT,
                    UNIQUE(chat_room_id, member_wx_id)
                )
            """
            )
            self.__conn__.commit()
            self.log.info("Chatroom_member table created successfully.")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                self.log.warning("Chatroom_member table already exists.")
            else:
                self.log.error(f"Error creating Chatroom_member table: {e}")
                raise e

    @staticmethod
    def wx_contacts(content_type=0):
        """获取微信联系人"""
        client = Client()
        contacts = client.contact_info(content_type)
        return contacts

    def db_contacts(self):
        """获取数据库联系人"""
        with self as m:
            m.__cursor__.execute("SELECT wxid FROM contacts")
            contacts = [contact[0] for contact in m.__cursor__.fetchall()]
        return contacts

    def db_chatroom(self):
        """获取数据库群聊"""
        with self as m:
            m.__cursor__.execute("SELECT roomid FROM chatroom")
            chatroom = [chatroom[0] for chatroom in m.__cursor__.fetchall()]
        return chatroom

    def update_contacts(self):
        """更新本地数据库联系人"""
        contacts_list = self.wx_contacts()
        contacts = self.db_contacts()
        updated_count = 0
        insert_count = 0
        try:
            with self as m:
                for contact in contacts_list:
                    if contact["friendid"] not in contacts:
                        m.__cursor__.execute(
                            """
                            INSERT INTO contacts (wxid, wxid_re, remark, nick_name, phone, sex, city, province, country, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                contact["friendid"],
                                contact["friend_wechatno"],
                                contact["memo"],
                                contact["nickname"],
                                contact["phone"],
                                contact["gender"],
                                contact["city"],
                                contact["province"],
                                contact["country"],
                                "",
                            ),
                        )
                        insert_count += m.__cursor__.rowcount
                    else:
                        m.__cursor__.execute(
                            """
                            UPDATE contacts SET wxid_re = ?, remark = ?, nick_name = ?, phone = ?, sex = ?, city = ?, province = ?, country = ?
                            WHERE wxid = ?
                        """,
                            (
                                contact["friend_wechatno"],
                                contact["memo"],
                                contact["nickname"],
                                contact["phone"],
                                contact["gender"],
                                contact["city"],
                                contact["province"],
                                contact["country"],
                                contact["friendid"],
                            ),
                        )
                        updated_count += m.__cursor__.rowcount
                self.__conn__.commit()

            if updated_count > 0 or insert_count > 0:
                self.log.info(f"更新联系人成功，更新{updated_count}条数据")
                self.log.info(f"插入联系人成功，插入{insert_count}条数据")
                return True
            else:
                self.log.info("联系人无更新")
                return False
        except Exception as e:
            self.log.error(f"更新联系人失败：{e}")
            return False

    def update_chatroom(self):
        """更新本地数据库群聊"""
        wx_chatroom = self.wx_contacts(1)
        # print(wx_chatroom)
        chatroom_list = self.db_chatroom()
        updated_count = 0
        try:
            for chatroom in wx_chatroom:
                with self as m:
                    if chatroom["friendid"] not in chatroom_list:
                        m.__cursor__.execute(
                            """
                            INSERT INTO chatroom (roomid, room_name)
                            VALUES (?,?)
                        """,
                            (chatroom["friendid"], chatroom["nickname"]),
                        )
                        self.__conn__.commit()
                        updated_count += m.__cursor__.rowcount
                    else:
                        m.__cursor__.execute(
                            """
                            UPDATE chatroom SET room_name =?
                            WHERE roomid =?
                        """,
                            (chatroom["nickname"], chatroom["friendid"]),
                        )
                        self.__conn__.commit()
                        updated_count += m.__cursor__.rowcount

            if updated_count > 0:
                self.log.info(f"更新群聊成功，更新{updated_count}条数据")
                return True
            else:
                self.log.info("群聊无更新")
                return False
        except Exception as e:
            self.log.error(f"更新群聊失败：{e}")
            return False
        
    def update_group_members(self, chat_room_id:str, new_members: list):
        """更新群聊成员"""
        with self as m:
            m.__cursor__.execute("""
            SELECT member_wx_id, name, is_deleted
            FROM chatroom_member
            WHERE chat_room_id = ? AND is_deleted = 0
        """, (chat_room_id,))
            old_records = {row[0]: {"name": row[1], "is_deleted": row[2]} for row in m.__cursor__.fetchall()}
            new_member_ids = set()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for member in new_members:
                member_wx_id = member.get("member_wx_id")
                new_member_ids.add(member_wx_id)

                if member_wx_id in old_records:
                    m.__cursor__.execute("""
                        UPDATE chatroom_member
                        SET name = ?, avatar = ?, unique_code = ?, join_timestamp = ?, status = ?, update_time = ?
                        WHERE chat_room_id = ? AND member_wx_id = ? AND is_deleted = 0
                    """, (
                        member.get("name"),
                        member.get("avatar"),
                        member.get("unique_code"),
                        member.get("join_timestamp"),
                        member.get("status"),
                        now,
                        chat_room_id,
                        member_wx_id
                    ))
                else:
                    try:
                        m.__cursor__.execute("""
                            INSERT INTO chatroom_member
                            (chat_room_id, member_wx_id, name, avatar, unique_code, join_timestamp, status, is_deleted, create_time, update_time)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                        """, (
                            chat_room_id,
                            member_wx_id,
                            member.get("name"),
                            member.get("avatar"),
                            member.get("unique_code"),
                            member.get("join_timestamp"),
                            member.get("status"),
                            now,
                            now
                        ))
                    except sqlite3.IntegrityError:
                        m.__cursor__.execute("""
                            UPDATE chatroom_member
                            SET name = ?, avatar = ?, unique_code = ?, join_timestamp = ?, status = ?, is_deleted = 0, update_time = ?
                            WHERE chat_room_id = ? AND member_wx_id = ?
                        """, (
                            member.get("name"),
                            member.get("avatar"),
                            member.get("unique_code"),
                            member.get("join_timestamp"),
                            member.get("status"),
                            now,
                            chat_room_id,
                            member_wx_id
                        ))

            exited_members = []
            for old_id, old_info in old_records.items():
                if old_id not in new_member_ids and old_info["is_deleted"] == 0:
                    m.__cursor__.execute("""
                        UPDATE chatroom_member
                        SET is_deleted = 1, update_time = ?
                        WHERE chat_room_id = ? AND member_wx_id = ?
                    """, (now, chat_room_id, old_id))
                    exited_members.append({"name": old_info["name"], "member_wx_id": old_id})

            self.__conn__.commit()

            m.__cursor__.execute("""
                SELECT COUNT(*) FROM chatroom_member
                WHERE chat_room_id = ? AND is_deleted = 0
            """, (chat_room_id,))
            current_count = m.__cursor__.fetchone()[0]

        report = {
            "chat_room_id": chat_room_id,
            "current_count": current_count,
            "new_count": len(new_members) - len(old_records) + len(exited_members) if old_records else len(new_members),
            "exited_count": len(exited_members),
            "exited_members": exited_members
        }

        print("\n" + "=" * 50)
        print("群成员更新报告")
        print("=" * 50)
        print(f"群ID: {chat_room_id}")
        print(f"当前成员数: {current_count}")
        print(f"新增成员数: {len(new_members) - (len(old_records) - len(exited_members))}")
        print(f"退出成员数: {len(exited_members)}")
        if exited_members:
            print("\n退出成员列表:")
            for m in exited_members:
                print(f"  - {m['name']} ({m['member_wx_id']})")
        print("=" * 50)

        return report
    
    def query_member_name(self, chat_room_id: str, member_wx_id: str):
        """查询群聊成员名称"""
        with self as m:
            try:
                m.__cursor__.execute(
                    "SELECT name FROM chatroom_member WHERE chat_room_id = ? AND member_wx_id = ? AND is_deleted = 0",
                    (chat_room_id, member_wx_id)
                )
                result = m.__cursor__.fetchone()
            except Exception as e:
                self.log.error(f"查询群聊成员名称失败：{e}")
                return ""
        if result:
            return result[0]
        self.log.info(f"数据库中未找到成员 {member_wx_id}，尝试重新同步...")
        client = Client()
        new_members = client.get_group_members(chat_room_id)
        if not new_members:
            self.log.error(f"获取群聊成员失败：{chat_room_id}")
            return ""
        report = self.update_group_members(chat_room_id, new_members)
        import json
        str_report = json.dumps(report, ensure_ascii=False, indent=4)
        self.log.info(f"群聊成员更新报告：{str_report}")
        with self as m:
            try:
                m.__cursor__.execute(
                    "SELECT name FROM chatroom_member WHERE chat_room_id = ? AND member_wx_id = ? AND is_deleted = 0",
                    (chat_room_id, member_wx_id)
                )
                result = m.__cursor__.fetchone()
            except Exception as e:
                self.log.error(f"查询群聊成员名称失败：{e}")
                return ""

        if result:
            return result[0]
        return ""

    def wxid_remark(self, wxid):
        """获取微信联系人备注"""
        with self as m:
            m.__cursor__.execute(
                "SELECT remark, nick_name FROM contacts WHERE wxid =?", (wxid,)
            )
            result = m.__cursor__.fetchone()
            if not result:
                self.update_contacts()
                with self as m:
                    m.__cursor__.execute(
                        "SELECT remark, nick_name FROM contacts WHERE wxid =?", (wxid,)
                    )
                    result = m.__cursor__.fetchone()
        return result if result else ("", "")
    
    def remark_wxid(self, remark):
        """根据备注获取微信联系人"""
        with self as m:
            m.__cursor__.execute(
                "SELECT wxid FROM contacts WHERE remark =?", (remark,)
            )
            result = m.__cursor__.fetchone()
            if not result:
                self.update_contacts()
                with self as m:
                    m.__cursor__.execute(
                        "SELECT wxid FROM contacts WHERE remark =?", (remark,)
                    )
                    result = m.__cursor__.fetchone()
        return result[0] if result else ""

    def chatroom_name(self, roomid):
        """获取群聊名称"""
        with self as m:
            m.__cursor__.execute(
                "SELECT room_name FROM chatroom WHERE roomid =?", (roomid,)
            )
            result = m.__cursor__.fetchone()
            if not result:
                self.update_chatroom()
                with self as m:
                    m.__cursor__.execute(
                        "SELECT room_name FROM chatroom WHERE roomid =?", (roomid,)
                    )
                    result = m.__cursor__.fetchone()
        return result if result else ("",)

    def insert_member(
        self,
        uuid,
        wxid,
        alias,
        active=1,
        score=50,
        balance=0,
        level=1,
        model="basic",
        ai_flag=0,
        birthday="",
        note="",
    ):
        """插入成员"""
        self.ensure_unified_member_schema()
        with _get_sqlite_connection_manager()(MORAL_DB) as conn:
            cursor = conn.cursor()
            wxid = wxid or uuid
            existing = cursor.execute(
                "SELECT teacher_id FROM teacher WHERE wxid = ?",
                (wxid,),
            ).fetchone()

            if existing:
                cursor.execute(
                    """
                    UPDATE teacher
                    SET wxid = ?,
                        name = CASE WHEN identity_type = 'teacher' THEN name ELSE ? END,
                        score = ?, balance = ?,
                        level = ?, model = ?, ai_flag = ?, birthday = ?,
                        is_active = ?, note = ?,
                        identity_type = CASE WHEN identity_type = 'teacher' THEN identity_type ELSE 'member' END,
                        updated_at = datetime('now', 'localtime')
                    WHERE teacher_id = ?
                    """,
                    (
                        wxid,
                        alias,
                        score,
                        balance,
                        level,
                        model,
                        ai_flag,
                        birthday,
                        active,
                        note,
                        existing[0],
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO teacher
                    (teacher_id, name, wxid, role, level, is_active, notice_enabled,
                     score, balance, model, ai_flag, birthday,
                     note, identity_type)
                    VALUES (?, ?, ?, 'member', ?, ?, 1, ?, ?, ?, ?, ?, ?, 'member')
                    """,
                    (
                        _member_teacher_id(wxid),
                        alias or uuid,
                        wxid,
                        level,
                        active,
                        score,
                        balance,
                        model,
                        ai_flag,
                        birthday,
                        note,
                    ),
                )
            conn.commit()
            return cursor.rowcount

    def delte_member(self, uuid):
        """删除成员"""
        self.ensure_unified_member_schema()
        with _get_sqlite_connection_manager()(MORAL_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE teacher
                SET is_active = CASE WHEN identity_type = 'member' THEN 0 ELSE is_active END,
                    updated_at = datetime('now', 'localtime')
                WHERE wxid = ?
                """,
                (uuid,),
            )
            conn.commit()
            return cursor.rowcount

    def member_info(self, uuid=""):
        """获取成员信息"""
        self.ensure_unified_member_schema()
        self.migrate_legacy_members_to_teacher()
        with _get_sqlite_connection_manager()(MORAL_DB) as conn:
            if uuid == "":
                rows = conn.execute(
                    self._member_select_sql() + " ORDER BY id"
                ).fetchall()
                return rows if rows else None

            row = conn.execute(
                self._member_select_sql() + " WHERE wxid = ?",
                (uuid,),
            ).fetchone()
            return row if row else None

    def update_member(self, uuid, **kwargs):
        """更新成员信息"""
        if not kwargs:
            return 0
        
        valid_columns = self.member_columns()
        column_map = {
            "active": "is_active",
            "create_at": "created_at",
        }
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            if key in valid_columns and key != 'uuid':  # uuid 是主键，通常不更新
                db_column = column_map.get(key, key)
                if key == "alias":
                    set_clauses.append("name = CASE WHEN identity_type = 'teacher' THEN name ELSE ? END")
                    values.append(value)
                else:
                    set_clauses.append(f"{db_column} = ?")
                    values.append(value)
        
        if not set_clauses:
            return 0
            
        values.append(uuid)
        
        sql = f"UPDATE teacher SET {', '.join(set_clauses)}, updated_at = datetime('now', 'localtime') WHERE wxid = ?"
        self.ensure_unified_member_schema()
        with _get_sqlite_connection_manager()(MORAL_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(values))
            conn.commit()
            return cursor.rowcount
    
    def member_columns(self):
        """获取成员列名"""
        return MEMBER_COLUMNS[:]
    
    def member_wxid(self, name, active: bool = True):
        """获取成员微信ID"""
        self.ensure_unified_member_schema()
        self.migrate_legacy_members_to_teacher()
        with _get_sqlite_connection_manager()(MORAL_DB) as conn:
            result = conn.execute(
                """
                SELECT wxid FROM teacher
                WHERE name = ? AND COALESCE(is_active, 1) = ?
                ORDER BY CASE WHEN identity_type = 'teacher' THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (name, 1 if active else 0),
            ).fetchone()
        return result if result else ""

    @staticmethod
    def _member_select_sql():
        return """
            SELECT
                rowid AS id,
                COALESCE(wxid, teacher_id) AS uuid,
                wxid,
                name AS alias,
                COALESCE(is_active, 1) AS active,
                COALESCE(score, 50) AS score,
                COALESCE(balance, 0) AS balance,
                COALESCE(level, 1) AS level,
                COALESCE(model, 'basic') AS model,
                COALESCE(ai_flag, 0) AS ai_flag,
                COALESCE(birthday, '') AS birthday,
                created_at AS create_at,
                COALESCE(note, '') AS note
            FROM teacher
        """

    @staticmethod
    def ensure_unified_member_schema():
        """确保 moral.teacher 可以承载原 member 表字段。"""
        os.makedirs(os.path.dirname(MORAL_DB), exist_ok=True)
        log = LogConfig().get_logger()
        with _get_sqlite_connection_manager()(MORAL_DB) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS teacher (
                    teacher_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    wxid TEXT,
                    subject TEXT,
                    password_hash TEXT,
                    role TEXT DEFAULT 'teacher',
                    level INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    notice_enabled INTEGER DEFAULT 1,
                    is_password_changed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
                )
                """
            )
            columns = {
                row[1]
                for row in cursor.execute("PRAGMA table_info(teacher)").fetchall()
            }
            if "alias" in columns:
                cursor.execute(
                    "UPDATE teacher SET name = alias WHERE (name IS NULL OR name = '') AND alias IS NOT NULL AND alias != ''"
                )
                try:
                    cursor.execute("ALTER TABLE teacher DROP COLUMN alias")
                    columns.remove("alias")
                except sqlite3.OperationalError as e:
                    log.warning(f"Could not drop obsolete teacher.alias column: {e}")
            if "member_active" in columns:
                cursor.execute(
                    "UPDATE teacher SET is_active = COALESCE(is_active, member_active) WHERE is_active IS NULL"
                )
                try:
                    cursor.execute("ALTER TABLE teacher DROP COLUMN member_active")
                    columns.remove("member_active")
                except sqlite3.OperationalError as e:
                    log.warning(f"Could not drop obsolete teacher.member_active column: {e}")
            if "uuid" in columns:
                cursor.execute(
                    "UPDATE teacher SET wxid = uuid WHERE (wxid IS NULL OR wxid = '') AND uuid IS NOT NULL AND uuid != ''"
                )
                cursor.execute("DROP INDEX IF EXISTS idx_teacher_uuid")
                try:
                    cursor.execute("ALTER TABLE teacher DROP COLUMN uuid")
                    columns.remove("uuid")
                except sqlite3.OperationalError as e:
                    log.warning(f"Could not drop obsolete teacher.uuid column: {e}")
            if "priority" in columns:
                try:
                    cursor.execute("ALTER TABLE teacher DROP COLUMN priority")
                    columns.remove("priority")
                except sqlite3.OperationalError as e:
                    log.warning(f"Could not drop obsolete teacher.priority column: {e}")

            additions = {
                "score": "INTEGER DEFAULT 50",
                "balance": "INTEGER DEFAULT 0",
                "model": "TEXT DEFAULT 'basic'",
                "ai_flag": "INTEGER DEFAULT 0",
                "birthday": "TEXT",
                "note": "TEXT",
                "identity_type": "TEXT DEFAULT 'teacher'",
            }
            for column, definition in additions.items():
                if column not in columns:
                    cursor.execute(f"ALTER TABLE teacher ADD COLUMN {column} {definition}")

            # 只执行表结构变更（CREATE TABLE / ALTER TABLE），不做 UPDATE
            # UPDATE 操作移到显式初始化脚本，避免每次查询时触发写入锁
            conn.commit()

    def migrate_legacy_members_to_teacher(self):
        """把 member.db.member 的历史数据迁移到 moral.teacher，原表保留备份。"""
        self.ensure_unified_member_schema()
        if not self.__cursor__:
            return 0
        try:
            self.__cursor__.execute("SELECT * FROM member")
            rows = self.__cursor__.fetchall()
            legacy_columns = [desc[0] for desc in self.__cursor__.description]
        except sqlite3.Error:
            return 0

        migrated = 0
        with _get_sqlite_connection_manager()(MORAL_DB) as conn:
            cursor = conn.cursor()
            for row in rows:
                member = dict(zip(legacy_columns, row))
                uuid = member.get("uuid") or member.get("wxid")
                wxid = member.get("wxid") or uuid
                alias = member.get("alias") or uuid
                if not uuid:
                    continue

                existing = cursor.execute(
                    "SELECT teacher_id FROM teacher WHERE wxid = ? OR name = ?",
                    (wxid, alias),
                ).fetchone()
                values = (
                    wxid,
                    alias,
                    member.get("score", 50),
                    member.get("balance", 0),
                    member.get("level", 1),
                    member.get("model", "basic"),
                    member.get("ai_flag", 0),
                    member.get("birthday", ""),
                    member.get("active", 1),
                    member.get("note", ""),
                )
                if existing:
                    cursor.execute(
                        """
                        UPDATE teacher
                        SET wxid = COALESCE(NULLIF(wxid, ''), ?),
                            name = CASE WHEN identity_type = 'teacher' THEN name ELSE ? END,
                            score = ?, balance = ?, level = CASE WHEN level IS NULL OR level = 0 THEN ? ELSE level END,
                            model = ?, ai_flag = ?, birthday = ?,
                            is_active = CASE WHEN identity_type = 'member' THEN ? ELSE is_active END,
                            note = COALESCE(NULLIF(note, ''), ?),
                            updated_at = datetime('now', 'localtime')
                        WHERE teacher_id = ?
                        """,
                        (*values, existing[0]),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO teacher
                        (teacher_id, name, wxid, role, level, is_active, notice_enabled,
                         score, balance, model, ai_flag, birthday,
                         note, identity_type, created_at)
                        VALUES (?, ?, ?, 'member', ?, ?, 1, ?, ?, ?, ?, ?, ?, 'member',
                                COALESCE(?, datetime('now', 'localtime')))
                        """,
                        (
                            _member_teacher_id(wxid),
                            alias,
                            wxid,
                            member.get("level", 1),
                            member.get("active", 1),
                            member.get("score", 50),
                            member.get("balance", 0),
                            member.get("model", "basic"),
                            member.get("ai_flag", 0),
                            member.get("birthday", ""),
                            member.get("note", ""),
                            member.get("create_at"),
                        ),
                    )
                migrated += 1
            conn.commit()
        return migrated

    def insert_permission(
        self,
        func,
        func_name,
        activate=1,
        black_list="",
        white_list="",
        type="",
        pattern="",
        keywords="",
        ai_flag=0,
        need_at=0,
        reply="",
        module="",
        level=1,
        priority=99,
        example="",
        check_permission=1,
        score=0,
        balance=0,
        notes="",
    ):
        """插入权限"""
        with self as m:
            m.__cursor__.execute(
                """
                INSERT INTO permission (func, func_name, activate, black_list, white_list, type, pattern, keywords, ai_flag, need_at, reply, module, level, priority, example, check_permission, score, balance, notes)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
                (
                    func,
                    func_name,
                    activate,
                    black_list,
                    white_list,
                    type,
                    pattern,
                    keywords,
                    ai_flag,
                    need_at,
                    reply,
                    module,
                    level,
                    priority,
                    example,
                    check_permission,
                    score,
                    balance,
                    notes,
                ),
            )
            self.__conn__.commit()
            return m.__cursor__.rowcount

    def delte_permission(self, id):
        """删除权限"""
        with self as m:
            m.__cursor__.execute("DELETE FROM permission WHERE id =?", (id,))
            self.__conn__.commit()
            return m.__cursor__.rowcount

    def permission_info(self, func=""):
        """获取权限信息"""
        if func == "":
            with self as m:
                m.__cursor__.execute("SELECT * FROM permission ORDER BY priority ASC, id ASC")
                result = m.__cursor__.fetchall()
            return result if result else None
        with self as m:
            m.__cursor__.execute("SELECT * FROM permission WHERE func =? ORDER BY priority ASC, id ASC", (func,))
            result = m.__cursor__.fetchone()
        return result if result else None

    def permission_func_list(self):
        """获取权限列表"""
        with self as m:
            m.__cursor__.execute("SELECT id, func, pattern FROM permission ORDER BY priority ASC, id ASC")
            result = m.__cursor__.fetchall()
        return result if result else None

    def permission_columns(self):
        """获取权限列名"""
        with self as m:
            m.__cursor__.execute(f"PRAGMA table_info(permission)")
            columns = m.__cursor__.fetchall()
            columns_list = [column[1] for column in columns]
        return columns_list

    def update_permission(self, id, **kwargs):
        """更新权限信息"""
        if not kwargs:
            return 0
        
        valid_columns = self.permission_columns()
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            if key in valid_columns and key != 'id':  # id 是主键
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if not set_clauses:
            return 0
            
        values.append(id)
        
        sql = f"UPDATE permission SET {', '.join(set_clauses)} WHERE id = ?"
        with self as m:
            m.__cursor__.execute(sql, tuple(values))
            self.__conn__.commit()
            return m.__cursor__.rowcount

    def get_permission_by_id(self, id):
        """根据ID获取权限信息"""
        with self as m:
            m.__cursor__.execute("SELECT * FROM permission WHERE id = ?", (id,))
            result = m.__cursor__.fetchone()
        return result if result else None

    def activate_func(self, id):
        """激活函数"""
        with self as m:
            m.__cursor__.execute(
                "UPDATE permission SET activate =? WHERE id =?", (1, id)
            )
            self.__conn__.commit()
            return m.__cursor__.rowcount

    def deactivate_func(self, id):
        """禁用函数"""
        with self as m:
            m.__cursor__.execute(
                "UPDATE permission SET activate =? WHERE id =?", (0, id)
            )
            self.__conn__.commit()
            return m.__cursor__.rowcount


async def query_permission(record):
    """查询权限"""
    text = record.content
    if text == "权限查询":
        with Member() as m:
            permission_list = m.permission_func_list()
        if not permission_list:
            send_text("权限查询失败：权限列表为空", record.sender)
            return None
        tips = "权限列表：\n"
        for permission in permission_list:
            tips += (
                f"id：{permission[0]}，名称：{permission[1]}，模式：{permission[2]}\n"
            )
        send_text(tips, record.sender)
        return None
    pid = re.match(r"权限查询-(\d+)$", text)
    if not pid:
        send_text("权限查询失败：请检查查询指令！", record.sender)
        return None
    pid = pid.group(1)
    with Member() as m:
        permission = m.permission_info(pid)
    if not permission:
        send_text("权限查询失败：权限不存在", record.sender)
        return None
    tips = (
        f"权限ID：{permission[0]}\n"
        f"功能：{permission[1]}\n"
        f"功能名称：{permission[2]}\n"
        f"是否启用：{permission[3]}\n"
        f"黑名单：{permission[4]}\n"
        f"白名单：{permission[5]}\n"
        f"类型：{permission[6]}\n"
        f"匹配模式：{permission[7]}\n"
        f"关键词：{permission[8]}\n"
        f"AI标记：{permission[9]}\n"
        f"是否需要@：{permission[10]}\n"
        f"回复内容：{permission[11]}\n"
        f"所属模块：{permission[12]}\n"
        f"权限等级：{permission[13]}\n"
        f"优先级：{permission[14]}\n"
        f"使用示例：{permission[15]}\n"
        f"权限检查：{permission[16]}\n"
        f"所需积分：{permission[17]}\n"
        f"所需余额：{permission[18]}"
    )
    send_text(tips, record.sender)
    return None


async def insert_permission(record):
    """插入权限"""
    text = record.content.replace("+权限\n", "")

    # 使用正则表达式匹配各个字段
    func = re.search(r"功能：(.+)\n", text)
    func_name = re.search(r"功能名称：(.+)\n", text)
    activate = re.search(r"是否启用：(.+)\n", text)
    black_list = re.search(r"黑名单：(.+)\n", text)
    white_list = re.search(r"白名单：(.+)\n", text)
    type_val = re.search(r"类型：(.+)\n", text)
    pattern = re.search(r"匹配模式：(.+)\n", text)
    keywords = re.search(r"关键词：(.+)\n", text)
    ai_flag = re.search(r"AI标记：(.+)\n", text)
    need_at = re.search(r"是否需要@：(.+)\n", text)
    # 使用非贪婪匹配和多行模式来获取回复内容
    reply = re.search(r"回复内容：([\s\S]*?)\n所属模块", text)
    module = re.search(r"所属模块：(.+)\n", text)
    level = re.search(r"权限等级：(.+)\n", text)
    priority = re.search(r"优先级：(.+)\n", text)
    example = re.search(r"使用示例：(.+)\n", text)
    check_permission = re.search(r"权限检查：(.+)\n", text)
    score = re.search(r"所需积分：(.+)\n", text)
    balance = re.search(r"所需余额：(.+)", text)
    # 处理回复内容的多行文本，去除首尾空白字符
    reply_content = reply.group(1).strip() if reply else ""
    # 验证必要字段
    if not all([func, func_name, pattern]):
        send_text(
            "添加权限失败：缺少必要字段（功能、功能名称、匹配模式）", record.sender
        )
        return None

    with Member() as m:
        result = m.insert_permission(
            func=func.group(1),
            func_name=func_name.group(1),
            activate=int(activate.group(1)) if activate else 1,
            black_list=(
                black_list.group(1)
                if black_list and black_list.group(1) != "None"
                else ""
            ),
            white_list=(
                white_list.group(1)
                if white_list and white_list.group(1) != "None"
                else ""
            ),
            type=type_val.group(1) if type_val and type_val.group(1) != "None" else "",
            pattern=pattern.group(1),
            keywords=(
                keywords.group(1) if keywords and keywords.group(1) != "None" else ""
            ),
            ai_flag=int(ai_flag.group(1)) if ai_flag else 0,
            need_at=int(need_at.group(1)) if need_at else 0,
            reply=reply_content,
            module=module.group(1) if module and module.group(1) != "None" else "",
            level=int(level.group(1)) if level else 1,
            priority=int(priority.group(1)) if priority else 99,
            example=example.group(1) if example and example.group(1) != "None" else "",
            check_permission=int(check_permission.group(1)) if check_permission else 1,
            score=int(score.group(1)) if score else 0,
            balance=int(balance.group(1)) if balance else 0,
        )

    if result > 0:
        send_text("添加权限成功", record.sender)
    else:
        send_text("添加权限失败", record.sender)
    return None


async def add_member(record):
    """插入会员：+会员：abc-10-lesson"""
    level = 1
    model = "basic"
    if "@chatroom" in record.roomid:
        send_text("群会员添加功能暂未实现！", record.sender)
        return 0
    results = record.content.split("-")
    if len(results) >= 3:
        try:
            level = results[1]
            model = results[2]
            member_str = (
                record.content.replace("：", ":")
                .replace(" ", "")
                .split("-")[0]
                .split(":")[1]
            )
            member_list = member_str.split(",")
            for mb in member_list:
                with Member() as m:
                    row = m.member_info(mb)
                if row:
                    send_text(f"会员已存在: {mb}", record.sender)
                else:
                    name = ""
                    alias = m.wxid_remark(mb)
                    if alias:
                        name = alias[0] if alias[0] else alias[1]
                    if name:
                        with Member() as m:
                            r = m.insert_member(mb, mb, name, level=level, model=model)
                            if r >= 1:
                                send_text(f"添加会员：{mb} {name}", record.sender)
                                return 0
                    send_text(
                        f"添加会员出错：{record.msg_id} {record.content}", record.sender
                    )
                    return -1
        except Exception as e:
            send_text(f"添加会员出错3：{record.msg_id}-{str(e)}", record.sender)
            return -1


async def del_member(record):
    """删除会员"""
    member_str = (
        record.content.replace("-会员", "")
        .replace("：", ":")
        .replace(" ", "")
        .split(":")[1]
    )
    member_list = member_str.split(",")
    for mb in member_list:
        with Member() as m:
            r = m.delte_member(mb)
            if r >= 1:
                send_text(f"删除会员：{mb}")
                return 0
    send_text(f"删除会员出错：{record.msg_id} {record.content}", record.sender)
    return -1


async def query_members(record):
    """查询会员"""
    with Member() as m:
        member_list = m.member_info()
    if not member_list:
        send_text("查询会员失败：会员列表为空", record.sender)
        return None
    tips = f"当前共有{len(member_list)}位会员：\n"
    for member in member_list:
        tips += f"uuid：{member[1]}, alias:{member[3]},level:{member[7]},model:{member[8]}\n"
    send_text(tips, record.sender)
    return None


async def start_func(record):
    """启动功能"""
    if record.sender not in Config().get_config("admin_list", "wechat.yaml"):
        send_text("权限不足", record.sender)
        return None
    pattern = r"^START (.*)"
    match = re.search(pattern, record.content)
    if match:
        func_id = match.group(1)
        try:
            with Member() as m:
                m.activate_func(func_id)
                send_text(f"start_func: {func_id}", record.sender)
                return True
        except Exception as e:
            self.log.error(f"start_func Failed: {e}")
            send_text(f"start_func Failed: {e}", record.sender)
            return False


async def stop_func(record: any):
    if record.sender not in Config().get_config("admin_list", "wechat.yaml"):
        return False
    pattern = r"^STOP (.*)"
    match = re.search(pattern, record.content)
    if match:
        func_id = match.group(1)
        try:
            with Member() as m:
                m.deactivate_func(func_id)
                send_text(f"stop_func: {func_id}", record.sender)
                return True
        except Exception as e:
            self.log.error(f"stop_func Failed: {e}")
            send_text(f"stop_func Failed: {e}", record.sender)
            return False


def check_permission(func):
    async def wrapper(record, *args, **kwargs):
        if has_permission(func, record, *args, **kwargs):
            return await func(record, *args, **kwargs)
        else:
            send_text(
                f"{record.msg_id}-{func.__name__}:鉴权失败,请联系管理员吧",
                record.sender,
            )
            return None

    return wrapper


def has_permission(func, record, *args, **kwargs):
    # TODO: 积分和余额的判断
    if record.is_group:
        uuid = record.sender + "#" + record.roomid
    else:
        uuid = record.sender
    with Member() as m:
        member_info = m.member_info(uuid)
        permission = m.permission_info(func.__name__)
    if not permission:
        send_text(f"{record.msg_id}-{func.__name__}:未注册权限", record.roomid)
        return False
    if permission[15] == 0:
        return True
    if not member_info:
        send_text(f"{record.msg_id}:未注册会员", record.roomid)
        return False
    if int(permission[13]) > int(member_info[7]):
        send_text(f"{record.msg_id}-{func.__name__}:会员等级不足", record.roomid)
        return False
    if permission[12] not in member_info[8].split("/"):
        send_text(f"{record.msg_id}-{func.__name__}:会员模块不足", record.roomid)
        return False
    return True
