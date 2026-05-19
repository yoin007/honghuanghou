/**
 * 统一资源权限状态管理
 *
 * 整合三层鉴权：
 * - 路由权限：canAccessRoute
 * - API权限：canCallApi
 * - 菜单权限：canShowMenu
 *
 * 基于 authStore 的角色标志 + apiPermission 缓存
 * 支持动态菜单配置（从后端加载）
 */

import { defineStore } from 'pinia'
import { computed, ref, reactive } from 'vue'
import { useAuthStore } from './auth'
import { useApiPermissionStore } from './apiPermission'
import httpClient from '../shared/api/httpClient'

// 静态资源配置（作为 fallback）
const STATIC_RESOURCE_CONFIG = {
  // === 公开菜单（无需登录） ===
  menus: {
    public: [
      { key: 'homework', label: '班级作业', route: '/homework', roles: ['all'], sort_order: 10 },
      { key: 'basic-info', label: '班级信息', route: '/basic-info', roles: ['all'], sort_order: 20 },
      { key: 'class-students', label: '班级学生', route: '/class-students', roles: ['all'], sort_order: 30 },
      { key: 'announcement', label: '班级公告', route: '/announcement', roles: ['all'], sort_order: 40 },
      { key: 'delay-application', label: '延时申请', route: '/delay-application', roles: ['all'], sort_order: 50 },
      { key: 'leave-record', label: '请假记录', route: '/leave-record', roles: ['all'], sort_order: 60 },
      { key: 'schedule', label: '课程表', route: '/schedule', roles: ['all'], sort_order: 70 },
      { key: 'schedules', label: '总课表', route: '/schedules', roles: ['all'], sort_order: 80 },
      { key: 'random-call', label: '随机点名', route: '/random-call', roles: ['all'], sort_order: 90 },
      { key: 'loud-pk', label: '大声PK', route: '/loud-pk', roles: ['all'], sort_order: 100 },
    ],

    teacher: [
      { key: 'publish-homework', label: '发布作业', route: '/publish-homework', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 10 },
      { key: 'publish-announcement', label: '发布公告', route: '/publish-announcement', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 20 },
      { key: 'file-upload', label: '文件上传', route: '/file-upload', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 30 },
      { key: 'my-files', label: '我的文件', route: '/my-files', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 40 },
      { key: 'teacher-todo', label: '我的待办', route: '/teacher/todo', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 50 },
      { key: 'teacher-todo-group', label: '协作群组', route: '/teacher/todo-group', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 55 },
    ],

    jiaowu: [
      { key: 'admin-files', label: '文件管理', route: '/admin-files', roles: ['jiaowu', 'admin'], sort_order: 10 },
      { key: 'admin-files-done', label: '已查阅文件', route: '/admin-files-done', roles: ['jiaowu', 'admin'], sort_order: 20 },
      { key: 'upload-schedule', label: '更新课表', route: '/upload-schedule', roles: ['jiaowu', 'admin'], sort_order: 30 },
      { key: 'invigilation', label: '监考安排', route: '/invigilation', roles: ['jiaowu', 'admin'], sort_order: 40 },
    ],

    moral: [
      { key: 'moral-daily', label: '日常表现', route: '/moral/daily-record', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 10 },
      { key: 'moral-school', label: '校级事件', route: '/moral/school-event', roles: ['xuefa', 'admin'], sort_order: 20 },
      { key: 'moral-task', label: '德育任务', route: '/moral/task', roles: ['xuefa', 'admin'], sort_order: 30 },
      { key: 'moral-punishment', label: '处分管理', route: '/moral/punishment', roles: ['xuefa', 'admin'], sort_order: 40 },
      { key: 'moral-collective', label: '集体事件', route: '/moral/collective', roles: ['xuefa', 'admin'], sort_order: 50 },
      { key: 'moral-evaluation', label: '评价查询', route: '/moral/evaluation', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 60 },
      { key: 'moral-moment', label: '点滴记录', route: '/moral/moment', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 70 },
      { key: 'moral-lifebook', label: '一生一册', route: '/moral/lifebook', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 80 },
      { key: 'moral-profile', label: '学生画像', route: '/moral/profile', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 90 },
      { key: 'moral-consultation', label: 'AI诊疗', route: '/moral/consultation', roles: ['cleader', 'g_leader', 'xuefa', 'admin'], sort_order: 95 },
      { key: 'moral-birthday', label: '生日提醒', route: '/moral/birthday', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 100 },
      { key: 'moral-student-manage', label: '学生管理', route: '/moral/config/student', roles: ['g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 110 },
      { key: 'moral-config', label: '德育配置', route: '/moral/config', roles: ['xuefa', 'jiaowu', 'admin'], sort_order: 120 },
    ],

    dashboard: [
      { key: 'dashboard-overview', label: '总览', route: '/dashboard', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 10 },
      { key: 'dashboard-moral', label: '德育驾驶舱', route: '/dashboard/moral', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 20 },
      { key: 'dashboard-teaching', label: '教务驾驶舱', route: '/dashboard/teaching', roles: ['jiaowu', 'admin'], sort_order: 30 },
      { key: 'dashboard-class', label: '班级驾驶舱', route: '/dashboard/class', roles: ['cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 40 },
      { key: 'dashboard-grade', label: '年级驾驶舱', route: '/dashboard/grade', roles: ['g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 50 },
      { key: 'dashboard-teacher', label: '教师工作台', route: '/dashboard/teacher', roles: ['teacher', 'cleader', 'g_leader', 'xuefa', 'jiaowu', 'admin'], sort_order: 60 },
      { key: 'dashboard-invigilation', label: '监考驾驶舱', route: '/dashboard/invigilation', roles: ['jiaowu', 'admin'], sort_order: 70 },
      { key: 'dashboard-system', label: '系统运维', route: '/dashboard/system', roles: ['admin'], sort_order: 80 },
    ],

    system: [
      { key: 'member-manage', label: '会员管理', route: '/member-manage', roles: ['admin'], sort_order: 10 },
      { key: 'permission-manage', label: '权限管理', route: '/permission-manage', roles: ['admin'], sort_order: 20 },
      { key: 'task-manage', label: '任务管理', route: '/task-manage', roles: ['admin'], sort_order: 30 },
      { key: 'system-monitor', label: '系统监控', route: '/system-monitor', roles: ['admin'], sort_order: 40 },
      { key: 'teacher-manage', label: '教师管理', route: '/teacher-manage', roles: ['admin'], sort_order: 50 },
      { key: 'moral-api-permission', label: 'API权限', route: '/moral/config/api-permission', roles: ['admin'], sort_order: 60 },
      { key: 'moral-database', label: '数据库管理', route: '/moral/config/database', roles: ['admin'], sort_order: 70 },
      { key: 'moral-database-backup', label: '数据库备份', route: '/moral/config/database-backup', roles: ['admin'], sort_order: 75 },
      { key: 'moral-menu-permission', label: '菜单权限', route: '/moral/config/menu-permission', roles: ['admin'], sort_order: 80 },
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

  // 动态加载的菜单配置（从后端加载）
  const dynamicMenuConfig = ref(null)
  const configLoaded = ref(false)

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

  // 合后的资源配置（动态配置优先，静态配置补充缺失项）
  const mergedConfig = computed(() => {
    // 如果有动态配置且已加载，使用动态配置 + 静态配置补充
    if (dynamicMenuConfig.value && configLoaded.value) {
      // 将后端配置转换为前端格式
      const menus = {}
      const menuMap = new Map()

      // 按 menu_group 分组
      for (const item of dynamicMenuConfig.value) {
        if (!item.is_active) continue // 跳过禁用的菜单

        const group = item.menu_group
        if (!menus[group]) menus[group] = []

        const menuItem = {
          key: item.menu_key,
          label: item.menu_label,
          route: item.menu_route,
          roles: item.is_public ? ['all'] : item.allowed_roles,
          sort_order: item.sort_order || 0
        }

        menus[group].push(menuItem)
        menuMap.set(item.menu_key, menuItem)
      }

      // 动态配置已加载，完全信任数据库配置，不做静态补充
      // 避免静态配置与数据库配置的角色定义冲突

      // 按 sort_order 排序每个分组
      for (const groupKey of Object.keys(menus)) {
        menus[groupKey].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
      }

      return {
        menus,
        menuGroups: STATIC_RESOURCE_CONFIG.menuGroups, // 分组定义保持静态
        menuMap // 用于快速查找
      }
    }

    // 使用静态配置作为 fallback
    const menuMap = new Map()
    for (const items of Object.values(STATIC_RESOURCE_CONFIG.menus)) {
      for (const item of items) {
        menuMap.set(item.key, item)
      }
    }

    // 按 sort_order 排序每个分组
    const menus = {}
    for (const [groupKey, items] of Object.entries(STATIC_RESOURCE_CONFIG.menus)) {
      menus[groupKey] = [...items].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
    }

    return {
      menus,
      menuGroups: STATIC_RESOURCE_CONFIG.menuGroups,
      menuMap
    }
  })

  /**
   * 从后端加载菜单权限配置
   * 未登录时静默跳过，不触发 401 弹窗
   */
  const loadMenuConfigFromBackend = async () => {
    // 未登录时跳过，避免触发 401 弹窗
    const token = localStorage.getItem('token')
    if (!token) {
      configLoaded.value = false
      return false
    }

    try {
      const res = await httpClient.get('/api/moral/menu-permission/my-menu')
      if (res.success && res.data && res.data.length > 0) {
        dynamicMenuConfig.value = res.data
        configLoaded.value = true
        return true
      }
      // 没有动态配置，使用静态配置
      configLoaded.value = false
      return false
    } catch (error) {
      // 加载失败，使用静态配置作为 fallback
      console.warn('[MenuPermission] Failed to load dynamic config, using static fallback:', error.message)
      configLoaded.value = false
      return false
    }
  }

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
    const item = mergedConfig.value.menuMap.get(menuKey)
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
    // 从合并配置中查找
    for (const items of Object.values(mergedConfig.value.menus)) {
      const item = items.find(m => m.route === routePath)
      if (item) {
        if (item.roles.includes('all')) return true
        if (!isLoggedIn.value) return false
        return hasAnyRole(item.roles)
      }
    }

    // 未定义的资源默认需要登录
    return isLoggedIn.value
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

    for (const group of mergedConfig.value.menuGroups) {
      // 检查分组权限
      if (group.requiresAuth && !isLoggedIn.value) continue
      if (group.roles && !hasAnyRole(group.roles)) continue

      // 过滤可见菜单项
      let items = mergedConfig.value.menus[group.items] || []
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
    const allMenus = Object.values(mergedConfig.value.menus).flat()
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
    loadMenuConfigFromBackend,
    mergedConfig,
    configLoaded,
    // 保留静态配置供外部访问
    RESOURCE_CONFIG: STATIC_RESOURCE_CONFIG,
  }
})
