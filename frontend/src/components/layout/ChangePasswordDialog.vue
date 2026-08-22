<template>
  <el-dialog
    v-model="visible"
    title="修改密码"
    width="400px"
    :close-on-click-modal="false"
    class="change-password-dialog"
  >
    <el-form
      :model="passwordForm"
      :rules="passwordRules"
      ref="passwordFormRef"
      label-width="90px"
    >
      <el-form-item prop="old_password" label="原密码">
        <el-input
          v-model="passwordForm.old_password"
          type="password"
          show-password
          placeholder="请输入原密码"
        />
      </el-form-item>
      <el-form-item prop="new_password" label="新密码">
        <el-input
          v-model="passwordForm.new_password"
          type="password"
          show-password
          placeholder="6-64 位"
        />
      </el-form-item>
      <el-form-item prop="confirm_password" label="确认新密码">
        <el-input
          v-model="passwordForm.confirm_password"
          type="password"
          show-password
          placeholder="请再次输入新密码"
          @keyup.enter="handleSubmit"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { teacherApi } from '@/api/modules/teacher'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const submitLoading = ref(false)
const passwordFormRef = ref(null)
const passwordForm = ref({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirm = (rule, value, callback) => {
  if (value !== passwordForm.value.new_password) {
    callback(new Error('两次输入的新密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度为 6-64 位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' }
  ]
}

// 同步 v-model，每次打开时清空表单
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val) {
      passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
    }
  }
)

watch(visible, (val) => {
  emit('update:modelValue', val)
})

// 改密成功后保持当前会话（JWT 无状态），仅提示
const handleSubmit = async () => {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitLoading.value = true
    try {
      await teacherApi.changePassword({
        old_password: passwordForm.value.old_password,
        new_password: passwordForm.value.new_password
      })
      ElMessage.success('密码修改成功')
      visible.value = false
    } catch (error) {
      console.error('修改密码失败:', error)
      ElMessage.error(error.response?.data?.detail || '修改密码失败')
    } finally {
      submitLoading.value = false
    }
  })
}
</script>
