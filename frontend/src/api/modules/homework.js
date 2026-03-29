/**
 * 作业相关 API
 * 使用带认证的 axios 实例
 */
import api from '@/utils/api'

export const homeworkApi = {
  /**
   * 获取班级作业列表
   * @param {string} classCode 班级代码
   * @returns {Promise}
   */
  getHomeworkList(classCode) {
    return api.get(`/api/homework/${classCode}`)
  },

  /**
   * 获取作业详情
   * @param {number} homeworkId 作业ID
   * @returns {Promise}
   */
  getHomeworkDetail(homeworkId) {
    return api.get(`/api/homework/detail/${homeworkId}`)
  },

  /**
   * 创建作业
   * @param {Object} data 作业数据
   * @returns {Promise}
   */
  createHomework(data) {
    return api.post('/api/homework', data)
  },

  /**
   * 更新作业
   * @param {number} homeworkId 作业ID
   * @param {Object} data 作业数据
   * @returns {Promise}
   */
  updateHomework(homeworkId, data) {
    return api.put(`/api/homework/${homeworkId}`, data)
  },

  /**
   * 删除作业
   * @param {number} homeworkId 作业ID
   * @returns {Promise}
   */
  deleteHomework(homeworkId) {
    return api.delete(`/api/homework/${homeworkId}`)
  },

  /**
   * 批量删除作业
   * @param {Array<number>} ids 作业ID数组
   * @returns {Promise}
   */
  batchDeleteHomework(ids) {
    return api.post('/api/homework/batch-delete', { ids })
  }
}

export default homeworkApi
