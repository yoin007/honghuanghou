/**
 * 菜单权限配置 API
 */

import httpClient from '@/shared/api/httpClient'

/**
 * 获取所有菜单配置
 * @param {string} group - 分组筛选
 */
export function getMenuConfigList(group = null) {
  return httpClient.get('/api/moral/menu-permission/list', { params: { group } })
}

/**
 * 获取菜单分组列表
 */
export function getMenuGroups() {
  return httpClient.get('/api/moral/menu-permission/groups')
}

/**
 * 获取所有角色列表
 */
export function getAllRoles() {
  return httpClient.get('/api/moral/menu-permission/roles')
}

/**
 * 创建菜单配置
 * @param {object} config - 菜单配置项
 */
export function createMenuConfig(config) {
  return httpClient.post('/api/moral/menu-permission/create', config)
}

/**
 * 更新菜单配置
 * @param {string} menuKey - 菜单key
 * @param {object} config - 新配置
 */
export function updateMenuConfig(menuKey, config) {
  return httpClient.put(`/api/moral/menu-permission/${menuKey}`, config)
}

/**
 * 删除菜单配置
 * @param {string} menuKey - 菜单key
 */
export function deleteMenuConfig(menuKey) {
  return httpClient.delete(`/api/moral/menu-permission/${menuKey}`)
}

/**
 * 批量更新菜单角色
 * @param {array} menuKeys - 菜单key列表
 * @param {array} allowedRoles - 新的角色列表
 */
export function batchUpdateMenuRoles(menuKeys, allowedRoles) {
  return httpClient.post('/api/moral/menu-permission/batch', {
    menu_keys: menuKeys,
    allowed_roles: allowedRoles
  })
}

/**
 * 按分组批量更新菜单角色
 * @param {string} menuGroup - 菜单分组
 * @param {array} allowedRoles - 新的角色列表
 */
export function batchUpdateByGroup(menuGroup, allowedRoles) {
  return httpClient.post('/api/moral/menu-permission/batch-by-group', {
    menu_group: menuGroup,
    allowed_roles: allowedRoles
  })
}

/**
 * 初始化默认菜单配置
 */
export function initDefaultMenuConfig() {
  return httpClient.post('/api/moral/menu-permission/init')
}

/**
 * 重置为默认配置
 */
export function resetToDefault() {
  return httpClient.post('/api/moral/menu-permission/reset')
}