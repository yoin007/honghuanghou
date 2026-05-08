<template>
  <div class="error-state">
    <div class="error-icon">
      <span>{{ icon }}</span>
    </div>
    <h2>{{ title }}</h2>
    <p>{{ message }}</p>
    <div class="action-buttons">
      <el-button type="primary" @click="retry" v-if="showRetryButton" :disabled="retryDisabled">
        {{ retryDisabled ? '重试中...' : '重试' }}
      </el-button>
      <el-button type="default" @click="goTo('/')" v-if="showHomeButton">
        返回首页
      </el-button>
      <el-button type="default" @click="goTo('/dashboard/teacher')" v-if="showWorkbench">
        教师工作台
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'error' // 'error' | 'unauthorized' | 'loading'
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  },
  showRetry: {
    type: Boolean,
    default: false
  },
  showHome: {
    type: Boolean,
    default: true
  },
  showWorkbench: {
    type: Boolean,
    default: false
  }
})

const router = useRouter()

const icon = computed(() => {
  switch (props.type) {
    case 'unauthorized': return '🔒'
    case 'loading': return '⏳'
    default: return '⚠'
  }
})

const title = computed(() => {
  if (props.title) return props.title
  switch (props.type) {
    case 'unauthorized': return '未登录或登录已过期'
    case 'loading': return '正在加载...'
    default: return '数据加载异常'
  }
})

const message = computed(() => {
  if (props.message) return props.message
  switch (props.type) {
    case 'unauthorized': return '请重新登录后再访问此页面。'
    case 'loading': return '数据正在加载中，请稍候。'
    default: return '数据加载出现问题，请刷新页面或稍后重试。'
  }
})

const isLoading = computed(() => props.type === 'loading')
const showRetryButton = computed(() => props.showRetry && !isLoading.value)
const showHomeButton = computed(() => props.showHome && !isLoading.value)
const showWorkbench = computed(() => props.showWorkbench && !isLoading.value)

// 防刷机制：点击重试后 disabled 3秒
const retryDisabled = ref(false)
let retryTimer = null

const goTo = (route) => {
  if (route) router.push(route)
}

const emit = defineEmits(['retry'])

const retry = () => {
  if (retryDisabled.value) return
  retryDisabled.value = true
  emit('retry')
  retryTimer = setTimeout(() => {
    retryDisabled.value = false
    retryTimer = null
  }, 3000)
}

onBeforeUnmount(() => {
  if (retryTimer) {
    clearTimeout(retryTimer)
    retryTimer = null
  }
})
</script>

<style scoped>
.error-state {
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

.error-icon {
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
