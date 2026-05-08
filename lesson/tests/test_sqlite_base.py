"""
SQLite 基础模块测试

Batch 5 第三阶段验收：连接工具功能正确
"""
import pytest
import sqlite3
import os
from models.datas_api.repositories.sqlite_base import (
    get_sqlite_connection,
    ensure_parent_dir,
    SQLiteConnectionManager
)


class TestSQLiteBase:
    """SQLite 连接基础功能测试"""

    def test_ensure_parent_dir_creates_directory(self, tmp_path):
        """父目录不存在时自动创建"""
        # 创建嵌套路径
        nested_path = str(tmp_path / "subdir" / "deep" / "db.sqlite")

        # 父目录不存在
        assert not os.path.exists(os.path.dirname(nested_path))

        # ensure_parent_dir 应创建
        result = ensure_parent_dir(nested_path)
        assert result == nested_path
        assert os.path.exists(os.path.dirname(nested_path))

    def test_ensure_parent_dir_existing_directory(self, tmp_path):
        """父目录已存在时不报错"""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        path = str(existing_dir / "db.sqlite")

        result = ensure_parent_dir(path)
        assert result == path
        assert os.path.exists(existing_dir)

    def test_get_sqlite_connection_creates_db(self, tmp_path):
        """连接自动创建数据库文件"""
        db_path = str(tmp_path / "test.db")

        # 文件不存在
        assert not os.path.exists(db_path)

        # 连接后应创建
        conn = get_sqlite_connection(db_path)
        assert os.path.exists(db_path)

        # 能执行基本操作
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")
        result = conn.execute("SELECT name FROM test").fetchone()
        assert result[0] == "hello"

        conn.close()

    def test_get_sqlite_connection_row_factory(self, tmp_path):
        """row_factory 参数生效"""
        db_path = str(tmp_path / "test.db")

        conn = get_sqlite_connection(db_path, row_factory=sqlite3.Row)

        conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO test VALUES (1, 'hello')")

        row = conn.execute("SELECT * FROM test").fetchone()
        # 使用 Row 工厂后可按列名访问
        assert row["name"] == "hello"

        conn.close()

    def test_get_sqlite_connection_timeout(self, tmp_path):
        """timeout 参数生效"""
        db_path = str(tmp_path / "test.db")

        # 使用自定义 timeout
        conn = get_sqlite_connection(db_path, timeout=5.0)

        # timeout 被设置（无法直接读取，但不报错即成功）
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()

    def test_get_sqlite_connection_wal_mode(self, tmp_path):
        """WAL 模式启用"""
        db_path = str(tmp_path / "test.db")

        conn = get_sqlite_connection(db_path, wal_mode=True)

        # 检查 journal_mode
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0].lower() == "wal"

        conn.close()

    def test_connection_manager_context(self, tmp_path):
        """SQLiteConnectionManager 上下文管理"""
        db_path = str(tmp_path / "test.db")

        with SQLiteConnectionManager(db_path) as conn:
            conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'data')")

        # 退出后自动提交并关闭
        # 再次连接验证数据存在
        conn2 = sqlite3.connect(db_path)
        result = conn2.execute("SELECT value FROM test").fetchone()
        assert result[0] == "data"
        conn2.close()

    def test_connection_manager_rollback_on_exception(self, tmp_path):
        """异常时自动回滚"""
        db_path = str(tmp_path / "test.db")

        # 先插入一条数据
        with SQLiteConnectionManager(db_path) as conn:
            conn.execute("CREATE TABLE test (id INTEGER, value TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'committed')")

        # 再尝试插入但抛异常
        try:
            with SQLiteConnectionManager(db_path) as conn:
                conn.execute("INSERT INTO test VALUES (2, 'should_rollback')")
                raise ValueError("模拟异常")
        except ValueError:
            pass

        # 验证第二条数据未提交
        conn2 = sqlite3.connect(db_path)
        count = conn2.execute("SELECT COUNT(*) FROM test").fetchone()[0]
        assert count == 1  # 只有第一条
        conn2.close()

    def test_connection_manager_with_row_factory(self, tmp_path):
        """ConnectionManager 支持 row_factory"""
        db_path = str(tmp_path / "test.db")

        with SQLiteConnectionManager(db_path, row_factory=sqlite3.Row) as conn:
            conn.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            conn.execute("INSERT INTO test VALUES (1, 'test_name')")

            row = conn.execute("SELECT * FROM test").fetchone()
            assert row["name"] == "test_name"