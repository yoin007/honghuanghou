<template>
  <div class="invigilation-page">
    <!-- 顶部工具栏 -->
    <el-card class="toolbar-card">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-select v-model="selectedProjectId" placeholder="选择考试项目" style="width: 300px" @change="loadProjectSlots">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id">
              <span>{{ p.name }}</span>
              <span style="color: #999; font-size: 12px; margin-left: 8px">{{ p.status }}</span>
            </el-option>
          </el-select>
          <el-button type="primary" @click="showCreateProjectDialog">新建考试项目</el-button>
        </div>
        <div class="toolbar-right">
          <el-button @click="downloadTemplate">下载模板</el-button>
          <el-button @click="showImportDialog" :disabled="!selectedProjectId">导入Excel</el-button>
          <el-button @click="exportExcel" :disabled="!selectedProjectId">导出Excel</el-button>
          <el-button @click="exportReport" :disabled="!selectedProjectId">导出报表</el-button>
          <el-button type="success" @click="saveSlots" :disabled="!selectedProjectId || !hasChanges">保存</el-button>
          <el-button type="warning" @click="sendNotifications" :disabled="!selectedProjectId">保存并通知</el-button>
          <el-button @click="showNotificationLogs" :disabled="!selectedProjectId">通知日志</el-button>
        </div>
      </div>
    </el-card>

    <!-- 项目信息 -->
    <el-card v-if="currentProject" class="project-info-card">
      <div class="project-info">
        <div class="info-item">
          <span class="label">考试名称:</span>
          <span class="value">{{ currentProject.name }}</span>
        </div>
        <div class="info-item">
          <span class="label">学年学期:</span>
          <span class="value">{{ currentProject.school_year }} {{ currentProject.semester }}</span>
        </div>
        <div class="info-item">
          <span class="label">考试日期:</span>
          <span class="value">{{ currentProject.start_date }} ~ {{ currentProject.end_date }}</span>
        </div>
        <div class="info-item">
          <span class="label">状态:</span>
          <el-tag :type="getStatusType(currentProject.status)">{{ getStatusName(currentProject.status) }}</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 年级Tabs -->
    <el-card v-if="selectedProjectId" class="slots-card">
      <el-tabs v-model="activeGradeId" type="card">
        <el-tab-pane v-for="grade in projectGrades" :key="grade.id" :label="grade.name" :name="String(grade.id)">
          <!-- 操作栏 -->
          <div class="grade-toolbar">
            <el-button type="primary" size="small" @click="addSlot(grade.id)">新增安排</el-button>
            <el-button size="small" @click="batchAddSlots(grade.id)">批量新增</el-button>
            <el-button size="small" @click="swapTeachers" :disabled="selectedRows.length !== 2">交换监考老师</el-button>
          </div>

          <!-- 安排表格 -->
          <el-table
            :data="getGradeSlots(grade.id)"
            border
            stripe
            @selection-change="handleSelectionChange"
            style="width: 100%"
          >
            <el-table-column type="selection" width="50" />
            <el-table-column prop="exam_date" label="日期" width="120">
              <template #default="{ row }">
                <el-date-picker
                  v-model="row.exam_date"
                  type="date"
                  value-format="YYYY-MM-DD"
                  size="small"
                  style="width: 100%"
                  @change="markChanged"
                />
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="开始时间" width="100">
              <template #default="{ row }">
                <el-input v-model="row.start_time" size="small" placeholder="08:00" @change="markChanged" />
              </template>
            </el-table-column>
            <el-table-column prop="end_time" label="结束时间" width="100">
              <template #default="{ row }">
                <el-input v-model="row.end_time" size="small" placeholder="10:00" @change="markChanged" />
              </template>
            </el-table-column>
            <el-table-column prop="subject" label="学科" width="120">
              <template #default="{ row }">
                <el-input v-model="row.subject" size="small" placeholder="语文" @change="markChanged" />
              </template>
            </el-table-column>
            <el-table-column prop="room_name" label="考场" width="150">
              <template #default="{ row }">
                <el-input v-model="row.room_name" size="small" placeholder="第1考场" @change="markChanged" />
              </template>
            </el-table-column>
            <el-table-column prop="teacher_name" label="监考老师" width="150">
              <template #default="{ row }">
                <el-select
                  v-model="row.teacher_id"
                  placeholder="选择教师"
                  size="small"
                  filterable
                  style="width: 100%"
                  @change="updateTeacherName(row)"
                >
                  <el-option v-for="t in teachers" :key="t.teacher_id" :label="t.name" :value="t.teacher_id" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row, $index }">
                <el-button type="danger" size="small" link @click="deleteSlot(grade.id, $index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 新建项目弹窗 -->
    <el-dialog v-model="createProjectVisible" title="新建考试项目" width="500px">
      <el-form ref="projectFormRef" :model="projectForm" :rules="projectRules" label-width="100px">
        <el-form-item label="考试名称" prop="name">
          <el-input v-model="projectForm.name" placeholder="如：2026春季期中考试" />
        </el-form-item>
        <el-form-item label="学年">
          <el-input v-model="projectForm.school_year" placeholder="如：2025-2026" />
        </el-form-item>
        <el-form-item label="学期">
          <el-input v-model="projectForm.semester" placeholder="如：下学期" />
        </el-form-item>
        <el-form-item label="考试日期">
          <el-date-picker
            v-model="projectForm.date_range"
            type="daterange"
            value-format="YYYY-MM-DD"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
          />
        </el-form-item>
        <el-form-item label="参与年级" prop="grade_ids">
          <el-checkbox-group v-model="projectForm.grade_ids">
            <el-checkbox :label="1">高一</el-checkbox>
            <el-checkbox :label="2">高二</el-checkbox>
            <el-checkbox :label="3">高三</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createProjectVisible = false">取消</el-button>
        <el-button type="primary" @click="createProject">创建</el-button>
      </template>
    </el-dialog>

    <!-- 导入Excel弹窗 -->
    <el-dialog v-model="importVisible" title="导入监考安排" width="500px">
      <el-upload
        drag
        accept=".xlsx,.xls"
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽文件到此处或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx/.xls 格式</div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" @click="importExcel" :loading="importLoading">导入</el-button>
      </template>
    </el-dialog>

    <!-- 通知日志弹窗 -->
    <el-dialog v-model="notificationLogsVisible" title="通知日志" width="800px">
      <el-table :data="notificationLogs" border stripe>
        <el-table-column prop="teacher_name" label="教师" width="100" />
        <el-table-column prop="change_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.change_type === 'initial'" type="success">首次</el-tag>
            <el-tag v-else-if="row.change_type === 'added'" type="primary">新增</el-tag>
            <el-tag v-else-if="row.change_type === 'changed'" type="warning">变更</el-tag>
            <el-tag v-else-if="row.change_type === 'removed'" type="danger">取消</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sent_status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.sent_status === 'success'" type="success">成功</el-tag>
            <el-tag v-else-if="row.sent_status === 'failed'" type="danger">失败</el-tag>
            <el-tag v-else-if="row.sent_status === 'skipped'" type="info">跳过</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sent_at" label="发送时间" width="160" />
        <el-table-column prop="error_message" label="错误信息" min-width="150" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '@/utils/api'

// 数据
const projects = ref([])
const selectedProjectId = ref(null)
const currentProject = ref(null)
const slots = ref([])
const teachers = ref([])
const hasChanges = ref(false)

const projectGrades = [
  { id: 1, name: '高一' },
  { id: 2, name: '高二' },
  { id: 3, name: '高三' }
]

const activeGradeId = ref('1')
const selectedRows = ref([])

// 弹窗
const createProjectVisible = ref(false)
const importVisible = ref(false)
const notificationLogsVisible = ref(false)
const importLoading = ref(false)
const importFile = ref(null)
const notificationLogs = ref([])

// 表单
const projectFormRef = ref(null)
const projectForm = reactive({
  name: '',
  school_year: '',
  semester: '',
  date_range: null,
  grade_ids: [1, 2, 3]
})

const projectRules = {
  name: [{ required: true, message: '请输入考试名称', trigger: 'blur' }],
  grade_ids: [{ required: true, message: '请选择参与年级', trigger: 'change' }]
}

// 初始化
onMounted(async () => {
  await loadProjects()
  await loadTeachers()
})

async function loadProjects() {
  try {
    const res = await api.get('/api/invigilation/projects')
    if (res.success) {
      projects.value = res.data
    }
  } catch (e) {
    console.error('加载项目失败:', e)
  }
}

async function loadTeachers() {
  try {
    const res = await api.get('/api/invigilation/teachers')
    if (res.success) {
      teachers.value = res.data
    }
  } catch (e) {
    console.error('加载教师失败:', e)
  }
}

async function loadProjectSlots() {
  if (!selectedProjectId.value) {
    currentProject.value = null
    slots.value = []
    return
  }

  try {
    // 加载项目详情
    const projectRes = await api.get(`/api/invigilation/projects/${selectedProjectId.value}`)
    if (projectRes.success) {
      currentProject.value = projectRes.data
    }

    // 加载安排
    const slotsRes = await api.get(`/api/invigilation/projects/${selectedProjectId.value}/slots`)
    if (slotsRes.success) {
      slots.value = slotsRes.data
      hasChanges.value = false
    }
  } catch (e) {
    console.error('加载安排失败:', e)
    ElMessage.error('加载安排失败')
  }
}

// 项目操作
function showCreateProjectDialog() {
  projectForm.name = ''
  projectForm.school_year = ''
  projectForm.semester = ''
  projectForm.date_range = null
  projectForm.grade_ids = [1, 2, 3]
  createProjectVisible.value = true
}

async function createProject() {
  try {
    await projectFormRef.value.validate()

    const data = {
      name: projectForm.name,
      school_year: projectForm.school_year,
      semester: projectForm.semester,
      start_date: projectForm.date_range?.[0],
      end_date: projectForm.date_range?.[1],
      grade_ids: projectForm.grade_ids
    }

    const res = await api.post('/api/invigilation/projects', data)
    if (res.success) {
      ElMessage.success('创建成功')
      createProjectVisible.value = false
      await loadProjects()
      selectedProjectId.value = res.data.id
      await loadProjectSlots()
    }
  } catch (e) {
    console.error('创建失败:', e)
  }
}

// 安排操作
function getGradeSlots(gradeId) {
  return slots.value.filter(s => s.grade_id === gradeId)
}

function addSlot(gradeId) {
  const newSlot = {
    grade_id: gradeId,
    grade_name: projectGrades.find(g => g.id === gradeId)?.name,
    exam_date: currentProject.value?.start_date || '',
    start_time: '08:00',
    end_time: '10:00',
    subject: '',
    room_name: '',
    room_order: 0,
    teacher_id: '',
    teacher_name: ''
  }
  slots.value.push(newSlot)
  hasChanges.value = true
}

function batchAddSlots(gradeId) {
  ElMessageBox.prompt('请输入考场数量', '批量新增', {
    inputPattern: /^[1-9]\d*$/,
    inputErrorMessage: '请输入正整数'
  }).then(({ value }) => {
    const count = parseInt(value)
    for (let i = 1; i <= count; i++) {
      addSlot(gradeId)
      const lastSlot = slots.value[slots.value.length - 1]
      lastSlot.room_name = `第${i}考场`
      lastSlot.room_order = i
    }
  }).catch(() => {})
}

function deleteSlot(gradeId, index) {
  const gradeSlots = getGradeSlots(gradeId)
  const globalIndex = slots.value.indexOf(gradeSlots[index])
  slots.value.splice(globalIndex, 1)
  hasChanges.value = true
}

function handleSelectionChange(rows) {
  selectedRows.value = rows
}

function swapTeachers() {
  if (selectedRows.value.length !== 2) {
    ElMessage.warning('请选择两条安排')
    return
  }

  const [row1, row2] = selectedRows.value
  const tempTeacherId = row1.teacher_id
  const tempTeacherName = row1.teacher_name

  row1.teacher_id = row2.teacher_id
  row1.teacher_name = row2.teacher_name
  row2.teacher_id = tempTeacherId
  row2.teacher_name = tempTeacherName

  hasChanges.value = true
  selectedRows.value = []
  ElMessage.success('已交换')
}

function updateTeacherName(row) {
  const teacher = teachers.value.find(t => t.teacher_id === row.teacher_id)
  if (teacher) {
    row.teacher_name = teacher.name
  }
  markChanged()
}

function markChanged() {
  hasChanges.value = true
}

// 保存
async function saveSlots() {
  if (!selectedProjectId.value) return

  try {
    const res = await api.put(`/api/invigilation/projects/${selectedProjectId.value}/slots`, {
      slots: slots.value
    })
    if (res.success) {
      ElMessage.success('保存成功')
      hasChanges.value = false
      await loadProjectSlots()
    }
  } catch (e) {
    console.error('保存失败:', e)
    ElMessage.error('保存失败')
  }
}

// 通知
async function sendNotifications() {
  try {
    await saveSlots()

    const res = await api.post(`/api/invigilation/projects/${selectedProjectId.value}/notify`)
    if (res.success) {
      ElMessage.success(`通知发送完成: 成功${res.data.success}, 失败${res.data.failed}, 跳过${res.data.skipped}`)
      await loadProjectSlots()
    }
  } catch (e) {
    console.error('通知失败:', e)
    ElMessage.error('通知发送失败')
  }
}

function showNotificationLogs() {
  loadNotificationLogs()
  notificationLogsVisible.value = true
}

async function loadNotificationLogs() {
  try {
    const res = await api.get(`/api/invigilation/projects/${selectedProjectId.value}/notification-logs`)
    if (res.success) {
      notificationLogs.value = res.data
    }
  } catch (e) {
    console.error('加载日志失败:', e)
  }
}

// Excel
async function downloadTemplate() {
  try {
    const response = await api.get('/api/invigilation/template', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '监考安排模板.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    console.error('下载模板失败:', e)
    ElMessage.error('下载失败')
  }
}

function showImportDialog() {
  importFile.value = null
  importVisible.value = true
}

function handleFileChange(file) {
  importFile.value = file.raw
}

async function importExcel() {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  importLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', importFile.value)

    const res = await api.post(`/api/invigilation/projects/${selectedProjectId.value}/import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    if (res.success) {
      ElMessage.success(`导入成功，共${res.data.count}条`)
      importVisible.value = false
      await loadProjectSlots()
    } else {
      ElMessage.error(`导入有错误: ${res.data.error_count}条`)
      if (res.data.errors?.length > 0) {
        ElMessageBox.alert(res.data.errors.join('\n'), '导入错误', { type: 'error' })
      }
    }
  } catch (e) {
    console.error('导入失败:', e)
    ElMessage.error('导入失败')
  } finally {
    importLoading.value = false
  }
}

async function exportExcel() {
  try {
    const response = await api.get(`/api/invigilation/projects/${selectedProjectId.value}/export`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${currentProject.value?.name || '监考安排'}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    console.error('导出失败:', e)
    ElMessage.error('导出失败')
  }
}

async function exportReport() {
  try {
    const response = await api.get(`/api/invigilation/projects/${selectedProjectId.value}/report`, { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${currentProject.value?.name || '监考'}_工作量报表.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('报表导出成功')
  } catch (e) {
    console.error('报表导出失败:', e)
    ElMessage.error('报表导出失败')
  }
}

// 状态
function getStatusType(status) {
  const map = { draft: 'info', saved: 'primary', notified: 'success', archived: 'default' }
  return map[status] || 'info'
}

function getStatusName(status) {
  const map = { draft: '草稿', saved: '已保存', notified: '已通知', archived: '已归档' }
  return map[status] || status
}
</script>

<style scoped>
.invigilation-page {
  padding: 20px;
}

.toolbar-card {
  margin-bottom: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toolbar-left {
  display: flex;
  gap: 10px;
  align-items: center;
}

.toolbar-right {
  display: flex;
  gap: 10px;
}

.project-info-card {
  margin-bottom: 20px;
}

.project-info {
  display: flex;
  gap: 30px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item .label {
  color: #666;
}

.info-item .value {
  font-weight: 500;
}

.slots-card {
  margin-bottom: 20px;
}

.grade-toolbar {
  margin-bottom: 15px;
  display: flex;
  gap: 10px;
}
</style>