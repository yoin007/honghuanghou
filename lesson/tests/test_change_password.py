# -*- coding: utf-8 -*-
"""自助修改密码 API 测试

回归覆盖：
- POST /api/teachers/change-password 全角色开放（含管理员自助改密）
- 旧密码校验（bcrypt 与明文兼容两条路径）
- 新密码强度（pydantic Field 6-64 位）
- 审计落库调用且不记录密码内容

打桩模式与 test_student_scores.py 一致。
"""
import sys
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

# 本机 zai 包为占位版本（缺 ZhipuAiClient），注入 mock 保证 import main 可用；
# 环境中已装正确 zai-sdk 时不受影响
_zai = sys.modules.get('zai')
if _zai is None or not hasattr(_zai, 'ZhipuAiClient'):
    sys.modules['zai'] = MagicMock(ZhipuAiClient=MagicMock())


@pytest.fixture(scope="module", autouse=True)
def mock_task_init():
    """Mock Task 类的初始化，避免在测试中连接真实数据库"""
    with patch('models.task.Task.__init__', return_value=None):
        with patch('models.task.task_scheduler', None):
            yield


def create_mock_user(role='teacher', username='zhangsan'):
    from models.datas_api.auth import User
    return User(username=username, role=role)


def real_hash(password: str) -> str:
    from models.datas_api.auth import hash_password
    return str(hash_password(password))


class TestChangePassword:
    @pytest.fixture
    def client(self):
        from main import app
        from models.datas_api.auth import get_current_user, get_current_user_optional

        mock_user = create_mock_user()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_user_optional] = lambda: mock_user
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def _patches(self, users):
        """统一打桩：权限放行 + 用户数据 + 写入与审计记录

        返回 (上下文管理器列表, update_mock, log_mock)。
        """
        update_mock = MagicMock()
        log_mock = MagicMock()
        patches = [
            patch('models.datas_api.moral.api_permission.check_configured_api_permission',
                  return_value={"allowed": True, "reason": "测试放行", "policy": {}, "config": {}}),
            patch('models.datas_api.teachers.get_users_dict', return_value=users),
            patch('models.datas_api.teachers.update_teacher_record', update_mock),
            patch('models.datas_api.teachers.log_operation', log_mock),
            patch('models.datas_api.teachers.SQLiteMoralDatabase', MagicMock()),
        ]
        return patches, update_mock, log_mock

    def test_change_password_bcrypt_path(self, client):
        """is_password_changed=1 时按 bcrypt 验旧密码，新密码落哈希并审计"""
        users = {'zhangsan': {
            'stored_password': real_hash('OldPass123'),
            'is_password_changed': 1,
        }}
        patches, update_mock, log_mock = self._patches(users)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/teachers/change-password', json={
                'old_password': 'OldPass123',
                'new_password': 'NewPass456',
            })

        assert resp.status_code == 200
        # 写入的是 bcrypt 哈希且标记已改密
        args, kwargs = update_mock.call_args
        assert args[0] == 'zhangsan'
        assert str(kwargs['pwd']).startswith('$2')
        assert kwargs['is_password_changed'] == 1
        # 审计只记操作人与操作，不含任何密码内容
        log_args, log_kwargs = log_mock.call_args
        all_values = [str(v) for v in log_args] + [str(v) for v in log_kwargs.values()]
        joined = ' '.join(all_values)
        assert '修改密码' in joined
        assert 'OldPass123' not in joined and 'NewPass456' not in joined

    def test_change_password_legacy_plaintext_path(self, client):
        """is_password_changed=0 的存量账号按明文验证旧密码"""
        users = {'zhangsan': {
            'stored_password': 'plainold123',
            'is_password_changed': 0,
        }}
        patches, update_mock, log_mock = self._patches(users)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/teachers/change-password', json={
                'old_password': 'plainold123',
                'new_password': 'NewPass456',
            })

        assert resp.status_code == 200
        args, kwargs = update_mock.call_args
        assert args[0] == 'zhangsan'
        assert str(kwargs['pwd']).startswith('$2')

    def test_wrong_old_password_rejected(self, client):
        """旧密码错误返回 400，不写库不审计"""
        users = {'zhangsan': {
            'stored_password': real_hash('OldPass123'),
            'is_password_changed': 1,
        }}
        patches, update_mock, log_mock = self._patches(users)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/teachers/change-password', json={
                'old_password': 'WrongOld999',
                'new_password': 'NewPass456',
            })

        assert resp.status_code == 400
        assert '旧密码错误' in resp.json()['detail']
        update_mock.assert_not_called()
        log_mock.assert_not_called()

    def test_short_new_password_rejected(self, client):
        """新密码不足 6 位被请求模型拒绝（422），不触发写入"""
        users = {'zhangsan': {
            'stored_password': real_hash('OldPass123'),
            'is_password_changed': 1,
        }}
        patches, update_mock, log_mock = self._patches(users)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/teachers/change-password', json={
                'old_password': 'OldPass123',
                'new_password': '123',
            })

        assert resp.status_code == 422
        update_mock.assert_not_called()

    def test_overlong_new_password_rejected(self, client):
        """新密码超过 64 位被拒绝，防 bcrypt 静默截断"""
        users = {'zhangsan': {
            'stored_password': real_hash('OldPass123'),
            'is_password_changed': 1,
        }}
        patches, update_mock, log_mock = self._patches(users)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/teachers/change-password', json={
                'old_password': 'OldPass123',
                'new_password': 'x' * 65,
            })

        assert resp.status_code == 422
        update_mock.assert_not_called()

    def test_admin_can_self_change(self, client):
        """回归：管理员也可自助改密（原端点拒绝管理员）"""
        from main import app
        from models.datas_api.auth import get_current_user, get_current_user_optional

        admin_user = create_mock_user(role='admin', username='admin')
        app.dependency_overrides[get_current_user] = lambda: admin_user
        app.dependency_overrides[get_current_user_optional] = lambda: admin_user
        try:
            users = {'admin': {
                'stored_password': real_hash('AdminOld1'),
                'is_password_changed': 1,
            }}
            patches, update_mock, log_mock = self._patches(users)
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                resp = client.post('/api/teachers/change-password', json={
                    'old_password': 'AdminOld1',
                    'new_password': 'AdminNew1',
                })

            assert resp.status_code == 200
            args, _ = update_mock.call_args
            assert args[0] == 'admin'
        finally:
            app.dependency_overrides.clear()
