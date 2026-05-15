<template>
  <div class="profile-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item>
          <el-radio-group v-model="viewMode" @change="handleViewModeChange">
            <el-radio-button value="single">单人画像</el-radio-button>
            <el-radio-button value="list">画像列表</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="学生学号" v-if="viewMode === 'single'">
          <el-input v-model="filterForm.student_id" placeholder="输入学号" clearable />
        </el-form-item>
        <el-form-item label="班级" v-if="viewMode === 'list'">
          <el-select v-model="filterForm.class_id" placeholder="全部班级" clearable @change="handleListSearch" style="width: 180px">
            <el-option v-for="c in classList" :key="c.class_id" :label="c.class_name" :value="c.class_id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch" v-if="viewMode === 'single'">查询</el-button>
          <el-button @click="handleGenerate" :loading="generating" v-if="viewMode === 'single' && canGenerateProfile">生成画像</el-button>
        </el-form-item>
      </el-form>
      <el-alert
        v-if="generating && generationMessage"
        :title="generationMessage"
        type="info"
        show-icon
        :closable="false"
        class="generation-alert"
      />
    </el-card>

    <!-- 画像列表视图 -->
    <el-card v-if="viewMode === 'list'" class="list-card">
      <el-table :data="profileList" v-loading="listLoading" stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="student_name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column prop="grade_name" label="年级" width="100" />
        <el-table-column prop="profile_version" label="版本" width="80" />
        <el-table-column prop="generated_at" label="生成时间" width="160">
          <template #default="{ row }">
            {{ formatDateTimeLocal(row.generated_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="generated_by" label="生成人" width="100" />
        <el-table-column prop="risk_level" label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskType(row.risk_level)" v-if="row.risk_level">
              {{ row.risk_level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="评分" width="180">
          <template #default="{ row }">
            <span>品德{{ row.moral_score?.toFixed(0) || 0 }}</span>
            <span style="margin-left:8px">态度{{ row.attitude_score?.toFixed(0) || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="viewStudentProfile(row.student_id)">查看详情</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="listPage"
        v-model:page-size="listPageSize"
        :total="listTotal"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="handleListSearch"
        @current-change="handleListSearch"
        style="margin-top: 16px"
      />
    </el-card>

    <!-- 单人画像视图 -->
    <el-card v-if="viewMode === 'single' && profile" class="profile-card">
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
          {{ formatDateTimeLocal(profile.generated_at) }}
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
      <el-alert type="info" :closable="false" style="margin-bottom: 12px">
        <template #title>
          <span>数据范围：全部学期（一生一册模式）</span>
        </template>
      </el-alert>
      <el-row :gutter="12" class="evidence-grid">
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="evidence-card">
            <div class="evidence-label">点滴记录</div>
            <div>{{ analysis.moment_stats?.count || 0 }} 条</div>
            <div class="hint-text">教师记录的成长点滴</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="evidence-card">
            <div class="evidence-label">日常表现</div>
            <div>正向 {{ analysis.daily_stats?.['1']?.count || 0 }} 次，{{ formatSigned(analysis.daily_stats?.['1']?.total || 0) }}</div>
            <div>需改进 {{ analysis.daily_stats?.['2']?.count || 0 }} 次，{{ formatSigned(analysis.daily_stats?.['2']?.total || 0) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="evidence-card">
            <div class="evidence-label">校级事件</div>
            <div>正向 {{ analysis.school_stats?.['1']?.count || 0 }} 次，{{ formatSigned(analysis.school_stats?.['1']?.total || 0) }}</div>
            <div>需改进 {{ analysis.school_stats?.['2']?.count || 0 }} 次，{{ formatSigned(analysis.school_stats?.['2']?.total || 0) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="evidence-card">
            <div class="evidence-label">德育任务</div>
            <div>完成 {{ analysis.task_stats?.finished || 0 }}/{{ analysis.task_stats?.total || 0 }}</div>
            <div>得分 {{ formatSigned(analysis.task_stats?.score || 0) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="evidence-card">
            <div class="evidence-label">集体事件</div>
            <div>参与 {{ analysis.collective_stats?.collective_count || 0 }} 次</div>
            <div>得分 {{ formatSigned(analysis.collective_stats?.score || 0) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6" :lg="4">
          <div class="evidence-card">
            <div class="evidence-label">处分记录</div>
            <div>{{ analysis.punishment_stats?.count || 0 }} 条</div>
            <div>扣分 {{ analysis.punishment_stats?.total_deduct || 0 }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-empty v-if="viewMode === 'single' && !profile" description="请输入学号查询学生画像" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  getStudentProfile,
  startStudentProfileGeneration,
  getStudentProfileGenerationStatus,
  getProfileList,
  getClasses
} from '@/api/modules/moral'
import { useApiPermission } from '@/composables/useApiPermission'
import { formatDateTimeLocal } from '@/utils/time'

const route = useRoute()
const router = useRouter()

// API权限检查
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canGenerateProfile = ref(false)

// 视图模式
const viewMode = ref('single')  // 'single' 或 'list'

// 数据
const filterForm = reactive({
  student_id: '',
  class_id: null
})
const profile = ref(null)
const student = ref({})
const generating = ref(false)
const generationMessage = ref('')

// 画像列表数据
const profileList = ref([])
const listLoading = ref(false)
const listPage = ref(1)
const listPageSize = ref(20)
const listTotal = ref(0)
const classList = ref([])

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
const handleViewModeChange = () => {
  if (viewMode.value === 'list') {
    handleListSearch()
  }
}

const handleListSearch = async () => {
  listLoading.value = true
  try {
    const res = await getProfileList({
      class_id: filterForm.class_id || undefined,
      page: listPage.value,
      page_size: listPageSize.value
    })
    if (res.success) {
      profileList.value = res.data.profiles || []
      listTotal.value = res.data.total || 0
    }
  } catch (error) {
    console.error('获取画像列表失败:', error)
    ElMessage.error('获取画像列表失败')
  } finally {
    listLoading.value = false
  }
}

const viewStudentProfile = (studentId) => {
  viewMode.value = 'single'
  filterForm.student_id = studentId
  handleSearch()
}

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
  generationMessage.value = '正在提交画像生成任务...'
  try {
    const res = await startStudentProfileGeneration(filterForm.student_id)
    const jobId = res.data?.job_id
    if (!jobId) throw new Error('画像生成任务创建失败')
    generationMessage.value = 'AI 正在生成画像，页面会自动刷新结果...'
    ElMessage.info('画像生成任务已提交，请稍候')
    await pollProfileGeneration(jobId)
  } catch (error) {
    console.error('生成画像失败:', error)
    ElMessage.error(error.message || '生成画像失败')
  } finally {
    generating.value = false
    generationMessage.value = ''
  }
}

const applyGeneratedProfile = (data) => {
  student.value = {
    student_id: data.student_id,
    name: data.student_name,
    class_name: data.class_name,
    grade_name: data.grade_name
  }
  profile.value = {
    ...data,
    moral_score: data.scores?.moral || 0,
    attitude_score: data.scores?.attitude || 0,
    social_score: data.scores?.social || 0,
    growth_score: data.scores?.growth || 0,
    generated_at: data.generated_at || new Date().toISOString(),
    data_source_summary: data.analysis,
    ai_used: data.ai_used
  }
}

const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms))

const pollProfileGeneration = async (jobId) => {
  const maxAttempts = 120
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await wait(attempt < 3 ? 1200 : 2500)
    const res = await getStudentProfileGenerationStatus(jobId)
    const job = res.data || {}
    generationMessage.value = job.message || '正在生成学生画像...'
    if (job.status === 'success') {
      applyGeneratedProfile(job.data)
      ElMessage.success('画像生成成功')
      return
    }
    if (job.status === 'failed') {
      throw new Error(job.message || '画像生成失败')
    }
  }
  throw new Error('画像生成仍在处理中，请稍后查询学生画像')
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

const formatSigned = (score) => {
  const value = Number(score || 0)
  return `${value >= 0 ? '+' : ''}${value.toFixed(1).replace(/\.0$/, '')}`
}

// 页面加载时检查 query 参数
onMounted(async () => {
  await loadMyPermissions()
  canGenerateProfile.value = hasApiPermissionSync('/api/moral/profiles/student/{student_id}/generate')
  // 加载班级列表
  try {
    const res = await getClasses()
    if (res.success) {
      classList.value = res.data || []
    }
  } catch (e) {
    console.error('获取班级列表失败:', e)
  }
  // 根据路由参数切换视图
  if (route.query.list === '1') {
    viewMode.value = 'list'
    handleListSearch()
  } else if (route.query.student_id) {
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

.generation-alert {
  margin-top: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.profile-summary {
  line-height: 1.8;
  color: #606266;
  white-space: pre-line;
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
  white-space: pre-line;
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

.hint-text {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
