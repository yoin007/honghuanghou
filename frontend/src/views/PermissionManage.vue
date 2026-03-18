<template>
  <div class="permission-manage-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>权限管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索权限(功能名/模块)"
              class="search-input"
              clearable
              @clear="handleSearch"
              @keyup.enter="handleSearch"
            >
              <template #append>
                <el-button :icon="Search" @click="handleSearch" />
              </template>
            </el-input>
            <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 120px" @change="handleSearch">
              <el-option label="全部" value="" />
              <el-option label="启用" :value="1" />
              <el-option label="禁用" :value="0" />
            </el-select>
            <el-button type="primary" @click="handleAdd">新增权限</el-button>
          </div>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" style="width: 100%" border stripe>
        <el-table-column prop="id" label="ID" width="60" align="center" />
        <el-table-column prop="func_name" label="功能名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="func" label="标识" min-width="120" show-overflow-tooltip />
        <el-table-column prop="module" label="模块" width="100" />
        <el-table-column prop="level" label="等级" width="80" align="center" />
        <el-table-column prop="priority" label="优先级" width="80" align="center" />
        <el-table-column prop="activate" label="状态" width="80" align="center">
          <template #default="scope">
            <el-switch
              v-model="scope.row.activate"
              :active-value="1"
              :inactive-value="0"
              @change="handleStatusChange(scope.row)"
            />
          </template>
        </el-table-column>
        <el-table-column prop="score" label="积分" width="80" align="center" />
        <el-table-column prop="pattern" label="匹配模式" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="180" fixed="right" align="center">
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

    <!-- 编辑/新增对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'add' ? '新增权限' : '编辑权限'"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="功能标识">
              <el-input v-model="form.func" :disabled="dialogType === 'edit'" placeholder="英文唯一标识" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="功能名称">
              <el-input v-model="form.func_name" placeholder="中文名称" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="匹配模式">
          <el-input v-model="form.pattern" placeholder="正则表达式" />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="所属模块" prop="module">
              <el-input v-model="form.module" placeholder="例如: lesson" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最低等级" prop="level">
              <el-input-number v-model="form.level" :min="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-input-number v-model="form.priority" :min="1" :max="999" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="所需积分" prop="score">
              <el-input-number v-model="form.score" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所需余额" prop="balance">
              <el-input-number v-model="form.balance" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="回复内容" prop="reply">
          <el-input v-model="form.reply" type="textarea" :rows="2" placeholder="自动回复内容模板" />
        </el-form-item>

        <el-form-item label="使用示例" prop="example">
          <el-input v-model="form.example" type="textarea" :rows="2" />
        </el-form-item>

        <el-form-item label="类型" prop="type">
          <el-input v-model="form.type" placeholder="权限类型" />
        </el-form-item>

        <el-form-item label="关键词" prop="keywords">
          <el-input v-model="form.keywords" type="textarea" :rows="2" placeholder="多个关键词用逗号分隔" />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="黑名单" prop="black_list">
              <el-input v-model="form.black_list" placeholder="用户ID黑名单" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="白名单" prop="white_list">
              <el-input v-model="form.white_list" placeholder="用户ID白名单" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="AI标识" prop="ai_flag">
              <el-switch v-model="form.ai_flag" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="检查权限" prop="check_permission">
              <el-switch v-model="form.check_permission" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="备注" prop="notes">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="备注信息" />
        </el-form-item>
        
        <el-row :gutter="20">
           <el-col :span="12">
             <el-form-item label="启用状态" prop="activate">
               <el-switch v-model="form.activate" :active-value="1" :inactive-value="0" />
             </el-form-item>
           </el-col>
           <el-col :span="12">
             <el-form-item label="需要@" prop="need_at">
               <el-switch v-model="form.need_at" :active-value="1" :inactive-value="0" />
             </el-form-item>
           </el-col>
        </el-row>
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
const statusFilter = ref('')

const dialogVisible = ref(false)
const dialogType = ref('add')
const submitLoading = ref(false)
const formRef = ref(null)
const form = reactive({
  func: '',
  func_name: '',
  pattern: '',
  module: '',
  level: 1,
  priority: 99,
  score: 0,
  balance: 0,
  reply: '',
  example: '',
  activate: 1,
  need_at: 0,
  black_list: '',
  white_list: '',
  type: '',
  keywords: '',
  ai_flag: 0,
  check_permission: 1,
  notes: ''
})

const rules = {
  // func: [{ required: true, message: '请输入功能标识', trigger: 'blur' }],
  // func_name: [{ required: true, message: '请输入功能名称', trigger: 'blur' }],
  // pattern: [{ required: true, message: '请输入匹配模式', trigger: 'blur' }],
  white_list: [{ required: true, message: '请输入白名单', trigger: 'blur' }],
  module: [{ required: true, message: '请输入所属模块', trigger: 'blur' }]
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
      activate: statusFilter.value !== '' ? statusFilter.value : undefined
    }
    const res = await api.get('/api/permissions', { params })
    tableData.value = res.data.data
    total.value = res.data.total
  } catch (error) {
    console.error('获取权限列表失败:', error)
    ElMessage.error('获取权限列表失败')
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

const handleStatusChange = async (row) => {
  try {
    await api.put(`/api/permissions/${row.id}`, { activate: row.activate })
    ElMessage.success('状态更新成功')
  } catch (error) {
    console.error('状态更新失败:', error)
    row.activate = row.activate === 1 ? 0 : 1 // Revert change
    ElMessage.error('状态更新失败')
  }
}

const handleAdd = () => {
  dialogType.value = 'add'
  // Reset form
  Object.keys(form).forEach(key => {
    if (key === 'level') form[key] = 1
    else if (key === 'priority') form[key] = 99
    else if (key === 'score') form[key] = 0
    else if (key === 'balance') form[key] = 0
    else if (key === 'activate') form[key] = 1
    else if (key === 'need_at') form[key] = 0
    else if (key === 'ai_flag') form[key] = 0
    else if (key === 'check_permission') form[key] = 1
    else form[key] = ''
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  dialogType.value = 'edit'
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除权限 ${row.func_name || row.func} 吗？此操作不可恢复。`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await api.delete(`/api/permissions/${row.id}`)
        ElMessage.success('删除成功')
        fetchData()
      } catch (error) {
        console.error('删除失败:', error)
        ElMessage.error('删除失败')
      }
    })
    .catch(() => {
      // 取消删除
    })
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        if (dialogType.value === 'add') {
          await api.post('/api/permissions', form)
          ElMessage.success('创建成功')
        } else {
          await api.put(`/api/permissions/${form.id}`, form)
          ElMessage.success('更新成功')
        }
        dialogVisible.value = false
        fetchData()
      } catch (error) {
        console.error('提交失败:', error)
        const message = error.response?.data?.detail || error.response?.data?.message || error.message || '提交失败'
        ElMessage.error(message)
      } finally {
        submitLoading.value = false
      }
    }
  })
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.permission-manage-container {
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
</style>