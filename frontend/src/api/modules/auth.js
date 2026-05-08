/**
 * 认证相关 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const authApi = {
  /**
   * 登录
   * @param {string} username 用户名
   * @param {string} password 密码
   * @returns {Promise}
   */
  login(username, password) {
    const formData = new URLSearchParams()
    formData.append('username', username)
    formData.append('password', password)
    return httpClient.post('/api/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
  },

  /**
   * 刷新 token
   * @returns {Promise}
   */
  refreshToken() {
    return httpClient.post('/api/refresh')
  },

  /**
   * 获取当前用户信息
   * @returns {Promise}
   */
  getCurrentUser() {
    return httpClient.get('/api/user/current')
  },

  /**
   * 登出
   * @returns {Promise}
   */
  logout() {
    return httpClient.post('/api/logout')
  }
}

export default authApi
