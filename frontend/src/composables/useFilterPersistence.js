// Filter Persistence Composable
// 使用 localStorage 保存和恢复筛选条件

import { ref, watch } from 'vue'

export function useFilterPersistence(key, defaultValue = {}) {
  const STORAGE_KEY = `filter_${key}`

  // 从 localStorage 读取保存的筛选条件
  const loadFilters = () => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        return { ...defaultValue, ...JSON.parse(saved) }
      }
    } catch (e) {
      console.warn('Failed to load filters:', e)
    }
    return defaultValue
  }

  // 保存筛选条件到 localStorage
  const saveFilters = (filters) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filters))
    } catch (e) {
      console.warn('Failed to save filters:', e)
    }
  }

  // 清除保存的筛选条件
  const clearFilters = () => {
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch (e) {
      console.warn('Failed to clear filters:', e)
    }
  }

  // 创建响应式筛选状态
  const filters = ref(loadFilters())

  // 监听筛选条件变化，自动保存
  watch(filters, (newValue) => {
    saveFilters(newValue)
  }, { deep: true })

  return {
    filters,
    saveFilters,
    clearFilters,
    reset: () => {
      filters.value = { ...defaultValue }
    }
  }
}
