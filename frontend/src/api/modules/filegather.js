/**
 * 文件收集系统 API 模块
 */
import api from '../../utils/api'

export const filegatherApi = {
  // ==================== 教师端 ====================

  /**
   * 上传文件
   * @param {File} file 文件对象
   * @param {number} copies 打印份数
   * @param {string} useDate 使用日期 (YYYY-MM-DD)
   * @param {string} note 备注
   * @returns {Promise}
   */
  uploadFile(file, copies, useDate, note = '') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('copies', copies)
    formData.append('use_date', useDate)
    if (note) {
      formData.append('note', note)
    }
    return api.post('/api/filegather/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000 // 60秒超时
    })
  },

  /**
   * 获取我的文件列表
   * @param {string} month 月份 (YYYYMM格式)
   * @returns {Promise}
   */
  getMyFiles(month = '') {
    const params = month ? { month } : {}
    return api.get('/api/filegather/my-files', { params })
  },

  /**
   * 删除文件
   * @param {number} fileId 文件ID
   * @returns {Promise}
   */
  deleteFile(fileId) {
    return api.delete(`/api/filegather/my-files/${fileId}`)
  },

  // ==================== 教务端 ====================

  /**
   * 获取待处理文件列表
   * @returns {Promise}
   */
  getPendingFiles() {
    return api.get('/api/filegather/admin/files')
  },

  /**
   * 获取已完成文件列表
   * @param {string} month 月份 (YYYYMM格式)
   * @returns {Promise}
   */
  getDoneFiles(month = '') {
    const params = month ? { month } : {}
    return api.get('/api/filegather/admin/done-files', { params })
  },

  /**
   * 标记文件为已完成
   * @param {number} fileId 文件ID
   * @returns {Promise}
   */
  markDone(fileId) {
    return api.post(`/api/filegather/admin/mark-done/${fileId}`)
  },

  /**
   * 获取下载链接
   * @param {number} fileId 文件ID
   * @returns {string} 下载URL
   */
  getDownloadUrl(fileId) {
    // 获取token
    const token = localStorage.getItem('token')
    const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
    return `${baseUrl}/api/filegather/admin/download/${fileId}?token=${token}`
  },

  /**
   * 下载文件
   * @param {number} fileId 文件ID
   * @returns {Promise}
   */
  downloadFile(fileId) {
    return api.get(`/api/filegather/admin/download/${fileId}`, {
      responseType: 'blob'
    })
  },

  /**
   * 获取统计信息
   * @param {string} month 月份 (YYYYMM格式)
   * @returns {Promise}
   */
  getStatistics(month = '') {
    const params = month ? { month } : {}
    return api.get('/api/filegather/admin/statistics', { params })
  },

  /**
   * 获取月份列表
   * @returns {Promise}
   */
  getMonths() {
    return api.get('/api/filegather/admin/months')
  }
}

export default filegatherApi