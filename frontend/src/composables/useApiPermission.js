/**
 * API权限检查 Composable
 * 使用全局 Pinia Store 管理权限缓存
 */

import { useApiPermissionStore } from '../stores/apiPermission'

/**
 * API权限检查（使用全局 store）
 */
export function useApiPermission() {
  const store = useApiPermissionStore()

  return {
    loading: store.loading,
    apiPermissionsCache: store.apiPermissionsCache,
    isAdmin: store.isAdmin,

    hasApiPermission: async (apiPath) => {
      return store.hasApiPermissionSync(apiPath)
    },
    hasApiPermissionSync: store.hasApiPermissionSync,
    checkMultiplePermissions: async (apiPaths) => {
      const result = {}
      for (const path of apiPaths) {
        result[path] = store.hasApiPermissionSync(path)
      }
      return result
    },
    loadMyPermissions: store.loadMyPermissions,
    clearCache: store.clearCache
  }
}

/**
 * 简化版权限检查（用于单个按钮）
 */
export async function checkButtonPermission(apiPath) {
  const store = useApiPermissionStore()
  return store.hasApiPermissionSync(apiPath)
}