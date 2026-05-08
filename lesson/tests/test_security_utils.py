"""
安全工具测试：验证 hash_password / verify_password 行为一致

Batch 5 第二阶段验收：密码函数从 auth 模块统一导入
"""
import pytest


class TestSecurityUtils:
    """密码安全工具测试"""

    def test_hash_password_returns_non_plain(self):
        """哈希结果不应是明文"""
        from models.datas_api.auth import hash_password

        password = "test_password_123"
        hashed = hash_password(password)

        # 哈希结果不应等于明文
        assert hashed != password
        # bcrypt 哈希应以 $2 开头
        assert hashed.startswith("$2")

    def test_verify_password_correct(self):
        """正确密码验证返回 True"""
        from models.datas_api.auth import hash_password, verify_password

        password = "correct_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_wrong(self):
        """错误密码验证返回 False"""
        from models.datas_api.auth import hash_password, verify_password

        password = "correct_password"
        hashed = hash_password(password)

        assert verify_password("wrong_password", hashed) is False

    def test_legacy_import_same_as_auth(self):
        """legacy 导入的函数与 auth 实现行为一致"""
        from models.datas_api.auth import hash_password as auth_hash
        from models.datas_api.auth import verify_password as auth_verify
        from models.datas_api_legacy import hash_password as legacy_hash
        from models.datas_api_legacy import verify_password as legacy_verify

        # 两处导入应指向同一个函数对象
        assert auth_hash is legacy_hash
        assert auth_verify is legacy_verify

    def test_verify_password_compat_works(self):
        """verify_password_compat 正确处理已修改密码"""
        from models.datas_api_legacy import verify_password_compat
        from models.datas_api.auth import hash_password

        # 已修改密码（bcrypt 哈希）
        password = "secure_password"
        hashed = hash_password(password)

        # is_password_changed=1 应使用 bcrypt 验证
        assert verify_password_compat(password, hashed, is_password_changed=1) is True
        assert verify_password_compat("wrong", hashed, is_password_changed=1) is False

    def test_verify_password_compat_plain(self):
        """verify_password_compat 正确处理未修改密码（明文）"""
        from models.datas_api_legacy import verify_password_compat

        # 未修改密码（明文存储）
        plain_password = "plain_text_password"

        # is_password_changed=0 应使用明文验证
        assert verify_password_compat(plain_password, plain_password, is_password_changed=0) is True
        assert verify_password_compat("wrong", plain_password, is_password_changed=0) is False

    def test_authenticate_changed_user_uses_hash_not_raw_pwd(self, monkeypatch):
        """已改密用户登录只使用 password_hash，不依赖 raw_pwd。"""
        from models.datas_api import auth

        password = "changed_password"
        hashed = auth.hash_password(password)

        monkeypatch.setattr(
            auth,
            "get_teacher_by_name",
            lambda _name: {
                "name": "张老师",
                "pwd": hashed,
                "raw_pwd": "old_plain_password",
                "is_password_changed": 1,
                "active": 1,
            },
        )

        assert auth.authenticate_user("张老师", password)["name"] == "张老师"
        assert auth.authenticate_user("张老师", "old_plain_password") is False

    def test_authenticate_changed_user_accepts_string_flag(self, monkeypatch):
        """is_password_changed 字符串值也应按已改密处理。"""
        from models.datas_api import auth

        password = "changed_password"
        hashed = auth.hash_password(password)

        monkeypatch.setattr(
            auth,
            "get_teacher_by_name",
            lambda _name: {
                "name": "赵老师",
                "pwd": hashed,
                "raw_pwd": "old_plain_password",
                "is_password_changed": "1",
                "active": 1,
            },
        )

        assert auth.authenticate_user("赵老师", password)["name"] == "赵老师"
        assert auth.authenticate_user("赵老师", "old_plain_password") is False

    def test_authenticate_unchanged_user_prefers_raw_pwd(self, monkeypatch):
        """未改密用户登录优先使用 raw_pwd，保留历史兼容。"""
        from models.datas_api import auth

        monkeypatch.setattr(
            auth,
            "get_teacher_by_name",
            lambda _name: {
                "name": "李老师",
                "pwd": "stale_or_hashed_value",
                "raw_pwd": "legacy_plain_password",
                "is_password_changed": 0,
                "active": 1,
            },
        )

        assert auth.authenticate_user("李老师", "legacy_plain_password")["name"] == "李老师"
        assert auth.authenticate_user("李老师", "stale_or_hashed_value") is False

    def test_get_users_dict_uses_raw_pwd_for_unchanged_users(self, monkeypatch):
        """用户字典中的未改密账号也应使用 raw_pwd 作为兼容密码。"""
        from models.datas_api import auth

        monkeypatch.setattr(
            auth,
            "get_all_teachers",
            lambda: [
                {
                    "name": "王老师",
                    "pwd": "stale_or_hashed_value",
                    "raw_pwd": "legacy_plain_password",
                    "is_password_changed": 0,
                    "active": 1,
                }
            ],
        )

        users = auth.get_users_dict()

        assert users["王老师"]["stored_password"] == "legacy_plain_password"

    def test_get_users_dict_string_changed_flag_uses_hash(self, monkeypatch):
        """用户字典中的字符串改密状态也必须使用 hash 字段。"""
        from models.datas_api import auth

        hashed = auth.hash_password("changed_password")
        monkeypatch.setattr(
            auth,
            "get_all_teachers",
            lambda: [
                {
                    "name": "钱老师",
                    "pwd": hashed,
                    "raw_pwd": "legacy_plain_password",
                    "is_password_changed": "1",
                    "active": 1,
                }
            ],
        )

        users = auth.get_users_dict()

        assert users["钱老师"]["stored_password"] == hashed

    def test_empty_password_handling(self):
        """空密码处理"""
        from models.datas_api.auth import hash_password, verify_password

        # 空密码也能哈希
        hashed = hash_password("")
        assert hashed.startswith("$2")
        assert verify_password("", hashed) is True

    def test_teacher_directory_add_teacher_does_not_write_raw_pwd(self, monkeypatch):
        """教师目录新增默认账号时不再写入 raw_pwd。"""
        from models.lesson import teacher_directory

        captured = {}

        def fake_create_teacher_record(**kwargs):
            captured.update(kwargs)

        def fake_update_teacher_record(*args, **kwargs):
            captured["updated_wxid"] = kwargs.get("wxid")

        monkeypatch.setattr(teacher_directory, "create_teacher_record", fake_create_teacher_record)
        monkeypatch.setattr(teacher_directory, "update_teacher_record", fake_update_teacher_record)

        directory = teacher_directory.TeacherDirectory()
        assert directory.add_teacher("wx-1", "张老师", "语文") == "OK"

        assert "raw_pwd" not in captured
        assert captured["password_hash"] == "666666"
        assert captured["is_password_changed"] == 0
        assert captured["updated_wxid"] == "wx-1"
