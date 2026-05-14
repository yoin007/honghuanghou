/**
 * 教师待办 API 模块
 * 提供教师个人及协作型待办事项的管理接口
 */

import { httpClient } from '@/shared/api/httpClient'

// =============================================================================
// 待办查询 API
// =============================================================================

/**
 * 查询待办列表
 * @param {Object} params - 查询参数
 * @param {string} params.view - 视图: week/month/year
 * @param {string} params.anchor_date - 当前周期锚点日期
 * @param {string} params.status - 状态筛选: all/pending/completed
 * @param {string} params.scope - 范围: all_visible/created/assigned
 */
export function getTodos(params = {}) {
  return httpClient.get('/api/teacher/todos', { params })
}

/**
 * 获取即将到期待办（用于教师工作台）
 * @param {Object} params - 查询参数
 * @param {number} params.days - 查询未来N天内的待办
 * @param {number} params.limit - 返回数量上限
 */
export function getUpcomingTodos(params = {}) {
  return httpClient.get('/api/teacher/todos/upcoming', { params })
}

// =============================================================================
// 待办创建/更新/删除 API
// =============================================================================

/**
 * 创建待办
 * @param {Object} data - 待办数据
 * @param {string} data.title - 标题
 * @param {string} data.description - 描述
 * @param {string} data.todo_type - 类型: one_off/weekly/monthly/yearly
 * @param {string} data.start_date - 生效开始日期
 * @param {string} data.end_date - 生效结束日期
 * @param {Object} data.recurrence_rule - 周期规则
 * @param {Array} data.assignee_teacher_ids - 关联教师ID列表
 */
export function createTodo(data) {
  return httpClient.post('/api/teacher/todos/create', data)
}

/**
 * 更新待办
 * @param {number} seriesId - 待办ID
 * @param {Object} data - 更新数据
 */
export function updateTodo(seriesId, data) {
  return httpClient.put(`/api/teacher/todos/${seriesId}`, data)
}

/**
 * 删除待办
 * @param {number} seriesId - 待办ID
 */
export function deleteTodo(seriesId) {
  return httpClient.delete(`/api/teacher/todos/${seriesId}`)
}

// =============================================================================
// 待办实例操作 API
// =============================================================================

/**
 * 完成待办实例
 * @param {number} occurrenceId - 实例ID
 * @param {string} completedDate - 完成日期
 */
export function completeOccurrence(occurrenceId, completedDate) {
  return httpClient.post(`/api/teacher/todos/occurrences/${occurrenceId}/complete`, {
    completed_date: completedDate
  })
}

/**
 * 重开待办实例（取消完成状态）
 * @param {number} occurrenceId - 实例ID
 */
export function reopenOccurrence(occurrenceId) {
  return httpClient.post(`/api/teacher/todos/occurrences/${occurrenceId}/reopen`)
}