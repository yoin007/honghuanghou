/**
 * 延时申请 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const delayApi = {
  /**
   * 获取学生信息
   * @param {Object} data { sid, classCode }
   * @returns {Promise}
   */
  getStudentInfo(data) {
    return httpClient.post('/api/student_info/', data)
  },

  /**
   * 创建延时申请
   * @param {Object} data { sid, classCode }
   * @returns {Promise}
   */
  createDelay(data) {
    return httpClient.post('/api/insert_delay/', data)
  },

  /**
   * 获取延时申请列表
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getDelayList(classCode) {
    return httpClient.get(`/api/delay_infos/${classCode}`)
  },

  /**
   * 删除延时申请
   * @param {number} delayId 申请ID
   * @returns {Promise}
   */
  deleteDelay(delayId) {
    return httpClient.delete(`/api/del_delay/${delayId}`)
  },

  /**
   * 删除延时申请（GET方式备用）
   * @param {number} delayId 申请ID
   * @returns {Promise}
   */
  deleteDelayGet(delayId) {
    return httpClient.get(`/api/del_delay/${delayId}`)
  }
}

export const getStudentInfo = delayApi.getStudentInfo
export const createDelay = delayApi.createDelay
export const getDelayList = delayApi.getDelayList
export const deleteDelay = delayApi.deleteDelay
export const deleteDelayGet = delayApi.deleteDelayGet

export default delayApi