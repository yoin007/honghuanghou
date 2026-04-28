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
          <el-button type="warning" @click="showNotifyDialog" :disabled="!selectedProjectId">发送通知</el-button>
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
        <div class="info-item">
          <el-button type="danger" size="small" @click="confirmDeleteProject">删除项目</el-button>
        </div>
      </div>
    </el-card>

    <!-- 年级Tabs -->
    <el-card v-if="selectedProjectId" class="slots-card">
      <el-tabs v-model="activeGradeId" type="card">
        <el-tab-pane v-for="grade in visibleGrades" :key="grade.id" :label="grade.name" :name="String(grade.id)">
          <!-- 横向布局表格 -->
          <div class="horizontal-table-wrapper">
            <table class="horizontal-table" v-if="horizontalSlots[grade.id]?.length">
              <thead>
                <tr>
                  <th class="th-date">日期</th>
                  <th class="th-time">时间</th>
                  <th class="th-subject">学科</th>
                  <th v-for="room in maxRooms[grade.id]" :key="room" class="th-room">考场{{ room }}</th>
                  <th class="th-actions">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in horizontalSlots[grade.id]" :key="rowIndex">
                  <td>
                    <el-date-picker
                      v-model="row.exam_date"
                      type="date"
                      value-format="YYYY-MM-DD"
                      size="small"
                      style="width: 120px"
                      @change="markChanged"
                    />
                  </td>
                  <td>
                    <div class="time-inputs">
                      <el-input v-model="row.start_time" size="small" placeholder="08:00" style="width: 70px" @change="markChanged" />
                      <span>-</span>
                      <el-input v-model="row.end_time" size="small" placeholder="10:00" style="width: 70px" @change="markChanged" />
                    </div>
                  </td>
                  <td>
                    <el-input v-model="row.subject" size="small" placeholder="语文" style="width: 100px" @change="markChanged" />
                  </td>
                  <td v-for="room in maxRooms[grade.id]" :key="room" class="td-teacher">
                    <div
                      class="teacher-cell"
                      draggable="true"
                      @dragstart="handleDragStart($event, grade.id, rowIndex, room)"
                      @dragover.prevent
                      @drop="handleDrop($event, grade.id, rowIndex, room)"
                    >
                      <el-select
                        v-model="row.teachers[room]"
                        placeholder="选择教师"
                        size="small"
                        filterable
                        style="width: 100%"
                        @change="markChanged"
                      >
                        <el-option v-for="t in teachers" :key="t.teacher_id" :label="t.name" :value="t.teacher_id" />
                      </el-select>
                    </div>
                  </td>
                  <td>
                    <el-button type="danger" size="small" link @click="deleteRow(grade.id, rowIndex)">删除</el-button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="empty-hint">暂无安排，请导入Excel或新增</div>
          </div>

          <!-- 操作栏 -->
          <div class="grade-toolbar">
            <el-button type="primary" size="small" @click="addRow(grade.id)">新增行</el-button>
            <el-button size="small" @click="addRoom(grade.id)">新增考场</el-button>
            <el-button size="small" @click="removeRoom(grade.id)" :disabled="maxRooms[grade.id] <= 1">减少考场</el-button>
            <span class="drag-hint">💡 拖拽教师姓名可互换监考安排</span>
          </div>
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

    <!-- 发送通知弹窗 -->
    <el-dialog v-model="notifyDialogVisible" title="发送监考通知" width="800px">
      <!-- 学科筛选 -->
      <div class="notify-filter">
        <div class="filter-label">选择学科：</div>
        <el-checkbox-group v-model="selectedSubjects">
          <el-checkbox label="">全部</el-checkbox>
          <el-checkbox v-for="sub in allSubjects" :key="sub" :label="sub">{{ sub }}</el-checkbox>
        </el-checkbox-group>
      </div>

      <!-- 变更预览 -->
      <div v-if="changesPreview" class="changes-preview">
        <el-divider>变更预览</el-divider>
        <div class="changes-stats">
          <el-tag type="success">新增 {{ changesPreview.stats.added_count }}人</el-tag>
          <el-tag type="danger">取消 {{ changesPreview.stats.removed_count }}人</el-tag>
          <el-tag type="info">互换 {{ changesPreview.stats.swapped_count }}对</el-tag>
          <el-tag>无变化 {{ changesPreview.stats.unchanged_count }}人</el-tag>
        </div>

        <!-- 新增列表 -->
        <div v-if="changesPreview.added.length" class="change-section">
          <div class="section-title">新增监考</div>
          <el-table :data="changesPreview.added" size="small" border>
            <el-table-column prop="teacher_name" label="教师" width="100" />
            <el-table-column label="安排">
              <template #default="{ row }">
                {{ row.slot.exam_date }} {{ row.slot.start_time }}-{{ row.slot.end_time }} {{ row.slot.subject }} {{ row.slot.grade_name }} {{ row.slot.room_name }}
              </template>
            </el-table-column>
            <el-table-column prop="teacher_wxid" label="wxid" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.teacher_wxid" type="success" size="small">有</el-tag>
                <el-tag v-else type="danger" size="small">无</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 取消列表 -->
        <div v-if="changesPreview.removed.length" class="change-section">
          <div class="section-title">取消监考</div>
          <el-table :data="changesPreview.removed" size="small" border>
            <el-table-column prop="teacher_name" label="教师" width="100" />
            <el-table-column label="原安排">
              <template #default="{ row }">
                {{ row.slot.exam_date }} {{ row.slot.start_time }}-{{ row.slot.end_time }} {{ row.slot.subject }} {{ row.slot.grade_name }} {{ row.slot.room_name }}
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" width="80" />
          </el-table>
        </div>

        <!-- 互换列表 -->
        <div v-if="changesPreview.swapped && changesPreview.swapped.length" class="change-section">
          <div class="section-title">教师互换</div>
          <el-table :data="changesPreview.swapped" size="small" border>
            <el-table-column prop="teacher_a_name" label="教师A" width="100" />
            <el-table-column prop="teacher_b_name" label="教师B" width="100" />
            <el-table-column label="A原位置">
              <template #default="{ row }">
                {{ row.slot_a.exam_date }} {{ row.slot_a.subject }} {{ row.slot_a.room_name }}
              </template>
            </el-table-column>
            <el-table-column label="B原位置">
              <template #default="{ row }">
                {{ row.slot_b.exam_date }} {{ row.slot_b.subject }} {{ row.slot_b.room_name }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div v-else class="preview-loading">
        <el-button @click="loadChangesPreview" :loading="previewLoading">加载变更预览</el-button>
      </div>

      <!-- 通知选项 -->
      <div class="notify-options">
        <el-checkbox v-model="notifyOptions.notify_added">通知新增监考的教师</el-checkbox>
        <el-checkbox v-model="notifyOptions.notify_removed">通知取消监考的教师</el-checkbox>
        <el-checkbox v-model="notifyOptions.notify_changed">通知变更的教师（双方）</el-checkbox>
        <el-checkbox v-model="notifyOptions.notify_reminder">发送提醒给无变化教师</el-checkbox>
      </div>

      <template #footer>
        <el-button @click="notifyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="sendNotificationsV2" :loading="notifySending" :disabled="!changesPreview">
          确认发送
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import api from '@/utils/api'

// 数据
const projects = ref([])
const selectedProjectId = ref(null)
const currentProject = ref(null)
const slots = ref([])  // 原始纵向数据
const horizontalSlots = ref({})  // 转换后的横向数据
const maxRooms = ref({ 1: 1, 2: 1, 3: 1 })  // 每个年级的考场数量
const teachers = ref([])
const hasChanges = ref(false)

const projectGrades = [
  { id: 1, name: '高一' },
  { id: 2, name: '高二' },
  { id: 3, name: '高三' }
]

// 根据项目的grade_ids过滤显示的年级
const visibleGrades = computed(() => {
  if (!currentProject.value || !currentProject.value.grade_ids) {
    return projectGrades  // 无项目时显示全部
  }
  return projectGrades.filter(g => currentProject.value.grade_ids.includes(g.id))
})

const activeGradeId = ref('1')

// 拖拽状态
const dragState = ref({ gradeId: null, rowIndex: null, room: null, teacherId: null })

// 弹窗
const createProjectVisible = ref(false)
const importVisible = ref(false)
const notificationLogsVisible = ref(false)
const notifyDialogVisible = ref(false)
const importLoading = ref(false)
const importFile = ref(null)
const notificationLogs = ref([])

// 通知弹窗数据
const selectedSubjects = ref([])
const allSubjects = ref([])
const changesPreview = ref(null)
const previewLoading = ref(false)
const notifySending = ref(false)
const notifyOptions = reactive({
  notify_added: true,
  notify_removed: true,
  notify_changed: true,
  notify_reminder: false
})

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
    horizontalSlots.value = {}
    return
  }

  try {
    const projectRes = await api.get(`/api/invigilation/projects/${selectedProjectId.value}`)
    if (projectRes.success) {
      currentProject.value = projectRes.data
      // 自动选择第一个可用年级
      const gradeIds = currentProject.value.grade_ids || [1, 2, 3]
      if (!gradeIds.includes(parseInt(activeGradeId.value))) {
        activeGradeId.value = String(gradeIds[0])
      }
    }

    const slotsRes = await api.get(`/api/invigilation/projects/${selectedProjectId.value}/slots`)
    if (slotsRes.success) {
      slots.value = slotsRes.data
      convertToHorizontal()
      hasChanges.value = false
    }
  } catch (e) {
    console.error('加载安排失败:', e)
    ElMessage.error('加载安排失败')
  }
}

// 纵向数据转换为横向布局
function convertToHorizontal() {
  const result = {}
  const roomCounts = {}

  for (const grade of projectGrades) {
    const gradeSlots = slots.value.filter(s => s.grade_id === grade.id)
    if (gradeSlots.length === 0) {
      result[grade.id] = []
      roomCounts[grade.id] = 1
      continue
    }

    // 按 日期+时间+学科 分组
    const groups = {}
    let maxRoom = 0

    for (const slot of gradeSlots) {
      const key = `${slot.exam_date}|${slot.start_time}|${slot.end_time}|${slot.subject}`
      if (!groups[key]) {
        groups[key] = {
          exam_date: slot.exam_date,
          start_time: slot.start_time,
          end_time: slot.end_time,
          subject: slot.subject,
          teachers: {}
        }
      }
      // 从 room_name 提取考场号 (支持 "考场1" 和 "第1考场")
      const roomMatch = slot.room_name?.match(/\d+/)
      const roomNum = roomMatch ? parseInt(roomMatch[0]) : 1
      groups[key].teachers[roomNum] = slot.teacher_id
      maxRoom = Math.max(maxRoom, roomNum)
    }

    result[grade.id] = Object.values(groups)
    roomCounts[grade.id] = Math.max(maxRoom, 1)  // 最少1个考场，根据实际数据
  }

  horizontalSlots.value = result
  maxRooms.value = roomCounts
}

// 横向数据转换为纵向（用于保存）
function convertToVertical() {
  const result = []

  for (const gradeId of [1, 2, 3]) {
    const rows = horizontalSlots.value[gradeId] || []
    for (const row of rows) {
      for (const room of Object.keys(row.teachers || {})) {
        const teacherId = row.teachers[room]
        if (teacherId) {
          result.push({
            grade_id: gradeId,
            grade_name: projectGrades.find(g => g.id === gradeId)?.name,
            exam_date: row.exam_date,
            start_time: row.start_time,
            end_time: row.end_time,
            subject: row.subject,
            room_name: `考场${room}`,
            room_order: parseInt(room),
            teacher_id: teacherId,
            teacher_name: teachers.value.find(t => t.teacher_id === teacherId)?.name || ''
          })
        }
      }
    }
  }

  return result
}

// 拖拽处理
function handleDragStart(event, gradeId, rowIndex, room) {
  const teacherId = horizontalSlots.value[gradeId]?.[rowIndex]?.teachers?.[room]
  if (!teacherId) {
    event.preventDefault()
    return
  }
  dragState.value = { gradeId, rowIndex, room, teacherId }
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', teacherId)
}

function handleDrop(event, targetGradeId, targetRowIndex, targetRoom) {
  const source = dragState.value
  if (!source.teacherId) return

  // 不能拖到同一个格子
  if (source.gradeId === targetGradeId && source.rowIndex === targetRowIndex && source.room === targetRoom) {
    return
  }

  // 互换教师
  const targetTeacherId = horizontalSlots.value[targetGradeId]?.[targetRowIndex]?.teachers?.[targetRoom]

  // 设置目标格子
  horizontalSlots.value[targetGradeId][targetRowIndex].teachers[targetRoom] = source.teacherId

  // 设置源格子
  if (horizontalSlots.value[source.gradeId]?.[source.rowIndex]?.teachers) {
    horizontalSlots.value[source.gradeId][source.rowIndex].teachers[source.room] = targetTeacherId || null
  }

  hasChanges.value = true
  dragState.value = {}

  // 提示互换
  const sourceName = teachers.value.find(t => t.teacher_id === source.teacherId)?.name
  const targetName = targetTeacherId ? teachers.value.find(t => t.teacher_id === targetTeacherId)?.name : '空'
  ElMessage.success(`已互换: ${sourceName} ↔ ${targetName}`)
}

// 行操作
function addRow(gradeId) {
  const rows = horizontalSlots.value[gradeId] || []
  const newRow = {
    exam_date: currentProject.value?.start_date || '',
    start_time: '08:00',
    end_time: '10:00',
    subject: '',
    teachers: {}
  }
  // 预填充空值
  for (let i = 1; i <= maxRooms.value[gradeId]; i++) {
    newRow.teachers[i] = null
  }
  rows.push(newRow)
  horizontalSlots.value[gradeId] = rows
  hasChanges.value = true
}

function deleteRow(gradeId, rowIndex) {
  horizontalSlots.value[gradeId].splice(rowIndex, 1)
  hasChanges.value = true
}

// 考场操作
function addRoom(gradeId) {
  maxRooms.value[gradeId]++
  // 为所有行补充新考场列
  for (const row of (horizontalSlots.value[gradeId] || [])) {
    row.teachers[maxRooms.value[gradeId]] = null
  }
  hasChanges.value = true
}

function removeRoom(gradeId) {
  if (maxRooms.value[gradeId] <= 1) return
  const removedRoom = maxRooms.value[gradeId]
  // 清除该考场数据
  for (const row of (horizontalSlots.value[gradeId] || [])) {
    delete row.teachers[removedRoom]
  }
  maxRooms.value[gradeId]--
  hasChanges.value = true
}

function markChanged() {
  hasChanges.value = true
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

// 保存
async function saveSlots() {
  if (!selectedProjectId.value) return

  try {
    const verticalSlots = convertToVertical()
    const res = await api.put(`/api/invigilation/projects/${selectedProjectId.value}/slots`, {
      slots: verticalSlots
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
function showNotifyDialog() {
  // 提取所有学科
  const subjects = new Set()
  for (const gradeId of [1, 2, 3]) {
    const rows = horizontalSlots.value[gradeId] || []
    for (const row of rows) {
      if (row.subject) subjects.add(row.subject)
    }
  }
  allSubjects.value = Array.from(subjects)
  selectedSubjects.value = []
  changesPreview.value = null
  notifyDialogVisible.value = true
}

async function loadChangesPreview() {
  if (!selectedProjectId.value) return

  previewLoading.value = true
  try {
    // 构建学科筛选参数
    const params = selectedSubjects.value.length > 0
      ? { subjects: selectedSubjects.value.join(',') }
      : {}

    const res = await api.get(`/api/invigilation/projects/${selectedProjectId.value}/changes`, { params })
    if (res.success) {
      changesPreview.value = res.data
    }
  } catch (e) {
    console.error('加载变更预览失败:', e)
    ElMessage.error('加载变更预览失败')
  } finally {
    previewLoading.value = false
  }
}

async function sendNotificationsV2() {
  if (!selectedProjectId.value || !changesPreview.value) return

  notifySending.value = true
  try {
    const body = {
      subjects: selectedSubjects.value.length > 0 ? selectedSubjects.value : null,
      notify_added: notifyOptions.notify_added,
      notify_removed: notifyOptions.notify_removed,
      notify_changed: notifyOptions.notify_changed,
      notify_reminder: notifyOptions.notify_reminder
    }

    const res = await api.post(`/api/invigilation/projects/${selectedProjectId.value}/notify`, body)
    if (res.success) {
      const stats = res.data
      ElMessage.success(`通知发送完成: 成功${stats.success}, 失败${stats.failed}, 跳过${stats.skipped}`)
      notifyDialogVisible.value = false
      await loadProjectSlots()
    }
  } catch (e) {
    console.error('通知发送失败:', e)
    ElMessage.error('通知发送失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    notifySending.value = false
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

// 删除项目（两次确认）
async function confirmDeleteProject() {
  if (!selectedProjectId.value || !currentProject.value) return

  const projectName = currentProject.value.name

  // 第一次确认
  try {
    await ElMessageBox.confirm(
      `确定要删除考试项目「${projectName}」吗？\n\n这将删除该项目下所有监考安排数据！`,
      '删除确认（第一步）',
      {
        confirmButtonText: '继续删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    // 第二次确认
    await ElMessageBox.confirm(
      `⚠️ 最后确认：删除「${projectName}」\n\n此操作不可恢复，所有监考安排、通知日志将永久删除！`,
      '删除确认（第二步）',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'error',
      }
    )

    // 执行删除
    const res = await api.delete(`/api/invigilation/projects/${selectedProjectId.value}`)
    if (res.success) {
      ElMessage.success('项目已删除')
      selectedProjectId.value = null
      currentProject.value = null
      slots.value = []
      horizontalSlots.value = {}
      await loadProjects()
    }
  } catch (e) {
    if (e !== 'cancel' && e !== 'close') {
      console.error('删除失败:', e)
      ElMessage.error('删除失败')
    }
  }
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

/* 横向表格样式 */
.horizontal-table-wrapper {
  overflow-x: auto;
}

.horizontal-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 15px;
}

.horizontal-table th,
.horizontal-table td {
  border: 1px solid #ddd;
  padding: 8px;
  text-align: center;
  min-width: 100px;
}

.horizontal-table th {
  background: #f5f7fa;
  font-weight: 500;
}

.horizontal-table tbody tr:hover {
  background: #f9f9f9;
}

.th-date { min-width: 140px; }
.th-time { min-width: 160px; }
.th-subject { min-width: 120px; }
.th-room { min-width: 120px; }
.th-actions { min-width: 80px; }

.td-teacher {
  position: relative;
}

.teacher-cell {
  cursor: grab;
}

.teacher-cell:active {
  cursor: grabbing;
}

.teacher-cell.dragging {
  opacity: 0.5;
}

.time-inputs {
  display: flex;
  align-items: center;
  gap: 4px;
  justify-content: center;
}

.time-inputs span {
  color: #999;
}

.grade-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.drag-hint {
  color: #909399;
  font-size: 12px;
  margin-left: 20px;
}

.empty-hint {
  text-align: center;
  color: #999;
  padding: 40px;
}

/* 通知弹窗样式 */
.notify-filter {
  margin-bottom: 20px;
}

.filter-label {
  font-weight: 500;
  margin-bottom: 10px;
}

.changes-preview {
  margin: 20px 0;
}

.changes-stats {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
}

.change-section {
  margin-bottom: 15px;
}

.section-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #409eff;
}

.notify-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.preview-loading {
  text-align: center;
  padding: 40px;
}
</style>