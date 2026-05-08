/**
 * 路由守卫模块
 *
 * 从权威角色模块导入并重新导出，保持接口不变
 */
import {
  parseRolesFromToken,
  getDefaultDashboardByRole,
  canAccessDashboardRoute
} from '@/shared/auth/roles'

// 重新导出，保持接口不变
export { getDefaultDashboardByRole, canAccessDashboardRoute }

// 保留 getRoleFlagsFromToken 供路由守卫内部使用
export const getRoleFlagsFromToken = parseRolesFromToken
