/**
 * 德育评价系统 API 模块
 * 提供所有德育相关的 API 调用函数
 */

import { httpClient } from '@/shared/api/httpClient'

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
  return httpClient.get('/api/moral/daily-records/types', { params })
}

/**
 * 创建日常事件类型
 */
export function createDailyEventType(data) {
  return httpClient.post('/api/moral/daily-records/types', data)
}

/**
 * 更新日常事件类型
 */
export function updateDailyEventType(typeId, data) {
  return httpClient.put(`/api/moral/daily-records/types/${typeId}`, data)
}

/**
 * 删除日常事件类型
 */
export function deleteDailyEventType(typeId) {
  return httpClient.delete(`/api/moral/daily-records/types/${typeId}`)
}

/**
 * 批量导入日常事件类型
 * @param {Array} items - 事件类型数组
 */
export function batchImportDailyEventTypes(items) {
  return httpClient.post('/api/moral/daily-records/types/batch-import', items)
}

/**
 * 获取日常表现记录列表
 * @param {Object} params - 查询参数
 */
export function getDailyRecords(params = {}) {
  return httpClient.get('/api/moral/daily-records', { params })
}

/**
 * 创建日常表现记录
 * @param {Object} data - 记录数据
 */
export function createDailyRecord(data) {
  return httpClient.post('/api/moral/daily-records', data)
}

/**
 * 批量创建日常表现记录
 * @param {Array} records - 记录数组
 */
export function batchCreateDailyRecords(records) {
  return httpClient.post('/api/moral/daily-records/batch', records)
}

/**
 * 更新日常表现记录
 * @param {number} recordId - 记录ID
 * @param {Object} data - 更新数据
 */
export function updateDailyRecord(recordId, data) {
  return httpClient.put(`/api/moral/daily-records/${recordId}`, data)
}

/**
 * 删除日常表现记录
 * @param {number} recordId - 记录ID
 */
export function deleteDailyRecord(recordId) {
  return httpClient.delete(`/api/moral/daily-records/${recordId}`)
}

/**
 * 获取学生日常表现统计
 * @param {string} studentId - 学号
 * @param {number} semesterId - 学期ID
 */
export function getStudentDailyStatistics(studentId, semesterId = null) {
  return httpClient.get(`/api/moral/daily-records/statistics/student/${studentId}`, {
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
  return httpClient.get('/api/moral/school-records/types', { params })
}

/**
 * 创建校级事件类型
 */
export function createSchoolEventType(data) {
  return httpClient.post('/api/moral/school-records/types', data)
}

/**
 * 更新校级事件类型
 */
export function updateSchoolEventType(typeId, data) {
  return httpClient.put(`/api/moral/school-records/types/${typeId}`, data)
}

/**
 * 删除校级事件类型
 */
export function deleteSchoolEventType(typeId) {
  return httpClient.delete(`/api/moral/school-records/types/${typeId}`)
}

/**
 * 批量导入校级事件类型
 * @param {Array} items - 事件类型数组
 */
export function batchImportSchoolEventTypes(items) {
  return httpClient.post('/api/moral/school-records/types/batch-import', items)
}

/**
 * 获取校级事件记录列表
 */
export function getSchoolRecords(params = {}) {
  return httpClient.get('/api/moral/school-records', { params })
}

/**
 * 创建校级事件记录
 */
export function createSchoolRecord(data) {
  return httpClient.post('/api/moral/school-records', data)
}

/**
 * 更新校级事件记录
 */
export function updateSchoolRecord(recordId, data) {
  return httpClient.put(`/api/moral/school-records/${recordId}`, data)
}

/**
 * 删除校级事件记录
 */
export function deleteSchoolRecord(recordId) {
  return httpClient.delete(`/api/moral/school-records/${recordId}`)
}

// =============================================================================
// 德育任务 API
// =============================================================================

/**
 * 获取德育任务列表
 */
export function getMoralTasks(params = {}) {
  return httpClient.get('/api/moral/tasks', { params })
}

/**
 * 创建德育任务
 */
export function createMoralTask(data) {
  return httpClient.post('/api/moral/tasks', data)
}

/**
 * 更新德育任务
 */
export function updateMoralTask(taskId, data) {
  return httpClient.put(`/api/moral/tasks/${taskId}`, data)
}

/**
 * 删除德育任务
 */
export function deleteMoralTask(taskId) {
  return httpClient.delete(`/api/moral/tasks/${taskId}`)
}

/**
 * 获取任务完成记录列表
 */
export function getTaskFinishRecords(params = {}) {
  return httpClient.get('/api/moral/tasks/finish', { params })
}

/**
 * 记录任务完成
 */
export function finishTask(data) {
  return httpClient.post('/api/moral/tasks/finish', data)
}

/**
 * 批量导入德育任务
 * @param {Array} items - 任务数组
 */
export function batchImportMoralTasks(items) {
  return httpClient.post('/api/moral/tasks/batch-import', items)
}

/**
 * 批量标记任务完成
 * @param {Object} data - { task_id, class_id?, student_ids?, finish_date?, remark? }
 */
export function batchFinishTask(data) {
  return httpClient.post('/api/moral/tasks/batch-finish', data)
}

// =============================================================================
// 任务结转 API
// =============================================================================

/**
 * 预览结转情况
 * @param {number} yearId - 学年ID
 */
export function previewCarryover(yearId) {
  return httpClient.get('/api/moral/carryover/preview', { params: { year_id: yearId } })
}

/**
 * 执行任务结转
 * @param {Object} data - { from_year_id, to_year_id }
 */
export function executeCarryover(data) {
  return httpClient.post('/api/moral/carryover/execute', data)
}

/**
 * 获取结转日志
 * @param {Object} params - 查询参数
 */
export function getCarryoverLogs(params = {}) {
  return httpClient.get('/api/moral/carryover/logs', { params })
}

/**
 * 获取结转配置
 */
export function getCarryoverConfig() {
  return httpClient.get('/api/moral/carryover/config')
}

/**
 * 更新结转配置
 * @param {Object} data - { carryover_factor, max_carryover_times }
 */
export function updateCarryoverConfig(data) {
  return httpClient.put('/api/moral/carryover/config', data)
}

// =============================================================================
// 升年级管理 API
// =============================================================================

/**
 * 预览升年级情况
 */
export function previewGradePromotion() {
  return httpClient.get('/api/moral/admin/grades/promote/preview')
}

/**
 * 执行升年级
 * @param {Object} data - { next_year_id? }
 */
export function executeGradePromotion(data = {}) {
  return httpClient.post('/api/moral/admin/grades/promote/execute', data)
}

/**
 * 获取已归档年级列表
 */
export function getArchivedGrades() {
  return httpClient.get('/api/moral/admin/grades/archived')
}

// =============================================================================
// 处分管理 API
// =============================================================================

/**
 * 获取处分记录列表
 */
export function getPunishments(params = {}) {
  return httpClient.get('/api/moral/punishments', { params })
}

/**
 * 创建处分记录
 */
export function createPunishment(data) {
  return httpClient.post('/api/moral/punishments', data)
}

/**
 * 更新处分记录
 */
export function updatePunishment(recordId, data) {
  return httpClient.put(`/api/moral/punishments/${recordId}`, data)
}

/**
 * 撤销处分
 */
export function revokePunishment(recordId, reason, revokeType = 2) {
  return httpClient.post(`/api/moral/punishments/${recordId}/revoke`, {
    revoke_reason: reason,
    revoke_type: revokeType
  })
}

/**
 * 获取处分复核信息
 */
export function getPunishmentReviewInfo(recordId) {
  return httpClient.get(`/api/moral/punishments/${recordId}/review-info`)
}

/**
 * 复核处分
 */
export function reviewPunishment(recordId, action, reason) {
  return httpClient.post(`/api/moral/punishments/${recordId}/review`, { action, reason })
}

// =============================================================================
// 评价查询 API
// =============================================================================

/**
 * 获取学生德育评价
 */
export function getStudentEvaluation(studentId, semesterId = null) {
  return httpClient.get(`/api/moral/evaluations/student/${studentId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 获取班级德育评价汇总
 */
export function getClassEvaluation(classId, semesterId = null) {
  return httpClient.get(`/api/moral/evaluations/class/${classId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 获取年级德育评价汇总
 */
export function getGradeEvaluation(gradeId, semesterId = null) {
  return httpClient.get(`/api/moral/evaluations/grade/${gradeId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 计算德育评价
 */
export function calculateEvaluation(params = {}) {
  return httpClient.post('/api/moral/evaluations/calculate', null, { params })
}

// =============================================================================
// 学生画像 API
// =============================================================================

/**
 * 获取学生画像
 */
export function getStudentProfile(studentId) {
  return httpClient.get(`/api/moral/profiles/student/${studentId}`)
}

/**
 * 生成学生画像
 */
export function generateStudentProfile(studentId) {
  return httpClient.post(`/api/moral/profiles/student/${studentId}/generate`, null, {
    timeout: 60000
  })
}

/**
 * 异步生成学生画像
 */
export function startStudentProfileGeneration(studentId) {
  return httpClient.post(`/api/moral/profiles/student/${studentId}/generate-async`, null, {
    timeout: 10000
  })
}

/**
 * 查询学生画像生成状态
 */
export function getStudentProfileGenerationStatus(jobId) {
  return httpClient.get(`/api/moral/profiles/generation-status/${jobId}`, {
    timeout: 10000
  })
}

/**
 * 批量生成学生画像
 */
export function batchGenerateProfiles(params = {}) {
  return httpClient.post('/api/moral/profiles/batch-generate', null, {
    params,
    timeout: 120000
  })
}

/**
 * 获取画像配置
 */
export function getProfileConfig() {
  return httpClient.get('/api/moral/profiles/config')
}

// =============================================================================
// 生日提醒 API
// =============================================================================

/**
 * 获取即将到来的生日
 */
export function getUpcomingBirthdays(days = 7, classId = null) {
  return httpClient.get('/api/moral/birthdays/upcoming', {
    params: { days, class_id: classId }
  })
}

/**
 * 获取今日过生日的学生
 */
export function getTodayBirthdays() {
  return httpClient.get('/api/moral/birthdays/today')
}

// =============================================================================
// AI诊疗 API
// =============================================================================

/**
 * 获取诊疗会话列表
 */
export function getConsultations(params = {}) {
  return httpClient.get('/api/moral/consultations', { params })
}

/**
 * 创建诊疗会话
 */
export function createConsultation(data) {
  return httpClient.post('/api/moral/consultations', data)
}

/**
 * 获取诊疗会话详情
 */
export function getConsultation(consultationId) {
  return httpClient.get(`/api/moral/consultations/${consultationId}`)
}

/**
 * 更新诊疗会话
 */
export function updateConsultation(consultationId, data) {
  return httpClient.put(`/api/moral/consultations/${consultationId}`, data)
}

/**
 * 添加诊疗消息
 */
export function addConsultationMessage(consultationId, data) {
  return httpClient.post(`/api/moral/consultations/${consultationId}/messages`, data)
}

/**
 * 关闭诊疗会话
 */
export function closeConsultation(consultationId, outcome = null) {
  return httpClient.post(`/api/moral/consultations/${consultationId}/close`, null, {
    params: { outcome }
  })
}

// =============================================================================
// 教师信息 API
// =============================================================================

/**
 * 获取教师列表（监考模块）
 */
export function getTeachers() {
  return httpClient.get('/api/teachers')
}

/**
 * 获取教师列表（德育配置模块，用于选择班主任/年级主任）
 */
export function getTeachersForConfig(params = {}) {
  return httpClient.get('/api/moral/admin/teachers', { params })
}

// =============================================================================
// 系统管理 API
// =============================================================================

/**
 * 获取级号列表
 */
export function getGrades() {
  return httpClient.get('/api/moral/admin/grades')
}

// =============================================================================
// 累进规则 API
// =============================================================================

/**
 * 获取累进规则列表
 */
export function getEscalationRules(params = {}) {
  return httpClient.get('/api/moral/escalation-rules', { params })
}

/**
 * 创建累进规则
 */
export function createEscalationRule(data) {
  return httpClient.post('/api/moral/escalation-rules', data)
}

/**
 * 更新累进规则
 */
export function updateEscalationRule(ruleId, data) {
  return httpClient.put(`/api/moral/escalation-rules/${ruleId}`, data)
}

/**
 * 删除累进规则
 */
export function deleteEscalationRule(ruleId) {
  return httpClient.delete(`/api/moral/escalation-rules/${ruleId}`)
}

/**
 * 获取可配置累进规则的消极事件列表
 */
export function getConfigurableEvents() {
  return httpClient.get('/api/moral/escalation-rules/events')
}

/**
 * 获取处罚类型列表（用于前端下拉框）
 */
export function getPunishmentTypes() {
  return httpClient.get('/api/moral/punishment-types')
}

/**
 * 获取学生累进处罚历史
 */
export function getStudentEscalationHistory(studentId, semesterId = null) {
  return httpClient.get(`/api/moral/escalation-rules/student/${studentId}/history`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 获取学生事件累计次数
 */
export function getStudentEventCount(studentId, eventId, timeWindowDays = 90) {
  return httpClient.get(`/api/moral/escalation-rules/student/${studentId}/count`, {
    params: { event_id: eventId, time_window_days: timeWindowDays }
  })
}

/**
 * 获取学生所有消极事件累计进度
 */
export function getStudentAllProgress(studentId) {
  return httpClient.get(`/api/moral/escalation-rules/student/${studentId}/progress`)
}

// =============================================================================
// API权限管理 API
// =============================================================================

/**
 * 获取API权限配置列表
 */
export function getApiPermissions(apiGroup = null) {
  return httpClient.get('/api/moral/api-permissions', {
    params: { api_group: apiGroup }
  })
}

/**
 * 获取API权限模块列表
 */
export function getApiPermissionModules() {
  return httpClient.get('/api/moral/api-permissions/modules')
}

/**
 * 创建API权限模块
 */
export function createApiPermissionModule(data) {
  return httpClient.post('/api/moral/api-permissions/modules', data)
}

/**
 * 更新API权限模块
 */
export function updateApiPermissionModule(moduleId, data) {
  return httpClient.put(`/api/moral/api-permissions/modules/${moduleId}`, data)
}

/**
 * 将模块权限应用到模块内API
 */
export function applyApiPermissionModule(moduleId) {
  return httpClient.post(`/api/moral/api-permissions/modules/${moduleId}/apply`)
}

/**
 * 同步旧版 YAML 权限配置
 */
export function syncLegacyApiPermissions() {
  return httpClient.post('/api/moral/api-permissions/sync-legacy-yaml')
}

/**
 * 创建API权限配置
 */
export function createApiPermission(data) {
  return httpClient.post('/api/moral/api-permissions', data)
}

/**
 * 更新API权限配置
 */
export function updateApiPermission(configId, data) {
  return httpClient.put(`/api/moral/api-permissions/${configId}`, data)
}

/**
 * 删除API权限配置
 */
export function deleteApiPermission(configId) {
  return httpClient.delete(`/api/moral/api-permissions/${configId}`)
}

/**
 * 获取当前用户可访问的API列表
 */
export function getMyApiPermissions() {
  return httpClient.get('/api/moral/api-permissions/my-permissions')
}

/**
 * 检查用户对特定API的权限
 */
export function checkApiPermission(apiPath) {
  return httpClient.get('/api/moral/api-permissions/check', {
    params: { api_path: apiPath }
  })
}

/**
 * 初始化默认API权限配置
 */
export function initApiPermissions() {
  return httpClient.post('/api/moral/api-permissions/init')
}

/**
 * 获取API分组列表
 */
export function getApiGroups() {
  return httpClient.get('/api/moral/api-permissions/groups')
}

// =============================================================================
// 集体事件 API
// =============================================================================

/**
 * 获取集体事件列表
 */
export function getCollectiveEvents(params = {}) {
  return httpClient.get('/api/moral/collective-events', { params })
}

/**
 * 创建集体事件
 */
export function createCollectiveEvent(data) {
  return httpClient.post('/api/moral/collective-events', data)
}

/**
 * 获取集体事件详情
 */
export function getCollectiveEvent(eventId) {
  return httpClient.get(`/api/moral/collective-events/${eventId}`)
}

/**
 * 更新集体事件
 */
export function updateCollectiveEvent(eventId, data) {
  return httpClient.put(`/api/moral/collective-events/${eventId}`, data)
}

/**
 * 删除集体事件
 */
export function deleteCollectiveEvent(eventId) {
  return httpClient.delete(`/api/moral/collective-events/${eventId}`)
}

/**
 * 更新分配记录
 */
export function updateDistribution(eventId, distributionId, data) {
  return httpClient.put(`/api/moral/collective-events/${eventId}/distributions/${distributionId}`, data)
}

/**
 * 获取学生集体事件得分汇总
 */
export function getStudentCollectiveScore(studentId, semesterId = null) {
  return httpClient.get(`/api/moral/collective-events/student/${studentId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 创建级号
 */
export function createGrade(data) {
  return httpClient.post('/api/moral/admin/grades', data)
}

/**
 * 更新级号
 */
export function updateGrade(gradeId, data) {
  return httpClient.put(`/api/moral/admin/grades/${gradeId}`, data)
}

/**
 * 删除级号
 */
export function deleteGrade(gradeId) {
  return httpClient.delete(`/api/moral/admin/grades/${gradeId}`)
}

/**
 * 获取班级列表
 */
export function getClasses(params = {}) {
  return httpClient.get('/api/moral/admin/classes', { params })
}

/**
 * 创建班级
 */
export function createClass(data) {
  return httpClient.post('/api/moral/admin/classes', data)
}

/**
 * 更新班级
 */
export function updateClass(classId, data) {
  return httpClient.put(`/api/moral/admin/classes/${classId}`, data)
}

/**
 * 删除班级
 */
export function deleteClass(classId) {
  return httpClient.delete(`/api/moral/admin/classes/${classId}`)
}

/**
 * 获取学年列表
 */
export function getSchoolYears() {
  return httpClient.get('/api/moral/admin/school-years')
}

/**
 * 创建学年
 */
export function createSchoolYear(data) {
  return httpClient.post('/api/moral/admin/school-years', data)
}

/**
 * 获取学期列表
 */
export function getSemesters(params = {}) {
  return httpClient.get('/api/moral/admin/semesters', { params })
}

/**
 * 创建学期
 */
export function createSemester(data) {
  return httpClient.post('/api/moral/admin/semesters', data)
}

/**
 * 设置当前学期
 */
export function setCurrentSemester(semesterId) {
  return httpClient.post(`/api/moral/admin/semesters/${semesterId}/set-current`)
}

/**
 * 获取学生列表
 */
export function getStudents(params = {}) {
  return httpClient.get('/api/moral/admin/students', { params })
}

/**
 * 批量创建学生
 */
export function batchCreateStudents(data) {
  return httpClient.post('/api/moral/admin/students/batch', data)
}

/**
 * 创建学生
 */
export function createStudent(data) {
  return httpClient.post('/api/moral/admin/students', data)
}

/**
 * 更新学生信息
 */
export function updateStudent(studentId, data) {
  return httpClient.put(`/api/moral/admin/students/${studentId}`, data)
}

/**
 * 更新学生状态
 */
export function updateStudentStatus(studentId, status) {
  return httpClient.put(`/api/moral/admin/students/${studentId}/status`, null, {
    params: { status }
  })
}

/**
 * 获取即时记录列表
 */
export function getMomentRecords(params = {}) {
  return httpClient.get('/api/moral/moment-records', { params })
}

/**
 * 创建即时记录
 */
export function createMomentRecord(data) {
  return httpClient.post('/api/moral/moment-records', data)
}

/**
 * 更新即时记录
 */
export function updateMomentRecord(recordId, data) {
  return httpClient.put(`/api/moral/moment-records/${recordId}`, data)
}

/**
 * 删除即时记录
 */
export function deleteMomentRecord(recordId) {
  return httpClient.delete(`/api/moral/moment-records/${recordId}`)
}

/**
 * 搜索时间线
 */
export function searchTimeline(params = {}) {
  return httpClient.get('/api/moral/timeline/search', { params })
}

/**
 * 获取学生时间线详情
 */
export function getStudentTimeline(studentId, params = {}) {
  return httpClient.get(`/api/moral/timeline/${studentId}`, { params })
}

/**
 * 获取操作日志
 */
export function getOperationLogs(params = {}) {
  return httpClient.get('/api/moral/admin/logs', { params })
}

/**
 * 获取系统配置
 */
export function getSystemConfig() {
  return httpClient.get('/api/moral/admin/config')
}

/**
 * 更新系统配置
 */
export function updateSystemConfig(data) {
  return httpClient.put('/api/moral/admin/config', data)
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
  batchImportMoralTasks,
  batchFinishTask,

  // 任务结转
  previewCarryover,
  executeCarryover,
  getCarryoverLogs,
  getCarryoverConfig,
  updateCarryoverConfig,

  // 升年级管理
  previewGradePromotion,
  executeGradePromotion,
  getArchivedGrades,

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
  startStudentProfileGeneration,
  getStudentProfileGenerationStatus,
  batchGenerateProfiles,
  getProfileConfig,

  // 生日查看
  getUpcomingBirthdays,
  getTodayBirthdays,

  // AI诊疗
  getConsultations,
  createConsultation,
  getConsultation,
  updateConsultation,
  addConsultationMessage,
  closeConsultation,

  // 教师信息
  getTeachers,
  getTeachersForConfig,

  // 系统管理
  getGrades,
  createGrade,
  updateGrade,
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
  getMomentRecords,
  createMomentRecord,
  updateMomentRecord,
  deleteMomentRecord,
  searchTimeline,
  getStudentTimeline,
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
  getPunishmentTypes,
  getStudentEscalationHistory,
  getStudentEventCount,
  getStudentAllProgress,

  // API权限管理
  getApiPermissions,
  createApiPermission,
  getApiPermissionModules,
  createApiPermissionModule,
  updateApiPermissionModule,
  applyApiPermissionModule,
  syncLegacyApiPermissions,
  updateApiPermission,
  deleteApiPermission,
  getMyApiPermissions,
  checkApiPermission,
  initApiPermissions,
  getApiGroups,

  // 集体事件
  getCollectiveEvents,
  createCollectiveEvent,
  getCollectiveEvent,
  updateCollectiveEvent,
  deleteCollectiveEvent,
  updateDistribution,
  getStudentCollectiveScore,
}
