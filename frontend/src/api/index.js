/**
 * API 模块化导出 - 聚合入口
 *
 * 不再创建 axios 实例，统一使用 httpClient
 */

// 导出 httpClient
export { httpClient, default as api } from '@/shared/api/httpClient'
export { default } from '@/shared/api/httpClient'

// 导出各模块 API
export { authApi } from './modules/auth'
export { userApi } from './modules/user'
export { homeworkApi } from './modules/homework'
export { scheduleApi } from './modules/schedule'
export { filegatherApi } from './modules/filegather'
export { teacherApi } from './modules/teacher'
export { invigilationApi } from './modules/invigilation'
export { taskApi } from './modules/task'
export { permissionApi } from './modules/permission'
export { leaveApi } from './modules/leave'
export { delayApi } from './modules/delay'
export { memberApi } from './modules/member'
export { systemApi } from './modules/system'
export { announcementApi } from './modules/announcement'
export { loudpkApi } from './modules/loudpk'
export { messageApi } from './modules/message'
export { dashboardApi } from './modules/dashboard'
