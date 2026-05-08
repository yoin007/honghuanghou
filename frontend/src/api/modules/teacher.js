/**
 * 教师管理相关 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const teacherApi = {
  /**
   * 获取教师列表
   * @param {Object} params 查询参数
   * @returns {Promise}
   */
  getTeachers(params = {}) {
    return httpClient.get('/api/teachers', { params })
  },

  /**
   * 创建教师
   * @param {Object} data 教师数据
   * @returns {Promise}
   */
  createTeacher(data) {
    return httpClient.post('/api/teachers', data)
  },

  /**
   * 更新教师
   * @param {string} username 用户名
   * @param {Object} data 教师数据
   * @returns {Promise}
   */
  updateTeacher(username, data) {
    return httpClient.put(`/api/teachers/${username}`, data)
  },

  /**
   * 删除教师
   * @param {string} username 用户名
   * @returns {Promise}
   */
  deleteTeacher(username) {
    return httpClient.delete(`/api/teachers/${username}`)
  },

  /**
   * 获取教师任教班级
   * @param {string} teacherId 教师ID
   * @returns {Promise}
   */
  getTeachingClasses(teacherId) {
    return httpClient.get(`/api/teachers/${encodeURIComponent(teacherId)}/teaching-classes`)
  },

  /**
   * 更新教师任教班级
   * @param {string} teacherId 教师ID
   * @param {Object} data 任教班级数据
   * @returns {Promise}
   */
  updateTeachingClasses(teacherId, data) {
    return httpClient.put(`/api/teachers/${encodeURIComponent(teacherId)}/teaching-classes`, data)
  },

  /**
   * 初始化教师任教班级（根据课表工作量）
   * @returns {Promise}
   */
  initTeachingClasses() {
    return httpClient.post('/api/teachers/init-teaching-classes')
  },

  /**
   * 管理员设置密码
   * @param {Object} data { username, new_password }
   * @returns {Promise}
   */
  adminSetPassword(data) {
    return httpClient.post('/api/admin/set-password', data)
  },

  /**
   * 教师修改密码
   * @param {Object} data { old_password, new_password }
   * @returns {Promise}
   */
  changePassword(data) {
    return httpClient.post('/api/teachers/change-password', data)
  }
}

export default teacherApi