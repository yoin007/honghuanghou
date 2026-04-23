<template>
  <div class="birthday-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="提前天数">
          <el-select v-model="filterForm.days" @change="fetchBirthdays">
            <el-option :value="7" label="7天内" />
            <el-option :value="14" label="14天内" />
            <el-option :value="30" label="30天内" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级" v-if="!isCleader">
          <el-select v-model="filterForm.class_id" placeholder="全部班级" clearable @change="fetchBirthdays">
            <el-option
              v-for="cls in classList"
              :key="cls.class_id"
              :label="cls.class_name"
              :value="cls.class_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="canGenerateReminders">
          <el-button type="primary" @click="handleGenerateReminders">生成本月提醒</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="today-card" v-if="todayBirthdays.length > 0">
      <template #header>
        <span class="today-title">🎉 今日生日</span>
      </template>
      <div class="today-list">
        <div v-for="student in todayBirthdays" :key="student.student_id" class="birthday-item today">
          <span class="student-name">{{ student.name }}</span>
          <span class="class-name">{{ student.class_name }}</span>
          <el-button type="primary" size="small" @click="handleSendBlessing(student)" v-if="canSendReminder">发送祝福</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="upcoming-card">
      <template #header>
        <span>即将过生日的学生</span>
      </template>

      <el-table :data="upcomingBirthdays" v-loading="loading" stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column prop="next_birthday" label="生日日期" width="120">
          <template #default="{ row }">
            {{ formatDate(row.next_birthday) }}
          </template>
        </el-table-column>
        <el-table-column prop="days_until" label="距今天数" width="100">
          <template #default="{ row }">
            <el-tag :type="getDaysTagType(row.days_until)">
              {{ row.days_until === 0 ? '今天' : `${row.days_until}天后` }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleCreateReminder(row)" v-if="canCreateReminder">创建提醒</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card class="reminders-card" v-if="reminderList.length > 0">
      <template #header>
        <span>已创建的提醒</span>
      </template>
      <el-table :data="reminderList" stripe size="small">
        <el-table-column prop="student_name" label="学生" width="100" />
        <el-table-column prop="reminder_date" label="提醒日期" width="120" />
        <el-table-column prop="message" label="祝福内容" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_sent ? 'success' : 'info'" size="small">
              {{ row.is_sent ? '已发送' : '待发送' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleSendReminder(row)" v-if="!row.is_sent && canSendReminder">发送</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建提醒对话框 -->
    <el-dialog v-model="dialogVisible" title="创建生日提醒" width="400px">
      <el-form :model="reminderForm" label-width="80px">
        <el-form-item label="学生">
          <span>{{ reminderForm.student_name }}</span>
        </el-form-item>
        <el-form-item label="提醒日期">
          <el-date-picker
            v-model="reminderForm.reminder_date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="祝福内容">
          <el-input
            v-model="reminderForm.message"
            type="textarea"
            :rows="3"
            placeholder="输入祝福内容（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitReminder">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getUpcomingBirthdays,
  getTodayBirthdays,
  getClasses,
  createBirthdayReminder,
  generateMonthlyReminders,
  getBirthdayReminders,
  sendBirthdayReminder
} from '@/api/modules/moral'
import { useApiPermission } from '@/composables/useApiPermission'
import { useAuthStore } from '@/stores/auth'

// 权限检查
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const authStore = useAuthStore()
const isCleader = computed(() => authStore.role === 'cleader')
const canGenerateReminders = ref(false)
const canCreateReminder = ref(false)
const canSendReminder = ref(false)

// 数据
const loading = ref(false)
const classList = ref([])
const todayBirthdays = ref([])
const upcomingBirthdays = ref([])
const reminderList = ref([])

const filterForm = reactive({
  days: 7,
  class_id: null
})

const dialogVisible = ref(false)
const reminderForm = reactive({
  student_id: '',
  student_name: '',
  reminder_date: '',
  message: ''
})

// 方法
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

const fetchTodayBirthdays = async () => {
  try {
    const res = await getTodayBirthdays()
    if (res.success) {
      todayBirthdays.value = res.data
    }
  } catch (error) {
    console.error('获取今日生日失败:', error)
  }
}

const fetchBirthdays = async () => {
  loading.value = true
  try {
    const res = await getUpcomingBirthdays(filterForm.days, filterForm.class_id)
    if (res.success) {
      upcomingBirthdays.value = res.data
    }
  } catch (error) {
    console.error('获取生日列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleGenerateReminders = async () => {
  try {
    const res = await generateMonthlyReminders()
    if (res.success) {
      ElMessage.success(res.message)
    }
  } catch (error) {
    console.error('生成提醒失败:', error)
  }
}

const handleSendBlessing = (student) => {
  ElMessage.info(`发送祝福给 ${student.name}`)
}

const handleCreateReminder = (student) => {
  reminderForm.student_id = student.student_id
  reminderForm.student_name = student.name
  reminderForm.reminder_date = student.next_birthday
  reminderForm.message = ''
  dialogVisible.value = true
}

const handleSubmitReminder = async () => {
  try {
    const res = await createBirthdayReminder(reminderForm)
    if (res.success) {
      ElMessage.success('提醒创建成功')
      dialogVisible.value = false
      fetchReminders() // 刷新提醒列表
    }
  } catch (error) {
    console.error('创建提醒失败:', error)
  }
}

const fetchReminders = async () => {
  try {
    const res = await getBirthdayReminders({ is_sent: 0, page_size: 20 })
    if (res.success) {
      reminderList.value = res.data.items || []
    }
  } catch (error) {
    console.error('获取提醒列表失败:', error)
  }
}

const handleSendReminder = async (row) => {
  try {
    const res = await sendBirthdayReminder(row.id)
    if (res.success) {
      ElMessage.success('提醒已发送')
      fetchReminders()
    }
  } catch (error) {
    console.error('发送提醒失败:', error)
    ElMessage.error('发送失败')
  }
}

const getDaysTagType = (days) => {
  if (days === 0) return 'danger'
  if (days <= 3) return 'warning'
  return 'success'
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

// 生命周期
onMounted(async () => {
  await loadMyPermissions()
  canGenerateReminders.value = hasApiPermissionSync('/api/moral/birthdays/generate')
  canCreateReminder.value = hasApiPermissionSync('/api/moral/birthdays/reminders/create')
  canSendReminder.value = hasApiPermissionSync('/api/moral/birthdays/reminders/send')
  fetchClassList()
  fetchTodayBirthdays()
  fetchBirthdays()
  fetchReminders()
})
</script>

<style scoped>
.birthday-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.today-card {
  margin-bottom: 20px;
}

.today-title {
  font-size: 16px;
  font-weight: bold;
}

.today-list {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
}

.birthday-item.today {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px 15px;
  background: #fef0f0;
  border-radius: 8px;
}

.birthday-item .student-name {
  font-weight: bold;
}

.birthday-item .class-name {
  color: #909399;
  font-size: 12px;
}
</style>