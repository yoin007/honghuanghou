# -*- coding: utf-8 -*-
"""
filegather_db.py / application.py sqlite_base 迁移回归测试

Batch 13: 验证单连接小模块使用 sqlite_base 后行为不变
"""
import pytest
import sqlite3
import os
import tempfile
import shutil
from datetime import UTC, datetime, timedelta


class TestFileGatherSqliteBase:
    """FileGatherDB sqlite_base 迁移测试"""

    def test_filegather_connection_uses_sqlite_base(self, monkeypatch):
        """FileGatherDB._get_connection 使用 sqlite_base 连接入口。"""
        from models import filegather_db as fg_module

        calls = []

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def execute(self, sql, params=None):
                return object()

            def commit(self):
                pass

            def close(self):
                self.closed = True

            @property
            def row_factory(self):
                return None

            @row_factory.setter
            def row_factory(self, value):
                pass

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            calls.append((db_path, kwargs))
            return fake_connection

        monkeypatch.setattr(
            fg_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        # 创建临时数据库路径
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "filegather.db")

        try:
            fg = fg_module.FileGatherDB(db_path=db_path)
            # _get_connection 在 _init_db 中被调用
            # 验证 sqlite_base 被调用
            assert len(calls) >= 1
            assert calls[0][0] == db_path
            assert "row_factory" in calls[0][1]
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_filegather_db_auto_created(self):
        """FileGatherDB 数据库在初始化时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "filegather.db")

            from models.filegather_db import FileGatherDB

            fg = FileGatherDB(db_path=db_path)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_filegather_insert_and_query(self):
        """FileGatherDB 插入记录后能查询"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "filegather.db")

            from models.filegather_db import FileGatherDB

            fg = FileGatherDB(db_path=db_path)

            # 插入记录（使用临时文件）
            test_file_path = os.path.join(tmp_dir, "test.txt")
            with open(test_file_path, "wb") as f:
                f.write(b"test content")

            file_id = fg.insert_file(
                username="test_user",
                original_name="test.txt",
                stored_path=test_file_path,
                content_type="text/plain",
                copies=1,
                use_date="2025-01-15",
                month="202501",
                note="test note",
            )

            assert file_id > 0

            # 验证查询
            files = fg.query_files(username="test_user")
            assert len(files) >= 1
            assert files[0]["username"] == "test_user"
            assert files[0]["original_name"] == "test.txt"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_filegather_timestamps_are_timezone_aware(self):
        """FileGatherDB 使用 timezone-aware UTC 时间写入记录。"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "filegather.db")

            from models.filegather_db import FileGatherDB

            fg = FileGatherDB(db_path=db_path)

            test_file_path = os.path.join(tmp_dir, "test.txt")
            with open(test_file_path, "wb") as f:
                f.write(b"test content")

            file_id = fg.insert_file(
                username="test_user",
                original_name="test.txt",
                stored_path=test_file_path,
                content_type="text/plain",
                copies=1,
                use_date="2025-01-15",
                month="202501",
                note="test note",
            )

            row = fg.get_file_by_id(file_id)
            assert row["uploaded_at"].endswith("+00:00")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_filegather_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from models.filegather_db import _get_sqlite_connection

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

    def test_filegather_row_factory(self):
        """FileGatherDB row_factory 设置正确"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "filegather.db")

            from models.filegather_db import FileGatherDB

            fg = FileGatherDB(db_path=db_path)

            # 插入记录
            test_file_path = os.path.join(tmp_dir, "test.txt")
            with open(test_file_path, "wb") as f:
                f.write(b"test content")

            fg.insert_file(
                username="test_user",
                original_name="test.txt",
                stored_path=test_file_path,
                content_type="text/plain",
                copies=1,
                use_date="2025-01-15",
                month="202501",
                note="test note",
            )

            # 验证 row_factory 返回 dict-like 对象
            files = fg.query_files(username="test_user")
            assert len(files) >= 1
            # files[0] 应该是 dict
            assert isinstance(files[0], dict)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_filegather_statistics_overdue_handles_iso_utc_timestamps(self):
        """文件统计逾期计算兼容 insert_file 写入的 ISO UTC 时间。"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "filegather.db")

            from models.filegather_db import FileGatherDB

            fg = FileGatherDB(db_path=db_path)
            old_time = (datetime.now(UTC) - timedelta(days=5)).isoformat()
            recent_time = (datetime.now(UTC) - timedelta(days=1)).isoformat()

            with fg._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO files
                    (username, original_name, stored_path, content_type, status, uploaded_at, copies, use_date, month, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("old_user", "old.pdf", "/tmp/old.pdf", "application/pdf", "否", old_time, 1, "2026-05-01", "202605", None),
                )
                conn.execute(
                    """
                    INSERT INTO files
                    (username, original_name, stored_path, content_type, status, uploaded_at, copies, use_date, month, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("recent_user", "recent.pdf", "/tmp/recent.pdf", "application/pdf", "否", recent_time, 1, "2026-05-01", "202605", None),
                )
                conn.commit()

            stats = fg.get_statistics("202605")

            assert stats["overdue_pending_count"] == 1
            overdue = [item for item in stats["pending_file_list"] if item["original_name"] == "old.pdf"][0]
            recent = [item for item in stats["pending_file_list"] if item["original_name"] == "recent.pdf"][0]
            assert overdue["overdue_days"] >= 1
            assert recent["overdue_days"] == 0
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_filegather_statistics_overdue_count_scans_all_pending_files(self):
        """逾期文件数应按全部待处理文件统计，而不是只统计最近 20 条展示列表。"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "filegather.db")

            from models.filegather_db import FileGatherDB

            fg = FileGatherDB(db_path=db_path)
            old_time = (datetime.now(UTC) - timedelta(days=5)).isoformat()
            recent_time = (datetime.now(UTC) - timedelta(days=1)).isoformat()

            with fg._get_connection() as conn:
                for idx in range(25):
                    conn.execute(
                        """
                        INSERT INTO files
                        (username, original_name, stored_path, content_type, status, uploaded_at, copies, use_date, month, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "old_user",
                            f"old-{idx}.pdf",
                            f"/tmp/old-{idx}.pdf",
                            "application/pdf",
                            "否",
                            old_time,
                            1,
                            "2026-05-01",
                            "202605",
                            None,
                        ),
                    )
                for idx in range(3):
                    conn.execute(
                        """
                        INSERT INTO files
                        (username, original_name, stored_path, content_type, status, uploaded_at, copies, use_date, month, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "recent_user",
                            f"recent-{idx}.pdf",
                            f"/tmp/recent-{idx}.pdf",
                            "application/pdf",
                            "否",
                            recent_time,
                            1,
                            "2026-05-01",
                            "202605",
                            None,
                        ),
                    )
                conn.commit()

            stats = fg.get_statistics("202605")

            assert stats["pending_files"] == 28
            assert stats["overdue_pending_count"] == 25
            assert len(stats["pending_file_list"]) == 20
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestApplicationSqliteBase:
    """Application sqlite_base 迁移测试"""

    def test_application_enter_uses_sqlite_base_and_exit_closes(self, monkeypatch):
        """Application.__enter__ 使用 sqlite_base 连接入口，__exit__ 关闭连接。"""
        from models.application import application as app_module

        calls = []

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def cursor(self):
                return object()

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            calls.append((db_path, kwargs))
            return fake_connection

        monkeypatch.setattr(
            app_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        app = app_module.Application(db_path="/tmp/application-test.db")
        app.__enter__()
        app.__exit__(None, None, None)

        assert calls == [("/tmp/application-test.db", {})]
        assert fake_connection.closed is True

    def test_application_db_auto_created_on_enter(self):
        """Application 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "application.db")

            from models.application.application import Application

            app = Application(db_path=db_path)
            app.__enter__()
            app.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_application_cursor_behavior(self):
        """Application cursor 行为正常"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "application.db")

            from models.application.application import Application

            app = Application(db_path=db_path)
            app.__enter__()

            # 创建测试表
            app.__cursor__.execute("CREATE TABLE test (id INTEGER, name TEXT)")
            app.__cursor__.execute("INSERT INTO test VALUES (1, 'test')")
            app.__conn__.commit()

            app.__cursor__.execute("SELECT * FROM test")
            result = app.__cursor__.fetchone()

            app.__exit__(None, None, None)

            assert result == (1, "test")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_application_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from models.application.application import _get_sqlite_connection

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
