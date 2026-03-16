import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

/**
 * 权限检查 Composable
 * 提供统一的权限检查逻辑
 */
export function usePermission() {
  const authStore = useAuthStore()

  // 是否为管理员
  const isAdmin = computed(() => authStore.isAdmin)

  // 当前用户角色
  const role = computed(() => authStore.role)

  // 当前用户名
  const username = computed(() => authStore.username)

  /**
   * 检查是否具有指定角色
   * @param {string} targetRole - 目标角色 (如 'teacher', 'admin', 'cleader')
   * @returns {boolean}
   */
  const hasRole = (targetRole) => {
    if (!role.value) return false
    return role.value.includes(targetRole)
  }

  /**
   * 检查是否是教师（含学法权限）
   * @returns {boolean}
   */
  const isTeacher = computed(() => hasRole('teacher'))

  /**
   * 检查是否是班主任/班级领导
   * @returns {boolean}
   */
  const isCleader = computed(() => hasRole('cleader'))

  /**
   * 检查是否是超级管理员
   * @returns {boolean}
   */
  const isSuperAdmin = computed(() => role.value === 'admin')

  /**
   * 检查是否具有任何管理权限
   * @returns {boolean}
   */
  const hasAdminRole = computed(() => {
    return isAdmin.value || hasRole('teacher') || hasRole('cleader')
  })

  /**
   * 检查是否是资源所有者
   * @param {string} ownerUsername - 资源所有者用户名
   * @returns {boolean}
   */
  const isOwner = (ownerUsername) => {
    return username.value === ownerUsername
  }

  /**
   * 检查是否可以编辑（管理员或所有者）
   * @param {string} ownerUsername - 资源所有者用户名
   * @returns {boolean}
   */
  const canEdit = (ownerUsername) => {
    return isAdmin.value || isOwner(ownerUsername)
  }

  /**
   * 检查是否可以删除（仅管理员）
   * @returns {boolean}
   */
  const canDelete = computed(() => isAdmin.value)

  /**
   * 检查是否可以发布作业（管理员或教师）
   * @returns {boolean}
   */
  const canPublishHomework = computed(() => {
    return isAdmin.value || isTeacher.value
  })

  /**
   * 检查是否可以管理教师（仅管理员）
   * @returns {boolean}
   */
  const canManageTeachers = computed(() => isAdmin.value)

  /**
   * 检查是否可以管理系统（仅管理员）
   * @returns {boolean}
   */
  const canManageSystem = computed(() => isAdmin.value)

  return {
    // 属性
    isAdmin,
    role,
    username,
    // 计算属性
    isTeacher,
    isCleader,
    isSuperAdmin,
    hasAdminRole,
    canDelete,
    canPublishHomework,
    canManageTeachers,
    canManageSystem,
    // 方法
    hasRole,
    isOwner,
    canEdit
  }
}
