import request from '@/utils/api'

export function getDashboardOverview() {
  return request.get('/api/dashboard/overview')
}

export function getMoralDashboardSummary(params = {}) {
  return request.get('/api/dashboard/moral/summary', { params })
}

export function getTeachingDashboardSummary(params = {}) {
  return request.get('/api/dashboard/teaching/summary', { params })
}

export function getClassDashboardSummary(params = {}) {
  return request.get('/api/dashboard/class/summary', { params })
}

export function getTeacherWorkbench() {
  return request.get('/api/dashboard/teacher/workbench')
}

export default {
  getDashboardOverview,
  getMoralDashboardSummary,
  getTeachingDashboardSummary,
  getClassDashboardSummary,
  getTeacherWorkbench
}
