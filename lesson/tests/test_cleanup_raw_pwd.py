# -*- coding: utf-8 -*-
"""
raw_pwd 清理脚本测试

Batch 8 第一阶段验收：清理脚本安全、可控、可回滚
"""
import pytest
import sqlite3
import os
import shutil
from datetime import datetime
from scripts.cleanup_raw_pwd import (
    get_cleanup_candidates,
    create_backup,
    build_recovery_command,
    cleanup_changed_raw_pwd,
    print_cleanup_report,
)


class TestCleanupCandidates:
    """get_cleanup_candidates 函数测试"""

    def test_db_not_exists_returns_zeros(self, tmp_path):
        """数据库不存在时返回全零，不抛异常"""
        db_path = str(tmp_path / "nonexistent.db")

        result = get_cleanup_candidates(db_path)

        assert result["db_exists"] is False
        assert result["table_exists"] is False
        assert result["changed_with_raw_pwd"] == 0
        assert result["unchanged_with_raw_pwd"] == 0
        assert result["cleanup_candidates"] == []

    def test_table_not_exists_returns_zeros(self, tmp_path):
        """teacher 表不存在时返回全零，不抛异常"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE other_table (id INTEGER)")
        conn.close()

        result = get_cleanup_candidates(db_path)

        assert result["db_exists"] is True
        assert result["table_exists"] is False
        assert result["cleanup_candidates"] == []

    def test_table_missing_required_columns_returns_error(self, tmp_path):
        """teacher 表缺少审计字段时返回可读提示"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                name TEXT
            )
        """)
        conn.commit()
        conn.close()

        result = get_cleanup_candidates(db_path)

        assert result["db_exists"] is True
        assert result["table_exists"] is True
        assert result["has_required_columns"] is False
        assert "error" in result
        assert "缺少审计字段" in result["error"]

    def test_candidates_count_correct(self, tmp_path):
        """正确统计可清理候选数量"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                password_hash TEXT,
                raw_pwd TEXT,
                is_password_changed INTEGER DEFAULT 0,
                updated_at TEXT
            )
        """)

        # 插入测试数据
        conn.execute("INSERT INTO teacher VALUES ('t1', '张老师', 'h1', 'pwd1', 1, NULL)")
        conn.execute("INSERT INTO teacher VALUES ('t2', '李老师', 'h2', 'pwd2', 0, NULL)")
        conn.execute("INSERT INTO teacher VALUES ('t3', '王老师', 'h3', NULL, 1, NULL)")
        conn.execute("INSERT INTO teacher VALUES ('t4', '刘老师', 'h4', '', 1, NULL)")
        conn.commit()
        conn.close()

        result = get_cleanup_candidates(db_path)

        assert result["teacher_total"] == 4
        assert result["has_updated_at"] is True
        assert result["changed_with_raw_pwd"] == 1  # t1
        assert result["unchanged_with_raw_pwd"] == 1  # t2
        assert result["cleanup_candidates"] == ["t1"]

    def test_candidates_closes_connection_when_query_fails(self, tmp_path, monkeypatch):
        """候选查询异常时也关闭数据库连接。"""
        db_path = str(tmp_path / "moral.db")
        open(db_path, "w").close()
        closed = {"value": False}

        class FailingConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                closed["value"] = True

            def execute(self, *_args, **_kwargs):
                raise RuntimeError("candidate query failed")

        monkeypatch.setattr(
            "scripts.cleanup_raw_pwd.sqlite3.connect",
            lambda _db_path: FailingConnection(),
        )

        result = get_cleanup_candidates(db_path)

        assert "candidate query failed" in result["error"]
        assert closed["value"] is True


class TestBackup:
    """create_backup 函数测试"""

    def test_backup_creates_file(self, tmp_path):
        """备份创建文件"""
        db_path = str(tmp_path / "moral.db")

        # 创建数据库
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        backup_path = create_backup(db_path, str(tmp_path))

        assert os.path.exists(backup_path)
        assert "raw_pwd_backup" in backup_path
        # 验证时间戳格式存在（YYYYMMDD_HHMMSS）
        assert ".raw_pwd_backup.20" in backup_path  # 年份前缀

    def test_backup_does_not_overwrite_same_second_file(self, tmp_path, monkeypatch):
        """同一秒多次备份时不覆盖已有备份。"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.commit()
        conn.close()

        class FixedDatetime:
            @classmethod
            def now(cls):
                return datetime(2026, 5, 3, 12, 0, 0)

        monkeypatch.setattr("scripts.cleanup_raw_pwd.datetime", FixedDatetime)

        backup_path_1 = create_backup(db_path, str(tmp_path))
        backup_path_2 = create_backup(db_path, str(tmp_path))

        assert os.path.exists(backup_path_1)
        assert os.path.exists(backup_path_2)
        assert backup_path_1 != backup_path_2

    def test_backup_preserves_data(self, tmp_path):
        """备份数据完整"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE teacher (teacher_id TEXT, name TEXT)")
        conn.execute("INSERT INTO teacher VALUES ('t1', '测试')")
        conn.commit()
        conn.close()

        backup_path = create_backup(db_path)

        # 验证备份数据
        conn_backup = sqlite3.connect(backup_path)
        cursor = conn_backup.execute("SELECT name FROM teacher WHERE teacher_id='t1'")
        assert cursor.fetchone()[0] == "测试"
        conn_backup.close()

    def test_backup_custom_dir(self, tmp_path):
        """自定义备份目录"""
        db_path = str(tmp_path / "moral.db")
        backup_dir = str(tmp_path / "custom_backup")

        conn = sqlite3.connect(db_path)
        conn.close()

        backup_path = create_backup(db_path, backup_dir)

        assert backup_path.startswith(backup_dir)
        assert os.path.exists(backup_path)

    def test_backup_raises_if_db_not_exists(self, tmp_path):
        """数据库不存在时抛 ValueError"""
        db_path = str(tmp_path / "nonexistent.db")

        with pytest.raises(ValueError, match="数据库不存在"):
            create_backup(db_path)


class TestCleanup:
    """cleanup_changed_raw_pwd 函数测试"""

    def test_dry_run_does_not_modify_db(self, tmp_path):
        """dry-run 不修改数据库"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                password_hash TEXT,
                raw_pwd TEXT,
                is_password_changed INTEGER DEFAULT 0,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', '张', 'h', 'secret_pwd', 1, NULL)")
        conn.commit()
        conn.close()

        # dry-run
        result = cleanup_changed_raw_pwd(db_path, apply=False)

        assert result["mode"] == "dry-run"
        assert result["candidates_count"] == 1

        # 验证数据库未修改
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT raw_pwd FROM teacher WHERE teacher_id='t1'")
        assert cursor.fetchone()[0] == "secret_pwd"
        conn.close()

    def test_apply_only_cleans_changed_accounts(self, tmp_path):
        """apply 只清理 is_password_changed=1 的 raw_pwd"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                password_hash TEXT,
                raw_pwd TEXT,
                is_password_changed INTEGER DEFAULT 0,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', '张', 'h', 'pwd_to_clean', 1, NULL)")
        conn.execute("INSERT INTO teacher VALUES ('t2', '李', 'h', 'pwd_keep', 0, NULL)")
        conn.commit()
        conn.close()

        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)

        assert result["mode"] == "apply"
        assert result["cleanup_count"] == 1
        assert result["unchanged_with_raw_pwd"] == 1

        # 验证数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT raw_pwd FROM teacher WHERE teacher_id='t1'")
        assert cursor.fetchone()[0] is None
        cursor = conn.execute("SELECT raw_pwd FROM teacher WHERE teacher_id='t2'")
        assert cursor.fetchone()[0] == "pwd_keep"
        conn.close()

    def test_apply_creates_backup(self, tmp_path):
        """apply 时创建备份"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 1, NULL)")
        conn.commit()
        conn.close()

        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)

        assert result["backup_path"] is not None
        assert os.path.exists(result["backup_path"])

    def test_apply_updates_timestamp(self, tmp_path):
        """apply 时更新 updated_at"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 1, NULL)")
        conn.commit()
        conn.close()

        cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT updated_at FROM teacher WHERE teacher_id='t1'")
        updated_at = cursor.fetchone()[0]
        assert updated_at is not None
        # 验证时间格式
        assert "-" in updated_at  # datetime('now') format: YYYY-MM-DD HH:MM:SS
        conn.close()

    def test_apply_works_without_updated_at_column(self, tmp_path):
        """旧表没有 updated_at 字段时仍能清理 raw_pwd。"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 1)")
        conn.commit()
        conn.close()

        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)

        assert "error" not in result
        assert result["cleanup_count"] == 1

        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT raw_pwd FROM teacher WHERE teacher_id='t1'")
        assert cursor.fetchone()[0] is None
        conn.close()

    def test_apply_no_candidates_does_nothing(self, tmp_path):
        """无候选时 apply 不做任何操作"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 0, NULL)")  # changed=0，不清理
        conn.commit()
        conn.close()

        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)

        assert result["cleanup_count"] == 0
        assert result["backup_path"] is None  # 无候选时不创建备份

    def test_db_not_exists_returns_error(self, tmp_path):
        """数据库不存在时返回错误，不抛异常"""
        db_path = str(tmp_path / "nonexistent.db")

        result = cleanup_changed_raw_pwd(db_path, apply=False)

        assert "error" in result
        assert "数据库不存在" in result["error"]

    def test_apply_closes_connection_when_cleanup_fails(self, tmp_path, monkeypatch):
        """清理写入异常时关闭连接，并返回可执行恢复命令。"""
        db_path = str(tmp_path / "live db.sqlite")
        backup_path = str(tmp_path / "backup dir" / "moral db.raw_pwd_backup.20260507_120000")
        closed = {"value": False}

        monkeypatch.setattr(
            "scripts.cleanup_raw_pwd.get_cleanup_candidates",
            lambda _db_path: {
                "db_exists": True,
                "table_exists": True,
                "has_required_columns": True,
                "has_updated_at": True,
                "changed_with_raw_pwd": 1,
                "unchanged_with_raw_pwd": 0,
                "cleanup_candidates": ["t1"],
            },
        )
        monkeypatch.setattr(
            "scripts.cleanup_raw_pwd.create_backup",
            lambda _db_path, _backup_dir=None: backup_path,
        )

        class FailingConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                closed["value"] = True

            def cursor(self):
                return self

            def execute(self, *_args, **_kwargs):
                raise RuntimeError("cleanup failed")

        monkeypatch.setattr(
            "scripts.cleanup_raw_pwd.sqlite3.connect",
            lambda _db_path: FailingConnection(),
        )

        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)

        assert "清理失败" in result["error"]
        assert closed["value"] is True
        assert result["recovery_hint"] == (
            "可恢复备份: "
            f"{build_recovery_command(backup_path, db_path)}"
        )


class TestOutput:
    """输出测试"""

    def test_report_does_not_output_plain_password(self, tmp_path, capsys):
        """打印报告不输出明文密码"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                password_hash TEXT,
                raw_pwd TEXT,
                is_password_changed INTEGER DEFAULT 0,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', '测试', 'h', 'secret_password_xyz', 1, NULL)")
        conn.commit()
        conn.close()

        result = cleanup_changed_raw_pwd(db_path, apply=False)
        print_cleanup_report(result)

        captured = capsys.readouterr()

        # 不应包含真实密码
        assert "secret_password_xyz" not in captured.out
        # 应包含数量
        assert "可清理候选数量" in captured.out

    def test_dry_run_report_shows_warning(self, tmp_path, capsys):
        """dry-run 报告显示警告提示"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 1, NULL)")
        conn.commit()
        conn.close()

        result = cleanup_changed_raw_pwd(db_path, apply=False)
        print_cleanup_report(result)

        captured = capsys.readouterr()

        assert "dry-run" in captured.out
        assert "--apply" in captured.out

    def test_apply_without_confirm_shows_hint(self, tmp_path, capsys):
        """apply=True 但 confirm=False 时显示提示，不修改数据库"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 1, NULL)")
        conn.commit()
        conn.close()

        # apply=True 但 confirm=False
        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=False)
        print_cleanup_report(result)

        captured = capsys.readouterr()

        # 不修改数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT raw_pwd FROM teacher WHERE teacher_id='t1'")
        assert cursor.fetchone()[0] == "pwd"
        conn.close()

        # 显示提示
        assert result["mode"] == "apply-needs-confirm"
        assert "需要确认" in captured.out
        assert "--yes" in captured.out

    def test_apply_with_confirm_executes_cleanup(self, tmp_path):
        """apply=True 且 confirm=True 时执行清理"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 1, NULL)")
        conn.commit()
        conn.close()

        # apply=True 且 confirm=True
        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)

        assert result["mode"] == "apply"
        assert result["cleanup_count"] == 1

        # 验证数据库已修改
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT raw_pwd FROM teacher WHERE teacher_id='t1'")
        assert cursor.fetchone()[0] is None
        conn.close()


class TestRecoveryCommand:
    """build_recovery_command 函数测试"""

    def test_recovery_command_format(self):
        """恢复命令格式正确"""
        backup_path = "/path/to/moral.db.raw_pwd_backup.20260503_085500"
        db_path = "/path/to/moral.db"

        cmd = build_recovery_command(backup_path, db_path)

        assert cmd == "cp /path/to/moral.db.raw_pwd_backup.20260503_085500 /path/to/moral.db"
        assert "cp" in cmd
        assert backup_path in cmd
        assert db_path in cmd

    def test_recovery_command_quotes_paths_with_spaces(self):
        """恢复命令会安全引用包含空格的路径。"""
        backup_path = "/tmp/db backups/moral db.raw_pwd_backup.20260503_085500"
        db_path = "/tmp/live db/moral db.sqlite"

        cmd = build_recovery_command(backup_path, db_path)

        assert cmd == "cp '/tmp/db backups/moral db.raw_pwd_backup.20260503_085500' '/tmp/live db/moral db.sqlite'"

    def test_recovery_command_in_result(self, tmp_path):
        """apply 成功后结果中包含恢复命令"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 1, NULL)")
        conn.commit()
        conn.close()

        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)

        assert result["recovery_command"] is not None
        assert "cp" in result["recovery_command"]
        assert str(tmp_path) in result["recovery_command"]

    def test_recovery_command_shown_in_report(self, tmp_path, capsys):
        """报告中显示恢复命令"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                raw_pwd TEXT,
                is_password_changed INTEGER,
                updated_at TEXT
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', 'pwd', 1, NULL)")
        conn.commit()
        conn.close()

        result = cleanup_changed_raw_pwd(db_path, apply=True, confirm=True)
        print_cleanup_report(result)

        captured = capsys.readouterr()

        assert "恢复命令" in captured.out
        assert "cp" in captured.out


class TestIntegration:
    """集成测试"""

    def test_cleanup_on_real_moral_db_dry_run(self):
        """在真实 moral.db 上执行 dry-run（如果存在）"""
        from utils.db_config import MORAL_DB

        if not os.path.exists(MORAL_DB):
            pytest.skip("真实数据库不存在")

        result = cleanup_changed_raw_pwd(MORAL_DB, apply=False)

        assert result["mode"] == "dry-run"
        # dry-run 不应修改数据库，所以可以安全执行
        assert "error" not in result or result.get("db_exists") is False
