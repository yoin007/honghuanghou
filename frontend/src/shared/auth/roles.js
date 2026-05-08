/**
 * 角色解析权威模块
 *
 * 统一 token 解析逻辑，避免散落在 auth.js、guards.js、useNavigationPermissions.js
 *
 * 提供：
 * - parseRolesFromToken(token) → { admin, jiaowu, xuefa, cleader, teacher }
 * - getDefaultDashboardByRole(token) → '/dashboard/xxx'
 * - canAccessDashboardRoute(meta, token) → boolean
 * - canViewDashboard(roleFlags, dashboardType) → boolean
 */

/**
 * 从 JWT token 解析角色标志
 * @param {string} token - JWT token
 * @returns {{ admin: boolean, jiaowu: boolean, xuefa: boolean, cleader: boolean, teacher: boolean }}
 */
export const parseRolesFromToken = (token) => {
  const flags = {
    admin: false,
    jiaowu: false,
    xuefa: false,
    g_leader: false,
    cleader: false,
    teacher: true // 默认所有用户都有 teacher 权限
  }

  if (!token) return flags

  try {
    const base64Url = token.split('.')[1]
    if (!base64Url) return flags
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(window.atob(base64))
    const roleText = String(payload.role || '')
    const roles = roleText.split('/').filter(Boolean)

    // admin 角色
    flags.admin = roles.includes('admin') || roleText === 'admin'

    // jiaowu 角色（admin 继承）
    flags.jiaowu = flags.admin || roles.includes('jiaowu') || roleText === 'jiaowu'

    // xuefa 角色（admin 继承）
    flags.xuefa = flags.admin || roles.includes('xuefa') || roleText === 'xuefa'

    // g_leader 角色（年级主任，admin 继承）
    flags.g_leader = flags.admin || roles.includes('g_leader') || roleText === 'g_leader'

    // cleader 角色（班主任，不继承）
    flags.cleader = roles.includes('cleader') || roleText === 'cleader'
  } catch {
    return flags
  }

  return flags
}

/**
 * 根据角色获取默认驾驶舱入口
 *
 * 优先级：admin > jiaowu > xuefa > cleader > teacher
 *
 * @param {string} token - JWT token
 * @returns {string} 默认驾驶舱路径
 */
export const getDefaultDashboardByRole = (token) => {
  const flags = parseRolesFromToken(token)

  if (flags.admin) return '/dashboard/system'
  if (flags.jiaowu) return '/dashboard/teaching'
  if (flags.xuefa) return '/dashboard/moral'
  if (flags.cleader) return '/dashboard/class'

  return '/dashboard/teacher'
}

/**
 * 检查是否可以访问指定驾驶舱路由
 *
 * @param {object} meta - 路由 meta 对象（包含 dashboardRoles）
 * @param {string} token - JWT token
 * @returns {boolean}
 */
export const canAccessDashboardRoute = (meta = {}, token = '') => {
  const requiredRoles = meta.dashboardRoles
  if (!Array.isArray(requiredRoles) || requiredRoles.length === 0) return true

  const flags = parseRolesFromToken(token)
  return requiredRoles.some(role => flags[role] === true)
}

/**
 * 检查是否可以查看指定类型的驾驶舱
 *
 * 用于导航菜单显示判断
 *
 * @param {{ admin: boolean, jiaowu: boolean, xuefa: boolean, cleader: boolean }} roleFlags - 角色标志
 * @param {string} dashboardType - 驾驶舱类型：'class' | 'moral' | 'invigilation' | 'system'
 * @returns {boolean}
 */
export const canViewDashboard = (roleFlags, dashboardType) => {
  switch (dashboardType) {
    case 'class':
      return roleFlags.admin || roleFlags.jiaowu || roleFlags.xuefa || roleFlags.g_leader || roleFlags.cleader
    case 'moral':
      return roleFlags.admin || roleFlags.jiaowu || roleFlags.xuefa || roleFlags.g_leader || roleFlags.cleader
    case 'grade':  // 年级驾驶舱
      return roleFlags.admin || roleFlags.jiaowu || roleFlags.xuefa || roleFlags.g_leader
    case 'invigilation':
      return roleFlags.admin || roleFlags.jiaowu
    case 'system':
      return roleFlags.admin
    default:
      return false
  }
}