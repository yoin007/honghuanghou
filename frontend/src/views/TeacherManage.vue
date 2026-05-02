<template>
  <div class="teacher-manage-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>教师管理</span>
          <div class="header-actions">
            <el-button type="success" @click="handleInitTeachingClasses" :icon="Setting" :loading="initLoading" v-if="isAdmin">初始化任教班级</el-button>
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
        <el-select v-model="noticeFilter" placeholder="通知筛选" clearable style="width: 120px" @change="handleSearch">
          <el-option label="全部" value="" />
          <el-option label="启用" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>
        <el-select v-model="activeFilter" placeholder="登录权限筛选" clearable style="width: 130px" @change="handleSearch">
          <el-option label="全部" value="" />
          <el-option label="允许" :value="1" />
          <el-option label="禁止" :value="0" />
        </el-select>
        <el-select v-model="identityFilter" placeholder="身份筛选" clearable style="width: 130px" @change="handleSearch">
          <el-option label="全部" value="" />
          <el-option label="教师账号" value="teacher" />
          <el-option label="微信会员" value="member" />
          <el-option label="已删除" value="deleted_teacher" />
        </el-select>
        <el-button type="primary" @click="handleSearch" :icon="Search">搜索</el-button>
        <el-button @click="handleReset">重置</el-button>
      </div>

      <el-table :data="teacherList" v-loading="loading" style="width: 100%" border stripe>
        <el-table-column prop="teacher_id" label="ID" min-width="130" show-overflow-tooltip />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="identity_type" label="身份" width="100" align="center">
          <template #default="scope">
            <el-tag :type="getIdentityType(scope.row.identity_type)">
              {{ getIdentityText(scope.row.identity_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="wxid" label="微信ID" min-width="170" show-overflow-tooltip />
        <el-table-column prop="subject" label="任教展示" min-width="120" show-overflow-tooltip />
        <el-table-column prop="course" label="课程" min-width="100" />
        <el-table-column prop="role" label="角色" min-width="120" align="center">
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
        <el-table-column prop="active" label="登录权限" width="90" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.active ? 'success' : 'danger'">
              {{ scope.row.active ? '允许' : '禁止' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="notice" label="通知" width="80" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.notice ? 'success' : 'danger'">
              {{ scope.row.notice ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="积分" width="80" align="center" />
        <el-table-column prop="balance" label="余额" width="80" align="center" />
        <el-table-column prop="model" label="模块" min-width="130" show-overflow-tooltip />
        <el-table-column prop="ai_flag" label="AI" width="70" align="center">
          <template #default="scope">{{ scope.row.ai_flag ? '是' : '否' }}</template>
        </el-table-column>
        <el-table-column prop="birthday" label="生日" width="110" />
        <el-table-column prop="is_password_changed" label="密码状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.is_password_changed ? 'success' : 'warning'">
              {{ scope.row.is_password_changed ? '已加密' : '兼容明文' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column prop="updated_at" label="更新时间" min-width="160" show-overflow-tooltip />
        <el-table-column label="操作" width="340" fixed="right" align="center" v-if="isAdmin">
          <template #default="scope">
            <el-button size="small" type="primary" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button size="small" type="success" @click="handleTeachingClasses(scope.row)" :disabled="scope.row.identity_type !== 'teacher'">任教班级</el-button>
            <el-button size="small" type="warning" @click="handleResetPassword(scope.row)" :disabled="scope.row.identity_type !== 'teacher'">重置密码</el-button>
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
            <el-option label="教务" value="jiaowu" />
            <el-option label="学发" value="xuefa" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级" prop="level">
          <el-input-number v-model="teacherForm.level" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="通知" prop="notice">
          <el-switch v-model="teacherForm.notice" :active-value="1" :inactive-value="0" />
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
    <el-dialog v-model="editDialogVisible" title="编辑身份记录" width="720px" :close-on-click-modal="false">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="96px">
        <el-form-item label="原用户名">
          <el-input v-model="editForm.originalUsername" disabled />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="editForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="身份" prop="identity_type">
          <el-select v-model="editForm.identity_type" placeholder="请选择身份">
            <el-option label="教师账号" value="teacher" />
            <el-option label="微信会员" value="member" />
            <el-option label="已删除" value="deleted_teacher" />
          </el-select>
        </el-form-item>
        <el-form-item label="微信ID" prop="wxid">
          <el-input v-model="editForm.wxid" placeholder="请输入微信ID" />
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
            <el-option label="教务" value="jiaowu" />
            <el-option label="学发" value="xuefa" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="等级" prop="level">
          <el-input-number v-model="editForm.level" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="通知" prop="notice">
          <el-switch v-model="editForm.notice" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="登录权限" prop="active">
          <el-switch v-model="editForm.active" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="积分" prop="score">
          <el-input-number v-model="editForm.score" :min="0" :max="999999" />
        </el-form-item>
        <el-form-item label="余额" prop="balance">
          <el-input-number v-model="editForm.balance" :min="0" :max="999999" />
        </el-form-item>
        <el-form-item label="模块" prop="model">
          <el-input v-model="editForm.model" placeholder="basic/lesson/inout" />
        </el-form-item>
        <el-form-item label="AI标记" prop="ai_flag">
          <el-switch v-model="editForm.ai_flag" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="生日" prop="birthday">
          <el-input v-model="editForm.birthday" placeholder="例如 2000-01-01" />
        </el-form-item>
        <el-form-item label="备注" prop="note">
          <el-input v-model="editForm.note" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleEditSubmit" :loading="submitLoading">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 任教班级维护对话框 -->
    <el-dialog v-model="teachingDialogVisible" title="维护任教班级" width="640px" :close-on-click-modal="false">
      <el-form label-width="96px">
        <el-form-item label="教师">
          <el-input :model-value="teachingForm.teacherName" disabled />
        </el-form-item>
        <el-form-item label="任教学科">
          <el-input v-model="teachingForm.subject" placeholder="默认使用教师任教展示，可按需覆盖" />
        </el-form-item>
        <el-form-item label="任教班级">
          <el-select
            v-model="teachingForm.classIds"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择任教班级"
            style="width: 100%"
          >
            <el-option
              v-for="cls in classOptions"
              :key="cls.class_id"
              :label="`${cls.grade_name || ''} ${cls.class_name}`"
              :value="cls.class_id"
            />
          </el-select>
          <div class="form-help">如果 API 目标范围配置为 {"teacher":["teaching_classes"]}，有维护任教班级时教师只能给这些班级学生录入；没有维护任教班级时默认全校班级可录入。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="teachingDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleTeachingSubmit" :loading="submitLoading">保存</el-button>
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
import { Plus, Refresh, Lock, Search, Setting } from '@element-plus/icons-vue'
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
const noticeFilter = ref('')
const activeFilter = ref('')
const identityFilter = ref('')
const submitLoading = ref(false)
const classOptions = ref([])

// 添加对话框
const addDialogVisible = ref(false)
const teacherFormRef = ref(null)
const teacherForm = reactive({
  username: '',
  password: '',
  subject: '',
  course: '',
  role: ['teacher'],
  notice: 1,
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
  originalUsername: '',
  username: '',
  wxid: '',
  subject: '',
  course: '',
  role: ['teacher'],
  notice: 1,
  active: 1,
  level: 1,
  score: 50,
  balance: 0,
  model: 'basic',
  ai_flag: 0,
  birthday: '',
  note: '',
  identity_type: 'teacher'
})

const editRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  identity_type: [{ required: true, message: '请选择身份', trigger: 'change' }]
}

// 任教班级维护对话框
const teachingDialogVisible = ref(false)
const teachingForm = reactive({
  teacherId: '',
  teacherName: '',
  subject: '',
  classIds: []
})

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
    jiaowu: 'primary',
    xuefa: 'warning'
  }
  return roleMap[role] || 'info'
}

const getRoleText = (role) => {
  const roleMap = {
    admin: '管理员',
    teacher: '教师',
    cleader: '班主任',
    jiaowu: '教务',
    xuefa: '学发'
  }
  if (!role) return '-'
  // 支持多角色显示（如 "teacher/cleader" -> "教师/班主任"）
  return role.split('/').map(r => roleMap[r] || r).join('/')
}

const getIdentityText = (identityType) => {
  const map = {
    teacher: '教师账号',
    member: '微信会员',
    deleted_teacher: '已删除'
  }
  return map[identityType] || identityType || '-'
}

const getIdentityType = (identityType) => {
  const map = {
    teacher: 'success',
    member: 'info',
    deleted_teacher: 'danger'
  }
  return map[identityType] || 'warning'
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
      (teacher.teacher_id && teacher.teacher_id.toLowerCase().includes(keyword)) ||
      (teacher.wxid && teacher.wxid.toLowerCase().includes(keyword)) ||
      (teacher.subject && teacher.subject.toLowerCase().includes(keyword)) ||
      (teacher.course && teacher.course.toLowerCase().includes(keyword)) ||
      (teacher.model && teacher.model.toLowerCase().includes(keyword)) ||
      (teacher.note && teacher.note.toLowerCase().includes(keyword))
    )
  }
  // 通知状态筛选
  if (noticeFilter.value !== '') {
    filteredData = filteredData.filter(teacher => teacher.notice === noticeFilter.value)
  }
  // 登录权限筛选
  if (activeFilter.value !== '') {
    filteredData = filteredData.filter(teacher => teacher.active === activeFilter.value)
  }
  if (identityFilter.value !== '') {
    filteredData = filteredData.filter(teacher => teacher.identity_type === identityFilter.value)
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
    const res = await api.get('/api/teachers', { params: { include_all: 1, _t: Date.now() } })
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

const fetchClassOptions = async () => {
  try {
    const res = await api.get('/api/moral/admin/classes', { params: { is_active: 1 } })
    classOptions.value = res.data?.data || res.data || []
  } catch (error) {
    console.error('获取班级列表失败:', error)
    ElMessage.error('获取班级列表失败')
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
  noticeFilter.value = ''
  activeFilter.value = ''
  identityFilter.value = ''
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
  teacherForm.notice = 1
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
          notice: teacherForm.notice,
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
  editForm.originalUsername = row.username
  editForm.username = row.username
  editForm.wxid = row.wxid || ''
  editForm.subject = row.subject || ''
  editForm.course = row.course || ''
  // 将角色字符串拆分为数组（支持多角色如 "teacher/cleader"）
  editForm.role = row.role ? row.role.split('/') : ['teacher']
  editForm.notice = row.notice !== undefined ? row.notice : 1
  editForm.active = row.active !== undefined ? row.active : 1
  editForm.level = row.level || 1
  editForm.score = row.score ?? 50
  editForm.balance = row.balance ?? 0
  editForm.model = row.model || ''
  editForm.ai_flag = row.ai_flag ?? 0
  editForm.birthday = row.birthday || ''
  editForm.note = row.note || ''
  editForm.identity_type = row.identity_type || 'teacher'
  editDialogVisible.value = true
}

const handleEditSubmit = async () => {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        await api.put(`/api/teachers/${editForm.originalUsername}`, {
          username: editForm.username,
          wxid: editForm.wxid,
          subject: editForm.subject,
          course: editForm.course,
          role: editForm.role.join('/'), // 将数组连接为字符串
          notice: editForm.notice,
          active: editForm.active,
          level: editForm.level,
          score: editForm.score,
          balance: editForm.balance,
          model: editForm.model,
          ai_flag: editForm.ai_flag,
          birthday: editForm.birthday,
          note: editForm.note,
          identity_type: editForm.identity_type
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

const handleTeachingClasses = async (row) => {
  teachingForm.teacherId = row.teacher_id || row.username
  teachingForm.teacherName = row.username
  teachingForm.subject = row.subject || ''
  teachingForm.classIds = []
  if (!classOptions.value.length) {
    await fetchClassOptions()
  }
  try {
    const res = await api.get(`/api/teachers/${encodeURIComponent(teachingForm.teacherId)}/teaching-classes`)
    const data = res.data?.data || res.data || {}
    const items = data.items || []
    teachingForm.classIds = items.map(item => item.class_id)
    if (items[0]?.subject) teachingForm.subject = items[0].subject
    teachingDialogVisible.value = true
  } catch (error) {
    console.error('获取任教班级失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取任教班级失败')
  }
}

const handleTeachingSubmit = async () => {
  submitLoading.value = true
  try {
    const payload = {
      classes: teachingForm.classIds.map(classId => ({
        class_id: classId,
        subject: teachingForm.subject || null
      }))
    }
    await api.put(`/api/teachers/${encodeURIComponent(teachingForm.teacherId)}/teaching-classes`, payload)
    ElMessage.success('任教班级已保存')
    teachingDialogVisible.value = false
  } catch (error) {
    console.error('保存任教班级失败:', error)
    ElMessage.error(error.response?.data?.detail || '保存任教班级失败')
  } finally {
    submitLoading.value = false
  }
}

// 初始化所有教师任教班级
const initLoading = ref(false)
const handleInitTeachingClasses = async () => {
  ElMessageBox.confirm(
    '将根据最近一个月的课表数据，批量更新所有教师的任教班级。已有记录的教师会被覆盖更新。确定继续？',
    '初始化任教班级',
    {
      confirmButtonText: '确定初始化',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(async () => {
    initLoading.value = true
    try {
      const res = await api.post('/api/teachers/init-teaching-classes')
      const raw = res?.status !== undefined ? res.data : res
      const data = raw?.data?.diagnostic_version !== undefined || raw?.data?.updated !== undefined
        ? raw.data
        : raw?.data?.data || raw?.data || {}
      const updated = Number(data.updated || 0)
      const message = raw?.message || raw?.data?.message || `初始化完成：${updated} 位教师任教班级已更新`
      if (updated > 0) {
        ElMessage.success(message)
      } else {
        const diagnosticLines = [
          `诊断版本：${data.diagnostic_version || '旧后端未返回'}`,
          `课表目录：${data.lesson_dir || '后端未返回'}`,
          `数据库：${data.moral_db_path || '后端未返回'}`,
          `进程目录：${data.cwd || '后端未返回'}`,
          `检查目录：${(data.checked_schedule_dirs || []).join('；') || '后端未返回'}`,
          `课表文件：${(data.source_files || []).join('；') || '0 个'}`,
          `匹配班级：${data.matched_classes || 0}`,
          `匹配教师：${data.matched_teachers || 0}`,
          `解析课时行：${data.parsed_rows || 0}`
        ]
        console.warn('初始化任教班级诊断', data)
        ElMessage.warning(`${message}。已读取 ${data.source_files?.length || 0} 个课表文件，匹配 ${data.matched_classes || 0} 个班级、${data.matched_teachers || 0} 位教师。`)
        ElMessageBox.alert(diagnosticLines.join('\n'), '初始化任教班级诊断', {
          type: 'warning',
          confirmButtonText: '知道了'
        })
      }
      // 如果有详情，显示更多信息
      if (data.details && data.details.length > 0) {
        const initialized = data.details.filter(d => d.status === 'updated' || d.status === 'initialized')
        const skipped = data.details.filter(d => d.status === 'skipped')
        console.log(`初始化任教班级结果：更新 ${initialized.length} 位，跳过 ${skipped.length} 位（已有记录）`, data)
      }
      await fetchTeachers()
    } catch (error) {
      console.error('初始化任教班级失败:', error)
      ElMessage.error(error.response?.data?.detail || '初始化任教班级失败')
    } finally {
      initLoading.value = false
    }
  }).catch(() => {})
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

.form-help {
  width: 100%;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
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
