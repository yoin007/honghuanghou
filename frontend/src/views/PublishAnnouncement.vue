<template>
  <div class="publish-announcement-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>发布公告</span>
        </div>
      </template>

      <el-form :model="announcementForm" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="班级" prop="classCodes">
          <el-select 
            v-model="announcementForm.classCodes" 
            multiple 
            placeholder="请选择班级" 
            style="width: 100%"
          >
            <el-option
              v-for="code in classCodes"
              :key="code"
              :label="code"
              :value="code"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="公告标题" prop="title">
          <el-input v-model="announcementForm.title" placeholder="请输入公告标题" />
        </el-form-item>
        
        <el-form-item label="发布人">
          <span class="author-display">{{ username }}</span>
        </el-form-item>
        
        <el-form-item label="公告内容" prop="content">
          <el-input
            v-model="announcementForm.content"
            type="textarea"
            :rows="8"
            placeholder="请输入公告内容"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitAnnouncement" :loading="submitting">发布公告</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const username = computed(() => authStore.username)

const formRef = ref(null)
const submitting = ref(false)
const classCodes = ref([])

const announcementForm = reactive({
  classCodes: [],
  title: '',
  content: ''
})

const rules = {
  classCodes: [{ required: true, message: '请选择班级', trigger: 'change' }],
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }]
}

const submitAnnouncement = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      let successCount = 0
      let failCount = 0
      
      for (const classCode of announcementForm.classCodes) {
        try {
          const formData = { 
            classCode: classCode,
            title: announcementForm.title,
            author: username.value,
            content: announcementForm.content
          }
          const response = await api.post('/api/announcement/', formData)
          if (response.data && response.data.id) {
            successCount++
          } else {
            failCount++
          }
        } catch (error) {
          console.error('Submit announcement error:', error)
          failCount++
        }
      }
      
      if (failCount === 0) {
        ElMessage.success(`公告已发布到 ${successCount} 个班级`)
        resetForm()
      } else {
        ElMessage.warning(`发布完成：成功 ${successCount} 个，失败 ${failCount} 个`)
      }
      
      submitting.value = false
    }
  })
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

const fetchClassCodes = async () => {
  try {
    const response = await api.get('/api/class-codes/')
    if (response.data && response.data.class_codes) {
      classCodes.value = response.data.class_codes
    }
  } catch (error) {
    console.error('Error fetching class codes:', error)
  }
}

onMounted(() => {
  fetchClassCodes()
})
</script>

<style scoped>
.publish-announcement-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.box-card {
  margin-bottom: 20px;
}

.author-display {
  color: #409EFF;
  font-weight: 500;
}
</style>
