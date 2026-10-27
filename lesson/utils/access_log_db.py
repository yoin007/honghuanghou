# _*_ coding: utf-8 _*_
"""访问日志存储（二期）：独立 SQLite 库，与业务库隔离。

记录每个 HTTP 请求：时间、用户名、角色、IP、方法、路径、状态码、耗时。
写入失败绝不阻断请求。
"""

import os
import sqlite3
import threading
from datetime import datetime

from utils.db_config import DATABASES_DIR

_DB_PATH = os.path.join(DATABASES_DIR, "access.db")
_lock = threading.Lock()
_initialized = False
_purged = False


def _get_retention_days():
    """与文件日志同源：lesson.yaml 的 log_retention_days，默认 1095 天"""
    try:
        import yaml
        cfg_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "lesson.yaml")
        with open(cfg_file, "r", encoding="utf-8") as f:
            return int(yaml.safe_load(f).get("log_retention_days", 1095))
    except Exception:
        return 1095


def _purge_old_records(conn):
    """每个进程启动后首次写入时，清理超过保留天数的记录"""
    global _purged
    if _purged:
        return
    _purged = True
    try:
        days = _get_retention_days()
        conn.execute(f"DELETE FROM access_log WHERE DATE(ts) < DATE('now', 'localtime', '-{int(days)} days')")
        conn.commit()
    except Exception:
        pass


def _ensure_schema(conn):
    global _initialized
    if not _initialized:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                username TEXT DEFAULT '',
                role TEXT DEFAULT '',
                ip TEXT DEFAULT '',
                method TEXT DEFAULT '',
                path TEXT DEFAULT '',
                status INTEGER,
                duration_ms INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_access_log_ts ON access_log(ts);
            CREATE INDEX IF NOT EXISTS idx_access_log_username ON access_log(username);
        """)
        _initialized = True


def record_access(username, role, ip, method, path, status, duration_ms):
    """写入一条访问记录，任何异常都静默吞掉（日志不能影响业务请求）"""
    try:
        with _lock:
            conn = sqlite3.connect(_DB_PATH, timeout=5)
            try:
                _ensure_schema(conn)
                _purge_old_records(conn)
                conn.execute(
                    "INSERT INTO access_log (ts, username, role, ip, method, path, status, duration_ms)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (datetime.now().isoformat(timespec="seconds"), username or "", role or "",
                     ip or "", method or "", path or "", status, int(duration_ms or 0)),
                )
                conn.commit()
            finally:
                conn.close()
    except Exception:
        pass


def query_access_logs(username=None, ip=None, path=None, start_date=None, end_date=None,
                      page=1, page_size=20):
    """分页查询访问日志，返回 {total, items, page, page_size, total_pages}"""
    conditions = ["1=1"]
    params = []

    if username:
        conditions.append("username LIKE ?")
        params.append(f"%{username}%")
    if ip:
        conditions.append("ip LIKE ?")
        params.append(f"%{ip}%")
    if path:
        conditions.append("path LIKE ?")
        params.append(f"%{path}%")
    if start_date:
        conditions.append("DATE(ts) >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("DATE(ts) <= ?")
        params.append(end_date)

    where_clause = " AND ".join(conditions)

    with _lock:
        conn = sqlite3.connect(_DB_PATH, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            _ensure_schema(conn)
            total = conn.execute(f"SELECT COUNT(*) FROM access_log WHERE {where_clause}", params).fetchone()[0]
            offset = (page - 1) * page_size
            rows = conn.execute(
                f"SELECT * FROM access_log WHERE {where_clause} ORDER BY ts DESC, id DESC LIMIT ? OFFSET ?",
                params + [page_size, offset],
            ).fetchall()
            items = [dict(r) for r in rows]
        finally:
            conn.close()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }
