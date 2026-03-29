import { createRouter, createWebHistory } from 'vue-router'

// 公开页面，不需要登录
const publicRoutes = ['/', '/zhf']

const routes = [
  {
    path: '/schedule',
    name: 'Schedule',
    component: () => import('../views/Schedule.vue'),
    meta: { requiresAuth: true, title: '课程表' }
  },
  {
    path: '/announcement',
    name: 'Announcement',
    component: () => import('../views/Announcement.vue'),
    meta: { requiresAuth: true, title: '公告' }
  },
  {
    path: '/basic-info',
    name: 'BasicInfo',
    component: () => import('../views/BasicInfo.vue'),
    meta: { requiresAuth: true, title: '基本信息' }
  },
  {
    path: '/class-students',
    name: 'ClassStudents',
    component: () => import('../views/ClassStudents.vue'),
    meta: {
      requiresAuth: true,
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
    meta: { requiresAuth: true, title: '作业' }
  },
  {
    path: '/delay-application',
    name: 'DelayApplication',
    component: () => import('../views/DelayApplication.vue'),
    meta: {
      requiresAuth: true,
      title: '延时申请'
    }
  },
  {
    path: '/leave-record',
    name: 'LeaveRecord',
    component: () => import('../views/LeaveRecord.vue'),
    meta: {
      requiresAuth: true,
      title: '请假记录'
    }
  },
  {
    path: '/routine-record',
    name: 'RoutineRecord',
    component: () => import('../views/RoutineRecord.vue'),
    meta: {
      requiresAuth: true,
      title: '常规记录'
    }
  },
  {
    path: '/routine-query',
    name: 'RoutineQuery',
    component: () => import('../views/RoutineQuery.vue'),
    meta: {
      requiresAuth: true,
      title: '常规查询'
    }
  },
  {
    path: '/random-call',
    name: 'RandomCall',
    component: () => import('../views/RandomCall.vue'),
    meta: {
      requiresAuth: true,
      title: '随机点名'
    }
  },
  {
    path: '/loud-pk',
    name: 'LoudPK',
    component: () => import('../views/LoudPK.vue'),
    meta: {
      requiresAuth: true,
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
      requiresAuth: true,
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
    path: '/',
    redirect: '/schedules'
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
    // 跳转到首页（登录页面），但先让首页加载
    return true
  }

  // 已登录但访问公开页面，重定向到首页
  if (token && isPublicPath(to.path)) {
    return { path: '/schedules' }
  }

  return true
})

export default router
