<template>
  <div class="consultation-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="学生">
          <el-input v-model="filterForm.student_id" placeholder="输入学号" clearable />
        </el-form-item>
        <el-form-item label="问题类型">
          <el-select v-model="filterForm.consultation_type" placeholder="选择类型" clearable>
            <el-option label="学业问题" value="academic" />
            <el-option label="行为问题" value="behavior" />
            <el-option label="心理问题" value="psychological" />
            <el-option label="情感问题" value="emotional" />
            <el-option label="综合" value="comprehensive" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable>
            <el-option label="进行中" value="active" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已关闭" value="closed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>AI诊疗会话</span>
          <div class="header-actions">
            <el-button type="primary" @click="handleCreate" v-if="canCreate">发起诊疗</el-button>
          </div>
        </div>
      </template>

      <el-table :data="consultationList" v-loading="loading" stripe>
        <el-table-column prop="title" label="标题" width="200" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.consultation_type)">
              {{ getTypeName(row.consultation_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="student_name" label="学生" width="120" />
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="getPriorityTag(row.priority)" size="small">
              {{ getPriorityName(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator" label="发起人" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看</el-button>
            <el-button link type="warning" @click="handleClose(row)" v-if="row.status === 'active' && canClose">
              关闭
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchConsultations"
        @current-change="fetchConsultations"
        class="pagination"
      />
    </el-card>

    <!-- 发起诊疗对话框 -->
    <el-dialog v-model="createDialogVisible" title="发起AI诊疗" width="600px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="100px">
        <el-form-item label="学生" prop="student_id">
          <el-select
            v-model="createForm.student_id"
            placeholder="选择学生"
            filterable
            style="width: 100%"
            :loading="studentLoading"
          >
            <el-option
              v-for="stu in studentList"
              :key="stu.student_id"
              :label="`${stu.name} (${stu.student_id}) - ${stu.class_name}`"
              :value="stu.student_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="问题类型" prop="consultation_type">
          <el-select v-model="createForm.consultation_type" placeholder="选择类型" style="width: 100%">
            <el-option label="学业问题" value="academic" />
            <el-option label="行为问题" value="behavior" />
            <el-option label="心理问题" value="psychological" />
            <el-option label="情感问题" value="emotional" />
            <el-option label="综合" value="comprehensive" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" prop="title">
          <el-input v-model="createForm.title" placeholder="问题描述标题" />
        </el-form-item>
        <el-form-item label="问题描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" :rows="4" placeholder="详细描述问题情况" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-radio-group v-model="createForm.priority">
            <el-radio value="normal">普通</el-radio>
            <el-radio value="high">紧急</el-radio>
            <el-radio value="urgent">非常紧急</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreateSubmit" :loading="creating">发起诊疗</el-button>
      </template>
    </el-dialog>

    <!-- 诊疗详情抽屉 - 侧边滑出 -->
    <el-drawer
      v-model="detailDrawerVisible"
      title="诊疗详情"
      direction="rtl"
      size="50%"
      :before-close="handleDrawerClose"
    >
      <div class="drawer-content">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="学生">
            {{ currentConsultation.student_name }}（{{ currentConsultation.student_id }}）
          </el-descriptions-item>
          <el-descriptions-item label="班级">{{ currentConsultation.class_name }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag :type="getTypeTag(currentConsultation.consultation_type)" size="small">
              {{ getTypeName(currentConsultation.consultation_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="getRiskTag(currentConsultation.ai_risk_assessment)" size="small">
              {{ getRiskName(currentConsultation.ai_risk_assessment) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">
            {{ currentConsultation.description }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- AI分析报告 - Markdown渲染 -->
        <div class="ai-analysis-section" v-if="currentConsultation.ai_analysis">
          <div class="section-header">
            <span class="section-title">AI 分析报告</span>
            <el-button size="small" @click="refreshDetail" :loading="refreshing">
              <el-icon><Refresh /></el-icon>刷新
            </el-button>
          </div>
          <div class="markdown-content" v-html="renderMarkdown(currentConsultation.ai_analysis)"></div>
        </div>
        <div class="ai-analysis-section" v-else>
          <div class="section-header">
            <span class="section-title">AI 分析</span>
            <el-tag type="warning" size="small">正在生成中...</el-tag>
          </div>
          <el-skeleton :rows="5" animated />
        </div>

        <!-- 对话记录 -->
        <div class="message-section">
          <div class="section-header">
            <span class="section-title">对话记录</span>
            <span class="message-count">{{ messages.length }} 条</span>
          </div>

          <div class="messages-container" ref="messagesContainer">
            <div v-if="messages.length === 0" class="no-messages">
              暂无对话记录
            </div>
            <div v-for="msg in messages" :key="msg.id" :class="['message-item', msg.sender_type === 'ai' ? 'ai-msg' : 'user-msg']">
              <div class="msg-avatar">
                <el-avatar :size="32" :class="msg.sender_type === 'ai' ? 'ai-avatar' : 'user-avatar'">
                  {{ msg.sender_type === 'ai' ? 'AI' : msg.sender?.charAt(0) || 'U' }}
                </el-avatar>
              </div>
              <div class="msg-body">
                <div class="msg-meta">
                  <span class="msg-sender">{{ msg.sender_type === 'ai' ? 'AI助手' : msg.sender || '用户' }}</span>
                  <span class="msg-time">{{ formatTime(msg.created_at) }}</span>
                </div>
                <div class="msg-content" v-html="msg.sender_type === 'ai' ? renderMarkdown(msg.content) : msg.content"></div>
              </div>
            </div>
          </div>

          <!-- 输入区域 -->
          <div class="input-area" v-if="currentConsultation.status === 'active'">
            <el-input
              v-model="newMessage"
              type="textarea"
              :rows="2"
              placeholder="输入消息描述新情况或提问..."
              resize="none"
            />
            <div class="input-actions">
              <el-button type="primary" @click="handleSendMessage" :loading="sending" :disabled="!newMessage.trim()">
                发送
              </el-button>
              <el-button @click="handleQuickAsk('有新情况')">补充信息</el-button>
              <el-button @click="handleQuickAsk('怎么办')">请求建议</el-button>
            </div>
          </div>
          <div class="closed-tip" v-else>
            <el-tag type="info">该会话已关闭</el-tag>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { usePermission } from '@/composables/usePermission'
import {
  getConsultations,
  createConsultation,
  getConsultation,
  addConsultationMessage,
  closeConsultation,
  getStudents,
  getDataScope
} from '@/api/modules/moral'

// 简单的 Markdown 渲染函数
const renderMarkdown = (text) => {
  if (!text) return ''
  let html = text
  // 标题
  html = html.replace(/^## (.*)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.*)$/gm, '<h2 class="md-h2">$1</h2>')
  // 表格
  html = html.replace(/\|(.+)\|/g, (match, content) => {
    const cells = content.split('|').map(c => c.trim())
    return '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>'
  })
  html = html.replace(/(<tr>.*<\/tr>\n?)+/g, '<table class="md-table">$&</table>')
  // 列表
  html = html.replace(/^(\d+)\. (.*)$/gm, '<li class="md-li">$2</li>')
  html = html.replace(/^- (.*)$/gm, '<li class="md-li">$1</li>')
  // 粗体
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 引用块
  html = html.replace(/^> (.*)$/gm, '<blockquote class="md-quote">$1</blockquote>')
  // 分隔线
  html = html.replace(/^---$/gm, '<hr class="md-hr" />')
  // 段落
  html = html.replace(/\n\n/g, '</p><p class="md-p">')
  html = '<p class="md-p">' + html + '</p>'
  return html
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const d = new Date(time)
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`
}

// 权限检查
const { hasPermission } = usePermission()
const canCreate = computed(() => hasPermission('consultation_create') || hasPermission('moral_record_own_class'))
const canClose = computed(() => hasPermission('consultation_close') || hasPermission('moral_record_own_class'))

// 数据
const loading = ref(false)
const consultationList = ref([])

const filterForm = reactive({
  student_id: '',
  consultation_type: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 类型映射
const getTypeTag = (type) => {
  const map = { academic: 'primary', behavior: 'warning', psychological: 'danger', emotional: 'success', comprehensive: 'info' }
  return map[type] || 'info'
}

const getTypeName = (type) => {
  const map = { academic: '学业问题', behavior: '行为问题', psychological: '心理问题', emotional: '情感问题', comprehensive: '综合' }
  return map[type] || type
}

const getStatusTag = (status) => {
  const map = { active: 'primary', resolved: 'success', closed: 'info' }
  return map[status] || 'info'
}

const getStatusName = (status) => {
  const map = { active: '进行中', resolved: '已解决', closed: '已关闭' }
  return map[status] || status
}

const getPriorityTag = (priority) => {
  const map = { normal: 'info', high: 'warning', urgent: 'danger' }
  return map[priority] || 'info'
}

const getPriorityName = (priority) => {
  const map = { normal: '普通', high: '紧急', urgent: '非常紧急' }
  return map[priority] || priority
}

const getRiskTag = (risk) => {
  const map = { high: 'danger', medium: 'warning', low: 'success', unknown: 'info' }
  return map[risk] || 'info'
}

const getRiskName = (risk) => {
  const map = { high: '高风险', medium: '中风险', low: '低风险', unknown: '待评估' }
  return map[risk] || '待评估'
}

// 创建诊疗
const createDialogVisible = ref(false)
const creating = ref(false)
const createFormRef = ref(null)
const studentList = ref([])
const studentLoading = ref(false)
const currentScope = ref('all')

const createForm = reactive({
  student_id: '',
  consultation_type: 'behavior',
  title: '',
  description: '',
  priority: 'normal'
})

const createRules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  consultation_type: [{ required: true, message: '请选择问题类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  description: [{ required: true, message: '请描述问题', trigger: 'blur' }]
}

// 详情抽屉
const detailDrawerVisible = ref(false)
const currentConsultation = ref({})
const messages = ref([])
const messagesContainer = ref(null)
const newMessage = ref('')
const sending = ref(false)
const refreshing = ref(false)
let pollTimer = null

// 方法
const fetchConsultations = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterForm.student_id) params.student_id = filterForm.student_id
    if (filterForm.consultation_type) params.consultation_type = filterForm.consultation_type
    if (filterForm.status) params.status = filterForm.status

    const res = await getConsultations(params)
    if (res.success) {
      consultationList.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (e) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchConsultations()
}

const handleReset = () => {
  filterForm.student_id = ''
  filterForm.consultation_type = ''
  filterForm.status = ''
  pagination.page = 1
  fetchConsultations()
}

const fetchStudentsForCreate = async () => {
  studentLoading.value = true
  try {
    const scopeRes = await getDataScope()
    if (scopeRes.success && scopeRes.data?.consultation) {
      const scopeInfo = scopeRes.data.consultation
      if (scopeInfo.can_own_class) currentScope.value = 'own_class'
      else if (scopeInfo.can_own_grade) currentScope.value = 'own_grade'
      else currentScope.value = 'all'
    }

    const params = { page_size: 500 }
    if (currentScope.value === 'own_class') params.for_record_input = 1

    const res = await getStudents(params)
    if (res.success && res.data?.items) studentList.value = res.data.items
  } catch (e) {
    ElMessage.error('获取学生列表失败')
  } finally {
    studentLoading.value = false
  }
}

const handleCreate = async () => {
  createForm.student_id = ''
  createForm.consultation_type = 'behavior'
  createForm.title = ''
  createForm.description = ''
  createForm.priority = 'normal'
  createDialogVisible.value = true
  await fetchStudentsForCreate()
}

const handleCreateSubmit = async () => {
  await createFormRef.value.validate()
  creating.value = true
  try {
    const res = await createConsultation(createForm)
    if (res.success) {
      ElMessage.success('诊疗会话已创建，AI正在分析')
      createDialogVisible.value = false
      fetchConsultations()
      // 直接打开详情查看AI分析进度
      if (res.data?.id) {
        setTimeout(() => {
          const newItem = consultationList.value.find(c => c.id === res.data.id)
          if (newItem) handleView(newItem)
        }, 500)
      }
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const handleView = async (row) => {
  currentConsultation.value = row
  detailDrawerVisible.value = true
  await refreshDetail()
}

const refreshDetail = async () => {
  refreshing.value = true
  try {
    const res = await getConsultation(currentConsultation.value.id)
    if (res.success) {
      currentConsultation.value = res.data
      messages.value = res.data.messages || []
      // 滚动到底部
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
      // 如果AI还在生成，启动轮询
      if (res.data.ai_analysis && res.data.ai_analysis.includes('正在生成') || !res.data.ai_analysis) {
        startPolling()
      }
    }
  } catch (e) {
    ElMessage.error('获取详情失败')
  } finally {
    refreshing.value = false
  }
}

// 轮询刷新（等待AI回复）
const startPolling = () => {
  if (pollTimer) return
  pollTimer = setInterval(() => {
    refreshDetail()
  }, 3000) // 每3秒刷新
  // 30秒后停止轮询
  setTimeout(() => {
    stopPolling()
  }, 30000)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const handleDrawerClose = () => {
  stopPolling()
  detailDrawerVisible.value = false
}

const handleSendMessage = async () => {
  if (!newMessage.value.trim()) return
  sending.value = true
  try {
    const res = await addConsultationMessage(currentConsultation.value.id, {
      content: newMessage.value
    })
    newMessage.value = ''
    ElMessage.success('消息已发送，AI正在回复')
    // 启动轮询等待AI回复
    startPolling()
    // 立即刷新一次
    await refreshDetail()
  } catch (e) {
    ElMessage.error('发送失败')
  } finally {
    sending.value = false
  }
}

const handleQuickAsk = (type) => {
  const templates = {
    '有新情况': '补充新情况：',
    '怎么办': '针对当前情况，我该怎么办？请给出具体建议。'
  }
  newMessage.value = templates[type] || ''
}

const handleClose = async (row) => {
  try {
    const { value: outcome } = await ElMessageBox.prompt('请输入处理结果', '关闭诊疗会话', {
      inputPattern: /.+/,
      inputErrorMessage: '请输入处理结果'
    })
    await closeConsultation(row.id, outcome)
    ElMessage.success('会话已关闭')
    fetchConsultations()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('关闭失败')
  }
}

onMounted(() => {
  fetchConsultations()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.consultation-page {
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

.pagination {
  margin-top: 20px;
  justify-content: flex-end;
}

/* 抽屉内容样式 */
.drawer-content {
  padding: 0 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-weight: 600;
  font-size: 16px;
  color: #303133;
}

/* AI分析区域 */
.ai-analysis-section {
  background: #f8f9fa;
  padding: 16px;
  border-radius: 8px;
  flex-shrink: 0;
}

.markdown-content {
  max-height: 300px;
  overflow-y: auto;
  line-height: 1.8;
}

/* Markdown 样式 */
.md-h2 {
  font-size: 18px;
  font-weight: 600;
  margin: 16px 0 12px;
  color: #409eff;
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 8px;
}

.md-h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 12px 0 8px;
  color: #606266;
}

.md-p {
  margin: 8px 0;
  color: #303133;
}

.md-table {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}

.md-table td {
  border: 1px solid #e4e7ed;
  padding: 8px 12px;
  text-align: left;
}

.md-table tr:first-child td {
  background: #f5f7fa;
  font-weight: 500;
}

.md-li {
  margin: 4px 0 4px 20px;
  list-style: decimal;
}

.md-quote {
  background: #fff3e0;
  padding: 12px 16px;
  margin: 8px 0;
  border-left: 4px solid #e6a23c;
  color: #5d4037;
}

.md-hr {
  margin: 16px 0;
  border: none;
  border-top: 1px dashed #dcdfe6;
}

/* 消息区域 */
.message-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.message-count {
  color: #909399;
  font-size: 12px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: #fafbfc;
  border-radius: 8px;
  min-height: 200px;
}

.no-messages {
  text-align: center;
  color: #909399;
  padding: 40px;
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.msg-avatar {
  flex-shrink: 0;
}

.ai-avatar {
  background: #67c23a;
  color: white;
}

.user-avatar {
  background: #409eff;
  color: white;
}

.msg-body {
  flex: 1;
  min-width: 0;
}

.msg-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}

.msg-sender {
  font-weight: 500;
  font-size: 13px;
}

.msg-time {
  color: #909399;
  font-size: 12px;
}

.msg-content {
  background: white;
  padding: 10px 12px;
  border-radius: 6px;
  line-height: 1.6;
  word-break: break-word;
}

.ai-msg .msg-content {
  background: #f0f9eb;
}

.user-msg .msg-content {
  background: #ecf5ff;
}

/* 输入区域 */
.input-area {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e4e7ed;
}

.input-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.closed-tip {
  text-align: center;
  padding: 20px;
}
</style>