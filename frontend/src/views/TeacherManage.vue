<template>
  <div class="teacher-manage-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>教师管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="handleAdd" :icon="Plus" v-if="isAdmin">添加教师</el-button>
            <el-button type="warning" @click="handleChangeMyPassword" :icon="Lock" v-if="!isAdmin">修改密码</el-button>
            <el-button type="info" @click="fetchTeachers" :icon="Refresh" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户名/科目/课程"
          clearable
          style="width: 250px"
          @keyup.enter="handleSearch"
        />
        <el-select v-model="activeFilter" placeholder="通知筛选" clearable style="width: 120px" @change="handleSearch">
          <el-option label="全部" value="" />
          <el-option label="启用" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>
        <el-button type="primary" @click="handleSearch" :icon="Search">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table :data="teacherList" v-loading="loading" style="width: 100%" border stripe>
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="subject" label="科目" width="120" />
        <el-table-column prop="course" label="课程" min-width="150" />
        <el-table-column prop="role" label="角色" width="100" align="center">
          <template #default="scope">
            <el-tag :type="getRoleType(scope.row.role)">
              {{ getRoleText(scope.row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="level" label="等级" width="80" align="center">
          <template #default="scope">
            {{ scope.row.level || 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="active" label="通知" width="80" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.active ? 'success' : 'danger'">
              {{ scope.row.active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right" align="center" v-if="isAdmin">
          <template #default="scope">
            <el-button size="small" type="primary" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="warning" @click="handleResetPassword(scope.row)">重置密码</el-button>
            <el-button size="small" type="danger" @click="handleDelete(scope.row)" :disabled="scope.row.role === 'admin'">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 添加教师对话框 -->
    <el-dialog v-model="addDialogVisible" title="添加教师" width="500px" :close-on-click-modal="false">
      <el-form :model="teacherForm" :rules="teacherRules" ref="teacherFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="teacherForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="teacherForm.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="科目" prop="subject">
          <el-input v-model="teacherForm.subject" placeholder="请输入科目" />
        </el-form-item>
        <el-form-item label="课程" prop="course">
          <el-input v-model="teacherForm.course" placeholder="请输入课程" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="teacherForm.role" multiple placeholder="请选择角色（可多选）">
            <el-option label="教师" value="teacher" />
            <el-option label="班主任" value="cleader" />
            <el-option label="学发部" value="xuefa" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级" prop="level">
          <el-input-number v-model="teacherForm.level" :min="0" :max="10" />
        </el-form-item>
        <el-form-item label="状态" prop="active">
          <el-switch v-model="teacherForm.active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleAddSubmit" :loading="submitLoading">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑教师对话框 -->
    <el-dialog v-model="editDialogVisible" title="编辑教师" width="500px" :close-on-click-modal="false">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="editForm.username" disabled />
        </el-form-item>
        <el-form-item label="科目" prop="subject">
          <el-input v-model="editForm.subject" placeholder="请输入科目" />
        </el-form-item>
        <el-form-item label="课程" prop="course">
          <el-input v-model="editForm.course" placeholder="请输入课程" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" multiple placeholder="请选择角色（可多选）">
            <el-option label="教师" value="teacher" />
            <el-option label="班主任" value="cleader" />
            <el-option label="学发部" value="xuefa" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级" prop="level">
          <el-input-number v-model="editForm.level" :min="0" :max="10" />
        </el-form-item>
        <el-form-item label="状态" prop="active">
          <el-switch v-model="editForm.active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleEditSubmit" :loading="submitLoading">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px" :close-on-click-modal="false">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="80px">
        <el-form-item label="用户">
          <el-input v-model="passwordForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resetDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleResetSubmit" :loading="submitLoading">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 修改自己密码对话框 -->
    <el-dialog v-model="changePasswordDialogVisible" title="修改密码" width="400px" :close-on-click-modal="false">
      <el-form :model="changePasswordForm" :rules="changePasswordRules" ref="changePasswordFormRef" label-width="80px">
        <el-form-item label="旧密码" prop="old_password">
          <el-input v-model="changePasswordForm.old_password" type="password" show-password placeholder="请输入旧密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="changePasswordForm.new_password" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="changePasswordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="changePasswordDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleChangePasswordSubmit" :loading="submitLoading">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { Plus, Refresh, Lock, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../utils/api'
import { useAuthStore } from '../stores/auth'

// 使用 Pinia auth store
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)

// 数据
const loading = ref(false)
const teacherList = ref([])
const allTeachers = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const searchKeyword = ref('')
const activeFilter = ref('')
const submitLoading = ref(false)

// 添加对话框
const addDialogVisible = ref(false)
const teacherFormRef = ref(null)
const teacherForm = reactive({
  username: '',
  password: '',
  subject: '',
  course: '',
  role: 'teacher',
  active: true,
  level: 1
})

const teacherRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
}

// 编辑对话框
const editDialogVisible = ref(false)
const editFormRef = ref(null)
const editForm = reactive({
  username: '',
  subject: '',
  course: '',
  role: 'teacher',
  active: true,
  level: 1
})

const editRules = {
  subject: [{ required: true, message: '请输入科目', trigger: 'blur' }]
}

// 重置密码对话框
const resetDialogVisible = ref(false)
const passwordFormRef = ref(null)
const passwordForm = reactive({
  username: '',
  new_password: '',
  confirm_password: ''
})

const passwordRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 修改自己密码对话框
const changePasswordDialogVisible = ref(false)
const changePasswordFormRef = ref(null)
const changePasswordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const changePasswordRules = {
  old_password: [
    { required: true, message: '请输入旧密码', trigger: 'blur' }
  ],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== changePasswordForm.new_password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 方法
const getRoleType = (role) => {
  const roleMap = {
    admin: 'danger',
    teacher: 'success',
    cleader: 'warning',
    xuefa: 'warning'
  }
  return roleMap[role] || 'info'
}

const getRoleText = (role) => {
  const roleMap = {
    admin: '管理员',
    teacher: '教师',
    cleader: '班主任',
    xuefa: '学发部'
  }
  if (!role) return '-'
  // 支持多角色显示（如 "teacher/cleader" -> "教师/班主任"）
  return role.split('/').map(r => roleMap[r] || r).join('/')
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

// 计算分页数据
const updatePagination = () => {
  // 过滤数据
  let filteredData = allTeachers.value
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filteredData = filteredData.filter(teacher =>
      teacher.username.toLowerCase().includes(keyword) ||
      (teacher.subject && teacher.subject.toLowerCase().includes(keyword)) ||
      (teacher.course && teacher.course.toLowerCase().includes(keyword))
    )
  }
  // 通知状态筛选
  if (activeFilter.value !== '') {
    filteredData = filteredData.filter(teacher => teacher.active === activeFilter.value)
  }
  // 分页
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  teacherList.value = filteredData.slice(start, end)
  total.value = filteredData.length
}

// 获取教师列表
const fetchTeachers = async () => {
  loading.value = true
  try {
    const res = await api.get('/api/teachers', { params: { _t: Date.now() } })
    allTeachers.value = res.data.teachers || []
    total.value = allTeachers.value.length
    updatePagination()
  } catch (error) {
    console.error('获取教师列表失败:', error)
    ElMessage.error('获取教师列表失败')
  } finally {
    loading.value = false
  }
}

// 分页大小变化
const handleSizeChange = (val) => {
  pageSize.value = val
  currentPage.value = 1
  updatePagination()
}

// 当前页变化
const handleCurrentChange = (val) => {
  currentPage.value = val
  updatePagination()
}

// 搜索
const handleSearch = () => {
  currentPage.value = 1
  updatePagination()
}

// 重置搜索
const handleReset = () => {
  searchKeyword.value = ''
  activeFilter.value = ''
  currentPage.value = 1
  updatePagination()
}

// 添加教师
const handleAdd = () => {
  teacherForm.username = ''
  teacherForm.password = ''
  teacherForm.subject = ''
  teacherForm.course = ''
  teacherForm.role = ['teacher']
  teacherForm.active = true
  teacherForm.level = 1
  addDialogVisible.value = true
}

const handleAddSubmit = async () => {
  if (!teacherFormRef.value) return
  await teacherFormRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        await api.post('/api/teachers', {
          username: teacherForm.username,
          password: teacherForm.password,
          subject: teacherForm.subject,
          course: teacherForm.course,
          role: teacherForm.role.join('/'), // 将数组连接为字符串
          active: teacherForm.active,
          level: teacherForm.level
        })
        ElMessage.success('添加成功')
        addDialogVisible.value = false
        fetchTeachers()
      } catch (error) {
        console.error('添加教师失败:', error)
        ElMessage.error(error.response?.data?.detail || '添加教师失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 编辑教师
const handleEdit = (row) => {
  editForm.username = row.username
  editForm.subject = row.subject || ''
  editForm.course = row.course || ''
  // 将角色字符串拆分为数组（支持多角色如 "teacher/cleader"）
  editForm.role = row.role ? row.role.split('/') : ['teacher']
  editForm.active = row.active !== false
  editForm.level = row.level || 1
  editDialogVisible.value = true
}

const handleEditSubmit = async () => {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        await api.put(`/api/teachers/${editForm.username}`, {
          subject: editForm.subject,
          course: editForm.course,
          role: editForm.role.join('/'), // 将数组连接为字符串
          active: editForm.active,
          level: editForm.level
        })
        ElMessage.success('更新成功')
        editDialogVisible.value = false
        fetchTeachers()
      } catch (error) {
        console.error('更新教师失败:', error)
        ElMessage.error(error.response?.data?.detail || '更新教师失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 删除教师
const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除教师 ${row.username} 吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await api.delete(`/api/teachers/${row.username}`)
      ElMessage.success('删除成功')
      fetchTeachers()
    } catch (error) {
      console.error('删除教师失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除教师失败')
    }
  }).catch(() => {})
}

// 重置密码
const handleResetPassword = (row) => {
  passwordForm.username = row.username
  passwordForm.new_password = ''
  passwordForm.confirm_password = ''
  resetDialogVisible.value = true
}

const handleResetSubmit = async () => {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        await api.post('/api/admin/set-password', {
          username: passwordForm.username,
          new_password: passwordForm.new_password
        })
        ElMessage.success('密码重置成功')
        resetDialogVisible.value = false
      } catch (error) {
        console.error('重置密码失败:', error)
        ElMessage.error(error.response?.data?.detail || '重置密码失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

// 修改自己的密码
const handleChangeMyPassword = () => {
  changePasswordForm.old_password = ''
  changePasswordForm.new_password = ''
  changePasswordForm.confirm_password = ''
  changePasswordDialogVisible.value = true
}

const handleChangePasswordSubmit = async () => {
  if (!changePasswordFormRef.value) return
  await changePasswordFormRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        await api.post('/api/teachers/change-password', {
          old_password: changePasswordForm.old_password,
          new_password: changePasswordForm.new_password
        })
        ElMessage.success('密码修改成功')
        changePasswordDialogVisible.value = false
      } catch (error) {
        console.error('修改密码失败:', error)
        ElMessage.error(error.response?.data?.detail || '修改密码失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

onMounted(() => {
  fetchTeachers()
})
</script>

<style scoped>
.teacher-manage-container {
  padding: 20px;
  overflow-x: auto;
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

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .teacher-manage-container {
    padding: 10px;
    overflow-x: visible;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .search-bar {
    flex-direction: column;
  }

  .search-bar .el-input {
    width: 100% !important;
  }

  /* Table 移动端横向滚动 - 确保滚动条可见 */
  :deep(.el-table) {
    width: 100% !important;
    overflow-x: scroll !important;
    display: block;
  }

  :deep(.el-table__inner-wrapper) {
    width: 100%;
    overflow-x: scroll;
  }

  :deep(.el-table__header-wrapper),
  :deep(.el-table__body-wrapper) {
    overflow-x: scroll;
    display: block;
  }

  :deep(.el-table__header),
  :deep(.el-table__body) {
    min-width: 100%;
  }

  /* 显示滚动条 */
  :deep(.el-scrollbar__bar.is-horizontal) {
    display: block !important;
    opacity: 1;
  }

  /* 移除固定列的固定定位，使表格可以正常滚动 */
  :deep(.el-table__fixed),
  :deep(.el-table__fixed-right) {
    display: none !important;
  }
}
</style>
