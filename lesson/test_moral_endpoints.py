#!/usr/bin/env python3
"""
德育评价系统 API 端点测试脚本
直接测试各个 API 端点功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from models.datas_api.auth import User, get_current_user

# 创建测试用户
def create_mock_user(role='admin', username='test_admin'):
    return User(username=username, role=role)

# 测试客户端
client = TestClient(app)

def call_api_endpoint(method, path, json_data=None, role='admin'):
    """通用 API 测试函数"""
    mock_user = create_mock_user(role=role, username=f'test_{role}')

    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        if method == 'GET':
            response = client.get(path)
        elif method == 'POST':
            response = client.post(path, json=json_data)
        elif method == 'PUT':
            response = client.put(path, json=json_data)
        elif method == 'DELETE':
            response = client.delete(path)

        return response.status_code, response.json() if response.content else {}
    finally:
        app.dependency_overrides.clear()

def main():
    print("=" * 60)
    print("德育评价系统 API 端点测试")
    print("=" * 60)

    # 1. 测试级号管理 API
    print("\n1. 测试级号管理 API")
    print("-" * 40)

    with patch('models.datas_api.moral.admin.get_moral_db') as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn

        # 获取级号列表
        mock_conn.query_all.return_value = [
            {'grade_id': 1, 'grade_name': '2025级', 'enrollment_year': 2025, 'class_count': 4, 'student_count': 160}
        ]
        status, data = call_api_endpoint('GET', '/api/moral/admin/grades')
        print(f"  GET /api/moral/admin/grades: {status} - {'✓' if status == 200 else '✗'}")
        if status == 200:
            print(f"    数据: {data}")

    # 2. 测试班级管理 API
    print("\n2. 测试班级管理 API")
    print("-" * 40)

    with patch('models.datas_api.moral.admin.get_moral_db') as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn

        mock_conn.query_all.return_value = [
            {'class_id': 1, 'class_name': '1班', 'grade_id': 1, 'grade_name': '2025级', 'student_count': 40}
        ]
        status, data = call_api_endpoint('GET', '/api/moral/admin/classes')
        print(f"  GET /api/moral/admin/classes: {status} - {'✓' if status == 200 else '✗'}")

    # 3. 测试学生管理 API
    print("\n3. 测试学生管理 API")
    print("-" * 40)

    with patch('models.datas_api.moral.admin.get_moral_db') as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn

        mock_conn.query_value.return_value = 100
        mock_conn.query_all.return_value = [
            {'student_id': '2025001', 'name': '张三', 'gender': '男', 'class_name': '1班'}
        ]
        status, data = call_api_endpoint('GET', '/api/moral/admin/students')
        print(f"  GET /api/moral/admin/students: {status} - {'✓' if status == 200 else '✗'}")

    # 4. 测试学年学期管理 API
    print("\n4. 测试学年学期管理 API")
    print("-" * 40)

    with patch('models.datas_api.moral.admin.get_moral_db') as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn

        mock_conn.query_all.return_value = [
            {'semester_id': 1, 'semester_name': '2025-2026上', 'status': 1}
        ]
        status, data = call_api_endpoint('GET', '/api/moral/admin/semesters')
        print(f"  GET /api/moral/admin/semesters: {status} - {'✓' if status == 200 else '✗'}")

    # 5. 测试日常事件类型 API
    print("\n5. 测试日常事件类型 API")
    print("-" * 40)

    with patch('models.datas_api.moral.daily_record.get_moral_db') as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn

        mock_conn.query_all.return_value = [
            {'event_id': 1, 'event_name': '拾金不昧', 'event_type': 1, 'score': 3, 'is_active': 1}
        ]
        status, data = call_api_endpoint('GET', '/api/moral/daily-records/types')
        print(f"  GET /api/moral/daily-records/types: {status} - {'✓' if status == 200 else '✗'}")

    # 6. 测试校级事件类型 API
    print("\n6. 测试校级事件类型 API")
    print("-" * 40)

    with patch('models.datas_api.moral.school_event.get_moral_db') as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn

        mock_conn.query_all.return_value = [
            {'event_id': 1, 'event_name': '三好学生', 'event_type': 1, 'event_level': '校级', 'score': 10, 'is_active': 1}
        ]
        status, data = call_api_endpoint('GET', '/api/moral/school-records/types')
        print(f"  GET /api/moral/school-records/types: {status} - {'✓' if status == 200 else '✗'}")

    # 7. 测试操作日志 API
    print("\n7. 测试操作日志 API")
    print("-" * 40)

    with patch('models.datas_api.moral.admin.get_moral_db') as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn

        mock_conn.query_value.return_value = 5
        mock_conn.query_all.return_value = [
            {'log_id': 1, 'operator': '管理员', 'operation': 'INSERT', 'table_name': 'grade'}
        ]
        status, data = call_api_endpoint('GET', '/api/moral/admin/logs')
        print(f"  GET /api/moral/admin/logs: {status} - {'✓' if status == 200 else '✗'}")

    # 8. 测试系统配置 API
    print("\n8. 测试系统配置 API")
    print("-" * 40)

    with patch('models.datas_api.moral.admin.get_moral_db') as mock_db:
        mock_conn = MagicMock()
        mock_db.return_value.__enter__.return_value = mock_conn

        mock_conn.query_all.return_value = []
        status, data = call_api_endpoint('GET', '/api/moral/admin/config')
        print(f"  GET /api/moral/admin/config: {status} - {'✓' if status == 200 else '✗'}")
        if status == 200:
            print(f"    配置数据: {data}")

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()