<template>
  <div class="upload-schedule-container">
    <el-card class="upload-card">
      <template #header>
        <div class="card-header">
          <span>更新课表</span>
        </div>
      </template>
      
      <div class="upload-content">
        <el-alert
          title="上传须知"
          type="info"
          description="仅支持上传 .xlsx 格式的课表文件。上传后文件将保存到服务器暂存目录。"
          show-icon
          :closable="false"
          class="mb-4"
        />
        
        <el-upload
          ref="uploadRef"
          class="schedule-upload"
          drag
          action="/api/upload-schedule"
          :headers="uploadHeaders"
          :on-success="handleSuccess"
          :on-error="handleError"
          :before-upload="beforeUpload"
          :on-change="handleChange"
          :auto-upload="false"
          accept=".xlsx"
          :limit="1"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            将文件拖到此处，或<em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              仅支持 xlsx 文件
            </div>
          </template>
        </el-upload>
        
        <div class="upload-footer">
          <el-button 
            type="primary" 
            @click="submitUpload" 
            :disabled="!hasFile"
            size="large"
            class="submit-btn"
          >
            开始提交
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

const uploadRef = ref(null)
const hasFile = ref(false)

const uploadHeaders = computed(() => {
  const token = localStorage.getItem('token')
  return {
    Authorization: token ? `Bearer ${token}` : ''
  }
})

const handleChange = (_, fileList) => {
  hasFile.value = fileList.length > 0
}

const beforeUpload = (file) => {
  const isXlsx = file.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || file.name.endsWith('.xlsx')
  if (!isXlsx) {
    ElMessage.error('只能上传 xlsx 格式的文件!')
    return false
  }
  return true
}

const submitUpload = () => {
  if (uploadRef.value) {
    uploadRef.value.submit()
  }
}

const handleSuccess = () => {
  ElMessage.success('文件上传成功！')
  hasFile.value = false
}

const handleError = (error) => {
  console.error('上传失败:', error)
  ElMessage.error('文件上传失败，请检查登录状态或网络。')
}
</script>

<style scoped>
.upload-schedule-container {
  padding: 20px;
  display: flex;
  justify-content: center;
}

.upload-card {
  width: 100%;
  max-width: 600px;
}

.card-header {
  font-weight: bold;
  font-size: 18px;
}

.upload-content {
  padding: 20px 0;
}

.mb-4 {
  margin-bottom: 20px;
}

.schedule-upload {
  width: 100%;
  margin-bottom: 20px;
}

.upload-footer {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.submit-btn {
  width: 200px;
}
</style>
