/**
 * 德育评价系统 API 模块
 * 提供所有德育相关的 API 调用函数
 */

import request from '@/utils/api'

// =============================================================================
// 日常表现记录 API
// =============================================================================

/**
 * 获取日常事件类型列表
 * @param {Object} params - 查询参数
 * @param {number} params.event_type - 事件类型：1=积极，2=消极
 * @param {number} params.is_active - 是否启用
 */
export function getDailyEventTypes(params = {}) {
  return request.get('/api/moral/daily-records/types', { params })
}

/**
 * 创建日常事件类型
 */
export function createDailyEventType(data) {
  return request.post('/api/moral/daily-records/types', data)
}

/**
 * 更新日常事件类型
 */
export function updateDailyEventType(typeId, data) {
  return request.put(`/api/moral/daily-records/types/${typeId}`, data)
}

/**
 * 删除日常事件类型
 */
export function deleteDailyEventType(typeId) {
  return request.delete(`/api/moral/daily-records/types/${typeId}`)
}

/**
 * 批量导入日常事件类型
 * @param {Array} items - 事件类型数组
 */
export function batchImportDailyEventTypes(items) {
  return request.post('/api/moral/daily-records/types/batch-import', items)
}

/**
 * 获取日常表现记录列表
 * @param {Object} params - 查询参数
 */
export function getDailyRecords(params = {}) {
  return request.get('/api/moral/daily-records', { params })
}

/**
 * 创建日常表现记录
 * @param {Object} data - 记录数据
 */
export function createDailyRecord(data) {
  return request.post('/api/moral/daily-records', data)
}

/**
 * 批量创建日常表现记录
 * @param {Array} records - 记录数组
 */
export function batchCreateDailyRecords(records) {
  return request.post('/api/moral/daily-records/batch', records)
}

/**
 * 更新日常表现记录
 * @param {number} recordId - 记录ID
 * @param {Object} data - 更新数据
 */
export function updateDailyRecord(recordId, data) {
  return request.put(`/api/moral/daily-records/${recordId}`, data)
}

/**
 * 删除日常表现记录
 * @param {number} recordId - 记录ID
 */
export function deleteDailyRecord(recordId) {
  return request.delete(`/api/moral/daily-records/${recordId}`)
}

/**
 * 获取学生日常表现统计
 * @param {string} studentId - 学号
 * @param {number} semesterId - 学期ID
 */
export function getStudentDailyStatistics(studentId, semesterId = null) {
  return request.get(`/api/moral/daily-records/statistics/student/${studentId}`, {
    params: { semester_id: semesterId }
  })
}

// =============================================================================
// 校级事件记录 API
// =============================================================================

/**
 * 获取校级事件类型列表
 */
export function getSchoolEventTypes(params = {}) {
  return request.get('/api/moral/school-records/types', { params })
}

/**
 * 创建校级事件类型
 */
export function createSchoolEventType(data) {
  return request.post('/api/moral/school-records/types', data)
}

/**
 * 更新校级事件类型
 */
export function updateSchoolEventType(typeId, data) {
  return request.put(`/api/moral/school-records/types/${typeId}`, data)
}

/**
 * 删除校级事件类型
 */
export function deleteSchoolEventType(typeId) {
  return request.delete(`/api/moral/school-records/types/${typeId}`)
}

/**
 * 批量导入校级事件类型
 * @param {Array} items - 事件类型数组
 */
export function batchImportSchoolEventTypes(items) {
  return request.post('/api/moral/school-records/types/batch-import', items)
}

/**
 * 获取校级事件记录列表
 */
export function getSchoolRecords(params = {}) {
  return request.get('/api/moral/school-records', { params })
}

/**
 * 创建校级事件记录
 */
export function createSchoolRecord(data) {
  return request.post('/api/moral/school-records', data)
}

/**
 * 更新校级事件记录
 */
export function updateSchoolRecord(recordId, data) {
  return request.put(`/api/moral/school-records/${recordId}`, data)
}

/**
 * 删除校级事件记录
 */
export function deleteSchoolRecord(recordId) {
  return request.delete(`/api/moral/school-records/${recordId}`)
}

// =============================================================================
// 德育任务 API
// =============================================================================

/**
 * 获取德育任务列表
 */
export function getMoralTasks(params = {}) {
  return request.get('/api/moral/tasks', { params })
}

/**
 * 创建德育任务
 */
export function createMoralTask(data) {
  return request.post('/api/moral/tasks', data)
}

/**
 * 更新德育任务
 */
export function updateMoralTask(taskId, data) {
  return request.put(`/api/moral/tasks/${taskId}`, data)
}

/**
 * 删除德育任务
 */
export function deleteMoralTask(taskId) {
  return request.delete(`/api/moral/tasks/${taskId}`)
}

/**
 * 获取任务完成记录列表
 */
export function getTaskFinishRecords(params = {}) {
  return request.get('/api/moral/tasks/finish', { params })
}

/**
 * 记录任务完成
 */
export function finishTask(data) {
  return request.post('/api/moral/tasks/finish', data)
}

/**
 * 批量导入德育任务
 * @param {Array} items - 任务数组
 */
export function batchImportMoralTasks(items) {
  return request.post('/api/moral/tasks/batch-import', items)
}

// =============================================================================
// 处分管理 API
// =============================================================================

/**
 * 获取处分记录列表
 */
export function getPunishments(params = {}) {
  return request.get('/api/moral/punishments', { params })
}

/**
 * 创建处分记录
 */
export function createPunishment(data) {
  return request.post('/api/moral/punishments', data)
}

/**
 * 更新处分记录
 */
export function updatePunishment(recordId, data) {
  return request.put(`/api/moral/punishments/${recordId}`, data)
}

/**
 * 撤销处分
 */
export function revokePunishment(recordId, reason) {
  return request.post(`/api/moral/punishments/${recordId}/revoke`, { revoke_reason: reason })
}

// =============================================================================
// 评价查询 API
// =============================================================================

/**
 * 获取学生德育评价
 */
export function getStudentEvaluation(studentId, semesterId = null) {
  return request.get(`/api/moral/evaluations/student/${studentId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 获取班级德育评价汇总
 */
export function getClassEvaluation(classId, semesterId = null) {
  return request.get(`/api/moral/evaluations/class/${classId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 获取年级德育评价汇总
 */
export function getGradeEvaluation(gradeId, semesterId = null) {
  return request.get(`/api/moral/evaluations/grade/${gradeId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 计算德育评价
 */
export function calculateEvaluation(params = {}) {
  return request.post('/api/moral/evaluations/calculate', null, { params })
}

// =============================================================================
// 学生画像 API
// =============================================================================

/**
 * 获取学生画像
 */
export function getStudentProfile(studentId) {
  return request.get(`/api/moral/profiles/student/${studentId}`)
}

/**
 * 生成学生画像
 */
export function generateStudentProfile(studentId) {
  return request.post(`/api/moral/profiles/student/${studentId}/generate`)
}

/**
 * 批量生成学生画像
 */
export function batchGenerateProfiles(params = {}) {
  return request.post('/api/moral/profiles/batch-generate', null, { params })
}

/**
 * 获取画像配置
 */
export function getProfileConfig() {
  return request.get('/api/moral/profiles/config')
}

// =============================================================================
// 生日提醒 API
// =============================================================================

/**
 * 获取即将到来的生日
 */
export function getUpcomingBirthdays(days = 7, classId = null) {
  return request.get('/api/moral/birthdays/upcoming', {
    params: { days, class_id: classId }
  })
}

/**
 * 获取今日过生日的学生
 */
export function getTodayBirthdays() {
  return request.get('/api/moral/birthdays/today')
}

/**
 * 获取生日提醒列表
 */
export function getBirthdayReminders(params = {}) {
  return request.get('/api/moral/birthdays/reminders', { params })
}

/**
 * 创建生日提醒
 */
export function createBirthdayReminder(data) {
  return request.post('/api/moral/birthdays/reminders', data)
}

/**
 * 发送生日提醒
 */
export function sendBirthdayReminder(reminderId) {
  return request.post(`/api/moral/birthdays/reminders/${reminderId}/send`)
}

/**
 * 生成本月生日提醒
 */
export function generateMonthlyReminders() {
  return request.post('/api/moral/birthdays/generate')
}

/**
 * 获取生日提醒配置
 */
export function getBirthdayConfig() {
  return request.get('/api/moral/birthdays/config')
}

// =============================================================================
// AI诊疗 API
// =============================================================================

/**
 * 获取诊疗会话列表
 */
export function getConsultations(params = {}) {
  return request.get('/api/moral/consultations', { params })
}

/**
 * 创建诊疗会话
 */
export function createConsultation(data) {
  return request.post('/api/moral/consultations', data)
}

/**
 * 获取诊疗会话详情
 */
export function getConsultation(consultationId) {
  return request.get(`/api/moral/consultations/${consultationId}`)
}

/**
 * 更新诊疗会话
 */
export function updateConsultation(consultationId, data) {
  return request.put(`/api/moral/consultations/${consultationId}`, data)
}

/**
 * 添加诊疗消息
 */
export function addConsultationMessage(consultationId, data) {
  return request.post(`/api/moral/consultations/${consultationId}/messages`, data)
}

/**
 * 关闭诊疗会话
 */
export function closeConsultation(consultationId, outcome = null) {
  return request.post(`/api/moral/consultations/${consultationId}/close`, null, {
    params: { outcome }
  })
}

// =============================================================================
// 教师信息 API
// =============================================================================

/**
 * 获取教师列表
 */
export function getTeachers() {
  return request.get('/api/teachers')
}

// =============================================================================
// 系统管理 API
// =============================================================================

/**
 * 获取级号列表
 */
export function getGrades() {
  return request.get('/api/moral/admin/grades')
}

// =============================================================================
// 累进规则 API
// =============================================================================

/**
 * 获取累进规则列表
 */
export function getEscalationRules(params = {}) {
  return request.get('/api/moral/escalation-rules', { params })
}

/**
 * 创建累进规则
 */
export function createEscalationRule(data) {
  return request.post('/api/moral/escalation-rules', data)
}

/**
 * 更新累进规则
 */
export function updateEscalationRule(ruleId, data) {
  return request.put(`/api/moral/escalation-rules/${ruleId}`, data)
}

/**
 * 删除累进规则
 */
export function deleteEscalationRule(ruleId) {
  return request.delete(`/api/moral/escalation-rules/${ruleId}`)
}

/**
 * 获取可配置累进规则的消极事件列表
 */
export function getConfigurableEvents() {
  return request.get('/api/moral/escalation-rules/events')
}

/**
 * 获取学生累进处罚历史
 */
export function getStudentEscalationHistory(studentId, semesterId = null) {
  return request.get(`/api/moral/escalation-rules/student/${studentId}/history`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 获取学生事件累计次数
 */
export function getStudentEventCount(studentId, eventId, timeWindowDays = 90) {
  return request.get(`/api/moral/escalation-rules/student/${studentId}/count`, {
    params: { event_id: eventId, time_window_days: timeWindowDays }
  })
}

/**
 * 获取学生所有消极事件累计进度
 */
export function getStudentAllProgress(studentId) {
  return request.get(`/api/moral/escalation-rules/student/${studentId}/progress`)
}

// =============================================================================
// API权限管理 API
// =============================================================================

/**
 * 获取API权限配置列表
 */
export function getApiPermissions(apiGroup = null) {
  return request.get('/api/moral/api-permissions', {
    params: { api_group: apiGroup }
  })
}

/**
 * 创建API权限配置
 */
export function createApiPermission(data) {
  return request.post('/api/moral/api-permissions', data)
}

/**
 * 更新API权限配置
 */
export function updateApiPermission(configId, data) {
  return request.put(`/api/moral/api-permissions/${configId}`, data)
}

/**
 * 删除API权限配置
 */
export function deleteApiPermission(configId) {
  return request.delete(`/api/moral/api-permissions/${configId}`)
}

/**
 * 获取当前用户可访问的API列表
 */
export function getMyApiPermissions() {
  return request.get('/api/moral/api-permissions/my-permissions')
}

/**
 * 检查用户对特定API的权限
 */
export function checkApiPermission(apiPath) {
  return request.get('/api/moral/api-permissions/check', {
    params: { api_path: apiPath }
  })
}

/**
 * 初始化默认API权限配置
 */
export function initApiPermissions() {
  return request.post('/api/moral/api-permissions/init')
}

/**
 * 获取API分组列表
 */
export function getApiGroups() {
  return request.get('/api/moral/api-permissions/groups')
}

/**
 * 创建级号
 */
export function createGrade(data) {
  return request.post('/api/moral/admin/grades', data)
}

/**
 * 删除级号
 */
export function deleteGrade(gradeId) {
  return request.delete(`/api/moral/admin/grades/${gradeId}`)
}

/**
 * 获取班级列表
 */
export function getClasses(params = {}) {
  return request.get('/api/moral/admin/classes', { params })
}

/**
 * 创建班级
 */
export function createClass(data) {
  return request.post('/api/moral/admin/classes', data)
}

/**
 * 更新班级
 */
export function updateClass(classId, data) {
  return request.put(`/api/moral/admin/classes/${classId}`, data)
}

/**
 * 删除班级
 */
export function deleteClass(classId) {
  return request.delete(`/api/moral/admin/classes/${classId}`)
}

/**
 * 获取学年列表
 */
export function getSchoolYears() {
  return request.get('/api/moral/admin/school-years')
}

/**
 * 创建学年
 */
export function createSchoolYear(data) {
  return request.post('/api/moral/admin/school-years', data)
}

/**
 * 获取学期列表
 */
export function getSemesters(params = {}) {
  return request.get('/api/moral/admin/semesters', { params })
}

/**
 * 创建学期
 */
export function createSemester(data) {
  return request.post('/api/moral/admin/semesters', data)
}

/**
 * 设置当前学期
 */
export function setCurrentSemester(semesterId) {
  return request.post(`/api/moral/admin/semesters/${semesterId}/set-current`)
}

/**
 * 获取学生列表
 */
export function getStudents(params = {}) {
  return request.get('/api/moral/admin/students', { params })
}

/**
 * 批量创建学生
 */
export function batchCreateStudents(data) {
  return request.post('/api/moral/admin/students/batch', data)
}

/**
 * 创建学生
 */
export function createStudent(data) {
  return request.post('/api/moral/admin/students', data)
}

/**
 * 更新学生信息
 */
export function updateStudent(studentId, data) {
  return request.put(`/api/moral/admin/students/${studentId}`, data)
}

/**
 * 更新学生状态
 */
export function updateStudentStatus(studentId, status) {
  return request.put(`/api/moral/admin/students/${studentId}/status`, null, {
    params: { status }
  })
}

/**
 * 获取操作日志
 */
export function getOperationLogs(params = {}) {
  return request.get('/api/moral/admin/logs', { params })
}

/**
 * 获取系统配置
 */
export function getSystemConfig() {
  return request.get('/api/moral/admin/config')
}

/**
 * 更新系统配置
 */
export function updateSystemConfig(data) {
  return request.put('/api/moral/admin/config', data)
}

// 导出所有 API
export default {
  // 日常表现
  getDailyEventTypes,
  getDailyRecords,
  createDailyRecord,
  batchCreateDailyRecords,
  updateDailyRecord,
  deleteDailyRecord,
  getStudentDailyStatistics,

  // 校级事件
  getSchoolEventTypes,
  getSchoolRecords,
  createSchoolRecord,
  updateSchoolRecord,
  deleteSchoolRecord,

  // 德育任务
  getMoralTasks,
  createMoralTask,
  updateMoralTask,
  deleteMoralTask,
  getTaskFinishRecords,
  finishTask,

  // 处分管理
  getPunishments,
  createPunishment,
  updatePunishment,
  revokePunishment,

  // 评价查询
  getStudentEvaluation,
  getClassEvaluation,
  getGradeEvaluation,
  calculateEvaluation,

  // 学生画像
  getStudentProfile,
  generateStudentProfile,
  batchGenerateProfiles,
  getProfileConfig,

  // 生日提醒
  getUpcomingBirthdays,
  getTodayBirthdays,
  getBirthdayReminders,
  createBirthdayReminder,
  sendBirthdayReminder,
  generateMonthlyReminders,
  getBirthdayConfig,

  // AI诊疗
  getConsultations,
  createConsultation,
  getConsultation,
  updateConsultation,
  addConsultationMessage,
  closeConsultation,

  // 教师信息
  getTeachers,

  // 系统管理
  getGrades,
  createGrade,
  deleteGrade,
  getClasses,
  createClass,
  updateClass,
  deleteClass,
  getSchoolYears,
  createSchoolYear,
  getSemesters,
  createSemester,
  setCurrentSemester,
  getStudents,
  createStudent,
  updateStudent,
  updateStudentStatus,
  getOperationLogs,
  getSystemConfig,
  updateSystemConfig,

  // 事件类型管理
  createDailyEventType,
  updateDailyEventType,
  deleteDailyEventType,
  createSchoolEventType,
  updateSchoolEventType,
  deleteSchoolEventType,

  // 累进规则
  getEscalationRules,
  createEscalationRule,
  updateEscalationRule,
  deleteEscalationRule,
  getConfigurableEvents,
  getStudentEscalationHistory,
  getStudentEventCount,
  getStudentAllProgress,

  // API权限管理
  getApiPermissions,
  createApiPermission,
  updateApiPermission,
  deleteApiPermission,
  getMyApiPermissions,
  checkApiPermission,
  initApiPermissions,
  getApiGroups,
}