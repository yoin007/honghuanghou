# _*_ coding: utf-8 _*_

import os
import json
import uuid
import logging
import logging.config
from logging.handlers import RotatingFileHandler
from datetime import datetime
from logging import Formatter
from contextvars import ContextVar
from typing import Optional

# 请求追踪 ID 上下文变量
request_id_ctx: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def get_request_id() -> str:
    """获取当前请求的追踪 ID"""
    return request_id_ctx.get() or str(uuid.uuid4())[:8]


def set_request_id(request_id: str = None) -> str:
    """设置当前请求的追踪 ID"""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_ctx.set(request_id)
    return request_id


class RequestIdFormatter(Formatter):
    """带请求追踪 ID 的 formatter"""

    def __init__(self, fmt=None, datefmt=None, style='%', use_json=False):
        super().__init__(fmt, datefmt, style)
        self.use_json = use_json

    def format(self, record):
        # 添加请求 ID
        request_id = get_request_id()
        record.request_id = request_id

        if self.use_json:
            return self._format_json(record)
        else:
            return self._format_text(record)

    def _format_json(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": record.request_id
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data, ensure_ascii=False)

    def _format_text(self, record):
        # 自定义格式添加 request_id
        original_msg = record.getMessage()
        record.msg = f"[{record.request_id}] {original_msg}"
        return super().format(record)


class JsonFormatter(Formatter):
    """JSON 格式日志 formatter"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # 添加请求 ID（如果存在）
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data, ensure_ascii=False)


class LogConfig:
    # 保留天数（只清理一次）
    _retention_days = None
    _cleaned = False

    def __init__(self, module_name="app", use_json=False):
        self.log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        self.log_name = module_name
        self.use_json = use_json
        self.__config_logging()
        self.__cleanup_old_logs()

    @classmethod
    def __get_retention_days(cls):
        """从 lesson.yaml 读取 log_retention_days，默认 1095 天（3 年）"""
        if cls._retention_days is None:
            days = 1095
            try:
                import yaml
                cfg_file = os.path.join(os.path.dirname(__file__), "lesson.yaml")
                with open(cfg_file, "r", encoding="utf-8") as f:
                    days = int(yaml.safe_load(f).get("log_retention_days", 1095))
            except Exception:
                pass
            cls._retention_days = days
        return cls._retention_days

    @classmethod
    def __cleanup_old_logs(cls):
        """删除超过保留天数的 *_%Y%m%d.log 历史日志文件（每个进程只执行一次）"""
        if cls._cleaned:
            return
        cls._cleaned = True
        try:
            import re
            log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
            retention = cls.__get_retention_days()
            today = datetime.now()
            pattern = re.compile(r"_(\d{8})\.log$")
            for fname in os.listdir(log_path):
                m = pattern.search(fname)
                if not m:
                    continue
                try:
                    fdate = datetime.strptime(m.group(1), "%Y%m%d")
                except ValueError:
                    continue
                if (today - fdate).days > retention:
                    os.remove(os.path.join(log_path, fname))
        except Exception:
            pass

    def __config_logging(self):
        """配置日志"""
        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)

        # 获取当前日期作为日志文件名的一部分
        current_date = datetime.now().strftime("%Y%m%d")

        # 根据配置选择 formatter
        if self.use_json:
            json_formatter = JsonFormatter()
            formatters = {
                "json": {
                    "()": JsonFormatter
                }
            }
        else:
            formatters = {
                "default": {
                    "format": "[%(asctime)s] [%(name)s] [%(levelname)s] [%(filename)s] [%(funcName)s:%(lineno)d] %(message)s"
                },
                "detailed": {
                    "format": "[%(asctime)s] [%(name)s] [%(levelname)s] [%(funcName)s:%(lineno)d] [%(threadName)s] %(message)s"
                },
                "access": {
                    "format": "[%(asctime)s] %(message)s"
                },
            }

        logging_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": formatters,
            "handlers": {
                "console_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "json" if self.use_json else "default",
                    "stream": "ext://sys.stdout",
                },
                # app 主文件：root 兜底，未挂专属文件的模块日志都落这里（保持旧行为不丢日志）
                "app_file_handler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "json" if self.use_json else "detailed",
                    "filename": os.path.join(self.log_path, f"app_{current_date}.log"),
                    "maxBytes": 10 * 1024 * 1024,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf-8",
                    "mode": "a",
                },
                "error_file_handler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "json" if self.use_json else "detailed",
                    "filename": os.path.join(self.log_path, f"error_{current_date}.log"),
                    "maxBytes": 10 * 1024 * 1024,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf-8",
                    "mode": "a",
                },
                # 模块专属文件（delay=True：首次写入才创建文件，避免空文件）
                "access_file_handler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "access",
                    "filename": os.path.join(self.log_path, f"access_{current_date}.log"),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "encoding": "utf-8",
                    "mode": "a",
                    "delay": True,
                },
                "wxbot_file_handler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "json" if self.use_json else "detailed",
                    "filename": os.path.join(self.log_path, f"wxbot_{current_date}.log"),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "encoding": "utf-8",
                    "mode": "a",
                    "delay": True,
                },
            },
            "loggers": {
                "": {  # Root logger：控制台 + app 主文件 + 错误汇聚
                    "handlers": [
                        "console_handler",
                        "app_file_handler",
                        "error_file_handler",
                    ],
                    "level": "INFO",
                    "propagate": True,
                },
                "access": {  # 访问日志：专属文件，不进 app/控制台刷屏
                    "handlers": ["access_file_handler"],
                    "level": "INFO",
                    "propagate": False,
                },
                "wxbot": {  # 微信机器人：专属文件 + 原有链路（控制台/app 文件）不丢
                    "handlers": ["wxbot_file_handler"],
                    "level": "INFO",
                    "propagate": True,
                },
                "uvicorn.access": {  # 访问记录由 access 中间件负责，此处降噪
                    "handlers": ["console_handler"],
                    "level": "WARNING",
                    "propagate": False,
                },
                "apscheduler": {
                    "handlers": [
                        "console_handler",
                        "error_file_handler",
                    ],
                    "level": "WARNING",
                    "propagate": False,
                },
                "watchfiles": {
                    "handlers": [
                        "console_handler",
                        "error_file_handler",
                    ],
                    "level": "ERROR",
                    "propagate": False,
                },
                "sqlite3": {
                    "handlers": [
                        "console_handler",
                        "error_file_handler",
                    ],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
        }

        # 模块专属文件 handler 已统一在上方定义（delay=True 惰性创建）
        # 配置日志
        logging.config.dictConfig(logging_config)

        # 设置第三方库的日志级别
        logging.getLogger("watchfiles.main").setLevel(logging.ERROR)
        logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
        logging.getLogger("sqlite3").setLevel(logging.WARNING)

    def get_logger(self):
        return logging.getLogger(self.log_name)


# 使用方法
# 标准日志
# logger = LogConfig(__name__).get_logger()
# logger.info("This is an info message")
# logger.error("This is an error message")

# JSON 格式日志（适合日志收集系统）
# logger = LogConfig(__name__, use_json=True).get_logger()
# logger.info("This is a JSON info message")
