/**
 * 驾驶舱 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const dashboardApi = {
  getOverview() {
    return httpClient.get('/api/dashboard/overview')
  },

  getMoralSummary(params = {}) {
    return httpClient.get('/api/dashboard/moral/summary', { params })
  },

  getTeachingSummary(params = {}) {
    return httpClient.get('/api/dashboard/teaching/summary', { params })
  },

  getClassSummary(params = {}) {
    return httpClient.get('/api/dashboard/class/summary', { params })
  },

  getTeacherWorkbench(params = {}) {
    return httpClient.get('/api/dashboard/teacher/workbench', { params })
  },

  getInvigilationSummary(params = {}) {
    return httpClient.get('/api/dashboard/invigilation/summary', { params })
  },

  getSystemSummary() {
    return httpClient.get('/api/dashboard/system/summary')
  },

  getGradeList() {
    return httpClient.get('/api/dashboard/grade/list')
  },

  getGradeSummary(params = {}) {
    return httpClient.get('/api/dashboard/grade/summary', { params })
  }
}

// 兼容旧命名导出
export const getDashboardOverview = dashboardApi.getOverview
export const getMoralDashboardSummary = dashboardApi.getMoralSummary
export const getTeachingDashboardSummary = dashboardApi.getTeachingSummary
export const getClassDashboardSummary = dashboardApi.getClassSummary
export const getTeacherWorkbench = dashboardApi.getTeacherWorkbench
export const getInvigilationDashboardSummary = dashboardApi.getInvigilationSummary
export const getSystemDashboardSummary = dashboardApi.getSystemSummary
export const fetchGradeList = dashboardApi.getGradeList
export const fetchGradeDashboardSummary = dashboardApi.getGradeSummary

export default dashboardApi
