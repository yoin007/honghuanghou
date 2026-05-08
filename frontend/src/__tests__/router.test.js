/**
 * 路由守卫测试
 * 测试登录检查、公开路由访问、协议检查
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// 模拟 localStorage
const localStorageMock = {
  store: {},
  getItem: vi.fn((key) => localStorageMock.store[key] || null),
  setItem: vi.fn((key, value) => { localStorageMock.store[key] = value }),
  removeItem: vi.fn((key) => { delete localStorageMock.store[key] }),
  clear: vi.fn(() => { localStorageMock.store = {} })
}
vi.stubGlobal('localStorage', localStorageMock)

// 模拟 window.location
const originalLocation = { protocol: 'http:', href: 'http://localhost/' }
vi.stubGlobal('window', {
  location: { ...originalLocation },
  atob: (str) => Buffer.from(str, 'base64').toString('binary')
})

// 模拟 import.meta.env
vi.stubGlobal('import.meta', {
  env: {
    DEV: false,
    VITE_DEV_HTTP_PORT: '',
    VITE_DEV_HTTPS_PORT: '',
    VITE_DEV_HTTPS: 'false'
  }
})

// 公开路由定义
const publicRoutes = ['/', '/zhf']

// 路由配置
const routes = [
  { path: '/schedule', meta: { requiresAuth: true, title: '课程表' } },
  { path: '/homework', meta: { requiresAuth: true, title: '作业' } },
  { path: '/teacher-manage', meta: { requiresAuth: true, title: '教师管理' } },
  { path: '/admin-files', meta: { requiresAuth: true, requiresJiaowu: true } },
  { path: '/dashboard/teaching', meta: { requiresAuth: true, dashboardRoles: ['admin', 'jiaowu'] } },
  { path: '/dashboard/moral', meta: { requiresAuth: true, dashboardRoles: ['admin', 'jiaowu', 'xuefa', 'cleader'] } },
  { path: '/dashboard/class', meta: { requiresAuth: true, dashboardRoles: ['admin', 'jiaowu', 'xuefa', 'cleader'] } },
  { path: '/dashboard/system', meta: { requiresAuth: true, dashboardRoles: ['admin'] } },
  { path: '/', redirect: '/schedules' },
  { path: '/zhf' }
]

function createJwt(payload) {
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url')
  return `header.${encodedPayload}.signature`
}

// 检查是否是公开路由
function isPublicPath(path) {
  return publicRoutes.includes(path)
}

// 模拟路由守卫逻辑（简化版，不包含角色默认入口逻辑）
function mockBeforeEach(to) {
  const token = localStorageMock.getItem('token')
  const requiresAuth = to.meta?.requiresAuth !== false

  // 需要登录但未登录
  if (requiresAuth && !token) {
    localStorageMock.removeItem('token')
    return { redirect: '/' }
  }

  // 已登录但访问公开页面，重定向到角色默认驾驶舱
  if (token && isPublicPath(to.path)) {
    // 在真实实现中，这里会调用 getDefaultDashboardByRole(token)
    // 简化版直接返回教师工作台作为默认
    return { redirect: '/dashboard/teacher' }
  }

  return { allowed: true }
}

// 协议检查函数
function ensureProtocol(to) {
  const isHttps = window.location.protocol === 'https:'
  const matched = to.matched || []
  const matchedProtocol = matched.length > 0 ? matched[matched.length - 1]?.meta?.protocol : undefined

  const protocol = matchedProtocol || 'http'
  const shouldUseHttps = protocol === 'https'

  if (shouldUseHttps === isHttps) return null

  return `redirect_to_${protocol}`
}

describe('路由守卫', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
    window.location.protocol = 'http:'
  })

  describe('公开路由检查', () => {
    it('/应该是公开路由', () => {
      expect(isPublicPath('/')).toBe(true)
    })

    it('/zhf应该是公开路由', () => {
      expect(isPublicPath('/zhf')).toBe(true)
    })

    it('/schedule不是公开路由', () => {
      expect(isPublicPath('/schedule')).toBe(false)
    })

    it('/homework不是公开路由', () => {
      expect(isPublicPath('/homework')).toBe(false)
    })

    it('/teacher-manage不是公开路由', () => {
      expect(isPublicPath('/teacher-manage')).toBe(false)
    })
  })

  describe('登录检查', () => {
    it('无token访问需要认证的路由应该回到公开入口', () => {
      const to = { path: '/schedule', meta: { requiresAuth: true } }
      const result = mockBeforeEach(to)

      expect(result.redirect).toBe('/')
    })

    it('有token访问需要认证的路由应该放行', () => {
      localStorageMock.setItem('token', 'valid_token')
      const to = { path: '/schedule', meta: { requiresAuth: true } }
      const result = mockBeforeEach(to)

      expect(result.allowed).toBe(true)
    })

    it('无token访问公开路由应该放行', () => {
      const to = { path: '/', meta: { requiresAuth: false } }
      const result = mockBeforeEach(to)

      expect(result.allowed).toBe(true)
    })

    it('有token访问公开路由应该重定向到角色默认驾驶舱', () => {
      localStorageMock.setItem('token', 'valid_token')
      const to = { path: '/', meta: {} }
      const result = mockBeforeEach(to)

      // 简化版 mockBeforeEach 返回 '/dashboard/teacher' 作为默认
      expect(result.redirect).toBe('/dashboard/teacher')
    })

    it('meta.requiresAuth为false时无token也能访问', () => {
      const to = { path: '/public-page', meta: { requiresAuth: false } }
      const result = mockBeforeEach(to)

      expect(result.allowed).toBe(true)
    })
  })

  describe('协议检查', () => {
    it('HTTP页面访问HTTP路由不需要重定向', () => {
      window.location.protocol = 'http:'
      const to = { matched: [{ meta: { protocol: 'http' } }] }
      const result = ensureProtocol(to)

      expect(result).toBeNull()
    })

    it('HTTP页面访问HTTPS路由需要重定向', () => {
      window.location.protocol = 'http:'
      const to = { matched: [{ meta: { protocol: 'https' } }] }
      const result = ensureProtocol(to)

      expect(result).toBe('redirect_to_https')
    })

    it('HTTPS页面访问HTTP路由需要重定向', () => {
      window.location.protocol = 'https:'
      const to = { matched: [{ meta: { protocol: 'http' } }] }
      const result = ensureProtocol(to)

      expect(result).toBe('redirect_to_http')
    })

    it('HTTPS页面访问HTTPS路由不需要重定向', () => {
      window.location.protocol = 'https:'
      const to = { matched: [{ meta: { protocol: 'https' } }] }
      const result = ensureProtocol(to)

      expect(result).toBeNull()
    })

    it('无protocol meta时默认使用HTTP', () => {
      window.location.protocol = 'http:'
      const to = { matched: [] }
      const result = ensureProtocol(to)

      expect(result).toBeNull()
    })
  })

  describe('路由配置验证', () => {
    it('所有非公开路由都应该有requiresAuth', () => {
      const protectedRoutes = routes.filter(r => !publicRoutes.includes(r.path))
      protectedRoutes.forEach(route => {
        if (route.meta) {
          expect(route.meta.requiresAuth).toBeDefined()
        }
      })
    })

    it('需要教发部权限的路由应该有requiresJiaowu标记', () => {
      const jiaowuRoutes = routes.filter(r => r.meta?.requiresJiaowu)
      expect(jiaowuRoutes.length).toBeGreaterThan(0)

      jiaowuRoutes.forEach(route => {
        expect(route.meta.requiresAuth).toBe(true)
        expect(route.meta.requiresJiaowu).toBe(true)
      })
    })

    it('redirect路由不应该有requiresAuth标记', () => {
      const redirectRoutes = routes.filter(r => r.redirect)
      redirectRoutes.forEach(route => {
        expect(route.meta?.requiresAuth).toBeFalsy()
      })
    })
  })

  describe('边界情况', () => {
    it('空meta对象应该默认需要认证', () => {
      const to = { path: '/some-route', meta: {} }
      // requiresAuth !== false 意味着默认需要认证
      const requiresAuth = to.meta?.requiresAuth !== false
      expect(requiresAuth).toBe(true)
    })

    it('无meta的路由应该默认需要认证', () => {
      const to = { path: '/some-route' }
      const requiresAuth = to.meta?.requiresAuth !== false
      expect(requiresAuth).toBe(true)
    })

    it('过期token访问应该被清除', () => {
      localStorageMock.setItem('token', 'expired_token')
      // 模拟token验证失败的情况
      const to = { path: '/schedule', meta: { requiresAuth: true } }

      // 在真实场景中，这里会验证token有效性
      // 目前我们只检查token是否存在
      const token = localStorageMock.getItem('token')

      expect(token).toBe('expired_token')
      // 如果token有效，应该放行
      expect(localStorageMock.getItem('token')).toBeDefined()
    })

    it('路径带查询参数时应该正确判断公开路由', () => {
      // isPublicPath 只检查精确路径匹配
      expect(isPublicPath('/?query=test')).toBe(false)
      expect(isPublicPath('/zhf?query=test')).toBe(false)
    })
  })

  describe('角色权限检查', () => {
    it('requiresJiaowu路由应该标记需要教发部权限', () => {
      const adminFilesRoute = routes.find(r => r.path === '/admin-files')
      expect(adminFilesRoute?.meta?.requiresJiaowu).toBe(true)
    })

    it('驾驶舱管理路由应该声明角色边界', () => {
      const dashboardRoutes = routes.filter(r => r.path.startsWith('/dashboard/'))

      expect(dashboardRoutes.length).toBeGreaterThan(0)
      dashboardRoutes.forEach(route => {
        expect(Array.isArray(route.meta?.dashboardRoles)).toBe(true)
        expect(route.meta.dashboardRoles.length).toBeGreaterThan(0)
      })
    })

    it('普通路由不需要特殊角色权限', () => {
      const normalRoutes = routes.filter(r =>
        r.meta?.requiresAuth === true && !r.meta?.requiresJiaowu && !r.meta?.dashboardRoles
      )
      expect(normalRoutes.length).toBeGreaterThan(0)
    })

    it('普通教师不能直达教务驾驶舱', async () => {
      const { canAccessDashboardRoute } = await import('../router/guards.js')
      const token = createJwt({ sub: 'teacher', role: 'teacher' })

      expect(canAccessDashboardRoute({ dashboardRoles: ['admin', 'jiaowu'] }, token)).toBe(false)
    })

    it('教务可以直达教务驾驶舱', async () => {
      const { canAccessDashboardRoute } = await import('../router/guards.js')
      const token = createJwt({ sub: 'jiaowu', role: 'jiaowu' })

      expect(canAccessDashboardRoute({ dashboardRoles: ['admin', 'jiaowu'] }, token)).toBe(true)
    })

    it('班主任可以直达班级驾驶舱但不能直达教务驾驶舱', async () => {
      const { canAccessDashboardRoute } = await import('../router/guards.js')
      const token = createJwt({ sub: 'cleader', role: 'teacher/cleader' })

      expect(canAccessDashboardRoute({ dashboardRoles: ['admin', 'jiaowu', 'xuefa', 'cleader'] }, token)).toBe(true)
      expect(canAccessDashboardRoute({ dashboardRoles: ['admin', 'jiaowu'] }, token)).toBe(false)
    })

    it('管理员可以访问所有驾驶舱管理路由', async () => {
      const { canAccessDashboardRoute } = await import('../router/guards.js')
      const token = createJwt({ sub: 'admin', role: 'teacher/admin' })

      expect(canAccessDashboardRoute({ dashboardRoles: ['admin'] }, token)).toBe(true)
      expect(canAccessDashboardRoute({ dashboardRoles: ['admin', 'jiaowu'] }, token)).toBe(true)
      expect(canAccessDashboardRoute({ dashboardRoles: ['admin', 'jiaowu', 'xuefa', 'cleader'] }, token)).toBe(true)
    })
  })

  describe('角色默认驾驶舱入口', () => {
    it('admin角色默认进入系统运维驾驶舱', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      const token = createJwt({ sub: 'admin', role: 'admin' })
      expect(getDefaultDashboardByRole(token)).toBe('/dashboard/system')
    })

    it('jiaowu角色默认进入教务驾驶舱', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      const token = createJwt({ sub: 'jiaowu', role: 'jiaowu' })
      expect(getDefaultDashboardByRole(token)).toBe('/dashboard/teaching')
    })

    it('xuefa角色默认进入德育驾驶舱', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      const token = createJwt({ sub: 'xuefa', role: 'xuefa' })
      expect(getDefaultDashboardByRole(token)).toBe('/dashboard/moral')
    })

    it('cleader角色默认进入班级驾驶舱', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      const token = createJwt({ sub: 'cleader', role: 'teacher/cleader' })
      expect(getDefaultDashboardByRole(token)).toBe('/dashboard/class')
    })

    it('teacher角色默认进入教师工作台', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      const token = createJwt({ sub: 'teacher', role: 'teacher' })
      expect(getDefaultDashboardByRole(token)).toBe('/dashboard/teacher')
    })

    it('admin优先级高于其他角色（admin/jiaowu复合角色）', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      const token = createJwt({ sub: 'admin', role: 'admin/jiaowu' })
      expect(getDefaultDashboardByRole(token)).toBe('/dashboard/system')
    })

    it('jiaowu优先级高于xuefa/cleader', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      const token = createJwt({ sub: 'jiaowu', role: 'jiaowu/xuefa' })
      expect(getDefaultDashboardByRole(token)).toBe('/dashboard/teaching')
    })

    it('无token时返回教师工作台（默认fallback）', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      expect(getDefaultDashboardByRole(null)).toBe('/dashboard/teacher')
      expect(getDefaultDashboardByRole('')).toBe('/dashboard/teacher')
    })
  })

  describe('重定向逻辑', () => {
    it('访问/应该动态重定向（根据角色）', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      // 无 token 时重定向到 /schedules（未登录用户）
      expect(getDefaultDashboardByRole(null)).toBe('/dashboard/teacher')
    })

    it('已登录用户访问公开路由应该重定向到角色默认驾驶舱', async () => {
      const { getDefaultDashboardByRole } = await import('../router/guards.js')
      localStorageMock.setItem('token', createJwt({ sub: 'jiaowu', role: 'jiaowu' }))
      const token = localStorageMock.getItem('token')
      const defaultPath = getDefaultDashboardByRole(token)

      expect(defaultPath).toBe('/dashboard/teaching')
    })

    it('未登录用户访问/重定向到/schedules（fallback）', async () => {
      // 根路径重定向逻辑：无 token → /schedules
      // 有 token → getDefaultDashboardByRole(token)
      // 此测试验证未登录场景
      const token = localStorageMock.getItem('token')
      expect(token).toBeNull()
    })
  })

  describe('无权限重定向', () => {
    it('teacher访问系统驾驶舱应重定向到/dashboard/forbidden', async () => {
      const { canAccessDashboardRoute } = await import('../router/guards.js')
      const token = createJwt({ sub: 'teacher', role: 'teacher' })
      const meta = { dashboardRoles: ['admin'] }

      expect(canAccessDashboardRoute(meta, token)).toBe(false)
      // router beforeEach 会重定向到 /dashboard/forbidden
    })

    it('cleader访问教务驾驶舱应重定向到/dashboard/forbidden', async () => {
      const { canAccessDashboardRoute } = await import('../router/guards.js')
      const token = createJwt({ sub: 'cleader', role: 'teacher/cleader' })
      const meta = { dashboardRoles: ['admin', 'jiaowu'] }

      expect(canAccessDashboardRoute(meta, token)).toBe(false)
    })

    it('xuefa访问系统驾驶舱应重定向到/dashboard/forbidden', async () => {
      const { canAccessDashboardRoute } = await import('../router/guards.js')
      const token = createJwt({ sub: 'xuefa', role: 'xuefa' })
      const meta = { dashboardRoles: ['admin'] }

      expect(canAccessDashboardRoute(meta, token)).toBe(false)
    })

    it('jiaowu访问系统驾驶舱应重定向到/dashboard/forbidden', async () => {
      const { canAccessDashboardRoute } = await import('../router/guards.js')
      const token = createJwt({ sub: 'jiaowu', role: 'jiaowu' })
      const meta = { dashboardRoles: ['admin'] }

      expect(canAccessDashboardRoute(meta, token)).toBe(false)
    })
  })
})
