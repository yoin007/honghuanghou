<template>
  <div class="app-container">
    <el-container>
      <el-header class="app-header" height="auto">
        <div class="header-inner">
          <div class="header-top">
            <h1 class="app-title">数字天龙</h1>
            <div class="header-right-actions">
              <el-select
                v-model="classCode"
                placeholder="选择班级"
                @change="handleClassChange"
                class="class-select"
              >
                <el-option
                  v-for="code in classCodes"
                  :key="code"
                  :label="code"
                  :value="code"
                />
              </el-select>
              <div class="auth-actions">
                <template v-if="isLoggedIn">
                  <span class="user-greeting hidden-xs-only">你好, {{ username }}</span>
                  <el-button type="danger" size="small" @click="handleLogout">退出</el-button>
                </template>
                <el-button v-else type="primary" size="small" @click="showLoginDialog = true">登录</el-button>
              </div>
            </div>
          </div>
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
              <el-menu-item index="/current-classes">实时课程</el-menu-item>
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
            
            <el-sub-menu v-if="isAdmin" index="system">
              <template #title>系统管理</template>
              <el-menu-item index="/member-manage">会员管理</el-menu-item>
              <el-menu-item index="/permission-manage">权限管理</el-menu-item>
              <el-menu-item index="/task-manage">任务管理</el-menu-item>
              <el-menu-item index="/system-monitor">系统监控</el-menu-item>
              <el-menu-item index="/teacher-manage">教师管理</el-menu-item>
            </el-sub-menu>
          </el-menu>
        </div>
      </el-header>
      <el-container class="main-container">
        <el-main class="app-main">
          <router-view v-slot="{ Component }">
            <transition name="fade">
              <component :is="Component" :key="route.path" />
            </transition>
          </router-view>
        </el-main>
      </el-container>
    </el-container>

    <!-- 登录对话框 -->
    <el-dialog 
      v-model="showLoginDialog" 
      title="登录" 
      width="400px"
      :close-on-click-modal="false"
      class="login-dialog"
    >
      <el-form :model="loginForm" :rules="loginRules" ref="loginFormRef" label-width="60px">
        <el-form-item prop="username" label="用户">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item prop="password" label="密码">
          <el-input v-model="loginForm.password" type="password" show-password placeholder="请输入密码" @keyup.enter="handleLogin" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showLoginDialog = false">取消</el-button>
        <el-button type="primary" @click="handleLogin" :loading="loginLoading">登录</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { RouterView, useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from './stores/auth'
import { useAppStore } from './stores/app'
import { useApiPermissionStore } from './stores/apiPermission'
import api from './utils/api'

const router = useRouter()
const route = useRoute()

// Use Pinia stores
const authStore = useAuthStore()
const appStore = useAppStore()
const apiPermissionStore = useApiPermissionStore()

// API权限检查方法
const { hasApiPermissionSync, loadMyPermissions, clearCache } = apiPermissionStore

// Local refs for UI
const showLoginDialog = ref(false)
const loginLoading = ref(false)
const loginForm = ref({ username: '', password: '' })
const loginFormRef = ref(null)
const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 德育菜单权限
const canViewDailyRecord = ref(false)
const canViewSchoolEvent = ref(false)
const canViewTask = ref(false)
const canViewPunishment = ref(false)
const canViewCollective = ref(false)
const canViewEvaluation = ref(false)
const canViewMoment = ref(false)
const canViewLifebook = ref(false)
const canViewProfile = ref(false)
const canViewBirthday = ref(false)
const canViewStudentManage = ref(false)
const canViewMoralConfig = ref(false)

// Computed properties from store
const isLoggedIn = computed(() => authStore.isLoggedIn)
const username = computed(() => authStore.username)
const isAdmin = computed(() => authStore.isAdmin)
const isJiaowu = computed(() => authStore.isJiaowu)
const isCleader = computed(() => authStore.isCleader)
const classCode = computed(() => appStore.classCode)
const classCodes = computed(() => appStore.classCodes)

// 德育菜单是否显示（有任一子菜单权限才显示）
const showMoralMenu = computed(() => {
  return canViewDailyRecord.value || canViewSchoolEvent.value || canViewTask.value ||
         canViewPunishment.value || canViewEvaluation.value || canViewMoment.value ||
         canViewLifebook.value || canViewProfile.value || canViewBirthday.value ||
         canViewStudentManage.value || canViewMoralConfig.value || canViewCollective.value
})

// 加载德育菜单权限
const loadMoralMenuPermissions = async () => {
  // 先清除缓存，确保重新加载最新权限
  clearCache()
  await loadMyPermissions()
  canViewDailyRecord.value = hasApiPermissionSync('/api/moral/daily-records')
  canViewSchoolEvent.value = hasApiPermissionSync('/api/moral/school-records')
  canViewTask.value = hasApiPermissionSync('/api/moral/tasks')
  canViewPunishment.value = hasApiPermissionSync('/api/moral/punishments')
  canViewCollective.value = hasApiPermissionSync('/api/moral/collective-events')
  canViewEvaluation.value = hasApiPermissionSync('/api/moral/evaluations/class') || hasApiPermissionSync('/api/moral/evaluation/class')
  canViewMoment.value = hasApiPermissionSync('/api/moral/moment-records')
  canViewLifebook.value = hasApiPermissionSync('/api/moral/timeline')
  canViewProfile.value = hasApiPermissionSync('/api/moral/profiles/student') || hasApiPermissionSync('/api/moral/profile/student')
  canViewBirthday.value = hasApiPermissionSync('/api/moral/birthdays/upcoming')
  canViewStudentManage.value = hasApiPermissionSync('/api/moral/admin/students')
  canViewMoralConfig.value = hasApiPermissionSync('/api/moral/admin/api-permissions')
}

// 监听登录状态变化，登录成功后加载权限
watch(isLoggedIn, async (newVal) => {
  if (newVal) {
    await loadMoralMenuPermissions()
  } else {
    // 退出登录时清空权限
    clearCache()
    canViewDailyRecord.value = false
    canViewSchoolEvent.value = false
    canViewTask.value = false
    canViewPunishment.value = false
    canViewCollective.value = false
    canViewEvaluation.value = false
    canViewMoment.value = false
    canViewLifebook.value = false
    canViewProfile.value = false
    canViewBirthday.value = false
    canViewStudentManage.value = false
    canViewMoralConfig.value = false
  }
}, { immediate: true })

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loginLoading.value = true
      try {
        await authStore.login(loginForm.value.username, loginForm.value.password)
        showLoginDialog.value = false
        loginForm.value = { username: '', password: '' }
        // 登录成功后主动加载权限
        await loadMoralMenuPermissions()
      } catch (error) {
        console.error(error)
        ElMessage.error('登录失败，请检查用户名和密码')
      } finally {
        loginLoading.value = false
      }
    }
  })
}

const handleLogout = () => {
  authStore.logout()
}

// Intercept 401
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      handleLogout()
    }
    return Promise.reject(error)
  }
)

// 计算当前激活的菜单项
const activeIndex = computed(() => route.path)

const handleClassChange = (value) => {
  appStore.handleClassChange(value)
}

const handleSelect = (index) => {
  if (!index || typeof index !== 'string') return
  if (!index.startsWith('/')) return

  const path = index

  if (path === route.path) {
    const timestamp = Date.now().toString()
    router.push({ path, query: { t: timestamp } })
  } else {
    router.push({ path })
  }
}

onMounted(() => {
  appStore.fetchClassCodes()
  appStore.initClassCode()
})
</script>

<style>
/* 全局移动端 table 适配 */
@media screen and (max-width: 768px) {
  * {
    box-sizing: border-box;
  }

  .el-table {
    width: 100% !important;
    max-width: 100vw;
    table-layout: auto !important;
  }

  .el-table__inner-wrapper {
    width: auto !important;
  }
}
</style>
<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background-color: #249ee0;
  color: #303133;
  padding: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: relative;
  z-index: 2;
  flex-shrink: 0;
}

.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1rem;
  display: flex;
  flex-direction: column;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
}

.app-title {
  margin: 0;
  font-size: 1.5rem;
  color: #fff;
  white-space: nowrap;
}

.class-select {
  width: 150px;
}

.header-right-actions {
  display: flex;
  align-items: center;
  gap: 15px;
}

.auth-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-greeting {
  color: #fff;
  font-size: 0.9rem;
}

.top-nav-menu {
  border-bottom: none;
  background-color: transparent;
.top-nav-menu :deep(.el-menu-item),
.top-nav-menu :deep(.el-sub-menu__title) {
  color: #409EFF;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .app-header {
    height: auto !important;
  }
  
  .header-top {
    flex-direction: column;
    height: auto;
    padding: 10px 0;
    align-items: stretch;
  }

  .app-title {
    text-align: center;
    margin-bottom: 10px;
    font-size: 1.2rem;
  }

  .class-select {
    width: 100%;
  }

  .header-right-actions {
    flex-direction: column;
    width: 100%;
    gap: 10px;
  }
  
  .auth-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .hidden-xs-only {
    display: none;
  }

  .top-nav-menu {
    display: flex;
    overflow-x: auto;
    white-space: nowrap;
    width: 100%;
    /* 隐藏滚动条但保留功能 */
    scrollbar-width: none; /* Firefox */
    -ms-overflow-style: none; /* IE and Edge */
  }

  .top-nav-menu::-webkit-scrollbar {
    display: none; /* Chrome, Safari, Opera */
  }
  
  /* 确保菜单项不换行 */
  .top-nav-menu :deep(.el-menu-item),
  .top-nav-menu :deep(.el-sub-menu),
  .top-nav-menu :deep(.el-sub-menu__title) {
    display: inline-flex;
    flex-shrink: 0;
  }
  
  /* 调整主容器内边距 */
  .app-main {
    padding: 10px;
  }
}  font-weight: 500;
}

.top-nav-menu :deep(.el-menu-item.is-active),
.top-nav-menu :deep(.el-sub-menu.is-active .el-sub-menu__title) {
  background-color: rgba(64, 158, 255, 0.1) !important;
  color: #077518;
}

.top-nav-menu :deep(.el-menu-item:hover),
.top-nav-menu :deep(.el-sub-menu__title:hover) {
  color: #085f18;
  background-color: rgba(64, 158, 255, 0.05) !important;
}

.main-container {
  flex: 1;
  min-height: 0;
  display: flex;
}

.app-main {
  flex: 1;
  padding: 5rem 1rem 1rem;
  overflow-y: auto;
  background-color: var(--background-color);
  position: relative;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 响应式布局 */
@media (max-width: 768px) {
  .app-header {
    padding: 0.5rem;
  }

  .header-top {
    flex-direction: column;
    align-items: stretch;
    height: auto;
  }

  .app-title {
    text-align: center;
    margin-bottom: 0.5rem;
  }

  .class-select {
    width: 100%;
  }
}

@media (max-width: 576px) {
  .app-main {
    padding: 0.5rem;
  }
}

/* 移动端 Table 全局适配 */
@media screen and (max-width: 768px) {
  .app-main {
    overflow-x: hidden;
    width: 100%;
  }

  /* Table 横向滚动 - 全局 */
  .el-table {
    width: 100% !important;
    overflow-x: auto !important;
    display: block !important;
  }

  .el-table__inner-wrapper {
    width: 100% !important;
    overflow-x: auto !important;
  }

  .el-table__body-wrapper,
  .el-table__header-wrapper {
    width: 100% !important;
    overflow-x: auto !important;
  }

  .el-table__body,
  .el-table__header {
    width: auto !important;
    min-width: 100%;
  }

  /* 表格列 */
  .el-table .el-table__cell {
    white-space: nowrap;
  }

  /* 显示滚动条 */
  .el-scrollbar__bar.is-horizontal {
    display: block !important;
    opacity: 1 !important;
  }

  /* 隐藏固定列 */
  .el-table__fixed,
  .el-table__fixed-right,
  .el-table__fixed-column-placeholder {
    display: none !important;
  }

  /* 确保表格父容器可以滚动 */
  .el-table__body-container {
    overflow-x: auto;
  }
}

.menu-link {
  text-decoration: none;
  color: inherit;
}

/* 移动端 el-tabs 全局适配 */
@media screen and (max-width: 768px) {
  .el-tabs__header {
    margin-bottom: 10px;
  }

  .el-tabs__nav-wrap {
    overflow-x: auto !important;
    overflow-y: hidden;
  }

  .el-tabs__item {
    font-size: 14px !important;
    padding: 0 12px !important;
    white-space: nowrap;
  }

  .el-tabs__nav {
    white-space: nowrap;
  }
}
</style>
