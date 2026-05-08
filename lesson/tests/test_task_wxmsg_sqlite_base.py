# -*- coding: utf-8 -*-
"""
task.py / wxmsg.py sqlite_base 迁移回归测试

Batch 14: 验证 task 和 wxmsg 使用 sqlite_base 后行为不变
"""
import pytest
import sqlite3
import os
import tempfile
import shutil
from datetime import datetime


class TestTaskSqliteBase:
    """Task sqlite_base 迁移测试"""

    def test_task_enter_uses_sqlite_base_with_check_same_thread_false(self, monkeypatch):
        """Task.__enter__ 使用 sqlite_base，并保留 check_same_thread=False。"""
        from models import task as task_module

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
            task_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        # 创建临时数据库路径
        tmp_dir = tempfile.mkdtemp()
        db_path = os.path.join(tmp_dir, "task.db")

        try:
            task = task_module.Task()
            # Task.__init__ 自动调用 __enter__，使用默认 TASK_DB
            # 验证 sqlite_base 被调用且 check_same_thread=False 参数保留
            assert len(calls) == 1
            # 第一次调用使用默认 TASK_DB
            assert "check_same_thread" in calls[0][1]
            assert calls[0][1]["check_same_thread"] is False

            # 关闭连接
            task.__exit__(None, None, None)
            assert fake_connection.closed is True
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_task_db_auto_created(self):
        """Task 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "task.db")

            from models.task import Task

            task = Task()
            task.__enter__(db=db_path)
            task.__create_table__()
            task.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_task_add_task_to_db(self):
        """Task 添加任务到数据库后能查询"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "task.db")

            from models.task import Task

            task = Task()
            task.__enter__(db=db_path)
            task.__create_table__()

            task_id = task.add_task_to_db(
                func_name="test_func",
                trigger_type="cron",
                trigger_args='{"hour": 3}',
                description="测试任务",
                one_off=True,
            )

            assert task_id > 0

            # 验证查询
            tasks = task.get_tasks_from_db()
            assert len(tasks) >= 1

            task.__exit__(None, None, None)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_task_update_consumed_creates_new_connection(self, monkeypatch):
        """update_task_consumed 创建新连接（非复用），并使用 sqlite_base。"""
        from models import task as task_module

        calls = []

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def cursor(self):
                class FakeCursor:
                    def execute(self, sql, params):
                        pass
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
            task_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        # 调用 update_task_consumed
        result = task_module.task_scheduler.update_task_consumed(1, consumed=True)

        assert result is True
        assert len(calls) == 1
        # update_task_consumed 不需要 check_same_thread=False（在当前线程使用）
        assert fake_connection.closed is True

    def test_task_update_consumed_closes_connection_on_error(self, monkeypatch):
        """update_task_consumed 执行失败时也关闭 sqlite_base 连接。"""
        from models import task as task_module

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def cursor(self):
                class FakeCursor:
                    def execute(self, sql, params):
                        raise RuntimeError("boom")

                return FakeCursor()

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            return fake_connection

        monkeypatch.setattr(
            task_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        result = task_module.task_scheduler.update_task_consumed(1, consumed=True)

        assert result is False
        assert fake_connection.closed is True

    def test_task_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from models.task import _get_sqlite_connection

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

    def test_task_sqlite_exception_names_available(self):
        """迁移连接后仍保留 sqlite3 异常引用。"""
        from models import task as task_module

        assert task_module.sqlite3.OperationalError is sqlite3.OperationalError


class TestWxMsgSqliteBase:
    """WxMsg sqlite_base 迁移测试"""

    def test_wxmsg_enter_uses_sqlite_base_and_exit_closes(self, monkeypatch):
        """MessageDB.__enter__ 使用 sqlite_base 连接入口，__exit__ 关闭连接。"""
        from lesson import wxmsg as wxmsg_module

        calls = []

        class FakeConnection:
            def __init__(self):
                self.closed = False

            def cursor(self):
                return object()

            def commit(self):
                pass

            def close(self):
                self.closed = True

        fake_connection = FakeConnection()

        def fake_get_sqlite_connection(db_path, **kwargs):
            calls.append((db_path, kwargs))
            return fake_connection

        monkeypatch.setattr(
            wxmsg_module,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        msg_db = wxmsg_module.MessageDB()
        msg_db.__enter__(db="/tmp/messages-test.db")
        msg_db.__exit__(None, None, None)

        assert calls == [("/tmp/messages-test.db", {})]
        assert fake_connection.closed is True

    def test_wxmsg_db_auto_created(self):
        """MessageDB 数据库在 __enter__ 时自动创建"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "messages.db")

            from lesson.wxmsg import MessageDB

            msg_db = MessageDB()
            msg_db.__enter__(db=db_path)
            msg_db.__create_table__()
            msg_db.__exit__(None, None, None)

            assert os.path.exists(db_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_wxmsg_insert_and_select(self):
        """MessageDB 插入消息后能查询"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "messages.db")

            from lesson.wxmsg import MessageDB

            msg_db = MessageDB()
            msg_db.__enter__(db=db_path)
            msg_db.__create_table__()

            # 插入消息
            msg = {
                "wxid": "test_wxid",
                "msg_id": "test_msg_001",
                "type": 1,
                "sender": "test_sender",
                "roomid": "test_room",
                "content": "测试消息",
                "thumb": "",
                "ext": "",
                "is_at": False,
                "is_self": False,
                "is_group": False,
                "create_time": 1700000000000,
            }
            msg_db.insert(msg)

            # 查询消息
            result = msg_db.select("test_msg_001")

            msg_db.__exit__(None, None, None)

            assert result is not None
            assert result[2] == "test_msg_001"  # msg_id in column 2
            assert result[6] == "测试消息"  # content in column 6
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_wxmsg_select_nonexistent_returns_none(self):
        """MessageDB 查询不存在消息返回 None"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "messages.db")

            from lesson.wxmsg import MessageDB

            msg_db = MessageDB()
            msg_db.__enter__(db=db_path)
            msg_db.__create_table__()

            result = msg_db.select("nonexistent_msg_id")

            msg_db.__exit__(None, None, None)

            assert result is None
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_wxmsg_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from lesson.wxmsg import _get_sqlite_connection

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
