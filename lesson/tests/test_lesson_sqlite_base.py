# -*- coding: utf-8 -*-
"""
homework.py / notes.py sqlite_base 迁移回归测试

Batch 12: 验证 lesson 小模块使用 sqlite_base 后行为不变
"""
import pytest
import sqlite3
import os
import tempfile
import shutil
from datetime import datetime


class TestHomeworkSqliteBase:
    """Homework sqlite_base 迁移测试"""

    def test_homework_enter_uses_sqlite_base_and_exit_closes(self, monkeypatch):
        """Homework.__enter__ 使用 sqlite_base 连接入口，__exit__ 关闭连接。"""
        from models.lesson import homework as homework_module

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
            homework_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        homework = homework_module.Homework()
        homework.__enter__(db_path="/tmp/homework-test.db")
        homework.__exit__(None, None, None)

        assert calls == [("/tmp/homework-test.db", {})]
        assert fake_connection.closed is True

    def test_homework_db_auto_created_on_enter(self):
        """Homework 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "homework.db")

            from models.lesson.homework import Homework

            hw = Homework()
            hw.__enter__(db_path=db_path)
            hw.__create_table__()
            hw.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_homework_add_and_get(self):
        """Homework 添加作业后能查询"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "homework.db")

            from models.lesson.homework import Homework

            hw = Homework()
            hw.__enter__(db_path=db_path)
            hw.__create_table__()

            # 添加作业
            hw_id = hw.add_homework(
                "202401", "数学", "张老师", "测试作业", "2024-12-12 19:00", 30, "日常", "wxid_001"
            )

            hw.__exit__(None, None, None)

            assert hw_id > 0

            # 验证查询
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT * FROM homework WHERE id=?", (hw_id,))
            record = cursor.fetchone()
            conn.close()

            assert record is not None
            assert record[1] == 202401  # class_code (integer in db)
            assert record[2] == "数学"  # subject
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_homework_cursor_behavior(self):
        """Homework cursor 行为正常"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "homework.db")

            from models.lesson.homework import Homework

            hw = Homework()
            hw.__enter__(db_path=db_path)
            hw.__create_table__()

            # 使用 cursor
            hw.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = hw.cursor.fetchall()

            hw.__exit__(None, None, None)

            assert len(tables) >= 1
            table_names = [t[0] for t in tables]
            assert "homework" in table_names
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_homework_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from models.lesson.homework import _get_sqlite_connection

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

    def test_homework_announcement_add_and_get(self):
        """Homework 公告添加和查询功能"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "homework.db")

            from models.lesson.homework import Homework

            hw = Homework()
            hw.__enter__(db_path=db_path)
            hw.__create_table__()

            # 添加公告
            ann_id = hw.add_announcement("202401", "测试公告", "王老师", "公告内容", "wxid_002")

            # 查询公告（不依赖返回值，直接查询验证）
            announcements = hw.get_announcement("202401")

            hw.__exit__(None, None, None)

            assert len(announcements) >= 1
            assert announcements[0]["title"] == "测试公告"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_homework_sqlite_exception_names_available(self):
        """迁移连接后仍保留 sqlite3 异常引用。"""
        from models.lesson import homework as homework_module

        assert homework_module.sqlite3.OperationalError is sqlite3.OperationalError
        assert homework_module.sqlite3.IntegrityError is sqlite3.IntegrityError


class TestNotesSqliteBase:
    """Notes sqlite_base 迁移测试"""

    def test_notes_enter_uses_sqlite_base_and_exit_closes(self, monkeypatch):
        """Notes.__enter__ 使用 sqlite_base 连接入口，__exit__ 关闭连接。"""
        from models.lesson import notes as notes_module

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
            notes_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        notes = notes_module.Notes()
        notes.__enter__(db="/tmp/notes-test.db")
        notes.__exit__(None, None, None)

        assert calls == [("/tmp/notes-test.db", {})]
        assert fake_connection.closed is True

    def test_notes_db_auto_created_on_enter(self):
        """Notes 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "notes.db")

            from models.lesson.notes import Notes

            notes = Notes()
            notes.__enter__(db=db_path)
            notes.__create_table__()
            notes.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_notes_insert_and_query(self):
        """Notes 入库后能查询"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "notes.db")

            from models.lesson.notes import Notes

            notes = Notes()
            notes.__enter__(db=db_path)
            notes.__create_table__()

            # 插入记录
            notes.insert_note("张老师", "测试记录")

            notes.__exit__(None, None, None)

            # 验证查询
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT * FROM notes")
            records = cursor.fetchall()
            conn.close()

            assert len(records) >= 1
            assert records[0][1] == "张老师"  # recorder
            assert records[0][2] == "测试记录"  # note
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_notes_cursor_behavior(self):
        """Notes cursor 行为正常"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "notes.db")

            from models.lesson.notes import Notes

            notes = Notes()
            notes.__enter__(db=db_path)
            notes.__create_table__()

            # 使用 cursor
            notes.__cursor__.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = notes.__cursor__.fetchall()

            notes.__exit__(None, None, None)

            assert len(tables) >= 1
            table_names = [t[0] for t in tables]
            assert "notes" in table_names
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_notes_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from models.lesson.notes import _get_sqlite_connection

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

    def test_notes_get_notes_by_month(self):
        """Notes 按月查询功能"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "notes.db")

            from models.lesson.notes import Notes

            notes = Notes()
            notes.__enter__(db=db_path)
            notes.__create_table__()

            # 插入记录
            notes.insert_note("李老师", "五月记录")

            # 查询本月
            current_month_records = notes.get_notes(month=0)

            notes.__exit__(None, None, None)

            # 验证查询返回列表
            assert isinstance(current_month_records, list)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_notes_sqlite_exception_names_available(self):
        """迁移连接后仍保留 sqlite3 异常引用。"""
        from models.lesson import notes as notes_module

        assert notes_module.sqlite3.OperationalError is sqlite3.OperationalError
