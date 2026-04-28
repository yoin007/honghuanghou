<template>
  <div class="moment-record-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="学生学号/姓名">
          <el-input v-model="filterForm.student_keyword" placeholder="输入学号或姓名" clearable />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filterForm.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="记录类型">
          <el-select v-model="filterForm.record_type" placeholder="全部" clearable style="width: 120px">
            <el-option label="点滴" value="moment" />
            <el-option label="观察" value="observation" />
            <el-option label="备注" value="note" />
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
          <span>我的点滴记录</span>
          <div class="header-actions">
            <el-button @click="handleExport">导出</el-button>
            <el-button type="primary" @click="handleAdd" v-if="canCreateMomentRecord">新增记录</el-button>
          </div>
        </div>
      </template>

      <el-table :data="recordList" v-loading="loading" stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="student_name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column prop="content" label="记录内容" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="getTypeColor(row.record_type)" size="small">{{ getTypeName(row.record_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" width="120">
          <template #default="{ row }">
            <template v-if="row.tags">
              <el-tag v-for="tag in parseTags(row.tags)" :key="tag" size="small" class="tag-item">{{ tag }}</el-tag>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="record_date" label="记录日期" width="100" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)" v-if="canUpdateMomentRecord">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)" v-if="canDeleteMomentRecord">删除</el-button>
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
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="学生" prop="student_id">
          <el-select
            v-model="form.student_id"
            placeholder="选择班级后选择学生"
            filterable
            style="width: 100%"
          >
            <el-option-group v-for="cls in classList" :key="cls.class_id" :label="cls.class_name">
              <el-option
                v-for="stu in studentsByClass[cls.class_id] || []"
                :key="stu.student_id"
                :label="`${stu.name} (${stu.student_id})`"
                :value="stu.student_id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="记录类型" prop="record_type">
          <el-select v-model="form.record_type" style="width: 100%">
            <el-option label="点滴记录" value="moment" />
            <el-option label="观察记录" value="observation" />
            <el-option label="备注" value="note" />
          </el-select>
        </el-form-item>
        <el-form-item label="记录内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="详细记录学生的表现..." maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple placeholder="选择或输入标签" filterable allow-create style="width: 100%">
            <el-option label="进步" value="进步" />
            <el-option label="表扬" value="表扬" />
            <el-option label="关注" value="关注" />
            <el-option label="优秀" value="优秀" />
            <el-option label="待改进" value="待改进" />
          </el-select>
        </el-form-item>
        <el-form-item label="记录日期" prop="record_date">
          <el-date-picker v-model="form.record_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/utils/api'
import { getGMT8DateString } from '@/utils/time'
import { useApiPermission } from '@/composables/useApiPermission'

const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canCreateMomentRecord = ref(false)
const canUpdateMomentRecord = ref(false)
const canDeleteMomentRecord = ref(false)

const loading = ref(false)
const recordList = ref([])
const classList = ref([])
const studentsByClass = ref({})

const filterForm = reactive({
  student_keyword: '',
  date_range: null,
  record_type: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const submitLoading = ref(false)

const form = reactive({
  record_id: null,
  student_id: '',
  content: '',
  record_type: 'moment',
  tags: [],
  record_date: getGMT8DateString() // 东八区当前日期
})

const rules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  content: [{ required: true, message: '请输入记录内容', trigger: 'blur' }],
  record_date: [{ required: true, message: '请选择日期', trigger: 'change' }]
}

const getTypeName = (type) => {
  const map = { moment: '点滴', observation: '观察', note: '备注' }
  return map[type] || type
}

const getTypeColor = (type) => {
  const map = { moment: 'primary', observation: 'success', note: 'info' }
  return map[type] || ''
}

const parseTags = (tags) => {
  if (!tags) return []
  try {
    return JSON.parse(tags)
  } catch {
    return []
  }
}

const fetchRecords = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterForm.student_keyword) {
      params.student_id = filterForm.student_keyword
    }
    if (filterForm.date_range) {
      params.start_date = filterForm.date_range[0]
      params.end_date = filterForm.date_range[1]
    }
    if (filterForm.record_type) {
      params.record_type = filterForm.record_type
    }

    const res = await api.get('/api/moral/moment-records', { params })
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

const fetchClassesAndStudents = async () => {
  try {
    // 获取班级列表
    const classRes = await api.get('/api/moral/admin/classes')
    if (classRes.success) {
      classList.value = classRes.data
    }

    // 获取每个班级的学生（简化处理，获取所有学生后按班级分组）
    const studentRes = await api.get('/api/moral/admin/students', { params: { page: 1, page_size: 10000, for_record_input: 1 } })
    if (studentRes.success) {
      const students = studentRes.data.items
      const grouped = {}
      students.forEach(s => {
        if (!grouped[s.class_id]) grouped[s.class_id] = []
        grouped[s.class_id].push(s)
      })
      studentsByClass.value = grouped
    }
  } catch (error) {
    console.error('获取数据失败:', error)
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchRecords()
}

const handleReset = () => {
  Object.assign(filterForm, {
    student_keyword: '',
    date_range: null,
    record_type: null
  })
  handleSearch()
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(form, {
    record_id: null,
    student_id: '',
    content: '',
    record_type: 'moment',
    tags: [],
    record_date: getGMT8DateString() // 东八区当前日期
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, {
    record_id: row.record_id,
    student_id: row.student_id,
    content: row.content,
    record_type: row.record_type,
    tags: parseTags(row.tags),
    record_date: row.record_date
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true

    const data = {
      student_id: form.student_id,
      content: form.content,
      record_type: form.record_type,
      tags: form.tags,
      record_date: form.record_date
    }

    let res
    if (isEdit.value) {
      res = await api.put(`/api/moral/moment-records/${form.record_id}`, data)
    } else {
      res = await api.post('/api/moral/moment-records', data)
    }

    if (res.success) {
      ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitLoading.value = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除该记录吗？', '提示', { type: 'warning' })
    const res = await api.delete(`/api/moral/moment-records/${row.record_id}`)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchRecords()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('删除失败:', error)
  }
}

// 导出点滴记录（支持筛选条件，导出全部数据）
const handleExport = async () => {
  const params = { ...filterForm, page_size: 10000 }
  Object.keys(params).forEach(key => {
    if (params[key] === '' || params[key] === null) {
      delete params[key]
    }
  })

  try {
    ElMessage.info('正在导出数据...')
    const res = await api.get('/api/moral/moment-records', { params })
    if (!res.success || !res.data?.items || res.data.items.length === 0) {
      ElMessage.warning('暂无数据可导出')
      return
    }

    const exportData = res.data.items
    let csvContent = '学号,姓名,班级,记录类型,标题,内容,日期\n'
    exportData.forEach(row => {
      csvContent += `${row.student_id},${row.student_name},${row.class_name},${row.record_type},${row.title || ''},${row.content},${row.record_date}\n`
    })

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `点滴记录_${new Date().toISOString().slice(0,10)}.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success(`导出成功，共 ${exportData.length} 条记录`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

onMounted(async () => {
  await loadMyPermissions()
  canCreateMomentRecord.value = hasApiPermissionSync('/api/moral/moment-records/create')
  canUpdateMomentRecord.value = hasApiPermissionSync('/api/moral/moment-records/update')
  canDeleteMomentRecord.value = hasApiPermissionSync('/api/moral/moment-records/delete')
  fetchRecords()
  fetchClassesAndStudents()
})
</script>

<style scoped>
.moment-record-page {
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

.tag-item {
  margin-right: 4px;
}
</style>
