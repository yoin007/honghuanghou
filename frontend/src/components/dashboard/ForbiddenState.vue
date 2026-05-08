<template>
  <div class="forbidden-state">
    <div class="forbidden-icon">
      <span>⚠</span>
    </div>
    <h2>{{ title }}</h2>
    <p>{{ message }}</p>
    <div class="action-buttons">
      <el-button v-if="fallbackRoute" type="primary" @click="goTo(fallbackRoute)">
        {{ fallbackLabel || '返回首页' }}
      </el-button>
      <el-button v-if="showWorkbench" type="default" @click="goTo('/dashboard/teacher')">
        教师工作台
      </el-button>
      <el-button v-if="showOverview" type="default" @click="goTo('/dashboard')">
        数据总览
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    default: '无访问权限'
  },
  message: {
    type: String,
    default: '您当前角色无权限查看此驾驶舱，请联系管理员或切换至可访问模块。'
  },
  fallbackRoute: {
    type: String,
    default: ''
  },
  fallbackLabel: {
    type: String,
    default: '返回首页'
  }
})

const router = useRouter()
const authStore = useAuthStore()

const showWorkbench = computed(() => authStore.isLoggedIn && !authStore.isAdmin && !authStore.isJiaowu && !authStore.isXuefa)
const showOverview = computed(() => authStore.isLoggedIn)

const goTo = (route) => {
  if (route) router.push(route)
}
</script>

<style scoped>
.forbidden-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 120px);
  padding: 48px;
  text-align: center;
  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 50% 50%, rgba(239, 68, 68, 0.15), transparent 40%);
}

.forbidden-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
  border: 2px solid rgba(239, 68, 68, 0.4);
  border-radius: 999px;
  background: rgba(239, 68, 68, 0.12);
  font-size: 36px;
  color: #f87171;
}

h2 {
  margin: 0 0 12px;
  color: #f8fafc;
  font-size: 28px;
  font-weight: 700;
}

p {
  max-width: 480px;
  margin: 0 0 32px;
  color: rgba(226, 232, 240, 0.72);
  font-size: 15px;
  line-height: 1.6;
}

.action-buttons {
  display: flex;
  gap: 16px;
}

.action-buttons :deep(.el-button--primary) {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.4);
  color: #f87171;
}

.action-buttons :deep(.el-button--primary:hover) {
  background: rgba(239, 68, 68, 0.3);
  border-color: rgba(239, 68, 68, 0.5);
}

.action-buttons :deep(.el-button--default) {
  background: rgba(15, 23, 42, 0.74);
  border-color: rgba(148, 163, 184, 0.26);
  color: #cbd5e1;
}

.action-buttons :deep(.el-button--default:hover) {
  background: rgba(15, 23, 42, 0.88);
  border-color: rgba(148, 163, 184, 0.36);
}
</style>