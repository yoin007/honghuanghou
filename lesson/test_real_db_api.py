#!/usr/bin/env python3
"""
测试德育 API 与 MySQL 数据库连接
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app
from models.datas_api.auth import User, get_current_user

# 创建测试用户
def create_mock_user(role='admin', username='test_admin'):
    return User(username=username, role=role)

# 测试客户端
client = TestClient(app)

def test_real_db_api():
    """测试真实数据库 API 连接"""
    mock_user = create_mock_user(role='admin', username='管理员')
    app.dependency_overrides[get_current_user] = lambda: mock_user

    try:
        print("=" * 60)
        print("德育 API 与 MySQL 数据库连接测试")
        print("=" * 60)

        # 1. 测试级号列表 API
        print("\n1. 测试级号列表 API")
        print("-" * 40)
        response = client.get("/api/moral/admin/grades")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  成功: {data.get('success')}")
            grades = data.get('data', [])
            print(f"  级号数量: {len(grades)}")
            for g in grades[:3]:
                print(f"    - {g.get('grade_name')}: {g.get('class_count', 0)} 班级, {g.get('student_count', 0)} 学生")

        # 2. 测试班级列表 API
        print("\n2. 测试班级列表 API")
        print("-" * 40)
        response = client.get("/api/moral/admin/classes")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  成功: {data.get('success')}")
            classes = data.get('data', [])
            print(f"  班级数量: {len(classes)}")
            for c in classes[:3]:
                print(f"    - {c.get('class_name')}: {c.get('student_count', 0)} 学生")

        # 3. 测试学生列表 API
        print("\n3. 测试学生列表 API")
        print("-" * 40)
        response = client.get("/api/moral/admin/students?page_size=5")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  成功: {data.get('success')}")
            result = data.get('data', {})
            if isinstance(result, dict):
                print(f"  学生总数: {result.get('total', 0)}")
                students = result.get('items', [])
            else:
                students = result
                print(f"  学生数量: {len(students)}")
            for s in students[:3]:
                print(f"    - {s.get('student_id')}: {s.get('name')} ({s.get('class_name')})")

        # 4. 测试学年学期 API
        print("\n4. 测试学年学期 API")
        print("-" * 40)
        response = client.get("/api/moral/admin/semesters")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  成功: {data.get('success')}")
            semesters = data.get('data', [])
            print(f"  学期数量: {len(semesters)}")
            for s in semesters[:3]:
                current = " (当前)" if s.get('status') == 1 or s.get('is_current') else ""
                print(f"    - {s.get('semester_name')}{current}")

        # 5. 测试日常事件类型 API
        print("\n5. 测试日常事件类型 API")
        print("-" * 40)
        response = client.get("/api/moral/daily-records/types")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  成功: {data.get('success')}")
            types = data.get('data', [])
            print(f"  事件类型数量: {len(types)}")

        # 6. 测试系统配置 API
        print("\n6. 测试系统配置 API")
        print("-" * 40)
        response = client.get("/api/moral/admin/config")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  成功: {data.get('success')}")
            config = data.get('data', {})
            print(f"  基础分: {config.get('evaluation_base_score')}")
            print(f"  生日提醒天数: {config.get('birthday_reminder_days')}")

        print("\n" + "=" * 60)
        print("测试完成!")
        print("=" * 60)

    finally:
        app.dependency_overrides.clear()

if __name__ == "__main__":
    test_real_db_api()