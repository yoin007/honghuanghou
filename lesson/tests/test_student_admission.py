# -*- coding: utf-8 -*-
"""毕业学生录取信息（批量导入/更新）API 测试"""
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


def create_mock_user(role='admin', username='test_admin'):
    from models.datas_api.auth import User
    return User(username=username, role=role)


class FakeDb:
    """模拟 moral.db：只实现录取导入路径用到的接口"""

    def __init__(self, students=None):
        self.students = students or {}  # student_id -> dict
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def query_one(self, sql, params=()):
        if 'FROM student' in sql:
            return self.students.get(params[0])
        return None

    def query_all(self, sql, params=()):
        return []

    def execute(self, sql, params=()):
        self.executed.append((sql.strip(), params))


class TestAdmissionBatchImport:
    @pytest.fixture
    def client(self):
        from main import app
        from models.datas_api.auth import get_current_user, get_current_user_optional

        mock_user = create_mock_user()
        # 权限依赖链走 get_current_user_optional，两个都要覆盖
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_user_optional] = lambda: mock_user
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def _patches(self, db):
        """统一打桩：权限放行 + 数据库替换"""
        return [
            patch('models.datas_api.moral.api_permission.check_configured_api_permission',
                  return_value={"allowed": True, "reason": "测试放行", "policy": {}, "config": {}}),
            patch('models.datas_api.moral.admin._has_scoped_permission', return_value=True),
            patch('models.datas_api.moral.admin._student_manage_scope',
                  return_value={"can_all": True}),
            patch('models.datas_api.moral.admin.get_moral_db', return_value=db),
            patch('models.datas_api.moral.admin.log_operation'),
        ]

    def test_updates_only_admission_columns(self, client):
        """毕业学生：只更新录取两列，不碰其他字段"""
        db = FakeDb(students={
            '20220101': {'student_id': '20220101', 'name': '张三', 'status': '毕业'}
        })
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/moral/admin/students/admission-batch', json={
                'students': [{'student_id': '20220101', 'name': '张三',
                              'university_name': '浙江大学', 'university_major': '计算机科学与技术'}]
            })

        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['success_count'] == 1
        assert data['error_count'] == 0
        # 只更新两列
        assert len(db.executed) == 1
        sql, params = db.executed[0]
        assert 'university_name = ?' in sql and 'university_major = ?' in sql
        assert params == ('浙江大学', '计算机科学与技术', '20220101')

    def test_rejects_non_graduate_student(self, client):
        """非毕业状态学生被拒绝并计入 errors"""
        db = FakeDb(students={
            '20230101': {'student_id': '20230101', 'name': '李四', 'status': '在校'},
            '20220102': {'student_id': '20220102', 'name': '王五', 'status': '转出'},
        })
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/moral/admin/students/admission-batch', json={
                'students': [
                    {'student_id': '20230101', 'name': '李四', 'university_name': '浙江大学'},
                    {'student_id': '20220102', 'name': '王五', 'university_name': '浙江大学'},
                ]
            })

        data = resp.json()['data']
        assert data['success_count'] == 0
        assert data['error_count'] == 2
        assert any('非毕业状态' in e for e in data['errors'])
        assert db.executed == []

    def test_name_mismatch_goes_to_errors(self, client):
        """姓名与系统不符时拒绝写入（防 Excel 行错位）"""
        db = FakeDb(students={
            '20220101': {'student_id': '20220101', 'name': '张三', 'status': '毕业'}
        })
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/moral/admin/students/admission-batch', json={
                'students': [{'student_id': '20220101', 'name': '张四', 'university_name': '浙江大学'}]
            })

        data = resp.json()['data']
        assert data['success_count'] == 0
        assert any('姓名不匹配' in e for e in data['errors'])
        assert db.executed == []

    def test_student_not_found(self, client):
        """学号不存在计入 errors"""
        db = FakeDb()
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/moral/admin/students/admission-batch', json={
                'students': [{'student_id': '99990101', 'name': '赵六', 'university_name': '浙江大学'}]
            })

        data = resp.json()['data']
        assert data['success_count'] == 0
        assert any('学生不存在' in e for e in data['errors'])

    def test_not_in_library_reported_without_blocking(self, client):
        """库外院校/专业照常入库，但在 not_in_library 中提示核对"""
        db = FakeDb(students={
            '20220101': {'student_id': '20220101', 'name': '张三', 'status': '毕业'}
        })
        fake_colleges_db = MagicMock()
        fake_colleges_db.query_all.side_effect = [
            [{'school_name': '浙江大学'}],   # schools 表
            [{'zymc': '计算机科学与技术'}],  # zyk 表
        ]
        fake_colleges_db.__enter__ = lambda s: s
        fake_colleges_db.__exit__ = lambda s, *a: False

        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], \
             patch('models.datas_api.moral.admin.MoralDatabase', return_value=fake_colleges_db):
            resp = client.post('/api/moral/admin/students/admission-batch', json={
                'students': [
                    {'student_id': '20220101', 'name': '张三',
                     'university_name': '浙工大', 'university_major': '软件工程'}
                ]
            })

        data = resp.json()['data']
        assert data['success_count'] == 1  # 不阻塞入库
        assert data['not_in_library']['schools'] == ['浙工大']
        assert data['not_in_library']['majors'] == ['软件工程']

    def test_forbidden_without_manage_scope(self, client):
        """无全量学生管理权限（如班主任）返回 403"""
        db = FakeDb()
        patches = self._patches(db)
        patches[2] = patch('models.datas_api.moral.admin._student_manage_scope',
                           return_value={"can_all": False})
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/moral/admin/students/admission-batch', json={
                'students': [{'student_id': '20220101', 'name': '张三', 'university_name': '浙江大学'}]
            })

        assert resp.status_code == 403
