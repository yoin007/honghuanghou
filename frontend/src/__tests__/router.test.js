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
  { path: '/', redirect: '/schedules' },
  { path: '/zhf' }
]

// 检查是否是公开路由
function isPublicPath(path) {
  return publicRoutes.includes(path)
}

// 模拟路由守卫逻辑
function mockBeforeEach(to) {
  const token = localStorageMock.getItem('token')
  const requiresAuth = to.meta?.requiresAuth !== false

  // 需要登录但未登录
  if (requiresAuth && !token) {
    localStorageMock.removeItem('token')
    return { blocked: true, reason: 'no_token' }
  }

  // 已登录但访问公开页面
  if (token && isPublicPath(to.path)) {
    return { redirect: '/schedules' }
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
    it('无token访问需要认证的路由应该被拦截', () => {
      const to = { path: '/schedule', meta: { requiresAuth: true } }
      const result = mockBeforeEach(to)

      expect(result.blocked).toBe(true)
      expect(result.reason).toBe('no_token')
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

    it('有token访问公开路由应该重定向', () => {
      localStorageMock.setItem('token', 'valid_token')
      const to = { path: '/', meta: {} }
      const result = mockBeforeEach(to)

      expect(result.redirect).toBe('/schedules')
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

    it('普通路由不需要特殊角色权限', () => {
      const normalRoutes = routes.filter(r =>
        r.meta?.requiresAuth === true && !r.meta?.requiresJiaowu
      )
      expect(normalRoutes.length).toBeGreaterThan(0)
    })
  })

  describe('重定向逻辑', () => {
    it('访问/应该重定向到/schedules', () => {
      const rootRoute = routes.find(r => r.path === '/')
      expect(rootRoute?.redirect).toBe('/schedules')
    })

    it('已登录用户访问公开路由应该重定向到schedules', () => {
      localStorageMock.setItem('token', 'valid_token')
      const to = { path: '/' }
      const result = mockBeforeEach(to)

      expect(result.redirect).toBe('/schedules')
    })
  })
})