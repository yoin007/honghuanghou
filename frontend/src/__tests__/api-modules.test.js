/**
 * API 模块导出测试
 * 验证所有 API 模块可正常导入，关键函数存在，不执行真实网络请求
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock httpClient - 在所有 import 之前
const mockHttpClient = {
  get: vi.fn(() => Promise.resolve({ data: {} })),
  post: vi.fn(() => Promise.resolve({ data: {} })),
  put: vi.fn(() => Promise.resolve({ data: {} })),
  delete: vi.fn(() => Promise.resolve({ data: {} }))
}

vi.mock('@/shared/api/httpClient', () => ({
  httpClient: mockHttpClient
}))

// 重置模块缓存，确保使用 mock
beforeEach(() => {
  vi.resetModules()
  vi.clearAllMocks()
})

describe('API Modules', () => {
  it('all modules should expose a default export', async () => {
    const modules = [
      ['announcement', () => import('@/api/modules/announcement')],
      ['auth', () => import('@/api/modules/auth')],
      ['dashboard', () => import('@/api/modules/dashboard')],
      ['delay', () => import('@/api/modules/delay')],
      ['filegather', () => import('@/api/modules/filegather')],
      ['homework', () => import('@/api/modules/homework')],
      ['invigilation', () => import('@/api/modules/invigilation')],
      ['leave', () => import('@/api/modules/leave')],
      ['loudpk', () => import('@/api/modules/loudpk')],
      ['member', () => import('@/api/modules/member')],
      ['message', () => import('@/api/modules/message')],
      ['moral', () => import('@/api/modules/moral')],
      ['permission', () => import('@/api/modules/permission')],
      ['schedule', () => import('@/api/modules/schedule')],
      ['system', () => import('@/api/modules/system')],
      ['task', () => import('@/api/modules/task')],
      ['teacher', () => import('@/api/modules/teacher')],
      ['user', () => import('@/api/modules/user')]
    ]

    for (const [moduleName, loadModule] of modules) {
      const apiModule = await loadModule()
      expect(apiModule.default, `${moduleName} default export`).toBeDefined()
    }
  })

  describe('authApi', () => {
    it('should export authApi object', async () => {
      const { authApi } = await import('@/api/modules/auth')
      expect(authApi).toBeDefined()
      expect(authApi.login).toBeDefined()
    })

    it('login should call POST /api/token', async () => {
      const { authApi } = await import('@/api/modules/auth')
      await authApi.login('testuser', 'testpass')
      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/token', expect.any(URLSearchParams), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
    })
  })

  describe('userApi', () => {
    it('should export userApi and named exports', async () => {
      const { userApi, getClassCodes } = await import('@/api/modules/user')
      expect(userApi).toBeDefined()
      expect(getClassCodes).toBeDefined()
    })

    it('getClassCodes should call GET /api/class-codes/', async () => {
      const { getClassCodes } = await import('@/api/modules/user')
      await getClassCodes()
      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/class-codes/', expect.any(Object))
    })
  })

  describe('homeworkApi', () => {
    it('should export homeworkApi and named exports', async () => {
      const { homeworkApi, getHomeworkList, publishHomework } = await import('@/api/modules/homework')
      expect(homeworkApi).toBeDefined()
      expect(getHomeworkList).toBeDefined()
      expect(publishHomework).toBeDefined()
    })

    it('getHomeworkList should call GET /api/homework/{classCode}', async () => {
      const { getHomeworkList } = await import('@/api/modules/homework')
      await getHomeworkList('G1-1')
      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/homework/G1-1')
    })

    it('publishHomework should call POST /api/homework/', async () => {
      const { publishHomework } = await import('@/api/modules/homework')
      const formData = new FormData()
      await publishHomework(formData)
      expect(mockHttpClient.post).toHaveBeenCalledWith('/api/homework/', formData)
    })
  })

  describe('announcementApi', () => {
    it('should export announcementApi and named exports', async () => {
      const { announcementApi, getAnnouncements } = await import('@/api/modules/announcement')
      expect(announcementApi).toBeDefined()
      expect(getAnnouncements).toBeDefined()
    })

    it('getAnnouncements should call GET /api/announcements/{classCode}', async () => {
      const { getAnnouncements } = await import('@/api/modules/announcement')
      await getAnnouncements('G1-1')
      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/announcements/G1-1')
    })
  })

  describe('leaveApi', () => {
    it('should export leaveApi and named exports', async () => {
      const { leaveApi, getLeaveRecords } = await import('@/api/modules/leave')
      expect(leaveApi).toBeDefined()
      expect(getLeaveRecords).toBeDefined()
    })

    it('getLeaveRecords should call GET /api/leave-records/ with params', async () => {
      const { getLeaveRecords } = await import('@/api/modules/leave')
      await getLeaveRecords({ page: 1, page_size: 10 })
      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/leave-records/', { params: { page: 1, page_size: 10 } })
    })
  })

  describe('loudpkApi', () => {
    it('should export loudpkApi and named exports', async () => {
      const { loudpkApi, getLoudpkList } = await import('@/api/modules/loudpk')
      expect(loudpkApi).toBeDefined()
      expect(getLoudpkList).toBeDefined()
    })

    it('getLoudpkList should call GET /api/loudpk with params', async () => {
      const { getLoudpkList } = await import('@/api/modules/loudpk')
      await getLoudpkList({ _ts: 12345 })
      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/loudpk', { params: { _ts: 12345 } })
    })
  })

  describe('scheduleApi', () => {
    it('should export scheduleApi and named exports', async () => {
      const { scheduleApi, getPeriods } = await import('@/api/modules/schedule')
      expect(scheduleApi).toBeDefined()
      expect(getPeriods).toBeDefined()
    })

    it('getPeriods should call GET /api/periods', async () => {
      const { getPeriods } = await import('@/api/modules/schedule')
      await getPeriods()
      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/periods', expect.any(Object))
    })
  })

  describe('teacherApi', () => {
    it('should export teacherApi and named exports', async () => {
      const { teacherApi } = await import('@/api/modules/teacher')
      expect(teacherApi).toBeDefined()
      expect(teacherApi.getTeachingClasses).toBeDefined()
    })

    it('getTeachingClasses should encode teacherId', async () => {
      const { teacherApi } = await import('@/api/modules/teacher')
      await teacherApi.getTeachingClasses('teacher@test')
      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/teachers/teacher%40test/teaching-classes')
    })
  })

  describe('invigilationApi', () => {
    it('should export invigilationApi and default', async () => {
      const invigilationModule = await import('@/api/modules/invigilation')
      expect(invigilationModule.invigilationApi).toBeDefined()
      expect(invigilationModule.default).toBeDefined()
    })

    it('downloadTemplate should call GET with responseType blob', async () => {
      const { invigilationApi } = await import('@/api/modules/invigilation')
      await invigilationApi.downloadTemplate()
      expect(mockHttpClient.get).toHaveBeenCalledWith('/api/invigilation/template', { responseType: 'blob' })
    })
  })

  describe('dashboardApi', () => {
    it('should export dashboardApi and named exports', async () => {
      const { dashboardApi, getDashboardOverview } = await import('@/api/modules/dashboard')
      expect(dashboardApi).toBeDefined()
      expect(getDashboardOverview).toBeDefined()
    })
  })

  describe('taskApi', () => {
    it('should export taskApi and named exports', async () => {
      const { taskApi, getTasks } = await import('@/api/modules/task')
      expect(taskApi).toBeDefined()
      expect(getTasks).toBeDefined()
    })
  })

  describe('permissionApi', () => {
    it('should export permissionApi and named exports', async () => {
      const { permissionApi, getPermissions } = await import('@/api/modules/permission')
      expect(permissionApi).toBeDefined()
      expect(getPermissions).toBeDefined()
    })
  })

  describe('memberApi', () => {
    it('should export memberApi and named exports', async () => {
      const { memberApi, getMembers } = await import('@/api/modules/member')
      expect(memberApi).toBeDefined()
      expect(getMembers).toBeDefined()
    })
  })

  describe('systemApi', () => {
    it('should export systemApi and named exports', async () => {
      const { systemApi, getHealth } = await import('@/api/modules/system')
      expect(systemApi).toBeDefined()
      expect(getHealth).toBeDefined()
    })
  })

  describe('messageApi', () => {
    it('should export messageApi and named exports', async () => {
      const { messageApi, getMessages } = await import('@/api/modules/message')
      expect(messageApi).toBeDefined()
      expect(getMessages).toBeDefined()
    })
  })

  describe('delayApi', () => {
    it('should export delayApi and named exports', async () => {
      const { delayApi, getDelayList } = await import('@/api/modules/delay')
      expect(delayApi).toBeDefined()
      expect(getDelayList).toBeDefined()
    })
  })
})
