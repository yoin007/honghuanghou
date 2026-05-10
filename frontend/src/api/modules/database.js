/**
 * 数据库管理 API 模块
 */

import { httpClient } from '@/shared/api/httpClient'

/**
 * 获取数据库列表
 */
export function listDatabases() {
  return httpClient.get('/api/moral/admin/database/list')
}

/**
 * 获取数据库表列表
 * @param {string} dbName - 数据库文件名
 */
export function getDatabaseTables(dbName) {
  return httpClient.get(`/api/moral/admin/database/tables/${dbName}`)
}

/**
 * 获取受保护表列表
 */
export function getProtectedTables() {
  return httpClient.get('/api/moral/admin/database/protected-tables')
}

/**
 * 生成清空确认令牌
 * @param {string} dbName - 数据库文件名
 * @param {string} tableName - 表名
 */
export function generateClearToken(dbName, tableName) {
  return httpClient.get(`/api/moral/admin/database/generate-token/${dbName}/${tableName}`)
}

/**
 * 清空表数据
 * @param {string} dbName - 数据库文件名
 * @param {string} tableName - 表名
 * @param {string} confirmationToken - 确认令牌
 */
export function clearTable(dbName, tableName, confirmationToken) {
  return httpClient.post(`/api/moral/admin/database/clear/${dbName}/${tableName}`, {
    confirmation_token: confirmationToken
  })
}

/**
 * 检查数据库完整性
 */
export function checkDatabaseIntegrity() {
  return httpClient.get('/api/moral/admin/database/check-integrity')
}

export default {
  listDatabases,
  getDatabaseTables,
  getProtectedTables,
  generateClearToken,
  clearTable,
  checkDatabaseIntegrity
}