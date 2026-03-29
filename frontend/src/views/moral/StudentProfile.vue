<template>
  <div class="profile-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="学生学号">
          <el-input v-model="filterForm.student_id" placeholder="输入学号" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleGenerate" :loading="generating">生成画像</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="profile" class="profile-card">
      <template #header>
        <div class="card-header">
          <span>学生画像</span>
          <el-tag :type="getRiskType(profile.risk_level)" v-if="profile.risk_level">
            风险等级: {{ profile.risk_level }}
          </el-tag>
        </div>
      </template>

      <el-descriptions :column="2" border>
        <el-descriptions-item label="学号">{{ student.student_id }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ student.name }}</el-descriptions-item>
        <el-descriptions-item label="班级">{{ student.class_name }}</el-descriptions-item>
        <el-descriptions-item label="生成时间">
          {{ formatDateTime(profile.generated_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">画像摘要</el-divider>
      <p class="profile-summary">{{ profile.profile_summary || '暂无画像摘要' }}</p>

      <el-divider content-position="left">画像标签</el-divider>
      <div class="tags-container">
        <el-tag
          v-for="tag in profileTags"
          :key="tag"
          :type="isStrengthTag(tag) ? 'success' : 'warning'"
          class="profile-tag"
        >
          {{ tag }}
        </el-tag>
        <span v-if="!profileTags || profileTags.length === 0" class="no-data">暂无标签</span>
      </div>

      <el-divider content-position="left">评分详情</el-divider>
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="score-card">
            <div class="score-label">品德评分</div>
            <el-progress
              type="circle"
              :percentage="profile.moral_score || 0"
              :color="getProgressColor(profile.moral_score)"
            />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="score-card">
            <div class="score-label">态度评分</div>
            <el-progress
              type="circle"
              :percentage="profile.attitude_score || 0"
              :color="getProgressColor(profile.attitude_score)"
            />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="score-card">
            <div class="score-label">社交评分</div>
            <el-progress
              type="circle"
              :percentage="profile.social_score || 0"
              :color="getProgressColor(profile.social_score)"
            />
          </div>
        </el-col>
        <el-col :span="6">
          <div class="score-card">
            <div class="score-label">成长评分</div>
            <el-progress
              type="circle"
              :percentage="profile.growth_score || 0"
              :color="getProgressColor(profile.growth_score)"
            />
          </div>
        </el-col>
      </el-row>

      <el-divider content-position="left" v-if="profile.suggestions">个性化建议</el-divider>
      <p v-if="profile.suggestions" class="suggestions">{{ profile.suggestions }}</p>
    </el-card>

    <el-empty v-else description="请输入学号查询学生画像" />
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getStudentProfile,
  generateStudentProfile
} from '@/api/modules/moral'

// 数据
const filterForm = reactive({
  student_id: ''
})
const profile = ref(null)
const student = ref({})
const generating = ref(false)

// 计算属性
const profileTags = computed(() => {
  if (!profile.value?.profile_tags) return []
  try {
    return typeof profile.value.profile_tags === 'string'
      ? JSON.parse(profile.value.profile_tags)
      : profile.value.profile_tags
  } catch {
    return []
  }
})

// 方法
const handleSearch = async () => {
  if (!filterForm.student_id) {
    ElMessage.warning('请输入学号')
    return
  }

  try {
    const res = await getStudentProfile(filterForm.student_id)
    if (res.success) {
      profile.value = res.data.profile
      student.value = res.data.student
    }
  } catch (error) {
    console.error('获取画像失败:', error)
    ElMessage.error('获取学生画像失败')
  }
}

const handleGenerate = async () => {
  if (!filterForm.student_id) {
    ElMessage.warning('请输入学号')
    return
  }

  generating.value = true
  try {
    const res = await generateStudentProfile(filterForm.student_id)
    if (res.success) {
      ElMessage.success('画像生成成功')
      profile.value = res.data
    }
  } catch (error) {
    console.error('生成画像失败:', error)
    ElMessage.error('生成画像失败')
  } finally {
    generating.value = false
  }
}

const isStrengthTag = (tag) => {
  const strengthTags = ['责任担当', '诚实守信', '乐于助人', '勤奋刻苦', '积极进取', '团结协作']
  return strengthTags.includes(tag)
}

const getRiskType = (level) => {
  const types = {
    'low': 'success',
    'medium': 'warning',
    'high': 'danger'
  }
  return types[level] || 'info'
}

const getProgressColor = (score) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

const formatDateTime = (datetime) => {
  if (!datetime) return '-'
  return new Date(datetime).toLocaleString('zh-CN')
}
</script>

<style scoped>
.profile-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profile-summary {
  line-height: 1.8;
  color: #606266;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.profile-tag {
  font-size: 14px;
}

.no-data {
  color: #909399;
}

.score-card {
  text-align: center;
  padding: 20px;
}

.score-card .score-label {
  margin-bottom: 15px;
  color: #606266;
}

.suggestions {
  line-height: 1.8;
  color: #606266;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
}
</style>