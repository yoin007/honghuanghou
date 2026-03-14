# _*_ coding: utf-8 _*_

import os
import json
import logging
import logging.config
from logging.handlers import RotatingFileHandler
from datetime import datetime
from logging import Formatter


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

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data, ensure_ascii=False)


class LogConfig:
    def __init__(self, module_name="bot", use_json=False):
        self.log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        self.log_name = module_name
        self.use_json = use_json
        self.__config_logging()

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
                "info_file_handler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "formatter": "json" if self.use_json else "detailed",
                    "filename": os.path.join(
                        self.log_path, f"{self.log_name}_{current_date}.log"
                    ),
                    "maxBytes": 10 * 1024 * 1024,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf-8",
                    "mode": "a",
                },
                "error_file_handler": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "json" if self.use_json else "detailed",
                    "filename": os.path.join(
                        self.log_path, f"{self.log_name}_error_{current_date}.log"
                    ),
                    "maxBytes": 10 * 1024 * 1024,  # 10MB
                    "backupCount": 5,
                    "encoding": "utf-8",
                    "mode": "a",
                },
            },
            "loggers": {
                "": {  # Root logger
                    "handlers": [
                        "console_handler",
                        "info_file_handler",
                        "error_file_handler",
                    ],
                    "level": "INFO",
                    "propagate": True,
                },
                "apscheduler": {
                    "handlers": [
                        "console_handler",
                        "info_file_handler",
                        "error_file_handler",
                    ],
                    "level": "WARNING",
                    "propagate": False,
                },
                "watchfiles": {
                    "handlers": [
                        "console_handler",
                        "info_file_handler",
                        "error_file_handler",
                    ],
                    "level": "ERROR",
                    "propagate": False,
                },
                "sqlite3": {
                    "handlers": [
                        "console_handler",
                        "info_file_handler",
                        "error_file_handler",
                    ],
                    "level": "WARNING",
                    "propagate": False,
                },
            },
        }

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
