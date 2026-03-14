import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/schedule',
    name: 'Schedule',
    component: () => import('../views/Schedule.vue')
  },
  {
    path: '/announcement',
    name: 'Announcement',
    component: () => import('../views/Announcement.vue')
  },
  {
    path: '/basic-info',
    name: 'BasicInfo',
    component: () => import('../views/BasicInfo.vue')
  },
  {
    path: '/class-students',
    name: 'ClassStudents',
    component: () => import('../views/ClassStudents.vue'),
    meta: {
      title: '班级学生'
    }
  },
  {
    path: '/teacher-message',
    name: 'TeacherMessage',
    component: () => import('../views/TeacherMessage.vue')
  },
  {
    path: '/homework',
    name: 'Homework',
    component: () => import('../views/Homework.vue')
  },
  {
    path: '/delay-application',
    name: 'DelayApplication',
    component: () => import('../views/DelayApplication.vue'),
    meta: {
      title: '延时申请'
    }
  },
  {
    path: '/leave-record',
    name: 'LeaveRecord',
    component: () => import('../views/LeaveRecord.vue'),
    meta: {
      title: '请假记录'
    }
  },
  {
    path: '/routine-record',
    name: 'RoutineRecord',
    component: () => import('../views/RoutineRecord.vue'),
    meta: {
      title: '常规记录'
    }
  },
  {
    path: '/routine-query',
    name: 'RoutineQuery',
    component: () => import('../views/RoutineQuery.vue'),
    meta: {
      title: '常规查询'
    }
  },
  {
    path: '/random-call',
    name: 'RandomCall',
    component: () => import('../views/RandomCall.vue'),
    meta: {
      title: '随机点名'
    }
  },
  {
    path: '/loud-pk',
    name: 'LoudPK',
    component: () => import('../views/LoudPK.vue'),
    meta: {
      title: '大声PK',
      protocol: 'https'
    }
  },
  {
    path: '/current-classes',
    name: 'CurrentClasses',
    component: () => import('../views/CurrentClasses.vue'),
    meta: {
      title: '实时课程'
    }
  },
  {
    path: '/schedules',
    name: 'Schedules',
    component: () => import('../views/Schedules.vue'),
    meta: {
      title: '课表文件'
    }
  },
  {
    path: '/upload-schedule',
    name: 'UploadSchedule',
    component: () => import('../views/UploadSchedule.vue'),
    meta: {
      title: '更新课表'
    }
  },
  {
    path: '/member-manage',
    name: 'MemberManage',
    component: () => import('../views/MemberManage.vue'),
    meta: {
      title: '会员管理'
    }
  },
  {
    path: '/permission-manage',
    name: 'PermissionManage',
    component: () => import('../views/PermissionManage.vue'),
    meta: {
      title: '权限管理'
    }
  },
  {
    path: '/task-manage',
    name: 'TaskManage',
    component: () => import('../views/TaskManage.vue'),
    meta: {
      title: '任务管理'
    }
  },
  {
    path: '/publish-homework',
    name: 'PublishHomework',
    component: () => import('../views/PublishHomework.vue'),
    meta: {
      title: '发布作业'
    }
  },
  {
    path: '/publish-announcement',
    name: 'PublishAnnouncement',
    component: () => import('../views/PublishAnnouncement.vue'),
    meta: {
      title: '发布公告'
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
  const isHttps = window.location.protocol === 'https:'
  const matched = Array.isArray(to.matched) ? to.matched : []
  const matchedProtocol =
    matched.length > 0 ? matched[matched.length - 1]?.meta?.protocol : undefined
  const isLoudPk = to.name === 'LoudPK' || to.path === '/loud-pk' || to.path === '/loud-pk/'
  const protocol = matchedProtocol || (isLoudPk ? 'https' : 'http')
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

router.beforeEach((to) => {
  const redirectUrl = ensureProtocol(to)
  if (redirectUrl) {
    window.location.replace(redirectUrl)
    return false
  }
  return true
})

export default router
