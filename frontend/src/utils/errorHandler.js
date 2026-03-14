// API Error Handler Utility
import { ElMessage, ElMessageBox } from 'element-plus'

// 错误代码到友好消息的映射
const errorMessages = {
  // 认证错误
  401: '登录已过期，请重新登录',
  403: '您没有权限执行此操作',
  419: '页面已过期，请刷新重试',

  // 客户端错误
  400: '请求参数错误',
  404: '请求的资源不存在',
  422: '数据验证失败',

  // 服务端错误
  500: '服务器内部错误',
  502: '服务暂时不可用',
  503: '服务维护中，请稍后重试',
  504: '请求超时，请重试',

  // 网络错误
  ECONNABORTED: '请求超时，请检查网络后重试',
  NETWORK_ERROR: '网络连接失败，请检查网络'
}

/**
 * 处理 API 错误，返回友好的错误消息
 * @param {Error} error - 错误对象
 * @returns {string} 友好的错误消息
 */
export function getFriendlyErrorMessage(error) {
  // 如果是 Axios 错误
  if (error.response) {
    const status = error.response.status

    // 检查是否有后端返回的详细错误消息
    const backendMessage = error.response.data?.detail
    if (backendMessage) {
      return backendMessage
    }

    // 使用预定义的错误消息
    return errorMessages[status] || `请求失败 (${status})`
  }

  // 如果是网络错误
  if (error.code === 'ECONNABORTED') {
    return errorMessages.ECONNABORTED
  }

  if (error.message?.includes('Network Error')) {
    return errorMessages.NETWORK_ERROR
  }

  // 默认错误消息
  return error.message || '发生未知错误'
}

/**
 * 显示错误消息
 * @param {Error} error - 错误对象
 * @param {string} defaultMessage - 默认消息
 */
export function showError(error, defaultMessage = '操作失败') {
  const message = getFriendlyErrorMessage(error)
  ElMessage.error(message)
}

/**
 * 显示成功消息
 * @param {string} message - 成功消息
 */
export function showSuccess(message = '操作成功') {
  ElMessage.success(message)
}

/**
 * 显示警告消息
 * @param {string} message - 警告消息
 */
export function showWarning(message) {
  ElMessage.warning(message)
}

/**
 * 显示确认对话框
 * @param {string} message - 确认消息
 * @param {string} title - 标题
 * @returns {Promise} Promise 对象
 */
export function showConfirm(message, title = '确认') {
  return ElMessageBox.confirm(message, title, {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
}

/**
 * 包装 async 函数，自动处理错误
 * @param {Function} fn - 要包装的函数
 * @param {object} options - 配置选项
 * @returns {Function} 包装后的函数
 */
export function withErrorHandler(fn, options = {}) {
  const {
    showError: showErrorOption = true,
    defaultMessage = '操作失败',
    onError = null
  } = options

  return async function (...args) {
    try {
      return await fn(...args)
    } catch (error) {
      const message = getFriendlyErrorMessage(error)

      if (showErrorOption) {
        ElMessage.error(message)
      }

      if (onError) {
        onError(error, message)
      }

      throw error
    }
  }
}

/**
 * 创建带错误处理的 API 请求包装器
 * @param {Function} apiFunc - API 函数
 * @returns {Function} 带错误处理的函数
 */
export function createApiWrapper(apiFunc) {
  return withErrorHandler(apiFunc, {
    showError: true,
    defaultMessage: '请求失败'
  })
}

export default {
  getFriendlyErrorMessage,
  showError,
  showSuccess,
  showWarning,
  showConfirm,
  withErrorHandler,
  createApiWrapper
}
