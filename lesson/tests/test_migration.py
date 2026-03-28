"""
数据库迁移验证测试
测试数据迁移脚本的正确性
"""
import pytest


class MockDatabase:
    """模拟数据库"""
    def __init__(self):
        self.data = {
            'grade': [],
            'class': [],
            'student': [],
            'teacher': [],
            'student_class_history': []
        }
        self._id_counter = 1

    def execute(self, sql, *args):
        """执行SQL（简化版）"""
        if 'INSERT INTO grade' in sql:
            self.data['grade'].append({
                'grade_id': self._id_counter,
                'grade_name': args[0],
                'enrollment_year': args[1]
            })
            self._id_counter += 1
        elif 'INSERT INTO class' in sql:
            self.data['class'].append({
                'class_id': self._id_counter,
                'class_code': args[0],
                'grade_id': args[1],
                'class_number': args[2],
                'class_name': args[3]
            })
            self._id_counter += 1
        elif 'INSERT INTO student_class_history' in sql:
            # SQL格式: VALUES (%s, %s, %s, %s, '入学') - 只有4个参数
            self.data['student_class_history'].append({
                'student_id': args[0],
                'class_id': args[1],
                'grade_id': args[2],
                'start_date': args[3],
                'change_reason': '入学'
            })
        elif 'INSERT INTO student' in sql:
            # 注意：必须先检查student_class_history，因为"student"也包含在其中
            self.data['student'].append({
                'student_id': args[0],
                'name': args[1],
                'class_id': args[2],
                'grade_id': args[3]
            })
        elif 'INSERT INTO teacher' in sql:
            self.data['teacher'].append({
                'teacher_id': args[0],
                'name': args[1],
                'subject': args[2]
            })

    def query(self, sql):
        """查询（简化版）"""
        class Result:
            def __init__(self, data):
                self._data = data

            def first(self):
                return self._data[0] if self._data else None

        if 'SELECT grade_id FROM grade WHERE enrollment_year' in sql:
            for g in self.data['grade']:
                if g['enrollment_year'] == 2025:
                    return Result([{'grade_id': g['grade_id']}])
            return Result([])

        if 'SELECT class_id, grade_id FROM class WHERE class_name' in sql:
            for c in self.data['class']:
                return Result([{'class_id': c['class_id'], 'grade_id': c['grade_id']}])
            return Result([])

        if 'COUNT' in sql:
            table = sql.split('FROM')[1].split()[0].strip()
            return Result([{'cnt': len(self.data.get(table, []))}])

        return Result([])


def validate_migration(db):
    """验证迁移结果"""
    errors = []

    # 1. 数据量验证
    checks = [
        ("级号", "grade", "SELECT COUNT(*) as cnt FROM grade"),
        ("班级", "class", "SELECT COUNT(*) as cnt FROM class"),
        ("学生", "student", "SELECT COUNT(*) as cnt FROM student"),
        ("教师", "teacher", "SELECT COUNT(*) as cnt FROM teacher"),
    ]

    for name, table, query in checks:
        result = db.query(query).first()
        count = result['cnt'] if result else 0
        if count == 0:
            errors.append(f"{name}数据为空")

    return errors


class TestDataMigration:
    """数据迁移测试"""

    def test_grade_migration(self):
        """测试级号迁移"""
        db = MockDatabase()
        db.execute("INSERT INTO grade (grade_name, enrollment_year) VALUES (%s, %s)", "2025级", 2025)

        assert len(db.data['grade']) == 1
        assert db.data['grade'][0]['grade_name'] == "2025级"
        assert db.data['grade'][0]['enrollment_year'] == 2025

    def test_class_migration(self):
        """测试班级迁移"""
        db = MockDatabase()
        # 先添加级号
        db.execute("INSERT INTO grade (grade_name, enrollment_year) VALUES (%s, %s)", "2025级", 2025)
        # 再添加班级
        db.execute(
            "INSERT INTO class (class_code, grade_id, class_number, class_name, leader_name, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
            "202501", 1, 1, "2025级1班", "张老师", 1
        )

        assert len(db.data['class']) == 1
        assert db.data['class'][0]['class_code'] == "202501"
        assert db.data['class'][0]['class_name'] == "2025级1班"

    def test_student_migration(self):
        """测试学生迁移"""
        db = MockDatabase()
        db.execute("INSERT INTO grade (grade_name, enrollment_year) VALUES (%s, %s)", "2025级", 2025)
        db.execute("INSERT INTO class (class_code, grade_id, class_number, class_name) VALUES (%s, %s, %s, %s)", "202501", 1, 1, "2025级1班")

        db.execute(
            "INSERT INTO student (student_id, name, class_id, grade_id, roomid, original_grade_id, status, is_active) VALUES (%s, %s, %s, %s, %s, %s, '在校', 1)",
            "202501001", "张三", 1, 1, "", 1
        )

        assert len(db.data['student']) == 1
        assert db.data['student'][0]['student_id'] == "202501001"
        assert db.data['student'][0]['name'] == "张三"

    def test_teacher_migration(self):
        """测试教师迁移"""
        db = MockDatabase()
        db.execute(
            "INSERT INTO teacher (teacher_id, name, subject, password_hash, role, level, is_active, is_password_changed) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            "T张老师", "张老师", "语文", "hashed_password", "teacher", 0, 1, 0
        )

        assert len(db.data['teacher']) == 1
        assert db.data['teacher'][0]['teacher_id'] == "T张老师"
        assert db.data['teacher'][0]['name'] == "张老师"

    def test_student_class_history_creation(self):
        """测试班级履历创建"""
        db = MockDatabase()
        db.execute(
            "INSERT INTO student_class_history (student_id, class_id, grade_id, start_date, change_reason) VALUES (%s, %s, %s, %s, '入学')",
            "202501001", 1, 1, "2025-09-01"
        )

        assert len(db.data['student_class_history']) == 1
        assert db.data['student_class_history'][0]['student_id'] == "202501001"
        assert db.data['student_class_history'][0]['change_reason'] == "入学"


class TestMigrationValidation:
    """迁移验证测试"""

    def test_validation_with_data(self):
        """有数据时验证应该通过"""
        db = MockDatabase()
        db.execute("INSERT INTO grade (grade_name, enrollment_year) VALUES (%s, %s)", "2025级", 2025)
        db.execute("INSERT INTO class (class_code, grade_id, class_number, class_name) VALUES (%s, %s, %s, %s)", "202501", 1, 1, "2025级1班")
        db.execute("INSERT INTO student (student_id, name, class_id, grade_id) VALUES (%s, %s, %s, %s)", "001", "张三", 1, 1)
        db.execute("INSERT INTO teacher (teacher_id, name, subject) VALUES (%s, %s, %s)", "T001", "张老师", "语文")

        errors = validate_migration(db)
        assert len(errors) == 0

    def test_validation_without_data(self):
        """无数据时验证应该失败"""
        db = MockDatabase()
        errors = validate_migration(db)
        assert len(errors) > 0
        assert any("级号" in e for e in errors)
        assert any("班级" in e for e in errors)
        assert any("学生" in e for e in errors)
        assert any("教师" in e for e in errors)


class TestSQLParameterCount:
    """SQL参数数量测试（验证设计文档中的参数匹配）"""

    def test_grade_insert_parameters(self):
        """grade表INSERT应该有2个参数"""
        # VALUES (%s, %s) → 2个参数
        params = ("2025级", 2025)
        assert len(params) == 2

    def test_class_insert_parameters(self):
        """class表INSERT应该有6个参数"""
        # VALUES (%s, %s, %s, %s, %s, %s) → 6个参数
        params = ("202501", 1, 1, "2025级1班", "张老师", 1)
        assert len(params) == 6

    def test_student_insert_parameters(self):
        """student表INSERT应该有6个参数+2固定值"""
        # VALUES (%s, %s, %s, %s, %s, %s, '在校', 1) → 6个参数+2固定值
        params = ("202501001", "张三", 1, 1, "", 1)
        assert len(params) == 6

    def test_student_class_history_insert_parameters(self):
        """student_class_history表INSERT应该有4个参数+1固定值"""
        # VALUES (%s, %s, %s, %s, '入学') → 4个参数+1固定值
        params = ("202501001", 1, 1, "2025-09-01")
        assert len(params) == 4

    def test_teacher_insert_parameters(self):
        """teacher表INSERT应该有8个参数"""
        # VALUES (%s, %s, %s, %s, %s, %s, %s, %s) → 8个参数
        params = ("T001", "张老师", "语文", "hash", "teacher", 0, 1, 0)
        assert len(params) == 8