# _*_ coding: utf-8 _*_
# 操作日志工具

import os
import json
import logging
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)


class OperationLogger:
    """操作日志记录器"""

    def __init__(self, log_dir: str = None):
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "operations")
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # 创建日志文件
        self.log_file = os.path.join(log_dir, f"operation_{datetime.now().strftime('%Y%m%d')}.log")

    def log(self, operation: str, username: str = None, details: dict = None, level: str = "info"):
        """记录操作日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "username": username or "anonymous",
            "details": details or {},
            "level": level
        }

        # 写入文件
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write operation log: {e}")

        # 同时输出到应用日志
        getattr(logger, level)(f"[{operation}] {username or 'anonymous'}: {json.dumps(details, ensure_ascii=False) if details else ''}")

    def info(self, operation: str, username: str = None, details: dict = None):
        """记录信息日志"""
        self.log(operation, username, details, "info")

    def warning(self, operation: str, username: str = None, details: dict = None):
        """记录警告日志"""
        self.log(operation, username, details, "warning")

    def error(self, operation: str, username: str = None, details: dict = None):
        """记录错误日志"""
        self.log(operation, username, details, "error")


# 全局操作日志实例
operation_logger = OperationLogger()


def log_operation(operation: str, get_username=None):
    """
    操作日志装饰器

    用法:
    @log_operation("删除作业")
    async def delete_homework(hw_id):
        ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            username = None
            if get_username:
                try:
                    username = get_username(*args, **kwargs)
                except:
                    pass

            try:
                result = await func(*args, **kwargs)
                operation_logger.info(
                    operation,
                    username,
                    {
                        "args": str(args)[:200],
                        "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                operation_logger.error(
                    operation,
                    username,
                    {
                        "args": str(args)[:200],
                        "error": str(e)[:200],
                        "status": "failed"
                    }
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            username = None
            if get_username:
                try:
                    username = get_username(*args, **kwargs)
                except:
                    pass

            try:
                result = func(*args, **kwargs)
                operation_logger.info(
                    operation,
                    username,
                    {
                        "args": str(args)[:200],
                        "kwargs": {k: str(v)[:100] for k, v in kwargs.items()},
                        "status": "success"
                    }
                )
                return result
            except Exception as e:
                operation_logger.error(
                    operation,
                    username,
                    {
                        "args": str(args)[:200],
                        "error": str(e)[:200],
                        "status": "failed"
                    }
                )
                raise

        # 根据函数类型返回对应的包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def log_user_action(action: str, username: str = None):
    """记录用户行为"""
    operation_logger.info(action, username)


def log_system_event(event: str, details: dict = None):
    """记录系统事件"""
    operation_logger.info(f"[SYSTEM] {event}", "system", details)
