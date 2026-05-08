/**
 * 角色解析权威模块测试
 */
import { describe, it, expect, vi } from 'vitest'
import {
  parseRolesFromToken,
  getDefaultDashboardByRole,
  canAccessDashboardRoute,
  canViewDashboard
} from '@/shared/auth/roles'

// Mock window.atob
vi.stubGlobal('window', {
  atob: (str) => Buffer.from(str, 'base64').toString('binary')
})

// Helper: 创建 JWT token
const createToken = (role) => {
  const payload = { sub: 'testuser', role }
  const header = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
  const payloadBase64 = Buffer.from(JSON.stringify(payload)).toString('base64')
  const signature = 'mock-signature'
  return `${header}.${payloadBase64}.${signature}`
}

describe('parseRolesFromToken', () => {
  it('returns default flags for empty token', () => {
    const flags = parseRolesFromToken('')
    expect(flags.admin).toBe(false)
    expect(flags.jiaowu).toBe(false)
    expect(flags.xuefa).toBe(false)
    expect(flags.cleader).toBe(false)
    expect(flags.teacher).toBe(true)
  })

  it('parses admin role correctly', () => {
    const token = createToken('admin')
    const flags = parseRolesFromToken(token)
    expect(flags.admin).toBe(true)
    expect(flags.jiaowu).toBe(true) // admin inherits jiaowu
    expect(flags.xuefa).toBe(true) // admin inherits xuefa
    expect(flags.cleader).toBe(false)
  })

  it('parses jiaowu role correctly', () => {
    const token = createToken('jiaowu')
    const flags = parseRolesFromToken(token)
    expect(flags.admin).toBe(false)
    expect(flags.jiaowu).toBe(true)
    expect(flags.xuefa).toBe(false)
    expect(flags.cleader).toBe(false)
  })

  it('parses xuefa role correctly', () => {
    const token = createToken('xuefa')
    const flags = parseRolesFromToken(token)
    expect(flags.admin).toBe(false)
    expect(flags.jiaowu).toBe(false)
    expect(flags.xuefa).toBe(true)
    expect(flags.cleader).toBe(false)
  })

  it('parses cleader role correctly', () => {
    const token = createToken('cleader')
    const flags = parseRolesFromToken(token)
    expect(flags.admin).toBe(false)
    expect(flags.jiaowu).toBe(false)
    expect(flags.xuefa).toBe(false)
    expect(flags.cleader).toBe(true)
  })

  it('parses multi-role format teacher/admin', () => {
    const token = createToken('teacher/admin')
    const flags = parseRolesFromToken(token)
    expect(flags.admin).toBe(true)
    expect(flags.jiaowu).toBe(true)
    expect(flags.xuefa).toBe(true)
    expect(flags.cleader).toBe(false)
  })

  it('parses multi-role format jiaowu/cleader', () => {
    const token = createToken('jiaowu/cleader')
    const flags = parseRolesFromToken(token)
    expect(flags.admin).toBe(false)
    expect(flags.jiaowu).toBe(true)
    expect(flags.xuefa).toBe(false)
    expect(flags.cleader).toBe(true)
  })
})

describe('getDefaultDashboardByRole', () => {
  it('returns system dashboard for admin', () => {
    const token = createToken('admin')
    expect(getDefaultDashboardByRole(token)).toBe('/dashboard/system')
  })

  it('returns teaching dashboard for jiaowu', () => {
    const token = createToken('jiaowu')
    expect(getDefaultDashboardByRole(token)).toBe('/dashboard/teaching')
  })

  it('returns moral dashboard for xuefa', () => {
    const token = createToken('xuefa')
    expect(getDefaultDashboardByRole(token)).toBe('/dashboard/moral')
  })

  it('returns class dashboard for cleader', () => {
    const token = createToken('cleader')
    expect(getDefaultDashboardByRole(token)).toBe('/dashboard/class')
  })

  it('returns teacher dashboard for default role', () => {
    const token = createToken('teacher')
    expect(getDefaultDashboardByRole(token)).toBe('/dashboard/teacher')
  })

  it('prioritizes admin over jiaowu in multi-role', () => {
    const token = createToken('jiaowu/admin')
    expect(getDefaultDashboardByRole(token)).toBe('/dashboard/system')
  })
})

describe('canAccessDashboardRoute', () => {
  it('returns true when no dashboardRoles required', () => {
    expect(canAccessDashboardRoute({}, 'token')).toBe(true)
  })

  it('returns true when dashboardRoles is empty', () => {
    expect(canAccessDashboardRoute({ dashboardRoles: [] }, 'token')).toBe(true)
  })

  it('returns true for admin accessing system dashboard', () => {
    const token = createToken('admin')
    const meta = { dashboardRoles: ['admin'] }
    expect(canAccessDashboardRoute(meta, token)).toBe(true)
  })

  it('returns false for jiaowu accessing system dashboard', () => {
    const token = createToken('jiaowu')
    const meta = { dashboardRoles: ['admin'] }
    expect(canAccessDashboardRoute(meta, token)).toBe(false)
  })

  it('returns true for admin accessing jiaowu dashboard (inheritance)', () => {
    const token = createToken('admin')
    const meta = { dashboardRoles: ['admin', 'jiaowu'] }
    expect(canAccessDashboardRoute(meta, token)).toBe(true)
  })
})

describe('canViewDashboard', () => {
  const adminFlags = { admin: true, jiaowu: true, xuefa: true, cleader: false }
  const jiaowuFlags = { admin: false, jiaowu: true, xuefa: false, cleader: false }
  const xuefaFlags = { admin: false, jiaowu: false, xuefa: true, cleader: false }
  const cleaderFlags = { admin: false, jiaowu: false, xuefa: false, cleader: true }
  const teacherFlags = { admin: false, jiaowu: false, xuefa: false, cleader: false }

  it('admin can view all dashboards', () => {
    expect(canViewDashboard(adminFlags, 'system')).toBe(true)
    expect(canViewDashboard(adminFlags, 'invigilation')).toBe(true)
    expect(canViewDashboard(adminFlags, 'moral')).toBe(true)
    expect(canViewDashboard(adminFlags, 'class')).toBe(true)
  })

  it('jiaowu cannot view system dashboard', () => {
    expect(canViewDashboard(jiaowuFlags, 'system')).toBe(false)
  })

  it('jiaowu can view invigilation dashboard', () => {
    expect(canViewDashboard(jiaowuFlags, 'invigilation')).toBe(true)
  })

  it('xuefa can view moral and class dashboards', () => {
    expect(canViewDashboard(xuefaFlags, 'moral')).toBe(true)
    expect(canViewDashboard(xuefaFlags, 'class')).toBe(true)
  })

  it('cleader can view class dashboard', () => {
    expect(canViewDashboard(cleaderFlags, 'class')).toBe(true)
  })

  it('cleader cannot view invigilation dashboard', () => {
    expect(canViewDashboard(cleaderFlags, 'invigilation')).toBe(false)
  })

  it('teacher cannot view any dashboard by default', () => {
    expect(canViewDashboard(teacherFlags, 'system')).toBe(false)
    expect(canViewDashboard(teacherFlags, 'invigilation')).toBe(false)
    expect(canViewDashboard(teacherFlags, 'moral')).toBe(false)
    expect(canViewDashboard(teacherFlags, 'class')).toBe(false)
  })
})