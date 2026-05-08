<template>
  <el-dialog
    v-model="visible"
    title="登录"
    width="400px"
    :close-on-click-modal="false"
    class="login-dialog"
  >
    <el-form
      :model="loginForm"
      :rules="loginRules"
      ref="loginFormRef"
      label-width="60px"
    >
      <el-form-item prop="username" label="用户">
        <el-input
          v-model="loginForm.username"
          placeholder="请输入用户名"
          @keyup.enter="handleLogin"
        />
      </el-form-item>
      <el-form-item prop="password" label="密码">
        <el-input
          v-model="loginForm.password"
          type="password"
          show-password
          placeholder="请输入密码"
          @keyup.enter="handleLogin"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleLogin" :loading="loginLoading">
        登录
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getDefaultDashboardByRole } from '@/router/guards'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'login-success'])

const router = useRouter()
const authStore = useAuthStore()

const visible = ref(props.modelValue)
const loginLoading = ref(false)
const loginForm = ref({ username: '', password: '' })
const loginFormRef = ref(null)

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 同步 v-model
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
  }
)

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const handleLogin = async () => {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loginLoading.value = true
      try {
        await authStore.login(loginForm.value.username, loginForm.value.password)
        visible.value = false
        loginForm.value = { username: '', password: '' }
        emit('login-success')
        // 登录成功后跳转到角色默认驾驶舱
        const token = localStorage.getItem('token')
        if (token) {
          const defaultPath = getDefaultDashboardByRole(token)
          router.push(defaultPath)
        }
      } catch (error) {
        console.error(error)
        ElMessage.error('登录失败，请检查用户名和密码')
      } finally {
        loginLoading.value = false
      }
    }
  })
}
</script>