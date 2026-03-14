# _*_ coding: utf-8 _*_
# 系统监控与告警工具

import os
import time
import logging
from datetime import datetime
from functools import wraps
import threading

logger = logging.getLogger(__name__)

# 告警阈值配置
ALERT_THRESHOLDS = {
    "cpu_percent": 80,      # CPU 使用率超过 80% 告警
    "memory_percent": 85,   # 内存使用率超过 85% 告警
    "disk_percent": 90,     # 磁盘使用率超过 90% 告警
}


class SystemMonitor:
    """系统监控器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self._initialized = False
        self._last_alert_time = {}
        self._alert_cooldown = 300  # 告警冷却时间（秒）

    def initialize(self):
        """初始化监控器"""
        if self._initialized:
            return
        self._initialized = True
        logger.info("System monitor initialized")

    def get_system_metrics(self):
        """获取系统指标"""
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # 获取进程信息
            process = psutil.Process()
            process_info = {
                "pid": process.pid,
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "num_threads": process.num_threads()
            }

            return {
                "cpu_percent": cpu,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / 1024 / 1024,
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / 1024 / 1024 / 1024,
                "process": process_info,
                "timestamp": datetime.now().isoformat()
            }
        except ImportError:
            logger.warning("psutil not installed, using basic metrics")
            return self._get_basic_metrics()
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return self._get_basic_metrics()

    def _get_basic_metrics(self):
        """获取基础指标（无 psutil 时）"""
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "timestamp": datetime.now().isoformat()
        }

    def check_alerts(self, metrics):
        """检查是否需要告警"""
        alerts = []

        for key, threshold in ALERT_THRESHOLDS.items():
            if key in metrics and metrics[key] > threshold:
                # 检查冷却时间
                alert_key = f"{key}_{threshold}"
                now = time.time()
                last_alert = self._last_alert_time.get(alert_key, 0)

                if now - last_alert > self._alert_cooldown:
                    alerts.append({
                        "type": key,
                        "value": metrics[key],
                        "threshold": threshold,
                        "timestamp": datetime.now().isoformat()
                    })
                    self._last_alert_time[alert_key] = now

        if alerts:
            logger.warning(f"System alerts triggered: {alerts}")

        return alerts

    def get_status(self):
        """获取系统状态"""
        metrics = self.get_system_metrics()
        alerts = self.check_alerts(metrics)

        # 判断健康状态
        is_healthy = len(alerts) == 0
        for key, threshold in ALERT_THRESHOLDS.items():
            if key in metrics and metrics[key] > threshold:
                is_healthy = False
                break

        return {
            "status": "healthy" if is_healthy else "warning",
            "metrics": metrics,
            "alerts": alerts
        }


# 全局监控器实例
monitor = SystemMonitor()


def init_monitor():
    """初始化监控器"""
    monitor.initialize()


def get_system_status():
    """获取系统状态"""
    return monitor.get_status()


def get_metrics():
    """获取系统指标"""
    return monitor.get_system_metrics()


# 装饰器：监控函数执行时间
def monitor_performance(threshold_ms=1000):
    """
    监控函数执行时间

    用法:
    @monitor_performance(threshold_ms=500)
    async def slow_function():
        ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.time() - start_time) * 1000
                if elapsed > threshold_ms:
                    logger.warning(
                        f"Function {func.__name__} took {elapsed:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.time() - start_time) * 1000
                if elapsed > threshold_ms:
                    logger.warning(
                        f"Function {func.__name__} took {elapsed:.2f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
