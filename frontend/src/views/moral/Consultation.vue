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
          <el-input v-model="createForm.student_id" placeholder="输入学号" />
        </el-form-item>
        <el-form-item label="问题类型" prop="consultation_type">
          <el-select v-model="createForm.consultation_type" placeholder="选择类型" style="width: 100%">
            <el-option label="学业问题" value="academic" />
            <el-option label="行为问题" value="behavior" />
            <el-option label="心理问题" value="psychological" />
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
        <el-button type="primary" @click="handleCreateSubmit" :loading="creating">发起并请求AI分析</el-button>
      </template>
    </el-dialog>

    <!-- 诊疗详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="诊疗详情" width="800px">
      <div class="consultation-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="学生">{{ currentConsultation.student_name }}（{{ currentConsultation.student_id }}）</el-descriptions-item>
          <el-descriptions-item label="类型">{{ getTypeName(currentConsultation.consultation_type) }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ getStatusName(currentConsultation.status) }}</el-descriptions-item>
          <el-descriptions-item label="优先级">{{ getPriorityName(currentConsultation.priority) }}</el-descriptions-item>
          <el-descriptions-item label="问题描述" :span="2">{{ currentConsultation.description }}</el-descriptions-item>
        </el-descriptions>

        <!-- AI分析报告 -->
        <div class="ai-analysis" v-if="currentConsultation.ai_analysis">
          <h4>AI分析报告</h4>
          <div class="analysis-content">{{ currentConsultation.ai_analysis }}</div>
        </div>

        <!-- 对话记录 -->
        <div class="message-list">
          <h4>对话记录</h4>
          <div class="messages">
            <div v-for="msg in messages" :key="msg.id" :class="['message', msg.sender_type === 'ai' ? 'ai-message' : 'user-message']">
              <div class="message-header">
                <span class="sender">{{ msg.sender_type === 'ai' ? 'AI助手' : msg.sender || '用户' }}</span>
                <span class="time">{{ msg.created_at }}</span>
              </div>
              <div class="message-content">{{ msg.content }}</div>
            </div>
          </div>

          <!-- 发送消息 -->
          <div class="message-input" v-if="currentConsultation.status === 'active'">
            <el-input v-model="newMessage" placeholder="输入消息..." />
            <el-button type="primary" @click="handleSendMessage" :loading="sending">发送</el-button>
            <el-button @click="handleRequestAI" :loading="requestingAI">请求AI分析</el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePermission } from '@/composables/usePermission'
import request from '@/utils/api'

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
  const map = { academic: 'primary', behavior: 'warning', psychological: 'danger', comprehensive: 'info' }
  return map[type] || 'info'
}

const getTypeName = (type) => {
  const map = { academic: '学业问题', behavior: '行为问题', psychological: '心理问题', comprehensive: '综合' }
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

// 创建诊疗
const createDialogVisible = ref(false)
const creating = ref(false)
const createFormRef = ref(null)

const createForm = reactive({
  student_id: '',
  consultation_type: 'behavior',
  title: '',
  description: '',
  priority: 'normal'
})

const createRules = {
  student_id: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  consultation_type: [{ required: true, message: '请选择问题类型', trigger: 'change' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  description: [{ required: true, message: '请描述问题', trigger: 'blur' }]
}

// 详情对话框
const detailDialogVisible = ref(false)
const currentConsultation = ref({})
const messages = ref([])
const newMessage = ref('')
const sending = ref(false)
const requestingAI = ref(false)

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

    const res = await request.get('/api/moral/consultations', { params })
    if (res.data.success) {
      consultationList.value = res.data.data.items
      pagination.total = res.data.data.total
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

const handleCreate = () => {
  createForm.student_id = ''
  createForm.consultation_type = 'behavior'
  createForm.title = ''
  createForm.description = ''
  createForm.priority = 'normal'
  createDialogVisible.value = true
}

const handleCreateSubmit = async () => {
  await createFormRef.value.validate()
  creating.value = true
  try {
    const res = await request.post('/api/moral/consultations', createForm)
    if (res.data.success) {
      ElMessage.success('诊疗会话已创建')
      createDialogVisible.value = false
      fetchConsultations()
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

const handleView = async (row) => {
  currentConsultation.value = row
  detailDialogVisible.value = true

  // 获取消息记录
  try {
    const res = await request.get(`/api/moral/consultations/${row.id}`)
    if (res.data.success) {
      currentConsultation.value = res.data.data
      messages.value = res.data.data.messages || []
    }
  } catch (e) {
    ElMessage.error('获取详情失败')
  }
}

const handleSendMessage = async () => {
  if (!newMessage.value.trim()) return
  sending.value = true
  try {
    await request.post(`/api/moral/consultations/${currentConsultation.value.id}/messages`, {
      content: newMessage.value,
      sender_type: 'user'
    })
    newMessage.value = ''
    // 刷新消息
    handleView(currentConsultation.value)
  } catch (e) {
    ElMessage.error('发送失败')
  } finally {
    sending.value = false
  }
}

const handleRequestAI = async () => {
  requestingAI.value = true
  try {
    const res = await request.post(`/api/moral/consultations/${currentConsultation.value.id}/messages`, {
      content: '请AI助手分析当前情况并提供建议',
      sender_type: 'user',
      message_type: 'analysis_request'
    })
    // 刷新
    handleView(currentConsultation.value)
  } catch (e) {
    ElMessage.error('请求AI分析失败')
  } finally {
    requestingAI.value = false
  }
}

const handleClose = async (row) => {
  try {
    const { value: outcome } = await ElMessageBox.prompt('请输入处理结果', '关闭诊疗会话', {
      inputPattern: /.+/,
      inputErrorMessage: '请输入处理结果'
    })

    await request.post(`/api/moral/consultations/${row.id}/close`, null, {
      params: { outcome }
    })

    ElMessage.success('会话已关闭')
    fetchConsultations()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('关闭失败')
    }
  }
}

// 初始化
import { computed } from 'vue'
onMounted(() => {
  fetchConsultations()
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

.consultation-detail {
  padding: 10px;
}

.ai-analysis {
  margin-top: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.ai-analysis h4 {
  margin-bottom: 10px;
  color: #409eff;
}

.analysis-content {
  white-space: pre-wrap;
  line-height: 1.6;
}

.message-list {
  margin-top: 20px;
}

.message-list h4 {
  margin-bottom: 10px;
}

.messages {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid #eee;
  padding: 10px;
  border-radius: 4px;
}

.message {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 4px;
}

.user-message {
  background: #ecf5ff;
  margin-left: 20px;
}

.ai-message {
  background: #f0f9eb;
  margin-right: 20px;
}

.message-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
  font-size: 12px;
  color: #666;
}

.message-content {
  line-height: 1.5;
}

.message-input {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.message-input .el-input {
  flex: 1;
}
</style>