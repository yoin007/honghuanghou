<template>
  <div class="delay-application-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>延时申请</span>
        </div>
      </template>

      <!-- 申请表单 -->
      <el-form :inline="true" class="demo-form-inline" @submit.prevent>
        <el-form-item label="学生代码">
          <el-input 
            v-model="sid" 
            placeholder="请输入SID" 
            @keyup.enter="fetchStudentInfo"
            @blur="fetchStudentInfo"
            clearable
          >
            <template #append>
              <el-button @click="fetchStudentInfo">查询</el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>

      <!-- 学生信息展示 -->
      <div v-if="studentInfo" class="student-info-display">
        <el-descriptions title="学生信息" border>
          <el-descriptions-item label="姓名">{{ studentInfo.name }}</el-descriptions-item>
          <el-descriptions-item label="宿舍">{{ studentInfo.roomid || '未分配' }}</el-descriptions-item>
          <el-descriptions-item label="床号">{{ studentInfo.rpid || '未分配' }}</el-descriptions-item>
        </el-descriptions>
        <div class="submit-action">
          <el-button type="primary" @click="submitDelay" :loading="submitting">提交申请</el-button>
        </div>
      </div>
    </el-card>

    <!-- 申请记录列表 -->
    <el-card class="box-card list-card">
      <template #header>
        <div class="card-header">
          <span>今日申请记录</span>
          <el-button link @click="fetchDelayRecords">刷新</el-button>
        </div>
      </template>
      
      <el-table :data="delayRecords" style="width: 100%" v-loading="loading">
        <el-table-column prop="姓名" label="姓名" width="120" />
        <el-table-column prop="宿舍" label="宿舍" width="100" />
        <el-table-column prop="床号" label="床号" width="100" />
        <el-table-column prop="申请时间" label="申请时间" min-width="160" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="scope">
            <el-popconfirm 
              title="确定要删除这条记录吗？"
              @confirm="handleDeleteDelay(scope.row.序号)"
            >
              <template #reference>
                <el-button type="danger" size="small" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getStudentInfo, createDelay, getDelayList, deleteDelay, deleteDelayGet } from '@/api/modules/delay'

const sid = ref('')
const studentInfo = ref(null)
const delayRecords = ref([])
const loading = ref(false)
const submitting = ref(false)

// 获取班级代码，用于查询记录
const getClassCode = () => {
  const cookie = document.cookie.split('; ').find(row => row.startsWith('classCode='))
  return cookie ? cookie.split('=')[1] : ''
}

// 1. 获取学生信息
const fetchStudentInfo = async () => {
  if (!sid.value) return
  
  try {
    const response = await getStudentInfo({ sid: sid.value, classCode: getClassCode() })
    if (response.data) {
      studentInfo.value = response.data
    } else {
      studentInfo.value = null
      ElMessage.warning('未找到该学生信息')
    }
  } catch (error) {
    console.error('Fetch student info error:', error)
    studentInfo.value = null
    ElMessage.error('查询失败')
  }
}

// 2. 提交申请
const submitDelay = async () => {
  if (!sid.value) return
  
  submitting.value = true
  try {
    await createDelay({ sid: sid.value, classCode: getClassCode() })
    ElMessage.success('申请提交成功')
    sid.value = ''
    studentInfo.value = null
    // 刷新列表
    fetchDelayRecords()
  } catch (error) {
    console.error('Submit delay error:', error)
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
  }
}

// 3. 获取今日申请记录
const fetchDelayRecords = async () => {
  const classCode = getClassCode()
  if (!classCode) return

  loading.value = true
  try {
    const response = await getDelayList(classCode)
    delayRecords.value = response.data || []
  } catch (error) {
    console.error('Fetch delay records error:', error)
    ElMessage.error('获取记录失败')
  } finally {
    loading.value = false
  }
}

// 4. 删除记录
const handleDeleteDelay = async (id) => {
  try {
    await deleteDelay(id)
    ElMessage.success('删除成功')
    fetchDelayRecords()
  } catch (error) {
    console.error('Delete delay error:', error)
    // Fallback if it was a GET or POST
    try {
        await deleteDelayGet(id)
        ElMessage.success('删除成功')
        fetchDelayRecords()
    } catch (retryError) {
        ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchDelayRecords()
})
</script>

<style scoped>
.delay-application-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.box-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.student-info-display {
  margin-top: 20px;
}

.submit-action {
  margin-top: 20px;
  text-align: right;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .delay-application-container {
    padding: 10px;
  }
  
  .el-form-item {
    margin-right: 0;
    width: 100%;
  }
  
  .el-form-item :deep(.el-form-item__content) {
    width: 100%;
  }
}
</style>
