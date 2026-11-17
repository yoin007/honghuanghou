# -*- coding: utf-8 -*-
"""sendqueue 生产侧常驻连接：连接复用、WAL、失败回滚不毒化后续写入、多线程并发入队。"""

import os
import sqlite3
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import sendqueue
from sendqueue import QueueDB


@pytest.fixture
def queue_env(tmp_path, monkeypatch):
    """把 QueueDB 指向临时 db，单例重置，连接工厂打点计数。"""
    db_file = str(tmp_path / "queues.db")
    real_factory = sendqueue._get_sqlite_connection()
    connect_calls = []

    def counting_factory():
        def wrapper(db, **kwargs):
            connect_calls.append(db)
            return real_factory(db_file, **kwargs)
        return wrapper

    monkeypatch.setattr(sendqueue, "_get_sqlite_connection", counting_factory)

    original_instance = QueueDB._instance
    QueueDB._instance = None

    db = QueueDB()
    yield db, db_file, connect_calls

    # 清理：关闭本线程常驻连接并还原单例
    if hasattr(db._local, "connection"):
        db._local.connection.close()
    QueueDB._instance = original_instance


def _produce(q, content="hello"):
    return q.__produce__(
        {"friend_id": "wx_x", "message": content, "remark": "", "content_type": 1},
        "http://consumer.example/send", "test",
    )


def test_connection_reused_across_contexts(queue_env):
    db, _, connect_calls = queue_env

    with db as q1:
        rid1 = _produce(q1)
    with db as q2:
        rid2 = _produce(q2)

    assert rid1 and rid2 and rid1 != rid2
    # 两次 with 只建了一次连接（原实现是每次开/关）
    assert len(connect_calls) == 1


def test_wal_mode_active(queue_env):
    db, _, _ = queue_env
    with db as q:
        mode = q._local.connection.execute("PRAGMA journal_mode").fetchone()[0]
        sync = q._local.connection.execute("PRAGMA synchronous").fetchone()[0]
    assert mode.lower() == "wal"
    assert sync == 1  # NORMAL


def test_produced_row_visible_in_new_context(queue_env):
    db, db_file, _ = queue_env
    with db as q:
        rid = _produce(q, "持久化验证")

    raw = sqlite3.connect(db_file)
    row = raw.execute("SELECT data, producer FROM queues WHERE id = ?", (rid,)).fetchone()
    raw.close()
    assert row is not None
    assert "持久化验证" in row[0]
    assert row[1] == "test"


def test_failed_produce_rolls_back_and_recovers(queue_env):
    db, db_file, _ = queue_env
    with db as q:
        # 制造真实写入失败：表被删除后 INSERT 报错，验证回滚 + 恢复
        q._local.connection.execute("DROP TABLE queues")
        assert _produce(q) is None
        assert not q._local.connection.in_transaction  # 已回滚，无残留事务
        q.__create_table__()                             # 恢复表
        rid = _produce(q)                                # 同一连接继续可用
        assert rid is not None


def test_concurrent_producers(queue_env):
    db, db_file, _ = queue_env
    # 主线程先建库建表：9 个线程同时首触全新 db 文件时，
    # journal_mode=WAL 切换需短暂独占锁，是测试环境特有的竞态（生产库早已是 WAL）
    with db as q:
        assert _produce(q, "warmup") is not None

    threads = []
    errors = []

    def worker(n):
        try:
            for i in range(20):
                with db as q:
                    rid = q.__produce__(
                        {"friend_id": f"wx_t{n}", "message": f"m{i}", "remark": "", "content_type": 1},
                        "http://consumer.example/send", "test",
                    )
                    assert rid is not None
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    for n in range(8):
        t = threading.Thread(target=worker, args=(n,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    raw = sqlite3.connect(db_file)
    count = raw.execute("SELECT COUNT(*) FROM queues").fetchone()[0]
    raw.close()
    assert count == 8 * 20 + 1  # 8 线程 × 20 条 + warmup 全部落库，常驻连接互不干扰


def test_exit_rollback_on_exception(queue_env):
    db, db_file, _ = queue_env
    with pytest.raises(RuntimeError):
        with db as q:
            q._local.connection.execute(
                "INSERT INTO queues (status, data, producer, p_time, consumer, c_time, timestamp, retry_count, error_message)"
                " VALUES ('pending', 'x', 't', '2026-01-01 00:00:00', 'c', '', 0, 0, '')"
            )
            raise RuntimeError("模拟 with 块内异常")

    with db as q:
        assert not q._local.connection.in_transaction
        # 异常插入已回滚
        raw_count = q._local.connection.execute("SELECT COUNT(*) FROM queues").fetchone()[0]
    assert raw_count == 0
