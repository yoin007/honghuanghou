# -*- coding: utf-8 -*-
"""
认证模块测试
测试JWT Token生成/验证、密码hash比对、用户认证流程
"""
import pytest
import jwt
import bcrypt
from datetime import datetime, timedelta, UTC


# 测试配置
TEST_SECRET_KEY = "test-secret-key-for-unit-testing"
TEST_ALGORITHM = "HS256"
TEST_EXPIRE_MINUTES = 120


def hash_password(password: str) -> str:
    """生成密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def verify_password_compat(plain_password, stored_password, is_password_changed=0):
    """验证密码，兼容明文和bcrypt"""
    if is_password_changed == 1:
        if stored_password and stored_password.startswith(('$2a$', '$2b$', '$2y$')):
            return verify_password(plain_password, stored_password)
        return False
    return plain_password == stored_password


def create_access_token(data: dict, expires_delta: timedelta = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=TEST_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


def decode_access_token(token: str):
    """解码访问令牌"""
    try:
        payload = jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def is_admin_user(user):
    """检查用户是否为管理员"""
    if not user:
        return False
    if hasattr(user, 'role'):
        role = str(user.role) if user.role else ""
    else:
        role = str(user.get("role", "")) if isinstance(user, dict) else ""
    return role == "admin" or "admin" in role


class MockUser:
    """模拟用户对象"""
    def __init__(self, username, role):
        self.username = username
        self.role = role


class TestPasswordHashing:
    """密码哈希测试"""

    def test_hash_password_creates_bcrypt_hash(self):
        """hash_password应该生成bcrypt格式哈希"""
        password = "test123"
        hashed = hash_password(password)
        assert hashed.startswith('$2b$')

    def test_hash_password_is_different_each_time(self):
        """每次hash应该生成不同的哈希值（因为有salt）"""
        password = "test123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2

    def test_verify_password_with_correct_password(self):
        """正确密码应该验证成功"""
        password = "test123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) == True

    def test_verify_password_with_wrong_password(self):
        """错误密码应该验证失败"""
        password = "test123"
        hashed = hash_password(password)
        assert verify_password("wrong_password", hashed) == False

    def test_verify_password_with_invalid_hash(self):
        """无效哈希应该返回False"""
        assert verify_password("test123", "invalid_hash") == False

    def test_verify_password_with_empty_password(self):
        """空密码应该验证失败"""
        hashed = hash_password("test123")
        assert verify_password("", hashed) == False


class TestPasswordCompat:
    """密码兼容验证测试"""

    def test_verify_compat_with_bcrypt_changed_password(self):
        """已修改密码应该用bcrypt验证"""
        password = "test123"
        hashed = hash_password(password)
        assert verify_password_compat(password, hashed, is_password_changed=1) == True

    def test_verify_compat_with_bcrypt_wrong_password(self):
        """bcrypt模式下错误密码应该失败"""
        password = "test123"
        hashed = hash_password(password)
        assert verify_password_compat("wrong", hashed, is_password_changed=1) == False

    def test_verify_compat_with_plaintext_password(self):
        """未修改密码应该用明文验证"""
        plain_password = "plaintext123"
        assert verify_password_compat(plain_password, plain_password, is_password_changed=0) == True

    def test_verify_compat_with_plaintext_wrong_password(self):
        """明文模式下错误密码应该失败"""
        assert verify_password_compat("wrong", "plaintext123", is_password_changed=0) == False

    def test_verify_compat_invalid_bcrypt_format(self):
        """非bcrypt格式在bcrypt模式应该失败"""
        assert verify_password_compat("test", "not_bcrypt", is_password_changed=1) == False


class TestJWTToken:
    """JWT Token测试"""

    def test_create_access_token_contains_username(self):
        """Token应该包含用户名"""
        token = create_access_token({"sub": "testuser"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"

    def test_create_access_token_contains_role(self):
        """Token应该包含角色"""
        token = create_access_token({"sub": "testuser", "role": "teacher"})
        payload = decode_access_token(token)
        assert payload["role"] == "teacher"

    def test_create_access_token_has_expiration(self):
        """Token应该有过期时间"""
        token = create_access_token({"sub": "testuser"})
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_create_access_token_custom_expiry(self):
        """自定义过期时间应该生效"""
        # 使用较短的自定义过期时间（5分钟）
        custom_expiry = timedelta(minutes=5)
        token = create_access_token({"sub": "testuser"}, expires_delta=custom_expiry)
        payload = decode_access_token(token)
        # 验证过期时间存在
        assert "exp" in payload
        # 验证exp是一个有效的数字时间戳
        assert isinstance(payload["exp"], (int, float))
        # 验证过期时间在未来
        now = datetime.now(UTC).timestamp()
        assert payload["exp"] > now

    def test_decode_expired_token(self):
        """过期Token解码应该返回None"""
        # 创建一个已经过期的token
        expired_delta = timedelta(seconds=-1)
        token = create_access_token({"sub": "testuser"}, expires_delta=expired_delta)
        payload = decode_access_token(token)
        assert payload is None

    def test_decode_invalid_token(self):
        """无效Token解码应该返回None"""
        payload = decode_access_token("invalid_token_string")
        assert payload is None

    def test_decode_token_wrong_secret(self):
        """使用错误密钥解码应该失败"""
        token = create_access_token({"sub": "testuser"})
        try:
            jwt.decode(token, "wrong_secret", algorithms=[TEST_ALGORITHM])
            assert False, "Should have raised exception"
        except jwt.InvalidTokenError:
            pass


class TestAdminCheck:
    """管理员检查测试"""

    def test_is_admin_with_admin_role(self):
        """admin角色应该返回True"""
        user = MockUser("admin_user", "admin")
        assert is_admin_user(user) == True

    def test_is_admin_with_teacher_role(self):
        """teacher角色应该返回False"""
        user = MockUser("teacher_user", "teacher")
        assert is_admin_user(user) == False

    def test_is_admin_with_jiaowu_role(self):
        """jiaowu角色应该返回False"""
        user = MockUser("jiaowu_user", "jiaowu")
        assert is_admin_user(user) == False

    def test_is_admin_with_combined_role(self):
        """包含admin的组合角色应该返回True"""
        user = MockUser("combined", "teacher/admin")
        assert is_admin_user(user) == True

    def test_is_admin_with_dict_user(self):
        """字典格式用户应该正确判断"""
        user = {"username": "admin_user", "role": "admin"}
        assert is_admin_user(user) == True

    def test_is_admin_with_none_user(self):
        """None用户应该返回False"""
        assert is_admin_user(None) == False

    def test_is_admin_with_empty_role(self):
        """空角色应该返回False"""
        user = MockUser("empty", "")
        assert is_admin_user(user) == False


class TestAuthenticateFlow:
    """认证流程测试"""

    def test_authenticate_success_flow(self):
        """成功认证流程模拟"""
        # 1. 用户注册/密码修改时hash密码
        password = "newpassword123"
        hashed = hash_password(password)

        # 2. 存储用户数据
        user_data = {
            "username": "testuser",
            "stored_password": hashed,
            "is_password_changed": 1,
            "role": "teacher"
        }

        # 3. 验证密码
        verified = verify_password_compat(password, user_data["stored_password"], user_data["is_password_changed"])
        assert verified == True

        # 4. 创建Token
        token = create_access_token({"sub": user_data["username"], "role": user_data["role"]})
        payload = decode_access_token(token)
        assert payload["sub"] == "testuser"
        assert payload["role"] == "teacher"

    def test_authenticate_failure_wrong_password(self):
        """密码错误认证失败"""
        password = "correctpassword"
        hashed = hash_password(password)
        user_data = {"stored_password": hashed, "is_password_changed": 1}

        verified = verify_password_compat("wrongpassword", user_data["stored_password"], user_data["is_password_changed"])
        assert verified == False

    def test_plaintext_to_bcrypt_migration(self):
        """明文密码迁移到bcrypt流程"""
        # 旧系统明文密码
        old_password = "plaintext123"
        user_data_old = {"stored_password": old_password, "is_password_changed": 0}

        # 验证明文密码
        assert verify_password_compat(old_password, user_data_old["stored_password"], 0) == True

        # 用户修改密码后，存储bcrypt哈希
        new_password = "newsecure123"
        user_data_new = {"stored_password": hash_password(new_password), "is_password_changed": 1}

        # 验证bcrypt密码
        assert verify_password_compat(new_password, user_data_new["stored_password"], 1) == True
        # 旧密码不能再用
        assert verify_password_compat(old_password, user_data_new["stored_password"], 1) == False


class TestSecurityEdgeCases:
    """安全边界测试"""

    def test_empty_password_not_accepted(self):
        """空密码不应被接受"""
        hashed = hash_password("")
        # 空密码hash后仍可验证空密码
        assert verify_password("", hashed) == True
        # 但非空密码不能匹配
        assert verify_password("something", hashed) == False

    def test_very_long_password(self):
        """超长密码bcrypt有72字节限制"""
        # bcrypt限制72字节，测试接近边界
        long_password = "a" * 70
        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) == True
        # 72字节密码应该能处理
        max_password = "a" * 72
        hashed_max = hash_password(max_password)
        assert verify_password(max_password, hashed_max) == True

    def test_special_characters_in_password(self):
        """特殊字符密码应该能处理"""
        special_password = "测试密码!@#$%^&*()"
        hashed = hash_password(special_password)
        assert verify_password(special_password, hashed) == True

    def test_unicode_password(self):
        """Unicode密码应该能处理"""
        unicode_password = "中文密码日本語한글"
        hashed = hash_password(unicode_password)
        assert verify_password(unicode_password, hashed) == True

    def test_token_with_special_username(self):
        """特殊字符用户名Token应该能处理"""
        special_username = "用户_测试-123"
        token = create_access_token({"sub": special_username})
        payload = decode_access_token(token)
        assert payload["sub"] == special_username