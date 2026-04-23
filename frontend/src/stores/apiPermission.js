/**
 * API权限全局状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'
import { getMyApiPermissions } from '../api/modules/moral'

export const useApiPermissionStore = defineStore('apiPermission', () => {
  const authStore = useAuthStore()

  // API权限缓存（全局共享）
  const apiPermissionsCache = ref(null)
  const loading = ref(false)

  // 是否为管理员
  const isAdmin = computed(() => authStore.isAdmin)

  /**
   * 加载用户可访问的API列表
   */
  const loadMyPermissions = async () => {
    // admin 不需要加载，直接跳过
    if (isAdmin.value) return

    // 已经加载过且缓存存在，不重复加载
    if (apiPermissionsCache.value) return

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
   * 同步检查权限（使用缓存）
   */
  const hasApiPermissionSync = (apiPath) => {
    // admin 直接返回 true
    if (isAdmin.value) return true

    // 使用缓存检查
    if (apiPermissionsCache.value) {
      return apiPermissionsCache.value.some(p => p.api_path === apiPath)
    }

    // 无缓存时返回 false
    return false
  }

  /**
   * 清除缓存
   */
  const clearCache = () => {
    apiPermissionsCache.value = null
  }

  return {
    apiPermissionsCache,
    loading,
    isAdmin,
    loadMyPermissions,
    hasApiPermissionSync,
    clearCache
  }
})