<template>
  <div class="punishment-page">
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
        <el-form-item label="处分状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable>
            <el-option label="生效中" :value="1" />
            <el-option label="已撤销" :value="0" />
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
          <span>处分记录管理</span>
          <el-button type="primary" @click="handleAdd">新增处分</el-button>
        </div>
      </template>

      <el-table :data="recordList" v-loading="loading" stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="student_name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column prop="punishment_type" label="处分类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getPunishmentTagType(row.punishment_level)">
              {{ row.punishment_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="punishment_reason" label="处分原因" show-overflow-tooltip />
        <el-table-column prop="punishment_date" label="处分日期" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'danger' : 'info'">
              {{ row.status === 1 ? '生效中' : '已撤销' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="revoke_date" label="撤销日期" width="120" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button
              link
              type="warning"
              @click="handleRevoke(row)"
              v-if="row.status === 1"
            >撤销</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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
        <el-form-item label="学生" prop="student_id">
          <el-select
            v-model="recordForm.student_id"
            placeholder="选择学生"
            style="width: 100%"
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
        <el-form-item label="处分类型" prop="punishment_type">
          <el-select v-model="recordForm.punishment_type" placeholder="选择处分类型" style="width: 100%" filterable>
            <el-option label="警告" value="警告" />
            <el-option label="严重警告" value="严重警告" />
            <el-option label="记过" value="记过" />
            <el-option label="记大过" value="记大过" />
            <el-option label="留校察看" value="留校察看" />
          </el-select>
        </el-form-item>
        <el-form-item label="处分等级" prop="punishment_level">
          <el-select v-model="recordForm.punishment_level" placeholder="选择等级" style="width: 100%">
            <el-option label="一级（轻微）" :value="1" />
            <el-option label="二级（一般）" :value="2" />
            <el-option label="三级（严重）" :value="3" />
            <el-option label="四级（重大）" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="处分日期" prop="punishment_date">
          <el-date-picker
            v-model="recordForm.punishment_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="处分原因" prop="punishment_reason">
          <el-input v-model="recordForm.punishment_reason" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="证明材料">
          <el-input v-model="recordForm.evidence" placeholder="相关证明材料链接" />
        </el-form-item>
        <el-form-item label="德育扣分">
          <el-input-number v-model="recordForm.score_deduct" :min="-100" :max="-1" />
          <span class="score-hint">处分将扣除德育分</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 撤销对话框 -->
    <el-dialog v-model="revokeDialogVisible" title="撤销处分" width="500px">
      <el-form :model="revokeForm" ref="revokeFormRef" label-width="100px">
        <el-form-item label="处分信息">
          <div class="punishment-info">
            <p><strong>学生：</strong>{{ revokeForm.student_name }}</p>
            <p><strong>处分类型：</strong>{{ revokeForm.punishment_type }}</p>
            <p><strong>处分日期：</strong>{{ revokeForm.punishment_date }}</p>
          </div>
        </el-form-item>
        <el-form-item label="撤销日期" prop="revoke_date">
          <el-date-picker
            v-model="revokeForm.revoke_date"
            type="date"
            placeholder="选择撤销日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="撤销原因" prop="revoke_reason">
          <el-input v-model="revokeForm.revoke_reason" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="revokeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRevokeSubmit">确定撤销</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getPunishments,
  createPunishment,
  updatePunishment,
  revokePunishment,
  getClasses,
  getGrades,
  getStudents
} from '@/api/modules/moral'

// 数据
const loading = ref(false)
const recordList = ref([])
const classList = ref([])
const gradeList = ref([])
const classStudents = ref([])

// 筛选表单
const filterForm = reactive({
  student_id: '',
  class_id: null,
  status: null
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = computed(() => (recordForm.record_id ? '编辑处分' : '新增处分'))
const formRef = ref(null)

// 记录表单
const recordForm = reactive({
  record_id: null,
  class_id: null,
  student_id: '',
  punishment_type: '',
  punishment_level: 2,
  punishment_date: '',
  punishment_reason: '',
  evidence: '',
  score_deduct: -10
})

// 表单校验规则
const rules = {
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }],
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  punishment_type: [{ required: true, message: '请选择处分类型', trigger: 'change' }],
  punishment_level: [{ required: true, message: '请选择处分等级', trigger: 'change' }],
  punishment_date: [{ required: true, message: '请选择处分日期', trigger: 'change' }],
  punishment_reason: [{ required: true, message: '请输入处分原因', trigger: 'blur' }]
}

// 撤销对话框
const revokeDialogVisible = ref(false)
const revokeFormRef = ref(null)
const revokeForm = reactive({
  record_id: null,
  student_name: '',
  punishment_type: '',
  punishment_date: '',
  revoke_date: '',
  revoke_reason: ''
})

// 方法
const getPunishmentTagType = (level) => {
  const types = {
    1: 'info',
    2: 'warning',
    3: 'danger',
    4: 'danger'
  }
  return types[level] || 'warning'
}

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

    const res = await getPunishments(params)
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
  recordForm.student_id = ''
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
  filterForm.status = null
  handleSearch()
}

const handleAdd = () => {
  Object.assign(recordForm, {
    record_id: null,
    class_id: null,
    student_id: '',
    punishment_type: '',
    punishment_level: 2,
    punishment_date: new Date().toISOString().split('T')[0],
    punishment_reason: '',
    evidence: '',
    score_deduct: -10
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
    student_id: row.student_id,
    punishment_type: row.punishment_type,
    punishment_level: row.punishment_level,
    punishment_date: row.punishment_date,
    punishment_reason: row.punishment_reason,
    evidence: row.evidence,
    score_deduct: row.score_deduct
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该处分记录吗？', '提示', {
      type: 'warning'
    })
    const res = await updatePunishment(row.record_id, { status: 0 })
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
    const api = recordForm.record_id
      ? updatePunishment(recordForm.record_id, recordForm)
      : createPunishment(recordForm)

    const res = await api
    if (res.success) {
      ElMessage.success(recordForm.record_id ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

const handleRevoke = (row) => {
  Object.assign(revokeForm, {
    record_id: row.record_id,
    student_name: row.student_name,
    punishment_type: row.punishment_type,
    punishment_date: row.punishment_date,
    revoke_date: new Date().toISOString().split('T')[0],
    revoke_reason: ''
  })
  revokeDialogVisible.value = true
}

const handleRevokeSubmit = async () => {
  try {
    const res = await revokePunishment(revokeForm.record_id, revokeForm.revoke_reason)
    if (res.success) {
      ElMessage.success('撤销成功')
      revokeDialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    console.error('撤销失败:', error)
  }
}

// 生命周期
onMounted(() => {
  fetchGradeList()
  fetchClassList()
  fetchRecords()
})
</script>

<style scoped>
.punishment-page {
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
  display: flex;
  justify-content: flex-end;
}

.punishment-info {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.punishment-info p {
  margin: 5px 0;
}

.score-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style>