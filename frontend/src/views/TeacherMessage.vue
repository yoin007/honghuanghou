<script setup>
import { ref, onMounted } from 'vue'
import { ElCard, ElMessage, ElEmpty } from 'element-plus'
import api from '../utils/api'

const messages = ref([])
const loading = ref(false)
const classCode = ref('')

const getClassCode = () => {
  const code = document.cookie.split('; ').find(row => row.startsWith('classCode='))
  return code ? code.split('=')[1] : null
}

const fetchMessages = async () => {
  const classCode = getClassCode()
  if (!classCode) {
    ElMessage.error('请先选择班级')
    return
  }

  loading.value = true
  try {
    const response = await api.get(`/api/messages/${classCode}`)
    console.log('Messages response:', response.data)
    if (response.data && Array.isArray(response.data.messages)) {
      messages.value = response.data.messages
    } else {
      messages.value = []
      ElMessage.warning('暂无老师留言')
    }
  } catch (error) {
    console.error('Error fetching messages:', error)
    ElMessage.error('获取老师留言失败')
    messages.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchMessages()
  classCode.value = getClassCode()
})
</script>

<template>
  <div class="teacher-message-container">
    <h2>{{ classCode ? `${classCode}班主任寄语` : '班主任寄语' }}</h2>
    <el-empty v-if="!loading && !messages.length" description="暂无班主任寄语" />
    <el-card v-else-if="messages.length" class="message-card">
      <div class="message-content" v-for="(message, index) in messages" :key="index">
        <div class="quote-marks">"</div>
        <p class="quote">{{ message.content }}</p>
        <div class="signature">
          <p class="teacher">—— {{ message.teacher }}</p>
          <p class="date">{{ message.date }}</p>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.teacher-message-container {
  padding: 1rem;
  max-width: 800px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
  color: #409EFF;
  text-align: center;
}

.message-card {
  margin-top: 1rem;
  background-color: #f8f9fa;
  position: relative;
  overflow: visible;
}

.message-content {
  padding: 1rem 0;
  border-bottom: 1px solid #ebeef5;
}

.message-content:last-child {
  border-bottom: none;
}

.message-date {
  font-size: 14px;
  color: #909399;
  margin-bottom: 0.5rem;
}

.message-text {
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.quote-marks {
  position: absolute;
  top: -20px;
  left: 20px;
  font-size: 80px;
  color: #dcdfe6;
  font-family: "Times New Roman", serif;
  line-height: 1;
}

.quote {
  font-size: 16px;
  line-height: 1.8;
  color: #303133;
  margin-bottom: 30px;
  text-indent: 2em;
  position: relative;
  z-index: 1;
}

.signature {
  text-align: right;
  margin-top: 20px;
}

.teacher {
  font-size: 16px;
  color: #606266;
  margin-bottom: 5px;
}

.date {
  font-size: 14px;
  color: #909399;
}

/* 移动设备适配 */
@media screen and (max-width: 768px) {
  .teacher-message-container {
    padding: 0.5rem;
  }

  .message-card {
    margin-top: 0.5rem;
  }

  .message-content {
    padding: 0.75rem 0;
  }

  .message-date {
    font-size: 12px;
  }

  .message-text {
    font-size: 14px;
  }

  :deep(.el-card__body) {
    padding: 12px;
  }
}

:deep(.el-card__body) {
  padding: 0;
}
</style>
