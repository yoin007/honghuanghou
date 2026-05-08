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
          <span class="leader-name">班主任: {{ student.leader_name || '未设置' }}</span>
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
        <el-table-column prop="leader_name" label="班主任" width="100">
          <template #default="{ row }">
            {{ row.leader_name || '未设置' }}
          </template>
        </el-table-column>
        <el-table-column prop="next_birthday" label="生日日期" width="120">
          <template #default="{ row }">
            {{ formatDateChinese(row.next_birthday) }}
          </template>
        </el-table-column>
        <el-table-column prop="days_until" label="距今天数" width="100">
          <template #default="{ row }">
            <el-tag :type="getDaysTagType(row.days_until)">
              {{ row.days_until === 0 ? '今天' : `${row.days_until}天后` }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useApiPermission } from '@/composables/useApiPermission'
import { useAuthStore } from '@/stores/auth'
import {
  getUpcomingBirthdays,
  getTodayBirthdays,
  getClasses
} from '@/api/modules/moral'
import { formatDateChinese } from '@/utils/time'

const { loadMyPermissions } = useApiPermission()
const authStore = useAuthStore()
const isCleader = computed(() => authStore.isCleader)

// 数据
const loading = ref(false)
const classList = ref([])
const todayBirthdays = ref([])
const upcomingBirthdays = ref([])

const filterForm = reactive({
  days: 7,
  class_id: null
})

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

const getDaysTagType = (days) => {
  if (days === 0) return 'danger'
  if (days <= 3) return 'warning'
  return 'success'
}

onMounted(async () => {
  await loadMyPermissions()
  fetchClassList()
  fetchTodayBirthdays()
  fetchBirthdays()
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

.birthday-item .leader-name {
  color: #606266;
  font-size: 12px;
}
</style>
