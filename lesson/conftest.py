# -*- coding: utf-8 -*-
"""
Pytest 配置文件

在测试运行前设置必要的环境
"""

import sys
import os
from unittest.mock import patch, MagicMock

# 添加 lesson 目录到 Python 路径
lesson_dir = os.path.dirname(os.path.abspath(__file__))
if lesson_dir not in sys.path:
    sys.path.insert(0, lesson_dir)

# 在导入任何应用代码之前，先 mock 数据库连接
# 这是为了避免在测试环境中连接真实数据库

def pytest_configure(config):
    """pytest 配置钩子，在测试收集之前执行"""
    # 设置工作目录为 lesson 目录，确保相对路径正确
    os.chdir(lesson_dir)