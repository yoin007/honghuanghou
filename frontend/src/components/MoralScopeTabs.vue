<template>
  <div class="moral-scope-tabs" v-if="showTabs">
    <el-radio-group v-model="activeScope" @change="handleScopeChange">
      <el-radio-button
        v-for="tab in tabs"
        :key="tab.key"
        :value="tab.key"
      >
        {{ tab.label }}
      </el-radio-button>
    </el-radio-group>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import moralApi from '@/api/modules/moral'

const props = defineProps({
  /**
   * 模块名称，对应后端 API 路径
   * 可选值: 'moment_records', 'daily_records'
   */
  module: {
    type: String,
    required: true,
    validator: (val) => ['moment_records', 'daily_records'].includes(val)
  }
})

const emit = defineEmits(['change', 'ready'])

const tabs = ref([])
const activeScope = ref(null)
const loading = ref(false)

// 是否显示选项卡（单一选项时不显示）
const showTabs = computed(() => tabs.value.length > 1)

/**
 * 加载数据范围能力
 */
async function loadDataScope() {
  loading.value = true
  try {
    const res = await moralApi.getDataScope()
    if (res.success && res.data) {
      const moduleScope = res.data[props.module]
      if (moduleScope) {
        tabs.value = moduleScope.tabs || []
        activeScope.value = moduleScope.default_tab || null

        // 即使只有一个选项也要通知父组件默认 scope
        if (tabs.value.length > 0) {
          emit('change', activeScope.value)
        }
        emit('ready', { tabs: tabs.value, defaultTab: activeScope.value })
      }
    }
  } catch (error) {
    console.error('获取数据范围能力失败:', error)
  } finally {
    loading.value = false
  }
}

/**
 * 选项卡切换事件
 */
function handleScopeChange(value) {
  emit('change', value)
}

onMounted(() => {
  loadDataScope()
})

// 监听 module 变化重新加载
watch(() => props.module, () => {
  loadDataScope()
})
</script>

<style scoped>
.moral-scope-tabs {
  margin-bottom: 16px;
}
</style>