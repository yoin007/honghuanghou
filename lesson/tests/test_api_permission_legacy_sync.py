# -*- coding: utf-8 -*-
"""旧版 YAML 权限同步回归测试。"""

import json
import sqlite3

from models.datas_api.moral.api_permission import _sync_legacy_api_level_yaml


class SQLiteLegacySyncDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE api_permission_module (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module_key TEXT,
                module_name TEXT,
                allowed_roles TEXT DEFAULT '[]',
                min_level INTEGER DEFAULT 0,
                policy_mode TEXT DEFAULT 'role_and_level',
                description TEXT DEFAULT ''
            );
            CREATE TABLE api_permission_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_path TEXT,
                api_name TEXT DEFAULT '',
                api_group TEXT DEFAULT '',
                allowed_roles TEXT DEFAULT '[]',
                min_level INTEGER DEFAULT 0,
                module_id INTEGER,
                http_method TEXT DEFAULT '*',
                match_type TEXT DEFAULT 'exact',
                policy_mode TEXT DEFAULT 'role_and_level',
                is_public INTEGER DEFAULT 0,
                enforce_backend INTEGER DEFAULT 1,
                description TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            );
            """
        )

    def execute(self, sql, params=()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur.rowcount

    def query_one(self, sql, params=()):
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def query_all(self, sql, params=()):
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def lastrowid(self):
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def test_legacy_yaml_sync_refreshes_existing_vehicle_permission():
    db = SQLiteLegacySyncDB()
    db.execute(
        """INSERT INTO api_permission_config
           (api_path, api_name, api_group, allowed_roles, min_level, is_public)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "/api/vehicle-inout/{counts}",
            "旧版接口 /vehicle-inout/{counts}",
            "旧版教务接口",
            "[]",
            0,
            1,
        ),
    )

    result = _sync_legacy_api_level_yaml(db)
    row = db.query_one(
        """SELECT allowed_roles, min_level, is_public, match_type
           FROM api_permission_config
           WHERE api_path = ?""",
        ("/api/vehicle-inout/{counts}",),
    )

    assert result["updated"] >= 1
    assert json.loads(row["allowed_roles"]) == ["admin"]
    assert row["min_level"] == 100
    assert row["is_public"] == 0
    assert row["match_type"] == "pattern"
