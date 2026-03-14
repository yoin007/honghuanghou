# _*_ coding: utf-8 _*_
# Redis 缓存工具

import os
import json
import redis
from functools import wraps
from typing import Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis 缓存管理器"""

    _instance = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._connect()

    def _connect(self):
        """连接 Redis"""
        host = os.getenv("REDIS_HOST", "localhost")
        port = int(os.getenv("REDIS_PORT", "6379"))
        password = os.getenv("REDIS_PASSWORD", None)
        db = int(os.getenv("REDIS_DB", "0"))

        try:
            self._client = redis.Redis(
                host=host,
                port=port,
                password=password if password else None,
                db=db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # 测试连接
            self._client.ping()
            logger.info(f"Redis connected: {host}:{port}")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}, caching disabled")
            self._client = None

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self._client:
            return None

        try:
            value = self._client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None

    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """设置缓存"""
        if not self._client:
            return False

        try:
            self._client.setex(key, expire, json.dumps(value))
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self._client:
            return False

        try:
            self._client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配的所有缓存"""
        if not self._client:
            return 0

        try:
            keys = self._client.keys(pattern)
            if keys:
                return self._client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
        return 0


# 全局缓存实例
cache = RedisCache()


def cached(key_prefix: str, expire: int = 3600):
    """
    缓存装饰器

    用法:
    @cached("user:", expire=1800)
    def get_user(user_id):
        return database.query(user_id)
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存 key
            key_parts = [key_prefix]
            if args:
                key_parts.extend([str(arg) for arg in args])
            cache_key = ":".join(key_parts)

            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数
            result = func(*args, **kwargs)

            # 存入缓存
            if result is not None:
                cache.set(cache_key, result, expire)

            return result
        return wrapper
    return decorator
