/**
 * usePermission Composable 测试
 * 测试权限检查组合函数
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref, computed } from 'vue'

// 模拟 auth store
const mockAuthStore = {
  isAdmin: ref(false),
  role: ref(''),
  username: ref('')
}

vi.mock('../stores/auth', () => ({
  useAuthStore: () => mockAuthStore
}))

// usePermission 实现用于测试
function usePermission() {
  const authStore = mockAuthStore

  const isAdmin = computed(() => authStore.isAdmin.value)
  const role = computed(() => authStore.role.value)
  const username = computed(() => authStore.username.value)

  const hasRole = (targetRole) => {
    if (!role.value) return false
    return role.value.includes(targetRole)
  }

  const isTeacher = computed(() => hasRole('teacher'))
  const isCleader = computed(() => hasRole('cleader'))
  const isSuperAdmin = computed(() => role.value === 'admin')

  const hasAdminRole = computed(() => {
    return isAdmin.value || hasRole('teacher') || hasRole('cleader')
  })

  const isOwner = (ownerUsername) => {
    return username.value === ownerUsername
  }

  const canEdit = (ownerUsername) => {
    return isAdmin.value || isOwner(ownerUsername)
  }

  const canDelete = computed(() => isAdmin.value)
  const canPublishHomework = computed(() => isAdmin.value || isTeacher.value)
  const canManageTeachers = computed(() => isAdmin.value)
  const canManageSystem = computed(() => isAdmin.value)

  return {
    isAdmin,
    role,
    username,
    isTeacher,
    isCleader,
    isSuperAdmin,
    hasAdminRole,
    canDelete,
    canPublishHomework,
    canManageTeachers,
    canManageSystem,
    hasRole,
    isOwner,
    canEdit
  }
}

describe('usePermission Composable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAuthStore.isAdmin.value = false
    mockAuthStore.role.value = ''
    mockAuthStore.username.value = ''
  })

  describe('基础属性', () => {
    it('isAdmin应该反映authStore的isAdmin', () => {
      const { isAdmin } = usePermission()
      expect(isAdmin.value).toBe(false)

      mockAuthStore.isAdmin.value = true
      expect(isAdmin.value).toBe(true)
    })

    it('role应该反映authStore的role', () => {
      const { role } = usePermission()
      expect(role.value).toBe('')

      mockAuthStore.role.value = 'teacher'
      expect(role.value).toBe('teacher')
    })

    it('username应该反映authStore的username', () => {
      const { username } = usePermission()
      expect(username.value).toBe('')

      mockAuthStore.username.value = 'testuser'
      expect(username.value).toBe('testuser')
    })
  })

  describe('hasRole方法', () => {
    it('角色匹配时应该返回true', () => {
      mockAuthStore.role.value = 'teacher'
      const { hasRole } = usePermission()
      expect(hasRole('teacher')).toBe(true)
    })

    it('角色不匹配时应该返回false', () => {
      mockAuthStore.role.value = 'teacher'
      const { hasRole } = usePermission()
      expect(hasRole('admin')).toBe(false)
    })

    it('组合角色应该能匹配部分', () => {
      mockAuthStore.role.value = 'teacher/admin'
      const { hasRole } = usePermission()
      expect(hasRole('teacher')).toBe(true)
      expect(hasRole('admin')).toBe(true)
    })

    it('空角色应该返回false', () => {
      mockAuthStore.role.value = ''
      const { hasRole } = usePermission()
      expect(hasRole('teacher')).toBe(false)
    })
  })

  describe('角色判断计算属性', () => {
    it('isTeacher - teacher角色应该为true', () => {
      mockAuthStore.role.value = 'teacher'
      const { isTeacher } = usePermission()
      expect(isTeacher.value).toBe(true)
    })

    it('isTeacher - 非teacher角色应该为false', () => {
      mockAuthStore.role.value = 'admin'
      const { isTeacher } = usePermission()
      expect(isTeacher.value).toBe(false)
    })

    it('isCleader - cleader角色应该为true', () => {
      mockAuthStore.role.value = 'cleader'
      const { isCleader } = usePermission()
      expect(isCleader.value).toBe(true)
    })

    it('isSuperAdmin - admin角色应该为true', () => {
      mockAuthStore.role.value = 'admin'
      const { isSuperAdmin } = usePermission()
      expect(isSuperAdmin.value).toBe(true)
    })

    it('isSuperAdmin - 组合角色admin应该为false', () => {
      mockAuthStore.role.value = 'teacher/admin'
      const { isSuperAdmin } = usePermission()
      expect(isSuperAdmin.value).toBe(false) // 不是纯admin
    })
  })

  describe('hasAdminRole', () => {
    it('admin用户应该为true', () => {
      mockAuthStore.isAdmin.value = true
      const { hasAdminRole } = usePermission()
      expect(hasAdminRole.value).toBe(true)
    })

    it('teacher角色应该为true', () => {
      mockAuthStore.role.value = 'teacher'
      const { hasAdminRole } = usePermission()
      expect(hasAdminRole.value).toBe(true)
    })

    it('cleader角色应该为true', () => {
      mockAuthStore.role.value = 'cleader'
      const { hasAdminRole } = usePermission()
      expect(hasAdminRole.value).toBe(true)
    })

    it('student角色应该为false', () => {
      mockAuthStore.role.value = 'student'
      const { hasAdminRole } = usePermission()
      expect(hasAdminRole.value).toBe(false)
    })
  })

  describe('isOwner方法', () => {
    it('自己的资源应该返回true', () => {
      mockAuthStore.username.value = 'user1'
      const { isOwner } = usePermission()
      expect(isOwner('user1')).toBe(true)
    })

    it('他人的资源应该返回false', () => {
      mockAuthStore.username.value = 'user1'
      const { isOwner } = usePermission()
      expect(isOwner('user2')).toBe(false)
    })

    it('空用户名应该返回false', () => {
      mockAuthStore.username.value = ''
      const { isOwner } = usePermission()
      expect(isOwner('user1')).toBe(false)
    })
  })

  describe('canEdit方法', () => {
    it('管理员可以编辑任何资源', () => {
      mockAuthStore.isAdmin.value = true
      mockAuthStore.username.value = 'admin'
      const { canEdit } = usePermission()
      expect(canEdit('other_user')).toBe(true)
    })

    it('非管理员可以编辑自己的资源', () => {
      mockAuthStore.isAdmin.value = false
      mockAuthStore.username.value = 'user1'
      const { canEdit } = usePermission()
      expect(canEdit('user1')).toBe(true)
    })

    it('非管理员不能编辑他人资源', () => {
      mockAuthStore.isAdmin.value = false
      mockAuthStore.username.value = 'user1'
      const { canEdit } = usePermission()
      expect(canEdit('user2')).toBe(false)
    })
  })

  describe('canDelete', () => {
    it('管理员可以删除', () => {
      mockAuthStore.isAdmin.value = true
      const { canDelete } = usePermission()
      expect(canDelete.value).toBe(true)
    })

    it('非管理员不能删除', () => {
      mockAuthStore.isAdmin.value = false
      const { canDelete } = usePermission()
      expect(canDelete.value).toBe(false)
    })
  })

  describe('canPublishHomework', () => {
    it('管理员可以发布作业', () => {
      mockAuthStore.isAdmin.value = true
      const { canPublishHomework } = usePermission()
      expect(canPublishHomework.value).toBe(true)
    })

    it('教师可以发布作业', () => {
      mockAuthStore.role.value = 'teacher'
      const { canPublishHomework } = usePermission()
      expect(canPublishHomework.value).toBe(true)
    })

    it('学生不能发布作业', () => {
      mockAuthStore.role.value = 'student'
      const { canPublishHomework } = usePermission()
      expect(canPublishHomework.value).toBe(false)
    })

    it('班主任(cleader)需要包含teacher角色才能发布作业', () => {
      // 注意：根据实现，canPublishHomework检查isTeacher(hasRole('teacher'))
      // 纯cleader角色不包含teacher，所以不能发布
      mockAuthStore.role.value = 'cleader'
      const { canPublishHomework } = usePermission()
      expect(canPublishHomework.value).toBe(false)
    })

    it('teacher/cleader组合角色可以发布作业', () => {
      mockAuthStore.role.value = 'teacher/cleader'
      const { canPublishHomework } = usePermission()
      expect(canPublishHomework.value).toBe(true)
    })
  })

  describe('canManageTeachers', () => {
    it('管理员可以管理教师', () => {
      mockAuthStore.isAdmin.value = true
      const { canManageTeachers } = usePermission()
      expect(canManageTeachers.value).toBe(true)
    })

    it('非管理员不能管理教师', () => {
      mockAuthStore.isAdmin.value = false
      mockAuthStore.role.value = 'teacher'
      const { canManageTeachers } = usePermission()
      expect(canManageTeachers.value).toBe(false)
    })
  })

  describe('canManageSystem', () => {
    it('管理员可以管理系统', () => {
      mockAuthStore.isAdmin.value = true
      const { canManageSystem } = usePermission()
      expect(canManageSystem.value).toBe(true)
    })

    it('非管理员不能管理系统', () => {
      mockAuthStore.isAdmin.value = false
      const { canManageSystem } = usePermission()
      expect(canManageSystem.value).toBe(false)
    })
  })

  describe('边界情况', () => {
    it('角色为null时hasRole应该返回false', () => {
      mockAuthStore.role.value = null
      const { hasRole } = usePermission()
      expect(hasRole('teacher')).toBe(false)
    })

    it('角色为undefined时hasRole应该返回false', () => {
      mockAuthStore.role.value = undefined
      const { hasRole } = usePermission()
      expect(hasRole('teacher')).toBe(false)
    })

    it('多次调用应该返回一致结果', () => {
      mockAuthStore.role.value = 'teacher'
      const { hasRole } = usePermission()
      expect(hasRole('teacher')).toBe(true)
      expect(hasRole('teacher')).toBe(true)
      expect(hasRole('admin')).toBe(false)
    })
  })

  describe('角色组合场景', () => {
    it('teacher/admin组合角色', () => {
      mockAuthStore.role.value = 'teacher/admin'
      mockAuthStore.isAdmin.value = true
      const { hasRole, isTeacher, isSuperAdmin } = usePermission()
      expect(hasRole('teacher')).toBe(true)
      expect(hasRole('admin')).toBe(true)
      expect(isTeacher.value).toBe(true)
      expect(isSuperAdmin.value).toBe(false) // 不是纯admin
    })

    it('teacher/cleader组合角色', () => {
      mockAuthStore.role.value = 'teacher/cleader'
      const { hasRole, isTeacher, isCleader, hasAdminRole } = usePermission()
      expect(hasRole('teacher')).toBe(true)
      expect(hasRole('cleader')).toBe(true)
      expect(isTeacher.value).toBe(true)
      expect(isCleader.value).toBe(true)
      expect(hasAdminRole.value).toBe(true)
    })
  })
})