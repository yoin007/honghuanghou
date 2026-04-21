<template>
  <div class="api-permission-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>API权限管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="handleInit" :loading="initLoading">初始化默认配置</el-button>
            <el-button type="success" @click="handleAdd">新增配置</el-button>
          </div>
        </div>
      </template>

      <!-- 筛选 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="API分组">
          <el-select v-model="filterGroup" placeholder="全部" clearable @change="fetchPermissions">
            <el-option v-for="group in apiGroups" :key="group" :label="group" :value="group" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="permissions" v-loading="loading" stripe>
        <el-table-column prop="api_name" label="API名称" width="150" />
        <el-table-column prop="api_path" label="API路径" width="200" />
        <el-table-column prop="api_group" label="分组" width="100" />
        <el-table-column label="允许角色" width="250">
          <template #default="{ row }">
            <el-tag v-for="role in row.allowed_roles" :key="role" size="small" class="role-tag">
              {{ getRoleName(role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="min_level" label="最低等级" width="80" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="API路径" prop="api_path">
          <el-input v-model="form.api_path" placeholder="/api/moral/xxx" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="API名称" prop="api_name">
          <el-input v-model="form.api_name" placeholder="如：获取日常记录" />
        </el-form-item>
        <el-form-item label="API分组" prop="api_group">
          <el-select v-model="form.api_group" placeholder="选择分组" filterable allow-create>
            <el-option v-for="group in apiGroups" :key="group" :label="group" :value="group" />
          </el-select>
        </el-form-item>
        <el-form-item label="允许角色" prop="allowed_roles">
          <el-checkbox-group v-model="form.allowed_roles">
            <el-checkbox label="admin">管理员</el-checkbox>
            <el-checkbox label="jiaowu">教发部</el-checkbox>
            <el-checkbox label="xuefa">学发部</el-checkbox>
            <el-checkbox label="cleader">班主任</el-checkbox>
            <el-checkbox label="teacher">教师</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="最低等级">
          <el-input-number v-model="form.min_level" :min="0" :max="100" :step="10" />
          <div class="form-tip">0表示不限制等级，仅角色检查</div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="是否启用" v-if="isEdit">
          <el-switch v-model="form.is_active" :active-value="1" :inactive-value="0" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getApiPermissions,
  createApiPermission,
  updateApiPermission,
  deleteApiPermission,
  initApiPermissions,
  getApiGroups
} from '@/api/modules/moral'

// 数据
const loading = ref(false)
const initLoading = ref(false)
const submitLoading = ref(false)
const permissions = ref([])
const apiGroups = ref([])
const filterGroup = ref(null)

// 对话框
const dialogVisible = ref(false)
const isEdit = ref(false)
const dialogTitle = computed(() => isEdit.value ? '编辑配置' : '新增配置')
const formRef = ref(null)

// 表单
const form = reactive({
  id: null,
  api_path: '',
  api_name: '',
  api_group: '',
  allowed_roles: ['admin'],
  min_level: 0,
  description: '',
  is_active: 1
})

const rules = {
  api_path: [{ required: true, message: '请输入API路径', trigger: 'blur' }],
  api_name: [{ required: true, message: '请输入API名称', trigger: 'blur' }],
  api_group: [{ required: true, message: '请选择分组', trigger: 'change' }],
  allowed_roles: [{ required: true, type: 'array', min: 1, message: '请选择至少一个角色', trigger: 'change' }]
}

// 角色名称映射
const roleNames = {
  admin: '管理员',
  jiaowu: '教发部',
  xuefa: '学发部',
  cleader: '班主任',
  teacher: '教师',
  student: '学生',
  parent: '家长'
}

const getRoleName = (role) => roleNames[role] || role

// 方法
const fetchPermissions = async () => {
  loading.value = true
  try {
    const res = await getApiPermissions(filterGroup.value)
    if (res.success) {
      permissions.value = res.data || []
    }
  } catch (error) {
    console.error('获取权限配置失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchGroups = async () => {
  try {
    const res = await getApiGroups()
    if (res.success) {
      apiGroups.value = res.data || []
    }
  } catch (error) {
    console.error('获取分组失败:', error)
  }
}

const handleInit = async () => {
  try {
    await ElMessageBox.confirm('初始化将添加默认的API权限配置，已存在的配置不会重复添加。确定继续？', '提示', {
      type: 'info'
    })

    initLoading.value = true
    const res = await initApiPermissions()
    if (res.success) {
      ElMessage.success(res.message)
      fetchPermissions()
      fetchGroups()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('初始化失败:', error)
    }
  } finally {
    initLoading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(form, {
    id: null,
    api_path: '',
    api_name: '',
    api_group: '',
    allowed_roles: ['admin'],
    min_level: 0,
    description: '',
    is_active: 1
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, {
    id: row.id,
    api_path: row.api_path,
    api_name: row.api_name,
    api_group: row.api_group,
    allowed_roles: row.allowed_roles || ['admin'],
    min_level: row.min_level || 0,
    description: row.description || '',
    is_active: row.is_active
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除配置 "${row.api_name}"？`, '提示', {
      type: 'warning'
    })

    const res = await deleteApiPermission(row.id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchPermissions()
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
    submitLoading.value = true

    if (isEdit.value) {
      const res = await updateApiPermission(form.id, {
        api_name: form.api_name,
        api_group: form.api_group,
        allowed_roles: form.allowed_roles,
        min_level: form.min_level,
        description: form.description,
        is_active: form.is_active
      })
      if (res.success) {
        ElMessage.success('更新成功')
        dialogVisible.value = false
        fetchPermissions()
      }
    } else {
      const res = await createApiPermission({
        api_path: form.api_path,
        api_name: form.api_name,
        api_group: form.api_group,
        allowed_roles: form.allowed_roles,
        min_level: form.min_level,
        description: form.description
      })
      if (res.success) {
        ElMessage.success('创建成功')
        dialogVisible.value = false
        fetchPermissions()
        fetchGroups()
      }
    }
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitLoading.value = false
  }
}

// 生命周期
onMounted(() => {
  fetchPermissions()
  fetchGroups()
})
</script>

<style scoped>
.api-permission-page {
  padding: 20px;
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

.filter-form {
  margin-bottom: 15px;
}

.role-tag {
  margin-right: 5px;
}

.form-tip {
  color: #909399;
  font-size: 12px;
  margin-left: 10px;
}
</style>