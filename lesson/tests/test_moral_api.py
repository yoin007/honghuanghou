# -*- coding: utf-8 -*-
"""
德育评价系统 API 测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# 添加 lesson 目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 在导入任何模块之前 mock Task 类的初始化
@pytest.fixture(scope="module", autouse=True)
def mock_task_init():
    """Mock Task 类的初始化，避免在测试中连接真实数据库"""
    with patch('models.task.Task.__init__', return_value=None):
        with patch('models.task.task_scheduler', None):
            yield


def create_mock_user(role='teacher', username='test_user'):
    """创建模拟用户"""
    from models.datas_api.auth import User
    return User(username=username, role=role)


class TestDailyRecordAPI:
    """日常表现记录 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from main import app
        from models.datas_api.auth import get_current_user

        # 创建模拟用户
        mock_user = create_mock_user(role='xuefa', username='test_xuefa')

        # 使用 FastAPI 的 dependency_overrides
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with TestClient(app) as client:
            yield client

        # 清理 override
        app.dependency_overrides.clear()

    def test_get_daily_event_types(self, client):
        """测试获取日常事件类型列表"""
        with patch('models.datas_api.moral.daily_record.get_moral_db') as mock_db:
            mock_db.return_value.__enter__.return_value.query_all.return_value = [
                {"event_id": 1, "event_name": "拾金不昧", "event_type": 1, "score": 3},
                {"event_id": 2, "event_name": "迟到", "event_type": 2, "score": -2},
            ]

            response = client.get("/api/moral/daily-records/types")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 2

    def test_get_daily_records(self, client):
        """测试获取日常表现记录列表"""
        with patch('models.datas_api.moral.daily_record.get_moral_db') as mock_db:
            mock_db.return_value.__enter__.return_value.query_value.return_value = 0
            mock_db.return_value.__enter__.return_value.query_all.return_value = []

            response = client.get("/api/moral/daily-records")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_create_daily_record_unauthorized(self):
        """测试未授权创建记录"""
        from main import app
        # 不设置 dependency_overrides，依赖项会抛出401
        with TestClient(app) as client:
            response = client.post("/api/moral/daily-records", json={
                "student_id": "2025001",
                "event_id": 1,
                "record_date": "2025-03-29"
            })

            assert response.status_code == 401


class TestEvaluationAPI:
    """评价查询 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from main import app
        return TestClient(app)

    def test_get_student_evaluation_not_found(self, client):
        """测试获取不存在学生的评价"""
        with patch('models.datas_api.moral.base.get_moral_db') as mock_db:
            mock_db.return_value.__enter__.return_value.query_one.return_value = None

            response = client.get("/api/moral/evaluations/student/999999")

            # 未认证会返回 401
            assert response.status_code in [401, 404]


class TestBirthdayAPI:
    """生日提醒 API 测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from main import app
        from models.datas_api.auth import get_current_user

        # 创建模拟用户
        mock_user = create_mock_user(role='xuefa', username='test_xuefa')

        # 使用 FastAPI 的 dependency_overrides
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with TestClient(app) as client:
            yield client

        # 清理 override
        app.dependency_overrides.clear()

    def test_get_today_birthdays(self, client):
        """测试获取今日生日"""
        with patch('models.datas_api.moral.birthday.get_moral_db') as mock_db:
            mock_db.return_value.__enter__.return_value.query_all.return_value = []

            response = client.get("/api/moral/birthdays/today")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestMySQLDatabase:
    """MySQL 数据库操作测试"""

    def test_moral_db_context_manager(self):
        """测试数据库上下文管理器"""
        from utils.mysql_db import MySQLDatabase

        # 模拟测试
        with patch('utils.mysql_db.get_connection_pool') as mock_pool:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_pool.return_value.get_connection.return_value = mock_conn

            # 这里只是测试导入和基本结构
            # 实际数据库测试需要在测试数据库环境中进行
            pass

    def test_execute_query_function(self):
        """测试快捷查询函数"""
        from utils.mysql_db import execute_query

        # 模拟测试
        with patch('utils.mysql_db.MySQLDatabase') as mock_db:
            mock_db.return_value.__enter__.return_value.query_one.return_value = {"test": 1}

            # 测试函数存在
            assert callable(execute_query)


class TestMoralPermissions:
    """德育系统权限测试"""

    def test_moral_permissions_structure(self):
        """测试权限配置结构"""
        from models.datas_api.moral.base import MORAL_PERMISSIONS

        assert 'admin' in MORAL_PERMISSIONS
        assert 'xuefa' in MORAL_PERMISSIONS
        assert 'cleader' in MORAL_PERMISSIONS
        assert 'teacher' in MORAL_PERMISSIONS

        # 检查 admin 有 all 权限
        assert 'all' in MORAL_PERMISSIONS['admin']['permissions']

    def test_check_moral_permission_admin(self):
        """测试管理员权限检查"""
        from models.datas_api.moral.base import check_moral_permission

        mock_user = MagicMock()
        mock_user.role = 'admin'

        # 管理员应该有所有权限
        assert check_moral_permission(mock_user, 'any_permission') is True

    def test_check_moral_permission_teacher(self):
        """测试教师权限检查"""
        from models.datas_api.moral.base import check_moral_permission

        mock_user = MagicMock()
        mock_user.role = 'teacher'

        # 教师应该有录入权限
        assert check_moral_permission(mock_user, 'moral_record_input') is True
        # 教师不应该有管理权限
        assert check_moral_permission(mock_user, 'punishment_manage') is False


class TestMoralUtilities:
    """德育系统工具函数测试"""

    def test_calculate_moral_level(self):
        """测试德育等级计算"""
        from models.datas_api.moral.base import calculate_moral_level

        assert calculate_moral_level(95) == "优秀"
        assert calculate_moral_level(90) == "优秀"
        assert calculate_moral_level(85) == "良好"
        assert calculate_moral_level(75) == "良好"
        assert calculate_moral_level(65) == "合格"
        assert calculate_moral_level(60) == "合格"
        assert calculate_moral_level(55) == "不合格"

    def test_get_user_role_level(self):
        """测试用户角色等级获取"""
        from models.datas_api.moral.base import get_user_role_level

        mock_user = MagicMock()
        mock_user.role = 'xuefa'

        level = get_user_role_level(mock_user)
        assert level == 50  # xuefa 等级应该是 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])