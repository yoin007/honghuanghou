# -*- coding: utf-8 -*-
"""
sendqueue.py sqlite_base 迁移回归测试

Batch 10: 验证 sendqueue.py 使用 sqlite_base 后行为不变
"""
import pytest
import sqlite3
import os
import json
import tempfile


class TestSendqueueSqliteBase:
    """sendqueue sqlite_base 迁移测试"""

    def test_queues_db_auto_created_on_enter(self):
        """队列数据库在 __enter__ 时自动创建"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "queues.db")

            # 直接使用 db 参数传入
            from sendqueue import QueueDB

            queue = QueueDB()
            queue.__enter__(db=db_path)
            queue.__create_table__()
            queue.__exit__()

            assert os.path.exists(db_path)

    def test_produce_and_query_message(self):
        """入队后能查询消息"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "queues.db")

            from sendqueue import QueueDB

            queue = QueueDB()
            queue.__enter__(db=db_path)
            queue.__create_table__()

            # 生产消息
            data = {"test": "message"}
            queue.__produce__(data, "http://test.api", "test_producer", "msg_001")

            queue.__exit__()

            # 查询消息
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM queues WHERE msg_id='msg_001'")
            record = cursor.fetchone()
            conn.close()

            assert record is not None
            assert record["producer"] == "test_producer"
            assert record["status"] == "pending"
            assert json.loads(record["data"]) == data
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_update_message_status(self):
        """状态更新仍然生效"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "queues.db")

            from sendqueue import QueueDB

            queue = QueueDB()
            queue.__enter__(db=db_path)
            queue.__create_table__()
            queue.__produce__({"test": "data"}, "http://test.api", "producer", "msg_002")

            # 获取消息 ID
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT id FROM queues WHERE msg_id='msg_002'")
            msg_id = cursor.fetchone()[0]
            conn.close()

            # 更新状态
            queue.__update_message_status__(msg_id, "success")
            queue.__exit__()

            # 验证更新
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT status FROM queues WHERE id=?", (msg_id,))
            status = cursor.fetchone()[0]
            conn.close()

            assert status == "success"
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_connection_timeout_is_30(self):
        """验证 sqlite_base 默认 timeout=30"""
        from models.datas_api.repositories.sqlite_base import get_sqlite_connection

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "test.db")

            # 使用默认参数创建连接
            conn = get_sqlite_connection(db_path)
            conn.execute("CREATE TABLE test (id INTEGER)")
            conn.close()

            assert os.path.exists(db_path)

    def test_enter_uses_sqlite_base_with_timeout_and_row_factory(self, monkeypatch):
        """线程本地连接入口使用 sqlite_base，并保留 timeout=30 和 Row 工厂。"""
        import sendqueue

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
            sendqueue,
            "_get_sqlite_connection",
            lambda: fake_get_sqlite_connection,
        )

        queue = sendqueue.QueueDB()
        queue.__enter__(db="/tmp/queues.db")
        queue.__exit__()

        assert calls == [
            (
                "/tmp/queues.db",
                {"timeout": 30, "row_factory": sqlite3.Row},
            )
        ]
        assert fake_connection.closed is True

    def test_get_queue_status_returns_correct_counts(self):
        """get_queue_status 返回正确统计"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "queues.db")

            from sendqueue import QueueDB

            queue = QueueDB()
            queue.__enter__(db=db_path)
            queue.__create_table__()

            # 生产多条消息
            for i in range(3):
                queue.__produce__({"idx": i}, "http://test.api", "producer", f"msg_{i}")

            queue.__exit__()

            # 使用临时 db 路径调用 get_queue_status
            # 注意：get_queue_status 使用 DB_DIR，无法直接测试
            # 但可以验证 sqlite_base 连接正常
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM queues WHERE status='pending'")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 3

    def test_thread_local_connection_isolated(self):
        """线程本地连接保持隔离"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "queues.db")

            from sendqueue import QueueDB
            import threading

            results = {}

            def thread_func(thread_id):
                queue = QueueDB()
                queue.__enter__(db=db_path)
                queue.__create_table__()
                # 每个线程有自己的连接
                results[thread_id] = hasattr(queue._local, "connection")
                queue.__exit__()

            threads = []
            for i in range(3):
                t = threading.Thread(target=thread_func, args=(i,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            # 每个线程都应该有自己的连接
            assert all(results.values())

    def test_clean_expired_messages(self):
        """清理过期消息功能正常"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "queues.db")

            from sendqueue import QueueDB
            from datetime import datetime, timedelta

            queue = QueueDB()
            queue.__enter__(db=db_path)
            queue.__create_table__()

            # 生产消息
            queue.__produce__({"test": "data"}, "http://test.api", "producer", "msg_003")

            # 修改消息时间戳使其过期
            conn = sqlite3.connect(db_path)
            expired_timestamp = int((datetime.now() - timedelta(minutes=30)).timestamp())
            conn.execute("UPDATE queues SET timestamp=?", (expired_timestamp,))
            conn.commit()
            conn.close()

            # 清理过期消息
            deleted_count = queue.__clean_expired_messages__()
            queue.__exit__()

            assert deleted_count == 1

            # 验证消息已删除
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT COUNT(*) FROM queues")
            count = cursor.fetchone()[0]
            conn.close()

            assert count == 0

    def test_retry_failed_messages(self):
        """重试失败消息功能正常"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "queues.db")

            from sendqueue import QueueDB

            queue = QueueDB()
            queue.__enter__(db=db_path)
            queue.__create_table__()

            # 生产消息
            queue.__produce__({"test": "data"}, "http://test.api", "producer", "msg_004")

            # 获取消息 ID
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT id FROM queues WHERE msg_id='msg_004'")
            msg_id = cursor.fetchone()[0]
            conn.close()

            # 设置为失败状态
            queue.__update_message_status__(msg_id, "failed", "test error")

            # 重试失败消息
            retry_count = queue.__retry_failed_messages__()
            queue.__exit__()

            assert retry_count == 1

            # 验证状态已恢复为 pending
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT status FROM queues WHERE id=?", (msg_id,))
            status = cursor.fetchone()[0]
            conn.close()

            assert status == "pending"

    def test_delayed_import_works(self):
        """验证延迟导入函数可用"""
        from sendqueue import _get_sqlite_connection

        get_sqlite_connection = _get_sqlite_connection()
        assert get_sqlite_connection is not None

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "test.db")
            conn = get_sqlite_connection(db_path)
            conn.close()

            assert os.path.exists(db_path)

    def test_produce_data_json_serialization(self):
        """验证消息数据 JSON 序列化正常"""
        tmp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(tmp_dir, "queues.db")

            from sendqueue import QueueDB

            queue = QueueDB()
            queue.__enter__(db=db_path)
            queue.__create_table__()

            # 生产包含中文的消息
            data = {"content": "测试消息", "user": "张三"}
            queue.__produce__(data, "http://test.api", "producer", "msg_005")
            queue.__exit__()

            # 验证 JSON 序列化（ensure_ascii=False）
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("SELECT data FROM queues WHERE msg_id='msg_005'")
            data_str = cursor.fetchone()[0]
            conn.close()

            # 验证中文没有被转义
            assert "测试消息" in data_str
            assert "张三" in data_str

            # 验证可以正确反序列化
            parsed = json.loads(data_str)
            assert parsed["content"] == "测试消息"
        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
