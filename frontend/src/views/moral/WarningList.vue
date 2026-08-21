<template>
  <div class="warning-list-page">
    <div class="page-header">
      <h2>德育预警管理</h2>
      <p class="subtitle">实时跟踪学生德育预警状态，自动消除与手动处置相结合</p>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div class="stat-card active" :class="{ active: activeTab === 'active' }" @click="switchTab('active')">
        <div class="stat-value">{{ summary.active_count || 0 }}</div>
        <div class="stat-label">活跃预警</div>
      </div>
      <div class="stat-card resolved" :class="{ active: activeTab === 'resolved' }" @click="switchTab('resolved')">
        <div class="stat-value">{{ summary.resolved_count || 0 }}</div>
        <div class="stat-label">已消除</div>
      </div>
      <div class="stat-card total" :class="{ active: activeTab === 'all' }" @click="switchTab('all')">
        <div class="stat-value">{{ summary.total || 0 }}</div>
        <div class="stat-label">累计预警</div>
      </div>
    </div>

    <!-- 筛选区 -->
    <div class="filter-bar">
      <div class="filter-left">
        <el-select v-model="filter.grade_id" placeholder="全部年级" clearable size="default" @change="handleFilter" style="width: 140px">
          <el-option v-for="g in grades" :key="g.grade_id" :label="g.grade_name" :value="g.grade_id" />
        </el-select>
        <el-select v-model="filter.class_id" placeholder="全部班级" clearable size="default" @change="handleFilter" style="width: 160px">
          <el-option v-for="c in filteredClasses" :key="c.class_id" :label="c.class_name" :value="c.class_id" />
        </el-select>
        <el-select v-model="filter.warning_level" placeholder="全部级别" clearable size="default" @change="handleFilter" style="width: 140px">
          <el-option label="一般预警" value="warning" />
          <el-option label="严重预警" value="error" />
          <el-option label="累进预警" value="escalation_warning" />
          <el-option label="通报批评" value="escalation_criticism" />
          <el-option label="记过处分" value="escalation_demerit" />
          <el-option label="留校察看" value="escalation_probation" />
        </el-select>
        <el-select v-model="filter.handle_status" placeholder="处置状态" clearable size="default" @change="handleFilter" style="width: 130px">
          <el-option label="未处置" value="unhandled" />
          <el-option label="已处置" value="handled" />
        </el-select>
        <el-select v-model="filter.days" placeholder="时间范围" size="default" @change="handleFilter" style="width: 130px">
          <el-option label="最近7天" :value="7" />
          <el-option label="最近30天" :value="30" />
          <el-option label="最近90天" :value="90" />
          <el-option label="本学期" :value="365" />
        </el-select>
      </div>
      <div class="filter-right">
        <el-button v-if="activeTab === 'active'" type="primary" plain @click="handleBatchMarkRead">全部已读</el-button>
        <el-button v-if="activeTab === 'active'" type="danger" plain @click="handleBatchResolve">批量消除</el-button>
        <el-button @click="fetchData">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <el-table :data="tableData" v-loading="loading" stripe style="width: 100%">
        <el-table-column prop="student_name" label="学生" width="100">
          <template #default="{ row }">
            <div class="student-cell">
              <strong>{{ row.student_name }}</strong>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column prop="grade_name" label="年级" width="100" />
        <el-table-column label="预警级别" width="180">
          <template #default="{ row }">
            <div class="level-cell">
              <el-tag :type="levelTagType(row.warning_level, row.trigger_type)" size="small" effect="dark">
                {{ formatWarningLevel(row.warning_level) }}
              </el-tag>
              <span class="level-source">{{ triggerSourceLabel(row.trigger_type) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="处置状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="handleStatusTagType(row)" effect="light" size="small">
              {{ handleStatusLabel(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'danger' : 'success'" effect="light" size="small">
              {{ row.status === 'active' ? '活跃' : '已消除' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="已读" width="80" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.is_read" :size="18" color="#10b981"><CircleCheck /></el-icon>
            <el-tag v-else type="danger" size="small" effect="dark">未读</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="预警内容" min-width="280" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="message-text">{{ row.message }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="产生时间" width="170" />
        <el-table-column prop="resolved_at" label="消除时间" width="170">
          <template #default="{ row }">
            <span v-if="row.resolved_at">{{ row.resolved_at }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button v-if="!row.is_read" link type="primary" size="small" @click="handleMarkRead(row)">已读</el-button>
              <el-button link type="success" size="small" @click="openHandleDialog(row)">处置</el-button>
              <el-button v-if="row.status === 'active'" link type="danger" size="small" @click="handleResolve(row)">消除</el-button>
              <el-button link type="info" size="small" @click="showDetail(row)">详情</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-bar">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :page-sizes="[20, 50, 100]"
        :total="pagination.total"
        layout="total, sizes, prev, pager, next, jumper"
        background
        @size-change="handlePageChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="预警详情" width="520px">
      <div v-if="currentWarning" class="detail-content">
        <div class="detail-row">
          <span class="label">学生：</span>
          <span>{{ currentWarning.student_name }}（{{ currentWarning.student_id }}）</span>
        </div>
        <div class="detail-row">
          <span class="label">班级：</span>
          <span>{{ currentWarning.grade_name }} {{ currentWarning.class_name }}</span>
        </div>
        <div class="detail-row">
          <span class="label">预警级别：</span>
          <div>
            <el-tag :type="levelTagType(currentWarning.warning_level, currentWarning.trigger_type)" size="small" effect="dark">
              {{ formatWarningLevel(currentWarning.warning_level) }}
            </el-tag>
            <div class="detail-hint">{{ triggerSourceLabel(currentWarning.trigger_type) }}</div>
          </div>
        </div>
        <div class="detail-row">
          <span class="label">状态：</span>
          <el-tag :type="currentWarning.status === 'active' ? 'danger' : 'success'" effect="light" size="small">
            {{ currentWarning.status === 'active' ? '活跃' : '已消除' }}
          </el-tag>
        </div>
        <div class="detail-row">
          <span class="label">产生时间：</span>
          <span>{{ currentWarning.created_at }}</span>
        </div>
        <div class="detail-row" v-if="currentWarning.resolved_at">
          <span class="label">消除时间：</span>
          <span>{{ currentWarning.resolved_at }}</span>
        </div>
        <div class="detail-row" v-if="currentWarning.resolved_reason">
          <span class="label">消除原因：</span>
          <span>{{ resolveReasonLabel(currentWarning.resolved_reason) }}</span>
        </div>
        <div class="detail-row message-row">
          <span class="label">预警内容：</span>
          <div class="message-box">{{ currentWarning.message }}</div>
        </div>

        <!-- 处置历史 -->
        <div class="handle-history-section">
          <div class="handle-history-header">
            <span class="handle-history-title">处置记录</span>
            <el-tag size="small" type="info" effect="plain">{{ handleRecords.length }} 条</el-tag>
          </div>
          <div v-if="handleRecords.length" class="handle-timeline">
            <div v-for="record in handleRecords" :key="record.id" class="handle-timeline-item">
              <div class="handle-timeline-dot"></div>
              <div class="handle-timeline-content">
                <div class="handle-timeline-top">
                  <el-tag size="small" :type="handleTypeTag(record.handle_type)">
                    {{ handleTypeLabel(record.handle_type) }}
                  </el-tag>
                  <span class="handle-timeline-date">{{ record.handle_date || record.created_at }}</span>
                  <span class="handle-timeline-handler">{{ record.handler_name }}</span>
                  <el-tag v-if="record.effect" size="small" effect="plain" :type="effectTagType(record.effect)">
                    效果：{{ effectLabel(record.effect) }}
                  </el-tag>
                </div>
                <div class="handle-timeline-text">{{ record.content }}</div>
                <div v-if="record.follow_up_date" class="handle-timeline-followup">
                  计划回访：{{ record.follow_up_date }}
                </div>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无处置记录" :image-size="80" />
        </div>
      </div>
      <template #footer>
        <div class="detail-footer">
          <el-button type="success" @click="openHandleDialogFromDetail">
            新增处置
          </el-button>
          <el-button v-if="currentWarning && !currentWarning.is_read" type="primary" @click="handleMarkReadFromDetail">
            标记已读
          </el-button>
          <el-button v-if="currentWarning && currentWarning.status === 'active'" type="danger" @click="handleResolveFromDetail">
            标记消除
          </el-button>
          <el-button @click="detailVisible = false">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 处置弹窗 -->
    <el-dialog v-model="handleDialogVisible" title="记录处置" width="560px" :close-on-click-modal="false">
      <el-form :model="handleForm" label-width="100px" :rules="handleRules" ref="handleFormRef">
        <el-form-item label="处置方式" prop="handle_type">
          <el-select v-model="handleForm.handle_type" placeholder="请选择处置方式" style="width: 100%">
            <el-option label="个别谈话" value="talk" />
            <el-option label="家长沟通" value="parent" />
            <el-option label="家访" value="home_visit" />
            <el-option label="心理辅导" value="psychology" />
            <el-option label="班级批评" value="class_criticism" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="处置日期" prop="handle_date">
          <el-date-picker
            v-model="handleForm.handle_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="处置详情" prop="content">
          <el-input
            v-model="handleForm.content"
            type="textarea"
            :rows="4"
            placeholder="请描述处置过程和学生反馈..."
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="效果评估" prop="effect">
          <el-radio-group v-model="handleForm.effect">
            <el-radio value="good">明显好转</el-radio>
            <el-radio value="normal">一般</el-radio>
            <el-radio value="poor">不明显</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="计划回访">
          <el-date-picker
            v-model="handleForm.follow_up_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择回访日期（可选）"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleDialogVisible = false">取消</el-button>
        <el-button type="success" @click="submitHandle(false)" :loading="handleSubmitting">
          保存
        </el-button>
        <el-button v-if="currentWarning && currentWarning.status === 'active'" type="danger" @click="submitHandle(true)" :loading="handleSubmitting">
          保存并消除预警
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, CircleCheck } from '@element-plus/icons-vue'
import {
  getWarnings,
  markWarningRead,
  markAllWarningsRead,
  resolveWarning,
  batchResolveWarnings,
  getGrades,
  getClasses,
  getWarningHandles,
  createWarningHandle,
} from '@/api/modules/moral'

// ===== 状态 =====
const loading = ref(false)
const tableData = ref([])
const summary = ref({ total: 0, active_count: 0, resolved_count: 0 })
const activeTab = ref('active')

const filter = reactive({
  grade_id: null,
  class_id: null,
  warning_level: null,
  handle_status: null,
  days: 30,
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

const grades = ref([])
const classes = ref([])

const detailVisible = ref(false)
const currentWarning = ref(null)

// 处置相关
const handleDialogVisible = ref(false)
const handleSubmitting = ref(false)
const handleFormRef = ref(null)
const handleRecords = ref([])
const handleForm = reactive({
  handle_type: 'talk',
  handle_date: new Date().toISOString().slice(0, 10),
  content: '',
  effect: 'normal',
  follow_up_date: null,
})

const handleRules = {
  handle_type: [{ required: true, message: '请选择处置方式', trigger: 'change' }],
  handle_date: [{ required: true, message: '请选择处置日期', trigger: 'change' }],
  content: [{ required: true, message: '请填写处置详情', trigger: 'blur', min: 2 }],
  effect: [{ required: true, message: '请选择效果评估', trigger: 'change' }],
}

// ===== 计算属性 =====
const filteredClasses = computed(() => {
  if (filter.grade_id) {
    return classes.value.filter(c => c.grade_id === filter.grade_id)
  }
  return classes.value
})

// ===== 方法 =====
const fetchGrades = async () => {
  try {
    const res = await getGrades()
    if (res.success) {
      grades.value = res.data || []
    }
  } catch (e) {
    // 静默
  }
}

const fetchClasses = async () => {
  try {
    const res = await getClasses()
    if (res.success) {
      classes.value = res.data || []
    }
  } catch (e) {
    // 静默
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
      days: filter.days,
    }
    if (activeTab.value !== 'all') {
      params.status = activeTab.value
    }
    if (filter.grade_id) params.grade_id = filter.grade_id
    if (filter.class_id) params.class_id = filter.class_id
    if (filter.warning_level) params.warning_level = filter.warning_level
    if (filter.handle_status) params.handle_status = filter.handle_status

    const res = await getWarnings(params)
    if (res.success) {
      tableData.value = res.data || []
      summary.value = res.summary || {}
      pagination.total = res.summary?.total || 0
    }
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const switchTab = (tab) => {
  activeTab.value = tab
  pagination.page = 1
  fetchData()
}

const handleFilter = () => {
  pagination.page = 1
  fetchData()
}

const handlePageChange = () => {
  fetchData()
}

const handleMarkRead = async (row) => {
  try {
    await markWarningRead(row.id)
    ElMessage.success('已标记为已读')
    row.is_read = 1
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleBatchMarkRead = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要将所有活跃预警标记为已读吗？',
      '确认操作',
      { type: 'warning' }
    )
    await markAllWarningsRead()
    ElMessage.success('已全部标记为已读')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleResolve = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要标记 ${row.student_name} 的预警为已消除吗？`,
      '确认消除',
      { type: 'warning' }
    )
    await resolveWarning(row.id)
    ElMessage.success('已标记为消除')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleBatchResolve = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要将当前筛选范围内所有活跃预警标记为已消除吗？此操作不可撤销。',
      '批量消除',
      { type: 'warning', confirmButtonText: '确定消除', cancelButtonText: '取消' }
    )
    const res = await batchResolveWarnings()
    ElMessage.success(res.message || '操作成功')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const formatWarningLevel = (level) => {
  if (!level) return '预警'
  const map = {
    'warning': '一般预警',
    'error': '严重预警',
    'escalation_warning': '累进预警',
    'escalation_criticism': '通报批评',
    'escalation_demerit': '记过处分',
    'escalation_probation': '留校察看',
  }
  return map[level] || level
}

const levelTagType = (level, triggerType) => {
  if (!level) return 'info'
  // 累进处罚系列：统一 danger
  if (level.startsWith('escalation_')) return 'danger'
  // 分数阈值类：warning 是警告色
  if (triggerType === 'score_threshold' && level === 'warning') return 'warning'
  if (triggerType === 'score_threshold' && level === 'error') return 'danger'
  // 违纪次数类：danger
  if (triggerType === 'count_threshold') return 'danger'
  return 'warning'
}

/**
 * 触发来源说明：解释这条预警是怎么产生的
 */
const triggerSourceLabel = (type) => {
  const map = {
    'score_threshold': '德育分低于阈值',
    'count_threshold': '违纪次数超标',
  }
  if (type?.startsWith('escalation_')) return '累进处罚触发'
  return map[type] || '系统触发'
}

const resolveReasonLabel = (reason) => {
  const map = {
    'auto_recovered': '自动恢复',
    'manual': '手动消除',
    'rule_deactivated': '规则停用',
    'rule_changed': '规则口径变更',
  }
  return map[reason] || reason
}

// ===== 处置状态展示 =====
const handleStatusLabel = (row) => {
  const handled = (row.handle_count || 0) > 0
  const active = row.status === 'active'
  if (handled && !active) return '已处置消除'
  if (handled && active) return '处置中'
  if (!handled && active) return '待处置'
  return '未处置已消除'
}

const handleStatusTagType = (row) => {
  const handled = (row.handle_count || 0) > 0
  const active = row.status === 'active'
  if (handled && !active) return 'success'
  if (handled && active) return 'warning'
  if (!handled && active) return 'danger'
  return 'info'
}

// ===== 处置方式映射 =====
const handleTypeLabel = (type) => {
  const map = {
    talk: '个别谈话',
    parent: '家长沟通',
    home_visit: '家访',
    psychology: '心理辅导',
    class_criticism: '班级批评',
    other: '其他',
  }
  return map[type] || type
}

const handleTypeTag = (type) => {
  const map = {
    talk: 'primary',
    parent: 'success',
    home_visit: 'warning',
    psychology: 'danger',
    class_criticism: 'info',
    other: 'info',
  }
  return map[type] || 'info'
}

const effectLabel = (effect) => {
  const map = { good: '明显好转', normal: '一般', poor: '不明显' }
  return map[effect] || effect
}

const effectTagType = (effect) => {
  const map = { good: 'success', normal: 'warning', poor: 'danger' }
  return map[effect] || 'info'
}

// ===== 处置弹窗 =====
const openHandleDialog = (row) => {
  currentWarning.value = row
  resetHandleForm()
  handleDialogVisible.value = true
}

const openHandleDialogFromDetail = () => {
  resetHandleForm()
  handleDialogVisible.value = true
}

const resetHandleForm = () => {
  handleForm.handle_type = 'talk'
  handleForm.handle_date = new Date().toISOString().slice(0, 10)
  handleForm.content = ''
  handleForm.effect = 'normal'
  handleForm.follow_up_date = null
}

const submitHandle = async (andResolve) => {
  try {
    await handleFormRef.value.validate()
  } catch {
    return
  }

  if (!currentWarning.value) return

  handleSubmitting.value = true
  try {
    const res = await createWarningHandle(currentWarning.value.id, {
      handle_type: handleForm.handle_type,
      handle_date: handleForm.handle_date,
      content: handleForm.content,
      effect: handleForm.effect,
      follow_up_date: handleForm.follow_up_date,
      resolve_warning: andResolve,
    })

    if (res.success) {
      ElMessage.success(andResolve ? '已保存并消除预警' : '处置记录已保存')
      handleDialogVisible.value = false
      fetchData()
      if (detailVisible.value) {
        fetchHandleRecords(currentWarning.value.id)
        // 同步更新 currentWarning 的状态
        if (andResolve) {
          currentWarning.value.status = 'resolved'
          currentWarning.value.resolved_at = new Date().toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-')
          currentWarning.value.resolved_reason = 'manual'
        }
      }
    }
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    handleSubmitting.value = false
  }
}

// ===== 详情里的方法 =====
const handleMarkReadFromDetail = async () => {
  if (!currentWarning.value) return
  try {
    await markWarningRead(currentWarning.value.id)
    currentWarning.value.is_read = 1
    ElMessage.success('已标记为已读')
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleResolveFromDetail = async () => {
  if (!currentWarning.value) return
  try {
    await resolveWarning(currentWarning.value.id)
    currentWarning.value.status = 'resolved'
    currentWarning.value.resolved_at = new Date().toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-')
    currentWarning.value.resolved_reason = 'manual'
    ElMessage.success('已标记为消除')
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

// ===== 处置记录加载 =====
const fetchHandleRecords = async (warningId) => {
  try {
    const res = await getWarningHandles(warningId)
    if (res.success) {
      handleRecords.value = res.data || []
    }
  } catch (e) {
    console.error('加载处置记录失败:', e)
  }
}

const showDetail = (row) => {
  currentWarning.value = row
  detailVisible.value = true
  handleRecords.value = []
  fetchHandleRecords(row.id)
}
onMounted(() => {
  fetchGrades()
  fetchClasses()
  fetchData()
})
</script>

<style scoped>
.warning-list-page {
  padding: 24px;
  background: var(--page-bg, #0f172a);
  min-height: calc(100vh - 60px);
  color: #e2e8f0;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 6px;
  font-size: 22px;
  font-weight: 600;
  color: #f1f5f9;
}

.subtitle {
  margin: 0;
  color: #94a3b8;
  font-size: 13px;
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  padding: 20px 24px;
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.stat-card:hover {
  border-color: rgba(148, 163, 184, 0.3);
}

.stat-card.active {
  border-color: rgba(56, 189, 248, 0.5);
  background: rgba(14, 116, 144, 0.15);
}

.stat-card.active .stat-value {
  color: #38bdf8;
}

.stat-card.active.resolved .stat-value {
  color: #34d399;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #f1f5f9;
  line-height: 1.2;
}

.stat-card.active .stat-value {
  color: #fb7185;
}

.stat-label {
  margin-top: 6px;
  font-size: 13px;
  color: #94a3b8;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding: 14px 16px;
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 8px;
}

.filter-left,
.filter-right {
  display: flex;
  gap: 10px;
  align-items: center;
}

.table-wrapper {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.1);
  border-radius: 8px;
  overflow: hidden;
}

.student-cell strong {
  color: #e2e8f0;
}

.level-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.level-source {
  font-size: 12px;
  color: #64748b;
}

.message-text {
  color: #cbd5e1;
  font-size: 13px;
  line-height: 1.5;
}

.muted {
  color: #64748b;
}

.action-btns {
  display: flex;
  gap: 4px;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

/* 详情弹窗 */
.detail-content {
  padding: 10px 0;
}

.detail-row {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.1);
  font-size: 14px;
}

.detail-row .label {
  width: 90px;
  flex-shrink: 0;
  color: #94a3b8;
}

.message-row {
  flex-direction: column;
}

.message-row .label {
  margin-bottom: 8px;
}

.message-box {
  background: rgba(15, 23, 42, 0.5);
  padding: 12px;
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.6;
  color: #e2e8f0;
  white-space: pre-wrap;
}

.detail-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.detail-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* ===== 处置历史 ===== */
.handle-history-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
}

.handle-history-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.handle-history-title {
  font-weight: 600;
  font-size: 15px;
  color: #e2e8f0;
}

.handle-timeline {
  position: relative;
  padding-left: 8px;
}

.handle-timeline-item {
  position: relative;
  padding: 0 0 18px 20px;
  border-left: 2px solid rgba(100, 116, 139, 0.3);
}

.handle-timeline-item:last-child {
  border-left-color: transparent;
  padding-bottom: 0;
}

.handle-timeline-dot {
  position: absolute;
  left: -7px;
  top: 4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #22d3ee;
  box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.2);
}

.handle-timeline-content {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(100, 116, 139, 0.2);
  border-radius: 8px;
  padding: 12px 14px;
}

.handle-timeline-top {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.handle-timeline-date {
  font-size: 12px;
  color: #94a3b8;
}

.handle-timeline-handler {
  font-size: 12px;
  color: #64748b;
  margin-left: auto;
}

.handle-timeline-text {
  font-size: 13px;
  line-height: 1.6;
  color: #cbd5e1;
  white-space: pre-wrap;
}

.handle-timeline-followup {
  margin-top: 8px;
  font-size: 12px;
  color: #f59e0b;
}
</style>
