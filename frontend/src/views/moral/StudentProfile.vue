<template>
  <div class="profile-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="学生学号">
          <el-input v-model="filterForm.student_id" placeholder="输入学号" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleGenerate" :loading="generating" v-if="canGenerateProfile">生成画像</el-button>
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
      <el-tag v-if="profile.ai_used" type="success" effect="plain">AI 辅助生成</el-tag>

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

      <el-divider content-position="left">数据依据</el-divider>
      <el-row :gutter="12" class="evidence-grid">
        <el-col :xs="24" :sm="12" :md="6">
          <div class="evidence-card">
            <div class="evidence-label">日常表现</div>
            <div>正向 {{ analysis.daily_stats?.['1']?.count || 0 }} 次，{{ formatSigned(analysis.daily_stats?.['1']?.total || 0) }}</div>
            <div>需改进 {{ analysis.daily_stats?.['2']?.count || 0 }} 次，{{ formatSigned(analysis.daily_stats?.['2']?.total || 0) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="evidence-card">
            <div class="evidence-label">德育任务</div>
            <div>完成 {{ analysis.task_stats?.finished || 0 }}/{{ analysis.task_stats?.total || 0 }}</div>
            <div>得分 {{ formatSigned(analysis.task_stats?.score || 0) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="evidence-card">
            <div class="evidence-label">集体事件</div>
            <div>参与 {{ analysis.collective_stats?.collective_count || 0 }} 次</div>
            <div>得分 {{ formatSigned(analysis.collective_stats?.score || 0) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="evidence-card">
            <div class="evidence-label">处分记录</div>
            <div>{{ analysis.punishment_stats?.count || 0 }} 条</div>
            <div>扣分 {{ analysis.punishment_stats?.total_deduct || 0 }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-empty v-else description="请输入学号查询学生画像" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getStudentProfile,
  generateStudentProfile
} from '@/api/modules/moral'
import { useApiPermission } from '@/composables/useApiPermission'

const route = useRoute()

// API权限检查
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canGenerateProfile = ref(false)

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
const analysis = computed(() => {
  const source = profile.value?.data_source_summary || profile.value?.analysis
  if (!source) return {}
  if (typeof source === 'object') return source
  try {
    return JSON.parse(source)
  } catch {
    return {}
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
      // 设置学生基本信息
      student.value = {
        student_id: res.data.student_id,
        name: res.data.student_name,
        class_name: res.data.class_name,
        grade_name: res.data.grade_name
      }
      // 设置画像数据，处理评分格式
      profile.value = {
        ...res.data,
        moral_score: res.data.scores?.moral || 0,
        attitude_score: res.data.scores?.attitude || 0,
        social_score: res.data.scores?.social || 0,
        growth_score: res.data.scores?.growth || 0,
        generated_at: res.data.generated_at || new Date().toISOString(),
        data_source_summary: res.data.analysis,
        ai_used: res.data.ai_used
      }
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

const formatSigned = (score) => {
  const value = Number(score || 0)
  return `${value >= 0 ? '+' : ''}${value.toFixed(1).replace(/\.0$/, '')}`
}

// 页面加载时检查 query 参数
onMounted(async () => {
  await loadMyPermissions()
  canGenerateProfile.value = hasApiPermissionSync('/api/moral/profiles/student/generate')
  if (route.query.student_id) {
    filterForm.student_id = route.query.student_id
    handleSearch()
  }
})
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

.evidence-grid {
  row-gap: 12px;
}

.evidence-card {
  min-height: 92px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  color: #606266;
  line-height: 1.8;
  background: #fafafa;
}

.evidence-label {
  margin-bottom: 4px;
  font-weight: 600;
  color: #303133;
}
</style>
