# -*- coding: utf-8 -*-
"""
跨平台路径工具

自动检测操作系统并返回对应的路径配置
"""

import platform
import os
from typing import Optional


def get_system() -> str:
    """获取操作系统类型"""
    return platform.system()


def get_cross_platform_path(base_key: str, config: dict) -> Optional[str]:
    """
    从配置字典中获取跨平台路径

    配置格式示例:
        方式1 - 按系统分类:
            lesson_dir:
                Darwin: /Users/yoin/bdsync/temp/lesson
                Windows: D:/lesson
                Linux: /home/user/lesson

        方式2 - 后缀方式:
            lesson_dir: /Users/yoin/bdsync/temp/lesson  # 默认
            lesson_dir_windows: D:/lesson

    Args:
        base_key: 基础键名，如 "lesson_dir"
        config: 配置字典

    Returns:
        str: 对应系统的路径
    """
    system = get_system()

    # 方式1: 配置为字典格式，按系统分类
    if base_key in config and isinstance(config[base_key], dict):
        system_config = config[base_key]
        if system in system_config:
            return system_config[system]
        # 默认值
        if "default" in system_config:
            return system_config["default"]
        # 返回第一个可用值
        for key in ["Darwin", "Windows", "Linux"]:
            if key in system_config:
                return system_config[key]
        return None

    # 方式2: 后缀方式 (key_windows, key_linux 等)
    system_suffix_map = {
        "Windows": "_windows",
        "Darwin": "",  # Mac 作为默认，无后缀
        "Linux": "_linux",
    }

    suffix = system_suffix_map.get(system, "")

    # 先尝试带后缀的键
    if suffix:
        suffixed_key = f"{base_key}{suffix}"
        if suffixed_key in config:
            return config[suffixed_key]

    # 回退到基础键
    if base_key in config:
        return config[base_key]

    return None


def normalize_path(path: str) -> str:
    """
    规范化路径，处理不同操作系统的路径分隔符

    Args:
        path: 原始路径

    Returns:
        str: 规范化后的路径
    """
    if not path:
        return path

    # 统一转换为当前系统的路径格式
    return os.path.normpath(path)


def get_lesson_dir(config: dict) -> Optional[str]:
    """
    获取课程数据目录（便捷函数）

    Args:
        config: 配置字典

    Returns:
        str: 课程数据目录路径
    """
    path = get_cross_platform_path("lesson_dir", config)
    if path:
        return normalize_path(path)
    return None