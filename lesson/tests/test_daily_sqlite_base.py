# -*- coding: utf-8 -*-
"""
daily.py / inout.py sqlite_base 迁移回归测试

Batch 11: 验证 daily 模块使用 sqlite_base 后行为不变
"""
import pytest
import sqlite3
import os
import tempfile
import shutil
from datetime import datetime


class TestDailySqliteBase:
    """Daily sqlite_base 迁移测试"""

    def test_daily_enter_uses_sqlite_base_and_exit_closes(self, monkeypatch):
        """Daily.__enter__ 使用 sqlite_base 连接入口，__exit__ 关闭连接。"""
        from models.daily import daily as daily_module

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
            daily_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        daily = daily_module.Daily()
        daily.__enter__(db="/tmp/daily-test.db")
        daily.__exit__(None, None, None)

        assert calls == [("/tmp/daily-test.db", {})]
        assert fake_connection.closed is True

    def test_daily_db_auto_created_on_enter(self):
        """Daily 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "daily.db")

            from models.daily.daily import Daily

            daily = Daily()
            daily.__enter__(db=db_path)
            daily.__create_table__()
            daily.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_daily_insert_and_query(self):
        """Daily 入库后能查询"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "daily.db")

            from models.daily.daily import Daily

            daily = Daily()
            daily.__enter__(db=db_path)
            daily.__create_table__()

            # 插入记录
            record_id = daily.insert_daily(
                "睡觉", "sid_001", "数学", "张老师", "测试备注"
            )

            daily.__exit__(None, None, None)

            assert record_id > 0

            # 验证查询
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT * FROM daily WHERE id=?", (record_id,))
            record = cursor.fetchone()
            conn.close()

            assert record is not None
            assert record[1] == "睡觉"  # event
            assert record[2] == "sid_001"  # sid
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_daily_columns_returns_correct_names(self):
        """daily_columns 返回正确列名"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "daily.db")

            from models.daily.daily import Daily

            daily = Daily()
            daily.__enter__(db=db_path)
            daily.__create_table__()

            columns = daily.daily_columns()

            daily.__exit__(None, None, None)

            assert "id" in columns
            assert "event" in columns
            assert "sid" in columns
            assert "recorder" in columns
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_daily_delete_works(self):
        """删除记录功能正常"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "daily.db")

            from models.daily.daily import Daily

            daily = Daily()
            daily.__enter__(db=db_path)
            daily.__create_table__()

            # 插入记录
            record_id = daily.insert_daily(
                "睡觉", "sid_002", "数学", "李老师", ""
            )

            # 删除记录
            count = daily.del_daily(record_id)

            daily.__exit__(None, None, None)

            assert count == 1

            # 验证已删除
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM daily WHERE id=?", (record_id,))
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 0
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_daily_get_recorder(self):
        """get_recorder 返回正确记录者"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "daily.db")

            from models.daily.daily import Daily

            daily = Daily()
            daily.__enter__(db=db_path)
            daily.__create_table__()

            # 插入记录
            record_id = daily.insert_daily(
                "睡觉", "sid_003", "数学", "王老师", ""
            )

            # 获取记录者
            recorder = daily.get_recorder(record_id)

            daily.__exit__(None, None, None)

            assert recorder == "王老师"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from models.daily.daily import _get_sqlite_connection

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


class TestInoutSqliteBase:
    """InOut sqlite_base 迁移测试"""

    def test_inout_enter_uses_sqlite_base_and_exit_closes(self, monkeypatch):
        """InOut.__enter__ 使用 sqlite_base 连接入口，__exit__ 关闭连接。"""
        from models.daily import inout as inout_module

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
            inout_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        inout = inout_module.InOut()
        inout.__enter__(db="/tmp/inout-test.db")
        inout.__exit__(None, None, None)

        assert calls == [("/tmp/inout-test.db", {})]
        assert fake_connection.closed is True

    def test_inout_db_auto_created_on_enter(self):
        """InOut 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "inout.db")

            from models.daily.inout import InOut

            inout = InOut()
            inout.__enter__(db=db_path)
            inout.__create_table__()
            inout.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_inout_insert_and_query(self):
        """InOut 入库后能查询"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "inout.db")

            from models.daily.inout import InOut

            inout = InOut()
            inout.__enter__(db=db_path)
            inout.__create_table__()

            # 插入记录
            record_id = inout.insert_inout(
                "sid_001", "事假", "张老师", "已请假", "2", "测试备注"
            )

            inout.__exit__(None, None, None)

            assert record_id > 0

            # 验证查询
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT * FROM inout WHERE id=?", (record_id,))
            record = cursor.fetchone()
            conn.close()

            assert record is not None
            assert record[1] == "sid_001"  # sid
            assert record[2] == "事假"  # style
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_inout_columns_returns_correct_names(self):
        """inout_columns 返回正确列名"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "inout.db")

            from models.daily.inout import InOut

            inout = InOut()
            inout.__enter__(db=db_path)
            inout.__create_table__()

            columns = inout.inout_columns()

            inout.__exit__(None, None, None)

            assert "id" in columns
            assert "sid" in columns
            assert "style" in columns
            assert "recorder" in columns
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_inout_out_inout_works(self):
        """出校功能正常"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "inout.db")

            from models.daily.inout import InOut

            inout = InOut()
            inout.__enter__(db=db_path)
            inout.__create_table__()

            # 插入记录
            record_id = inout.insert_inout(
                "sid_002", "事假", "李老师", "已请假", "1", ""
            )

            # 出校
            inout.out_inout(record_id, guard="门卫张")

            inout.__exit__(None, None, None)

            # 验证状态
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT status, guard FROM inout WHERE id=?", (record_id,)
            )
            record = cursor.fetchone()
            conn.close()

            assert record[0] == "已出校"
            assert record[1] == "门卫张"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_inout_in_inout_works(self):
        """销假功能正常"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "inout.db")

            from models.daily.inout import InOut

            inout = InOut()
            inout.__enter__(db=db_path)
            inout.__create_table__()

            # 插入记录
            record_id = inout.insert_inout(
                "sid_003", "事假", "王老师", "已请假", "1", ""
            )

            # 销假
            inout.in_inout(record_id, consumer="王老师")

            inout.__exit__(None, None, None)

            # 验证状态
            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT status, consumer FROM inout WHERE id=?", (record_id,)
            )
            record = cursor.fetchone()
            conn.close()

            assert record[0] == "已销假"
            assert record[1] == "王老师"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_inout_get_recorder(self):
        """get_recorder 返回正确记录者"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "inout.db")

            from models.daily.inout import InOut

            inout = InOut()
            inout.__enter__(db=db_path)
            inout.__create_table__()

            # 插入记录
            record_id = inout.insert_inout(
                "sid_004", "事假", "赵老师", "已请假", "1", ""
            )

            # 获取记录者
            recorder = inout.get_recorder(record_id)

            inout.__exit__(None, None, None)

            assert recorder == "赵老师"
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_inout_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from models.daily.inout import _get_sqlite_connection

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
