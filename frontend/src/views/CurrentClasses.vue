<template>
  <div class="current-classes">
    <!-- 当前课程部分 -->
    <el-card class="box-card mb-4" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">当前课程</span>
          </div>
          <div class="header-right">
            <el-button type="primary" size="small" @click="fetchCurrentClasses" :loading="loading">
              刷新
            </el-button>
          </div>
        </div>
      </template>
      <el-table 
        v-loading="loading" 
        :data="currentClassesArray" 
        style="width: 100%"
        :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
      >
        <el-table-column prop="className" label="班级" width="120">
          <template #default="{ row }">
            <span class="class-name">{{ row.className }}</span>
          </template>
        </el-table-column>
        <!-- <el-table-column prop="currentCourse" label="当前课程" width="120">
          <template #default="{ row }">
            <span class="course-name">{{ row.currentCourse }}</span>
          </template> -->
        <!-- </el-table-column> -->
        <el-table-column prop="teacher" label="任课教师" width="120">
          <template #default="{ row }">
            <span class="teacher-name">{{ row.teacher }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="学科" width="120">
          <template #default="{ row }">
            <span class="subject-name">{{ row.subject }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="period" label="课节" width="120">
          <template #default="{ row }">
            <span class="period-name">{{ row.period }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="时间" min-width="180">
          <template #default="{ row }">
            <span class="time-range">{{ periods[row.period] || '' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 教师课表部分 -->
    <el-card class="box-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="title">教师课表</span>
          <div class="header-right">
            <el-input 
              v-model="teacherSearch" 
              placeholder="搜索教师" 
              style="width: 200px; margin-left: 10px"
            />
            <el-select
              v-model="selectedTeacher"
              placeholder="选择教师"
              style="width: 200px"
              @change="handleTeacherChange"
              :filter-method="filterTeachers"
            >
              <el-option
                v-for="teacher in filteredTeachers"
                :key="teacher"
                :label="teacher"
                :value="teacher"
              />
            </el-select>
            <el-button-group>
              <el-button 
                :type="isNextWeek ? 'default' : 'primary'" 
                size="small" 
                @click="toggleWeek(false)"
                :disabled="!selectedTeacher"
              >
                本周
              </el-button>
              <el-button 
                :type="isNextWeek ? 'primary' : 'default'" 
                size="small" 
                @click="toggleWeek(true)"
                :disabled="!selectedTeacher"
              >
                下周
              </el-button>
            </el-button-group>
            <el-button 
              type="primary" 
              size="small" 
              @click="refreshSchedule" 
              :loading="teacherScheduleLoading"
            >
              刷新
            </el-button>
          </div>
        </div>
      </template>
      <div v-loading="teacherScheduleLoading">
        <template v-if="teacherSchedule">
          <el-table 
            :data="formatTeacherSchedule" 
            style="width: 100%; text-align: center;"
            :header-cell-style="{ background: '#f5f7fa', color: '#606266' }"
            border
          >
            <el-table-column prop="period" label="节次" width="120" fixed="left">
              <template #default="{ row }">
                <div class="period-cell">
                  <span class="period-name">{{ row.period }}</span>
                  <span class="time-range">{{ periods[row.period] || '' }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="monday" label="星期一" min-width="120">
              <template #default="{ row }">
                <template v-if="row.monday">
                  <div v-for="(item, index) in parseScheduleCell(row.monday)" :key="index" class="schedule-cell" style="display: flex; flex-direction: column;">
                    <el-tag size="small" effect="plain" class="class-tag">{{ item.class_code }}</el-tag>
                    <el-tag size="small" effect="plain" type="success" class="subject-tag">{{ item.subject }}</el-tag>
                  </div>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="tuesday" label="星期二" min-width="120">
              <template #default="{ row }">
                <template v-if="row.tuesday">
                  <div v-for="(item, index) in parseScheduleCell(row.tuesday)" :key="index" class="schedule-cell" style="display: flex; flex-direction: column;">
                    <el-tag size="small" effect="plain" class="class-tag">{{ item.class_code }}</el-tag>
                    <el-tag size="small" effect="plain" type="success" class="subject-tag">{{ item.subject }}</el-tag>
                  </div>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="wednesday" label="星期三" min-width="120">
              <template #default="{ row }">
                <template v-if="row.wednesday">
                  <div v-for="(item, index) in parseScheduleCell(row.wednesday)" :key="index" class="schedule-cell" style="display: flex; flex-direction: column;">
                    <el-tag size="small" effect="plain" class="class-tag">{{ item.class_code }}</el-tag>
                    <el-tag size="small" effect="plain" type="success" class="subject-tag">{{ item.subject }}</el-tag>
                  </div>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="thursday" label="星期四" min-width="120">
              <template #default="{ row }">
                <template v-if="row.thursday">
                  <div v-for="(item, index) in parseScheduleCell(row.thursday)" :key="index" class="schedule-cell" style="display: flex; flex-direction: column;">
                    <el-tag size="small" effect="plain" class="class-tag">{{ item.class_code }}</el-tag>
                    <el-tag size="small" effect="plain" type="success" class="subject-tag">{{ item.subject }}</el-tag>
                  </div>
                </template>
              </template>
            </el-table-column>
            <el-table-column prop="friday" label="星期五" min-width="120">
              <template #default="{ row }">
                <template v-if="row.friday">
                  <div v-for="(item, index) in parseScheduleCell(row.friday)" :key="index" class="schedule-cell" style="display: flex; flex-direction: column;">
                    <el-tag size="small" effect="plain" class="class-tag">{{ item.class_code }}</el-tag>
                    <el-tag size="small" effect="plain" type="success" class="subject-tag">{{ item.subject }}</el-tag>
                  </div>
                </template>
              </template>
            </el-table-column>
          </el-table>
        </template>
        <el-empty v-else description="请选择教师查看课表" />
      </div>
    </el-card>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'
import { scheduleApi, getPeriods, getCurrentClasses, getTeacherSchedule, getTeacherScheduleNextweek } from '@/api/modules/schedule'
import { teacherApi } from '@/api/modules/teacher'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const authStore = useAuthStore()
// Pinia 的 computed 在 script setup 中需要用 computed 包装
const isLoggedIn = computed(() => authStore.isLoggedIn)
const username = computed(() => authStore.username)

// 数据定义
const currentClasses = ref({})
const loading = ref(false)
const teachers = ref([])
const selectedTeacher = ref('')
const teacherSchedule = ref(null)
const teacherScheduleLoading = ref(false)
const periods = ref({})
const teacherSearch = ref('')
const isNextWeek = ref(false)

// 将对象格式的当前课程数据转换为数组格式
const currentClassesArray = computed(() => {
  if (!currentClasses.value) return []
  
  // 如果已经是数组，直接返回
  if (Array.isArray(currentClasses.value)) {
    return currentClasses.value
  }
  
  // 如果是对象，转换为数组
  return Object.entries(currentClasses.value).map(([className, data]) => ({
    className,
    ...data
  }))
})

// 解析课表单元格数据
const parseScheduleCell = (cellData) => {
  if (!cellData) return []
  // 增加对不同分隔符的兼容性
  const items = cellData.includes(', ') ? cellData.split(', ') : cellData.split(',')
  
  return items.map(item => {
    item = item.trim()
    if (!item) return null
    
    // 尝试解析 "Class Subject" 格式
    const parts = item.split(' ')
    if (parts.length >= 2) {
      return { 
        class_code: parts[0], 
        subject: parts.slice(1).join(' ') 
      }
    } else {
      // 如果格式不匹配，直接返回原始内容作为 subject，或者标记为未知
      return { class_code: '', subject: item }
    }
  }).filter(Boolean)
}

// 格式化教师课表数据
const formatTeacherSchedule = computed(() => {
  if (!teacherSchedule.value) return []
  
  const periodList = Object.keys(periods.value)
  return periodList.map(period => {
    const row = { period }
    const weekdays = {
      '1': 'monday',
      '2': 'tuesday',
      '3': 'wednesday',
      '4': 'thursday',
      '5': 'friday'
    }
    
    Object.entries(weekdays).forEach(([dayNumber, dayName]) => {
      const classes = teacherSchedule.value[dayNumber]?.[period]
      if (classes && classes.length > 0) {
        row[dayName] = classes.map(c => `${c.class_code} ${c.subject}`).join(', ')
      } else {
        row[dayName] = ''
      }
    })
    
    return row
  })
})

// 教师搜索
const filteredTeachers = computed(() => {
  if (!teacherSearch.value) {
    return teachers.value
  }
  const search = teacherSearch.value.toLowerCase()
  return teachers.value.filter(teacher => 
    teacher.toLowerCase().includes(search)
  )
})

// 教师选择框的过滤方法
const filterTeachers = (query) => {
  const search = query.toLowerCase()
  return teachers.value.filter(teacher => 
    teacher.toLowerCase().includes(search)
  )
}

// 判断是否为移动设备
const isMobile = computed(() => {
  return window.innerWidth <= 768
})

// 监听窗口大小变化
const handleResize = () => {
  // 触发isMobile的重新计算
  window.dispatchEvent(new Event('resize'))
}

// 获取课程时间表
const fetchPeriods = async () => {
  try {
    const response = await getPeriods()
    periods.value = response.data.periods
  } catch (error) {
    handleApiError(error)
    ElMessage.error('获取课程时间表失败')
  }
}

// API错误处理
const handleApiError = (error) => {
  console.error('API error:', error)
  if (error.response?.status === 401) {
    ElMessage.error('登录已过期，请重新登录')
  }
}

// 获取当前各班级课程
const fetchCurrentClasses = async () => {
  loading.value = true
  try {
    const response = await getCurrentClasses()
    currentClasses.value = response.data.current_classes
  } catch (error) {
    handleApiError(error)
    ElMessage.error('获取当前课程信息失败')
  } finally {
    loading.value = false
  }
}

// 获取教师列表
const fetchTeachers = async () => {
  try {
    const response = await teacherApi.getTeachers()
    // 新API返回对象数组，提取username字段
    teachers.value = response.data.teachers.map(t => t.username)
  } catch (error) {
    handleApiError(error)
    ElMessage.error('获取教师列表失败')
  }
}

// 获取教师课表
const fetchTeacherSchedule = async (teacherName) => {
  if (!teacherName) {
    teacherSchedule.value = null
    return
  }

  teacherScheduleLoading.value = true
  try {
    const response = await getTeacherSchedule(teacherName)
    teacherSchedule.value = response.data.schedule
  } catch (error) {
    handleApiError(error)
    ElMessage.error('获取教师课表失败')
  } finally {
    teacherScheduleLoading.value = false
  }
}

// 获取下周课表
const fetchNextWeekSchedule = async (teacherName) => {
  if (!teacherName) return
  
  teacherScheduleLoading.value = true
  try {
    const response = await getTeacherScheduleNextweek(teacherName)
    teacherSchedule.value = response.data.schedule
  } catch (error) {
    handleApiError(error)
    ElMessage.error('获取下周课表失败')
  } finally {
    teacherScheduleLoading.value = false
  }
}

// 切换周次
const toggleWeek = async (nextWeek) => {
  isNextWeek.value = nextWeek
  await refreshSchedule()
}

// 刷新课表
const refreshSchedule = async () => {
  if (selectedTeacher.value) {
    if (isNextWeek.value) {
      await fetchNextWeekSchedule(selectedTeacher.value)
    } else {
      await fetchTeacherSchedule(selectedTeacher.value)
    }
  }
}

// 处理教师选择变更
const handleTeacherChange = async (teacher) => {
  isNextWeek.value = false // 切换教师时重置为本周
  await fetchTeacherSchedule(teacher)
}

// Watch for login changes
watch(() => authStore.isLoggedIn, async (newVal) => {
  if (newVal) {
    try {
      await fetchTeachers()
      if (username.value) {
        selectedTeacher.value = username.value
      }
      await Promise.all([
        fetchCurrentClasses(),
        fetchTeacherSchedule(username.value),
        fetchPeriods()
      ])
    } catch (error) {
      handleApiError(error)
    }
  } else {
    // Clear data on logout
    currentClasses.value = []
    teacherSchedule.value = null
    teachers.value = []
    selectedTeacher.value = ''
  }
})

// 自动刷新课表
const autoRefreshSchedule = async () => {
  if (isLoggedIn.value && selectedTeacher.value) {
    try {
      await Promise.all([
        fetchCurrentClasses(),
        isNextWeek.value ? 
          fetchNextWeekSchedule(selectedTeacher.value) : 
          fetchTeacherSchedule(selectedTeacher.value)
      ])
    } catch (error) {
      handleApiError(error)
    }
  }
}

// 设置自动刷新
let refreshInterval
onMounted(async () => {
  if (isLoggedIn.value) {
    try {
      await fetchTeachers()
      if (username.value && !selectedTeacher.value) {
        selectedTeacher.value = username.value
      }
      await Promise.all([
        fetchCurrentClasses(),
        fetchTeacherSchedule(selectedTeacher.value || username.value),
        fetchPeriods()
      ])
    } catch (error) {
      handleApiError(error)
    }
  }
  
  // 设置自动刷新
  refreshInterval = setInterval(autoRefreshSchedule, 60000*8)
})

watch(
  () => route.fullPath,
  async () => {
    if (isLoggedIn.value && selectedTeacher.value) {
      try {
        await Promise.all([
          fetchCurrentClasses(),
          isNextWeek.value
            ? fetchNextWeekSchedule(selectedTeacher.value)
            : fetchTeacherSchedule(selectedTeacher.value),
          fetchPeriods()
        ])
      } catch (error) {
        handleApiError(error)
      }
    }
  }
)

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.current-classes {
  padding: 20px;
}

.box-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .header-right {
    display: flex;
    gap: 10px;
    align-items: center;
    
    @media screen and (max-width: 768px) {
      flex-wrap: wrap;
      justify-content: flex-end;
      
      .el-input,
      .el-select {
        width: 100% !important;
        margin-bottom: 10px;
      }
      
      .el-button-group {
        width: 100%;
        display: flex;
        
        .el-button {
          flex: 1;
        }
      }
    }
  }
}

.title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}

.mb-4 {
  margin-bottom: 1rem;
}

.class-name {
  color: #409EFF;
  font-weight: bold;
}

.course-name {
  color: #67C23A;
}

.teacher-name {
  color: #E6A23C;
}

.subject-name {
  color: #F56C6C;
}

.period-name {
  font-weight: bold;
  color: #303133;
  text-align: center;
}

.time-range {
  color: #909399;
  font-size: 12px;
  margin-left: 8px;
}

.schedule-cell {
  padding: 4px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.class-tag {
  color: #409EFF;
  border-color: #409EFF;
}

.subject-tag {
  color: #67C23A;
  border-color: #67C23A;
}

.schedule-cell:not(:last-child) {
  border-bottom: 1px dashed #EBEEF5;
}

.period-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.period-name {
  font-weight: bold;
  color: #303133;
}

.time-range {
  font-size: 12px;
  color: #909399;
}

/* 表格悬浮效果 */
:deep(.el-table__row:hover > td) {
  background-color: #F5F7FA !important;
}

/* 表格单元格内边距 */
:deep(.el-table td) {
  padding: 8px;
}

.user-info {
  font-size: 14px;
  color: #606266;
}

/* 移动设备适配 */
@media screen and (max-width: 768px) {
  .current-classes-container {
    padding: 0.5rem;
  }

  :deep(.el-table) {
    font-size: 14px;
  }

  :deep(.el-table .cell) {
    padding: 8px 4px;
  }

  .class-name, .course-name, .teacher-name, 
  .subject-name, .period-name, .time-range {
    font-size: 14px;
  }

  :deep(.el-dialog__body) {
    padding: 15px;
  }

  :deep(.el-form-item__label) {
    font-size: 14px;
  }

  .card-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .header-left {
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

/* 登录对话框样式 */
:deep(.login-dialog) {
  border-radius: 8px;
  
  .el-dialog__header {
    padding: 15px 20px;
    margin-right: 0;
    border-bottom: 1px solid #eee;
  }

  .el-dialog__body {
    padding: 20px;
  }

  .el-form-item {
    margin-bottom: 20px;
  }

  .el-input {
    width: 100%;
  }
}
</style>
