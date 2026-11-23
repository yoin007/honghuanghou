/**
 * 需求中心 API 模块
 * 需求提交、列表查询、状态跟踪（详见 docs/requirements/REQ-2026-003）
 */

import { httpClient } from '@/shared/api/httpClient'

/**
 * 提交功能需求
 * @param {Object} data - { title, problem, scenario?, expectation }
 */
export function submitRequirement(data) {
  return httpClient.post('/api/requirements', data)
}

/**
 * 查询需求列表
 * @param {string} scope - mine（自己的，全员）/ all（全部，仅教务管理员）
 */
export function listRequirements(scope = 'mine') {
  return httpClient.get('/api/requirements', { params: { scope } })
}

/**
 * 需求详情与进展时间线
 * @param {number} id - 需求ID
 */
export function getRequirementDetail(id) {
  return httpClient.get(`/api/requirements/${id}`)
}

/**
 * 更新需求状态（教务/管理员）
 * @param {number} id - 需求ID
 * @param {Object} data - { status, note? }
 */
export function updateRequirementStatus(id, data) {
  return httpClient.put(`/api/requirements/${id}/status`, data)
}

/**
 * 追加补充说明
 * @param {number} id - 需求ID
 * @param {string} note - 说明内容
 */
export function addRequirementComment(id, note) {
  return httpClient.post(`/api/requirements/${id}/comments`, { note })
}
