# -*- coding: utf-8 -*-
"""学生档案字段（初中毕业学校/中考成绩/高考成绩）API 测试

复用 test_student_admission.py 的打桩模式：FakeDb 记录 SQL，
断言 UPDATE/INSERT 语句正确携带新列（含空串清空、None 跳过语义）。
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


def create_mock_user(role='admin', username='test_admin'):
    from models.datas_api.auth import User
    return User(username=username, role=role)


class FakeDb:
    """模拟 moral.db：覆盖更新/创建学生路径用到的查询"""

    def __init__(self, students=None):
        self.students = students or {}  # student_id -> dict
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def query_one(self, sql, params=()):
        if 'FROM class' in sql and 'grade_id' in sql.split('WHERE')[0]:
            return {'grade_id': 4}
        if 'FROM student' in sql:
            return self.students.get(params[0])
        return None

    def query_all(self, sql, params=()):
        return []

    def execute(self, sql, params=()):
        self.executed.append((sql.strip(), params))


class TestStudentProfileFields:
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

    def _student_row(self):
        return {
            'student_id': '20240101', 'name': '张三', 'status': '在校',
            'class_id': 19, 'grade_id': 4,
        }

    def test_update_writes_three_profile_columns(self, client):
        """PUT 携带三档案字段时全部写入 SET 子句"""
        db = FakeDb(students={'20240101': self._student_row()})
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.put('/api/moral/admin/students/20240101', json={
                'middle_school': '金华四中',
                'entrance_score': '632.5',
                'gaokao_score': '',
            })

        assert resp.status_code == 200
        assert len(db.executed) == 1
        sql, params = db.executed[0]
        assert sql.startswith('UPDATE student SET')
        assert 'middle_school = ?' in sql
        assert 'entrance_score = ?' in sql
        assert 'gaokao_score = ?' in sql  # 空串也写入（前端始终携带以支持清空）
        assert params == ('金华四中', '632.5', '', '20240101')

    def test_update_absent_fields_not_touched(self, client):
        """未携带的档案字段不出现在 SET 中（None 跳过，不误清数据）"""
        db = FakeDb(students={'20240101': self._student_row()})
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.put('/api/moral/admin/students/20240101', json={
                'roomid': 'A101',
            })

        assert resp.status_code == 200
        sql, params = db.executed[0]
        assert 'roomid = ?' in sql
        for col in ('middle_school', 'entrance_score', 'gaokao_score'):
            assert col not in sql
        assert params == ('A101', '20240101')

    def test_create_inserts_non_empty_fields(self, client):
        """POST 创建学生：非空档案字段进入 INSERT 列"""
        db = FakeDb()
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/moral/admin/students', json={
                'student_id': '20260999', 'name': '李四', 'gender': '女',
                'class_id': 19,
                'middle_school': '婺城中学', 'entrance_score': '618',
                'gaokao_score': '',
            })

        assert resp.status_code == 200
        insert_sql, insert_params = db.executed[0]
        assert insert_sql.startswith('INSERT INTO student')
        assert 'middle_school' in insert_sql and 'entrance_score' in insert_sql
        assert 'gaokao_score' not in insert_sql  # 空串不写库
        assert '婺城中学' in insert_params and '618' in insert_params
        assert '' not in [p for p in insert_params if isinstance(p, str)]

    def test_create_skips_all_empty_fields(self, client):
        """POST 创建学生：档案字段全空时不拼额外列，走原始插入"""
        db = FakeDb()
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.post('/api/moral/admin/students', json={
                'student_id': '20260998', 'name': '王五', 'gender': '男',
                'class_id': 19, 'middle_school': '', 'entrance_score': '',
                'gaokao_score': '',
            })

        assert resp.status_code == 200
        insert_sql, insert_params = db.executed[0]
        for col in ('middle_school', 'entrance_score', 'gaokao_score'):
            assert col not in insert_sql
        assert '王五' in insert_params


class TestGradeLeaderEditScope:
    """年级主任编辑本年级（含已归档毕业年级）学生信息

    回归：PUT /students/{id} 的权限门此前只认 student_manage /
    student_manage_own_class，导致配置了 managed_grades 范围的年级主任
    被 403「需要学生管理权限」拦截。
    """

    @pytest.fixture
    def client(self):
        from main import app
        from models.datas_api.auth import get_current_user, get_current_user_optional

        mock_user = create_mock_user(role='g_leader', username='齐建文')
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_user_optional] = lambda: mock_user
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    @staticmethod
    def _student_row(class_id=14):
        return {
            'student_id': '20232056', 'name': '赵六', 'status': '毕业',
            'class_id': class_id, 'grade_id': 1,
        }

    def _patches(self, db, *, in_scope=True):
        """打桩：门函数只认 own_grade；范围限定为本年级班级 14"""
        def fake_scoped(_db, _user, _api_path, permission):
            return permission == 'student_manage_own_grade'

        scope = {
            "can_all": False, "can_own_class": False,
            "can_own_grade": True,
            "my_grade_ids": [1], "my_grade_class_ids": [14] if in_scope else [],
        }
        return [
            patch('models.datas_api.moral.api_permission.check_configured_api_permission',
                  return_value={"allowed": True, "reason": "测试放行", "policy": {}, "config": {}}),
            patch('models.datas_api.moral.admin._has_scoped_permission',
                  side_effect=fake_scoped),
            patch('models.datas_api.moral.admin._student_manage_scope',
                  return_value=scope),
            patch('models.datas_api.moral.admin.get_moral_db', return_value=db),
            patch('models.datas_api.moral.admin.log_operation'),
        ]

    def test_g_leader_edits_own_graded_student(self, client):
        """年级主任可编辑本年级（毕业班）学生的档案字段"""
        db = FakeDb(students={'20232056': self._student_row()})
        patches = self._patches(db)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.put('/api/moral/admin/students/20232056', json={
                'entrance_score': '589', 'gaokao_score': '612',
            })

        assert resp.status_code == 200
        sql, params = db.executed[0]
        assert 'entrance_score = ?' in sql and 'gaokao_score = ?' in sql
        assert params == ('589', '612', '20232056')

    def test_g_leader_rejected_outside_grade(self, client):
        """他班学生不在范围内时返回 403 且不写库"""
        db = FakeDb(students={'20232099': self._student_row(class_id=20)})
        patches = self._patches(db, in_scope=False)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.put('/api/moral/admin/students/20232099', json={
                'entrance_score': '589',
            })

        assert resp.status_code == 403
        assert '授权范围' in resp.json()['detail']
        assert db.executed == []

    def test_user_without_any_manage_permission_rejected(self, client):
        """三种权限都不具备时仍被权限门拦截"""
        db = FakeDb(students={'20232056': self._student_row()})

        def fake_scoped(_db, _user, _api_path, _permission):
            return False

        patches = self._patches(db)
        patches[1] = patch('models.datas_api.moral.admin._has_scoped_permission',
                           side_effect=fake_scoped)
        patches[2] = patch('models.datas_api.moral.admin._student_manage_scope',
                           return_value={"can_all": False})
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            resp = client.put('/api/moral/admin/students/20232056', json={
                'name': '新名字',
            })

        assert resp.status_code == 403
        assert '需要学生管理权限' in resp.json()['detail']
        assert db.executed == []
