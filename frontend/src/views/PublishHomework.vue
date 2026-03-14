<template>
  <div class="publish-homework-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>发布作业</span>
        </div>
      </template>

      <el-form :model="homeworkForm" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="班级" prop="classCodes">
          <el-select 
            v-model="homeworkForm.classCodes" 
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
        
        <el-form-item label="学科" prop="subject">
          <el-select v-model="homeworkForm.subject" placeholder="请选择学科">
            <el-option
              v-for="subject in subjects"
              :key="subject"
              :label="subject"
              :value="subject"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="作业内容" prop="content">
          <el-input
            v-model="homeworkForm.content"
            type="textarea"
            :rows="5"
            placeholder="请输入作业内容，每项一行"
          />
        </el-form-item>
        
        <el-form-item label="上交日期" prop="deadline">
          <el-date-picker
            v-model="homeworkForm.deadline"
            type="datetime"
            placeholder="选择日期和时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
          />
        </el-form-item>
        
        <el-form-item label="预计用时" prop="duration">
          <el-input-number v-model="homeworkForm.duration" :min="1" :max="180" />
          <span class="unit">分钟</span>
        </el-form-item>
        
        <el-form-item label="作业类型" prop="type">
          <el-radio-group v-model="homeworkForm.type">
            <el-radio value="日常">日常</el-radio>
            <el-radio value="周末">周末</el-radio>
            <el-radio value="假期">假期</el-radio>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="submitHomework" :loading="submitting">发布作业</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()

const formRef = ref(null)
const submitting = ref(false)
const username = authStore.username
const classCodes = ref([])

const subjects = [
  "语文", "数学", "英语", "物理", "化学", "生物", "地理", "历史", "政治", "美术", "技术", "班级"
]

const homeworkForm = reactive({
  classCodes: [],
  subject: '',
  teacher: '',
  content: '',
  deadline: '',
  duration: 30,
  type: '日常'
})

const rules = {
  classCodes: [{ required: true, message: '请选择班级', trigger: 'change' }],
  subject: [{ required: true, message: '请选择学科', trigger: 'change' }],
  content: [{ required: true, message: '请输入作业内容', trigger: 'blur' }],
  deadline: [{ required: true, message: '请选择上交日期', trigger: 'change' }],
  type: [{ required: true, message: '请选择作业类型', trigger: 'change' }]
}

const submitHomework = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      if (homeworkForm.deadline) {
        const deadlineTime = new Date(homeworkForm.deadline).getTime()
        const now = new Date().getTime()
        if (deadlineTime < now) {
          ElMessage.error('上交时间不能早于当前时间')
          return
        }
      }
      
      submitting.value = true
      let successCount = 0
      let failCount = 0
      
      for (const classCode of homeworkForm.classCodes) {
        try {
          const formData = { 
            classCode: classCode,
            subject: homeworkForm.subject,
            teacher: username.value,
            content: homeworkForm.content,
            deadline: homeworkForm.deadline,
            duration: homeworkForm.duration,
            type: homeworkForm.type
          }
          const response = await api.post('/api/homework/', formData)
          if (response.data && response.data.id) {
            successCount++
          } else {
            failCount++
          }
        } catch (error) {
          console.error('Submit homework error:', error)
          failCount++
        }
      }
      
      if (failCount === 0) {
        ElMessage.success(`作业已发布到 ${successCount} 个班级`)
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
  homeworkForm.duration = 30
  homeworkForm.type = '日常'
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
.publish-homework-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.box-card {
  margin-bottom: 20px;
}

.unit {
  margin-left: 10px;
  color: #666;
}
</style>
