<template>
  <div class="daily-record-page">
    <!-- 数据范围选项卡 -->
    <MoralScopeTabs
      module="daily_records"
      @change="handleScopeChange"
      @ready="handleScopeReady"
    />

    <!-- 日常记录 / 待完善记录 选项卡 -->
    <el-tabs v-model="activeTab" class="record-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="日常记录" name="daily" />
      <el-tab-pane label="待完善记录" name="pending" />
    </el-tabs>

    <!-- ==================== 日常记录视图 ==================== -->
    <template v-if="activeTab === 'daily'">
      <el-card class="filter-card">
        <el-form :inline="true" :model="filterForm" class="filter-form">
          <el-form-item label="学生学号">
            <el-input v-model="filterForm.student_id" placeholder="输入学号" clearable />
          </el-form-item>
          <el-form-item label="班级">
            <el-select v-model="filterForm.class_id" placeholder="选择班级" clearable>
              <el-option
                v-for="cls in classList"
                :key="cls.class_id"
                :label="cls.class_name"
                :value="cls.class_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="事件类型">
            <el-select v-model="filterForm.event_type" placeholder="选择类型" clearable>
              <el-option label="积极事件" :value="1" />
              <el-option label="消极事件" :value="2" />
            </el-select>
          </el-form-item>
          <el-form-item label="事件">
            <el-select v-model="filterForm.event_id" placeholder="选择事件" clearable filterable>
              <el-option-group label="积极事件">
                <el-option
                  v-for="event in positiveEvents"
                  :key="event.event_id"
                  :label="event.event_name"
                  :value="event.event_id"
                />
              </el-option-group>
              <el-option-group label="消极事件">
                <el-option
                  v-for="event in negativeEvents"
                  :key="event.event_id"
                  :label="event.event_name"
                  :value="event.event_id"
                />
              </el-option-group>
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
            <span>日常表现记录</span>
            <div class="header-actions">
              <el-button @click="handleExport">导出</el-button>
              <el-button type="warning" @click="handleAddPending" v-if="isXuefa">待完善记录</el-button>
              <el-button type="primary" @click="handleAdd" v-if="canCreateDailyRecord">新增记录</el-button>
              <el-button @click="handleBatchAdd" v-if="canBatchCreateDailyRecord">批量录入</el-button>
            </div>
          </div>
        </template>

        <el-table :data="recordList" v-loading="loading" stripe>
          <el-table-column prop="student_id" label="学号" width="120" />
          <el-table-column prop="student_name" label="姓名" width="100" />
          <el-table-column prop="class_name" label="班级" width="150" />
          <el-table-column prop="event_name" label="事件" width="120" />
          <el-table-column label="类型" width="80">
            <template #default="{ row }">
              <el-tag :type="row.event_type === 1 ? 'success' : 'danger'">
                {{ row.event_type === 1 ? '积极' : '消极' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="分值" width="80">
            <template #default="{ row }">
              <span :class="row.score > 0 ? 'score-positive' : 'score-negative'">
                {{ row.score > 0 ? '+' : '' }}{{ row.score }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="记录人" width="100">
            <template #default="{ row }">
              {{ row.recorder_name || row.recorder || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="record_date" label="时间" width="160" />
          <el-table-column prop="remark" label="备注" show-overflow-tooltip />
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleEdit(row)" v-if="canUpdateDailyRecord && row.can_edit">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(row)" v-if="canDeleteDailyRecord && row.can_delete">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchRecords"
          @current-change="fetchRecords"
          class="pagination"
        />
      </el-card>
    </template>

    <!-- ==================== 待完善记录视图 ==================== -->
    <template v-if="activeTab === 'pending'">
      <el-card class="table-card">
        <template #header>
          <div class="card-header">
            <span>待完善记录</span>
            <div class="header-actions">
              <el-button type="primary" @click="handleAddPending" v-if="isXuefa">待完善记录</el-button>
            </div>
          </div>
        </template>

        <el-table :data="pendingList" v-loading="pendingLoading" stripe>
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="class_name" label="班级" width="150" />
          <el-table-column prop="student_count" label="学生数" width="80" />
          <el-table-column prop="event_name" label="事件" width="120" />
          <el-table-column prop="teacher_name" label="任课教师" width="100" />
          <el-table-column prop="record_date" label="时间" width="160" />
          <el-table-column prop="remark" label="备注" show-overflow-tooltip />
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_completed ? 'success' : 'warning'">
                {{ row.is_completed ? '已完善' : '待完善' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="160" fixed="right">
            <template #default="{ row }">
              <el-button v-if="!row.is_completed" link type="primary" @click="handleComplete(row)">完善</el-button>
              <el-button v-if="canDeletePending" link type="danger" @click="handleDeletePending(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="pendingPagination.page"
          v-model:page-size="pendingPagination.pageSize"
          :total="pendingPagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchPendingRecords"
          @current-change="fetchPendingRecords"
          class="pagination"
        />
      </el-card>
    </template>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="recordForm" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="班级" prop="class_id">
          <el-select v-model="recordForm.class_id" placeholder="选择班级" style="width: 100%" @change="handleClassChange" filterable>
            <el-option-group v-for="grade in gradeList" :key="grade.grade_id" :label="grade.grade_name">
              <el-option
                v-for="cls in classList.filter(c => c.grade_id === grade.grade_id)"
                :key="cls.class_id"
                :label="cls.class_name"
                :value="cls.class_id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="学生" prop="student_ids">
          <el-select
            v-model="recordForm.student_ids"
            placeholder="选择学生（可多选）"
            style="width: 100%"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            :disabled="!recordForm.class_id || !!recordForm.record_id"
          >
            <el-option
              v-for="student in classStudents"
              :key="student.student_id"
              :label="`${student.student_id} - ${student.name}`"
              :value="student.student_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="事件类型" prop="event_id">
          <el-select v-model="recordForm.event_id" placeholder="选择事件类型" style="width: 100%" filterable>
            <el-option-group label="积极事件">
              <el-option
                v-for="event in positiveEvents"
                :key="event.event_id"
                :label="`${event.event_name} (+${event.score})`"
                :value="event.event_id"
              />
            </el-option-group>
            <el-option-group label="消极事件">
              <el-option
                v-for="event in negativeEvents"
                :key="event.event_id"
                :label="`${event.event_name} (${event.score})`"
                :value="event.event_id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="时间" prop="record_date">
          <el-date-picker
            v-model="recordForm.record_date"
            type="datetime"
            placeholder="选择时间"
            style="width: 100%"
            value-format="YYYY-MM-DD HH:mm"
            format="YYYY-MM-DD HH:mm"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="recordForm.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 待完善记录对话框 -->
    <el-dialog v-model="pendingDialogVisible" title="待完善记录" width="600px">
      <el-form :model="pendingForm" :rules="pendingRules" ref="pendingFormRef" label-width="90px">
        <el-form-item label="班级" prop="class_id">
          <el-select v-model="pendingForm.class_id" placeholder="选择班级" style="width: 100%" filterable>
            <el-option-group v-for="grade in gradeList" :key="grade.grade_id" :label="grade.grade_name">
              <el-option
                v-for="cls in classList.filter(c => c.grade_id === grade.grade_id)"
                :key="cls.class_id"
                :label="cls.class_name"
                :value="cls.class_id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="学生数" prop="student_count">
          <el-input-number v-model="pendingForm.student_count" :min="1" :max="50" style="width: 100%" />
        </el-form-item>
        <el-form-item label="事件类型" prop="event_id">
          <el-select v-model="pendingForm.event_id" placeholder="选择事件类型" style="width: 100%" filterable>
            <el-option-group label="积极事件">
              <el-option
                v-for="event in positiveEvents"
                :key="event.event_id"
                :label="`${event.event_name} (+${event.score})`"
                :value="event.event_id"
              />
            </el-option-group>
            <el-option-group label="消极事件">
              <el-option
                v-for="event in negativeEvents"
                :key="event.event_id"
                :label="`${event.event_name} (${event.score})`"
                :value="event.event_id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="任课教师">
          <el-select
            v-model="pendingForm.teacher_name"
            placeholder="输入姓名搜索"
            style="width: 100%"
            filterable
            clearable
          >
            <el-option
              v-for="t in teacherOptions"
              :key="t.name"
              :label="t.subject ? `${t.name}(${t.subject})` : t.name"
              :value="t.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="时间" prop="record_date">
          <el-date-picker
            v-model="pendingForm.record_date"
            type="datetime"
            placeholder="选择时间"
            style="width: 100%"
            value-format="YYYY-MM-DD HH:mm"
            format="YYYY-MM-DD HH:mm"
          />
        </el-form-item>
        <el-form-item label="图片">
          <el-upload
            v-model:file-list="pendingFileList"
            action=""
            :http-request="handlePendingUpload"
            list-type="picture-card"
            accept="image/*"
            multiple
          >
            <el-icon><Plus /></el-icon>
          </el-upload>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="pendingForm.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pendingDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handlePendingSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 完善待完善记录对话框 -->
    <el-dialog v-model="completeDialogVisible" title="完善待完善记录" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="班级">{{ completeRecord.class_name }}</el-descriptions-item>
        <el-descriptions-item label="学生数">{{ completeRecord.student_count }}</el-descriptions-item>
        <el-descriptions-item label="事件">{{ completeRecord.event_name }}</el-descriptions-item>
        <el-descriptions-item label="任课教师">{{ completeRecord.teacher_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="时间">{{ completeRecord.record_date }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ completeRecord.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <!-- 图片展示 -->
      <div v-if="completeRecordImages.length" class="complete-images">
        <el-image
          v-for="(img, idx) in completeRecordImages"
          :key="idx"
          :src="img"
          :preview-src-list="completeRecordImages"
          :initial-index="idx"
          fit="cover"
          style="width: 120px; height: 120px; margin-right: 8px; border-radius: 4px;"
        />
      </div>

      <el-form :model="completeForm" :rules="completeRules" ref="completeFormRef" label-width="80px" style="margin-top: 16px;">
        <el-form-item label="学生" prop="student_ids">
          <el-select
            v-model="completeForm.student_ids"
            placeholder="选择学生（可多选）"
            style="width: 100%"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
          >
            <el-option
              v-for="student in completeClassStudents"
              :key="student.student_id"
              :label="`${student.student_id} - ${student.name}`"
              :value="student.student_id"
            />
          </el-select>
          <div class="student-count-tip">
            需选择 {{ completeRecord.student_count }} 名学生，已选 {{ completeForm.student_ids.length }} 名
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="completeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCompleteSubmit" :disabled="completeForm.student_ids.length !== completeRecord.student_count">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getDailyRecords,
  getDailyEventTypes,
  createDailyRecord,
  updateDailyRecord,
  deleteDailyRecord,
  getClasses,
  getGrades,
  getStudents,
  getPendingRecords,
  createPendingRecord,
  completePendingRecord,
  deletePendingRecord,
  uploadPendingImages,
  searchTeachers as searchTeachersApi
} from '@/api/modules/moral'
import { getGMT8TimeString } from '@/utils/time'
import { downloadRowsAsExcel } from '@/utils/filegather'
import { useApiPermission } from '@/composables/useApiPermission'
import { useAuthStore } from '@/stores/auth'
import MoralScopeTabs from '@/components/MoralScopeTabs.vue'

// 当前用户角色
const authStore = useAuthStore()
const currentUserRole = computed(() => authStore.role)
const isXuefa = computed(() => ['xuefa', 'admin'].includes(currentUserRole.value))
const canDeletePending = computed(() => ['xuefa', 'admin'].includes(currentUserRole.value))

// 选项卡
const activeTab = ref('daily')

// API权限
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canCreateDailyRecord = ref(false)
const canBatchCreateDailyRecord = ref(false)
const canUpdateDailyRecord = ref(false)
const canDeleteDailyRecord = ref(false)

// ====== 日常记录数据 ======
const loading = ref(false)
const recordList = ref([])
const classList = ref([])
const gradeList = ref([])
const classStudents = ref([])
const eventTypes = ref([])
const currentScope = ref(null)

const filterForm = reactive({
  student_id: '',
  class_id: null,
  event_type: null,
  event_id: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = computed(() => (recordForm.record_id ? '编辑记录' : '新增记录'))
const formRef = ref(null)

const recordForm = reactive({
  record_id: null,
  class_id: null,
  student_ids: [],
  event_id: null,
  record_date: '',
  remark: ''
})

// 拉取全量教师列表
const loadAllTeachers = async () => {
  try {
    const res = await searchTeachersApi({ keyword: '' })
    if (res.success) allTeacherList.value = teacherOptions.value = res.data
  } catch (error) {
    console.error('拉取教师列表失败:', error)
  }
}

const rules = {
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }],
  student_ids: [{ required: true, type: 'array', min: 1, message: '请选择至少一名学生', trigger: 'change' }],
  event_id: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  record_date: [{ required: true, message: '请选择日期', trigger: 'change' }]
}

const positiveEvents = computed(() =>
  eventTypes.value.filter(e => e.event_type === 1)
)
const negativeEvents = computed(() =>
  eventTypes.value.filter(e => e.event_type === 2)
)

// ====== 待完善记录数据 ======
const pendingLoading = ref(false)
const pendingList = ref([])
const pendingPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 待完善记录对话框
const pendingDialogVisible = ref(false)
const pendingFormRef = ref(null)
const pendingFileList = ref([])
const teacherOptions = ref([])
const allTeacherList = ref([])  // 全量教师数据，用于前端过滤

const pendingForm = reactive({
  class_id: null,
  student_count: 1,
  event_id: null,
  teacher_name: '',
  record_date: '',
  images: '',
  remark: ''
})

const pendingRules = {
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }],
  student_count: [{ required: true, message: '请输入学生数', trigger: 'change' }],
  event_id: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  record_date: [{ required: true, message: '请选择时间', trigger: 'change' }]
}

// 完善对话框
const completeDialogVisible = ref(false)
const completeFormRef = ref(null)
const completeRecord = ref({})
const completeRecordImages = ref([])
const completeClassStudents = ref([])

const completeForm = reactive({
  student_ids: []
})

const completeRules = {
  student_ids: [{ required: true, type: 'array', min: 1, message: '请选择学生', trigger: 'change' }]
}

// ====== 日常记录方法 ======
const fetchRecords = async () => {
  loading.value = true
  try {
    const params = {
      ...filterForm,
      page: pagination.page,
      page_size: pagination.pageSize
    }
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null) {
        delete params[key]
      }
    })
    if (currentScope.value) {
      params.scope = currentScope.value
    }
    const res = await getDailyRecords(params)
    if (res.success) {
      recordList.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error('获取记录失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchEventTypes = async () => {
  try {
    const res = await getDailyEventTypes()
    if (res.success) {
      eventTypes.value = res.data
    }
  } catch (error) {
    console.error('获取事件类型失败:', error)
  }
}

const fetchClassList = async () => {
  try {
    const res = await getClasses({ for_record_input: 1 })
    if (res.success) {
      classList.value = res.data
    }
  } catch (error) {
    console.error('获取班级列表失败:', error)
  }
}

const fetchGradeList = async () => {
  try {
    const res = await getGrades()
    if (res.success) {
      gradeList.value = res.data
    }
  } catch (error) {
    console.error('获取级号列表失败:', error)
  }
}

const handleClassChange = async (classId) => {
  recordForm.student_ids = []
  classStudents.value = []
  if (!classId) return
  try {
    const res = await getStudents({ class_id: classId, page_size: 10000, for_record_input: 1 })
    if (res.success) {
      classStudents.value = res.data.items || res.data || []
    }
  } catch (error) {
    console.error('获取班级学生失败:', error)
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchRecords()
}

const handleReset = () => {
  filterForm.student_id = ''
  filterForm.class_id = null
  filterForm.event_type = null
  filterForm.event_id = null
  handleSearch()
}

const handleAdd = () => {
  Object.assign(recordForm, {
    record_id: null,
    class_id: null,
    student_ids: [],
    event_id: null,
    record_date: getGMT8TimeString(),
    remark: ''
  })
  classStudents.value = []
  dialogVisible.value = true
}

const handleBatchAdd = () => {
  handleAdd()
}

const handleEdit = async (row) => {
  const studentClass = classList.value.find(c => c.class_name === row.class_name)
  const classId = studentClass?.class_id
  if (classId) {
    try {
      const res = await getStudents({ class_id: classId, page_size: 10000, for_record_input: 1 })
      if (res.success) {
        classStudents.value = res.data.items || res.data || []
      }
    } catch (error) {
      console.error('获取班级学生失败:', error)
    }
  }
  Object.assign(recordForm, {
    record_id: row.record_id,
    class_id: classId,
    student_ids: [row.student_id],
    event_id: row.event_id,
    record_date: row.record_date,
    remark: row.remark
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该记录吗？', '提示', { type: 'warning' })
    const res = await deleteDailyRecord(row.record_id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchRecords()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    if (recordForm.record_id) {
      const updateData = {
        remark: recordForm.remark,
        event_id: recordForm.event_id,
        record_date: recordForm.record_date
      }
      const res = await updateDailyRecord(recordForm.record_id, updateData)
      if (res.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        fetchRecords()
      } else {
        ElMessage.error(res.message || '更新失败')
      }
      return
    }

    const results = []
    let escalationMessages = []
    for (const studentId of recordForm.student_ids) {
      const res = await createDailyRecord({
        student_id: studentId,
        event_id: recordForm.event_id,
        record_date: recordForm.record_date,
        remark: recordForm.remark
      })
      results.push(res.success)
      if (res.success && res.message && res.message.includes('触发累进处罚')) {
        escalationMessages.push(res.message.replace('记录创建成功，', ''))
      }
    }
    const successCount = results.filter(r => r).length
    if (successCount > 0) {
      if (escalationMessages.length > 0) {
        ElMessage({
          type: 'warning',
          message: `成功创建 ${successCount} 条记录，触发累进处罚：\n${escalationMessages.join('\n')}`,
          duration: 5000,
          dangerouslyUseInnerHTMLString: false
        })
      } else {
        ElMessage.success(`成功创建 ${successCount} 条记录`)
      }
      dialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

const handleExport = async () => {
  const params = { ...filterForm, page_size: 10000 }
  Object.keys(params).forEach(key => {
    if (params[key] === '' || params[key] === null) {
      delete params[key]
    }
  })
  try {
    ElMessage.info('正在导出数据...')
    const res = await getDailyRecords(params)
    if (!res.success || !res.data.items || res.data.items.length === 0) {
      ElMessage.warning('暂无数据可导出')
      return
    }
    const exportData = res.data.items
    await downloadRowsAsExcel({
      filename: `日常表现记录_${new Date().toISOString().slice(0, 10)}`,
      sheetName: '日常表现记录',
      columns: [
        { header: '学号', key: 'student_id', width: 16 },
        { header: '姓名', key: 'student_name', width: 12 },
        { header: '班级', key: 'class_name', width: 16 },
        { header: '事件', key: 'event_name', width: 24 },
        { header: '类型', key: 'event_type_name', width: 10 },
        { header: '分值', key: 'score', width: 10 },
        { header: '时间', key: 'record_date', width: 18 },
        { header: '备注', key: 'remark', width: 30 }
      ],
      rows: exportData.map(row => ({
        ...row,
        event_type_name: row.event_type === 1 ? '积极' : '消极',
        remark: row.remark || ''
      }))
    })
    ElMessage.success(`导出成功，共 ${exportData.length} 条记录`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

const handleScopeChange = (scope) => {
  currentScope.value = scope
  pagination.page = 1
  fetchRecords()
}

const handleScopeReady = ({ tabs, defaultTab }) => {
  // 选项卡组件已通过 change 事件触发首次数据获取
}

// ====== 待完善记录方法 ======
const fetchPendingRecords = async () => {
  pendingLoading.value = true
  try {
    const res = await getPendingRecords({
      page: pendingPagination.page,
      page_size: pendingPagination.pageSize
    })
    if (res.success) {
      pendingList.value = res.data.items
      pendingPagination.total = res.data.total
    }
  } catch (error) {
    console.error('获取待完善记录失败:', error)
  } finally {
    pendingLoading.value = false
  }
}

const handleTabChange = (tab) => {
  if (tab === 'pending') {
    fetchPendingRecords()
  }
}

// 搜索教师
const searchTeachers = (query) => {
  if (!query) teacherOptions.value = allTeacherList.value
  else teacherOptions.value = allTeacherList.value.filter(t => t.name.startsWith(query))
}

// 上传待完善记录图片
const handlePendingUpload = async ({ file }) => {
  const formData = new FormData()
  formData.append('files', file)
  const res = await uploadPendingImages(formData)
  if (res.success && res.data && res.data.length > 0) {
    return { url: res.data[0] }
  }
  throw new Error('上传失败')
}

// 打开待完善记录对话框
const handleAddPending = () => {
  Object.assign(pendingForm, {
    class_id: null,
    student_count: 1,
    event_id: null,
    teacher_name: '',
    record_date: getGMT8TimeString(),
    images: '',
    remark: ''
  })
  pendingFileList.value = []
  loadAllTeachers()
  pendingDialogVisible.value = true
}

// 提交待完善记录
const handlePendingSubmit = async () => {
  try {
    await pendingFormRef.value.validate()

    // 收集已上传图片路径
    const imagePaths = pendingFileList.value
      .map(f => f.response?.url)
      .filter(Boolean)

    // 图片必填验证
    if (imagePaths.length === 0) {
      ElMessage.warning('请上传至少一张图片')
      return
    }

    const data = {
      class_id: pendingForm.class_id,
      student_count: pendingForm.student_count,
      event_id: pendingForm.event_id,
      teacher_name: pendingForm.teacher_name || '',
      record_date: pendingForm.record_date,
      images: JSON.stringify(imagePaths),
      remark: pendingForm.remark || ''
    }

    const res = await createPendingRecord(data)
    if (res.success) {
      ElMessage.success('待完善记录创建成功')
      pendingDialogVisible.value = false
      fetchPendingRecords()
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch (error) {
    console.error('提交待完善记录失败:', error)
  }
}

// 删除待完善记录
const handleDeletePending = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该待完善记录吗？', '提示', { type: 'warning' })
    const res = await deletePendingRecord(row.id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchPendingRecords()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除待完善记录失败:', error)
    }
  }
}

// 完善待完善记录
const handleComplete = async (row) => {
  completeRecord.value = row
  completeForm.student_ids = []
  completeClassStudents.value = []

  // 解析图片路径
  try {
    completeRecordImages.value = JSON.parse(row.images || '[]')
  } catch {
    completeRecordImages.value = []
  }

  // 获取班级学生
  if (row.class_id) {
    try {
      const res = await getStudents({ class_id: row.class_id, page_size: 10000, for_record_input: 1 })
      if (res.success) {
        completeClassStudents.value = res.data.items || res.data || []
      }
    } catch (error) {
      console.error('获取班级学生失败:', error)
    }
  }

  completeDialogVisible.value = true
}

// 提交完善
const handleCompleteSubmit = async () => {
  try {
    await completeFormRef.value.validate()
    if (completeForm.student_ids.length !== completeRecord.value.student_count) {
      ElMessage.warning(`需选择 ${completeRecord.value.student_count} 名学生`)
      return
    }

    const res = await completePendingRecord(completeRecord.value.id, {
      student_ids: completeForm.student_ids
    })
    if (res.success) {
      ElMessage.success('完善成功')
      completeDialogVisible.value = false
      fetchPendingRecords()
    } else {
      ElMessage.error(res.message || '完善失败')
    }
  } catch (error) {
    console.error('完善记录失败:', error)
  }
}

// 生命周期
onMounted(async () => {
  await loadMyPermissions()
  canCreateDailyRecord.value = hasApiPermissionSync('/api/moral/daily-records/create')
  canBatchCreateDailyRecord.value = hasApiPermissionSync('/api/moral/daily-records/batch')
  canUpdateDailyRecord.value = hasApiPermissionSync('/api/moral/daily-records/update')
  canDeleteDailyRecord.value = hasApiPermissionSync('/api/moral/daily-records/delete')
  fetchEventTypes()
  fetchGradeList()
  fetchClassList()
})
</script>

<style scoped>
.daily-record-page {
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

.header-actions {
  display: flex;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.score-positive {
  color: #67c23a;
  font-weight: bold;
}

.score-negative {
  color: #f56c6c;
  font-weight: bold;
}

.complete-images {
  display: flex;
  flex-wrap: wrap;
  margin-top: 12px;
  gap: 8px;
}

.student-count-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
}

.record-tabs {
  margin-bottom: 16px;
}
</style>
