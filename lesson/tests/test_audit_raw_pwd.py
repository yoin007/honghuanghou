"""
raw_pwd 审计脚本测试

Batch 7 第一阶段验收：审计脚本只读、不输出明文、统计准确
"""
import pytest
import sqlite3
import os
from scripts.audit_raw_pwd import audit_raw_pwd_status, print_audit_report


class TestAuditRawPwd:
    """审计脚本测试"""

    def test_audit_returns_dict_with_expected_keys(self, tmp_path):
        """返回结果包含预期字段"""
        db_path = str(tmp_path / "moral.db")

        # 创建空数据库
        conn = sqlite3.connect(db_path)
        conn.close()

        result = audit_raw_pwd_status(db_path)

        expected_keys = [
            "teacher_total",
            "raw_pwd_non_empty",
            "changed_with_raw_pwd",
            "unchanged_with_raw_pwd",
            "changed_without_raw_pwd",
            "unchanged_without_raw_pwd",
            "db_exists",
            "table_exists",
            "has_required_columns",
        ]

        for key in expected_keys:
            assert key in result

    def test_audit_db_not_exists_returns_zeros(self, tmp_path):
        """数据库不存在时返回全零"""
        db_path = str(tmp_path / "nonexistent.db")

        result = audit_raw_pwd_status(db_path)

        assert result["db_exists"] is False
        assert result["teacher_total"] == 0
        assert result["raw_pwd_non_empty"] == 0

    def test_audit_table_not_exists_returns_zeros(self, tmp_path):
        """teacher 表不存在时返回全零"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        # 创建其他表但不创建 teacher 表
        conn.execute("CREATE TABLE other_table (id INTEGER)")
        conn.close()

        result = audit_raw_pwd_status(db_path)

        assert result["db_exists"] is True
        assert result["table_exists"] is False
        assert result["teacher_total"] == 0

    def test_audit_table_missing_required_columns_returns_hint(self, tmp_path, capsys):
        """teacher 表缺少审计字段时返回可读提示，不抛异常。"""
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

        result = audit_raw_pwd_status(db_path)
        print_audit_report(result)
        captured = capsys.readouterr()

        assert result["db_exists"] is True
        assert result["table_exists"] is True
        assert result["has_required_columns"] is False
        assert result["teacher_total"] == 0
        assert "缺少审计字段" in captured.out

    def test_audit_counts_teacher_records(self, tmp_path):
        """正确统计教师记录数"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                password_hash TEXT,
                raw_pwd TEXT,
                is_password_changed INTEGER DEFAULT 0
            )
        """)

        # 插入测试数据
        conn.execute("INSERT INTO teacher VALUES ('t1', '张老师', 'hash1', 'pwd1', 1)")
        conn.execute("INSERT INTO teacher VALUES ('t2', '李老师', 'hash2', 'pwd2', 0)")
        conn.execute("INSERT INTO teacher VALUES ('t3', '王老师', 'hash3', NULL, 1)")
        conn.execute("INSERT INTO teacher VALUES ('t4', '刘老师', 'hash4', '', 1)")
        conn.commit()
        conn.close()

        result = audit_raw_pwd_status(db_path)

        assert result["teacher_total"] == 4
        assert result["raw_pwd_non_empty"] == 2
        assert result["changed_with_raw_pwd"] == 1  # 张老师
        assert result["unchanged_with_raw_pwd"] == 1  # 李老师
        assert result["changed_without_raw_pwd"] == 2  # 王老师、刘老师

    def test_audit_handles_empty_raw_pwd(self, tmp_path):
        """正确处理空 raw_pwd"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                password_hash TEXT,
                raw_pwd TEXT,
                is_password_changed INTEGER DEFAULT 0
            )
        """)

        # 各种空值情况
        conn.execute("INSERT INTO teacher VALUES ('t1', 'A', 'h', NULL, 1)")
        conn.execute("INSERT INTO teacher VALUES ('t2', 'B', 'h', '', 1)")
        conn.execute("INSERT INTO teacher VALUES ('t3', 'C', 'h', '   ', 0)")  # 空格不算空
        conn.commit()
        conn.close()

        result = audit_raw_pwd_status(db_path)

        # 空格字符串不算空
        assert result["raw_pwd_non_empty"] == 1  # 只有空格那条
        assert result["changed_with_raw_pwd"] == 0
        assert result["unchanged_with_raw_pwd"] == 1

    def test_audit_does_not_output_plain_password(self, tmp_path, capsys):
        """打印报告不输出明文密码"""
        db_path = str(tmp_path / "moral.db")

        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE teacher (
                teacher_id TEXT PRIMARY KEY,
                name TEXT,
                password_hash TEXT,
                raw_pwd TEXT,
                is_password_changed INTEGER DEFAULT 0
            )
        """)
        conn.execute("INSERT INTO teacher VALUES ('t1', '测试', 'h', 'secret_password_123', 1)")
        conn.commit()
        conn.close()

        result = audit_raw_pwd_status(db_path)
        print_audit_report(result)

        captured = capsys.readouterr()

        # 不应包含真实密码
        assert "secret_password_123" not in captured.out
        # 应包含数量
        assert "changed=1 且 raw_pwd 非空: 1" in captured.out

    def test_audit_on_real_moral_db(self):
        """在真实 moral.db 上执行审计（如果存在）"""
        from utils.db_config import MORAL_DB

        result = audit_raw_pwd_status(MORAL_DB)

        # 数据库可能不存在（测试环境）
        if result["db_exists"] and result["table_exists"]:
            # 如果存在，验证统计逻辑
            assert result["teacher_total"] >= 0
            # 验证分组统计一致性
            total_with_raw = result["changed_with_raw_pwd"] + result["unchanged_with_raw_pwd"]
            total_without_raw = result["changed_without_raw_pwd"] + result["unchanged_without_raw_pwd"]
            # 总数应该等于各分组之和
            assert result["teacher_total"] == total_with_raw + total_without_raw

    def test_audit_closes_connection_when_query_fails(self, tmp_path, monkeypatch):
        """查询异常时也关闭数据库连接。"""
        db_path = str(tmp_path / "moral.db")
        open(db_path, "w").close()
        closed = {"value": False}

        class FailingConnection:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                closed["value"] = True

            def execute(self, *_args, **_kwargs):
                raise RuntimeError("query failed")

        monkeypatch.setattr(
            "scripts.audit_raw_pwd.sqlite3.connect",
            lambda _db_path: FailingConnection(),
        )

        result = audit_raw_pwd_status(db_path)

        assert "query failed" in result["error"]
        assert closed["value"] is True
