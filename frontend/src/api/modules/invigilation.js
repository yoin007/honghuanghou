/**
 * 监考安排相关 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const invigilationApi = {
  /**
   * 获取监考项目列表
   * @returns {Promise}
   */
  getProjects() {
    return httpClient.get('/api/invigilation/projects')
  },

  /**
   * 获取监考教师列表
   * @returns {Promise}
   */
  getTeachers() {
    return httpClient.get('/api/invigilation/teachers')
  },

  /**
   * 获取单个监考项目详情
   * @param {number} projectId 项目ID
   * @returns {Promise}
   */
  getProject(projectId) {
    return httpClient.get(`/api/invigilation/projects/${projectId}`)
  },

  /**
   * 获取项目监考安排槽位
   * @param {number} projectId 项目ID
   * @returns {Promise}
   */
  getSlots(projectId) {
    return httpClient.get(`/api/invigilation/projects/${projectId}/slots`)
  },

  /**
   * 创建监考项目
   * @param {Object} data 项目数据
   * @returns {Promise}
   */
  createProject(data) {
    return httpClient.post('/api/invigilation/projects', data)
  },

  /**
   * 更新项目监考安排
   * @param {number} projectId 项目ID
   * @param {Object} data 安排数据 { slots, notify }
   * @returns {Promise}
   */
  updateSlots(projectId, data) {
    return httpClient.put(`/api/invigilation/projects/${projectId}/slots`, data)
  },

  /**
   * 获取项目变更预览
   * @param {number} projectId 项目ID
   * @param {Object} params 查询参数
   * @returns {Promise}
   */
  getChanges(projectId, params = {}) {
    return httpClient.get(`/api/invigilation/projects/${projectId}/changes`, { params })
  },

  /**
   * 发送监考通知
   * @param {number} projectId 项目ID
   * @param {Object} body 通知内容
   * @returns {Promise}
   */
  sendNotification(projectId, body) {
    // 通知是批量入队 + 逐条落库，人数多时会明显超过全局 10s 超时。
    // 每条估算 ~200ms（队列 INSERT + 日志 INSERT + commit），
    // 按 1500 人的上限给 5 分钟兜底；同时 silent=true 让业务层自己处理超时提示。
    return httpClient.post(`/api/invigilation/projects/${projectId}/notify`, body, {
      timeout: 300000,
      silent: true,
    })
  },

  /**
   * 获取通知日志
   * @param {number} projectId 项目ID
   * @returns {Promise}
   */
  getNotificationLogs(projectId) {
    return httpClient.get(`/api/invigilation/projects/${projectId}/notification-logs`)
  },

  /**
   * 下载导入模板
   * @returns {Promise} blob响应
   */
  downloadTemplate() {
    return httpClient.get('/api/invigilation/template', { responseType: 'blob' })
  },

  /**
   * 导入监考安排
   * @param {number} projectId 项目ID
   * @param {FormData} formData Excel文件
   * @returns {Promise}
   */
  importSlots(projectId, formData) {
    return httpClient.post(`/api/invigilation/projects/${projectId}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      // 让业务失败（success:false + errors[]）返回到调用方自己处理，
      // 不被拦截器吞成一句笼统的"操作失败"。
      returnBusinessError: true,
    })
  },

  /**
   * 导出监考安排
   * @param {number} projectId 项目ID
   * @returns {Promise} blob响应
   */
  exportSlots(projectId) {
    return httpClient.get(`/api/invigilation/projects/${projectId}/export`, { responseType: 'blob' })
  },

  /**
   * 下载工作量报表
   * @param {number} projectId 项目ID
   * @returns {Promise} blob响应
   */
  downloadReport(projectId) {
    return httpClient.get(`/api/invigilation/projects/${projectId}/report`, { responseType: 'blob' })
  },

  /**
   * 删除监考项目
   * @param {number} projectId 项目ID
   * @returns {Promise}
   */
  deleteProject(projectId) {
    return httpClient.delete(`/api/invigilation/projects/${projectId}`)
  }
}

export default invigilationApi