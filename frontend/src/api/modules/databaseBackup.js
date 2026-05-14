/**
 * 数据库备份管理 API 模块
 */

import { httpClient } from '@/shared/api/httpClient'

/**
 * 获取备份配置
 */
export function getBackupConfig() {
  return httpClient.get('/api/moral/admin/database-backup/config')
}

/**
 * 更新备份配置
 * @param {Object} data - { backup_dir, max_backups, include_wal }
 */
export function updateBackupConfig(data) {
  return httpClient.post('/api/moral/admin/database-backup/config', data)
}

/**
 * 手动执行备份
 */
export function executeManualBackup() {
  return httpClient.post('/api/moral/admin/database-backup/manual', null, {
    timeout: 60000
  })
}

/**
 * 获取备份历史
 * @param {Object} params - { page, size, backup_type }
 */
export function getBackupHistory(params = {}) {
  return httpClient.get('/api/moral/admin/database-backup/history', { params })
}

/**
 * 删除备份
 * @param {number} backupId - 备份ID
 */
export function deleteBackup(backupId) {
  return httpClient.delete(`/api/moral/admin/database-backup/delete/${backupId}`)
}

/**
 * 下载备份文件
 * @param {number} backupId - 备份ID
 */
export function downloadBackup(backupId) {
  return httpClient.get(`/api/moral/admin/database-backup/download/${backupId}`, {
    responseType: 'blob'
  })
}

/**
 * 获取定时备份配置
 */
export function getBackupSchedule() {
  return httpClient.get('/api/moral/admin/database-backup/schedule')
}

/**
 * 更新定时备份配置
 * @param {Object} data - { enabled, day_of_week, hour, minute }
 */
export function updateBackupSchedule(data) {
  return httpClient.post('/api/moral/admin/database-backup/schedule', data)
}

export default {
  getBackupConfig,
  updateBackupConfig,
  executeManualBackup,
  getBackupHistory,
  deleteBackup,
  downloadBackup,
  getBackupSchedule,
  updateBackupSchedule
}