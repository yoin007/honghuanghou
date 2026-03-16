# _*_ coding: utf-8 _*_
# @Time: 2024/09/23 18:27
# @Author: Tech_T


import json
import requests
import sqlite3
import time
from datetime import datetime, timedelta
import threading

from config.log import LogConfig
from config.config import Config
from client import Client

log = LogConfig().get_logger()
config = Config()
base_url = config.get_config("base_url", "wechat.yaml")
static_url = config.get_config("static_url", "wechat.yaml")
admin_wxid = config.get_config("admin", "wechat.yaml")


class QueueDB:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "initialized"):
            return
        self.initialized = True
        self.expeired_minutes = 28
        self.expeired_time = None
        self.wxid = config.get_config("bot_wxid", "wechat.yaml")
        self._local = threading.local()
        self.client = Client()
        self.max_retries = 3
        self.retry_delay = 2

    def __enter__(self, db="databases/queues.db"):
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(db, timeout=30)
            self._local.connection.row_factory = sqlite3.Row
            self._local.cursor = self._local.connection.cursor()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            del self._local.connection
            del self._local.cursor

    def __create_table__(self):
        """
        创建队列表
        producer: 消息生产者
        consumer: 消息消费者
        p_time: 消息生产时间
        c_time: 消息消费时间
        """
        self._local.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS queues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT DEFAULT 'pending',
                msg_id TEXT,
                data TEXT,
                producer TEXT,
                p_time TEXT,
                consumer TEXT,
                c_time TEXT,
                timestamp INTEGER,
                retry_count INTEGER DEFAULT 0,
                error_message TEXT
                )"""
        )
        self._local.connection.commit()

    def __produce__(self, data: dict, consumer: str, producer: str, msg_id: str = ""):
        """
        生产消息队列
        :param msg_id: 对应微信消息的msg_id
        :param data: 消息内容
        :param producer: 消息生产者
        :param consumer: 消息消费者,api
        :return:
        """
        data_string = json.dumps(data, ensure_ascii=False)

        record = {
            "msg_id": msg_id,
            "data": data_string,
            "producer": producer,
            "p_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "consumer": consumer,
            "c_time": "",
            "timestamp": time.time().__int__(),
            "status": "pending",
            "retry_count": 0,
            "error_message": "",
        }
        try:
            self._local.cursor.execute(
                """
            INSERT INTO queues (msg_id, data, producer, p_time, consumer, c_time, timestamp, status, retry_count, error_message) VALUES (:msg_id, :data, :producer, :p_time, :consumer, :c_time, :timestamp, :status, :retry_count, :error_message)
            """,
                record,
            )
            self._local.connection.commit()
        except Exception as e:
            log.error(f"生产消息队列失败: {e}")

    def __is_message_expired__(self, record):
        """
        检查消息是否过期
        :param record: 消息记录
        :return: bool
        """
        if not record:
            return False
        p_time_str = record["p_time"]
        if not p_time_str:
            return False
        try:
            p_time = datetime.strptime(p_time_str, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            expired_minutes = (now - p_time).total_seconds() / 60
            return expired_minutes > self.expeired_minutes
        except Exception as e:
            log.error(f"检查消息过期失败: {e}")
            return False

    def __clean_expired_messages__(self):
        """
        清理过期消息
        :return: 清理的消息数量
        """
        try:
            now = datetime.now()
            expired_timestamp = int((now - timedelta(minutes=self.expeired_minutes)).timestamp())
            self._local.cursor.execute(
                """
                DELETE FROM queues WHERE status = 'pending' AND timestamp < ?
                """,
                (expired_timestamp,),
            )
            deleted_count = self._local.cursor.rowcount
            self._local.connection.commit()
            if deleted_count > 0:
                log.info(f"清理了 {deleted_count} 条过期消息")
            return deleted_count
        except Exception as e:
            log.error(f"清理过期消息失败: {e}")
            return 0

    def __retry_failed_messages__(self):
        """
        重试失败的消息
        :return: 重试的消息数量
        """
        try:
            self._local.cursor.execute(
                """
                UPDATE queues SET status = 'pending', retry_count = 0, error_message = ''
                WHERE status = 'failed' AND retry_count < ?
                """,
                (self.max_retries,),
            )
            retry_count = self._local.cursor.rowcount
            self._local.connection.commit()
            if retry_count > 0:
                log.info(f"重置了 {retry_count} 条失败消息进行重试")
            return retry_count
        except Exception as e:
            log.error(f"重试失败消息失败: {e}")
            return 0

    def get_queue_status(self):
        """
        获取队列状态
        :return: dict
        """
        try:
            with sqlite3.connect("databases/queues.db") as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT status, COUNT(*) as count FROM queues GROUP BY status
                    """
                )
                status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}

                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM queues WHERE status = 'pending' AND timestamp < ?
                    """,
                    (int((datetime.now() - timedelta(minutes=self.expeired_minutes)).timestamp()),),
                )
                expired_count = cursor.fetchone()["count"]

                cursor.execute("SELECT COUNT(*) as count FROM queues")
                total_count = cursor.fetchone()["count"]

                return {
                    "total": total_count,
                    "pending": status_counts.get("pending", 0),
                    "sending": status_counts.get("sending", 0),
                    "success": status_counts.get("success", 0),
                    "failed": status_counts.get("failed", 0),
                    "expired": expired_count,
                }
        except Exception as e:
            log.error(f"获取队列状态失败: {e}")
            return {}

    def __update_message_status__(self, msg_id, status, error_message=""):
        """
        更新消息状态
        :param msg_id: 消息ID
        :param status: 状态
        :param error_message: 错误信息
        """
        try:
            c_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            self._local.cursor.execute(
                """
                UPDATE queues SET status = ?, c_time = ?, error_message = ? WHERE id = ?
                """,
                (status, c_time, error_message, msg_id),
            )
            self._local.connection.commit()
        except Exception as e:
            log.error(f"更新消息状态失败: {e}")

    def __increment_retry_count__(self, msg_id):
        """
        增加重试计数
        :param msg_id: 消息ID
        """
        try:
            self._local.cursor.execute(
                """
                UPDATE queues SET retry_count = retry_count + 1 WHERE id = ?
                """,
                (msg_id,),
            )
            self._local.connection.commit()
        except Exception as e:
            log.error(f"增加重试计数失败: {e}")

    def __consume__(self):
        """
        消费消息队列（带重试机制）
        :return:
        """
        self.__clean_expired_messages__()

        with sqlite3.connect("databases/queues.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT * FROM queues WHERE status = 'pending' ORDER BY timestamp ASC LIMIT 1
                    """
                )
                record = cursor.fetchone()
                if not record:
                    return None

                if self.__is_message_expired__(record):
                    self.__update_message_status__(record["id"], "expired", "消息已过期")
                    log.warning(f"消息 {record['id']} 已过期")
                    return None

                self.__update_message_status__(record["id"], "sending")

                for attempt in range(self.max_retries):
                    try:
                        token = self.client._check_token()
                        if not token:
                            log.error(f"获取token失败")
                            time.sleep(self.retry_delay * (attempt + 1))
                            continue

                        headers = {
                            "content-type": "application/x-www-form-urlencoded; charset=utf-8",
                            "Authorization": f"Bearer {token}",
                        }

                        r = requests.post(
                            url=record["consumer"],
                            data=json.loads(record["data"]),
                            headers=headers,
                            timeout=30,
                        )
                        r.raise_for_status()

                        try:
                            response_data = r.json()
                            code = response_data.get("code")
                            message = response_data.get("message", "")
                            if code == 0 or "成功" in message or "success" in message.lower():
                                self.__update_message_status__(record["id"], "success")
                                log.info(f"消息 {record['id']} 发送成功")
                                return r.content.decode("utf-8")
                            else:
                                error_msg = message if message else f"API返回码: {code}"
                                log.warning(f"API 返回错误: {error_msg}, 消息ID: {record['id']}, 尝试 {attempt + 1}/{self.max_retries}")
                                if attempt < self.max_retries - 1:
                                    time.sleep(self.retry_delay * (2 ** attempt))
                                    continue
                                else:
                                    self.__increment_retry_count__(record["id"])
                                    self.__update_message_status__(record["id"], "failed", error_msg)
                                    return -1
                        except json.JSONDecodeError:
                            if r.status_code == 200:
                                self.__update_message_status__(record["id"], "success")
                                return r.content.decode("utf-8")
                            log.warning(f"解析 API 响应失败, 消息ID: {record['id']}, 尝试 {attempt + 1}/{self.max_retries}")
                            if attempt < self.max_retries - 1:
                                time.sleep(self.retry_delay * (2 ** attempt))
                                continue
                            else:
                                self.__increment_retry_count__(record["id"])
                                self.__update_message_status__(record["id"], "failed", "解析响应失败")
                                return -1

                    except requests.exceptions.Timeout:
                        log.warning(f"请求超时, 消息ID: {record['id']}, 尝试 {attempt + 1}/{self.max_retries}")
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        else:
                            self.__increment_retry_count__(record["id"])
                            self.__update_message_status__(record["id"], "failed", "请求超时")
                            return -1

                    except requests.exceptions.RequestException as e:
                        log.warning(f"请求异常: {e}, 消息ID: {record['id']}, 尝试 {attempt + 1}/{self.max_retries}")
                        if attempt < self.max_retries - 1:
                            time.sleep(self.retry_delay * (2 ** attempt))
                            continue
                        else:
                            self.__increment_retry_count__(record["id"])
                            self.__update_message_status__(record["id"], "failed", str(e))
                            return -1

                    except Exception as e:
                        log.error(f"发送消息未知异常: {e}, 消息ID: {record['id']}")
                        self.__increment_retry_count__(record["id"])
                        self.__update_message_status__(record["id"], "failed", str(e))
                        return -1

            except Exception as e:
                log.error(f"消费消息队列失败: {e}")
                return None


def send_text(content: str, receiver: str, aters: str = "", producer: str = "main"):
    """发送文本消息"""
    data = {
        "friend_id": receiver,
        "message": content,
        "remark": aters,
        "content_type": 1,
    }
    with QueueDB() as queue:
        queue.__produce__(data, base_url + "send_message_250514.html", producer)


def send_image(path: str = "", receiver: str = "", producer: str = "main"):
    """发送图片消息"""
    if not (path.startswith("http://") or path.startswith("https://")):
        path = static_url + path
    data = {"friend_id": receiver, "message": path, "content_type": 2}
    with QueueDB() as queue:
        queue.__produce__(data, base_url + "send_message_250514.html", producer)


def send_file(file_dict, receiver: str = "", producer: str = "main"):
    """发送文件消息"""
    if isinstance(file_dict, str):
        file_path = file_dict
        file_name = file_path.split("/")[-1]
        file_dict = {"name": file_name, "url": file_path}
    if not (
        file_dict.get("url", "").startswith("http://")
        or file_dict.get("url", "").startswith("https://")
    ):
        file_dict["url"] = static_url + file_dict.get("url")
    data = {
        "friend_id": receiver,
        "content_type": "8",
        "message": json.dumps(file_dict),
    }
    with QueueDB() as queue:
        queue.__produce__(data, base_url + "send_message_250514.html", producer)


def send_app_msg(xml_dict: dict, receiver: str, type: int = 13, producer: str = "main"):
    """发送应用消息"""
    data = {
        "friend_id": receiver,
        "content_type": type,
        "message": json.dumps(xml_dict),
    }
    with QueueDB() as queue:
        queue.__produce__(data, base_url + "send_message_250514.html", producer)


async def get_queue_info(msg=None):
    """获取队列状态信息"""
    with QueueDB() as queue:
        rsp = queue.get_queue_status()
        send_text(f"队列状态: {rsp}", receiver=admin_wxid, producer="queue")
        return rsp


def clean_expired_messages():
    """清理过期消息"""
    with QueueDB() as queue:
        return queue.__clean_expired_messages__()


def retry_failed_messages():
    """重试失败的消息"""
    with QueueDB() as queue:
        return queue.__retry_failed_messages__()


if __name__ == "__main__":
    db = QueueDB()
    db.__enter__()
    db.__create_table__()
    log.info("Done!")
    log.info("队列状态: %s", db.get_queue_status())
