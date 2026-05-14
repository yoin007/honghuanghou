<template>
  <div class="semester-evaluation-page">
    <!-- 筛选和操作区 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="学期">
          <el-select v-model="filterForm.semester_id" placeholder="选择学期" style="width: 150px">
            <el-option v-for="sem in semesterList" :key="sem.semester_id" :label="sem.semester_name" :value="sem.semester_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="年级">
          <el-select v-model="filterForm.grade_id" placeholder="选择年级" clearable style="width: 150px" @change="handleGradeChange">
            <el-option v-for="g in gradeList" :key="g.grade_id" :label="g.grade_name" :value="g.grade_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="filterForm.class_id" placeholder="选择班级" clearable filterable style="width: 150px">
            <el-option v-for="cls in classList" :key="cls.class_id" :label="cls.class_name" :value="cls.class_id" />
          </el-select>
        </el-form-item>
        <el-form-item class="action-btns">
          <el-button type="primary" @click="handleSearch" :loading="searchLoading">
            查询评价
          </el-button>
          <el-button type="info" @click="showSingleGenerateDialog">
            单学生生成
          </el-button>
          <el-button type="success" @click="handleBatchGenerate" :loading="generateLoading" :disabled="!canBatchGenerate">
            批量生成
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 单学生生成对话框 -->
    <el-dialog v-model="singleGenerateDialog.visible" title="单学生评价生成" width="500px">
      <el-form label-width="80px">
        <el-form-item label="选择班级">
          <el-select v-model="singleGenerateDialog.class_id" placeholder="请选择班级" filterable @change="loadStudentsForClass">
            <el-option v-for="cls in classList" :key="cls.class_id" :label="cls.class_name" :value="cls.class_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择学生">
          <el-select v-model="singleGenerateDialog.student_id" placeholder="请选择学生" filterable :disabled="!singleGenerateDialog.class_id">
            <el-option v-for="stu in singleGenerateDialog.studentList" :key="stu.student_id" :label="`${stu.name} (${stu.student_id})`" :value="stu.student_id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="singleGenerateDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSingleGenerate" :loading="singleGenerateDialog.loading" :disabled="!singleGenerateDialog.student_id">
          生成评价
        </el-button>
      </template>
    </el-dialog>

    <!-- 生成进度提示 -->
    <el-card v-if="generateProgress.show" class="progress-card">
      <el-progress :percentage="generateProgress.percentage" :status="generateProgress.status" />
      <div class="progress-text">
        <span v-if="generateProgress.message">{{ generateProgress.message }}</span>
        <span v-if="generateProgress.current_student_name">
          当前：{{ generateProgress.current_student_name }}
        </span>
        已完成 {{ generateProgress.success_count }} / {{ generateProgress.total_count }}
        <span v-if="generateProgress.error_count > 0" class="error-text">
          (失败 {{ generateProgress.error_count }} 个)
        </span>
      </div>
      <el-alert v-if="generateProgress.errors.length > 0" type="warning" :closable="false">
        <template #title>错误列表（前10条）</template>
        <ul class="error-list">
          <li v-for="err in generateProgress.errors" :key="err">{{ err }}</li>
        </ul>
      </el-alert>
    </el-card>

    <!-- 评价列表 -->
    <el-card class="list-card">
      <el-table :data="evaluationList" v-loading="tableLoading" stripe>
        <el-table-column prop="student_id" label="学号" min-width="100" />
        <el-table-column prop="name" label="姓名" min-width="80" />
        <el-table-column prop="class_name" label="班级" min-width="120" />
        <el-table-column prop="total_score" label="德育总分" width="90">
          <template #default="{ row }">
            <span :class="getScoreClass(row.total_score)">{{ row.total_score }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="等级" width="80">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="generated_at" label="生成时间" width="150">
          <template #default="{ row }">
            {{ formatDateTime(row.generated_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="ai_generated_at" label="AI总结" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.ai_generated_at" type="success" size="small">已生成</el-tag>
            <el-tag v-else type="info" size="small">无</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleViewDetail(row)">详情</el-button>
            <el-button type="warning" link @click="handleGenerateEvaluation(row)">生成评价</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchEvaluationList"
        @current-change="fetchEvaluationList"
        class="pagination"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="学期末德育评价详情" width="800px" destroy-on-close>
      <div v-if="detailDialog.data" class="evaluation-detail">
        <!-- 基本信息 -->
        <el-descriptions title="基本信息" :column="4" border>
          <el-descriptions-item label="学号">{{ detailDialog.data.student_id }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ detailDialog.data.name }}</el-descriptions-item>
          <el-descriptions-item label="班级">{{ detailDialog.data.class_name }}</el-descriptions-item>
          <el-descriptions-item label="学期">{{ detailDialog.data.semester_name }}</el-descriptions-item>
        </el-descriptions>

        <!-- 评价结果 -->
        <el-descriptions title="评价结果" :column="4" border class="mt-20">
          <el-descriptions-item label="德育总分">
            <span :class="getScoreClass(detailDialog.data.total_score)" style="font-weight: bold">
              {{ detailDialog.data.total_score }} 分
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="评价等级">
            <el-tag :type="getLevelType(detailDialog.data.level)">{{ detailDialog.data.level }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 分项得分 -->
        <el-card shadow="never" class="mt-20">
          <template #header><strong>分项得分明细</strong></template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="基础分">{{ detailDialog.data.score_details?.base_score || 0 }} 分</el-descriptions-item>
            <el-descriptions-item label="日常表现分">{{ detailDialog.data.score_details?.daily_score || 0 }} 分</el-descriptions-item>
            <el-descriptions-item label="校级事件分">{{ detailDialog.data.score_details?.school_score || 0 }} 分</el-descriptions-item>
            <el-descriptions-item label="任务完成分">{{ detailDialog.data.score_details?.task_score || 0 }} 分</el-descriptions-item>
            <el-descriptions-item label="集体事件分">{{ detailDialog.data.score_details?.collective_score || 0 }} 分</el-descriptions-item>
            <el-descriptions-item label="处分扣分">{{ detailDialog.data.score_details?.punishment_score || 0 }} 分</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- 统计数据 -->
        <el-card shadow="never" class="mt-20">
          <template #header><strong>数据支撑</strong></template>
          <el-descriptions :column="4" border>
            <el-descriptions-item label="正向记录">{{ detailDialog.data.statistics?.positive_count || 0 }} 次</el-descriptions-item>
            <el-descriptions-item label="需改进">{{ detailDialog.data.statistics?.negative_count || 0 }} 次</el-descriptions-item>
            <el-descriptions-item label="校级荣誉">{{ detailDialog.data.statistics?.honor_count || 0 }} 次</el-descriptions-item>
            <el-descriptions-item label="处分记录">{{ detailDialog.data.statistics?.punishment_count || 0 }} 条</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <!-- AI 总结 -->
        <el-card v-if="detailDialog.data.ai_summary" shadow="never" class="mt-20 ai-summary-card">
          <template #header><strong>学期末总结与建议（AI生成）</strong></template>
          <div class="ai-section">
            <div class="ai-label">【学生学期德育总结】</div>
            <div class="ai-content">{{ detailDialog.data.ai_summary?.summary || '暂无' }}</div>
          </div>
          <div class="ai-section">
            <div class="ai-label">【优势与亮点】</div>
            <div class="ai-content">{{ detailDialog.data.ai_summary?.strengths || '暂无' }}</div>
          </div>
          <div class="ai-section">
            <div class="ai-label">【需提升方向】</div>
            <div class="ai-content">{{ detailDialog.data.ai_summary?.improvements || '暂无' }}</div>
          </div>
          <el-divider content-position="left">成长建议</el-divider>
          <div class="ai-section" v-if="detailDialog.data.ai_summary?.suggestions">
            <div class="suggestions-grid">
              <div class="suggestion-item">
                <div class="suggestion-label">📋 学生建议</div>
                <div class="suggestion-content">{{ detailDialog.data.ai_summary?.suggestions?.student || '暂无' }}</div>
              </div>
              <div class="suggestion-item">
                <div class="suggestion-label">👨‍🏫 班主任建议</div>
                <div class="suggestion-content">{{ detailDialog.data.ai_summary?.suggestions?.teacher || '暂无' }}</div>
              </div>
              <div class="suggestion-item">
                <div class="suggestion-label">👨‍👩‍👧 家长建议</div>
                <div class="suggestion-content">{{ detailDialog.data.ai_summary?.suggestions?.parent || '暂无' }}</div>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 关键事件 -->
        <el-card shadow="never" class="mt-20">
          <template #header><strong>近期关键事件</strong></template>
          <el-table :data="detailDialog.data.key_events" stripe size="small" v-if="detailDialog.data.key_events?.length">
            <el-table-column prop="date" label="日期" width="100">
              <template #default="{ row }">{{ row.date || '—' }}</template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="getEventTypeTag(row.type)" size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="事件" min-width="180">
              <template #default="{ row }">{{ row.title || '—' }}</template>
            </el-table-column>
            <el-table-column prop="score" label="分值" width="70" align="center">
              <template #default="{ row }">
                <span :class="row.score >= 0 ? 'score-positive' : 'score-negative'">
                  {{ row.score >= 0 ? '+' : '' }}{{ row.score || 0 }}
                </span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="本学期暂有相关记录" :image-size="60" />
        </el-card>

        <!-- 签字区 -->
        <el-card shadow="never" class="mt-20 signature-card">
          <template #header><strong>签字确认区</strong></template>
          <div class="signature-grid">
            <div class="signature-item">
              <span class="signature-label">学生签字：</span>
              <span class="signature-space"></span>
            </div>
            <div class="signature-item">
              <span class="signature-label">家长签字：</span>
              <span class="signature-space"></span>
            </div>
            <div class="signature-item">
              <span class="signature-label">班主任签字：</span>
              <span class="signature-space"></span>
            </div>
            <div class="signature-item">
              <span class="signature-label">日期：</span>
              <span class="signature-space"></span>
            </div>
          </div>
        </el-card>
      </div>
      <template #footer>
        <el-button type="warning" @click="handlePrintFromDetail">打印 PDF</el-button>
        <el-button @click="detailDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import moralApi from '@/api/modules/moral'

// 筛选表单
const filterForm = reactive({
  semester_id: null,
  grade_id: null,
  class_id: null,
})

// 数据列表
const semesterList = ref([])
const gradeList = ref([])
const classList = ref([])
const evaluationList = ref([])

// 加载状态
const searchLoading = ref(false)
const tableLoading = ref(false)
const generateLoading = ref(false)

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0,
})

// 生成进度
const generateProgress = reactive({
  show: false,
  percentage: 0,
  status: '',
  success_count: 0,
  error_count: 0,
  total_count: 0,
  message: '',
  current_student_name: '',
  errors: [],
})

// 详情对话框
const detailDialog = reactive({
  visible: false,
  data: null,
})

// 单学生生成对话框
const singleGenerateDialog = reactive({
  visible: false,
  class_id: null,
  student_id: null,
  studentList: [],
  loading: false,
})

// 计算是否可以批量生成
const canBatchGenerate = computed(() => {
  return filterForm.grade_id || filterForm.class_id
})

// 初始化
onMounted(async () => {
  await fetchSemesters()
  await fetchGrades()
  await fetchEvaluationList()
})

// 获取学期列表
async function fetchSemesters() {
  try {
    const res = await moralApi.getSemesters()
    if (res?.success) {
      semesterList.value = res.data || []
      // 默认选择当前学期
      const current = semesterList.value.find(s => s.status === 1)
      if (current) {
        filterForm.semester_id = current.semester_id
      }
    }
  } catch (e) {
    console.error('获取学期失败:', e)
  }
}

// 获取年级列表
async function fetchGrades() {
  try {
    const res = await moralApi.getGrades()
    if (res?.success) {
      gradeList.value = res.data || []
    }
  } catch (e) {
    console.error('获取年级失败:', e)
  }
}

// 年级变化时更新班级列表
async function handleGradeChange() {
  filterForm.class_id = null
  classList.value = []
  if (filterForm.grade_id) {
    try {
      const res = await moralApi.getClasses({ grade_id: filterForm.grade_id })
      if (res?.success) {
        classList.value = res.data || []
      }
    } catch (e) {
      console.error('获取班级失败:', e)
    }
  }
}

// 查询评价列表
async function fetchEvaluationList() {
  tableLoading.value = true
  try {
    const params = {
      semester_id: filterForm.semester_id,
      grade_id: filterForm.grade_id,
      class_id: filterForm.class_id,
      page: pagination.page,
      pageSize: pagination.pageSize,
    }
    const res = await moralApi.getSemesterEvaluationList(params)
    if (res?.success) {
      evaluationList.value = res.data.list || []
      pagination.total = res.data.total || 0
    }
  } catch (e) {
    console.error('查询失败:', e)
    ElMessage.error('查询失败：' + (e.response?.data?.detail || '未知错误'))
  } finally {
    tableLoading.value = false
  }
}

// 搜索按钮
function handleSearch() {
  pagination.page = 1
  fetchEvaluationList()
}

// 批量生成
async function handleBatchGenerate() {
  const target = filterForm.class_id ? '本班' : '本年级'
  try {
    await ElMessageBox.confirm(
      `确定要为${target}学生批量生成学期末评价吗？生成过程可能需要几分钟。`,
      '批量生成确认',
      { type: 'warning' }
    )

    generateLoading.value = true
    generateProgress.show = true
    generateProgress.percentage = 0
    generateProgress.status = ''
    generateProgress.message = '正在提交批量生成任务...'
    generateProgress.current_student_name = ''
    generateProgress.errors = []
    generateProgress.success_count = 0
    generateProgress.error_count = 0
    generateProgress.total_count = 0

    const params = {
      semester_id: filterForm.semester_id,
      generate_ai: true,
    }
    if (filterForm.class_id) {
      params.class_id = filterForm.class_id
    } else {
      params.grade_id = filterForm.grade_id
    }

    const res = await moralApi.batchGenerateSemesterEvaluations(params)
    if (res?.success) {
      const jobId = res.data?.job_id
      generateProgress.total_count = res.data?.total_count || 0
      generateProgress.message = res.message || '批量生成任务已提交'
      if (jobId) {
        ElMessage.info('批量生成任务已提交，正在后台处理')
        await pollBatchGenerate(jobId)
      } else {
        const data = res.data || {}
        generateProgress.success_count = data.success_count || 0
        generateProgress.error_count = data.error_count || 0
        generateProgress.total_count = data.total_count || 0
        generateProgress.errors = data.errors || []
        generateProgress.percentage = 100
        generateProgress.status = data.error_count > 0 ? 'warning' : 'success'
      }
      fetchEvaluationList()
    }
  } catch (e) {
    if (e !== 'cancel') {
      console.error('批量生成失败:', e)
      ElMessage.error('批量生成失败：' + (e.response?.data?.detail || '未知错误'))
    }
  } finally {
    generateLoading.value = false
  }
}

const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms))

async function pollBatchGenerate(jobId) {
  const maxAttempts = 360
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await wait(attempt < 3 ? 1000 : 2000)
    const res = await moralApi.getSemesterEvaluationBatchStatus(jobId)
    const data = res?.data || {}
    generateProgress.success_count = data.success_count || 0
    generateProgress.error_count = data.error_count || 0
    generateProgress.total_count = data.total_count || generateProgress.total_count || 0
    generateProgress.errors = data.errors || []
    generateProgress.percentage = data.progress || 0
    generateProgress.message = data.message || '正在批量生成...'
    generateProgress.current_student_name = data.current_student_name || ''

    if (data.status === 'success' || data.status === 'partial_success' || data.status === 'failed') {
      generateProgress.percentage = 100
      generateProgress.status = data.error_count > 0 ? 'warning' : 'success'
      generateProgress.current_student_name = ''
      ElMessage.success(`批量生成完成：成功 ${data.success_count || 0} 个`)
      return
    }
  }
  generateProgress.status = 'warning'
  throw new Error('批量生成仍在后台处理中，请稍后刷新列表查看')
}

// 查看详情
async function handleViewDetail(row) {
  try {
    const res = await moralApi.getSemesterEvaluationDetail(row.record_id)
    if (res?.success) {
      detailDialog.data = res.data
      detailDialog.visible = true
    }
  } catch (e) {
    console.error('获取详情失败:', e)
    ElMessage.error('获取详情失败')
  }
}

// 生成单学生评价（包含AI总结）
async function handleGenerateEvaluation(row) {
  try {
    const studentName = row.name || row.student_id
    const action = row.generated_at ? '重新生成' : '生成'

    await ElMessageBox.confirm(
      `确认${action}学生「${studentName}」的学期末德育评价？${row.generated_at ? '将覆盖已有评价数据。' : ''}`,
      '确认操作',
      { type: 'warning' }
    )

    ElMessage.info(`正在${action}评价...`)
    const res = await moralApi.generateSemesterEvaluation(row.student_id, filterForm.semester_id, true)
    if (res?.success) {
      ElMessage.success(`${action}成功`)
      fetchEvaluationList()
    }
  } catch (e) {
    if (e !== 'cancel') {
      console.error('生成失败:', e)
      ElMessage.error('生成失败：' + (e.response?.data?.detail || '未知错误'))
    }
  }
}

// 显示单学生生成对话框
function showSingleGenerateDialog() {
  if (!filterForm.semester_id) {
    ElMessage.warning('请先选择学期')
    return
  }
  singleGenerateDialog.visible = true
  singleGenerateDialog.class_id = filterForm.class_id || null
  singleGenerateDialog.student_id = null
  singleGenerateDialog.studentList = []
  if (singleGenerateDialog.class_id) {
    loadStudentsForClass()
  }
}

// 加载班级学生列表
async function loadStudentsForClass() {
  if (!singleGenerateDialog.class_id) {
    singleGenerateDialog.studentList = []
    return
  }
  try {
    const res = await moralApi.getStudents({ class_id: singleGenerateDialog.class_id, status: '在校', page_size: 100 })
    if (res?.success) {
      singleGenerateDialog.studentList = res.data?.items || []
    }
  } catch (e) {
    console.error('获取学生列表失败:', e)
    singleGenerateDialog.studentList = []
  }
}

// 执行单学生生成
async function handleSingleGenerate() {
  if (!singleGenerateDialog.student_id) {
    ElMessage.warning('请选择学生')
    return
  }
  try {
    singleGenerateDialog.loading = true
    const stu = singleGenerateDialog.studentList.find(s => s.student_id === singleGenerateDialog.student_id)
    const studentName = stu?.name || singleGenerateDialog.student_id

    ElMessage.info(`正在生成学生「${studentName}」的评价...`)
    const res = await moralApi.generateSemesterEvaluation(singleGenerateDialog.student_id, filterForm.semester_id, true)
    if (res?.success) {
      ElMessage.success('生成成功')
      singleGenerateDialog.visible = false
      // 刷新列表
      if (filterForm.class_id === singleGenerateDialog.class_id) {
        fetchEvaluationList()
      }
    }
  } catch (e) {
    console.error('生成失败:', e)
    ElMessage.error('生成失败：' + (e.response?.data?.detail || '未知错误'))
  } finally {
    singleGenerateDialog.loading = false
  }
}

// 打印 PDF（从详情对话框）
function handlePrintFromDetail() {
  document.body.classList.add('print-evaluation')
  setTimeout(() => {
    window.print()
    document.body.classList.remove('print-evaluation')
  }, 100)
}

// 格式化日期时间
function formatDateTime(dt) {
  if (!dt) return ''
  return dt.substring(0, 16).replace('T', ' ')
}

// 分数样式
function getScoreClass(score) {
  if (score >= 90) return 'score-excellent'
  if (score >= 75) return 'score-good'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

// 等级标签类型
function getLevelType(level) {
  const map = {
    '优秀': 'success',
    '良好': 'primary',
    '合格': 'info',
    '不合格': 'danger',
  }
  return map[level] || 'info'
}

// 事件类型标签
function getEventTypeTag(type) {
  const map = {
    '日常表现': 'primary',
    '校级事件': 'success',
    '处分': 'danger',
    '集体活动': 'warning',
  }
  return map[type] || 'info'
}
</script>

<style scoped>
.semester-evaluation-page {
  padding: 20px;
}

.filter-card,
.list-card,
.progress-card {
  margin-bottom: 16px;
}

.action-btns {
  margin-left: 20px;
}

.progress-card .progress-text {
  margin-top: 10px;
  text-align: center;
}

.progress-card .error-text {
  color: #f56c6c;
}

.progress-card .error-list {
  margin: 10px 0;
  padding-left: 20px;
  font-size: 12px;
}

.progress-card .error-list li {
  margin-bottom: 4px;
}

.pagination {
  margin-top: 16px;
  justify-content: flex-end;
}

.evaluation-detail .mt-20 {
  margin-top: 20px;
}

.evaluation-detail .score-excellent {
  color: #67c23a;
  font-weight: bold;
}

.evaluation-detail .score-good {
  color: #409eff;
  font-weight: bold;
}

.evaluation-detail .score-pass {
  color: #909399;
}

.evaluation-detail .score-fail {
  color: #f56c6c;
  font-weight: bold;
}

.evaluation-detail .score-positive {
  color: #67c23a;
}

.evaluation-detail .score-negative {
  color: #f56c6c;
}

.ai-summary-card .ai-section {
  margin-bottom: 16px;
}

.ai-summary-card .ai-label {
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
  font-size: 14px;
}

.ai-summary-card .ai-content {
  line-height: 1.8;
  text-align: justify;
  color: #606266;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.ai-summary-card .suggestions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.ai-summary-card .suggestion-item {
  padding: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  border-radius: 8px;
  border: 1px solid #dcdfe6;
}

.ai-summary-card .suggestion-label {
  font-weight: bold;
  display: block;
  margin-bottom: 10px;
  color: #409eff;
  font-size: 14px;
}

.ai-summary-card .suggestion-content {
  line-height: 1.6;
  color: #606266;
  font-size: 13px;
}

.signature-card .signature-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.signature-card .signature-item {
  display: flex;
  align-items: center;
}

.signature-card .signature-label {
  font-weight: bold;
}

.signature-card .signature-space {
  flex: 1;
  border-bottom: 1px solid #dcdfe6;
  margin-left: 10px;
  height: 30px;
}

/* 打印样式 */
@media print {
  body.print-evaluation .semester-evaluation-page {
    padding: 0;
  }

  body.print-evaluation .filter-card,
  body.print-evaluation .list-card,
  body.print-evaluation .progress-card,
  body.print-evaluation .el-dialog__footer {
    display: none !important;
  }

  body.print-evaluation .el-dialog {
    width: 100% !important;
    margin: 0 !important;
  }

  body.print-evaluation .el-dialog__header {
    display: none !important;
  }

  body.print-evaluation .el-dialog__body {
    padding: 20px !important;
  }

  body.print-evaluation .el-overlay {
    display: none !important;
  }
}
</style>
