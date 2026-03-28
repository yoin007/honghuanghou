/**
 * 权限检查函数测试
 * 测试文档中定义的7个角色的权限配置
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { createStore } from 'pinia'
import { setActivePinia } from 'pinia'

// 模拟store
const mockStore = {
  state: {
    user: null
  }
}

// 权限检查函数（从设计文档）
function checkPermission(user, permission) {
  // 如果只传一个参数，则从store获取用户
  if (typeof user === 'string') {
    permission = user
    user = mockStore.state.user
  }

  // 管理员拥有所有权限
  if (user.role === 'admin') {
    return true
  }

  // admin 权限标识只对管理员开放
  if (permission === 'admin') {
    return false
  }

  // 获取角色权限配置（与后端ROLES定义保持一致）
  const rolePermissions = {
    jiaowu: [
      'teacher_manage', 'teaching_quality_monitor', 'academic_diagnosis',
      'ai_consultation', 'report_view_all', 'class_manage', 'schedule_manage',
      'birthday_reminder', 'student_profile', 'moral_record_manage', 'event_type_manage'
    ],
    xuefa: [
      'moral_record_manage', 'punishment_manage', 'event_type_manage',
      'class_change_approve', 'report_view_all', 'student_manage', 'ai_consultation',
      'birthday_reminder', 'student_profile'
    ],
    cleader: [
      'moral_record_own_class', 'report_view_own_class', 'homework_publish',
      'announcement_publish', 'leave_approve', 'ai_consultation_own_class',
      'student_profile_own_class', 'birthday_reminder_own_class'
    ],
    teacher: [
      'homework_publish', 'schedule_view', 'student_view', 'moral_record_input'
    ],
    student: [
      'moral_self_view', 'homework_view', 'schedule_view', 'profile_self_view',
      'birthday_blessing_receive'
    ],
    parent: [
      'moral_child_view', 'profile_child_view', 'birthday_reminder_child'
    ]
  }

  const permissions = rolePermissions[user.role] || []
  return permissions.includes(permission)
}

function hasAnyPermission(permissions) {
  return permissions.some(p => checkPermission(p))
}

describe('权限检查函数', () => {
  beforeEach(() => {
    mockStore.state.user = null
  })

  describe('admin角色', () => {
    it('应该拥有所有权限', () => {
      const user = { role: 'admin' }
      expect(checkPermission(user, 'any_permission')).toBe(true)
      expect(checkPermission(user, 'teacher_manage')).toBe(true)
      expect(checkPermission(user, 'moral_record_manage')).toBe(true)
    })

    it('admin权限标识应该只对管理员开放', () => {
      const adminUser = { role: 'admin' }
      const teacherUser = { role: 'teacher' }

      expect(checkPermission(adminUser, 'admin')).toBe(true)
      expect(checkPermission(teacherUser, 'admin')).toBe(false)
    })
  })

  describe('jiaowu角色', () => {
    const user = { role: 'jiaowu' }

    it('应该拥有教师管理权限', () => {
      expect(checkPermission(user, 'teacher_manage')).toBe(true)
    })

    it('应该拥有德育记录管理权限', () => {
      expect(checkPermission(user, 'moral_record_manage')).toBe(true)
    })

    it('应该拥有事件类型管理权限', () => {
      expect(checkPermission(user, 'event_type_manage')).toBe(true)
    })

    it('不应该拥有admin权限', () => {
      expect(checkPermission(user, 'admin')).toBe(false)
    })

    it('不应该拥有本班德育记录权限', () => {
      expect(checkPermission(user, 'moral_record_own_class')).toBe(false)
    })
  })

  describe('xuefa角色', () => {
    const user = { role: 'xuefa' }

    it('应该拥有德育记录管理权限', () => {
      expect(checkPermission(user, 'moral_record_manage')).toBe(true)
    })

    it('应该拥有处分管理权限', () => {
      expect(checkPermission(user, 'punishment_manage')).toBe(true)
    })

    it('应该拥有班级变更审批权限', () => {
      expect(checkPermission(user, 'class_change_approve')).toBe(true)
    })

    it('不应该拥有教师管理权限', () => {
      expect(checkPermission(user, 'teacher_manage')).toBe(false)
    })
  })

  describe('cleader角色', () => {
    const user = { role: 'cleader' }

    it('应该拥有本班德育记录权限', () => {
      expect(checkPermission(user, 'moral_record_own_class')).toBe(true)
    })

    it('应该拥有本班报告查看权限', () => {
      expect(checkPermission(user, 'report_view_own_class')).toBe(true)
    })

    it('应该拥有作业发布权限', () => {
      expect(checkPermission(user, 'homework_publish')).toBe(true)
    })

    it('应该拥有本班AI诊疗权限', () => {
      expect(checkPermission(user, 'ai_consultation_own_class')).toBe(true)
    })

    it('不应该拥有全局德育记录管理权限', () => {
      expect(checkPermission(user, 'moral_record_manage')).toBe(false)
    })

    it('不应该拥有处分管理权限', () => {
      expect(checkPermission(user, 'punishment_manage')).toBe(false)
    })
  })

  describe('teacher角色', () => {
    const user = { role: 'teacher' }

    it('应该拥有作业发布权限', () => {
      expect(checkPermission(user, 'homework_publish')).toBe(true)
    })

    it('应该拥有课表查看权限', () => {
      expect(checkPermission(user, 'schedule_view')).toBe(true)
    })

    it('应该拥有德育记录录入权限', () => {
      expect(checkPermission(user, 'moral_record_input')).toBe(true)
    })

    it('不应该拥有本班德育记录权限', () => {
      expect(checkPermission(user, 'moral_record_own_class')).toBe(false)
    })

    it('不应该拥有公告发布权限', () => {
      expect(checkPermission(user, 'announcement_publish')).toBe(false)
    })
  })

  describe('student角色', () => {
    const user = { role: 'student' }

    it('应该拥有自己德育查看权限', () => {
      expect(checkPermission(user, 'moral_self_view')).toBe(true)
    })

    it('应该拥有作业查看权限', () => {
      expect(checkPermission(user, 'homework_view')).toBe(true)
    })

    it('应该拥有生日祝福接收权限', () => {
      expect(checkPermission(user, 'birthday_blessing_receive')).toBe(true)
    })

    it('不应该拥有德育记录录入权限', () => {
      expect(checkPermission(user, 'moral_record_input')).toBe(false)
    })
  })

  describe('parent角色', () => {
    const user = { role: 'parent' }

    it('应该拥有子女德育查看权限', () => {
      expect(checkPermission(user, 'moral_child_view')).toBe(true)
    })

    it('应该拥有子女画像查看权限', () => {
      expect(checkPermission(user, 'profile_child_view')).toBe(true)
    })

    it('应该拥有子女生日提醒权限', () => {
      expect(checkPermission(user, 'birthday_reminder_child')).toBe(true)
    })

    it('不应该拥有作业查看权限', () => {
      expect(checkPermission(user, 'homework_view')).toBe(false)
    })
  })

  describe('hasAnyPermission函数', () => {
    it('应该返回true当有任一权限时', () => {
      mockStore.state.user = { role: 'cleader' }
      expect(hasAnyPermission(['homework_publish', 'punishment_manage'])).toBe(true)
    })

    it('应该返回false当没有任何权限时', () => {
      mockStore.state.user = { role: 'student' }
      expect(hasAnyPermission(['teacher_manage', 'punishment_manage'])).toBe(false)
    })
  })

  describe('未知角色', () => {
    it('应该没有任何权限', () => {
      const user = { role: 'unknown' }
      expect(checkPermission(user, 'any_permission')).toBe(false)
    })
  })
})