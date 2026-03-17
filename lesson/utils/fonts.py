# -*- coding: utf-8 -*-
"""
跨平台字体工具

自动检测操作系统并返回合适的中文字体
"""

import platform
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


# 各操作系统默认中文字体配置
FONT_CONFIG = {
    "Windows": {
        "sans_serif": ["Microsoft YaHei", "SimHei", "SimSun", "KaiTi"],
        "font_family": "Microsoft YaHei",
        "font_file": "msyh.ttc",  # 微软雅黑
    },
    "Darwin": {  # macOS
        "sans_serif": ["PingFang SC", "Hiragino Sans GB", "STHeiti", "Heiti SC"],
        "font_family": "PingFang SC",
        "font_file": "PingFang.ttc",
    },
    "Linux": {
        "sans_serif": ["WenQuanYi Micro Hei", "Noto Sans CJK SC", "Droid Sans Fallback", "DejaVu Sans"],
        "font_family": "WenQuanYi Micro Hei",
        "font_file": "wqy-microhei.ttc",
    },
}


def get_system() -> str:
    """获取操作系统类型"""
    return platform.system()


def get_chinese_font_family() -> str:
    """
    获取适合当前操作系统的中文字体名称

    Returns:
        str: 字体名称
    """
    system = get_system()
    config = FONT_CONFIG.get(system, FONT_CONFIG["Linux"])
    return config["font_family"]


def get_chinese_fonts_list() -> List[str]:
    """
    获取适合当前操作系统的中文字体列表（按优先级排序）

    Returns:
        List[str]: 字体列表
    """
    system = get_system()
    config = FONT_CONFIG.get(system, FONT_CONFIG["Linux"])
    return config["sans_serif"]


def get_font_file() -> str:
    """
    获取适合当前操作系统的字体文件名

    Returns:
        str: 字体文件名
    """
    system = get_system()
    config = FONT_CONFIG.get(system, FONT_CONFIG["Linux"])
    return config["font_file"]


def setup_matplotlib_chinese_font():
    """
    配置 matplotlib 支持中文显示

    用法:
        import matplotlib.pyplot as plt
        from utils.fonts import setup_matplotlib_chinese_font
        setup_matplotlib_chinese_font()
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib

        fonts = get_chinese_fonts_list()

        # 设置默认字体
        matplotlib.rcParams["font.sans-serif"] = fonts
        matplotlib.rcParams["axes.unicode_minus"] = False  # 解决负号显示问题

        logger.info(f"Matplotlib font configured: {fonts[0]}")
        return fonts[0]
    except ImportError:
        logger.warning("matplotlib not installed, skipping font setup")
        return None


def get_available_chinese_font() -> Optional[str]:
    """
    检测系统中可用的中文字体

    Returns:
        Optional[str]: 第一个可用的中文字体名称，如果没有则返回 None
    """
    try:
        import matplotlib.font_manager as fm

        # 获取系统所有字体
        available_fonts = set([f.name for f in fm.fontManager.ttflist])

        # 按优先级检测
        fonts = get_chinese_fonts_list()
        for font in fonts:
            if font in available_fonts:
                logger.info(f"Found available Chinese font: {font}")
                return font

        # 尝试模糊匹配
        for font in fonts:
            for available in available_fonts:
                if font.lower() in available.lower() or available.lower() in font.lower():
                    logger.info(f"Found similar font: {available} (requested: {font})")
                    return available

        logger.warning("No Chinese font found in system")
        return None
    except ImportError:
        # matplotlib 未安装，返回默认配置
        return get_chinese_font_family()


# 初始化时检测可用字体
_CACHED_FONT = None


def get_cached_chinese_font() -> str:
    """
    获取缓存的中文字体（首次调用时检测，后续使用缓存）

    Returns:
        str: 可用的中文字体名称
    """
    global _CACHED_FONT
    if _CACHED_FONT is None:
        _CACHED_FONT = get_available_chinese_font() or get_chinese_font_family()
    return _CACHED_FONT