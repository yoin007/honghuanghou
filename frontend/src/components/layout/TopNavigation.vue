<template>
  <el-menu
    :default-active="activeIndex"
    mode="horizontal"
    class="top-nav-menu"
    @select="handleSelect"
  >
    <el-sub-menu index="class">
      <template #title>班级</template>
      <el-menu-item index="/homework">班级作业</el-menu-item>
      <el-menu-item index="/basic-info">班级信息</el-menu-item>
      <el-menu-item index="/class-students">班级学生</el-menu-item>
      <el-menu-item index="/announcement">班级公告</el-menu-item>
      <el-menu-item index="/delay-application">延时申请</el-menu-item>
      <el-menu-item index="/leave-record">请假记录</el-menu-item>
    </el-sub-menu>

    <el-sub-menu index="schedule">
      <template #title>课表</template>
      <el-menu-item index="/schedule">课程表</el-menu-item>
      <el-menu-item index="/schedules">总课表</el-menu-item>
    </el-sub-menu>

    <el-sub-menu index="fun">
      <template #title>趣味</template>
      <el-menu-item index="/random-call">随机点名</el-menu-item>
      <el-menu-item index="/loud-pk">大声PK</el-menu-item>
    </el-sub-menu>

    <el-sub-menu v-if="isLoggedIn" index="teacher">
      <template #title>教师</template>
      <el-menu-item index="/publish-homework">发布作业</el-menu-item>
      <el-menu-item index="/publish-announcement">发布公告</el-menu-item>
      <el-menu-item index="/file-upload">文件上传</el-menu-item>
      <el-menu-item index="/my-files">我的文件</el-menu-item>
    </el-sub-menu>

    <el-sub-menu v-if="isJiaowu" index="jiaowu">
      <template #title>教务</template>
      <el-menu-item index="/admin-files">文件管理</el-menu-item>
      <el-menu-item index="/admin-files-done">已查阅文件</el-menu-item>
      <el-menu-item index="/upload-schedule">更新课表</el-menu-item>
      <el-menu-item index="/invigilation">监考安排</el-menu-item>
    </el-sub-menu>

    <el-sub-menu v-if="isLoggedIn && showMoralMenu" index="moral">
      <template #title>德育评价</template>
      <el-menu-item v-if="canViewDailyRecord" index="/moral/daily-record">日常表现</el-menu-item>
      <el-menu-item v-if="canViewSchoolEvent" index="/moral/school-event">校级事件</el-menu-item>
      <el-menu-item v-if="canViewTask" index="/moral/task">德育任务</el-menu-item>
      <el-menu-item v-if="canViewPunishment" index="/moral/punishment">处分管理</el-menu-item>
      <el-menu-item v-if="canViewCollective" index="/moral/collective">集体事件</el-menu-item>
      <el-menu-item v-if="canViewEvaluation" index="/moral/evaluation">评价查询</el-menu-item>
      <el-menu-item v-if="canViewMoment" index="/moral/moment">点滴记录</el-menu-item>
      <el-menu-item v-if="canViewLifebook" index="/moral/lifebook">一生一册</el-menu-item>
      <el-menu-item v-if="canViewProfile" index="/moral/profile">学生画像</el-menu-item>
      <el-menu-item v-if="canViewBirthday" index="/moral/birthday">生日提醒</el-menu-item>
      <el-menu-item v-if="canViewStudentManage" index="/moral/config/student">学生管理</el-menu-item>
      <el-menu-item v-if="canViewMoralConfig" index="/moral/config">德育配置</el-menu-item>
    </el-sub-menu>

    <el-sub-menu v-if="isLoggedIn" index="dashboard">
      <template #title>驾驶舱</template>
      <el-menu-item index="/dashboard">总览</el-menu-item>
      <el-menu-item v-if="canViewMoralDashboard" index="/dashboard/moral">德育驾驶舱</el-menu-item>
      <el-menu-item v-if="isJiaowu" index="/dashboard/teaching">教务驾驶舱</el-menu-item>
      <el-menu-item v-if="canViewClassDashboard" index="/dashboard/class">班级驾驶舱</el-menu-item>
      <el-menu-item index="/dashboard/teacher">教师工作台</el-menu-item>
      <el-menu-item v-if="canViewInvigilationDashboard" index="/dashboard/invigilation">监考驾驶舱</el-menu-item>
      <el-menu-item v-if="canViewSystemDashboard" index="/dashboard/system">系统运维</el-menu-item>
    </el-sub-menu>

    <el-sub-menu v-if="isAdmin" index="system">
      <template #title>系统管理</template>
      <el-menu-item index="/member-manage">会员管理</el-menu-item>
      <el-menu-item index="/permission-manage">权限管理</el-menu-item>
      <el-menu-item index="/task-manage">任务管理</el-menu-item>
      <el-menu-item index="/system-monitor">系统监控</el-menu-item>
      <el-menu-item index="/teacher-manage">教师管理</el-menu-item>
    </el-sub-menu>
  </el-menu>
</template>

<script setup>
defineProps({
  activeIndex: {
    type: String,
    default: '/'
  },
  isLoggedIn: {
    type: Boolean,
    default: false
  },
  isAdmin: {
    type: Boolean,
    default: false
  },
  isJiaowu: {
    type: Boolean,
    default: false
  },
  showMoralMenu: {
    type: Boolean,
    default: false
  },
  // 德育菜单权限
  canViewDailyRecord: {
    type: Boolean,
    default: false
  },
  canViewSchoolEvent: {
    type: Boolean,
    default: false
  },
  canViewTask: {
    type: Boolean,
    default: false
  },
  canViewPunishment: {
    type: Boolean,
    default: false
  },
  canViewCollective: {
    type: Boolean,
    default: false
  },
  canViewEvaluation: {
    type: Boolean,
    default: false
  },
  canViewMoment: {
    type: Boolean,
    default: false
  },
  canViewLifebook: {
    type: Boolean,
    default: false
  },
  canViewProfile: {
    type: Boolean,
    default: false
  },
  canViewBirthday: {
    type: Boolean,
    default: false
  },
  canViewStudentManage: {
    type: Boolean,
    default: false
  },
  canViewMoralConfig: {
    type: Boolean,
    default: false
  },
  // 驾驶舱权限
  canViewClassDashboard: {
    type: Boolean,
    default: false
  },
  canViewMoralDashboard: {
    type: Boolean,
    default: false
  },
  canViewInvigilationDashboard: {
    type: Boolean,
    default: false
  },
  canViewSystemDashboard: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select'])

const handleSelect = (index) => {
  emit('select', index)
}
</script>

<style scoped>
.top-nav-menu {
  border-bottom: none;
  background-color: transparent;
}

.top-nav-menu :deep(.el-menu-item),
.top-nav-menu :deep(.el-sub-menu__title) {
  color: #fff;
  font-weight: 500;
}

.top-nav-menu :deep(.el-menu-item.is-active),
.top-nav-menu :deep(.el-sub-menu.is-active .el-sub-menu__title) {
  background-color: rgba(255, 255, 255, 0.15) !important;
  color: #fff;
}

.top-nav-menu :deep(.el-menu-item:hover),
.top-nav-menu :deep(.el-sub-menu__title:hover) {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.1) !important;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .top-nav-menu {
    display: flex;
    overflow-x: auto;
    white-space: nowrap;
    width: 100%;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .top-nav-menu::-webkit-scrollbar {
    display: none;
  }

  .top-nav-menu :deep(.el-menu-item),
  .top-nav-menu :deep(.el-sub-menu),
  .top-nav-menu :deep(.el-sub-menu__title) {
    display: inline-flex;
    flex-shrink: 0;
  }
}
</style>
