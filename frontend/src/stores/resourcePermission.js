/**
 * 统一资源权限状态管理
 *
 * 整合三层鉴权：
 * - 路由权限：canAccessRoute
 * - API权限：canCallApi
 * - 菜单权限：canShowMenu
 *
 * 基于 authStore 的角色标志 + apiPermission 缓存
 */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { useAuthStore } from './auth'
import { useApiPermissionStore } from './apiPermission'

// 资源定义：菜单 + 路由 + API的权限配置
const RESOURCE_CONFIG = {
  // === 公开菜单（无需登录） ===
  menus: {
    public: [
      { key: 'homework', label: '班级作业', route: '/homework', roles: ['all'] },
      { key: 'basic-info', label: '班级信息', route: '/basic-info', roles: ['all'] },
      { key: 'class-students', label: '班级学生', route: '/class-students', roles: ['all'] },
      { key: 'announcement', label: '班级公告', route: '/announcement', roles: ['all'] },
      { key: 'delay-application', label: '延时申请', route: '/delay-application', roles: ['all'] },
      { key: 'leave-record', label: '请假记录', route: '/leave-record', roles: ['all'] },
      { key: 'schedule', label: '课程表', route: '/schedule', roles: ['all'] },
      { key: 'schedules', label: '总课表', route: '/schedules', roles: ['all'] },
      { key: 'random-call', label: '随机点名', route: '/random-call', roles: ['all'] },
      { key: 'loud-pk', label: '大声PK', route: '/loud-pk', roles: ['all'] },
    ],

    teacher: [
      { key: 'publish-homework', label: '发布作业', route: '/publish-homework', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'publish-announcement', label: '发布公告', route: '/publish-announcement', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'file-upload', label: '文件上传', route: '/file-upload', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'my-files', label: '我的文件', route: '/my-files', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
    ],

    jiaowu: [
      { key: 'admin-files', label: '文件管理', route: '/admin-files', roles: ['jiaowu', 'admin'] },
      { key: 'admin-files-done', label: '已查阅文件', route: '/admin-files-done', roles: ['jiaowu', 'admin'] },
      { key: 'upload-schedule', label: '更新课表', route: '/upload-schedule', roles: ['jiaowu', 'admin'] },
      { key: 'invigilation', label: '监考安排', route: '/invigilation', roles: ['jiaowu', 'admin'] },
    ],

    moral: [
      { key: 'moral-daily', label: '日常表现', route: '/moral/daily-record', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-school', label: '校级事件', route: '/moral/school-event', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-task', label: '德育任务', route: '/moral/task', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-punishment', label: '处分管理', route: '/moral/punishment', roles: ['xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-collective', label: '集体事件', route: '/moral/collective', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-evaluation', label: '评价查询', route: '/moral/evaluation', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-moment', label: '点滴记录', route: '/moral/moment', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-lifebook', label: '一生一册', route: '/moral/lifebook', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-profile', label: '学生画像', route: '/moral/profile', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-birthday', label: '生日提醒', route: '/moral/birthday', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-student-manage', label: '学生管理', route: '/moral/config/student', roles: ['g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'moral-config', label: '德育配置', route: '/moral/config', roles: ['xuefa', 'jiaowu', 'admin'] },
    ],

    dashboard: [
      { key: 'dashboard-overview', label: '总览', route: '/dashboard', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'dashboard-moral', label: '德育驾驶舱', route: '/dashboard/moral', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'dashboard-teaching', label: '教务驾驶舱', route: '/dashboard/teaching', roles: ['jiaowu', 'admin'] },
      { key: 'dashboard-class', label: '班级驾驶舱', route: '/dashboard/class', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'dashboard-grade', label: '年级驾驶舱', route: '/dashboard/grade', roles: ['g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'dashboard-teacher', label: '教师工作台', route: '/dashboard/teacher', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
      { key: 'dashboard-invigilation', label: '监考驾驶舱', route: '/dashboard/invigilation', roles: ['jiaowu', 'admin'] },
      { key: 'dashboard-system', label: '系统运维', route: '/dashboard/system', roles: ['admin'] },
    ],

    system: [
      { key: 'member-manage', label: '会员管理', route: '/member-manage', roles: ['admin'] },
      { key: 'permission-manage', label: '权限管理', route: '/permission-manage', roles: ['admin'] },
      { key: 'task-manage', label: '任务管理', route: '/task-manage', roles: ['admin'] },
      { key: 'system-monitor', label: '系统监控', route: '/system-monitor', roles: ['admin'] },
      { key: 'teacher-manage', label: '教师管理', route: '/teacher-manage', roles: ['admin'] },
    ],
  },

  // 菜单分组定义
  menuGroups: [
    { key: 'class', label: '班级', items: 'public', requiresAuth: false, itemFilter: ['homework', 'basic-info', 'class-students', 'announcement', 'delay-application', 'leave-record'] },
    { key: 'schedule', label: '课表', items: 'public', requiresAuth: false, itemFilter: ['schedule', 'schedules'] },
    { key: 'fun', label: '趣味', items: 'public', requiresAuth: false, itemFilter: ['random-call', 'loud-pk'] },
    { key: 'teacher', label: '教师', items: 'teacher', requiresAuth: true },
    { key: 'jiaowu', label: '教务', items: 'jiaowu', requiresAuth: true, roles: ['jiaowu', 'admin'] },
    { key: 'moral', label: '德育评价', items: 'moral', requiresAuth: true, roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'] },
    { key: 'dashboard', label: '驾驶舱', items: 'dashboard', requiresAuth: true },
    { key: 'system', label: '系统管理', items: 'system', requiresAuth: true, roles: ['admin'] },
  ],
}

export const useResourcePermissionStore = defineStore('resourcePermission', () => {
  const authStore = useAuthStore()
  const apiPermissionStore = useApiPermissionStore()

  // 用户角色集合（从authStore提取）
  const userRoles = computed(() => {
    const roles = []
    if (authStore.isAdmin) roles.push('admin')
    if (authStore.isJiaowu) roles.push('jiaowu')
    if (authStore.isXuefa) roles.push('xuefa')
    if (authStore.isGleader) roles.push('g_leader')
    if (authStore.isCleader) roles.push('cleader')
    if (authStore.isTeacher) roles.push('teacher')
    return roles
  })

  // 是否登录
  const isLoggedIn = computed(() => authStore.isLoggedIn)

  /**
   * 检查用户是否有某个角色
   */
  const hasRole = (role) => {
    if (role === 'all') return true
    if (role === 'admin') return authStore.isAdmin
    return userRoles.value.includes(role)
  }

  /**
   * 检查用户是否有任意一个指定角色
   */
  const hasAnyRole = (roles) => {
    if (!roles || roles.length === 0) return true
    return roles.some(r => hasRole(r))
  }

  /**
   * 检查菜单项是否可见
   */
  const canShowMenu = (menuKey) => {
    const allMenus = Object.values(RESOURCE_CONFIG.menus).flat()
    const item = allMenus.find(m => m.key === menuKey)
    if (!item) return false

    // 'all' 表示公开
    if (item.roles.includes('all')) return true

    // 需要登录
    if (!isLoggedIn.value) return false

    // 检查角色
    return hasAnyRole(item.roles)
  }

  /**
   * 检查路由是否可访问
   */
  const canAccessRoute = (routePath) => {
    const allMenus = Object.values(RESOURCE_CONFIG.menus).flat()
    const item = allMenus.find(m => m.route === routePath)

    // 未定义的资源默认需要登录
    if (!item) return isLoggedIn.value

    if (item.roles.includes('all')) return true
    if (!isLoggedIn.value) return false
    return hasAnyRole(item.roles)
  }

  /**
   * 检查API是否可调用（使用apiPermission缓存）
   */
  const canCallApi = (apiPath) => {
    // admin 拥有所有权限
    if (authStore.isAdmin) return true

    // 使用API权限缓存
    return apiPermissionStore.hasApiPermissionSync(apiPath)
  }

  /**
   * 构建动态菜单树
   */
  const buildMenuTree = () => {
    const visibleGroups = []

    for (const group of RESOURCE_CONFIG.menuGroups) {
      // 检查分组权限
      if (group.requiresAuth && !isLoggedIn.value) continue
      if (group.roles && !hasAnyRole(group.roles)) continue

      // 过滤可见菜单项
      let items = RESOURCE_CONFIG.menus[group.items] || []
      if (group.itemFilter) {
        items = items.filter(item => group.itemFilter.includes(item.key))
      }

      const visibleItems = items.filter(item => canShowMenu(item.key))

      if (visibleItems.length > 0) {
        visibleGroups.push({
          key: group.key,
          label: group.label,
          items: visibleItems
        })
      }
    }

    return visibleGroups
  }

  /**
   * 获取用户可访问的所有路由
   */
  const getAccessibleRoutes = () => {
    const allMenus = Object.values(RESOURCE_CONFIG.menus).flat()
    return allMenus
      .filter(item => canShowMenu(item.key))
      .map(item => item.route)
  }

  return {
    userRoles,
    isLoggedIn,
    hasRole,
    hasAnyRole,
    canShowMenu,
    canAccessRoute,
    canCallApi,
    buildMenuTree,
    getAccessibleRoutes,
    RESOURCE_CONFIG,
  }
})