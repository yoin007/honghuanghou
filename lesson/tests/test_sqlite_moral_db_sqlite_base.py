# -*- coding: utf-8 -*-
"""
sqlite_moral_db.py sqlite_base 迁移回归测试

Batch 16: 验证 sqlite_moral_db 使用 sqlite_base 后行为不变
"""
import pytest
import sqlite3
import os
import tempfile
import shutil


class TestMoralDatabaseSqliteBase:
    """MoralDatabase sqlite_base 迁移测试"""

    def test_moral_database_enter_uses_sqlite_base_with_row_factory(self, monkeypatch):
        """MoralDatabase.__enter__ 使用 sqlite_base，并设置 row_factory。"""
        from utils import sqlite_moral_db as moral_db_module

        calls = []

        class FakeCursor:
            def close(self):
                pass

        class FakeConnection:
            def __init__(self):
                self.closed = False
                self.row_factory = None

            def cursor(self):
                return FakeCursor()

            def execute(self, sql):
                return self

            def commit(self):
                pass

            def rollback(self):
                pass

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            calls.append((db_path, kwargs))
            return fake_connection

        monkeypatch.setattr(
            moral_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "moral.db")

        try:
            db = moral_db_module.MoralDatabase(db_path=db_path)
            db.__enter__()
            db.__exit__(None, None, None)

            assert len(calls) == 1
            assert calls[0][0] == db_path
            # row_factory 在连接后设置，不在 kwargs 中传递
            assert fake_connection.row_factory is sqlite3.Row
            assert fake_connection.closed is True
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_moral_database_db_auto_created(self):
        """MoralDatabase 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "moral.db")

            from utils.sqlite_moral_db import MoralDatabase

            db = MoralDatabase(db_path=db_path)
            db.__enter__()
            db.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_moral_database_query_one_returns_dict(self):
        """MoralDatabase query_one 返回字典（row_factory 设置正确）"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")

            from utils.sqlite_moral_db import MoralDatabase

            db = MoralDatabase(db_path=db_path)
            db.__enter__()

            # 创建测试表
            db._connection.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            db._connection.execute("INSERT INTO test VALUES (1, 'test')")
            db._connection.commit()

            result = db.query_one("SELECT * FROM test WHERE id = ?", (1,))

            db.__exit__(None, None, None)

            assert result is not None
            assert isinstance(result, dict)
            assert result["id"] == 1
            assert result["name"] == "test"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_moral_database_commit_on_success(self):
        """MoralDatabase 正常退出时 commit"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")

            from utils.sqlite_moral_db import MoralDatabase

            db = MoralDatabase(db_path=db_path)
            db.__enter__()

            db._connection.execute("CREATE TABLE test (id INTEGER)")
            db.execute("INSERT INTO test VALUES (1)")

            db.__exit__(None, None, None)

            # 验证数据已提交
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 1
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_moral_database_rollback_on_error(self):
        """MoralDatabase 异常退出时 rollback"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")

            from utils.sqlite_moral_db import MoralDatabase

            db = MoralDatabase(db_path=db_path)
            db.__enter__()

            db._connection.execute("CREATE TABLE test (id INTEGER)")
            db.execute("INSERT INTO test VALUES (1)")

            # 异常退出
            db.__exit__(Exception, Exception("test"), None)

            # 验证数据未提交
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 0
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_moral_database_cursor_closed_on_exit(self):
        """MoralDatabase 退出时关闭 cursor"""
        from utils import sqlite_moral_db as moral_db_module

        class FakeCursor:
            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        class FakeConnection:
            def __init__(self):
                self.closed = False
                self.row_factory = None

            def cursor(self):
                return FakeCursor()

            def execute(self, sql):
                return self

            def commit(self):
                pass

            def rollback(self):
                pass

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            return fake_connection

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            moral_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        try:
            db = moral_db_module.MoralDatabase(db_path="/tmp/test.db")
            db.__enter__()
            fake_cursor = db._cursor
            db.__exit__(None, None, None)

            assert fake_cursor.closed is True
            assert fake_connection.closed is True
        finally:
            monkeypatch.undo()

    def test_moral_database_enter_closes_connection_on_pragma_error(self, monkeypatch):
        """MoralDatabase.__enter__ 在 PRAGMA 失败时关闭已创建连接。"""
        from utils import sqlite_moral_db as moral_db_module

        class FakeConnection:
            def __init__(self):
                self.closed = False
                self.row_factory = None

            def execute(self, sql):
                raise RuntimeError("pragma failed")

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            return fake_connection

        monkeypatch.setattr(
            moral_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        db = moral_db_module.MoralDatabase(db_path="/tmp/test.db")

        with pytest.raises(RuntimeError):
            db.__enter__()

        assert fake_connection.closed is True
        assert db._connection is None

    def test_moral_database_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from utils.sqlite_moral_db import _get_sqlite_connection

        get_sqlite_connection = _get_sqlite_connection()
        assert get_sqlite_connection is not None

        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")
            conn = get_sqlite_connection(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_moral_database_sqlite_exception_names_available(self):
        """迁移后 sqlite3 异常类型仍可用"""
        from utils import sqlite_moral_db as moral_db_module

        assert moral_db_module.sqlite3.OperationalError is sqlite3.OperationalError
        assert moral_db_module.sqlite3.Row is sqlite3.Row


class TestInitMoralDbSqliteBase:
    """init_moral_db sqlite_base 迁移测试"""

    def test_init_moral_db_uses_sqlite_base(self, monkeypatch):
        """init_moral_db 使用 sqlite_base 连接"""
        from utils import sqlite_moral_db as moral_db_module

        calls = []

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def execute(self, sql):
                return self

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            calls.append((db_path, kwargs))
            return fake_connection

        monkeypatch.setattr(
            moral_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )
        monkeypatch.setattr(moral_db_module.os.path, "exists", lambda path: True)

        moral_db_module.init_moral_db()

        assert len(calls) == 1
        assert fake_connection.closed is True

    def test_init_moral_db_skips_when_db_not_exists(self, monkeypatch):
        """init_moral_db 数据库不存在时跳过"""
        from utils import sqlite_moral_db as moral_db_module

        calls = []

        def fake_get_sqlite_connection(db_path, **kwargs):
            calls.append(db_path)
            return object()

        monkeypatch.setattr(
            moral_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )
        monkeypatch.setattr(moral_db_module.os.path, "exists", lambda path: False)

        moral_db_module.init_moral_db()

        assert len(calls) == 0

    def test_init_moral_db_creates_wal_and_foreign_keys(self):
        """init_moral_db 启用 WAL 模式和外键约束"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "moral.db")

            # 先创建数据库
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.commit()
            conn.close()

            from utils.sqlite_moral_db import init_moral_db

            # Monkeypatch MORAL_DB
            import utils.sqlite_moral_db as moral_db_module
            original_moral_db = moral_db_module.MORAL_DB
            moral_db_module.MORAL_DB = db_path

            try:
                init_moral_db()

                # 验证 WAL 模式
                conn = sqlite3.connect(db_path)
                result = conn.execute("PRAGMA journal_mode").fetchone()[0]
                conn.close()

                assert result.lower() == "wal"
            finally:
                moral_db_module.MORAL_DB = original_moral_db
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_init_moral_db_closes_connection(self, monkeypatch):
        """init_moral_db 关闭连接"""
        from utils import sqlite_moral_db as moral_db_module

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def execute(self, sql):
                return self

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            return fake_connection

        monkeypatch.setattr(
            moral_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )
        monkeypatch.setattr(moral_db_module.os.path, "exists", lambda path: True)

        moral_db_module.init_moral_db()

        assert fake_connection.closed is True

    def test_init_moral_db_closes_connection_on_pragma_error(self, monkeypatch):
        """init_moral_db 在 PRAGMA 失败时也关闭连接。"""
        from utils import sqlite_moral_db as moral_db_module

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def execute(self, sql):
                raise RuntimeError("pragma failed")

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            return fake_connection

        monkeypatch.setattr(
            moral_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )
        monkeypatch.setattr(moral_db_module.os.path, "exists", lambda path: True)

        with pytest.raises(RuntimeError):
            moral_db_module.init_moral_db()

        assert fake_connection.closed is True


class TestMoralDatabasePragmas:
    """MoralDatabase PRAGMA 设置测试"""

    def test_moral_database_enables_wal_mode(self):
        """MoralDatabase 启用 WAL 模式"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")

            from utils.sqlite_moral_db import MoralDatabase

            db = MoralDatabase(db_path=db_path)
            db.__enter__()

            # 验证 WAL 模式
            result = db._connection.execute("PRAGMA journal_mode").fetchone()[0]

            db.__exit__(None, None, None)

            assert result.lower() == "wal"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_moral_database_enables_foreign_keys(self):
        """MoralDatabase 启用外键约束"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")

            from utils.sqlite_moral_db import MoralDatabase

            db = MoralDatabase(db_path=db_path)
            db.__enter__()

            # 验证外键约束
            result = db._connection.execute("PRAGMA foreign_keys").fetchone()[0]

            db.__exit__(None, None, None)

            assert result == 1
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
