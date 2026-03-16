import { ref } from 'vue'

/**
 * 加载状态管理 Composable
 * 用于管理页面的加载状态
 */
export function useLoading(initialState = false) {
  const loading = ref(initialState)
  const error = ref(null)

  const startLoading = () => {
    loading.value = true
    error.value = null
  }

  const stopLoading = () => {
    loading.value = false
  }

  const setError = (err) => {
    error.value = err
    loading.value = false
  }

  const wrap = async (fn) => {
    startLoading()
    try {
      const result = await fn()
      stopLoading()
      return result
    } catch (err) {
      setError(err)
      throw err
    }
  }

  return {
    loading,
    error,
    startLoading,
    stopLoading,
    setError,
    wrap
  }
}
