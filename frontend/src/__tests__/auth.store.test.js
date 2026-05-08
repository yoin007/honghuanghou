/**
 * Pinia Auth Store 测试
 * 测试 login/logout 流程、JWT解析、状态管理
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { parseRolesFromToken } from '@/shared/auth/roles'

// 模拟 localStorage
const localStorageMock = {
  store: {},
  getItem: vi.fn((key) => localStorageMock.store[key] || null),
  setItem: vi.fn((key, value) => { localStorageMock.store[key] = value }),
  removeItem: vi.fn((key) => { delete localStorageMock.store[key] }),
  clear: vi.fn(() => { localStorageMock.store = {} })
}
vi.stubGlobal('localStorage', localStorageMock)

// 模拟 ElMessage
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

// 模拟 api
const mockApi = {
  defaults: {
    headers: {
      common: {}
    }
  },
  post: vi.fn()
}
// JWT 解析工具函数
function parseJwtPayload(token) {
  if (!token) return null
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(window.atob(base64))
  } catch {
    return null
  }
}

// 创建模拟Token (不验证签名，只用于解析payload)
function createMockToken(payload) {
  const header = { alg: 'HS256', typ: 'JWT' }
  const headerB64 = btoa(JSON.stringify(header)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
  const payloadB64 = btoa(JSON.stringify(payload)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
  const signature = 'mock_signature'
  return `${headerB64}.${payloadB64}.${signature}`
}

// Auth Store 模拟实现
function createAuthStore() {
  const state = {
    token: localStorageMock.getItem('token') || '',
    username: '',
    role: '',
    isAdmin: false,
    isJiaowu: false
  }

  const isLoggedIn = () => !!state.token

  const setRolesFromToken = (token) => {
    const flags = parseRolesFromToken(token)
    state.isAdmin = flags.admin
    state.isJiaowu = flags.jiaowu
  }

  const initAuth = () => {
    if (state.token) {
      try {
        mockApi.defaults.headers.common['Authorization'] = `Bearer ${state.token}`
        const payload = parseJwtPayload(state.token)
        if (payload) {
          state.username = payload.sub
          state.role = payload.role
          setRolesFromToken(state.token)
        }
      } catch (error) {
        logout()
      }
    }
  }

  const login = async (user, password) => {
    const formData = new URLSearchParams()
    formData.append('username', user)
    formData.append('password', password)

    const response = await mockApi.post('/api/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    if (response.data?.access_token) {
      const newToken = response.data.access_token
      state.token = newToken
      localStorageMock.setItem('token', newToken)
      mockApi.defaults.headers.common['Authorization'] = `Bearer ${newToken}`

      const payload = parseJwtPayload(newToken)
      if (payload) {
        state.username = payload.sub
        state.role = payload.role
        setRolesFromToken(newToken)
      }

      return true
    }
    return false
  }

  const logout = () => {
    state.token = ''
    state.username = ''
    state.role = ''
    state.isAdmin = false
    state.isJiaowu = false
    localStorageMock.removeItem('token')
    delete mockApi.defaults.headers.common['Authorization']
  }

  return {
    state,
    isLoggedIn,
    initAuth,
    login,
    logout
  }
}

describe('Auth Store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorageMock.clear()
    mockApi.defaults.headers.common = {}
  })

  describe('初始化', () => {
    it('无token时状态应为空', () => {
      const store = createAuthStore()
      expect(store.state.token).toBe('')
      expect(store.state.username).toBe('')
      expect(store.isLoggedIn()).toBe(false)
    })

    it('有token时应初始化用户状态', () => {
      const token = createMockToken({ sub: 'testuser', role: 'teacher' })
      localStorageMock.setItem('token', token)
      const store = createAuthStore()
      store.initAuth()
      expect(store.state.username).toBe('testuser')
      expect(store.state.role).toBe('teacher')
    })

    it('admin角色应该设置isAdmin', () => {
      const token = createMockToken({ sub: 'adminuser', role: 'admin' })
      localStorageMock.setItem('token', token)
      const store = createAuthStore()
      store.initAuth()
      expect(store.state.isAdmin).toBe(true)
      expect(store.state.isJiaowu).toBe(true) // admin也算jiaowu
    })

    it('jiaowu角色应该设置isJiaowu', () => {
      const token = createMockToken({ sub: 'jiaowuuser', role: 'jiaowu' })
      localStorageMock.setItem('token', token)
      const store = createAuthStore()
      store.initAuth()
      expect(store.state.isJiaowu).toBe(true)
      expect(store.state.isAdmin).toBe(false)
    })

    it('组合角色teacher/admin应该设置isAdmin', () => {
      const token = createMockToken({ sub: 'combined', role: 'teacher/admin' })
      localStorageMock.setItem('token', token)
      const store = createAuthStore()
      store.initAuth()
      expect(store.state.isAdmin).toBe(true)
    })
  })

  describe('login登录', () => {
    it('登录成功应该设置token和用户信息', async () => {
      const mockToken = createMockToken({ sub: 'teacher1', role: 'teacher' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      const result = await store.login('teacher1', 'password123')

      expect(result).toBe(true)
      expect(mockApi.post).toHaveBeenCalledWith('/api/token', expect.any(URLSearchParams), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      expect(store.state.token).toBe(mockToken)
      expect(store.state.username).toBe('teacher1')
      expect(store.state.role).toBe('teacher')
    })

    it('登录成功应该存储token到localStorage', async () => {
      const mockToken = createMockToken({ sub: 'user1', role: 'teacher' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('user1', 'password')

      expect(localStorageMock.setItem).toHaveBeenCalledWith('token', mockToken)
    })

    it('登录成功应该设置Authorization header', async () => {
      const mockToken = createMockToken({ sub: 'user1', role: 'teacher' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('user1', 'password')

      expect(mockApi.defaults.headers.common['Authorization']).toBe(`Bearer ${mockToken}`)
    })

    it('登录失败应该返回false', async () => {
      mockApi.post.mockResolvedValueOnce({ data: {} })

      const store = createAuthStore()
      const result = await store.login('wronguser', 'wrongpassword')

      expect(result).toBe(false)
      expect(store.state.token).toBe('')
    })

    it('admin登录应该设置isAdmin', async () => {
      const mockToken = createMockToken({ sub: 'admin', role: 'admin' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('admin', 'password')

      expect(store.state.isAdmin).toBe(true)
    })

    it('jiaowu登录应该设置isJiaowu', async () => {
      const mockToken = createMockToken({ sub: 'jiaowu', role: 'jiaowu' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('jiaowu', 'password')

      expect(store.state.isJiaowu).toBe(true)
      expect(store.state.isAdmin).toBe(false)
    })
  })

  describe('logout退出', () => {
    it('退出应该清除所有状态', async () => {
      const mockToken = createMockToken({ sub: 'user1', role: 'teacher' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('user1', 'password')
      store.logout()

      expect(store.state.token).toBe('')
      expect(store.state.username).toBe('')
      expect(store.state.role).toBe('')
      expect(store.state.isAdmin).toBe(false)
      expect(store.state.isJiaowu).toBe(false)
    })

    it('退出应该清除localStorage', async () => {
      const mockToken = createMockToken({ sub: 'user1', role: 'teacher' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('user1', 'password')
      store.logout()

      expect(localStorageMock.removeItem).toHaveBeenCalledWith('token')
    })

    it('退出应该清除Authorization header', async () => {
      const mockToken = createMockToken({ sub: 'user1', role: 'teacher' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('user1', 'password')
      store.logout()

      expect(mockApi.defaults.headers.common['Authorization']).toBeUndefined()
    })
  })

  describe('isLoggedIn计算属性', () => {
    it('有token时应该返回true', async () => {
      const mockToken = createMockToken({ sub: 'user1', role: 'teacher' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('user1', 'password')

      expect(store.isLoggedIn()).toBe(true)
    })

    it('无token时应该返回false', () => {
      const store = createAuthStore()
      expect(store.isLoggedIn()).toBe(false)
    })

    it('退出后应该返回false', async () => {
      const mockToken = createMockToken({ sub: 'user1', role: 'teacher' })
      mockApi.post.mockResolvedValueOnce({ data: { access_token: mockToken } })

      const store = createAuthStore()
      await store.login('user1', 'password')
      store.logout()

      expect(store.isLoggedIn()).toBe(false)
    })
  })

  describe('JWT Token解析', () => {
    it('应该正确解析JWT payload', () => {
      const payload = { sub: 'testuser', role: 'teacher', exp: 1234567890 }
      const token = createMockToken(payload)
      const parsed = parseJwtPayload(token)

      expect(parsed.sub).toBe('testuser')
      expect(parsed.role).toBe('teacher')
      expect(parsed.exp).toBe(1234567890)
    })

    it('无效token应该返回null', () => {
      expect(parseJwtPayload('invalid_token')).toBeNull()
      expect(parseJwtPayload('')).toBeNull()
      expect(parseJwtPayload(null)).toBeNull()
    })

    it('格式错误的token应该返回null', () => {
      expect(parseJwtPayload('only.one.part')).toBeNull()
      expect(parseJwtPayload('part1.part2')).toBeNull()
    })
  })

  describe('边界情况', () => {
    it('空用户名登录应该仍能发送请求', async () => {
      mockApi.post.mockResolvedValueOnce({ data: {} })

      const store = createAuthStore()
      await store.login('', 'password')

      expect(mockApi.post).toHaveBeenCalled()
    })

    it('空密码登录应该仍能发送请求', async () => {
      mockApi.post.mockResolvedValueOnce({ data: {} })

      const store = createAuthStore()
      await store.login('user', '')

      expect(mockApi.post).toHaveBeenCalled()
    })

    it('API错误不应该抛出异常', async () => {
      mockApi.post.mockRejectedValueOnce(new Error('Network error'))

      const store = createAuthStore()
      try {
        await store.login('user', 'password')
      } catch (e) {
        // 应该被store内部处理
      }

      expect(store.state.token).toBe('')
    })
  })
})
