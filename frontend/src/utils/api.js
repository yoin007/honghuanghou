import axios from 'axios'

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

// 响应拦截器
api.interceptors.response.use(
  response => {
    if (import.meta.env.DEV) {
      // 开发环境只记录状态码，不记录响应体（可能包含敏感数据）
      console.log('[DEV] Response:', response.status, response.config.url)
    }
    return response
  },
  error => {
    // 生产环境也记录错误以便调试
    console.error('Response Error:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

export default api
