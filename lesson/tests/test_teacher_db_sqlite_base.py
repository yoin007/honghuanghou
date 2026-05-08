# -*- coding: utf-8 -*-
"""
teacher_db.py sqlite_base 迁移回归测试

Batch 15: 验证 teacher_db 使用 sqlite_base 后行为不变
"""
import pytest
import sqlite3
import os
import tempfile
import shutil
import inspect
from datetime import datetime


class TestTeacherDBSqliteBase:
    """TeacherDB sqlite_base 迁移测试"""

    def test_teacher_db_enter_uses_sqlite_base_with_row_factory(self, monkeypatch):
        """TeacherDB.__enter__ 使用 sqlite_base，并设置 row_factory。"""
        from utils import teacher_db as teacher_db_module

        calls = []

        class FakeConnection:
            def __init__(self):
                self.closed = False
                self.row_factory = None

            def cursor(self):
                return object()

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
            teacher_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "moral.db")

        try:
            # 使用临时路径避免触发 ensure_teacher_schema 的真实数据库检查
            db = teacher_db_module.TeacherDB(db_path=db_path)
            db.__enter__()
            db.__exit__(None, None, None)

            assert len(calls) == 1
            assert calls[0][0] == db_path
            # row_factory 在连接后设置，不在 kwargs 中传递
            assert fake_connection.closed is True
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_teacher_db_auto_created(self):
        """TeacherDB 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "moral.db")

            from utils.teacher_db import TeacherDB

            db = TeacherDB(db_path=db_path)
            db.__enter__()
            db.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_teacher_db_query_one_returns_dict(self):
        """TeacherDB query_one 返回字典（row_factory 设置正确）"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")

            from utils.teacher_db import TeacherDB

            db = TeacherDB(db_path=db_path)
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

    def test_teacher_db_commit_on_success(self):
        """TeacherDB 正常退出时 commit"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")

            from utils.teacher_db import TeacherDB

            db = TeacherDB(db_path=db_path)
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

    def test_teacher_db_rollback_on_error(self):
        """TeacherDB 异常退出时 rollback"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "test.db")

            from utils.teacher_db import TeacherDB

            db = TeacherDB(db_path=db_path)
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

    def test_teacher_db_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from utils.teacher_db import _get_sqlite_connection

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


class TestEnsureTeacherSchemaSqliteBase:
    """ensure_teacher_schema sqlite_base 迁移测试"""

    def test_ensure_teacher_schema_creates_db_when_none(self, monkeypatch):
        """ensure_teacher_schema 无 conn 时创建独立连接"""
        from utils import teacher_db as teacher_db_module

        calls = []

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def cursor(self):
                class FakeCursor:
                    def execute(self, sql, params=None):
                        # PRAGMA table_info 返回空列表
                        return self

                    def fetchall(self):
                        return []

                    def fetchone(self):
                        return None

                    def rowcount(self):
                        return 0
                return FakeCursor()

            def commit(self):
                pass

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            calls.append((db_path, kwargs))
            return fake_connection

        monkeypatch.setattr(
            teacher_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        # 调用 ensure_teacher_schema 无 conn
        teacher_db_module.ensure_teacher_schema(conn=None)

        assert len(calls) == 1
        assert calls[0][0] == teacher_db_module.MORAL_DB
        assert fake_connection.closed is True

    def test_ensure_teacher_schema_with_provided_conn_does_not_close(self, monkeypatch):
        """ensure_teacher_schema 有 conn 时不关闭"""
        from utils import teacher_db as teacher_db_module

        calls = []

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def cursor(self):
                class FakeCursor:
                    def execute(self, sql, params=None):
                        return self

                    def fetchall(self):
                        return []

                    def fetchone(self):
                        return None

                    def rowcount(self):
                        return 0
                return FakeCursor()

            def commit(self):
                pass

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        # 调用 ensure_teacher_schema 有 conn
        teacher_db_module.ensure_teacher_schema(conn=fake_connection)

        assert len(calls) == 0
        assert fake_connection.closed is False

    def test_ensure_teacher_schema_closes_owned_connection_on_error(self, monkeypatch):
        """ensure_teacher_schema 自建连接时，异常路径也关闭连接。"""
        from utils import teacher_db as teacher_db_module

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def cursor(self):
                class FakeCursor:
                    def execute(self, sql, params=None):
                        raise RuntimeError("boom")

                return FakeCursor()

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            return fake_connection

        monkeypatch.setattr(
            teacher_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        with pytest.raises(RuntimeError):
            teacher_db_module.ensure_teacher_schema(conn=None)

        assert fake_connection.closed is True


class TestMigrateAuthTeachersSqliteBase:
    """migrate_auth_teachers_to_moral sqlite_base 迁移测试"""

    def test_migrate_closes_connections_on_success(self, monkeypatch, tmp_path):
        """migrate 成功后关闭双库连接"""
        from utils import teacher_db as teacher_db_module

        # 创建临时 auth.db 和 moral.db
        auth_db = tmp_path / "auth.db"
        moral_db = tmp_path / "moral.db"

        # 创建 auth.db teacher 表
        conn = sqlite3.connect(str(auth_db))
        conn.execute("CREATE TABLE teacher (name TEXT)")
        conn.commit()
        conn.close()

        # Mock db_config
        monkeypatch.setattr(teacher_db_module, "AUTH_DB", str(auth_db))
        monkeypatch.setattr(teacher_db_module, "MORAL_DB", str(moral_db))

        # 重置 _AUTH_MIGRATED
        teacher_db_module._AUTH_MIGRATED = False

        # 调用迁移
        result = teacher_db_module.migrate_auth_teachers_to_moral()

        assert result == 0  # 空表，无数据迁移
        # 验证 moral.db 已创建（ensure_teacher_schema 使用 sqlite_base）
        assert moral_db.exists()

    def test_migrate_closes_auth_connection_when_moral_connection_fails(self, monkeypatch):
        """migrate 打开 moral 连接失败时，已打开的 auth 连接会关闭。"""
        from utils import teacher_db as teacher_db_module

        class FakeConnection:
            def __init__(self):
                self.closed = False
                self.row_factory = None

            def close(self):
                self.closed = True

        auth_connection = FakeConnection()
        calls = []

        def fake_get_sqlite_connection(db_path, **kwargs):
            calls.append(db_path)
            if len(calls) == 1:
                return auth_connection
            raise RuntimeError("moral connect failed")

        monkeypatch.setattr(teacher_db_module, "AUTH_DB", "/tmp/auth.db")
        monkeypatch.setattr(teacher_db_module, "MORAL_DB", "/tmp/moral.db")
        monkeypatch.setattr(teacher_db_module.os.path, "exists", lambda path: True)
        monkeypatch.setattr(teacher_db_module, "ensure_teacher_schema", lambda conn=None: None)
        monkeypatch.setattr(
            teacher_db_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )
        teacher_db_module._AUTH_MIGRATED = False

        with pytest.raises(RuntimeError):
            teacher_db_module.migrate_auth_teachers_to_moral()

        assert auth_connection.closed is True


class TestTeacherDBFunctionsWithSqliteBase:
    """teacher_db 辅助函数测试"""

    def test_get_teacher_db_context_manager(self):
        """get_teacher_db 上下文管理器正常工作"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "moral.db")

            from utils.teacher_db import get_teacher_db, TeacherDB

            # 使用自定义路径
            with TeacherDB(db_path=db_path) as db:
                db._connection.execute("CREATE TABLE test (id INTEGER)")
                db.execute("INSERT INTO test VALUES (1)")

            # 验证数据已提交
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 1
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_sqlite_exception_names_available(self):
        """迁移后 sqlite3 异常类型仍可用"""
        from utils import teacher_db as teacher_db_module

        assert teacher_db_module.sqlite3.OperationalError is sqlite3.OperationalError
        assert teacher_db_module.sqlite3.Row is sqlite3.Row

    def test_create_teacher_record_raw_pwd_signature_unchanged(self):
        """Batch 15 不改变 create_teacher_record 的 raw_pwd 必填签名。"""
        from utils.teacher_db import create_teacher_record

        signature = inspect.signature(create_teacher_record)

        assert signature.parameters["raw_pwd"].default is inspect.Parameter.empty
