<template>
  <div class="evaluation-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="选择班级">
          <el-select v-model="filterForm.class_id" placeholder="选择班级" @change="fetchEvaluation">
            <el-option
              v-for="cls in classList"
              :key="cls.class_id"
              :label="cls.class_name"
              :value="cls.class_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="学期">
          <el-select v-model="filterForm.semester_id" placeholder="选择学期" @change="fetchEvaluation">
            <el-option
              v-for="sem in semesterList"
              :key="sem.semester_id"
              :label="sem.semester_name"
              :value="sem.semester_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleCalculate" v-if="canCalculateEvaluation">计算评价</el-button>
          <el-button @click="handleExport">导出报表</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-title">班级人数</div>
          <div class="stat-value">{{ stats.total_count || 0 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card success">
          <div class="stat-title">平均分</div>
          <div class="stat-value">{{ (stats.avg_score || 0).toFixed(1) }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card warning">
          <div class="stat-title">优秀人数</div>
          <div class="stat-value">{{ stats.excellent_count || 0 }}</div>
          <div class="stat-rate">
            优秀率: {{ stats.total_count ? ((stats.excellent_count / stats.total_count) * 100).toFixed(1) : 0 }}%
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card danger">
          <div class="stat-title">不合格人数</div>
          <div class="stat-value">{{ stats.fail_count || 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="table-card">
      <el-table :data="evaluationList" v-loading="loading" stripe @sort-change="handleSortChange">
        <el-table-column type="index" label="排名" width="60" />
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="student_name" label="姓名" width="100" />
        <el-table-column prop="total_score" label="总分" width="100" sortable="custom">
          <template #default="{ row }">
            <span :class="getScoreClass(row.total_score)">
              {{ row.total_score?.toFixed(1) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="等级" width="80">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleViewDetail(row)">查看详情</el-button>
            <el-button link type="primary" @click="handleViewProfile(row)" v-if="canViewProfile">画像</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 学生详情对话框 -->
    <el-dialog v-model="detailVisible" title="学生德育详情" width="960px" class="evaluation-detail-dialog">
      <div v-if="selectedStudent" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="学号">{{ selectedStudent.student_id }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ selectedStudent.student_name }}</el-descriptions-item>
          <el-descriptions-item label="班级">{{ selectedStudent.class_name }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ calculatedTotalScore.toFixed(1) }}</el-descriptions-item>
          <el-descriptions-item label="等级">{{ selectedStudent.level }}</el-descriptions-item>
          <el-descriptions-item label="学期">{{ currentSemesterName }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">分项得分</el-divider>

        <el-row :gutter="12" class="score-grid">
          <el-col v-for="item in scoreBreakdown" :key="item.key" :xs="12" :sm="8" :md="4">
            <div class="score-item compact">
              <div class="score-label">{{ item.label }}</div>
              <div class="score-value" :class="scoreClass(item.value, item.signed)">
                {{ formatScore(item.value, item.signed) }}
              </div>
            </div>
          </el-col>
        </el-row>

        <el-alert
          class="formula-alert"
          type="info"
          :closable="false"
          show-icon
          :title="scoreFormula"
        />

        <el-divider content-position="left">统计概览</el-divider>

        <el-row :gutter="12">
          <el-col :span="12">
            <el-card shadow="never" class="detail-stat-card">
              <template #header>积极事件</template>
              <p>次数: {{ detailData.daily_stats?.positive?.count || 0 }}</p>
              <p>得分: +{{ detailData.daily_stats?.positive?.total || 0 }}</p>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never" class="detail-stat-card">
              <template #header>消极事件</template>
              <p>次数: {{ detailData.daily_stats?.negative?.count || 0 }}</p>
              <p>扣分: -{{ detailData.daily_stats?.negative?.total || 0 }}</p>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never" class="detail-stat-card">
              <template #header>校级事件</template>
              <p>荣誉: {{ detailData.school_stats?.honors?.count || 0 }} 次，+{{ detailData.school_stats?.honors?.total || 0 }}</p>
              <p>扣分: {{ detailData.school_stats?.punishments?.count || 0 }} 次，-{{ detailData.school_stats?.punishments?.total || 0 }}</p>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never" class="detail-stat-card">
              <template #header>任务与集体</template>
              <p>任务: {{ detailData.task_stats?.finished_tasks || 0 }}/{{ detailData.task_stats?.total_tasks || 0 }}，+{{ detailData.task_stats?.total_score || 0 }}</p>
              <p>集体: {{ detailData.collective_stats?.participant_count || 0 }} 次，{{ formatScore(detailData.collective_stats?.total_score || 0, true) }}</p>
            </el-card>
          </el-col>
        </el-row>

        <el-divider content-position="left">近期记录</el-divider>
        <el-tabs model-value="daily">
          <el-tab-pane label="日常" name="daily">
            <el-table :data="detailData.recent_records?.daily || []" size="small" empty-text="暂无日常记录">
              <el-table-column prop="date" label="日期" width="110" />
              <el-table-column prop="title" label="事件" min-width="140" />
              <el-table-column prop="score" label="分值" width="80">
                <template #default="{ row }">{{ formatScore(row.score, true) }}</template>
              </el-table-column>
              <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="校级" name="school">
            <el-table :data="detailData.recent_records?.school || []" size="small" empty-text="暂无校级记录">
              <el-table-column prop="date" label="日期" width="110" />
              <el-table-column prop="title" label="事件" min-width="140" />
              <el-table-column prop="score" label="分值" width="80">
                <template #default="{ row }">{{ formatScore(row.score, true) }}</template>
              </el-table-column>
              <el-table-column prop="proof" label="凭证" min-width="180" show-overflow-tooltip />
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="集体" name="collective">
            <el-table :data="detailData.recent_records?.collective || []" size="small" empty-text="暂无集体事件">
              <el-table-column prop="date" label="日期" width="110" />
              <el-table-column prop="title" label="事件" min-width="140" />
              <el-table-column prop="event_type" label="类型" width="100" />
              <el-table-column prop="score" label="分值" width="80">
                <template #default="{ row }">{{ formatScore(row.score, true) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
          <el-tab-pane label="处分" name="punishment">
            <el-table :data="detailData.recent_records?.punishments || []" size="small" empty-text="暂无处分记录">
              <el-table-column prop="date" label="日期" width="110" />
              <el-table-column prop="title" label="等级" width="120" />
              <el-table-column prop="reason" label="原因" min-width="180" show-overflow-tooltip />
              <el-table-column prop="score" label="扣分" width="80" />
              <el-table-column label="状态" width="90">
                <template #default="{ row }">{{ row.is_revoked ? '已撤销' : '生效中' }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useApiPermission } from '@/composables/useApiPermission'
import {
  getClasses,
  getSemesters,
  getClassEvaluation,
  getStudentEvaluation,
  calculateEvaluation
} from '@/api/modules/moral'

const router = useRouter()
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canCalculateEvaluation = ref(false)
const canViewProfile = ref(false)

// 数据
const loading = ref(false)
const classList = ref([])
const semesterList = ref([])
const evaluationList = ref([])
const stats = ref({})

// 筛选
const filterForm = reactive({
  class_id: null,
  semester_id: null
})

// 详情
const detailVisible = ref(false)
const selectedStudent = ref(null)
const detailData = ref({})
const currentSemesterName = computed(() => {
  return semesterList.value.find(s => s.semester_id === filterForm.semester_id)?.semester_name || '-'
})
const scoreBreakdown = computed(() => [
  { key: 'base', label: '基础分', value: detailData.value.base_score || 80, signed: false },
  { key: 'daily', label: '日常', value: detailData.value.daily_score || 0, signed: true },
  { key: 'school', label: '校级', value: detailData.value.school_score || 0, signed: true },
  { key: 'task', label: '任务', value: detailData.value.task_score || 0, signed: true },
  { key: 'collective', label: '集体', value: detailData.value.collective_score || 0, signed: true },
  { key: 'punishment', label: '处分', value: -(detailData.value.punishment_score || 0), signed: true }
])
const calculatedTotalScore = computed(() => {
  const e = detailData.value
  return (e.base_score || 80) + (e.daily_score || 0) + (e.school_score || 0) + (e.task_score || 0) + (e.collective_score || 0) - (e.punishment_score || 0)
})
const scoreFormula = computed(() => {
  const e = detailData.value
  return `计算：${formatScore(e.base_score || 80)} ${formatScore(e.daily_score || 0, true)} ${formatScore(e.school_score || 0, true)} ${formatScore(e.task_score || 0, true)} ${formatScore(e.collective_score || 0, true)} ${formatScore(-(e.punishment_score || 0), true)} = ${formatScore(calculatedTotalScore.value)}`
})

// 方法
const fetchClassList = async () => {
  try {
    const res = await getClasses({ for_evaluation: 1 })
    if (res.success) {
      classList.value = res.data
      if (res.data.length > 0) {
        filterForm.class_id = res.data[0].class_id
      }
    }
  } catch (error) {
    console.error('获取班级列表失败:', error)
  }
}

const fetchSemesterList = async () => {
  try {
    const res = await getSemesters()
    if (res.success) {
      semesterList.value = res.data
      // 默认选择当前学期
      const current = res.data.find(s => s.status === 1)
      if (current) {
        filterForm.semester_id = current.semester_id
      }
    }
  } catch (error) {
    console.error('获取学期列表失败:', error)
  }
}

const fetchEvaluation = async () => {
  if (!filterForm.class_id) return

  loading.value = true
  try {
    const res = await getClassEvaluation(filterForm.class_id, filterForm.semester_id)
    if (res.success) {
      evaluationList.value = res.data.evaluations || []
      stats.value = res.data.stats || {}
    }
  } catch (error) {
    console.error('获取评价失败:', error)
  } finally {
    loading.value = false
  }
}

const handleCalculate = async () => {
  if (!filterForm.class_id) {
    ElMessage.warning('请先选择班级')
    return
  }

  try {
    loading.value = true
    const res = await calculateEvaluation({
      class_id: filterForm.class_id,
      semester_id: filterForm.semester_id
    })
    if (res.success) {
      ElMessage.success(res.message)
      fetchEvaluation()
    }
  } catch (error) {
    console.error('计算评价失败:', error)
  } finally {
    loading.value = false
  }
}

// 导出德育评价报表（支持筛选条件，导出全部数据）
const handleExport = async () => {
  if (!filterForm.class_id || !filterForm.semester_id) {
    ElMessage.warning('请先选择班级和学期')
    return
  }

  try {
    ElMessage.info('正在导出数据...')
    const res = await getClassEvaluation(filterForm.class_id, filterForm.semester_id)
    const exportData = res.data?.evaluations || []
    if (!res.success || exportData.length === 0) {
      ElMessage.warning('暂无数据可导出')
      return
    }

    const className = classList.value.find(c => c.class_id === filterForm.class_id)?.class_name || '班级'
    const semesterName = semesterList.value.find(s => s.semester_id === filterForm.semester_id)?.semester_name || '学期'

    // 构建 CSV 内容
    let csvContent = `德育评价报表 - ${className} - ${semesterName}\n\n`
    csvContent += `班级人数: ${stats.total_count || exportData.length}\n`
    csvContent += `平均分: ${(stats.avg_score || 0).toFixed(1)}\n`
    csvContent += `优秀人数: ${stats.excellent_count || 0}\n`
    csvContent += `不合格人数: ${stats.fail_count || 0}\n\n`
    csvContent += '排名,学号,姓名,总分,等级\n'

    // 按分数排序
    const sortedData = [...exportData].sort((a, b) => (b.total_score || 0) - (a.total_score || 0))
    sortedData.forEach((row, index) => {
      csvContent += `${index + 1},${row.student_id},${row.student_name},${row.total_score?.toFixed(1) || ''},${row.level || ''}\n`
    })

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `德育评价报表_${className}_${semesterName}.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success(`导出成功，共 ${exportData.length} 条记录`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

const handleSortChange = ({ prop, order }) => {
  if (prop === 'total_score') {
    evaluationList.value.sort((a, b) => {
      const diff = (a.total_score || 0) - (b.total_score || 0)
      return order === 'ascending' ? diff : -diff
    })
  }
}

const handleViewDetail = async (row) => {
  selectedStudent.value = row
  detailVisible.value = true

  try {
    const res = await getStudentEvaluation(row.student_id, filterForm.semester_id)
    if (res.success) {
      detailData.value = {
        total_score: res.data.evaluation?.total_score || row.total_score || 0,
        base_score: res.data.evaluation?.base_score || 80,
        daily_score: res.data.evaluation?.daily_score || 0,
        school_score: res.data.evaluation?.school_score || 0,
        task_score: res.data.evaluation?.task_score || 0,
        collective_score: res.data.evaluation?.collective_score || 0,
        punishment_score: res.data.evaluation?.punishment_score || 0,
        daily_stats: res.data.daily_stats,
        school_stats: res.data.school_stats,
        task_stats: res.data.task_stats,
        collective_stats: res.data.collective_stats,
        punishment_stats: res.data.punishment_stats,
        recent_records: res.data.recent_records
      }
    }
  } catch (error) {
    console.error('获取详情失败:', error)
  }
}

const handleViewProfile = (row) => {
  router.push({
    path: '/moral/profile',
    query: { student_id: row.student_id }
  })
}

const getScoreClass = (score) => {
  if (score >= 90) return 'score-excellent'
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

const getLevelType = (level) => {
  const types = {
    '优秀': 'success',
    '良好': 'primary',
    '合格': 'warning',
    '不合格': 'danger'
  }
  return types[level] || 'info'
}

const formatScore = (score, signed = false) => {
  const value = Number(score || 0)
  if (!signed) return value.toFixed(1).replace(/\.0$/, '')
  return `${value >= 0 ? '+' : ''}${value.toFixed(1).replace(/\.0$/, '')}`
}

const scoreClass = (score, signed = true) => {
  if (!signed) return ''
  return Number(score || 0) >= 0 ? 'positive' : 'negative'
}

// 生命周期
onMounted(async () => {
  await loadMyPermissions()
  canCalculateEvaluation.value = hasApiPermissionSync('/api/moral/evaluations/calculate')
  canViewProfile.value = hasApiPermissionSync('/api/moral/profiles/student')
  await Promise.all([fetchClassList(), fetchSemesterList()])
  if (filterForm.class_id) {
    fetchEvaluation()
  }
})
</script>

<style scoped>
.evaluation-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 10px 0;
}

.stat-card .stat-title {
  font-size: 14px;
  color: #909399;
}

.stat-card .stat-value {
  font-size: 28px;
  font-weight: bold;
  margin: 10px 0;
}

.stat-card .stat-rate {
  font-size: 12px;
  color: #909399;
}

.stat-card.success .stat-value {
  color: #67c23a;
}

.stat-card.warning .stat-value {
  color: #e6a23c;
}

.stat-card.danger .stat-value {
  color: #f56c6c;
}

.score-excellent {
  color: #67c23a;
  font-weight: bold;
}

.score-good {
  color: #409eff;
  font-weight: bold;
}

.score-pass {
  color: #e6a23c;
  font-weight: bold;
}

.score-fail {
  color: #f56c6c;
  font-weight: bold;
}

.detail-content {
  padding: 0 20px;
}

.score-grid {
  row-gap: 12px;
}

.score-item {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.score-item.compact {
  padding: 14px 10px;
  min-height: 86px;
}

.score-item .score-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 10px;
}

.score-item .score-value {
  font-size: 24px;
  font-weight: bold;
}

.score-item .score-value.positive {
  color: #67c23a;
}

.score-item .score-value.negative {
  color: #f56c6c;
}

.formula-alert {
  margin-top: 14px;
}

.detail-stat-card {
  margin-bottom: 12px;
}

.detail-stat-card p {
  margin: 6px 0;
  color: #606266;
}
</style>
