/**
 * API 权限管理 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const permissionApi = {
  /**
   * 获取权限列表
   * @param {Object} params 查询参数
   * @returns {Promise}
   */
  getPermissions(params = {}) {
    return httpClient.get('/api/permissions', { params })
  },

  /**
   * 创建权限
   * @param {Object} data 权限数据
   * @returns {Promise}
   */
  createPermission(data) {
    return httpClient.post('/api/permissions', data)
  },

  /**
   * 更新权限
   * @param {number} permissionId 权限ID
   * @param {Object} data 权限数据
   * @returns {Promise}
   */
  updatePermission(permissionId, data) {
    return httpClient.put(`/api/permissions/${permissionId}`, data)
  },

  /**
   * 删除权限
   * @param {number} permissionId 权限ID
   * @returns {Promise}
   */
  deletePermission(permissionId) {
    return httpClient.delete(`/api/permissions/${permissionId}`)
  },

  /**
   * 切换权限激活状态
   * @param {number} permissionId 权限ID
   * @param {boolean} activate 是否激活
   * @returns {Promise}
   */
  togglePermission(permissionId, activate) {
    return httpClient.put(`/api/permissions/${permissionId}`, { activate })
  }
}

export const getPermissions = permissionApi.getPermissions
export const createPermission = permissionApi.createPermission
export const updatePermission = permissionApi.updatePermission
export const deletePermission = permissionApi.deletePermission
export const togglePermission = permissionApi.togglePermission

export default permissionApi