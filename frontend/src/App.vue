<template>
  <AppLayout
    :is-logged-in="isLoggedIn"
    :username="username"
    @logout="handleLogout"
    @login-click="showLoginDialog = true"
  >
    <template #class-selector>
      <ClassSelector
        :class-code="classCode"
        :class-codes="classCodes"
        @change="handleClassChange"
      />
    </template>

    <template #navigation>
      <TopNavigation
        :active-index="activeIndex"
        @select="handleSelect"
      />
    </template>

    <template #main>
      <router-view v-slot="{ Component }">
        <transition name="fade">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </template>
  </AppLayout>

  <!-- 登录对话框 -->
  <LoginDialog
    v-model="showLoginDialog"
    @login-success="handleLoginSuccess"
  />
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { isPublicPath } from '@/router'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { useApiPermissionStore } from '@/stores/apiPermission'
import { useResourcePermissionStore } from '@/stores/resourcePermission'
import AppLayout from '@/components/layout/AppLayout.vue'
import ClassSelector from '@/components/layout/ClassSelector.vue'
import TopNavigation from '@/components/layout/TopNavigation.vue'
import LoginDialog from '@/components/layout/LoginDialog.vue'

const router = useRouter()
const route = useRoute()

// Stores
const authStore = useAuthStore()
const appStore = useAppStore()
const apiPermissionStore = useApiPermissionStore()
const resourcePermissionStore = useResourcePermissionStore()

// Local UI state
const showLoginDialog = ref(false)

// Computed from stores
const isLoggedIn = computed(() => authStore.isLoggedIn)
const username = computed(() => authStore.username)
const classCode = computed(() => appStore.classCode)
const classCodes = computed(() => appStore.classCodes)
const activeIndex = computed(() => route.path)

// Watch login state to load/clear API permissions cache
watch(isLoggedIn, async (newVal) => {
  if (newVal) {
    await apiPermissionStore.loadMyPermissions()
  } else {
    apiPermissionStore.clearCache()
  }
}, { immediate: true })

// Handlers
const handleClassChange = (value) => {
  appStore.handleClassChange(value)
}

// 目标路由缓存（登录后跳转）
const pendingRoute = ref(null)

// 公开路由判定统一走 isPublicPath（内部读 store.publicRoutes，
// 后端 menu_permission_config 表 is_public=1 决定；meta.requiresAuth 兜底）

const handleSelect = (index) => {
  if (!index || typeof index !== 'string') return
  if (!index.startsWith('/')) return

  // 公开路由直接跳转，不需要登录
  if (isPublicPath(index)) {
    if (index === route.path) {
      const timestamp = Date.now().toString()
      router.push({ path: index, query: { t: timestamp } })
    } else {
      router.push({ path: index })
    }
    return
  }

  // 需要登录的路由：未登录时弹出登录对话框
  if (!isLoggedIn.value) {
    pendingRoute.value = index
    showLoginDialog.value = true
    return
  }

  if (index === route.path) {
    const timestamp = Date.now().toString()
    router.push({ path: index, query: { t: timestamp } })
  } else {
    router.push({ path: index })
  }
}

const handleLogout = () => {
  authStore.logout()
}

const handleLoginSuccess = async () => {
  await apiPermissionStore.loadMyPermissions()
  // 登录成功后跳转到之前缓存的路由
  if (pendingRoute.value) {
    router.push({ path: pendingRoute.value })
    pendingRoute.value = null
  }
}

onMounted(() => {
  appStore.fetchClassCodes()
  appStore.initClassCode()
  // 加载动态菜单配置
  resourcePermissionStore.loadMenuConfigFromBackend()
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

/* 移动端 Table 全局适配 */
@media screen and (max-width: 768px) {
  .el-main {
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

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
