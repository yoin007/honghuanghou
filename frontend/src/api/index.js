/**
 * API 模块化导出
 */
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

// 请求拦截器
api.interceptors.request.use(
  config => {
    console.log('Request URL:', config.url)
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
    console.log('Response:', response.data)
    return response
  },
  error => {
    console.error('Response Error:', error.response || error)
    return Promise.reject(error)
  }
)

// 导出 axios 实例
export { api }

// 导出各模块 API
export { authApi } from './modules/auth'
export { userApi } from './modules/user'
export { homeworkApi } from './modules/homework'
export { scheduleApi } from './modules/schedule'
export { filegatherApi } from './modules/filegather'

// 默认导出
export default api
