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

export function getTeacherWorkbench(params = {}) {
  return request.get('/api/dashboard/teacher/workbench', { params })
}

export function getInvigilationDashboardSummary(params = {}) {
  return request.get('/api/dashboard/invigilation/summary', { params })
}

export function getSystemDashboardSummary() {
  return request.get('/api/dashboard/system/summary')
}

export default {
  getDashboardOverview,
  getMoralDashboardSummary,
  getTeachingDashboardSummary,
  getClassDashboardSummary,
  getTeacherWorkbench,
  getInvigilationDashboardSummary,
  getSystemDashboardSummary
}
