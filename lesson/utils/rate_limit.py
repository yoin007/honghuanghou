# _*_ coding: utf-8 _*_
# API 限流工具

import time
import os
from collections import defaultdict
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """简单的内存限流器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._requests: Dict[str, list] = defaultdict(list)
        # 默认配置
        self.default_limit = int(os.getenv("RATE_LIMIT_DEFAULT", "100"))  # 每分钟 100 次
        self.default_window = 60  # 60 秒窗口

    def _cleanup(self, key: str, window: int = 60):
        """清理过期的请求记录"""
        now = time.time()
        self._requests[key] = [
            t for t in self._requests[key]
            if now - t < window
        ]

    def is_allowed(
        self,
        key: str,
        limit: int = None,
        window: int = None
    ) -> Tuple[bool, int]:
        """
        检查请求是否允许

        返回: (是否允许, 剩余次数)
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        self._cleanup(key, window)

        now = time.time()
        request_times = self._requests[key]

        # 检查是否超过限制
        if len(request_times) >= limit:
            return False, 0

        # 记录本次请求
        request_times.append(now)
        self._requests[key] = request_times

        return True, limit - len(request_times)

    def get_remaining(self, key: str, limit: int = None, window: int = None) -> int:
        """获取剩余请求次数"""
        limit = limit or self.default_limit
        window = window or self.default_window

        self._cleanup(key, window)
        return max(0, limit - len(self._requests[key]))

    def reset(self, key: str = None):
        """重置限流记录"""
        if key:
            self._requests.pop(key, None)
        else:
            self._requests.clear()


# 全局限流器实例
rate_limiter = RateLimiter()


def check_rate_limit(
    key: str,
    limit: int = None,
    window: int = 60
):
    """
    限流装饰器/检查函数

    用法:
    # 方式1: 手动检查
    allowed, remaining = check_rate_limit("user:123", limit=10)

    # 方式2: 装饰器（需要在异常处理中使用）
    @check_rate_limit("login", limit=5, window=60)
    def login():
        ...
    """
    allowed, remaining = rate_limiter.is_allowed(key, limit, window)
    return allowed, remaining
