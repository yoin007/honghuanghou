# -*- coding: utf-8 -*-
"""Dashboard SQLite base migration tests.

Batch24: verify _get_homework_db / _get_inout_db / _get_invigilation_db
migrated to sqlite_base.get_sqlite_connection.
"""

import os
import sqlite3
import tempfile
from contextlib import contextmanager

import pytest

from models.datas_api import dashboard


class TestDashboardSQLiteBaseMigration:
    """验证三个连接函数迁移到 sqlite_base。"""

    def test_get_homework_db_uses_sqlite_base(self, monkeypatch):
        """_get_homework_db 使用 sqlite_base，传入 homework.db 路径。"""
        captured = {}

        def fake_get_sqlite_connection(db_path, **kwargs):
            captured["db_path"] = db_path
            captured["kwargs"] = kwargs
            # 返回一个最小化 fake connection
            class FakeConn:
                row_factory = None
                def close(self):
                    pass
            return FakeConn()

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        conn = dashboard._get_homework_db()

        # 验证路径包含 homework.db
        assert "homework.db" in captured["db_path"]
        # 验证 row_factory 传入 sqlite3.Row
        assert captured["kwargs"].get("row_factory") == sqlite3.Row
        # 验证返回连接对象
        assert conn is not None

    def test_get_inout_db_uses_sqlite_base(self, monkeypatch):
        """_get_inout_db 使用 sqlite_base，传入 inout.db 路径。"""
        captured = {}

        def fake_get_sqlite_connection(db_path, **kwargs):
            captured["db_path"] = db_path
            captured["kwargs"] = kwargs
            class FakeConn:
                row_factory = None
                def close(self):
                    pass
            return FakeConn()

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        conn = dashboard._get_inout_db()

        # 验证路径包含 inout.db
        assert "inout.db" in captured["db_path"]
        # 验证 row_factory 传入 sqlite3.Row
        assert captured["kwargs"].get("row_factory") == sqlite3.Row
        assert conn is not None

    def test_get_invigilation_db_uses_sqlite_base(self, monkeypatch):
        """_get_invigilation_db 使用 sqlite_base，传入 invigilation.db 路径。"""
        captured = {}

        def fake_get_sqlite_connection(db_path, **kwargs):
            captured["db_path"] = db_path
            captured["kwargs"] = kwargs
            class FakeConn:
                row_factory = None
                def close(self):
                    pass
            return FakeConn()

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        conn = dashboard._get_invigilation_db()

        # 验证路径包含 invigilation.db
        assert "invigilation.db" in captured["db_path"]
        # 验证 row_factory 传入 sqlite3.Row
        assert captured["kwargs"].get("row_factory") == sqlite3.Row
        assert conn is not None

    def test_connections_preserve_row_factory(self, monkeypatch, tmp_path):
        """三个连接都保留 sqlite3.Row row_factory。"""
        # 创建临时数据库文件
        homework_db = tmp_path / "homework.db"
        inout_db = tmp_path / "inout.db"
        invigilation_db = tmp_path / "invigilation.db"

        for db_path in [homework_db, inout_db, invigilation_db]:
            conn = sqlite3.connect(str(db_path))
            conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'test')")
            conn.commit()
            conn.close()

        # Monkeypatch 数据库路径
        original_join = os.path.join

        def fake_join(base_dir, *parts):
            # 拦截 databases 路径拼接
            if "databases" in parts:
                db_name = parts[-1]
                if db_name == "homework.db":
                    return str(homework_db)
                elif db_name == "inout.db":
                    return str(inout_db)
                elif db_name == "invigilation.db":
                    return str(invigilation_db)
            return original_join(base_dir, *parts)

        monkeypatch.setattr(os.path, "join", fake_join)

        # 测试三个连接的 row_factory
        for get_db_func in [dashboard._get_homework_db, dashboard._get_inout_db, dashboard._get_invigilation_db]:
            conn = get_db_func()
            # sqlite_base 已设置 row_factory，连接对象应有此属性
            assert hasattr(conn, "row_factory")
            # 实际查询验证 Row 返回字典式访问
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM test")
            row = cursor.fetchone()
            # row_factory 设置后，row 应支持 dict-style 访问
            assert row["name"] == "test" or row[1] == "test"  # 兼容两种访问方式
            conn.close()

    def test_connection_wrapper_closes_after_with(self, monkeypatch):
        """三个连接可作为上下文管理器使用并在退出时 close。"""
        closed = []

        class FakeConn:
            row_factory = sqlite3.Row

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def close(self):
                closed.append(True)

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            lambda db_path, **kwargs: FakeConn()
        )

        for get_db_func in [dashboard._get_homework_db, dashboard._get_inout_db, dashboard._get_invigilation_db]:
            with get_db_func() as conn:
                assert conn.row_factory == sqlite3.Row

        assert len(closed) == 3

    def test_connection_wrapper_closes_on_exception(self, monkeypatch):
        """异常路径下连接也能关闭。"""
        closed = []

        class FakeConn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def close(self):
                closed.append(True)

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            lambda db_path, **kwargs: FakeConn()
        )

        with pytest.raises(ValueError):
            with dashboard._get_homework_db():
                raise ValueError("test exception")

        assert closed == [True]

    def test_connection_wrapper_direct_close_delegates(self, monkeypatch):
        """直接调用 close 仍会关闭底层连接。"""
        closed = []

        class FakeConn:
            def close(self):
                closed.append(True)

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            lambda db_path, **kwargs: FakeConn()
        )

        conn = dashboard._get_homework_db()
        conn.close()

        assert closed == [True]


class TestDashboardRouteContractPreserved:
    """验证 dashboard route contract 不变。"""

    # 这些测试在 test_dashboard_contract.py 中已有覆盖
    # 这里只验证迁移后 contract 未破坏
    def test_get_homework_db_returns_connection(self, monkeypatch):
        """迁移后仍返回连接对象。"""
        def fake_get_sqlite_connection(db_path, **kwargs):
            class FakeConn:
                row_factory = kwargs.get("row_factory")
                def close(self):
                    pass
            return FakeConn()

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        conn = dashboard._get_homework_db()
        assert conn is not None
        assert hasattr(conn, "close")

    def test_get_inout_db_returns_connection(self, monkeypatch):
        """迁移后仍返回连接对象。"""
        def fake_get_sqlite_connection(db_path, **kwargs):
            class FakeConn:
                row_factory = kwargs.get("row_factory")
                def close(self):
                    pass
            return FakeConn()

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        conn = dashboard._get_inout_db()
        assert conn is not None
        assert hasattr(conn, "close")

    def test_get_invigilation_db_returns_connection(self, monkeypatch):
        """迁移后仍返回连接对象。"""
        def fake_get_sqlite_connection(db_path, **kwargs):
            class FakeConn:
                row_factory = kwargs.get("row_factory")
                def close(self):
                    pass
            return FakeConn()

        monkeypatch.setattr(
            "models.datas_api.repositories.sqlite_base.get_sqlite_connection",
            fake_get_sqlite_connection
        )

        conn = dashboard._get_invigilation_db()
        assert conn is not None
        assert hasattr(conn, "close")
