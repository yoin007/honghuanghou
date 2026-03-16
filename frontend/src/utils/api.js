import axios from 'axios'
import { ElMessage } from 'element-plus'

const envBaseURL = import.meta.env.VITE_API_BASE_URL || ''
const isHttpsPage =
  typeof window !== 'undefined' && window.location && window.location.protocol === 'https:'
const isEnvHttp = /^http:\/\//i.test(envBaseURL)
const baseURL = import.meta.env.DEV ? '' : (isHttpsPage && isEnvHttp ? '' : envBaseURL)

const api = axios.create({
  baseURL,
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: false
})

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

    // 支持两种响应格式:
    // 1. 统一格式: { code, message, data }
    // 2. 原始格式: 直接返回数据 (兼容旧接口)

    // 如果是统一响应格式
    if (res !== undefined && 'code' in res) {
      // 业务层面的成功 (code >= 200 && code < 300)
      if (res.code >= 200 && res.code < 300) {
        // 可选: 显示成功消息 (避免频繁提示)
        // if (res.message) {
        //   ElMessage.success(res.message)
        // }
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
    const message = error.response?.data?.message || error.message

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
