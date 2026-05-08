/**
 * 驾驶舱请求状态管理 composable
 *
 * 职责边界：
 * - 管理 loading / errorState / forbidden 三个状态
 * - 执行请求流程（try/catch/finally + 错误处理）
 * - 不涉及具体 API（页面提供 requestFn）
 * - 不涉及 summary 结构（页面处理 onSuccess）
 */
import { ref } from 'vue'
import { applyDashboardError } from '@/utils/dashboardError'

export function useDashboardRequest() {
  const loading = ref(false)
  const errorState = ref(null)
  const forbidden = ref(false)

  /**
   * 执行驾驶舱请求
   * @param {Function} requestFn - 返回 Promise 的请求函数（页面提供，如 () => getTeachingDashboardSummary(filters)）
   * @param {Function} onSuccess - 成功回调，接收 res.data（页面提供，如 data => { summary.value = data }）
   * @returns {Promise<void>}
   */
  const execute = async (requestFn, onSuccess) => {
    loading.value = true
    errorState.value = 'loading'
    forbidden.value = false
    try {
      const res = await requestFn()
      if (res.success) {
        onSuccess(res.data)
        errorState.value = null
      } else {
        applyDashboardError(res, forbidden, errorState)
      }
    } catch (e) {
      applyDashboardError(e, forbidden, errorState)
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    errorState,
    forbidden,
    execute
  }
}