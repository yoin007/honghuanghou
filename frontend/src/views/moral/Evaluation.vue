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
          <el-button type="primary" @click="handleCalculate">计算评价</el-button>
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
            <el-button link type="primary" @click="handleViewProfile(row)">画像</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 学生详情对话框 -->
    <el-dialog v-model="detailVisible" title="学生德育详情" width="800px">
      <div v-if="selectedStudent" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="学号">{{ selectedStudent.student_id }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ selectedStudent.student_name }}</el-descriptions-item>
          <el-descriptions-item label="班级">{{ selectedStudent.class_name }}</el-descriptions-item>
          <el-descriptions-item label="总分">{{ selectedStudent.total_score?.toFixed(1) }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">分项得分</el-divider>

        <el-row :gutter="20">
          <el-col :span="8">
            <div class="score-item">
              <div class="score-label">基础分</div>
              <div class="score-value">60</div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="score-item">
              <div class="score-label">日常表现分</div>
              <div class="score-value" :class="detailData.daily_score >= 0 ? 'positive' : 'negative'">
                {{ detailData.daily_score >= 0 ? '+' : '' }}{{ detailData.daily_score }}
              </div>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="score-item">
              <div class="score-label">校级事件分</div>
              <div class="score-value" :class="detailData.school_score >= 0 ? 'positive' : 'negative'">
                {{ detailData.school_score >= 0 ? '+' : '' }}{{ detailData.school_score }}
              </div>
            </div>
          </el-col>
        </el-row>

        <el-divider content-position="left">日常表现统计</el-divider>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>积极事件</template>
              <p>次数: {{ detailData.daily_stats?.positive?.count || 0 }}</p>
              <p>得分: +{{ detailData.daily_stats?.positive?.total || 0 }}</p>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>消极事件</template>
              <p>次数: {{ detailData.daily_stats?.negative?.count || 0 }}</p>
              <p>扣分: -{{ detailData.daily_stats?.negative?.total || 0 }}</p>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getClasses,
  getSemesters,
  getClassEvaluation,
  getStudentEvaluation,
  calculateEvaluation
} from '@/api/modules/moral'

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

// 方法
const fetchClassList = async () => {
  try {
    const res = await getClasses()
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

const handleExport = () => {
  ElMessage.info('导出功能开发中')
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
        daily_score: res.data.evaluation?.daily_score || 0,
        school_score: res.data.evaluation?.school_score || 0,
        task_score: res.data.evaluation?.task_score || 0,
        daily_stats: res.data.daily_stats,
        school_stats: res.data.school_stats
      }
    }
  } catch (error) {
    console.error('获取详情失败:', error)
  }
}

const handleViewProfile = (row) => {
  ElMessage.info('学生画像功能开发中')
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

// 生命周期
onMounted(async () => {
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

.score-item {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
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
</style>