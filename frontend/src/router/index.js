import { createRouter, createWebHistory } from 'vue-router'
import { canAccessDashboardRoute, getDefaultDashboardByRole } from './guards'

// 公开页面，不需要登录
const publicRoutes = ['/', '/zhf', '/homework', '/basic-info', '/class-students', '/announcement', '/delay-application', '/leave-record', '/schedule', '/schedules', '/random-call', '/loud-pk']

const routes = [
  {
    path: '/dashboard',
    name: 'DashboardOverview',
    component: () => import('../views/dashboard/Overview.vue'),
    meta: { requiresAuth: true, title: '数据驾驶舱' }
  },
  {
    path: '/dashboard/forbidden',
    name: 'DashboardForbidden',
    component: () => import('../components/dashboard/ForbiddenState.vue'),
    meta: { requiresAuth: true, title: '无权限' }
  },
  {
    path: '/dashboard/moral',
    name: 'MoralDashboard',
    component: () => import('../views/dashboard/MoralDashboard.vue'),
    meta: { requiresAuth: true, title: '德育驾驶舱', dashboardRoles: ['admin', 'jiaowu', 'xuefa', 'cleader'] }
  },
  {
    path: '/dashboard/teaching',
    name: 'TeachingDashboard',
    component: () => import('../views/dashboard/TeachingDashboard.vue'),
    meta: { requiresAuth: true, title: '教务驾驶舱', dashboardRoles: ['admin', 'jiaowu'] }
  },
  {
    path: '/dashboard/class',
    name: 'ClassDashboard',
    component: () => import('../views/dashboard/ClassDashboard.vue'),
    meta: { requiresAuth: true, title: '班级驾驶舱', dashboardRoles: ['admin', 'jiaowu', 'xuefa', 'cleader', 'g_leader'] }
  },
  {
    path: '/dashboard/grade',
    name: 'GradeDashboard',
    component: () => import('../views/dashboard/GradeDashboard.vue'),
    meta: { requiresAuth: true, title: '年级驾驶舱', dashboardRoles: ['admin', 'jiaowu', 'xuefa', 'g_leader'] }
  },
  {
    path: '/dashboard/teacher',
    name: 'TeacherWorkbench',
    component: () => import('../views/dashboard/TeacherWorkbench.vue'),
    meta: { requiresAuth: true, title: '教师工作台' }
  },
  {
    path: '/dashboard/invigilation',
    name: 'InvigilationDashboard',
    component: () => import('../views/dashboard/InvigilationDashboard.vue'),
    meta: { requiresAuth: true, title: '监考驾驶舱', dashboardRoles: ['admin', 'jiaowu'] }
  },
  {
    path: '/dashboard/system',
    name: 'SystemDashboard',
    component: () => import('../views/dashboard/SystemDashboard.vue'),
    meta: { requiresAuth: true, title: '系统运维驾驶舱', dashboardRoles: ['admin'] }
  },
  {
    path: '/schedule',
    name: 'Schedule',
    component: () => import('../views/Schedule.vue'),
    meta: { requiresAuth: false, title: '课程表' }
  },
  {
    path: '/announcement',
    name: 'Announcement',
    component: () => import('../views/Announcement.vue'),
    meta: { requiresAuth: false, title: '公告' }
  },
  {
    path: '/basic-info',
    name: 'BasicInfo',
    component: () => import('../views/BasicInfo.vue'),
    meta: { requiresAuth: false, title: '基本信息' }
  },
  {
    path: '/class-students',
    name: 'ClassStudents',
    component: () => import('../views/ClassStudents.vue'),
    meta: {
      requiresAuth: false,
      title: '班级学生'
    }
  },
  {
    path: '/teacher-message',
    name: 'TeacherMessage',
    component: () => import('../views/TeacherMessage.vue'),
    meta: { requiresAuth: true, title: '教师消息' }
  },
  {
    path: '/homework',
    name: 'Homework',
    component: () => import('../views/Homework.vue'),
    meta: { requiresAuth: false, title: '作业' }
  },
  {
    path: '/delay-application',
    name: 'DelayApplication',
    component: () => import('../views/DelayApplication.vue'),
    meta: {
      requiresAuth: false,
      title: '延时申请'
    }
  },
  {
    path: '/leave-record',
    name: 'LeaveRecord',
    component: () => import('../views/LeaveRecord.vue'),
    meta: {
      requiresAuth: false,
      title: '请假记录'
    }
  },
  {
    path: '/random-call',
    name: 'RandomCall',
    component: () => import('../views/RandomCall.vue'),
    meta: {
      requiresAuth: false,
      title: '随机点名'
    }
  },
  {
    path: '/loud-pk',
    name: 'LoudPK',
    component: () => import('../views/LoudPK.vue'),
    meta: {
      requiresAuth: false,
      title: '大声PK',
      protocol: 'https'
    }
  },
  {
    path: '/current-classes',
    name: 'CurrentClasses',
    component: () => import('../views/CurrentClasses.vue'),
    meta: {
      requiresAuth: true,
      title: '实时课程'
    }
  },
  {
    path: '/schedules',
    name: 'Schedules',
    component: () => import('../views/Schedules.vue'),
    meta: {
      requiresAuth: false,
      title: '课表文件'
    }
  },
  {
    path: '/upload-schedule',
    name: 'UploadSchedule',
    component: () => import('../views/UploadSchedule.vue'),
    meta: {
      requiresAuth: true,
      title: '更新课表'
    }
  },
  {
    path: '/member-manage',
    name: 'MemberManage',
    component: () => import('../views/MemberManage.vue'),
    meta: {
      requiresAuth: true,
      title: '会员管理'
    }
  },
  {
    path: '/permission-manage',
    name: 'PermissionManage',
    component: () => import('../views/PermissionManage.vue'),
    meta: {
      requiresAuth: true,
      title: '权限管理'
    }
  },
  {
    path: '/task-manage',
    name: 'TaskManage',
    component: () => import('../views/TaskManage.vue'),
    meta: {
      requiresAuth: true,
      title: '任务管理'
    }
  },
  {
    path: '/publish-homework',
    name: 'PublishHomework',
    component: () => import('../views/PublishHomework.vue'),
    meta: {
      requiresAuth: true,
      title: '发布作业'
    }
  },
  {
    path: '/publish-announcement',
    name: 'PublishAnnouncement',
    component: () => import('../views/PublishAnnouncement.vue'),
    meta: {
      requiresAuth: true,
      title: '发布公告'
    }
  },
  {
    path: '/system-monitor',
    name: 'SystemMonitor',
    component: () => import('../views/SystemMonitor.vue'),
    meta: {
      requiresAuth: true,
      title: '系统监控'
    }
  },
  {
    path: '/teacher-manage',
    name: 'TeacherManage',
    component: () => import('../views/TeacherManage.vue'),
    meta: {
      requiresAuth: true,
      title: '教师管理'
    }
  },
  {
    path: '/file-upload',
    name: 'FileUpload',
    component: () => import('../views/FileUpload.vue'),
    meta: {
      requiresAuth: true,
      title: '文件上传'
    }
  },
  {
    path: '/my-files',
    name: 'MyFiles',
    component: () => import('../views/MyFiles.vue'),
    meta: {
      requiresAuth: true,
      title: '我的文件'
    }
  },
  {
    path: '/admin-files',
    name: 'AdminFiles',
    component: () => import('../views/AdminFiles.vue'),
    meta: {
      requiresAuth: true,
      title: '文件管理',
      requiresJiaowu: true
    }
  },
  {
    path: '/admin-files-done',
    name: 'AdminFilesDone',
    component: () => import('../views/AdminFilesDone.vue'),
    meta: {
      requiresAuth: true,
      title: '已查阅文件',
      requiresJiaowu: true
    }
  },
  {
    path: '/invigilation',
    name: 'InvigilationArrange',
    component: () => import('../views/InvigilationArrange.vue'),
    meta: {
      requiresAuth: true,
      title: '监考安排',
      requiresJiaowu: true
    }
  },
  // 德育评价系统路由
  {
    path: '/moral/daily-record',
    name: 'MoralDailyRecord',
    component: () => import('../views/moral/DailyRecord.vue'),
    meta: {
      requiresAuth: true,
      title: '日常表现记录'
    }
  },
  {
    path: '/moral/school-event',
    name: 'MoralSchoolEvent',
    component: () => import('../views/moral/SchoolEvent.vue'),
    meta: {
      requiresAuth: true,
      title: '校级事件'
    }
  },
  {
    path: '/moral/task',
    name: 'MoralTask',
    component: () => import('../views/moral/TaskManage.vue'),
    meta: {
      requiresAuth: true,
      title: '德育任务'
    }
  },
  {
    path: '/moral/punishment',
    name: 'MoralPunishment',
    component: () => import('../views/moral/Punishment.vue'),
    meta: {
      requiresAuth: true,
      title: '处分管理'
    }
  },
  {
    path: '/moral/evaluation',
    name: 'MoralEvaluation',
    component: () => import('../views/moral/Evaluation.vue'),
    meta: {
      requiresAuth: true,
      title: '德育评价'
    }
  },
  {
    path: '/moral/profile',
    name: 'MoralProfile',
    component: () => import('../views/moral/StudentProfile.vue'),
    meta: {
      requiresAuth: true,
      title: '学生画像'
    }
  },
  {
    path: '/moral/birthday',
    name: 'MoralBirthday',
    component: () => import('../views/moral/Birthday.vue'),
    meta: {
      requiresAuth: true,
      title: '生日提醒'
    }
  },
  {
    path: '/moral/collective',
    name: 'MoralCollective',
    component: () => import('../views/moral/Collective.vue'),
    meta: {
      requiresAuth: true,
      title: '集体事件'
    }
  },
  {
    path: '/moral/consultation',
    name: 'MoralConsultation',
    component: () => import('../views/moral/Consultation.vue'),
    meta: {
      requiresAuth: true,
      title: 'AI诊疗'
    }
  },
  {
    path: '/moral/moment',
    name: 'MoralMoment',
    component: () => import('../views/moral/MomentRecord.vue'),
    meta: {
      requiresAuth: true,
      title: '点滴记录'
    }
  },
  {
    path: '/moral/lifebook',
    name: 'MoralLifeBook',
    component: () => import('../views/moral/LifeBook.vue'),
    meta: {
      requiresAuth: true,
      title: '一生一册'
    }
  },
  // 德育配置管理路由
  {
    path: '/moral/config',
    name: 'MoralConfig',
    component: () => import('../views/moral/config/Index.vue'),
    meta: {
      requiresAuth: true,
      title: '德育配置'
    }
  },
  {
    path: '/moral/config/grade',
    name: 'MoralConfigGrade',
    component: () => import('../views/moral/config/GradeManage.vue'),
    meta: {
      requiresAuth: true,
      title: '级号管理'
    }
  },
  {
    path: '/moral/config/class',
    name: 'MoralConfigClass',
    component: () => import('../views/moral/config/ClassManage.vue'),
    meta: {
      requiresAuth: true,
      title: '班级管理'
    }
  },
  {
    path: '/moral/config/student',
    name: 'MoralConfigStudent',
    component: () => import('../views/moral/config/StudentManage.vue'),
    meta: {
      requiresAuth: true,
      title: '学生管理'
    }
  },
  {
    path: '/moral/config/semester',
    name: 'MoralConfigSemester',
    component: () => import('../views/moral/config/SemesterManage.vue'),
    meta: {
      requiresAuth: true,
      title: '学年学期管理'
    }
  },
  {
    path: '/moral/config/event-type',
    name: 'MoralConfigEventType',
    component: () => import('../views/moral/config/EventTypeManage.vue'),
    meta: {
      requiresAuth: true,
      title: '事件类型管理'
    }
  },
  {
    path: '/moral/config/escalation',
    name: 'MoralConfigEscalation',
    component: () => import('../views/moral/EscalationRuleManage.vue'),
    meta: {
      requiresAuth: true,
      title: '累进规则管理'
    }
  },
  {
    path: '/moral/config/settings',
    name: 'MoralConfigSettings',
    component: () => import('../views/moral/config/Settings.vue'),
    meta: {
      requiresAuth: true,
      title: '系统配置'
    }
  },
  {
    path: '/moral/config/api-permission',
    name: 'MoralConfigApiPermission',
    component: () => import('../views/moral/config/ApiPermission.vue'),
    meta: {
      requiresAuth: true,
      title: 'API权限管理'
    }
  },
  {
    path: '/moral/config/operation-log',
    name: 'MoralConfigOperationLog',
    component: () => import('../views/moral/config/OperationLog.vue'),
    meta: {
      requiresAuth: true,
      title: '操作日志'
    }
  },
  {
    path: '/moral/config/database',
    name: 'MoralConfigDatabase',
    component: () => import('../views/moral/config/DatabaseManage.vue'),
    meta: {
      requiresAuth: true,
      title: '数据库管理',
      requiresAdmin: true
    }
  },
  {
    path: '/moral/config/menu-permission',
    name: 'MoralConfigMenuPermission',
    component: () => import('../views/moral/config/MenuPermission.vue'),
    meta: {
      requiresAuth: true,
      title: '菜单权限配置',
      requiresAdmin: true
    }
  },
  {
    path: '/moral/config/ai-model',
    name: 'MoralConfigAiModel',
    component: () => import('../views/moral/config/AiModelConfig.vue'),
    meta: {
      requiresAuth: true,
      title: '大模型配置',
      requiresAdmin: true
    }
  },
  {
    path: '/',
    name: 'Root',
    component: () => import('../views/Root.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/zhf',
    redirect: () => {
      window.location.href = '/src/assets/zhf.html';
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const ensureProtocol = (to) => {
  if (typeof window === 'undefined') return null
  const isDev = import.meta.env.DEV
  const devHttpPort = isDev ? import.meta.env.VITE_DEV_HTTP_PORT : ''
  const devHttpsPort = isDev ? import.meta.env.VITE_DEV_HTTPS_PORT : ''
  const devUseHttps = isDev && import.meta.env.VITE_DEV_HTTPS === 'true'
  const isHttps = window.location.protocol === 'https:'
  const matched = Array.isArray(to.matched) ? to.matched : []
  const matchedProtocol =
    matched.length > 0 ? matched[matched.length - 1]?.meta?.protocol : undefined
  const isLoudPk = to.name === 'LoudPK' || to.path === '/loud-pk' || to.path === '/loud-pk/'
  // 开发环境 HTTPS 模式下默认使用 HTTPS
  const defaultProtocol = devUseHttps ? 'https' : 'http'
  const protocol = matchedProtocol || (isLoudPk ? 'https' : defaultProtocol)
  const shouldUseHttps = protocol === 'https'
  if (shouldUseHttps === isHttps) return null
  const targetProtocol = shouldUseHttps ? 'https:' : 'http:'
  const url = new URL(window.location.href)
  url.protocol = targetProtocol
  if (shouldUseHttps && devHttpsPort) {
    url.port = devHttpsPort
  }
  if (!shouldUseHttps && devHttpPort) {
    url.port = devHttpPort
  }
  url.pathname = to.fullPath.split('?')[0].split('#')[0] || to.path
  url.search = to.fullPath.includes('?') ? `?${to.fullPath.split('?')[1].split('#')[0]}` : ''
  url.hash = to.fullPath.includes('#') ? `#${to.fullPath.split('#')[1]}` : ''
  return url.toString()
}

// 检查是否需要登录
const isPublicPath = (path) => {
  return publicRoutes.includes(path)
}

router.beforeEach((to) => {
  // 协议检查
  const redirectUrl = ensureProtocol(to)
  if (redirectUrl) {
    window.location.replace(redirectUrl)
    return false
  }

  // 登录检查
  const token = localStorage.getItem('token')
  const requiresAuth = to.meta.requiresAuth !== false

  // 需要登录但未登录
  if (requiresAuth && !token) {
    // 清除过期的 token
    localStorage.removeItem('token')
    // 未登录停留在公开页面（App.vue会显示登录对话框），不重定向避免循环
    if (isPublicPath(to.path)) {
      return true
    }
    // 未登录直达受保护页面时回到公开入口
    return { path: '/' }
  }

  if (token && !canAccessDashboardRoute(to.meta, token)) {
    return { path: '/dashboard/forbidden' }
  }

  // 已登录访问根路径 '/' 时，重定向到角色默认驾驶舱
  // 其他公开路由（班级、课表、趣味）无论是否登录都可访问
  if (token && to.path === '/') {
    return { path: getDefaultDashboardByRole(token) }
  }

  return true
})

export default router
