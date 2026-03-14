<template>
  <div class="task-manage-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索任务(函数名/描述)"
              class="search-input"
              clearable
              @clear="handleSearch"
              @keyup.enter="handleSearch"
            >
              <template #append>
                <el-button :icon="Search" @click="handleSearch" />
              </template>
            </el-input>
            <el-button type="primary" @click="handleAdd">新增任务</el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="tableData" v-loading="loading" style="width: 100%" border stripe>
        <el-table-column prop="id" label="ID" width="60" align="center" />
        <el-table-column prop="func" label="函数名" min-width="120" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="80" align="center" />
        <el-table-column prop="trigger_type" label="触发器" width="80" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.trigger_type === 'cron' ? 'success' : 'warning'">
              {{ scope.row.trigger_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="trigger_args" label="触发参数" min-width="150" show-overflow-tooltip />
        <el-table-column prop="one_off" label="一次性" width="70" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.one_off ? 'info' : 'success'" size="small">
              {{ scope.row.one_off ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="consumed" label="状态" width="70" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.consumed ? 'danger' : 'success'" size="small">
              {{ scope.row.consumed ? '已执行' : '待执行' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="scope">
            <el-button size="small" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增任务' : '编辑任务'"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="函数名" prop="func">
              <el-select v-model="form.func" placeholder="选择函数" style="width: 100%">
                <el-option
                  v-for="item in funcOptions"
                  :key="item.value"
                  :label="item.label"
                  :value="item.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="触发器" prop="trigger_type">
              <el-select v-model="form.trigger_type" placeholder="选择触发器" style="width: 100%" @change="handleTriggerTypeChange">
                <el-option label="Cron" value="cron" />
                <el-option label="Interval" value="interval" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="触发参数" prop="trigger_args">
          <el-input
            v-model="form.trigger_args"
            type="textarea"
            :rows="4"
            placeholder='{"hour": 3} 或 {"seconds": 60}'
          />
          <div class="form-tip">
            cron格式: {"year": 2024, "month": 1, "day": 1, "hour": 12, "minute": 0, "second": 0}
            <br>
            interval格式: {"seconds": 60} 或 {"hours": 1, "minutes": 30}
          </div>
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="一次性任务">
              <el-switch v-model="form.one_off" :active-value="true" :inactive-value="false" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="已执行">
              <el-switch v-model="form.consumed" :active-value="true" :inactive-value="false" :disabled="dialogType === 'add'" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="函数参数">
          <el-input
            v-model="form.kwargs"
            type="textarea"
            :rows="3"
            placeholder='{"key": "value"}'
          />
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="任务描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'

const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const funcOptions = ref([])

const dialogVisible = ref(false)
const dialogType = ref('add')
const submitLoading = ref(false)
const formRef = ref(null)
const form = reactive({
  func: '',
  type: 'function',
  trigger_type: 'cron',
  trigger_args: '{"hour": 0}',
  args: '',
  kwargs: '',
  one_off: true,
  description: '',
  consumed: false
})

const rules = {
  func: [{ required: true, message: '请选择函数', trigger: 'change' }],
  trigger_type: [{ required: true, message: '请选择触发器', trigger: 'change' }],
  trigger_args: [{ required: true, message: '请输入触发参数', trigger: 'blur' }]
}

const handleTriggerTypeChange = (value) => {
  if (value === 'cron') {
    form.trigger_args = '{"hour": 0}'
  } else {
    form.trigger_args = '{"seconds": 60}'
  }
}

const fetchFuncOptions = async () => {
  try {
    const res = await api.get('/api/tasks/funcs')
    funcOptions.value = res.data.funcs || []
  } catch (error) {
    console.error('获取函数列表失败:', error)
    ElMessage.error('获取函数列表失败')
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined
    }
    const res = await api.get('/api/tasks', { params })
    tableData.value = res.data.data
    total.value = res.data.total
  } catch (error) {
    console.error('获取任务列表失败:', error)
    ElMessage.error('获取任务列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchData()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  fetchData()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  fetchData()
}

const handleAdd = () => {
  dialogType.value = 'add'
  Object.assign(form, {
    func: '',
    type: 'function',
    trigger_type: 'cron',
    trigger_args: '{"hour": 0}',
    args: '',
    kwargs: '',
    one_off: true,
    description: '',
    consumed: false
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogType.value = 'edit'
  Object.assign(form, {
    id: row.id,
    func: row.func,
    type: row.type,
    trigger_type: row.trigger_type,
    trigger_args: row.trigger_args,
    args: row.args || '',
    kwargs: row.kwargs || '',
    one_off: Boolean(row.one_off),
    description: row.description || '',
    consumed: Boolean(row.consumed)
  })
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除任务 ${row.description || row.func} (ID: ${row.id}) 吗？此操作不可恢复。`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await api.delete(`/api/tasks/${row.id}`)
        ElMessage.success('删除成功')
        fetchData()
      } catch (error) {
        console.error('删除失败:', error)
        ElMessage.error('删除失败')
      }
    })
    .catch(() => {})
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        const taskData = {
          func: form.func,
          type: form.type,
          trigger_type: form.trigger_type,
          trigger_args: form.trigger_args || '',
          args: form.args || '',
          kwargs: form.kwargs || '',
          one_off: form.one_off,
          description: form.description || null
        }
        
        if (dialogType.value === 'add') {
          await api.post('/api/tasks', taskData)
          ElMessage.success('创建成功')
        } else {
          taskData.consumed = form.consumed
          await api.put(`/api/tasks/${form.id}`, taskData)
          ElMessage.success('更新成功')
        }
        dialogVisible.value = false
        fetchData()
      } catch (error) {
        console.error('提交失败:', error)
        ElMessage.error(error.response?.data?.detail || '提交失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

onMounted(() => {
  fetchFuncOptions()
  fetchData()
})
</script>

<style scoped>
.task-manage-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 15px;
}

.search-input {
  width: 300px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
  line-height: 1.5;
}
</style>
