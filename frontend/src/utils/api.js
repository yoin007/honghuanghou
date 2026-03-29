import axios from 'axios'
import { ElMessage } from 'element-plus'

const envBaseURL = import.meta.env.VITE_API_BASE_URL || ''
const isHttpsPage =
  typeof window !== 'undefined' && window.location && window.location.protocol === 'https:'
const isEnvHttp = /^http:\/\//i.test(envBaseURL)
const baseURL = import.meta.env.DEV ? '' : (isHttpsPage && isEnvHttp ? '' : envBaseURL)

// 请求重试配置
const retryConfig = {
  retries: 3,
  retryDelay: 1000,
  retryStatuses: [408, 429, 500, 502, 503, 504]
}

const api = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: false
})

// 请求重试拦截器
api.interceptors.request.use(
  config => {
    // 为请求添加唯一标识，用于取消请求
    config.metadata = { startTime: Date.now() }
    return config
  },
  error => Promise.reject(error)
)

// 添加重试响应拦截器
api.interceptors.response.use(
  response => response,
  async error => {
    const config = error.config

    // 如果没有配置或不支持重试，则直接拒绝
    if (!config || !config.metadata) {
      return Promise.reject(error)
    }

    // 检查是否在重试配置的状态码中
    const shouldRetry =
      config &&
      retryConfig.retryStatuses.includes(error.response?.status) &&
      config.__retryCount < retryConfig.retries

    // 如果需要重试
    if (shouldRetry) {
      config.__retryCount = config.__retryCount || 0
      config.__retryCount++

      // 延迟后再重试
      const delay = retryConfig.retryDelay * config.__retryCount

      if (import.meta.env.DEV) {
        console.log(`[API] Retrying request (${config.__retryCount}/${retryConfig.retries}):`, config.url)
      }

      return new Promise(resolve =>
        setTimeout(() => resolve(api(config)), delay)
      )
    }

    return Promise.reject(error)
  }
)

// 请求拦截器 - 开发环境记录日志
api.interceptors.request.use(
  config => {
    if (import.meta.env.DEV) {
      console.log('[DEV] Request:', config.method?.toUpperCase(), config.url)
    }
    return config
  },
  error => {
    console.error('Request Error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器 - 统一处理响应格式
api.interceptors.response.use(
  response => {
    if (import.meta.env.DEV) {
      // 开发环境只记录状态码，不记录响应体（可能包含敏感数据）
      console.log('[DEV] Response:', response.status, response.config.url)
    }

    const res = response.data

    // 支持多种响应格式:
    // 1. FastAPI 格式: { success: true, data: [...] }
    // 2. 统一格式: { code: 200, message, data }
    // 3. 原始格式: 直接返回数据 (兼容旧接口)

    // FastAPI 格式 (success 字段)
    if (res !== undefined && 'success' in res) {
      if (res.success) {
        return res
      } else {
        ElMessage.error(res.message || '操作失败')
        return Promise.reject(new Error(res.message || '操作失败'))
      }
    }

    // 统一响应格式 (code 字段)
    if (res !== undefined && 'code' in res) {
      // 业务层面的成功 (code >= 200 && code < 300)
      if (res.code >= 200 && res.code < 300) {
        return res
      }

      // 业务错误 (code >= 400)
      if (res.code >= 400) {
        ElMessage.error(res.message || '操作失败')
        return Promise.reject(new Error(res.message || '操作失败'))
      }

      // 其他 code 情况直接返回
      return res
    }

    // 兼容旧格式: 直接返回 response
    return response
  },
  error => {
    // 统一处理错误
    const status = error.response?.status
    // FastAPI HTTPException 返回 detail 字段，后端自定义返回 message 字段
    const message = error.response?.data?.detail || error.response?.data?.message || error.message

    switch (status) {
      case 401:
        ElMessage.error('登录已过期，请重新登录')
        // 可以在这里跳转到登录页
        // window.location.href = '/login'
        break
      case 403:
        ElMessage.error('没有权限执行此操作')
        break
      case 404:
        ElMessage.error('请求的资源不存在')
        break
      case 500:
        ElMessage.error('服务器内部错误')
        break
      default:
        ElMessage.error(message || '网络错误')
    }

    // 生产环境也记录错误以便调试
    console.error('Response Error:', status, error.message)
    return Promise.reject(error)
  }
)

export default api
