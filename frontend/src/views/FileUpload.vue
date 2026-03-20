<template>
  <div class="file-upload-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>文件上传</span>
        </div>
      </template>

      <div v-if="!isLoggedIn" class="login-tip">
        <el-result
          icon="warning"
          title="需要登录"
          sub-title="请先登录教师账号以使用此功能"
        >
        </el-result>
      </div>

      <el-form
        v-else
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        class="upload-form"
      >
        <el-form-item label="选择文件" prop="file">
          <el-upload
            ref="uploadRef"
            class="upload-area"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-exceed="handleExceed"
            :file-list="fileList"
            accept=".jpg,.jpeg,.png,.doc,.docx,.xlsx,.xls,.ppt,.pptx,.pdf"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 jpg, png, doc, docx, xlsx, xls, ppt, pptx, pdf 格式，最大 50MB
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <el-form-item label="打印份数" prop="copies">
          <el-input-number v-model="form.copies" :min="1" :max="5000" style="width: 200px" />
        </el-form-item>

        <el-form-item label="使用日期" prop="useDate">
          <el-date-picker
            v-model="form.useDate"
            type="date"
            placeholder="选择日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 200px"
          />
        </el-form-item>

        <el-form-item label="备注" prop="note">
          <el-input
            v-model="form.note"
            type="textarea"
            placeholder="打印要求(单双面打印等)"
            :rows="3"
            style="max-width: 400px"
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="submitting">
            上传文件
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { filegatherApi } from '../api/modules/filegather'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isLoggedIn)

const formRef = ref(null)
const uploadRef = ref(null)
const fileList = ref([])
const submitting = ref(false)

const form = ref({
  file: null,
  copies: 1,
  useDate: '',
  note: ''
})

const rules = {
  file: [{ required: true, message: '请选择文件', trigger: 'change' }],
  copies: [{ required: true, message: '请输入打印份数', trigger: 'change' }],
  useDate: [{ required: true, message: '请选择使用日期', trigger: 'change' }]
}

const handleFileChange = (file) => {
  form.value.file = file.raw
  fileList.value = [file]
}

const handleExceed = () => {
  ElMessage.warning('最多只能上传一个文件')
}

const submitForm = async () => {
  if (!form.value.file) {
    ElMessage.error('请选择文件')
    return
  }

  if (!form.value.useDate) {
    ElMessage.error('请选择使用日期')
    return
  }

  submitting.value = true
  try {
    const response = await filegatherApi.uploadFile(
      form.value.file,
      form.value.copies,
      form.value.useDate,
      form.value.note
    )
    ElMessage.success('文件上传成功')
    resetForm()
  } catch (error) {
    const detail = error?.response?.data?.detail || '上传失败'
    ElMessage.error(detail)
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  form.value = {
    file: null,
    copies: 1,
    useDate: '',
    note: ''
  }
  fileList.value = []
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}
</script>

<style scoped>
.file-upload-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.login-tip {
  text-align: center;
  padding: 40px 0;
}

.upload-area {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
}
</style>