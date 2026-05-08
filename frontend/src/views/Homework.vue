<template>
  <div class="homework-container">
    <h2>{{ classCode ? `${classCode}作业` : '作业' }}</h2>
    
    <div v-if="loading" class="loading-container">
      <el-loading />
    </div>
    
    <template v-else>
      <div v-if="currentTabDuration > 0" class="total-duration">
        <el-alert
          :title="activeTab === '日常' ? '日常作业时间预估' : '周末作业时间预估'"
          type="warning"
          :description="`完成${activeTab === '日常' ? '日常' : '周末'}作业预计需要 ${currentTabDuration} 分钟（${Math.round(currentTabDuration/60 * 10) / 10} 小时）`"
          show-icon
          :closable="false"
        />
      </div>

      <div v-if="isAdmin && hasHomework(activeTab)" class="batch-actions">
          <el-checkbox v-model="selectAll" :indeterminate="isIndeterminate" @change="handleSelectAll">
            全选
          </el-checkbox>
          <el-button v-if="selectedIds.length > 0" type="danger" size="small" @click="handleBatchDelete">
            批量删除 ({{ selectedIds.length }})
          </el-button>
        </div>

<el-tabs v-model="activeTab" class="homework-tabs">
        <el-tab-pane label="日常作业" name="日常">
          <el-empty v-if="!hasHomework('日常')" description="暂无日常作业" />
          <div v-else class="table-container">
            <el-table ref="tableRef" :data="getAllHomeworkList('日常')" stripe style="width: 100%" :max-height="tableMaxHeight" @selection-change="handleSelectionChange">
              <el-table-column v-if="isAdmin || (role.value && role.value.includes('teacher'))" type="selection" width="50" />
              <el-table-column prop="subject" label="学科" width="80" fixed>
                <template #default="scope">
                  <div class="cell-content">
                    <span class="subject-badge" :class="getSubjectClass(scope.row.subject)">
                      {{ scope.row.subject }}
                    </span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="teacher" label="老师" width="80">
                <template #default="scope">
                  <div class="cell-content">{{ scope.row.teacher }}</div>
                </template>
              </el-table-column>
              <el-table-column prop="content" label="作业内容" min-width="250">
                <template #default="scope">
                  <div class="cell-content">{{ scope.row.content }}</div>
                </template>
              </el-table-column>
              <el-table-column prop="duration" label="用时" width="70" align="center">
                <template #default="scope">
                  <div class="cell-content duration-text">{{ scope.row.duration }}分钟</div>
                </template>
              </el-table-column>
              <el-table-column label="截止时间" min-width="100" max-width="300" align="center">
                <template #default="scope">
                  <span v-if="getContentLines(scope.row.content) === 1" class="deadline-cell" :class="getDeadlineClass(scope.row.deadline)">
                    <span class="deadline-date">{{ formatDateMonthDay(scope.row.deadline, true) }}</span>
                    <span class="deadline-status">{{ getDeadlineStatus(scope.row.deadline) }}</span>
                  </span>
                  <div v-else class="deadline-multi">
                    <div class="deadline-cell" :class="getDeadlineClass(scope.row.deadline)">
                      <div class="deadline-date">{{ formatDateMonthDay(scope.row.deadline, true) }}</div>
                      <div class="deadline-status">{{ getDeadlineStatus(scope.row.deadline) }}</div>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" align="center" fixed="right">
                <template #default="scope">
                  <div v-if="canModifyHomework(scope.row)" class="cell-content action-cell">
                    <el-button size="small" type="primary" @click="openEditDialog(scope.row)">编辑</el-button>
                    <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="周末作业" name="周末">
          <el-empty v-if="!hasHomework('周末')" description="暂无周末作业" />
          <div v-else class="table-container">
            <el-table ref="weekendTableRef" :data="getAllHomeworkList('周末')" stripe style="width: 100%" :max-height="tableMaxHeight" @selection-change="handleSelectionChange">
              <el-table-column v-if="isAdmin || (role.value && role.value.includes('teacher'))" type="selection" width="50" />
              <el-table-column prop="subject" label="学科" width="80" fixed>
                <template #default="scope">
                  <div class="cell-content">
                    <span class="subject-badge" :class="getSubjectClass(scope.row.subject)">
                      {{ scope.row.subject }}
                    </span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="teacher" label="老师" width="80">
                <template #default="scope">
                  <div class="cell-content">{{ scope.row.teacher }}</div>
                </template>
              </el-table-column>
              <el-table-column prop="content" label="作业内容" min-width="250">
                <template #default="scope">
                  <div class="cell-content">{{ scope.row.content }}</div>
                </template>
              </el-table-column>
              <el-table-column prop="duration" label="用时" width="70" align="center">
                <template #default="scope">
                  <div class="cell-content duration-text">{{ scope.row.duration }}分钟</div>
                </template>
              </el-table-column>
              <el-table-column label="截止时间" min-width="100" max-width="300" align="center">
                <template #default="scope">
                  <span v-if="getContentLines(scope.row.content) === 1" class="deadline-cell" :class="getDeadlineClass(scope.row.deadline)">
                    <span class="deadline-date">{{ formatDateMonthDay(scope.row.deadline, true) }}</span>
                    <span class="deadline-status">{{ getDeadlineStatus(scope.row.deadline) }}</span>
                  </span>
                  <div v-else class="deadline-multi">
                    <div class="deadline-cell" :class="getDeadlineClass(scope.row.deadline)">
                      <div class="deadline-date">{{ formatDateMonthDay(scope.row.deadline, true) }}</div>
                      <div class="deadline-status">{{ getDeadlineStatus(scope.row.deadline) }}</div>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" align="center" fixed="right">
                <template #default="scope">
                  <div v-if="canModifyHomework(scope.row)" class="cell-content action-cell">
                    <el-button size="small" type="primary" @click="openEditDialog(scope.row)">编辑</el-button>
                    <el-button size="small" type="danger" @click="handleDelete(scope.row.id)">删除</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>

    <el-dialog v-model="editDialogVisible" title="编辑作业" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="学科">
          <el-select v-model="editForm.subject" placeholder="请选择学科">
            <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="作业内容">
          <el-input v-model="editForm.content" type="textarea" :rows="4" />
        </el-form-item>
        <el-form-item label="上交日期">
          <el-date-picker
            v-model="editForm.deadline"
            type="datetime"
            placeholder="选择日期和时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DD HH:mm"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="预计用时">
          <el-input-number v-model="editForm.duration" :min="1" :max="180" />
          <span style="margin-left: 10px">分钟</span>
        </el-form-item>
        <el-form-item label="作业类型">
          <el-radio-group v-model="editForm.type">
            <el-radio value="日常">日常</el-radio>
            <el-radio value="周末">周末</el-radio>
            <el-radio value="假期">假期</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate" :loading="updating">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElLoading, ElMessage, ElEmpty, ElTabs, ElTabPane, ElTable, ElTableColumn, ElTag, ElAlert, ElButton, ElDialog, ElForm, ElFormItem, ElSelect, ElOption, ElInput, ElDatePicker, ElInputNumber, ElRadioGroup, ElRadio } from 'element-plus'
import { getHomeworkList, updateHomework, deleteHomework, batchDeleteHomework } from '@/api/modules/homework'
import { useAuthStore } from '../stores/auth'
import { formatDateMonthDay } from '@/utils/time'

const authStore = useAuthStore()
const username = computed(() => authStore.username)
const isAdmin = computed(() => authStore.isAdmin)
const role = computed(() => authStore.role)

// 检查是否可以编辑/删除作业（管理员或作业发布者）
const canModifyHomework = (row) => {
  if (!row) return false
  if (isAdmin.value) return true

  // 非管理员：只能操作自己发布的作业
  const currentUsername = username.value || username || ''
  return row.teacher === currentUsername
}

const loading = ref(false)
const activeTab = ref('日常')
const homework = ref({
  日常: {},
  周末: {}
})
const classCode = ref('')
const editDialogVisible = ref(false)
const editForm = ref({
  id: null,
  subject: '',
  content: '',
  deadline: '',
  duration: 30,
  type: '日常'
})
const updating = ref(false)
const selectedIds = ref([])
const tableRef = ref(null)
const weekendTableRef = ref(null)
const selectAll = ref(false)

const isIndeterminate = computed(() => {
  const list = getAllHomeworkList(activeTab.value)
  return selectedIds.value.length > 0 && selectedIds.value.length < list.length
})

const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

const handleSelectAll = (checked) => {
  if (checked) {
    const list = getAllHomeworkList(activeTab.value)
    selectedIds.value = list.map(item => item.id)
  } else {
    selectedIds.value = []
  }
}

const handleBatchDelete = async () => {
  if (selectedIds.value.length === 0) return
  try {
    await batchDeleteHomework({ ids: selectedIds.value, classCode: classCode.value })
    ElMessage.success(`成功删除 ${selectedIds.value.length} 条作业`)
    selectedIds.value = []
    selectAll.value = false
    fetchHomework()
  } catch (error) {
    console.error('Batch delete error:', error)
    ElMessage.error('批量删除失败')
  }
}

const subjects = ["语文", "数学", "英语", "物理", "化学", "生物", "地理", "历史", "政治", "美术", "技术", "班级"]

const getContentLines = (content) => {
  if (!content) return 1
  return content.split('\n').length
}

const tableMaxHeight = computed(() => {
  return window.innerHeight - 200
})

const hasHomework = (type) => {
  const data = homework.value[type]
  if (!data || typeof data !== 'object') return false
  for (const subject in data) {
    if (data[subject] && typeof data[subject] === 'object') {
      for (const teacher in data[subject]) {
        if (data[subject][teacher] && data[subject][teacher].length > 0) {
          return true
        }
      }
    }
  }
  return false
}

const getAllHomeworkList = (type) => {
  const data = homework.value[type]
  if (!data || typeof data !== 'object') return []
  
  const result = []
  for (const subject in data) {
    if (data[subject] && typeof data[subject] === 'object') {
      for (const teacher in data[subject]) {
        const list = data[subject][teacher]
        if (Array.isArray(list)) {
          for (const hw of list) {
            result.push({
              subject,
              teacher,
              content: hw.content,
              duration: hw.duration || 0,
              deadline: hw.deadline,
              id: hw.id,
              type: type,
              hasEmergency: getDeadlineStatus(hw.deadline) === '紧急'
            })
          }
        }
      }
    }
  }
  
  return result.sort((a, b) => {
    if (a.hasEmergency && !b.hasEmergency) return -1
    if (!a.hasEmergency && b.hasEmergency) return 1
    return 0
  })
}

const calculateDuration = (type) => {
  const data = homework.value[type]
  if (!data || typeof data !== 'object') return 0
  let total = 0
  for (const subject in data) {
    if (data[subject] && typeof data[subject] === 'object') {
      let subjectMaxDuration = 0
      for (const teacher in data[subject]) {
        const list = data[subject][teacher]
        if (Array.isArray(list)) {
          const subjectDuration = list.reduce((sum, item) => sum + (item.duration || 0), 0)
          if (subjectDuration > subjectMaxDuration) {
            subjectMaxDuration = subjectDuration
          }
        }
      }
      total += subjectMaxDuration
    }
  }
  return total
}

const dailyDuration = computed(() => calculateDuration('日常'))
const weeklyDuration = computed(() => calculateDuration('周末'))
const currentTabDuration = computed(() => {
  return activeTab.value === '日常' ? dailyDuration.value : weeklyDuration.value
})

const getSubjectClass = (subject) => {
  const classes = {
    '语文': 'subject-chinese',
    '数学': 'subject-math',
    '英语': 'subject-english',
    '物理': 'subject-physics',
    '化学': 'subject-chemistry',
    '生物': 'subject-biology',
    '政治': 'subject-politics',
    '历史': 'subject-history',
    '地理': 'subject-geography'
  }
  return classes[subject] || 'subject-default'
}

const getDeadlineClass = (deadline) => {
  const now = new Date()
  const dueDate = new Date(deadline.replace(' ', 'T'))
  const diffHours = (dueDate - now) / (1000 * 60 * 60)
  
  if (diffHours < 0) return 'deadline-expired'
  if (diffHours <= 24) return 'deadline-urgent'
  if (diffHours <= 48) return 'deadline-soon'
  return 'deadline-normal'
}

const getDeadlineStatus = (deadline) => {
  const now = new Date()
  const dueDate = new Date(deadline.replace(' ', 'T'))
  const diffHours = (dueDate - now) / (1000 * 60 * 60)
  const diffDays = Math.ceil((dueDate - now) / (1000 * 60 * 60 * 24))
  
  if (diffHours < 0) return '已过期'
  if (diffHours <= 24) return '紧急'
  if (diffHours <= 48) return '明天'
  if (diffDays <= 3) return `${diffDays}天`
  return '充裕'
}

const getClassCode = () => {
  const code = document.cookie.split('; ').find(row => row.startsWith('classCode='))
  return code ? code.split('=')[1] : null
}

const openEditDialog = (hw) => {
  editForm.value = {
    id: hw.id,
    subject: hw.subject,
    content: hw.content,
    deadline: hw.deadline,
    duration: hw.duration,
    type: hw.type
  }
  editDialogVisible.value = true
}

const handleUpdate = async () => {
  updating.value = true
  try {
    await updateHomework(editForm.value.id, {
      homework: {
        subject: editForm.value.subject,
        content: editForm.value.content,
        deadline: editForm.value.deadline,
        duration: editForm.value.duration,
        type: editForm.value.type
      }
    })
    ElMessage.success('作业更新成功')
    editDialogVisible.value = false
    fetchHomework()
  } catch (error) {
    console.error('Update homework error:', error)
    ElMessage.error('更新失败：' + (error.response?.data?.detail || '未知错误'))
  } finally {
    updating.value = false
  }
}

const handleDelete = async (hwId) => {
  try {
    await deleteHomework(hwId)
    ElMessage.success('作业删除成功')
    fetchHomework()
  } catch (error) {
    console.error('Delete homework error:', error)
    ElMessage.error('删除失败：' + (error.response?.data?.detail || '未知错误'))
  }
}

const fetchHomework = async () => {
  const code = getClassCode()
  if (!code) {
    ElMessage.warning('请先选择班级')
    return
  }

  loading.value = true
  try {
    const response = await getHomeworkList(code)
    homework.value = response.data || { 日常: {}, 周末: {} }
  } catch (error) {
    console.error('Error fetching homework:', error)
    ElMessage.error('获取作业列表失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchHomework()
  classCode.value = getClassCode()
})
</script>

<style scoped>
.homework-container {
  padding: 10px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 10px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.homework-container h2 {
  margin: 0 0 10px 0;
  font-size: 18px;
}

.homework-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.total-duration {
  margin-bottom: 10px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.table-container {
  flex: 1;
  overflow: hidden;
}

.subject-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  font-weight: bold;
}

.cell-content {
  display: flex;
  align-items: center;
  min-height: 26px;
  line-height: 1.4;
}

.subject-chinese { background-color: #67C23A; }
.subject-math { background-color: #E6A23C; }
.subject-english { background-color: #F56C6C; }
.subject-physics { background-color: #409EFF; }
.subject-chemistry { background-color: #9B59B6; }
.subject-biology { background-color: #2ECC71; }
.subject-politics { background-color: #FF9800; }
.subject-history { background-color: #795548; }
.subject-geography { background-color: #607D8B; }
.subject-default { background-color: #909399; }

.hw-content-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hw-row {
  display: flex;
  gap: 4px;
  line-height: 1.4;
}

.hw-teacher {
  color: #909399;
  font-size: 12px;
  white-space: nowrap;
}

.hw-content-text {
  color: #303133;
}

.duration-text {
  font-size: 12px;
  color: #E6A23C;
}

.deadline-cell, span.deadline-cell {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.deadline-multi .deadline-cell {
  align-items: flex-start;
  justify-content: flex-start;
  height: 100%;
}

.deadline-date {
  font-weight: bold;
  white-space: nowrap;
}

.deadline-status {
  font-size: 11px;
  white-space: nowrap;
  margin-left: 3px;
}

.deadline-normal {
  background: #f0f9eb;
  color: #67c23a;
}

.deadline-soon {
  background: #fdf6ec;
  color: #e6a23c;
}

.deadline-urgent {
  background: #fef0f0;
  color: #f56c6c;
}

.deadline-expired {
  background: #f4f4f5;
  color: #909399;
  text-decoration: line-through;
}

.action-cell {
  display: flex;
  gap: 4px;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .homework-container {
    padding: 5px;
    height: auto;
    min-height: 100vh;
  }

  .homework-tabs :deep(.el-tabs__header) {
    margin-bottom: 10px;
  }

  .homework-tabs :deep(.el-tabs__nav-wrap) {
    overflow-x: auto;
    overflow-y: hidden;
  }

  .homework-tabs :deep(.el-tabs__item) {
    font-size: 14px;
    padding: 0 12px;
  }

  .batch-actions {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .table-container {
    overflow-x: auto;
  }

  :deep(.el-table) {
    overflow-x: scroll;
    display: block;
  }

  :deep(.el-table__inner-wrapper) {
    overflow-x: scroll;
  }

  :deep(.el-table__header-wrapper),
  :deep(.el-table__body-wrapper) {
    overflow-x: scroll;
  }

  :deep(.el-table__header),
  :deep(.el-table__body) {
    min-width: 100%;
  }

  /* 显示滚动条 */
  :deep(.el-scrollbar__bar.is-horizontal) {
    display: block !important;
    opacity: 1;
  }

  /* 移除固定列 */
  :deep(.el-table__fixed),
  :deep(.el-table__fixed-right) {
    display: none !important;
  }
}
</style>
