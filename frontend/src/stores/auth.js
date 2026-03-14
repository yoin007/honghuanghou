import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../utils/api'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref('')
  const role = ref('')
  const isAdmin = ref(false)
  const isLoggedIn = computed(() => !!token.value)

  // 初始化时解析 token
  const initAuth = () => {
    if (token.value) {
      try {
        api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
        const base64Url = token.value.split('.')[1]
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
        const payload = JSON.parse(window.atob(base64))
        username.value = payload.sub
        role.value = payload.role
        isAdmin.value = payload.role === 'admin'
      } catch (error) {
        console.error('Failed to parse token:', error)
        logout()
      }
    }
  }

  const login = async (user, password) => {
    const formData = new URLSearchParams()
    formData.append('username', user)
    formData.append('password', password)

    const response = await api.post('/api/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })

    if (response.data.access_token) {
      const newToken = response.data.access_token
      token.value = newToken
      localStorage.setItem('token', newToken)
      api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`

      const base64Url = newToken.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(window.atob(base64))
      username.value = payload.sub
      role.value = payload.role
      isAdmin.value = payload.role === 'admin'

      ElMessage.success('登录成功')
      return true
    }
    return false
  }

  const logout = () => {
    token.value = ''
    username.value = ''
    role.value = ''
    isAdmin.value = false
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
    ElMessage.success('已退出登录')
  }

  // 初始化
  initAuth()

  return {
    token,
    username,
    role,
    isAdmin,
    isLoggedIn,
    login,
    logout,
    initAuth
  }
})
