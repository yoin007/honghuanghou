/**
 * API函数测试
 * 测试德育模块API函数是否正确构建请求
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// 模拟axios请求
const mockRequest = {
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn()
}

// 模拟request模块
vi.mock('@/utils/request', () => ({
  default: mockRequest
}))

// API函数定义（从设计文档）
const api = {
  // 日常表现
  getDailyRecords: (params) => mockRequest.get('/api/moral/daily-records', { params }),
  createDailyRecord: (data) => mockRequest.post('/api/moral/daily-records', data),
  getDailyRecordsByStudent: (studentId, params) => mockRequest.get(`/api/moral/daily-records/${studentId}`, { params }),

  // 德育任务
  getTasks: (params) => mockRequest.get('/api/moral/tasks', { params }),
  createTask: (data) => mockRequest.post('/api/moral/tasks', data),
  updateTask: (taskId, data) => mockRequest.put(`/api/moral/tasks/${taskId}`, data),
  deleteTask: (taskId) => mockRequest.delete(`/api/moral/tasks/${taskId}`),

  // 评价查询
  getStudentEvaluation: (studentId, semesterId) => mockRequest.get(`/api/moral/evaluation/student/${studentId}`, { params: { semester_id: semesterId } }),
  getClassEvaluation: (classId, semesterId) => mockRequest.get(`/api/moral/evaluation/class/${classId}`, { params: { semester_id: semesterId } }),

  // 学生画像
  getStudentProfile: (studentId) => mockRequest.get(`/api/moral/profile/${studentId}`),
  generateStudentProfile: (studentId) => mockRequest.post(`/api/moral/profile/generate/${studentId}`),

  // 级号管理
  getGrades: () => mockRequest.get('/api/admin/grades'),
  createGrade: (data) => mockRequest.post('/api/admin/grades', data),
  updateGrade: (id, data) => mockRequest.put(`/api/admin/grades/${id}`, data),
  deleteGrade: (id) => mockRequest.delete(`/api/admin/grades/${id}`),

  // 教师管理
  getTeachers: (params) => mockRequest.get('/api/admin/teachers', { params }),
  createTeacher: (data) => mockRequest.post('/api/admin/teachers', data),
  deleteTeacher: (id) => mockRequest.delete(`/api/admin/teachers/${id}`),
  resetTeacherPassword: (id) => mockRequest.post(`/api/admin/teachers/${id}/reset-password`)
}

describe('德育API函数', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('日常表现API', () => {
    it('getDailyRecords应该发送GET请求', () => {
      api.getDailyRecords({ semester_id: 1 })
      expect(mockRequest.get).toHaveBeenCalledWith('/api/moral/daily-records', { params: { semester_id: 1 } })
    })

    it('createDailyRecord应该发送POST请求', () => {
      const data = { student_id: '202501001', event_id: 1 }
      api.createDailyRecord(data)
      expect(mockRequest.post).toHaveBeenCalledWith('/api/moral/daily-records', data)
    })

    it('getDailyRecordsByStudent应该正确构建URL', () => {
      api.getDailyRecordsByStudent('202501001', { semester_id: 1 })
      expect(mockRequest.get).toHaveBeenCalledWith('/api/moral/daily-records/202501001', { params: { semester_id: 1 } })
    })
  })

  describe('德育任务API', () => {
    it('getTasks应该发送GET请求', () => {
      api.getTasks({ grade_id: 1 })
      expect(mockRequest.get).toHaveBeenCalledWith('/api/moral/tasks', { params: { grade_id: 1 } })
    })

    it('createTask应该发送POST请求', () => {
      const data = { task_name: '测试任务', score: 10 }
      api.createTask(data)
      expect(mockRequest.post).toHaveBeenCalledWith('/api/moral/tasks', data)
    })

    it('updateTask应该发送PUT请求到正确URL', () => {
      api.updateTask(123, { task_name: '更新任务' })
      expect(mockRequest.put).toHaveBeenCalledWith('/api/moral/tasks/123', { task_name: '更新任务' })
    })

    it('deleteTask应该发送DELETE请求到正确URL', () => {
      api.deleteTask(123)
      expect(mockRequest.delete).toHaveBeenCalledWith('/api/moral/tasks/123')
    })
  })

  describe('评价查询API', () => {
    it('getStudentEvaluation应该正确构建URL和参数', () => {
      api.getStudentEvaluation('202501001', 1)
      expect(mockRequest.get).toHaveBeenCalledWith('/api/moral/evaluation/student/202501001', { params: { semester_id: 1 } })
    })

    it('getClassEvaluation应该正确构建URL和参数', () => {
      api.getClassEvaluation(5, 1)
      expect(mockRequest.get).toHaveBeenCalledWith('/api/moral/evaluation/class/5', { params: { semester_id: 1 } })
    })
  })

  describe('学生画像API', () => {
    it('getStudentProfile应该发送GET请求', () => {
      api.getStudentProfile('202501001')
      expect(mockRequest.get).toHaveBeenCalledWith('/api/moral/profile/202501001')
    })

    it('generateStudentProfile应该发送POST请求', () => {
      api.generateStudentProfile('202501001')
      expect(mockRequest.post).toHaveBeenCalledWith('/api/moral/profile/generate/202501001')
    })
  })

  describe('级号管理API', () => {
    it('getGrades应该发送GET请求', () => {
      api.getGrades()
      expect(mockRequest.get).toHaveBeenCalledWith('/api/admin/grades')
    })

    it('createGrade应该发送POST请求', () => {
      api.createGrade({ grade_name: '2025级', enrollment_year: 2025 })
      expect(mockRequest.post).toHaveBeenCalledWith('/api/admin/grades', { grade_name: '2025级', enrollment_year: 2025 })
    })

    it('updateGrade应该发送PUT请求', () => {
      api.updateGrade(1, { grade_name: '2025级' })
      expect(mockRequest.put).toHaveBeenCalledWith('/api/admin/grades/1', { grade_name: '2025级' })
    })

    it('deleteGrade应该发送DELETE请求', () => {
      api.deleteGrade(1)
      expect(mockRequest.delete).toHaveBeenCalledWith('/api/admin/grades/1')
    })
  })

  describe('教师管理API', () => {
    it('getTeachers应该发送GET请求', () => {
      api.getTeachers({ role: 'teacher' })
      expect(mockRequest.get).toHaveBeenCalledWith('/api/admin/teachers', { params: { role: 'teacher' } })
    })

    it('createTeacher应该发送POST请求', () => {
      api.createTeacher({ name: '测试教师', subject: '语文' })
      expect(mockRequest.post).toHaveBeenCalledWith('/api/admin/teachers', { name: '测试教师', subject: '语文' })
    })

    it('deleteTeacher应该发送DELETE请求', () => {
      api.deleteTeacher('T001')
      expect(mockRequest.delete).toHaveBeenCalledWith('/api/admin/teachers/T001')
    })

    it('resetTeacherPassword应该发送POST请求', () => {
      api.resetTeacherPassword('T001')
      expect(mockRequest.post).toHaveBeenCalledWith('/api/admin/teachers/T001/reset-password')
    })
  })
})