<template>
  <div class="member-manage-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>会员管理</span>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索会员(昵称/wxid/uuid)"
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
            <el-button type="primary" @click="handleAdd">新增会员</el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="tableData" v-loading="loading" style="width: 100%" border stripe>
        <el-table-column prop="uuid" label="UUID" min-width="120" show-overflow-tooltip />
        <el-table-column prop="wxid" label="WXID" min-width="120" show-overflow-tooltip />
        <el-table-column prop="alias" label="昵称" min-width="100" />
        <el-table-column prop="level" label="等级" width="80" align="center" />
        <el-table-column prop="score" label="积分" width="80" align="center" />
        <el-table-column prop="balance" label="余额" width="80" align="center" />
        <el-table-column prop="model" label="模块" min-width="100" show-overflow-tooltip />
        <el-table-column prop="active" label="状态" width="80" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.active ? 'success' : 'danger'">
              {{ scope.row.active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip />
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
      :title="dialogType === 'add' ? '新增会员' : '编辑会员'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="UUID" prop="uuid">
          <el-input v-model="form.uuid" :disabled="dialogType === 'edit'" placeholder="请输入UUID" />
        </el-form-item>
        <el-form-item label="WXID" prop="wxid">
          <el-input v-model="form.wxid" placeholder="请输入WXID" />
        </el-form-item>
        <el-form-item label="昵称" prop="alias">
          <el-input v-model="form.alias" placeholder="请输入昵称" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="等级" prop="level">
              <el-input-number v-model="form.level" :min="0" :max="100" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="active">
              <el-switch v-model="form.active" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="积分" prop="score">
              <el-input-number v-model="form.score" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="余额" prop="balance">
              <el-input-number v-model="form.balance" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="模块" prop="model">
          <el-input v-model="form.model" placeholder="basic/lesson" />
        </el-form-item>
        <el-form-item label="备注" prop="note">
          <el-input v-model="form.note" type="textarea" :rows="2" />
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
import { getMembers, createMember, updateMember, deleteMember } from '@/api/modules/member'

// 列表数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchQuery = ref('')
const statusFilter = ref('')

// 表单数据
const dialogVisible = ref(false)
const dialogType = ref('add') // 'add' or 'edit'
const submitLoading = ref(false)
const formRef = ref(null)
const form = reactive({
  uuid: '',
  wxid: '',
  alias: '',
  active: 1,
  score: 50,
  balance: 0,
  level: 1,
  model: 'basic',
  note: ''
})

const rules = {
  uuid: [{ required: true, message: '请输入UUID', trigger: 'blur' }],
  wxid: [{ required: true, message: '请输入WXID', trigger: 'blur' }],
  alias: [{ required: true, message: '请输入昵称', trigger: 'blur' }]
}

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchQuery.value || undefined,
      active: statusFilter.value !== '' ? statusFilter.value : undefined
    }
    const res = await getMembers(params)
    tableData.value = res.data.data
    total.value = res.data.total
  } catch (error) {
    console.error('获取会员列表失败:', error)
    ElMessage.error('获取会员列表失败')
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
    uuid: '',
    wxid: '',
    alias: '',
    active: 1,
    score: 50,
    balance: 0,
    level: 1,
    model: 'basic',
    note: ''
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
    `确定要删除会员 ${row.alias || row.uuid} 吗？此操作不可恢复。`,
    '删除确认',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )
    .then(async () => {
      try {
        await deleteMember(row.uuid)
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
          await createMember(form)
          ElMessage.success('创建成功')
        } else {
          await updateMember(form.uuid, form)
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
  fetchData()
})
</script>

<style scoped>
.member-manage-container {
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