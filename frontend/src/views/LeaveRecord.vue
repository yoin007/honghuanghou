<template>
  <div class="leave-record-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>请假记录</span>
        </div>
      </template>

      <div v-if="!isLoggedIn" class="login-tip">
        <el-result
          icon="warning"
          title="需要登录"
          sub-title="请先登录教师账号以使用此功能"
        >
        </el-result>
      </div>

      <div v-else-if="!hasPermission" class="login-tip">
        <el-result
          icon="error"
          title="无权限"
          sub-title="仅班主任可提交和查看请假记录"
        >
        </el-result>
      </div>

      <el-form
        v-else
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
        class="record-form"
      >
        <el-form-item label="班级" prop="class_code">
          <el-select
            v-model="form.class_code"
            placeholder="请选择班级"
            @change="handleClassChange"
            style="width: 100%"
          >
            <el-option
              v-for="item in classOptions"
              :key="item.class_code"
              :label="classLabel(item)"
              :value="item.class_code"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="姓名" prop="names">
          <el-select
            v-model="form.names"
            multiple
            filterable
            placeholder="请选择学生（可多选）"
            style="width: 100%"
            :loading="studentsLoading"
          >
            <el-option
              v-for="student in students"
              :key="student.name"
              :label="student.name"
              :value="student.name"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="类型" prop="style">
          <el-select v-model="form.style" placeholder="请选择请假类型" style="width: 100%">
            <el-option
              v-for="style in leaveStyles"
              :key="style"
              :label="style"
              :value="style"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="天数" prop="days">
          <el-input-number v-model="form.days" :min="1" :max="30" style="width: 100%" />
        </el-form-item>

        <el-form-item label="备注" prop="note">
          <el-input v-model="form.note" placeholder="请输入备注（可选）" />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="submitForm" :loading="submitting">提交记录</el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card v-if="isLoggedIn && hasPermission" class="box-card table-card">
      <template #header>
        <div class="card-header">
          <span>请假记录列表</span>
          <div class="header-actions">
            <el-select
              v-model="filterClassCode"
              placeholder="全部班级"
              clearable
              style="width: 180px"
              @change="handleFilterChange"
            >
              <el-option
                v-for="item in classOptions"
                :key="item.class_code"
                :label="classLabel(item)"
                :value="item.class_code"
              />
            </el-select>
            <el-button size="small" @click="refreshRecords" :loading="listLoading">刷新</el-button>
          </div>
        </div>
      </template>

      <el-empty v-if="!listLoading && records.length === 0" description="暂无请假记录" />
      <el-table v-else :data="records" v-loading="listLoading" border stripe style="width: 100%">
        <el-table-column prop="create_at" label="提交时间" width="160" />
        <el-table-column prop="class_code" label="班级" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="style" label="类型" width="100" />
        <el-table-column prop="days" label="天数" width="80" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="recorder" label="记录人" width="100" />
        <el-table-column prop="consumer" label="销假人" width="100" />
        <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status !== '已销假'"
              type="success"
              size="small"
              :loading="consumingId === row.id"
              @click="handleConsume(row)"
            >
              销假
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          background
          layout="prev, pager, next, jumper, ->, total"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
// Pinia 的 computed 在 script setup 中需要用 .value 访问，或者直接用 authStore.isLoggedIn
const isLoggedIn = computed(() => authStore.isLoggedIn)
const username = computed(() => authStore.username)

const formRef = ref(null)
const classOptions = ref([])
const students = ref([])
const studentsLoading = ref(false)
const submitting = ref(false)
const listLoading = ref(false)
const hasPermission = ref(true)

const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const consumingId = ref(null)
const filterClassCode = ref('')

const leaveStyles = ['事假', '病假', '公假', '其他']

const form = ref({
  class_code: '',
  names: [],
  style: '',
  days: 1,
  note: ''
})

const rules = {
  class_code: [{ required: true, message: '请选择班级', trigger: 'change' }],
  names: [{ required: true, message: '请选择至少一名学生', trigger: 'change' }],
  style: [{ required: true, message: '请选择请假类型', trigger: 'change' }],
  days: [{ required: true, message: '请输入天数', trigger: 'change' }]
}

const classLabel = (item) => {
  if (!item) return ''
  if (item.class_name && item.class_name !== item.class_code) {
    return `${item.class_code} ${item.class_name}`
  }
  return item.class_code
}

const fetchCleaderClasses = async () => {
  if (!isLoggedIn.value) return
  try {
    const response = await api.get('/api/cleader-classes/')
    const list = Array.isArray(response.data?.classes) ? response.data.classes : []
    classOptions.value = list
    if (!form.value.class_code && list.length > 0) {
      form.value.class_code = list[0].class_code
      filterClassCode.value = list[0].class_code
      await handleClassChange(list[0].class_code)
    }
  } catch (error) {
    if (error?.response?.status === 403) {
      hasPermission.value = false
      classOptions.value = []
      records.value = []
      total.value = 0
      return
    }
    ElMessage.error('获取班级列表失败')
  }
}

const handleClassChange = async (val) => {
  form.value.names = []
  if (!val) {
    students.value = []
    return
  }
  studentsLoading.value = true
  try {
    const response = await api.get(`/api/students/${val}`)
    students.value = Array.isArray(response.data?.students)
      ? response.data.students.map(name => ({ name }))
      : []
  } catch (error) {
    ElMessage.error('获取学生列表失败')
  } finally {
    studentsLoading.value = false
  }
}

const fetchRecords = async () => {
  if (!isLoggedIn.value || !hasPermission.value) return
  listLoading.value = true
  try {
    const response = await api.get('/api/leave-records/', {
      params: {
        page: page.value,
        page_size: pageSize.value,
        class_code: filterClassCode.value || undefined
      }
    })
    records.value = Array.isArray(response.data?.records) ? response.data.records : []
    total.value = Number(response.data?.total) || 0
  } catch (error) {
    ElMessage.error('获取请假记录失败')
  } finally {
    listLoading.value = false
  }
}

const handleFilterChange = () => {
  page.value = 1
  fetchRecords()
}

const handlePageChange = (val) => {
  page.value = val
  fetchRecords()
}

const refreshRecords = async () => {
  await fetchRecords()
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await api.post('/api/leave-records/', {
        class_code: form.value.class_code,
        names: form.value.names,
        style: form.value.style,
        days: form.value.days,
        note: form.value.note,
        recorder: username.value || ''
      })
      ElMessage.success('提交成功')
      resetForm()
      page.value = 1
      await fetchRecords()
    } catch (error) {
      if (error?.response?.status === 403) {
        ElMessage.error('仅班主任可提交请假记录')
      } else {
        ElMessage.error('提交失败')
      }
    } finally {
      submitting.value = false
    }
  })
}

const handleConsume = async (row) => {
  if (!row?.id) return
  consumingId.value = row.id
  try {
    await api.post(`/api/leave-records/${row.id}/consume`)
    ElMessage.success('销假成功')
    await fetchRecords()
  } catch (error) {
    if (error?.response?.status === 403) {
      ElMessage.error('仅班主任可销假')
    } else {
      ElMessage.error('销假失败')
    }
  } finally {
    consumingId.value = null
  }
}

const resetForm = () => {
  if (formRef.value) {
    const currentClass = form.value.class_code
    formRef.value.resetFields()
    form.value.class_code = currentClass
  }
  form.value.days = 1
  form.value.note = ''
}

watch(() => authStore.isLoggedIn, async (val) => {
  if (val) {
    hasPermission.value = true
    await fetchCleaderClasses()
    await fetchRecords()
  } else {
    classOptions.value = []
    students.value = []
    records.value = []
    total.value = 0
    filterClassCode.value = ''
  }
})

onMounted(async () => {
  if (isLoggedIn.value) {
    await fetchCleaderClasses()
    await fetchRecords()
  }
})
</script>

<style scoped>
.leave-record-container {
  padding: 20px;
  max-width: 1000px;
  margin: 0 auto;
}

.login-tip {
  text-align: center;
  padding: 40px 0;
}

.table-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.pagination-container {
  margin-top: 15px;
  display: flex;
  justify-content: flex-end;
}

@media screen and (max-width: 768px) {
  .leave-record-container {
    padding: 10px;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
