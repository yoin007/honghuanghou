# -*- coding: utf-8 -*-
"""uac-bak.py 运行时隔离契约测试。

Batch78: 验证 uac-bak.py 不属于运行时导入链，证明隔离有效。
"""

import pytest
import sys
from pathlib import Path


class TestUacBakRuntimeIsolation:
    """验证 uac-bak.py 不在运行时导入链中"""

    def test_models_init_does_not_import_uac_bak(self):
        """models/__init__.py 不导入 uac-bak 模块"""
        import models

        # 检查 models 包的导入
        module_names = set(sys.modules.keys())
        uac_modules = {name for name in module_names if "uac" in name and "network" in name}

        # 允许的 uac 模块：只有 uac.py（不含 uac_bak）
        forbidden = {"models.network.uac-bak", "models.network.uac_bak"}

        for forbidden_name in forbidden:
            assert forbidden_name not in uac_modules, f"{forbidden_name} 被导入到运行时"

        # uac.py 应该可导入
        assert "models.network.uac" in module_names

    def test_uac_module_imports_successfully(self):
        """正式 uac 模块可正常导入"""
        from models.network import uac

        # 验证关键异步函数存在
        assert hasattr(uac, "query_uac_async")
        assert hasattr(uac, "del_pc_user_async")
        assert hasattr(uac, "add_pc_user_async")
        assert hasattr(uac, "get_one_ip_async")
        assert hasattr(uac, "black_ip_async")
        assert hasattr(uac, "del_black_ip_async")

        # 验证函数可调用
        assert callable(uac.query_uac_async)
        assert callable(uac.del_pc_user_async)

    def test_uac_bak_module_not_imported_implicitly(self):
        """uac-bak.py 不会被隐式导入"""
        import importlib

        # 常规模块导入不会自动把磁盘文件 uac-bak.py 映射成 uac_bak。
        with pytest.raises(ImportError):
            importlib.import_module("models.network.uac_bak")

    def test_uac_has_no_selenium_dependency(self):
        """正式 uac.py 不依赖 Selenium"""
        from models.network import uac
        import inspect

        source = inspect.getsource(uac)

        # uac.py 不应包含 Selenium 导入
        assert "from selenium" not in source
        assert "import selenium" not in source
        assert "webdriver" not in source
        assert "init_driver" not in source

    def test_uac_has_ssl_verify_false_for_testing(self):
        """uac.py 禁用 SSL 验证（仅用于开发/测试环境）"""
        from models.network import uac
        import inspect

        source = inspect.getsource(uac)

        # uac.py 禁用 SSL 验证（已确认，用于内网 UAC 设备）
        assert "verify=False" in source

        # 但不应包含 debugger 禁用逻辑
        assert "window.debugger" not in source
        assert "AutomationControlled" not in source

    def test_uac_bak_file_exists_but_is_archived(self):
        """uac-bak.py 文件存在，但处于归档状态"""
        bak_path = Path(__file__).resolve().parents[1] / "models" / "network" / "uac-bak.py"
        assert bak_path.exists(), "uac-bak.py 文件存在"

        # 读取文件，确认包含 Selenium 和调试禁用逻辑
        content = bak_path.read_text(encoding="utf-8")

        # uac-bak.py 包含高风险逻辑（Selenium + 禁用调试器）
        assert "from selenium" in content
        assert "window.debugger" in content
        assert "--disable-blink-features=AutomationControlled" in content
