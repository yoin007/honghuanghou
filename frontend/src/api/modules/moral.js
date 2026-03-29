/**
 * 德育评价系统 API 模块
 * 提供所有德育相关的 API 调用函数
 */

import request from '../request'

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
  return request.get('/moral/daily-records/types', { params })
}

/**
 * 获取日常表现记录列表
 * @param {Object} params - 查询参数
 */
export function getDailyRecords(params = {}) {
  return request.get('/moral/daily-records', { params })
}

/**
 * 创建日常表现记录
 * @param {Object} data - 记录数据
 */
export function createDailyRecord(data) {
  return request.post('/moral/daily-records', data)
}

/**
 * 批量创建日常表现记录
 * @param {Array} records - 记录数组
 */
export function batchCreateDailyRecords(records) {
  return request.post('/moral/daily-records/batch', records)
}

/**
 * 更新日常表现记录
 * @param {number} recordId - 记录ID
 * @param {Object} data - 更新数据
 */
export function updateDailyRecord(recordId, data) {
  return request.put(`/moral/daily-records/${recordId}`, data)
}

/**
 * 删除日常表现记录
 * @param {number} recordId - 记录ID
 */
export function deleteDailyRecord(recordId) {
  return request.delete(`/moral/daily-records/${recordId}`)
}

/**
 * 获取学生日常表现统计
 * @param {string} studentId - 学号
 * @param {number} semesterId - 学期ID
 */
export function getStudentDailyStatistics(studentId, semesterId = null) {
  return request.get(`/moral/daily-records/statistics/student/${studentId}`, {
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
  return request.get('/moral/school-records/types', { params })
}

/**
 * 获取校级事件记录列表
 */
export function getSchoolRecords(params = {}) {
  return request.get('/moral/school-records', { params })
}

/**
 * 创建校级事件记录
 */
export function createSchoolRecord(data) {
  return request.post('/moral/school-records', data)
}

/**
 * 更新校级事件记录
 */
export function updateSchoolRecord(recordId, data) {
  return request.put(`/moral/school-records/${recordId}`, data)
}

/**
 * 删除校级事件记录
 */
export function deleteSchoolRecord(recordId) {
  return request.delete(`/moral/school-records/${recordId}`)
}

// =============================================================================
// 德育任务 API
// =============================================================================

/**
 * 获取德育任务列表
 */
export function getMoralTasks(params = {}) {
  return request.get('/moral/tasks', { params })
}

/**
 * 创建德育任务
 */
export function createMoralTask(data) {
  return request.post('/moral/tasks', data)
}

/**
 * 更新德育任务
 */
export function updateMoralTask(taskId, data) {
  return request.put(`/moral/tasks/${taskId}`, data)
}

/**
 * 删除德育任务
 */
export function deleteMoralTask(taskId) {
  return request.delete(`/moral/tasks/${taskId}`)
}

/**
 * 获取任务完成记录列表
 */
export function getTaskFinishRecords(params = {}) {
  return request.get('/moral/tasks/finish', { params })
}

/**
 * 记录任务完成
 */
export function finishTask(data) {
  return request.post('/moral/tasks/finish', data)
}

// =============================================================================
// 处分管理 API
// =============================================================================

/**
 * 获取处分记录列表
 */
export function getPunishments(params = {}) {
  return request.get('/moral/punishments', { params })
}

/**
 * 创建处分记录
 */
export function createPunishment(data) {
  return request.post('/moral/punishments', data)
}

/**
 * 更新处分记录
 */
export function updatePunishment(recordId, data) {
  return request.put(`/moral/punishments/${recordId}`, data)
}

/**
 * 撤销处分
 */
export function revokePunishment(recordId, reason) {
  return request.post(`/moral/punishments/${recordId}/revoke`, { revoke_reason: reason })
}

// =============================================================================
// 评价查询 API
// =============================================================================

/**
 * 获取学生德育评价
 */
export function getStudentEvaluation(studentId, semesterId = null) {
  return request.get(`/moral/evaluations/student/${studentId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 获取班级德育评价汇总
 */
export function getClassEvaluation(classId, semesterId = null) {
  return request.get(`/moral/evaluations/class/${classId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 获取年级德育评价汇总
 */
export function getGradeEvaluation(gradeId, semesterId = null) {
  return request.get(`/moral/evaluations/grade/${gradeId}`, {
    params: { semester_id: semesterId }
  })
}

/**
 * 计算德育评价
 */
export function calculateEvaluation(params = {}) {
  return request.post('/moral/evaluations/calculate', null, { params })
}

// =============================================================================
// 学生画像 API
// =============================================================================

/**
 * 获取学生画像
 */
export function getStudentProfile(studentId) {
  return request.get(`/moral/profiles/student/${studentId}`)
}

/**
 * 生成学生画像
 */
export function generateStudentProfile(studentId) {
  return request.post(`/moral/profiles/student/${studentId}/generate`)
}

/**
 * 批量生成学生画像
 */
export function batchGenerateProfiles(params = {}) {
  return request.post('/moral/profiles/batch-generate', null, { params })
}

/**
 * 获取画像配置
 */
export function getProfileConfig() {
  return request.get('/moral/profiles/config')
}

// =============================================================================
// 生日提醒 API
// =============================================================================

/**
 * 获取即将到来的生日
 */
export function getUpcomingBirthdays(days = 7, classId = null) {
  return request.get('/moral/birthdays/upcoming', {
    params: { days, class_id: classId }
  })
}

/**
 * 获取今日过生日的学生
 */
export function getTodayBirthdays() {
  return request.get('/moral/birthdays/today')
}

/**
 * 获取生日提醒列表
 */
export function getBirthdayReminders(params = {}) {
  return request.get('/moral/birthdays/reminders', { params })
}

/**
 * 创建生日提醒
 */
export function createBirthdayReminder(data) {
  return request.post('/moral/birthdays/reminders', data)
}

/**
 * 发送生日提醒
 */
export function sendBirthdayReminder(reminderId) {
  return request.post(`/moral/birthdays/reminders/${reminderId}/send`)
}

/**
 * 生成本月生日提醒
 */
export function generateMonthlyReminders() {
  return request.post('/moral/birthdays/generate')
}

/**
 * 获取生日提醒配置
 */
export function getBirthdayConfig() {
  return request.get('/moral/birthdays/config')
}

// =============================================================================
// AI诊疗 API
// =============================================================================

/**
 * 获取诊疗会话列表
 */
export function getConsultations(params = {}) {
  return request.get('/moral/consultations', { params })
}

/**
 * 创建诊疗会话
 */
export function createConsultation(data) {
  return request.post('/moral/consultations', data)
}

/**
 * 获取诊疗会话详情
 */
export function getConsultation(consultationId) {
  return request.get(`/moral/consultations/${consultationId}`)
}

/**
 * 更新诊疗会话
 */
export function updateConsultation(consultationId, data) {
  return request.put(`/moral/consultations/${consultationId}`, data)
}

/**
 * 添加诊疗消息
 */
export function addConsultationMessage(consultationId, data) {
  return request.post(`/moral/consultations/${consultationId}/messages`, data)
}

/**
 * 关闭诊疗会话
 */
export function closeConsultation(consultationId, outcome = null) {
  return request.post(`/moral/consultations/${consultationId}/close`, null, {
    params: { outcome }
  })
}

// =============================================================================
// 系统管理 API
// =============================================================================

/**
 * 获取级号列表
 */
export function getGrades() {
  return request.get('/moral/admin/grades')
}

/**
 * 创建级号
 */
export function createGrade(data) {
  return request.post('/moral/admin/grades', data)
}

/**
 * 删除级号
 */
export function deleteGrade(gradeId) {
  return request.delete(`/moral/admin/grades/${gradeId}`)
}

/**
 * 获取班级列表
 */
export function getClasses(params = {}) {
  return request.get('/moral/admin/classes', { params })
}

/**
 * 创建班级
 */
export function createClass(data) {
  return request.post('/moral/admin/classes', data)
}

/**
 * 更新班级
 */
export function updateClass(classId, data) {
  return request.put(`/moral/admin/classes/${classId}`, data)
}

/**
 * 获取学年列表
 */
export function getSchoolYears() {
  return request.get('/moral/admin/school-years')
}

/**
 * 创建学年
 */
export function createSchoolYear(data) {
  return request.post('/moral/admin/school-years', data)
}

/**
 * 获取学期列表
 */
export function getSemesters(params = {}) {
  return request.get('/moral/admin/semesters', { params })
}

/**
 * 创建学期
 */
export function createSemester(data) {
  return request.post('/moral/admin/semesters', data)
}

/**
 * 设置当前学期
 */
export function setCurrentSemester(semesterId) {
  return request.post(`/moral/admin/semesters/${semesterId}/set-current`)
}

/**
 * 获取学生列表
 */
export function getStudents(params = {}) {
  return request.get('/moral/admin/students', { params })
}

/**
 * 创建学生
 */
export function createStudent(data) {
  return request.post('/moral/admin/students', data)
}

/**
 * 更新学生状态
 */
export function updateStudentStatus(studentId, status) {
  return request.put(`/moral/admin/students/${studentId}/status`, null, {
    params: { status }
  })
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

  // 系统管理
  getGrades,
  createGrade,
  deleteGrade,
  getClasses,
  createClass,
  updateClass,
  getSchoolYears,
  createSchoolYear,
  getSemesters,
  createSemester,
  setCurrentSemester,
  getStudents,
  createStudent,
  updateStudentStatus,
}