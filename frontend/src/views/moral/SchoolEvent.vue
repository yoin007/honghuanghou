<template>
  <div class="school-event-page">
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
            <el-option label="荣誉奖励" :value="1" />
            <el-option label="违纪处分" :value="2" />
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
          <span>校级事件记录</span>
          <div class="header-actions">
            <el-button @click="handleExport">导出</el-button>
            <el-button type="primary" @click="handleAdd" v-if="canCreateSchoolRecord">新增记录</el-button>
          </div>
        </div>
      </template>

      <el-table :data="recordList" v-loading="loading" stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="student_name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column prop="event_name" label="事件名称" width="150" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.event_type === 1 ? 'success' : 'danger'">
              {{ row.event_type === 1 ? '荣誉奖励' : '违纪处分' }}
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
        <el-table-column prop="event_date" label="日期" width="120" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)" v-if="canUpdateSchoolRecord">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)" v-if="canDeleteSchoolRecord">删除</el-button>
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

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="recordForm" :rules="rules" ref="formRef" label-width="100px">
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
            :disabled="!recordForm.class_id"
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
            <el-option-group label="荣誉奖励">
              <el-option
                v-for="event in honorEvents"
                :key="event.event_id"
                :label="`${event.event_name} (+${event.score})`"
                :value="event.event_id"
              />
            </el-option-group>
            <el-option-group label="违纪处分">
              <el-option
                v-for="event in disciplineEvents"
                :key="event.event_id"
                :label="`${event.event_name} (${event.score})`"
                :value="event.event_id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="事件日期" prop="event_date">
          <el-date-picker
            v-model="recordForm.event_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="事件描述">
          <el-input v-model="recordForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="证明材料">
          <el-input v-model="recordForm.evidence" placeholder="相关证明材料链接" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getSchoolRecords,
  getSchoolEventTypes,
  createSchoolRecord,
  updateSchoolRecord,
  deleteSchoolRecord,
  getClasses,
  getGrades,
  getStudents
} from '@/api/modules/moral'
import { getGMT8DateString } from '@/utils/time'
import { useApiPermission } from '@/composables/useApiPermission'

// API权限
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canCreateSchoolRecord = ref(false)
const canUpdateSchoolRecord = ref(false)
const canDeleteSchoolRecord = ref(false)

// 数据
const loading = ref(false)
const recordList = ref([])
const classList = ref([])
const gradeList = ref([])
const classStudents = ref([])
const eventTypes = ref([])

// 筛选表单
const filterForm = reactive({
  student_id: '',
  class_id: null,
  event_type: null
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = computed(() => (recordForm.record_id ? '编辑记录' : '新增记录'))
const formRef = ref(null)

// 记录表单
const recordForm = reactive({
  record_id: null,
  class_id: null,
  student_ids: [],
  event_id: null,
  event_date: '',
  description: '',
  evidence: ''
})

// 表单校验规则
const rules = {
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }],
  student_ids: [{ required: true, type: 'array', min: 1, message: '请选择至少一名学生', trigger: 'change' }],
  event_id: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  event_date: [{ required: true, message: '请选择日期', trigger: 'change' }]
}

// 计算属性
const honorEvents = computed(() =>
  eventTypes.value.filter(e => e.event_type === 1)
)
const disciplineEvents = computed(() =>
  eventTypes.value.filter(e => e.event_type === 2)
)

// 方法
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

    const res = await getSchoolRecords(params)
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
    const res = await getSchoolEventTypes()
    if (res.success) {
      eventTypes.value = res.data
    }
  } catch (error) {
    console.error('获取事件类型失败:', error)
  }
}

const fetchClassList = async () => {
  try {
    const res = await getClasses()
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
    const res = await getStudents({ class_id: classId, page_size: 100 })
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
  handleSearch()
}

const handleAdd = () => {
  Object.assign(recordForm, {
    record_id: null,
    class_id: null,
    student_ids: [],
    event_id: null,
    event_date: getGMT8DateString(), // 东八区当前日期
    description: '',
    evidence: ''
  })
  classStudents.value = []
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  // 获取学生所属班级
  const studentClass = classList.value.find(c => c.class_name === row.class_name)
  const classId = studentClass?.class_id

  // 加载该班级的学生列表
  if (classId) {
    try {
      const res = await getStudents({ class_id: classId, page_size: 100 })
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
    event_date: row.event_date,
    description: row.description,
    evidence: row.evidence
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该记录吗？', '提示', {
      type: 'warning'
    })
    const res = await deleteSchoolRecord(row.record_id)
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

    // 编辑模式：只更新
    if (recordForm.record_id) {
      const res = await updateSchoolRecord(recordForm.record_id, {
        event_date: recordForm.event_date,
        description: recordForm.description,
        evidence: recordForm.evidence
      })
      if (res.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        fetchRecords()
      }
      return
    }

    // 新增模式：批量为每个学生创建记录
    const results = []
    for (const studentId of recordForm.student_ids) {
      const res = await createSchoolRecord({
        student_id: studentId,
        event_id: recordForm.event_id,
        event_date: recordForm.event_date,
        description: recordForm.description,
        evidence: recordForm.evidence
      })
      results.push(res.success)
    }
    const successCount = results.filter(r => r).length
    if (successCount > 0) {
      ElMessage.success(`成功创建 ${successCount} 条记录`)
      dialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

// 导出校级事件记录（支持筛选条件，导出全部数据）
const handleExport = async () => {
  const params = { ...filterForm, page_size: 10000 }
  Object.keys(params).forEach(key => {
    if (params[key] === '' || params[key] === null) {
      delete params[key]
    }
  })

  try {
    ElMessage.info('正在导出数据...')
    const res = await getSchoolRecords(params)
    if (!res.success || !res.data.items || res.data.items.length === 0) {
      ElMessage.warning('暂无数据可导出')
      return
    }

    const exportData = res.data.items
    let csvContent = '学号,姓名,班级,事件名称,类型,分值,日期,描述,证明材料\n'
    exportData.forEach(row => {
      csvContent += `${row.student_id},${row.student_name},${row.class_name},${row.event_name},${row.event_type === 1 ? '荣誉奖励' : '违纪处分'},${row.score},${row.event_date},${row.description || ''},${row.evidence || ''}\n`
    })

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `校级事件记录_${new Date().toISOString().slice(0,10)}.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success(`导出成功，共 ${exportData.length} 条记录`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 生命周期
onMounted(async () => {
  await loadMyPermissions()
  canCreateSchoolRecord.value = hasApiPermissionSync('/api/moral/school-records/create')
  canUpdateSchoolRecord.value = hasApiPermissionSync('/api/moral/school-records/update')
  canDeleteSchoolRecord.value = hasApiPermissionSync('/api/moral/school-records/delete')
  fetchEventTypes()
  fetchGradeList()
  fetchClassList()
  fetchRecords()
})
</script>

<style scoped>
.school-event-page {
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
</style>