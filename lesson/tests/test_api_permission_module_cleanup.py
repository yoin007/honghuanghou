# -*- coding: utf-8 -*-
"""API 权限模块清理回归测试。"""

import sqlite3

from models.datas_api.moral.api_permission import _fix_incorrect_scope_rules


class SQLiteTestDB:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
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
                is_active INTEGER DEFAULT 1,
                enforce_backend INTEGER DEFAULT 1,
                resource_type TEXT DEFAULT '',
                action_type TEXT DEFAULT '',
                operation_scope_rules TEXT DEFAULT '{}',
                data_scope_rules TEXT DEFAULT '{}',
                target_scope_rules TEXT DEFAULT '{}'
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


def test_fix_scope_rules_removes_empty_legacy_birthday_module():
    db = SQLiteTestDB()
    db.execute(
        """INSERT INTO api_permission_module
           (module_key, module_name, allowed_roles, min_level, description)
           VALUES (?, ?, ?, ?, ?)""",
        ("birthday_reminder", "生日提醒", '["admin"]', 10, "existing"),
    )
    birthday_module_id = db.lastrowid()
    db.execute(
        """INSERT INTO api_permission_module
           (module_key, module_name, allowed_roles, min_level, description)
           VALUES (?, ?, ?, ?, ?)""",
        ("legacy_birthday_view", "生日查看", '["admin"]', 10, "legacy"),
    )
    db.execute(
        """INSERT INTO api_permission_config
           (api_path, api_name, api_group, allowed_roles, min_level, module_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            "/api/moral/birthdays/today",
            "今日生日",
            "生日提醒",
            '["admin"]',
            10,
            birthday_module_id,
        ),
    )

    _fix_incorrect_scope_rules(db)

    legacy = db.query_one("SELECT id FROM api_permission_module WHERE module_name = '生日查看'")
    today = db.query_one(
        "SELECT api_group, module_id FROM api_permission_config WHERE api_path = ?",
        ("/api/moral/birthdays/today",),
    )

    assert legacy is None
    assert today["api_group"] == "生日提醒"
    assert today["module_id"] == birthday_module_id


def test_fix_scope_rules_repairs_legacy_lookup_permissions_for_record_pages():
    db = SQLiteTestDB()
    for api_path in (
        "/api/moral/admin/grades",
        "/api/moral/admin/classes",
        "/api/moral/admin/school-years",
        "/api/moral/admin/semesters",
    ):
        db.execute(
            """INSERT INTO api_permission_config
               (api_path, api_name, api_group, allowed_roles, min_level)
               VALUES (?, ?, ?, ?, ?)""",
            (api_path, "legacy lookup", "基础配置", '["admin", "xuefa", "jiaowu"]', 0),
        )

    _fix_incorrect_scope_rules(db)

    for api_path in (
        "/api/moral/admin/grades",
        "/api/moral/admin/classes",
        "/api/moral/admin/school-years",
        "/api/moral/admin/semesters",
    ):
        row = db.query_one(
            "SELECT allowed_roles, min_level FROM api_permission_config WHERE api_path = ?",
            (api_path,),
        )
        assert row["allowed_roles"] == '["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"]'
        assert row["min_level"] == 10
