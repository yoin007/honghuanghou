<template>
  <div class="random-call-container">
    <el-card class="box-card">
      <div class="card-header">
        <h2>随机点名</h2>
        <div class="controls">
          <span>单次抽取人数:</span>
          <el-input-number
            v-model="pickCount"
            :min="1"
            :max="remainingStudents.length || 1"
            :disabled="loading || !remainingStudents.length"
            size="large"
            @change="handleCountChange"
          />
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="!remainingStudents.length"
            @click="pickRandomStudents"
          >
            开始点名
          </el-button>
          <el-button
            type="warning"
            size="large"
            :disabled="!pickedStudents.length"
            @click="clearPickedStudents"
          >
            清空名单
          </el-button>
        </div>
      </div>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="3" animated />
      </div>

      <template v-else>
        <div v-if="pickedStudents.length > 0" class="result-container">
          <el-alert
            title="本次抽取的同学"
            type="success"
            :closable="false"
            show-icon
          />
          <div class="picked-students">
            <el-tag
              v-for="student in pickedStudents"
              :key="student"
              class="student-tag"
              effect="dark"
              type="success"
            >
              {{ student }}
            </el-tag>
          </div>
        </div>

        <div v-if="allPickedStudents.length > 0" class="history-container">
          <el-alert
            title="已抽取的同学"
            type="warning"
            :closable="false"
            show-icon
          />
          <div class="picked-students">
            <el-tag
              v-for="student in allPickedStudents"
              :key="student"
              class="student-tag"
              effect="plain"
              type="warning"
            >
              {{ student }}
            </el-tag>
          </div>
        </div>

        <div v-if="!classCode" class="empty-container">
          <el-empty description="请先选择班级" />
        </div>
        <div v-else-if="studentList.length === 0" class="empty-container">
          <el-empty description="暂无学生数据" />
        </div>
      </template>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudents } from '@/api/modules/user'

const loading = ref(false)
const studentList = ref([])
const pickedStudents = ref([])
const allPickedStudents = ref([])
const pickCount = ref(1)
const classCode = ref('')

// 计算剩余未抽取的学生
const remainingStudents = computed(() => {
  return studentList.value.filter(student => !allPickedStudents.value.includes(student))
})

const getClassCode = () => {
  const code = document.cookie.split('; ').find(row => row.startsWith('classCode='))
  if (!code) return null
  const value = code.split('=')[1]
  return value
}

const fetchStudentList = async () => {
  const code = getClassCode()
  if (!code) {
    ElMessage.warning('请先选择班级')
    return
  }

  classCode.value = code
  loading.value = true

  try {
    const response = await getStudents(code)
    if (response.data && Array.isArray(response.data.students)) {
      studentList.value = response.data.students
      // 重置选择数量
      pickCount.value = Math.min(pickCount.value, remainingStudents.value.length)
    }
  } catch (error) {
    console.error('Error fetching student list:', error)
    ElMessage.error('获取学生列表失败')
    studentList.value = []
  } finally {
    loading.value = false
  }
}

const handleCountChange = (value) => {
  if (value > remainingStudents.value.length) {
    pickCount.value = remainingStudents.value.length
    ElMessage.warning(`最多只能选择 ${remainingStudents.value.length} 名未抽取的学生`)
  }
}

const pickRandomStudents = () => {
  if (remainingStudents.value.length === 0) {
    ElMessage.warning('所有学生都已被抽取')
    return
  }

  const count = Math.min(pickCount.value, remainingStudents.value.length)
  const tempList = [...remainingStudents.value]
  const picked = []

  for (let i = 0; i < count; i++) {
    const randomIndex = Math.floor(Math.random() * tempList.length)
    picked.push(tempList[randomIndex])
    tempList.splice(randomIndex, 1)
  }

  pickedStudents.value = picked
  allPickedStudents.value = [...allPickedStudents.value, ...picked]
}

const clearPickedStudents = () => {
  pickedStudents.value = []
  allPickedStudents.value = []
  // 重置选择数量
  pickCount.value = Math.min(pickCount.value, studentList.value.length)
}

onMounted(() => {
  fetchStudentList()
})
</script>

<style scoped>
.random-call-container {
  padding: 1rem;
}

.box-card {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text-color);
}

.controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.loading-container {
  padding: 2rem 0;
}

.result-container {
  margin-top: 2rem;
}

.history-container {
  margin-top: 2rem;
}

.picked-students {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.student-tag {
  font-size: 1.2rem;
  padding: 0.5rem 1rem;
}

.empty-container {
  padding: 2rem 0;
}

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    gap: 1rem;
  }

  .controls {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }

  .student-tag {
    font-size: 1rem;
    padding: 0.4rem 0.8rem;
  }
}
</style>
