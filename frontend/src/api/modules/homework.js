/**
 * 作业相关 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const homeworkApi = {
  /**
   * 获取班级作业列表
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getHomeworkList(classCode) {
    return httpClient.get(`/api/homework/${classCode}`)
  },

  /**
   * 获取作业详情
   * @param {number} homeworkId 作业ID
   * @returns {Promise}
   */
  getHomeworkDetail(homeworkId) {
    return httpClient.get(`/api/homework/detail/${homeworkId}`)
  },

  /**
   * 创建作业
   * @param {Object} data 作业数据
   * @returns {Promise}
   */
  createHomework(data) {
    return httpClient.post('/api/homework', data)
  },

  /**
   * 更新作业
   * @param {number} homeworkId 作业ID
   * @param {Object} data 作业数据
   * @returns {Promise}
   */
  updateHomework(homeworkId, data) {
    return httpClient.put(`/api/homework/${homeworkId}`, data)
  },

  /**
   * 删除作业
   * @param {number} homeworkId 作业ID
   * @returns {Promise}
   */
  deleteHomework(homeworkId) {
    return httpClient.delete(`/api/homework/${homeworkId}`)
  },

  /**
   * 批量删除作业
   * @param {Object} data { ids, classCode }
   * @returns {Promise}
   */
  batchDeleteHomework(data) {
    return httpClient.delete('/api/homework/batch', { data })
  },

  /**
   * 发布作业（multipart/form-data）
   * @param {FormData} formData 作业数据
   * @returns {Promise}
   */
  publishHomework(formData) {
    return httpClient.post('/api/homework/', formData)
  }
}

export const getHomeworkList = homeworkApi.getHomeworkList
export const updateHomework = homeworkApi.updateHomework
export const deleteHomework = homeworkApi.deleteHomework
export const batchDeleteHomework = homeworkApi.batchDeleteHomework
export const publishHomework = homeworkApi.publishHomework

export default homeworkApi
