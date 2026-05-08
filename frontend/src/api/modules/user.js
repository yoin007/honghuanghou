/**
 * 用户与班级学生相关 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const userApi = {
  /**
   * 获取用户列表
   * @param {Object} params 查询参数
   * @returns {Promise}
   */
  getUserList(params) {
    return httpClient.get('/api/users', { params })
  },

  /**
   * 获取用户详情
   * @param {number} userId 用户ID
   * @returns {Promise}
   */
  getUserDetail(userId) {
    return httpClient.get(`/api/users/${userId}`)
  },

  /**
   * 创建用户
   * @param {Object} data 用户数据
   * @returns {Promise}
   */
  createUser(data) {
    return httpClient.post('/api/users', data)
  },

  /**
   * 更新用户
   * @param {number} userId 用户ID
   * @param {Object} data 用户数据
   * @returns {Promise}
   */
  updateUser(userId, data) {
    return httpClient.put(`/api/users/${userId}`, data)
  },

  /**
   * 删除用户
   * @param {number} userId 用户ID
   * @returns {Promise}
   */
  deleteUser(userId) {
    return httpClient.delete(`/api/users/${userId}`)
  },

  /**
   * 获取班级代码列表
   * @param {Object} params 可选参数 { ip }
   * @returns {Promise}
   */
  getClassCodes(params = {}) {
    return httpClient.get('/api/class-codes/', { params })
  },

  /**
   * 获取班级信息
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getClassInfo(classCode) {
    return httpClient.get(`/api/class-info/${classCode}`)
  },

  /**
   * 获取班级学生列表 (class-students 接口)
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getClassStudents(classCode) {
    return httpClient.get(`/api/class-students/${classCode}`)
  },

  /**
   * 获取学生状态列表 (students_status 接口)
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getStudentsStatus(classCode) {
    return httpClient.get(`/api/students_status/${classCode}`)
  },

  /**
   * 获取学生列表 (students 接口)
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getStudents(classCode) {
    return httpClient.get(`/api/students/${encodeURIComponent(classCode)}`)
  }
}

// 导出独立函数便于按需导入
export const getClassCodes = userApi.getClassCodes
export const getClassInfo = userApi.getClassInfo
export const getClassStudents = userApi.getClassStudents
export const getStudentsStatus = userApi.getStudentsStatus
export const getStudents = userApi.getStudents

export default userApi
