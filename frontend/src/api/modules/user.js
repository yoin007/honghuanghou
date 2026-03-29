/**
 * 用户相关 API
 * 使用带认证的 axios 实例
 */
import api from '@/utils/api'

export const userApi = {
  /**
   * 获取用户列表
   * @param {Object} params 查询参数
   * @returns {Promise}
   */
  getUserList(params) {
    return api.get('/api/users', { params })
  },

  /**
   * 获取用户详情
   * @param {number} userId 用户ID
   * @returns {Promise}
   */
  getUserDetail(userId) {
    return api.get(`/api/users/${userId}`)
  },

  /**
   * 创建用户
   * @param {Object} data 用户数据
   * @returns {Promise}
   */
  createUser(data) {
    return api.post('/api/users', data)
  },

  /**
   * 更新用户
   * @param {number} userId 用户ID
   * @param {Object} data 用户数据
   * @returns {Promise}
   */
  updateUser(userId, data) {
    return api.put(`/api/users/${userId}`, data)
  },

  /**
   * 删除用户
   * @param {number} userId 用户ID
   * @returns {Promise}
   */
  deleteUser(userId) {
    return api.delete(`/api/users/${userId}`)
  },

  /**
   * 获取班级学生列表
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getClassStudents(classCode) {
    return api.get(`/api/class-students/${classCode}`)
  },

  /**
   * 获取班级列表
   * @param {string} ip 客户端IP
   * @returns {Promise}
   */
  getClassCodes(ip) {
    return api.get('/api/class-codes/', {
      params: ip ? { ip } : {}
    })
  }
}

export default userApi
