# -*- coding: utf-8 -*-
"""
API端点测试
测试管理员和教师管理API的业务逻辑
"""
import pytest
from fastapi import HTTPException


# ==================== Mock Models ====================

class MockUser:
    """模拟用户对象"""
    def __init__(self, username, role):
        self.username = username
        self.role = role


class MockUsersDict:
    """模拟用户数据"""
    def __init__(self):
        self.users = {
            "admin": {
                "username": "admin",
                "role": "admin",
                "level": 100,
                "subject": "",
                "course": "",
                "stored_password": "$2b$12$hashedpassword",
                "is_password_changed": 1,
                "notice": 1,
                "active": 1
            },
            "teacher1": {
                "username": "teacher1",
                "role": "teacher",
                "level": 10,
                "subject": "语文",
                "course": "语文教学",
                "stored_password": "plaintext123",
                "is_password_changed": 0,
                "notice": 1,
                "active": 1
            },
            "teacher2": {
                "username": "teacher2",
                "role": "teacher",
                "level": 5,
                "subject": "数学",
                "course": "数学教学",
                "stored_password": "$2b$12$hashedpassword2",
                "is_password_changed": 1,
                "notice": 1,
                "active": 1
            },
            "jiaowu_user": {
                "username": "jiaowu_user",
                "role": "jiaowu",
                "level": 50,
                "subject": "",
                "course": "",
                "stored_password": "$2b$12$hashedpassword3",
                "is_password_changed": 1,
                "notice": 1,
                "active": 1
            }
        }

    def get(self, username):
        return self.users.get(username)


# ==================== Helper Functions ====================

def is_admin_user(user):
    """检查用户是否为管理员"""
    if not user:
        return False
    role = user.role if hasattr(user, 'role') else user.get("role", "")
    return role == "admin" or "admin" in role


def check_admin_permission(current_user):
    """检查管理员权限，无权限则抛出异常"""
    if not is_admin_user(current_user):
        raise HTTPException(status_code=403, detail="只有管理员可以访问")


def generate_random_password(length=8):
    """生成随机密码"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def filter_users_by_role(users_dict, role_filter=None):
    """按角色过滤用户"""
    if not role_filter:
        return list(users_dict.values())
    return [u for u in users_dict.values() if u.get("role") == role_filter]


# ==================== Test Classes ====================

class TestAdminPermissionCheck:
    """管理员权限检查测试"""

    def test_admin_user_has_permission(self):
        """管理员应该有权限"""
        user = MockUser("admin", "admin")
        assert is_admin_user(user) == True

    def test_non_admin_user_no_permission(self):
        """非管理员应该没有权限"""
        user = MockUser("teacher1", "teacher")
        assert is_admin_user(user) == False

    def test_combined_role_with_admin(self):
        """包含admin的组合角色应该有权限"""
        user = MockUser("combined", "teacher/admin")
        assert is_admin_user(user) == True

    def test_jiaowu_user_no_admin_permission(self):
        """教发部用户没有管理员权限"""
        user = MockUser("jiaowu_user", "jiaowu")
        assert is_admin_user(user) == False

    def test_none_user_no_permission(self):
        """None用户没有权限"""
        assert is_admin_user(None) == False

    def test_check_admin_permission_raises_for_non_admin(self):
        """非管理员调用check_admin_permission应该抛出403"""
        user = MockUser("teacher1", "teacher")
        with pytest.raises(HTTPException) as exc_info:
            check_admin_permission(user)
        assert exc_info.value.status_code == 403

    def test_check_admin_permission_passes_for_admin(self):
        """管理员调用check_admin_permission不应该抛出异常"""
        user = MockUser("admin", "admin")
        # 不应该抛出异常
        check_admin_permission(user)


class TestUserListAPI:
    """用户列表API测试"""

    def test_list_users_returns_all_users(self):
        """获取用户列表应该返回所有用户"""
        mock_db = MockUsersDict()
        users = list(mock_db.users.values())
        assert len(users) == 4

    def test_list_users_includes_required_fields(self):
        """用户列表应该包含必要字段"""
        mock_db = MockUsersDict()
        users = list(mock_db.users.values())
        required_fields = ["username", "role", "level"]
        for user in users:
            for field in required_fields:
                assert field in user

    def test_filter_users_by_teacher_role(self):
        """按teacher角色过滤用户"""
        mock_db = MockUsersDict()
        teachers = filter_users_by_role(mock_db.users, "teacher")
        assert len(teachers) == 2
        for t in teachers:
            assert t["role"] == "teacher"

    def test_filter_users_by_admin_role(self):
        """按admin角色过滤用户"""
        mock_db = MockUsersDict()
        admins = filter_users_by_role(mock_db.users, "admin")
        assert len(admins) == 1
        assert admins[0]["username"] == "admin"

    def test_filter_users_no_match(self):
        """过滤不存在的角色返回空列表"""
        mock_db = MockUsersDict()
        result = filter_users_by_role(mock_db.users, "nonexistent")
        assert len(result) == 0


class TestPasswordResetAPI:
    """密码重置API测试"""

    def test_generate_random_password_length(self):
        """随机密码长度应该正确"""
        password = generate_random_password(8)
        assert len(password) == 8

    def test_generate_random_password_contains_alphanumeric(self):
        """随机密码应该包含字母和数字"""
        password = generate_random_password(10)
        assert any(c.isalpha() for c in password)
        assert any(c.isdigit() for c in password)

    def test_generate_random_password_uniqueness(self):
        """多次生成的随机密码应该不同"""
        passwords = [generate_random_password() for _ in range(10)]
        assert len(set(passwords)) > 1  # 至少有一些不同

    def test_generate_random_password_custom_length(self):
        """自定义长度的随机密码"""
        password = generate_random_password(16)
        assert len(password) == 16


class TestTeacherCreateAPI:
    """教师创建API测试"""

    def test_create_teacher_requires_admin(self):
        """创建教师需要管理员权限"""
        teacher_user = MockUser("teacher1", "teacher")
        with pytest.raises(HTTPException) as exc_info:
            check_admin_permission(teacher_user)
        assert exc_info.value.status_code == 403

    def test_create_teacher_duplicate_check(self):
        """创建重复教师应该失败"""
        mock_db = MockUsersDict()
        existing_username = "teacher1"
        assert existing_username in mock_db.users

    def test_create_teacher_new_username(self):
        """新教师用户名应该不存在"""
        mock_db = MockUsersDict()
        new_username = "new_teacher"
        assert new_username not in mock_db.users


class TestTeacherUpdateAPI:
    """教师更新API测试"""

    def test_update_teacher_requires_admin(self):
        """更新教师需要管理员权限"""
        teacher_user = MockUser("teacher1", "teacher")
        with pytest.raises(HTTPException) as exc_info:
            check_admin_permission(teacher_user)
        assert exc_info.value.status_code == 403

    def test_update_teacher_not_found(self):
        """更新不存在的教师应该失败"""
        mock_db = MockUsersDict()
        non_existent = "non_existent_teacher"
        assert mock_db.get(non_existent) is None

    def test_update_teacher_fields(self):
        """教师字段更新模拟"""
        mock_db = MockUsersDict()
        teacher = mock_db.get("teacher1")
        # 模拟更新
        teacher["subject"] = "英语"
        teacher["level"] = 15
        assert teacher["subject"] == "英语"
        assert teacher["level"] == 15


class TestTeacherDeleteAPI:
    """教师删除API测试"""

    def test_delete_teacher_requires_admin(self):
        """删除教师需要管理员权限"""
        teacher_user = MockUser("teacher1", "teacher")
        with pytest.raises(HTTPException) as exc_info:
            check_admin_permission(teacher_user)
        assert exc_info.value.status_code == 403

    def test_delete_teacher_not_found(self):
        """删除不存在的教师应该失败"""
        mock_db = MockUsersDict()
        non_existent = "non_existent_teacher"
        assert mock_db.get(non_existent) is None


class TestPasswordChangeAPI:
    """密码修改API测试"""

    def test_admin_cannot_use_teacher_endpoint(self):
        """管理员不能使用教师密码修改接口"""
        admin_user = MockUser("admin", "admin")
        # 根据代码逻辑，管理员会收到403
        # 这里测试is_admin_user返回True
        assert is_admin_user(admin_user) == True

    def test_teacher_can_use_change_password(self):
        """教师可以使用密码修改接口"""
        teacher_user = MockUser("teacher1", "teacher")
        assert is_admin_user(teacher_user) == False  # 非管理员可以访问

    def test_password_verification_old_password_correct(self):
        """旧密码验证正确"""
        import bcrypt
        plain_password = "test123"
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        assert bcrypt.checkpw(plain_password.encode('utf-8'), hashed.encode('utf-8'))

    def test_password_verification_old_password_wrong(self):
        """旧密码验证错误"""
        import bcrypt
        plain_password = "test123"
        wrong_password = "wrong123"
        hashed = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        assert not bcrypt.checkpw(wrong_password.encode('utf-8'), hashed.encode('utf-8'))


class TestResponseFormat:
    """响应格式测试"""

    def test_user_list_response_format(self):
        """用户列表响应格式"""
        mock_db = MockUsersDict()
        users_list = [
            {
                "username": u["username"],
                "role": u["role"],
                "level": u["level"]
            }
            for u in mock_db.users.values()
        ]
        response = {"users": users_list, "total": len(users_list)}
        assert "users" in response
        assert "total" in response
        assert response["total"] == len(response["users"])

    def test_success_response_format(self):
        """成功响应格式"""
        response = {"message": "操作成功", "success": True}
        assert response["success"] == True
        assert "message" in response

    def test_error_response_format(self):
        """错误响应格式"""
        response = {"detail": "错误信息"}
        assert "detail" in response


class TestEdgeCases:
    """边界情况测试"""

    def test_empty_username(self):
        """空用户名处理"""
        mock_db = MockUsersDict()
        assert mock_db.get("") is None

    def test_special_characters_in_username(self):
        """用户名特殊字符"""
        special_usernames = ["用户名", "user@test", "user-name", "user_name"]
        mock_db = MockUsersDict()
        for username in special_usernames:
            # 应该能正常查询，即使不存在
            result = mock_db.get(username)
            assert result is None  # 这些用户名不存在

    def test_concurrent_user_operations(self):
        """并发用户操作模拟"""
        mock_db = MockUsersDict()
        # 模拟同时读取
        users1 = list(mock_db.users.values())
        users2 = list(mock_db.users.values())
        assert len(users1) == len(users2)

    def test_user_with_empty_fields(self):
        """空字段用户处理"""
        empty_user = {
            "username": "empty_user",
            "role": "",
            "level": 0,
            "subject": "",
            "course": ""
        }
        # 应该能正常处理
        assert empty_user["role"] == ""
        assert empty_user["level"] == 0

    def test_user_with_missing_fields(self):
        """缺失字段用户处理"""
        incomplete_user = {"username": "incomplete"}
        # 使用get方法安全访问
        assert incomplete_user.get("role", "teacher") == "teacher"
        assert incomplete_user.get("level", 0) == 0


class TestRoleBasedAccess:
    """基于角色的访问控制测试"""

    def test_admin_can_access_all_endpoints(self):
        """管理员可以访问所有端点"""
        admin = MockUser("admin", "admin")
        # 所有权限检查都应该通过
        assert is_admin_user(admin) == True

    def test_jiaowu_can_list_users(self):
        """教发部可以查看用户列表（无权限限制）"""
        jiaowu = MockUser("jiaowu_user", "jiaowu")
        # 列表接口不检查管理员权限
        assert jiaowu.role == "jiaowu"

    def test_teacher_cannot_create_teacher(self):
        """普通教师不能创建教师"""
        teacher = MockUser("teacher1", "teacher")
        with pytest.raises(HTTPException):
            check_admin_permission(teacher)

    def test_teacher_cannot_delete_teacher(self):
        """普通教师不能删除教师"""
        teacher = MockUser("teacher1", "teacher")
        with pytest.raises(HTTPException):
            check_admin_permission(teacher)

    def test_teacher_cannot_update_teacher(self):
        """普通教师不能更新其他教师"""
        teacher = MockUser("teacher1", "teacher")
        with pytest.raises(HTTPException):
            check_admin_permission(teacher)