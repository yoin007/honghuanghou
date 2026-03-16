<template>
  <div class="routine-record-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>常规记录</span>
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
        label-width="80px"
        class="record-form"
      >
        <el-form-item label="班级" prop="class_code">
          <el-select 
            v-model="form.class_code" 
            placeholder="请选择班级" 
            @change="handleClassChange"
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

        <el-form-item label="姓名" prop="names">
          <el-select
            v-model="form.names"
            multiple
            filterable
            placeholder="请选择学生（可多选）"
            style="width: 100%"
            :loading="studentsLoading"
          >
            <el-option
              v-for="student in students"
              :key="student.name"
              :label="student.name"
              :value="student.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="睡觉" value="睡觉" />
            <el-option label="校服" value="校服" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>

        <el-form-item label="事件" prop="event">
          <el-input 
            v-model="form.event" 
            type="textarea" 
            :rows="3" 
            placeholder="请输入事件详情"
          />
        </el-form-item>

        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" placeholder="请输入备注（可选）" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="submitting">提交记录</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 提交成功后的反馈 -->
    <el-dialog
      v-model="showSuccessDialog"
      title="提交成功"
      width="90%"
      style="max-width: 500px;"
    >
      <el-result
        icon="success"
        title="记录已保存"
        sub-title="您提交的常规记录已成功保存"
      >
        <template #extra>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="班级">{{ lastRecord.class_code }}</el-descriptions-item>
            <el-descriptions-item label="学生">{{ lastRecord.names?.join('/') }}</el-descriptions-item>
            <el-descriptions-item label="类型">{{ lastRecord.type }}</el-descriptions-item>
            <el-descriptions-item label="事件">{{ lastRecord.event }}</el-descriptions-item>
            <el-descriptions-item label="备注">{{ lastRecord.remark }}</el-descriptions-item>
            <el-descriptions-item label="记录人">{{ lastRecord.recorder }}</el-descriptions-item>
          </el-descriptions>
          <div style="margin-top: 20px; text-align: center;">
            <el-button type="primary" @click="showSuccessDialog = false">确定</el-button>
          </div>
        </template>
      </el-result>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
// Pinia 的 computed 在 script setup 中需要用 computed 包装
const isLoggedIn = computed(() => authStore.isLoggedIn)
const username = computed(() => authStore.username)

const formRef = ref(null)
const classCodes = ref([])
const students = ref([])
const studentsLoading = ref(false)
const submitting = ref(false)
const showSuccessDialog = ref(false)
const lastRecord = ref({})

const form = ref({
  class_code: '',
  names: [],
  type: '',
  event: '',
  remark: '',
  recorder: ''
})

const rules = {
  class_code: [{ required: true, message: '请选择班级', trigger: 'change' }],
  names: [{ required: true, message: '请选择至少一名学生', trigger: 'change' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  event: [{ required: true, message: '请输入事件详情', trigger: 'blur' }]
}

// 获取班级列表
const fetchClassCodes = async () => {
  try {
    const response = await api.get('/api/class-codes/')
    if (response.data) {
      classCodes.value = response.data['class_codes']
    } else {
      classCodes.value = []
      ElMessage.warning('未找到班级列表')
    }
  } catch (error) {
    console.error('Fetch class codes error:', error)
    ElMessage.error('获取班级列表失败')
  }
}

// 获取学生列表
const handleClassChange = async (val) => {
  form.value.names = [] // 清空已选学生
  if (!val) return
  
  studentsLoading.value = true
  try {
    const response = await api.get(`/api/students/${val}`)
    // API returns ['Name1', 'Name2', ...]
    // Transform to [{name: 'Name1'}, {name: 'Name2'}, ...] for the template
    students.value = Array.isArray(response.data['students']) ? response.data['students'].map(name => ({ name })) : []
  } catch (error) {
    console.error('Fetch students error:', error)
    ElMessage.error('获取学生列表失败')
  } finally {
    studentsLoading.value = false
  }
}

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      form.value.recorder = username.value || ''
      try {
        await api.post('/api/insert_daily/', form.value)
        
        lastRecord.value = { ...form.value }
        showSuccessDialog.value = true
        resetForm()
        ElMessage.success('提交成功')
      } catch (error) {
        console.error('Submit daily error:', error)
        ElMessage.error('提交失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
}

onMounted(() => {
  fetchClassCodes()
})
</script>

<style scoped>
.routine-record-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.login-tip {
  text-align: center;
  padding: 40px 0;
}

@media screen and (max-width: 768px) {
  .routine-record-container {
    padding: 10px;
  }
}
</style>