/**
 * 课表相关 API
 * 使用带认证的 axios 实例
 */
import api from '@/utils/api'

export const scheduleApi = {
  /**
   * 获取班级课表
   * @param {string} classCode 班级代码
   * @param {string} week 可选，周次
   * @returns {Promise}
   */
  getClassSchedule(classCode, week) {
    return api.get(`/api/schedule/${classCode}`, {
      params: week ? { week } : {}
    })
  },

  /**
   * 获取总课表
   * @returns {Promise}
   */
  getAllSchedules() {
    return api.get('/api/schedules')
  },

  /**
   * 获取实时课程
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getCurrentClass(classCode) {
    return api.get(`/api/current-class/${classCode}`)
  },

  /**
   * 上传课表
   * @param {FormData} formData 课表数据
   * @returns {Promise}
   */
  uploadSchedule(formData) {
    return api.post('/api/schedule/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  /**
   * 删除课表
   * @param {number} scheduleId 课表ID
   * @returns {Promise}
   */
  deleteSchedule(scheduleId) {
    return api.delete(`/api/schedule/${scheduleId}`)
  }
}

export default scheduleApi
