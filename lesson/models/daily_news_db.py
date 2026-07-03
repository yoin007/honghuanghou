# -*- coding: utf-8 -*-
"""每日早报缓存数据库

将 alapi 每日早报接口返回的数据按日期落库，避免同一天重复调用外部接口。

存储字段：
- date        早报日期（YYYY-MM-DD），主键
- payload     完整响应 JSON（字符串）
- created_at  首次入库时间
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional

from utils.db_config import DATABASES_DIR

logger = logging.getLogger(__name__)

DAILY_NEWS_DB = os.path.join(DATABASES_DIR, "daily_news.db")


def _connect() -> sqlite3.Connection:
    os.makedirs(DATABASES_DIR, exist_ok=True)
    conn = sqlite3.connect(DAILY_NEWS_DB, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_news (
            date TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
        """
    )
    conn.commit()


@contextmanager
def _db():
    conn = _connect()
    try:
        _ensure_schema(conn)
        yield conn
    finally:
        conn.close()


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_cached(date_str: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """按日期读取缓存，未命中返回 None。默认今日。"""
    date_str = date_str or _today_str()
    try:
        with _db() as conn:
            row = conn.execute(
                "SELECT payload FROM daily_news WHERE date = ?",
                (date_str,),
            ).fetchone()
            if not row:
                return None
            return json.loads(row["payload"])
    except Exception as exc:  # 缓存失败不应影响主流程
        logger.warning(f"读取每日早报缓存失败: {exc}")
        return None


def save_cache(data: Dict[str, Any], date_str: Optional[str] = None) -> bool:
    """把接口返回落库；同一天只保存一次（INSERT OR IGNORE）。"""
    if not data:
        return False
    # 优先使用接口返回的 date 字段（形如 2026-07-03）
    date_str = date_str or str(data.get("date") or "").strip() or _today_str()
    try:
        with _db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO daily_news (date, payload) VALUES (?, ?)",
                (date_str, json.dumps(data, ensure_ascii=False)),
            )
            conn.commit()
            return True
    except Exception as exc:
        logger.warning(f"写入每日早报缓存失败: {exc}")
        return False


def list_dates(limit: int = 90) -> list[str]:
    """返回已缓存的日期列表（按新→旧），供前端 DatePicker 标注可选项。"""
    try:
        with _db() as conn:
            rows = conn.execute(
                "SELECT date FROM daily_news ORDER BY date DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [row["date"] for row in rows]
    except Exception as exc:
        logger.warning(f"读取每日早报日期列表失败: {exc}")
        return []


__all__ = ["get_cached", "save_cache", "list_dates", "DAILY_NEWS_DB"]
