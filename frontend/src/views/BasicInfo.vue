<script setup>
import { ref, onMounted } from 'vue'
import { ElCard, ElDescriptions, ElDescriptionsItem, ElMessage, ElEmpty } from 'element-plus'
import api from '../utils/api'

const classInfo = ref(null)
const loading = ref(false)
const classCode = ref('')

const getClassCode = () => {
  const code = document.cookie.split('; ').find(row => row.startsWith('classCode='))
  return code ? code.split('=')[1] : null
}

const fetchClassInfo = async () => {
  const classCode = getClassCode()
  if (!classCode) {
    ElMessage.error('请先选择班级')
    return
  }

  loading.value = true
  try {
    const response = await api.get(`/api/class-info/${classCode}`)
    console.log('Class info response:', response.data)
    if (response.data && response.data.class_info) {
      classInfo.value = response.data.class_info
    } else {
      classInfo.value = null
      ElMessage.warning('暂无班级信息')
    }
  } catch (error) {
    console.error('Error fetching class info:', error)
    ElMessage.error('获取班级信息失败')
    classInfo.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchClassInfo()
  classCode.value = getClassCode()
})
</script>

<template>
  <div class="basic-info-container">
    <h2>{{ classCode ? `${classCode}基本信息` : '基本信息' }}</h2>
    <el-empty v-if="!loading && !classInfo" description="暂无班级信息" />
    <el-card v-else-if="classInfo" class="info-card">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="班级名称">{{ classInfo.className }}</el-descriptions-item>
        <el-descriptions-item label="班主任">{{ classInfo.classTeacher }}</el-descriptions-item>
        <el-descriptions-item label="班级人数">{{ classInfo.studentCount }} 人</el-descriptions-item>
        <el-descriptions-item label="成立时间">{{ classInfo.established }}</el-descriptions-item>
        <el-descriptions-item label="教室位置">{{ classInfo.location }}</el-descriptions-item>
        <el-descriptions-item label="班级口号">{{ classInfo.motto }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.basic-info-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
  color: #409EFF;
  text-align: center;
}

.info-card {
  margin-top: 20px;
}

:deep(.el-descriptions__label) {
  width: 120px;
  justify-content: flex-end;
  padding: 12px 16px;
}

:deep(.el-descriptions__content) {
  padding: 12px 16px;
}

:deep(.el-descriptions__body) {
  background-color: #fff;
}

:deep(.el-descriptions__label.el-descriptions__cell) {
  background-color: #f5f7fa;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .basic-info-container {
    padding: 10px;
  }

  h2 {
    font-size: 1.2rem;
    margin-bottom: 15px;
  }

  /* 调整 descriptions 在移动端的显示 */
  :deep(.el-descriptions__label) {
    width: 80px; /* 减小标签宽度 */
    padding: 8px 10px;
    font-size: 14px;
  }

  :deep(.el-descriptions__content) {
    padding: 8px 10px;
    font-size: 14px;
  }
}
</style>
