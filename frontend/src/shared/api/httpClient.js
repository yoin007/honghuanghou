/**
 * 统一 HTTP 客户端
 *
 * 提供唯一的 axios 实例，统一处理：
 * - baseURL 配置（环境变量 + HTTPS 协议检测）
 * - timeout（10秒）
 * - Content-Type / Accept
 * - Authorization（通过请求拦截器注入）
 * - 401 处理（跳转登录）
 * - 错误提示（ElMessage）
 * - 重试策略（3次，1秒延迟，针对 5xx 状态码）
 * - 响应格式解析（支持 FastAPI success 格式和 code 格式）
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

// 环境变量 baseURL
const envBaseURL = import.meta.env.VITE_API_BASE_URL || ''

// HTTPS 页面检测
const isHttpsPage =
  typeof window !== 'undefined' && window.location && window.location.protocol === 'https:'
const isEnvHttp = /^http:\/\//i.test(envBaseURL)

// 开发模式使用 Vite proxy，生产模式使用环境变量
const baseURL = import.meta.env.DEV ? '' : (isHttpsPage && isEnvHttp ? '' : envBaseURL)
const debugHttp = import.meta.env.DEV && import.meta.env.VITE_DEBUG_HTTP === 'true'

// 重试配置
const retryConfig = {
  retries: 3,
  retryDelay: 1000,
  retryStatuses: [408, 429, 500, 502, 503, 504]
}

// 创建 axios 实例
const httpClient = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: false
})

// 请求拦截器 - 添加元数据和 Authorization
httpClient.interceptors.request.use(
  config => {
    // 添加请求元数据
    config.metadata = { startTime: Date.now() }

    // 从 localStorage 获取 token 并注入 Authorization
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 开发环境日志
    if (debugHttp) {
      console.debug('[httpClient] Request:', config.method?.toUpperCase(), config.url)
    }

    return config
  },
  error => {
    console.error('[httpClient] Request Error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器 - 重试机制
httpClient.interceptors.response.use(
  response => response,
  async error => {
    const config = error.config

    // 无配置或不支持重试
    if (!config || !config.metadata) {
      return Promise.reject(error)
    }

    config.__retryCount = config.__retryCount || 0

    // 检查是否需要重试
    const shouldRetry =
      config &&
      retryConfig.retryStatuses.includes(error.response?.status) &&
      config.__retryCount < retryConfig.retries

    if (shouldRetry) {
      config.__retryCount++

      const delay = retryConfig.retryDelay * config.__retryCount

      if (debugHttp) {
        console.debug(`[httpClient] Retrying (${config.__retryCount}/${retryConfig.retries}):`, config.url)
      }

      return new Promise(resolve =>
        setTimeout(() => resolve(httpClient(config)), delay)
      )
    }

    return Promise.reject(error)
  }
)

// 响应拦截器 - 响应格式解析和错误处理
httpClient.interceptors.response.use(
  response => {
    if (debugHttp) {
      console.debug('[httpClient] Response:', response.status, response.config.url)
    }

    const res = response.data

    // 允许调用方拿业务失败 payload 自己处理（不弹全局 Toast、不 reject）
    // 用法：httpClient.post(url, data, { returnBusinessError: true })
    //   适用场景：导入接口要拿到 errors[] 明细，注册接口要看具体报错等。
    const cfg = response.config || {}
    const passBusinessError = cfg.returnBusinessError === true

    // FastAPI 格式: { success: true/false, data, message }
    if (res !== undefined && 'success' in res) {
      if (res.success) {
        return res
      } else if (passBusinessError) {
        return res
      } else {
        ElMessage.error(res.message || '操作失败')
        return Promise.reject(new Error(res.message || '操作失败'))
      }
    }

    // 统一响应格式: { code, message, data }
    if (res !== undefined && 'code' in res) {
      if (res.code >= 200 && res.code < 300) {
        return res
      }
      if (res.code >= 400) {
        if (passBusinessError) {
          return res
        }
        ElMessage.error(res.message || '操作失败')
        return Promise.reject(new Error(res.message || '操作失败'))
      }
      return res
    }

    // 兼容旧格式：直接返回 axios response
    return response
  },
  error => {
    const status = error.response?.status
    const cfg = error.config || {}
    const isTimeout = error.code === 'ECONNABORTED' || /timeout/i.test(error.message || '')
    const message = isTimeout
      ? '请求处理时间较长，请稍后查看结果或重试'
      : (error.response?.data?.detail || error.response?.data?.message || error.message)

    // 允许调用方按状态码抑制全局错误弹窗：
    //   httpClient.get(url, { silentStatuses: [404] })
    //   httpClient.get(url, { silent: true })  // 全部状态码都不弹
    const silentStatuses = Array.isArray(cfg.silentStatuses) ? cfg.silentStatuses : []
    const shouldSilent = cfg.silent === true || (status && silentStatuses.includes(status))

    if (isTimeout) {
      if (!shouldSilent) ElMessage.error(message)
    } else if (shouldSilent) {
      // 业务层自行处理，不弹全局
    } else {
      switch (status) {
        case 401:
          ElMessage.error('登录已过期，请重新登录')
          // 清除 token 并跳转登录
          localStorage.removeItem('token')
          // 如果当前不在登录页，跳转到首页触发登录弹窗
          if (window.location.pathname !== '/') {
            window.location.href = '/'
          }
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
    }

    console.error('[httpClient] Error:', status, error.message)
    return Promise.reject(error)
  }
)

// 命名导出
export { httpClient }

// 默认导出
export default httpClient
