# -*- coding: utf-8 -*-
"""毕业年级隔离测试：选项端点默认现役、include_archived 开关、学生计数口径（在校+毕业）、一生一册守卫"""
import sqlite3
import sys
import pytest
from unittest.mock import patch, MagicMock

from fastapi import HTTPException
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


class MemDb:
    """内存 sqlite：真实 SQL 跑 grades/classes 端点与计数口径"""

    def __init__(self):
        # TestClient 在独立线程中执行请求，需允许跨线程使用连接
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE teacher (teacher_id TEXT PRIMARY KEY, name TEXT)")
        self.conn.execute("""CREATE TABLE grade (
            grade_id INTEGER PRIMARY KEY, grade_name TEXT, enrollment_year INTEGER,
            is_archived INTEGER DEFAULT 0, archived_at TEXT,
            leader_ids TEXT DEFAULT '', leader_names TEXT DEFAULT '')""")
        self.conn.execute("""CREATE TABLE class (
            class_id INTEGER PRIMARY KEY, class_name TEXT, grade_id INTEGER,
            is_active INTEGER DEFAULT 1, class_number INTEGER DEFAULT 0,
            leader_ids TEXT DEFAULT '', leader_names TEXT DEFAULT '',
            leader_name TEXT DEFAULT '', leader_wxid TEXT DEFAULT '')""")
        self.conn.execute("""CREATE TABLE student (
            student_id TEXT PRIMARY KEY, name TEXT,
            class_id INTEGER, grade_id INTEGER,
            status TEXT DEFAULT '在校')""")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def query_one(self, sql, params=()):
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def query_all(self, sql, params=()):
        if params is None:
            rows = self.conn.execute(sql).fetchall()
        else:
            rows = self.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def _fixture_db():
    """年级1=2023级(归档,2名毕业生)、年级4=2026级(现役,1名在校生)"""
    db = MemDb()
    db.conn.executemany(
        "INSERT INTO grade (grade_id, grade_name, enrollment_year, is_archived, archived_at) VALUES (?,?,?,?,?)",
        [
            (1, '2023级', 2023, 1, '2026-08-18 23:06:28'),
            (4, '2026级', 2026, 0, None),
        ]
    )
    db.conn.executemany(
        "INSERT INTO class (class_id, class_name, grade_id, is_active, class_number) VALUES (?,?,?,?,?)",
        [
            (14, '2023级3班', 1, 1, 3),
            (19, '高一1班', 4, 1, 1),
        ]
    )
    db.conn.executemany(
        "INSERT INTO student (student_id, name, class_id, grade_id, status) VALUES (?,?,?,?,?)",
        [
            ('20220101', '张三', 14, 1, '毕业'),
            ('20220102', '李四', 14, 1, '毕业'),
            ('20260101', '王五', 19, 4, '在校'),
        ]
    )
    return db


def _patches(db):
    return [
        patch('models.datas_api.moral.api_permission.check_configured_api_permission',
              return_value={"allowed": True, "reason": "测试放行", "policy": {}, "config": {}}),
        patch('models.datas_api.moral.admin.get_moral_db', return_value=db),
    ]


class TestGradesEndpoint:
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

    def test_default_excludes_archived_grade(self, client):
        """默认只返回现役级号，学生数按在校+毕业统计"""
        db = _fixture_db()
        p1, p2 = _patches(db)
        with p1, p2:
            resp = client.get('/api/moral/admin/grades')

        assert resp.status_code == 200
        grades = resp.json()['data']
        assert [g['grade_id'] for g in grades] == [4]
        assert grades[0]['student_count'] == 1

    def test_include_archived_returns_graduated_count(self, client):
        """include_archived=1 返回全部级号，毕业年级学生数不再为 0"""
        db = _fixture_db()
        p1, p2 = _patches(db)
        with p1, p2:
            resp = client.get('/api/moral/admin/grades', params={'include_archived': 1})

        assert resp.status_code == 200
        by_id = {g['grade_id']: g for g in resp.json()['data']}
        assert set(by_id) == {1, 4}
        assert by_id[1]['student_count'] == 2   # 毕业生计入
        assert by_id[4]['student_count'] == 1

    def test_scoped_variant_excludes_archived_by_default(self, client):
        """scoped 分支（班主任视角）同样默认排除归档年级且 SQL 合法"""
        db = _fixture_db()
        db.conn.execute(
            "UPDATE class SET leader_ids = 'T_任秀辉', leader_names = '任秀辉' WHERE class_id IN (14, 19)")
        db.conn.execute("INSERT INTO teacher VALUES ('T_任秀辉', '任秀辉')")
        p1, p2 = _patches(db)
        with p1, p2:
            resp = client.get('/api/moral/admin/grades')

        assert resp.status_code == 200
        grades = resp.json()['data']
        assert [g['grade_id'] for g in grades] == [4]


class TestClassesEndpoint:
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

    def test_default_excludes_archived_grade_classes(self, client):
        """默认不含毕业级班级（回归：升年级不改 class.is_active 导致毕业班外泄）"""
        db = _fixture_db()
        p1, p2 = _patches(db)
        with p1, p2:
            resp = client.get('/api/moral/admin/classes')

        assert resp.status_code == 200
        classes = resp.json()['data']
        assert [c['class_id'] for c in classes] == [19]
        assert classes[0]['student_count'] == 1

    def test_include_archived_lists_graduated_class_with_count(self, client):
        """include_archived=1 返回毕业班，学生数计入毕业生"""
        db = _fixture_db()
        p1, p2 = _patches(db)
        with p1, p2:
            resp = client.get('/api/moral/admin/classes', params={'include_archived': 1})

        assert resp.status_code == 200
        by_id = {c['class_id']: c for c in resp.json()['data']}
        assert set(by_id) == {14, 19}
        assert by_id[14]['student_count'] == 2
        assert by_id[19]['student_count'] == 1

    def test_include_archived_with_grade_filter(self, client):
        """配置页「查看班级」对话框场景：include_archived=1 + grade_id 组合可用"""
        db = _fixture_db()
        p1, p2 = _patches(db)
        with p1, p2:
            resp = client.get('/api/moral/admin/classes',
                              params={'include_archived': 1, 'grade_id': 1})

        assert resp.status_code == 200
        assert [c['class_id'] for c in resp.json()['data']] == [14]

    def test_default_hides_archived_even_with_grade_filter(self, client):
        """不带开关时即使指定毕业 grade_id 也返回空（防止误用）"""
        db = _fixture_db()
        p1, p2 = _patches(db)
        with p1, p2:
            resp = client.get('/api/moral/admin/classes', params={'grade_id': 1})

        assert resp.status_code == 200
        assert resp.json()['data'] == []


class TestTimelineAccessGuard:
    """_ensure_timeline_student_access：范围校验放行本班毕业生"""

    def _run(self, student, scope):
        from models.datas_api.moral import timeline_api
        with patch.object(timeline_api, '_timeline_scope', return_value=scope):
            timeline_api._ensure_timeline_student_access(
                MagicMock(), create_mock_user(role='cleader', username='任秀辉'), student)

    def test_cleader_can_view_graduated_own_class(self):
        """班主任可查看本班毕业生的一生一册（守卫移除回归）"""
        student = {'student_id': '20220101', 'class_id': 14, 'status': '毕业', 'grade_archived': 1}
        self._run(student, {'can_all': False, 'can_own_class': True, 'my_class_ids': [14]})

    def test_out_of_scope_graduated_rejected(self):
        """他班毕业生仍被范围校验拒绝"""
        student = {'student_id': '20220999', 'class_id': 20, 'status': '毕业', 'grade_archived': 1}
        with pytest.raises(HTTPException) as exc_info:
            self._run(student, {'can_all': False, 'can_own_class': True, 'my_class_ids': [14]})
        assert exc_info.value.status_code == 403

    def test_active_student_scope_rules_unchanged(self):
        """现役学生的范围校验行为不变"""
        student = {'student_id': '20260101', 'class_id': 20, 'status': '在校'}
        with pytest.raises(HTTPException) as exc_info:
            self._run(student, {'can_all': False, 'can_own_class': True, 'my_class_ids': [14]})
        assert exc_info.value.status_code == 403
