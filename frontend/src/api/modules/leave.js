/**
 * 请假记录 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const leaveApi = {
  /**
   * 获取班级列表（班主任）
   * @returns {Promise}
   */
  getCleaderClasses() {
    return httpClient.get('/api/cleader-classes/')
  },

  /**
   * 获取学生列表
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getStudentsByClass(classCode) {
    return httpClient.get(`/api/students/${classCode}`)
  },

  /**
   * 获取请假记录
   * @param {Object} params 查询参数
   * @returns {Promise}
   */
  getLeaveRecords(params = {}) {
    return httpClient.get('/api/leave-records/', { params })
  },

  /**
   * 创建请假记录
   * @param {Object} data 请假数据
   * @returns {Promise}
   */
  createLeaveRecord(data) {
    return httpClient.post('/api/leave-records/', data)
  },

  /**
   * 核销请假记录
   * @param {number} recordId 记录ID
   * @returns {Promise}
   */
  consumeLeaveRecord(recordId) {
    return httpClient.post(`/api/leave-records/${recordId}/consume`)
  }
}

export const getCleaderClasses = leaveApi.getCleaderClasses
export const getStudentsByClass = leaveApi.getStudentsByClass
export const getLeaveRecords = leaveApi.getLeaveRecords
export const createLeaveRecord = leaveApi.createLeaveRecord
export const consumeLeaveRecord = leaveApi.consumeLeaveRecord

export default leaveApi