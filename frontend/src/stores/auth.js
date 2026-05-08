import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/modules/auth'
import { ElMessage } from 'element-plus'
import { parseRolesFromToken } from '@/shared/auth/roles'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref('')
  const role = ref('')
  const isAdmin = ref(false)
  const isJiaowu = ref(false)
  const isXuefa = ref(false)
  const isCleader = ref(false)
  const isLoggedIn = computed(() => !!token.value)

  // 从 token 解析角色并设置 refs
  const setRolesFromToken = (tokenValue) => {
    const flags = parseRolesFromToken(tokenValue)
    isAdmin.value = flags.admin
    isJiaowu.value = flags.jiaowu
    isXuefa.value = flags.xuefa
    isCleader.value = flags.cleader
  }

  // 初始化时解析 token
  const initAuth = () => {
    if (token.value) {
      try {
        const base64Url = token.value.split('.')[1]
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
        const payload = JSON.parse(window.atob(base64))
        username.value = payload.sub
        role.value = payload.role
        setRolesFromToken(token.value)
      } catch (error) {
        console.error('Failed to parse token:', error)
        logout()
      }
    }
  }

  const login = async (user, password) => {
    const response = await authApi.login(user, password)

    if (response.data.access_token) {
      const newToken = response.data.access_token
      token.value = newToken
      localStorage.setItem('token', newToken)

      const base64Url = newToken.split('.')[1]
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(window.atob(base64))
      username.value = payload.sub
      role.value = payload.role
      setRolesFromToken(newToken)

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
    isJiaowu.value = false
    isXuefa.value = false
    isCleader.value = false
    localStorage.removeItem('token')
    ElMessage.success('已退出登录')
  }

  // 初始化
  initAuth()

  return {
    token,
    username,
    role,
    isAdmin,
    isJiaowu,
    isXuefa,
    isCleader,
    isLoggedIn,
    login,
    logout,
    initAuth
  }
})
