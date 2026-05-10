<template>
  <div class="schedules-page">
    <div class="schedules-container">
      <h2>课程表列表</h2>
      
      <el-empty v-if="!loading && (!validSchedules || validSchedules.length === 0)" description="暂无课程表数据" />
      
      <div v-else-if="loading" class="loading-container">
        <div class="loading-spinner">加载中...</div>
      </div>
      
      <div v-else class="schedules-list">
        <div class="schedule-cards">
          <div 
            v-for="(item, index) in allSchedules" 
            :key="index"
            class="schedule-card-wrapper"
          >
            <div class="schedule-card">
              <div class="card-header">
                <span>{{ index === 0 ? '当前课表' : index === 1 ? '下周课表' : `课程表 ${index + 1}` }}</span>
              </div>
              <div class="card-content">
                <a 
                  v-if="item && item.trim() !== ''"
                  :href="getScheduleDownloadUrl(item)" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  class="schedule-link"
                >
                  📄 点击下载
                </a>
                <div v-else class="no-data">
                  ❌ 尚未排好
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="schedules-container">
      <h2>本周课表</h2>
      
      <div class="week-tabs">
        <div
          v-for="day in visibleWeekDays"
          :key="day.date"
          class="week-tab"
          :class="{
            'active': selectedDate === day.date,
            'today': day.isToday,
            'past': day.isPast
          }"
          @click="handleDateChange(day.date)"
        >
          <div class="tab-day">{{ day.label }}</div>
          <div class="tab-date">{{ day.dateStr }}</div>
        </div>
      </div>
      
      <div v-if="selectedDateInfo" class="date-info">
        {{ selectedDateInfo }}
      </div>
      
      <el-empty v-if="!loading && (!todays || todays.length === 0)" description="暂无课程表数据" />
      
      <div v-else-if="loading" class="loading-container">
        <div class="loading-spinner">加载中...</div>
      </div>
      
      <el-table
        v-else
        :data="tableData"
        border
        stripe
        style="width: 100%"
        class="schedules-table"
        :row-class-name="tableRowClassName"
      >
        <el-table-column prop="week" label="星期" fixed="left" />
        <el-table-column prop="order" label="节次" fixed="left" />
        
        <el-table-column
          v-for="column in classColumns"
          :key="column"
          :prop="column"
          :label="column"
        >
          <template #default="scope">
            {{ scope.row[column] }}
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { scheduleApi } from '@/api/modules/schedule'

const schedules = ref([])
const todays = ref([])
const loading = ref(false)
const selectedDate = ref('')
const weekHasClass = ref({}) // 记录一周各天是否有课

const getWeekDays = () => {
  const today = new Date()
  const dayOfWeek = today.getDay()
  const monday = new Date(today)
  monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1))

  const days = []
  const labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

  for (let i = 0; i < 7; i++) {
    const date = new Date(monday)
    date.setDate(monday.getDate() + i)
    const dateStr = `${date.getMonth() + 1}-${date.getDate()}`
    const isToday = date.toDateString() === today.toDateString()
    const isPast = date < new Date(today.setHours(0, 0, 0, 0))

    days.push({
      date: date.toISOString().split('T')[0],
      label: labels[i],
      dateStr: dateStr,
      isToday,
      isPast,
      hasClass: true // 默认显示，后续根据数据动态调整
    })
  }

  return days
}

const weekDays = ref(getWeekDays())

const getScheduleDownloadUrl = (rawUrl) => {
  const urlText = typeof rawUrl === 'string' ? rawUrl.trim() : ''
  if (!urlText) return ''

  const isHttpsPage =
    typeof window !== 'undefined' && window.location && window.location.protocol === 'https:'

  if (!isHttpsPage) return urlText

  if (urlText.startsWith('/static')) return urlText

  if (urlText.startsWith('http://') || urlText.startsWith('https://')) {
    try {
      const parsed = new URL(urlText)
      if (parsed.protocol === 'http:') {
        const idx = parsed.pathname.indexOf('/static')
        if (idx !== -1) {
          return parsed.pathname.slice(idx) + parsed.search + parsed.hash
        }
      }
    } catch {
      return urlText
    }
  }

  return urlText
}

const allSchedules = computed(() => {
  return schedules.value
})

const validSchedules = computed(() => {
  return schedules.value.filter(url => url && url.trim() !== '')
})

const selectedDateInfo = computed(() => {
  if (!selectedDate.value) return ''
  try {
    const day = weekDays.value.find(d => d.date === selectedDate.value)
    if (day) {
      return `${day.label} ${day.dateStr}`
    }
    const date = new Date(selectedDate.value)
    return `${date.getMonth() + 1}月${date.getDate()}日`
  } catch {
    return ''
  }
})

// 根据有课日期过滤显示的日期标签
const visibleWeekDays = computed(() => {
  return weekDays.value.filter(day => day.hasClass)
})

const fetchWeekSchedule = async () => {
  // 获取一周7天的课表数据，判断哪些天有课
  const today = new Date()
  const dayOfWeek = today.getDay()
  const monday = new Date(today)
  monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1))

  const hasClassMap = {}

  for (let i = 0; i < 7; i++) {
    const date = new Date(monday)
    date.setDate(monday.getDate() + i)
    const dateStr = date.toISOString().split('T')[0]

    try {
      const response = await scheduleApi.getTodays(dateStr)
      const data = Array.isArray(response.data) ? response.data : (response.data ? [response.data] : [])
      // 判断是否有课：数据不为空且有实际课程内容（不只是空行）
      const hasRealClass = data.some(row => {
        // 检查是否有非空课程内容（排除只包含 week/order 等固定列的空行）
        const keys = Object.keys(row)
        const classColumns = keys.filter(k => !['style', 'date', 'week', 'order'].includes(k))
        return classColumns.some(col => row[col] && row[col].trim() !== '')
      })
      hasClassMap[dateStr] = hasRealClass
    } catch {
      hasClassMap[dateStr] = false
    }
  }

  // 更新 weekDays 的 hasClass 属性
  weekDays.value.forEach(day => {
    day.hasClass = hasClassMap[day.date] ?? false
  })

  weekHasClass.value = hasClassMap
}

const fetchTodays = async (date = null) => {
  loading.value = true
  try {
    const response = await scheduleApi.getTodays(date)
    if (Array.isArray(response.data)) {
      todays.value = response.data
    } else {
      if (response.data && typeof response.data === 'object') {
        todays.value = [response.data]
      } else {
        console.error('API返回数据不是数组格式:', response.data)
        ElMessage.error('API返回数据不是数组格式')
        todays.value = []
      }
    }
  } catch (error) {
    console.error('获取今日课程表数据失败:', error)
    todays.value = []
  } finally {
    loading.value = false
  }
}

const fetchSchedules = async () => {
  loading.value = true
  try {
    const response = await scheduleApi.getAllSchedules()
    if (Array.isArray(response.data)) {
      schedules.value = response.data
    } else {
      console.error('API返回数据格式错误:', response.data)
      schedules.value = []
    }
  } catch (error) {
    console.error('获取课程表数据失败:', error)
    schedules.value = []
  } finally {
    loading.value = false
  }
}

const handleDateChange = (date) => {
  selectedDate.value = date
  fetchTodays(date)
}

const classColumns = computed(() => {
  if (!todays.value || todays.value.length === 0) return []
  const allKeys = Object.keys(todays.value[0] || {})
  const fixedColumns = ['style', 'date', 'week', 'order']
  return allKeys.filter(key => !fixedColumns.includes(key))
})

const tableData = computed(() => {
  return Array.isArray(todays.value) ? todays.value : []
})

const tableRowClassName = ({ rowIndex }) => {
  if (rowIndex === 0) {
    return 'first-row'
  }
  if (rowIndex >= 1 && rowIndex <= 4) {
    return 'color-group-1'
  }
  if (rowIndex >= 5 && rowIndex <= 8) {
    return 'color-group-2'
  }
  if (rowIndex >= 9 && rowIndex <= 12) {
    return 'color-group-3'
  }
  const groupIndex = Math.floor((rowIndex - 1) / 4)
  return groupIndex % 2 === 0 ? 'color-group-1' : 'color-group-2'
}

onMounted(async () => {
  const today = new Date()
  selectedDate.value = today.toISOString().split('T')[0]

  // 先获取一周课表数据，判断哪些天有课
  await fetchWeekSchedule()

  // 如果今天没课，自动选择第一个有课的日期
  if (!weekHasClass.value[selectedDate.value]) {
    const firstDayWithClass = weekDays.value.find(d => d.hasClass)
    if (firstDayWithClass) {
      selectedDate.value = firstDayWithClass.date
    }
  }

  fetchSchedules()
  fetchTodays(selectedDate.value)
})
</script>

<style scoped>
.schedules-container {
  padding: 20px;
}

.schedules-container h2 {
  margin-bottom: 20px;
  text-align: center;
}

.week-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  overflow-x: auto;
  padding-bottom: 10px;
}

.week-tab {
  flex: 1;
  min-width: 70px;
  padding: 12px 8px;
  text-align: center;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: #f5f7fa;
  border: 2px solid transparent;
}

.week-tab:hover {
  background: #ecf5ff;
  border-color: #409eff;
}

.week-tab.active {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

.week-tab.today {
  border-color: #67c23a;
}

.week-tab.today.active {
  background: #67c23a;
  border-color: #67c23a;
}

.week-tab.past {
  opacity: 0.6;
}

.tab-day {
  font-size: 14px;
  font-weight: bold;
  margin-bottom: 4px;
}

.tab-date {
  font-size: 12px;
}

.date-info {
  text-align: center;
  font-size: 16px;
  color: #409eff;
  margin-bottom: 15px;
  font-weight: bold;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}

.loading-spinner {
  color: #409eff;
  font-size: 16px;
}

.schedules-list {
  margin-top: 20px;
}

.schedule-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.schedule-card-wrapper {
  flex: 1;
  min-width: 300px;
}

.schedule-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.card-header {
  font-weight: bold;
  color: #303133;
  margin-bottom: 12px;
  font-size: 16px;
}

.card-content {
  padding: 8px 0;
}

.schedule-link {
  color: #409eff;
  text-decoration: none;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.schedule-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}

.no-data {
  color: #f56c6c;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
}

:deep(.el-table__body-wrapper .el-table__body tr.first-row td) {
  background-color: #e6f7ff !important;
}

:deep(.el-table__body-wrapper .el-table__body tr.color-group-1 td) {
  background-color: #f6ffed !important;
}

:deep(.el-table__body-wrapper .el-table__body tr.color-group-2 td) {
  background-color: #fff7e6 !important;
}

:deep(.el-table__body-wrapper .el-table__body tr.color-group-3 td) {
  background-color: #f7aa6b !important;
}

:deep(.el-table__body-wrapper .el-table__body tr.first-row:hover td) {
  background-color: #bae7ff !important;
}

:deep(.el-table__body-wrapper .el-table__body tr.color-group-1:hover td) {
  background-color: #d9f7be !important;
}

:deep(.el-table__body-wrapper .el-table__body tr.color-group-2:hover td) {
  background-color: #ffd591 !important;
}

:deep(.el-table__body-wrapper .el-table__body tr.color-group-3:hover td) {
  background-color: #d97b2e !important;
}

@media screen and (max-width: 768px) {
  .schedules-container {
    padding: 10px;
  }
  
  .schedules-container h2 {
    font-size: 1.2rem;
    margin-bottom: 15px;
  }

  .week-tabs {
    gap: 6px;
  }

  .week-tab {
    min-width: 50px;
    padding: 10px 4px;
  }

  .tab-day {
    font-size: 12px;
  }

  .tab-date {
    font-size: 11px;
  }

  .schedule-cards {
    gap: 10px;
  }

  .schedule-card-wrapper {
    min-width: 100%;
  }
  
  .schedule-card {
    padding: 12px;
  }
  
  :deep(.el-table) {
    font-size: 12px;
  }
  
  :deep(.el-table .cell) {
    padding: 4px;
  }
}
</style>
