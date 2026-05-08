/**
 * 课表相关 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const scheduleApi = {
  /**
   * 获取班级课表
   * @param {string} classCode 班级代码
   * @param {Object} options 可选参数 { week, _ts }
   * @returns {Promise}
   */
  getClassSchedule(classCode, options = {}) {
    return httpClient.get(`/api/schedule/${classCode}`, {
      params: { ...options, _ts: options._ts || Date.now() }
    })
  },

  /**
   * 获取总课表列表
   * @param {Object} options 可选参数 { _ts }
   * @returns {Promise}
   */
  getAllSchedules(options = {}) {
    return httpClient.get('/api/schedules', {
      params: { ...options, _ts: options._ts || Date.now() }
    })
  },

  /**
   * 获取今日课程表
   * @param {string} date 可选，指定日期
   * @returns {Promise}
   */
  getTodays(date = null) {
    const params = date ? { date, _ts: Date.now() } : { _ts: Date.now() }
    return httpClient.get('/api/todays', { params })
  },

  /**
   * 获取课程时间表（节次时间）
   * @returns {Promise}
   */
  getPeriods() {
    return httpClient.get('/api/periods', { params: { _ts: Date.now() } })
  },

  /**
   * 获取实时课程
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getCurrentClass(classCode) {
    return httpClient.get(`/api/current-class/${classCode}`)
  },

  /**
   * 上传课表
   * @param {FormData} formData 课表数据
   * @returns {Promise}
   */
  uploadSchedule(formData) {
    return httpClient.post('/api/schedule/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  /**
   * 删除课表
   * @param {number} scheduleId 课表ID
   * @returns {Promise}
   */
  deleteSchedule(scheduleId) {
    return httpClient.delete(`/api/schedule/${scheduleId}`)
  },

  /**
   * 获取实时班级课程
   * @param {Object} params 查询参数
   * @returns {Promise}
   */
  getCurrentClasses(params = {}) {
    return httpClient.get('/api/current-classes', { params: { ...params, _ts: Date.now() } })
  },

  /**
   * 获取教师课表
   * @param {string} teacherName 教师姓名
   * @returns {Promise}
   */
  getTeacherSchedule(teacherName) {
    return httpClient.get(`/api/teacher-schedule/${teacherName}`, { params: { _ts: Date.now() } })
  },

  /**
   * 获取教师下周课表
   * @param {string} teacherName 教师姓名
   * @returns {Promise}
   */
  getTeacherScheduleNextweek(teacherName) {
    return httpClient.get(`/api/teacher-schedule-nextweek/${teacherName}`, { params: { _ts: Date.now() } })
  }
}

export const getPeriods = scheduleApi.getPeriods
export const getCurrentClasses = scheduleApi.getCurrentClasses
export const getTeacherSchedule = scheduleApi.getTeacherSchedule
export const getTeacherScheduleNextweek = scheduleApi.getTeacherScheduleNextweek

export default scheduleApi
