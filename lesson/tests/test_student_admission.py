# -*- coding: utf-8 -*-
"""毕业学生录取信息（批量导入/更新）API 测试 + 班主任/年级主任数据范围匹配测试"""
import sqlite3
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


class MemDb:
    """内存 sqlite：跑真实 SQL，验证班主任/年级主任匹配与 prefer-active"""

    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE teacher (teacher_id TEXT PRIMARY KEY, name TEXT)")
        self.conn.execute("""CREATE TABLE class (
            class_id INTEGER PRIMARY KEY, class_name TEXT, grade_id INTEGER,
            is_active INTEGER DEFAULT 1,
            leader_ids TEXT DEFAULT '', leader_names TEXT DEFAULT '',
            leader_name TEXT DEFAULT '', leader_wxid TEXT DEFAULT '')""")
        self.conn.execute("""CREATE TABLE grade (
            grade_id INTEGER PRIMARY KEY, grade_name TEXT, is_archived INTEGER DEFAULT 0,
            leader_ids TEXT DEFAULT '', leader_names TEXT DEFAULT '')""")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def query_one(self, sql, params=()):
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def query_all(self, sql, params=()):
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]


def _scope_db():
    """任秀辉：现役高一1班(19,新字段) + 毕业班2023级3班(14,旧字段残留)；齐建文管两级。"""
    db = MemDb()
    db.conn.execute("INSERT INTO teacher VALUES ('T_任秀辉', '任秀辉')")
    db.conn.executemany(
        "INSERT INTO class VALUES (?,?,?,?,?,?,?,?)",
        [
            (14, '2023级3班', 1, 1, '', '', '任秀辉', ''),
            (19, '高一1班', 4, 1, 'T_任秀辉', '任秀辉', '', ''),
            (20, '高一2班', 4, 1, 'T_张三丰', '张三丰', '', ''),
        ]
    )
    db.conn.executemany(
        "INSERT INTO grade VALUES (?,?,?,?,?)",
        [
            (1, '2023级', 1, 'T_齐建文', '齐建文'),
            (4, '2026级', 0, 'T_齐建文', '齐建文'),
        ]
    )
    return db


class TestTeacherScopeMatching:
    """get_teacher_class_ids / get_teacher_grade_ids 匹配与 prefer-active 行为"""

    def test_matches_new_multi_person_fields(self):
        """新多人字段配置的班级能被匹配（回归：SELECT 缺列导致方式1/2失效）"""
        from models.datas_api.moral.base import get_teacher_class_ids
        user = create_mock_user(role='cleader', username='任秀辉')
        assert sorted(get_teacher_class_ids(user, _scope_db())) == [14, 19]

    def test_like_no_false_positive_on_similar_name(self):
        """T_张三 不得误匹配 T_张三丰 的班级（精确 split 校验）"""
        from models.datas_api.moral.base import get_teacher_class_ids
        db = _scope_db()
        db.conn.execute("INSERT INTO teacher VALUES ('T_张三', '张三')")
        user = create_mock_user(role='cleader', username='张三')
        assert get_teacher_class_ids(user, db) == []

    def test_singular_prefers_active_class(self):
        """一人两岗：单数版优先返回现役班级"""
        from models.datas_api.moral.base import get_teacher_class_id
        user = create_mock_user(role='cleader', username='任秀辉')
        assert get_teacher_class_id(user, _scope_db()) == 19

    def test_singular_falls_back_when_all_archived(self):
        """全部年级已归档时回退毕业班，仍可管理毕业生"""
        from models.datas_api.moral.base import get_teacher_class_id
        db = _scope_db()
        db.conn.execute("UPDATE grade SET is_archived = 1 WHERE grade_id = 4")
        user = create_mock_user(role='cleader', username='任秀辉')
        assert get_teacher_class_id(user, db) == 14

    def test_grade_ids_match_new_fields_and_sorted(self):
        """年级主任多人字段匹配 + 有序返回"""
        from models.datas_api.moral.base import get_teacher_grade_ids
        user = create_mock_user(role='g_leader', username='齐建文')
        assert get_teacher_grade_ids(user, _scope_db()) == [1, 4]

    def test_prefer_active_grade_id(self):
        """年级 prefer-active：默认现役级，全归档回退最小 ID"""
        from models.datas_api.moral.base import prefer_active_grade_id
        db = _scope_db()
        assert prefer_active_grade_id(db, [1, 4]) == 4
        db.conn.execute("UPDATE grade SET is_archived = 1 WHERE grade_id = 4")
        assert prefer_active_grade_id(db, [1, 4]) == 1


class TestAdmissionOwnClassScope:
    """班主任/年级主任导入录取信息的范围校验"""

    def _student_row(self, student_id='20220101', name='张三', status='毕业',
                     class_id=14, grade_id=1):
        return {'student_id': student_id, 'name': name, 'status': status,
                'class_id': class_id, 'grade_id': grade_id}

    def _patches(self, db, scope):
        return [
            patch('models.datas_api.moral.api_permission.check_configured_api_permission',
                  return_value={"allowed": True, "reason": "测试放行", "policy": {}, "config": {}}),
            patch('models.datas_api.moral.admin._has_scoped_permission', return_value=True),
            patch('models.datas_api.moral.admin._student_manage_scope', return_value=scope),
            patch('models.datas_api.moral.admin.get_moral_db', return_value=db),
            patch('models.datas_api.moral.admin.log_operation'),
        ]

    def _client(self):
        from main import app
        from models.datas_api.auth import get_current_user, get_current_user_optional
        mock_user = create_mock_user(role='cleader', username='T_任秀辉')
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_user_optional] = lambda: mock_user
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def test_cleader_imports_own_graduated_class(self):
        """班主任可导入本毕业班学生"""
        db = FakeDb(students={
            '20220101': self._student_row(),
        })
        scope = {"can_all": False, "can_own_class": True,
                 "my_class_ids": [14], "my_grade_ids": []}
        patches = self._patches(db, scope)
        for client in self._client():
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                resp = client.post('/api/moral/admin/students/admission-batch', json={
                    'students': [{'student_id': '20220101', 'name': '张三',
                                  'university_name': '浙江大学'}]
                })
        data = resp.json()['data']
        assert resp.status_code == 200
        assert data['success_count'] == 1 and data['error_count'] == 0

    def test_cleader_rejects_other_class_with_unified_message(self):
        """他班学生统一报「无权录入该学生」，不泄露存在性"""
        db = FakeDb(students={
            '20220999': self._student_row(student_id='20220999', name='王五',
                                          class_id=20, grade_id=4),
        })
        scope = {"can_all": False, "can_own_class": True,
                 "my_class_ids": [14], "my_grade_ids": []}
        patches = self._patches(db, scope)
        for client in self._client():
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                resp = client.post('/api/moral/admin/students/admission-batch', json={
                    'students': [{'student_id': '20220999', 'name': '王五',
                                  'university_name': '浙江大学'}]
                })
        data = resp.json()['data']
        assert data['success_count'] == 0
        assert any('无权录入该学生' in e for e in data['errors'])
        assert db.executed == []

    def test_mixed_batch_partial_success(self):
        """混合批次：本班成功、他班拒绝、互不影响"""
        db = FakeDb(students={
            '20220101': self._student_row(),
            '20220999': self._student_row(student_id='20220999', name='王五',
                                          class_id=20, grade_id=4),
        })
        scope = {"can_all": False, "can_own_class": True,
                 "my_class_ids": [14], "my_grade_ids": []}
        patches = self._patches(db, scope)
        for client in self._client():
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                resp = client.post('/api/moral/admin/students/admission-batch', json={
                    'students': [
                        {'student_id': '20220101', 'name': '张三', 'university_name': '浙江大学'},
                        {'student_id': '20220999', 'name': '王五', 'university_name': '复旦大学'},
                    ]
                })
        data = resp.json()['data']
        assert data['success_count'] == 1 and data['error_count'] == 1

    def test_g_leader_imports_own_graduated_grade(self):
        """年级主任可导入本毕业年级学生"""
        db = FakeDb(students={
            '20220101': self._student_row(class_id=14, grade_id=1),
        })
        scope = {"can_all": False, "can_own_class": False,
                 "my_class_ids": [], "can_own_grade": True, "my_grade_ids": [1]}
        patches = self._patches(db, scope)
        for client in self._client():
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                resp = client.post('/api/moral/admin/students/admission-batch', json={
                    'students': [{'student_id': '20220101', 'name': '张三',
                                  'university_name': '浙江大学'}]
                })
        data = resp.json()['data']
        assert resp.status_code == 200
        assert data['success_count'] == 1

    def test_empty_scope_returns_403(self):
        """范围为空（既无班级也无年级）直接 403"""
        db = FakeDb()
        scope = {"can_all": False, "my_class_ids": [], "my_grade_ids": []}
        patches = self._patches(db, scope)
        for client in self._client():
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                resp = client.post('/api/moral/admin/students/admission-batch', json={
                    'students': [{'student_id': '20220101', 'name': '张三',
                                  'university_name': '浙江大学'}]
                })
        assert resp.status_code == 403
