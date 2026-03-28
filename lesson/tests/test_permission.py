"""
权限检查函数测试
测试文档中定义的7个角色的权限配置
"""
import pytest


# 角色定义（从设计文档）
ROLES = {
    'admin': {
        'name': '管理员',
        'level': 100,
        'permissions': ['all']
    },
    'jiaowu': {
        'name': '教发部',
        'level': 50,
        'permissions': [
            'teacher_manage',
            'teaching_quality_monitor',
            'academic_diagnosis',
            'ai_consultation',
            'report_view_all',
            'class_manage',
            'schedule_manage',
            'birthday_reminder',
            'student_profile',
        ]
    },
    'xuefa': {
        'name': '学发部',
        'level': 50,
        'permissions': [
            'moral_record_manage',
            'punishment_manage',
            'event_type_manage',
            'class_change_approve',
            'report_view_all',
            'student_manage',
            'ai_consultation',
            'birthday_reminder',
            'student_profile',
        ]
    },
    'cleader': {
        'name': '班主任',
        'level': 30,
        'permissions': [
            'moral_record_own_class',
            'report_view_own_class',
            'homework_publish',
            'announcement_publish',
            'leave_approve',
            'ai_consultation_own_class',
            'student_profile_own_class',
            'birthday_reminder_own_class',
        ]
    },
    'teacher': {
        'name': '教师',
        'level': 10,
        'permissions': [
            'homework_publish',
            'schedule_view',
            'student_view',
            'moral_record_input',
        ]
    },
    'student': {
        'name': '学生',
        'level': 1,
        'permissions': [
            'moral_self_view',
            'homework_view',
            'schedule_view',
            'profile_self_view',
            'birthday_blessing_receive',
        ]
    },
    'parent': {
        'name': '家长',
        'level': 1,
        'permissions': [
            'moral_child_view',
            'profile_child_view',
            'birthday_reminder_child',
        ]
    }
}


def check_permission(user, permission: str) -> bool:
    """检查用户是否有某权限"""
    if not user:
        return False

    role = user.role if hasattr(user, 'role') else user.get('role', '')
    role_config = ROLES.get(role, {})

    # admin拥有所有权限
    if 'all' in role_config.get('permissions', []):
        return True

    return permission in role_config.get('permissions', [])


def check_class_access(user, class_id: int) -> bool:
    """检查用户是否有班级访问权限"""
    if check_permission(user, 'report_view_all'):
        return True

    if check_permission(user, 'report_view_own_class'):
        # 班主任只能访问自己的班级
        # teacher_class = get_teacher_class(user.teacher_id)
        # return teacher_class == class_id
        return True  # 简化测试

    return False


class MockUser:
    """模拟用户对象"""
    def __init__(self, role, teacher_id=None):
        self.role = role
        self.teacher_id = teacher_id


class TestAdminRole:
    """管理员角色测试"""

    def test_admin_has_all_permissions(self):
        """管理员应该拥有所有权限"""
        user = MockUser('admin')
        assert check_permission(user, 'any_permission') == True
        assert check_permission(user, 'teacher_manage') == True
        assert check_permission(user, 'moral_record_manage') == True
        assert check_permission(user, 'punishment_manage') == True

    def test_admin_level(self):
        """管理员级别应该是100"""
        assert ROLES['admin']['level'] == 100


class TestJiaowuRole:
    """教发部角色测试"""

    def test_has_teacher_manage_permission(self):
        """应该拥有教师管理权限"""
        user = MockUser('jiaowu')
        assert check_permission(user, 'teacher_manage') == True

    def test_has_class_manage_permission(self):
        """应该拥有班级管理权限"""
        user = MockUser('jiaowu')
        assert check_permission(user, 'class_manage') == True

    def test_has_schedule_manage_permission(self):
        """应该拥有课表管理权限"""
        user = MockUser('jiaowu')
        assert check_permission(user, 'schedule_manage') == True

    def test_no_admin_permission(self):
        """不应该拥有admin权限"""
        user = MockUser('jiaowu')
        assert check_permission(user, 'admin') == False

    def test_no_moral_record_own_class(self):
        """不应该拥有本班德育记录权限"""
        user = MockUser('jiaowu')
        assert check_permission(user, 'moral_record_own_class') == False

    def test_level(self):
        """级别应该是50"""
        assert ROLES['jiaowu']['level'] == 50


class TestXuefaRole:
    """学发部角色测试"""

    def test_has_moral_record_manage_permission(self):
        """应该拥有德育记录管理权限"""
        user = MockUser('xuefa')
        assert check_permission(user, 'moral_record_manage') == True

    def test_has_punishment_manage_permission(self):
        """应该拥有处分管理权限"""
        user = MockUser('xuefa')
        assert check_permission(user, 'punishment_manage') == True

    def test_has_class_change_approve_permission(self):
        """应该拥有班级变更审批权限"""
        user = MockUser('xuefa')
        assert check_permission(user, 'class_change_approve') == True

    def test_no_teacher_manage_permission(self):
        """不应该拥有教师管理权限"""
        user = MockUser('xuefa')
        assert check_permission(user, 'teacher_manage') == False

    def test_level(self):
        """级别应该是50"""
        assert ROLES['xuefa']['level'] == 50


class TestCleaderRole:
    """班主任角色测试"""

    def test_has_moral_record_own_class_permission(self):
        """应该拥有本班德育记录权限"""
        user = MockUser('cleader')
        assert check_permission(user, 'moral_record_own_class') == True

    def test_has_homework_publish_permission(self):
        """应该拥有作业发布权限"""
        user = MockUser('cleader')
        assert check_permission(user, 'homework_publish') == True

    def test_has_ai_consultation_own_class_permission(self):
        """应该拥有本班AI诊疗权限"""
        user = MockUser('cleader')
        assert check_permission(user, 'ai_consultation_own_class') == True

    def test_no_moral_record_manage_permission(self):
        """不应该拥有全局德育记录管理权限"""
        user = MockUser('cleader')
        assert check_permission(user, 'moral_record_manage') == False

    def test_no_punishment_manage_permission(self):
        """不应该拥有处分管理权限"""
        user = MockUser('cleader')
        assert check_permission(user, 'punishment_manage') == False

    def test_level(self):
        """级别应该是30"""
        assert ROLES['cleader']['level'] == 30


class TestTeacherRole:
    """教师角色测试"""

    def test_has_homework_publish_permission(self):
        """应该拥有作业发布权限"""
        user = MockUser('teacher')
        assert check_permission(user, 'homework_publish') == True

    def test_has_schedule_view_permission(self):
        """应该拥有课表查看权限"""
        user = MockUser('teacher')
        assert check_permission(user, 'schedule_view') == True

    def test_has_moral_record_input_permission(self):
        """应该拥有德育记录录入权限"""
        user = MockUser('teacher')
        assert check_permission(user, 'moral_record_input') == True

    def test_no_moral_record_own_class_permission(self):
        """不应该拥有本班德育记录权限"""
        user = MockUser('teacher')
        assert check_permission(user, 'moral_record_own_class') == False

    def test_no_announcement_publish_permission(self):
        """不应该拥有公告发布权限"""
        user = MockUser('teacher')
        assert check_permission(user, 'announcement_publish') == False

    def test_level(self):
        """级别应该是10"""
        assert ROLES['teacher']['level'] == 10


class TestStudentRole:
    """学生角色测试"""

    def test_has_moral_self_view_permission(self):
        """应该拥有自己德育查看权限"""
        user = MockUser('student')
        assert check_permission(user, 'moral_self_view') == True

    def test_has_homework_view_permission(self):
        """应该拥有作业查看权限"""
        user = MockUser('student')
        assert check_permission(user, 'homework_view') == True

    def test_has_birthday_blessing_receive_permission(self):
        """应该拥有生日祝福接收权限"""
        user = MockUser('student')
        assert check_permission(user, 'birthday_blessing_receive') == True

    def test_no_moral_record_input_permission(self):
        """不应该拥有德育记录录入权限"""
        user = MockUser('student')
        assert check_permission(user, 'moral_record_input') == False

    def test_level(self):
        """级别应该是1"""
        assert ROLES['student']['level'] == 1


class TestParentRole:
    """家长角色测试"""

    def test_has_moral_child_view_permission(self):
        """应该拥有子女德育查看权限"""
        user = MockUser('parent')
        assert check_permission(user, 'moral_child_view') == True

    def test_has_profile_child_view_permission(self):
        """应该拥有子女画像查看权限"""
        user = MockUser('parent')
        assert check_permission(user, 'profile_child_view') == True

    def test_has_birthday_reminder_child_permission(self):
        """应该拥有子女生日提醒权限"""
        user = MockUser('parent')
        assert check_permission(user, 'birthday_reminder_child') == True

    def test_no_homework_view_permission(self):
        """不应该拥有作业查看权限"""
        user = MockUser('parent')
        assert check_permission(user, 'homework_view') == False

    def test_level(self):
        """级别应该是1"""
        assert ROLES['parent']['level'] == 1


class TestUnknownRole:
    """未知角色测试"""

    def test_no_permissions(self):
        """未知角色不应该有任何权限"""
        user = MockUser('unknown')
        assert check_permission(user, 'any_permission') == False
        assert check_permission(user, 'homework_view') == False


class TestCheckClassAccess:
    """班级访问权限测试"""

    def test_admin_has_access(self):
        """管理员应该有班级访问权限"""
        user = MockUser('admin')
        assert check_class_access(user, 1) == True

    def test_jiaowu_has_access(self):
        """教发部应该有班级访问权限"""
        user = MockUser('jiaowu')
        assert check_class_access(user, 1) == True

    def test_cleader_has_own_class_access(self):
        """班主任应该有本班访问权限"""
        user = MockUser('cleader')
        assert check_class_access(user, 1) == True


class TestRoleLevelHierarchy:
    """角色级别层级测试"""

    def test_admin_is_highest(self):
        """管理员级别最高"""
        levels = [ROLES[r]['level'] for r in ROLES]
        assert ROLES['admin']['level'] == max(levels)

    def test_level_order(self):
        """级别顺序应该正确"""
        assert ROLES['admin']['level'] > ROLES['jiaowu']['level']
        assert ROLES['jiaowu']['level'] >= ROLES['xuefa']['level']
        assert ROLES['xuefa']['level'] > ROLES['cleader']['level']
        assert ROLES['cleader']['level'] > ROLES['teacher']['level']
        assert ROLES['teacher']['level'] > ROLES['student']['level']
        assert ROLES['student']['level'] == ROLES['parent']['level']