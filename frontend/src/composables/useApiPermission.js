/**
 * API权限检查 Composable
 * 提供统一的API权限检查逻辑
 */

import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth'
import { getMyApiPermissions, checkApiPermission as checkApiPermissionApi } from '../api/modules/moral'

/**
 * API权限检查
 */
export function useApiPermission() {
  const authStore = useAuthStore()

  // API权限缓存
  const apiPermissionsCache = ref(null)
  const loading = ref(false)

  // 是否为管理员
  const isAdmin = computed(() => authStore.isAdmin)

  /**
   * 加载用户可访问的API列表
   */
  const loadMyPermissions = async () => {
    if (apiPermissionsCache.value || isAdmin.value) return

    loading.value = true
    try {
      const res = await getMyApiPermissions()
      if (res.success) {
        apiPermissionsCache.value = res.data || []
      }
    } catch (e) {
      console.error('获取API权限失败:', e)
      apiPermissionsCache.value = []
    } finally {
      loading.value = false
    }
  }

  /**
   * 检查用户是否有访问特定API的权限
   * @param {string} apiPath - API路径
   * @returns {Promise<boolean>}
   */
  const hasApiPermission = async (apiPath) => {
    // admin 直接返回 true
    if (isAdmin.value) return true

    // 加载权限缓存
    if (!apiPermissionsCache.value) {
      await loadMyPermissions()
    }

    // 检查缓存
    if (apiPermissionsCache.value) {
      return apiPermissionsCache.value.some(p => p.api_path === apiPath)
    }

    // 缓存失败时调用API检查
    try {
      const res = await checkApiPermissionApi(apiPath)
      return res.success && res.data?.has_permission
    } catch (e) {
      return false
    }
  }

  /**
   * 同步检查权限（使用缓存，不等待加载）
   * @param {string} apiPath - API路径
   * @returns {boolean}
   */
  const hasApiPermissionSync = (apiPath) => {
    // admin 直接返回 true
    if (isAdmin.value) return true

    // 使用缓存检查
    if (apiPermissionsCache.value) {
      return apiPermissionsCache.value.some(p => p.api_path === apiPath)
    }

    // 无缓存时默认返回 false（保守策略）
    return false
  }

  /**
   * 批量检查多个API权限
   * @param {string[]} apiPaths - API路径数组
   * @returns {Promise<Object>} 权限映射 { apiPath: boolean }
   */
  const checkMultiplePermissions = async (apiPaths) => {
    // admin 所有权限都为 true
    if (isAdmin.value) {
      const result = {}
      apiPaths.forEach(path => result[path] = true)
      return result
    }

    // 加载权限缓存
    if (!apiPermissionsCache.value) {
      await loadMyPermissions()
    }

    const result = {}
    for (const path of apiPaths) {
      result[path] = hasApiPermissionSync(path)
    }
    return result
  }

  /**
   * 清除权限缓存（用于切换用户等场景）
   */
  const clearCache = () => {
    apiPermissionsCache.value = null
  }

  return {
    // 属性
    loading,
    apiPermissionsCache,
    isAdmin,

    // 方法
    hasApiPermission,
    hasApiPermissionSync,
    checkMultiplePermissions,
    loadMyPermissions,
    clearCache
  }
}

/**
 * 简化版权限检查（用于单个按钮）
 * @param {string} apiPath - API路径
 * @returns {Promise<boolean>}
 */
export async function checkButtonPermission(apiPath) {
  const { hasApiPermission } = useApiPermission()
  return await hasApiPermission(apiPath)
}