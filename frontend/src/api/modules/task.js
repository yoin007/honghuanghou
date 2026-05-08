/**
 * 系统任务管理 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const taskApi = {
  /**
   * 获取任务函数列表
   * @returns {Promise}
   */
  getTaskFuncs() {
    return httpClient.get('/api/tasks/funcs')
  },

  /**
   * 获取任务列表
   * @param {Object} params 查询参数
   * @returns {Promise}
   */
  getTasks(params = {}) {
    return httpClient.get('/api/tasks', { params })
  },

  /**
   * 创建任务
   * @param {Object} data 任务数据
   * @returns {Promise}
   */
  createTask(data) {
    return httpClient.post('/api/tasks', data)
  },

  /**
   * 更新任务
   * @param {number} taskId 任务ID
   * @param {Object} data 任务数据
   * @returns {Promise}
   */
  updateTask(taskId, data) {
    return httpClient.put(`/api/tasks/${taskId}`, data)
  },

  /**
   * 删除任务
   * @param {number} taskId 任务ID
   * @returns {Promise}
   */
  deleteTask(taskId) {
    return httpClient.delete(`/api/tasks/${taskId}`)
  }
}

// 导出独立函数
export const getTaskFuncs = taskApi.getTaskFuncs
export const getTasks = taskApi.getTasks
export const createTask = taskApi.createTask
export const updateTask = taskApi.updateTask
export const deleteTask = taskApi.deleteTask

export default taskApi