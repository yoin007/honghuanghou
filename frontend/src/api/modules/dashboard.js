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

export default {
  getDashboardOverview,
  getMoralDashboardSummary,
  getTeachingDashboardSummary
}
