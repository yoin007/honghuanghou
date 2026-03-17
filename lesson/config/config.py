# _*_ coding: utf-8 _*_
# @Time: 2024/09/23 11:31
# @Author: Tech_T

import yaml
import os
import platform


class Config:
    def __init__(self):
        self.root_path = os.path.dirname(__file__)
        self.config_path = self.root_path + "/config.yaml"

    def get_config(self, key, config_file: str = ""):
        if config_file == "":
            config_file = self.config_path
        else:
            config_file = os.path.join(self.root_path, config_file)
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config[key]

    def get_cross_platform_path(self, key, config_file: str = "") -> str:
        """
        获取跨平台路径配置

        配置格式示例 (YAML):
            lesson_dir:
                Darwin: /Users/yoin/bdsync/temp/lesson    # macOS
                Windows: D:/lesson                         # Windows
                Linux: /home/user/lesson                   # Linux

        Args:
            key: 配置键名
            config_file: 配置文件名

        Returns:
            str: 当前操作系统对应的路径
        """
        config = self.get_config_all(config_file)
        if key not in config:
            return None

        value = config[key]

        # 如果是字典格式，按系统选择
        if isinstance(value, dict):
            system = platform.system()
            if system in value:
                path = value[system]
            elif "default" in value:
                path = value["default"]
            else:
                # 返回第一个可用值
                for sys_key in ["Darwin", "Windows", "Linux"]:
                    if sys_key in value:
                        path = value[sys_key]
                        break
                else:
                    return None
            return os.path.normpath(path) if path else None

        # 普通字符串，直接返回
        return os.path.normpath(value) if value else None

    def get_config_all(self, config_file: str = ""):
        if config_file == "":
            config_file = self.config_path
        else:
            config_file = os.path.join(self.root_path, config_file)
        with open(config_file, "r", encoding="utf-8") as f:
            config_all = yaml.safe_load(f)
        return config_all

    def modify_config(self, key, value, config_file: str = ""):
        config_all = self.get_config_all(config_file)
        try:
            config_all[key] = value
            if config_file == "":
                config_file = self.config_path
            else:
                config_file = os.path.join(self.root_path, config_file)
            with open(config_file, "w", encoding="utf-8") as f:
                yaml.dump(config_all, f, allow_unicode=True)
                return True
        except:
            return False