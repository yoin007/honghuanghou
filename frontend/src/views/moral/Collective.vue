<template>
  <div class="collective-event-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="班级">
          <el-select v-model="filterForm.class_id" placeholder="选择班级" clearable filterable>
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
        <el-form-item label="事件类型">
          <el-select v-model="filterForm.event_type" placeholder="选择类型" clearable>
            <el-option label="班级荣誉" value="班级荣誉" />
            <el-option label="集体活动" value="集体活动" />
            <el-option label="集体违纪" value="集体违纪" />
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
          <span>集体事件管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="handleAdd" v-if="canCreate">新增集体事件</el-button>
          </div>
        </div>
      </template>

      <el-table :data="eventList" v-loading="loading" stripe>
        <el-table-column prop="event_name" label="事件名称" width="200" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getEventTypeTag(row.event_type)">
              {{ row.event_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column prop="grade_name" label="年级" width="100" />
        <el-table-column label="分值" width="80">
          <template #default="{ row }">
            <span :class="row.score > 0 ? 'score-positive' : 'score-negative'">
              {{ row.score > 0 ? '+' : '' }}{{ row.score }}/人
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="participant_count" label="参与人数" width="100" />
        <el-table-column prop="event_date" label="事件日期" width="120" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">查看分配</el-button>
            <el-button link type="primary" @click="handleEdit(row)" v-if="canUpdateEvent">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)" v-if="canDelete">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchEvents"
        @current-change="fetchEvents"
        class="pagination"
      />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="eventForm" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="事件名称" prop="event_name">
          <el-input v-model="eventForm.event_name" placeholder="输入事件名称" />
        </el-form-item>
        <el-form-item label="事件类型" prop="event_type">
          <el-select v-model="eventForm.event_type" placeholder="选择类型" style="width: 100%">
            <el-option label="班级荣誉" value="班级荣誉" />
            <el-option label="集体活动" value="集体活动" />
            <el-option label="集体违纪" value="集体违纪" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级" prop="class_id">
          <el-select v-model="eventForm.class_id" placeholder="选择班级" style="width: 100%" filterable>
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
        <el-form-item label="每人分值" prop="score">
          <el-input-number v-model="eventForm.score" :min="-30" :max="20" />
          <span class="score-hint">
            （荣誉/活动为正数，违纪为负数）
          </span>
        </el-form-item>
        <el-form-item label="事件日期" prop="event_date">
          <el-date-picker
            v-model="eventForm.event_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="eventForm.description" type="textarea" :rows="3" placeholder="事件描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 分配详情对话框 -->
    <el-dialog v-model="distributionDialogVisible" title="学生分配详情" width="800px">
      <el-table :data="distributions" v-loading="distributionLoading" stripe max-height="400">
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="student_name" label="姓名" width="100" />
        <el-table-column label="是否参与" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_participant ? 'success' : 'info'">
              {{ row.is_participant ? '参与' : '不参与' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="得分" width="80">
          <template #default="{ row }">
            <span :class="row.score_assigned > 0 ? 'score-positive' : 'score-negative'">
              {{ row.score_assigned || 0 }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEditDistribution(row)" v-if="canUpdateDistribution">
              调整
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 分配调整对话框 -->
    <el-dialog v-model="adjustDialogVisible" title="调整学生分配" width="400px">
      <el-form :model="adjustForm" label-width="100px">
        <el-form-item label="是否参与">
          <el-radio-group v-model="adjustForm.is_participant">
            <el-radio :value="1">参与</el-radio>
            <el-radio :value="0">不参与</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="实际得分" v-if="adjustForm.is_participant">
          <el-input-number v-model="adjustForm.score_assigned" :min="-30" :max="20" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="adjustForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdjustSubmit" :loading="adjustSubmitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useApiPermission } from '@/composables/useApiPermission'
import {
  getGrades,
  getClasses,
  getCollectiveEvents,
  createCollectiveEvent,
  getCollectiveEvent,
  updateCollectiveEvent,
  deleteCollectiveEvent,
  updateDistribution
} from '@/api/modules/moral'

// 权限检查
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canCreate = ref(false)
const canUpdateEvent = ref(false)
const canUpdateDistribution = ref(false)
const canDelete = ref(false)

// 数据
const loading = ref(false)
const eventList = ref([])
const gradeList = ref([])
const classList = ref([])

const filterForm = reactive({
  class_id: null,
  event_type: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = ref('新增集体事件')
const submitting = ref(false)
const formRef = ref(null)

const eventForm = reactive({
  event_id: null,
  event_name: '',
  event_type: '班级荣誉',
  class_id: null,
  score: 5,
  event_date: new Date().toISOString().split('T')[0],
  description: ''
})

const rules = {
  event_name: [{ required: true, message: '请输入事件名称', trigger: 'blur' }],
  event_type: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }],
  score: [{ required: true, message: '请输入分值', trigger: 'blur' }],
  event_date: [{ required: true, message: '请选择日期', trigger: 'change' }]
}

// 分配详情对话框
const distributionDialogVisible = ref(false)
const distributionLoading = ref(false)
const distributions = ref([])
const currentEventId = ref(null)

// 分配调整对话框
const adjustDialogVisible = ref(false)
const adjustSubmitting = ref(false)
const adjustForm = reactive({
  id: null,
  event_id: null,
  is_participant: 1,
  score_assigned: 0,
  remark: ''
})

// 方法
const getEventTypeTag = (type) => {
  const tagMap = {
    '班级荣誉': 'success',
    '集体活动': 'primary',
    '集体违纪': 'danger'
  }
  return tagMap[type] || 'info'
}

const fetchGrades = async () => {
  try {
    const res = await getGrades()
    if (res.success) {
      gradeList.value = res.data
    }
  } catch (e) {
    console.error('获取年级列表失败', e)
  }
}

const fetchClasses = async () => {
  try {
    const res = await getClasses()
    if (res.success) {
      classList.value = res.data
    }
  } catch (e) {
    console.error('获取班级列表失败', e)
  }
}

const fetchEvents = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterForm.class_id) params.class_id = filterForm.class_id
    if (filterForm.event_type) params.event_type = filterForm.event_type

    const res = await getCollectiveEvents(params)
    if (res.success) {
      eventList.value = res.data.items
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
  fetchEvents()
}

const handleReset = () => {
  filterForm.class_id = null
  filterForm.event_type = null
  pagination.page = 1
  fetchEvents()
}

const handleAdd = () => {
  dialogTitle.value = '新增集体事件'
  eventForm.event_id = null
  eventForm.event_name = ''
  eventForm.event_type = '班级荣誉'
  eventForm.class_id = null
  eventForm.score = 5
  eventForm.event_date = new Date().toISOString().split('T')[0]
  eventForm.description = ''
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogTitle.value = '编辑集体事件'
  eventForm.event_id = row.event_id
  eventForm.event_name = row.event_name
  eventForm.event_type = row.event_type
  eventForm.class_id = row.class_id
  eventForm.score = row.score
  eventForm.event_date = row.event_date
  eventForm.description = row.description || ''
  dialogVisible.value = true
}

const handleSubmit = async () => {
  await formRef.value.validate()
  submitting.value = true
  try {
    if (eventForm.event_id) {
      // 编辑
      await updateCollectiveEvent(eventForm.event_id, {
        event_name: eventForm.event_name,
        event_type: eventForm.event_type,
        event_date: eventForm.event_date,
        score: eventForm.score,
        description: eventForm.description
      })
      ElMessage.success('更新成功')
    } else {
      // 新增
      const res = await createCollectiveEvent(eventForm)
      if (res.success) {
        ElMessage.success(res.message)
      }
    }
    dialogVisible.value = false
    fetchEvents()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('删除该集体事件将同时删除所有分配记录，确认删除？', '确认删除', {
      type: 'warning'
    })
    await deleteCollectiveEvent(row.event_id)
    ElMessage.success('删除成功')
    fetchEvents()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleView = async (row) => {
  currentEventId.value = row.event_id
  distributionDialogVisible.value = true
  distributionLoading.value = true
  try {
    const res = await getCollectiveEvent(row.event_id)
    if (res.success) {
      distributions.value = res.data.distributions
    }
  } catch (e) {
    ElMessage.error('获取分配详情失败')
  } finally {
    distributionLoading.value = false
  }
}

const handleEditDistribution = (row) => {
  adjustForm.id = row.id
  adjustForm.event_id = currentEventId.value
  adjustForm.is_participant = row.is_participant
  adjustForm.score_assigned = row.score_assigned || 0
  adjustForm.remark = row.remark || ''
  adjustDialogVisible.value = true
}

const handleAdjustSubmit = async () => {
  adjustSubmitting.value = true
  try {
    await updateDistribution(adjustForm.event_id, adjustForm.id, {
      is_participant: adjustForm.is_participant,
      score_assigned: adjustForm.is_participant ? adjustForm.score_assigned : 0,
      remark: adjustForm.remark
    })
    ElMessage.success('调整成功')
    adjustDialogVisible.value = false
    // 刷新分配列表
    handleView({ event_id: currentEventId.value })
  } catch (e) {
    ElMessage.error('调整失败')
  } finally {
    adjustSubmitting.value = false
  }
}

// 初始化
onMounted(() => {
  loadMyPermissions().then(() => {
    canCreate.value = hasApiPermissionSync('/api/moral/collective-events/create')
    canUpdateEvent.value = hasApiPermissionSync('/api/moral/collective-events/update')
    canUpdateDistribution.value = hasApiPermissionSync('/api/moral/collective-events/distributions/update')
    canDelete.value = hasApiPermissionSync('/api/moral/collective-events/delete')
  })
  fetchGrades()
  fetchClasses()
  fetchEvents()
})
</script>

<style scoped>
.collective-event-page {
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

.score-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style>
