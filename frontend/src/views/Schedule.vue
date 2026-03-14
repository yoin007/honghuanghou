<template>
  <div class="schedule-container">
    <h2>{{ classCode ? `${classCode}课程表` : '课程表' }}</h2>
    
    <el-empty v-if="!loading && !schedule" description="暂无课程表数据" />
    
    <div v-else-if="loading" class="loading-container" v-loading="true">
    </div>
    
    <el-table
      v-else
      :data="tableData"
      border
      :cell-style="getCellStyle"
      class="schedule-table"
    >
      <el-table-column prop="period" label="节次" min-width="120" fixed="left" />
      <el-table-column prop="monday" label="星期一" min-width="120" />
      <el-table-column prop="tuesday" label="星期二" min-width="120" />
      <el-table-column prop="wednesday" label="星期三" min-width="120" />
      <el-table-column prop="thursday" label="星期四" min-width="120" />
      <el-table-column prop="friday" label="星期五" min-width="120" />
    </el-table>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../utils/api'

const route = useRoute()
const schedule = ref(null)
const loading = ref(false)
const currentTime = ref(new Date())  // 使用实际当前时间
const periods = ref({}) // 课程时间表数据
const classCode = ref('') // 班级代码

// 更新当前时间的函数
const updateCurrentTime = () => {
  currentTime.value = new Date()
}

// 每分钟更新一次时间
let timeInterval

onMounted(() => {
  fetchSchedule()
  fetchPeriods()  // 获取课程时间数据
  classCode.value = getClassCode() // 获取班级代码
  // 立即更新一次时间
  updateCurrentTime()
  // 设置定时更新
  timeInterval = setInterval(updateCurrentTime, 60000) // 每分钟更新一次
})

watch(
  () => route.fullPath,
  () => {
    fetchSchedule()
    fetchPeriods()
  }
)

// 组件卸载时清除定时器
onUnmounted(() => {
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})

// 获取当前是星期几（0-6，0是星期日）
const currentDay = computed(() => currentTime.value.getDay())

// 获取当前时间对应的课节
const getCurrentPeriod = () => {
  const hour = currentTime.value.getHours()
  const minute = currentTime.value.getMinutes()
  const time = hour * 60 + minute

  // 如果 periods 为空，返回 -1
  if (!periods.value || Object.keys(periods.value).length === 0) {
    return -1
  }

  const periodsList = Object.keys(periods.value)
  const currentPeriod = periodsList.findIndex(period => {
    const timeRange = periods.value[period]

    // 确保 timeRange 为字符串再处理，避免调用 split 报错
    if (typeof timeRange !== 'string') {
      return false
    }

    const parts = timeRange.split('-')
    if (parts.length !== 2) {
      return false
    }

    const [startTime, endTime] = parts.map(t => {
      const [h, m] = t.split(':').map(Number)
      return h * 60 + m
    })

    return time >= startTime && time <= endTime
  })

  return currentPeriod
}

const tableData = computed(() => {
  if (!schedule.value || !periods.value) return []
  
  // 使用后端返回的 periods 数据的键作为课节列表
  const periodKeys = Object.keys(periods.value)
  const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
  // const currentPeriod = getCurrentPeriod()
  
  return periodKeys.map((period) => {
    const row = { 
      // period: `${period} (${periods.value[period]})` // 显示课节名称和时间
      period: `${period}` // 显示课节名称和时间
    }
    days.forEach((day) => {
      row[day] = schedule.value[day] && schedule.value[day][periodKeys.indexOf(period)]
        ? schedule.value[day][periodKeys.indexOf(period)]
        : ''
    })
    return row
  })
})

const getSubjectColor = (subject) => {
  const colors = {
    '语文': '#FFE7E7',
    '数学': '#E7FFE7',
    '英语': '#E7E7FF',
    '物理': '#FFFFE7',
    '化学': '#FFE7FF',
    '生物': '#E7FFFF',
    '政治': '#F5E7FF',
    '历史': '#FFE7F5',
    '地理': '#E7FFF5'
  }
  return colors[subject] || '#FFFFFF'
}

const getCellStyle = ({ row, column }) => {
  if (column.property === 'period') {
    return {
      backgroundColor: '#f5f7fa',
      fontWeight: 'bold',
      fontSize: '13px'
    }
  }
  
  const subject = row[column.property]
  if (!subject) return {}
  
  const dayMap = {
    'monday': 1,
    'tuesday': 2,
    'wednesday': 3,
    'thursday': 4,
    'friday': 5
  }
  
  const currentDayNumber = currentDay.value || 7  // 如果是周日(0)，设为7
  const cellDayNumber = dayMap[column.property]
  const periodIndex = tableData.value.findIndex(r => r.period === row.period)
  const currentPeriod = getCurrentPeriod()

  // console.log('Cell info:', {
  //   day: column.property,
  //   currentDay: currentDayNumber,
  //   cellDay: cellDayNumber,
  //   periodIndex,
  //   currentPeriod
  // }) // 调试日志
  
  // 基础样式
  const baseStyle = {
    fontSize: '14px',
    transition: 'all 0.3s',
    padding: '12px'
  }

  // 判断课程状态
  // 1. 已结束的课程
  if (
    cellDayNumber < currentDayNumber || // 之前的天数
    (cellDayNumber === currentDayNumber && periodIndex < currentPeriod) // 当天已结束的课程
  ) {
    return {
      ...baseStyle,
      backgroundColor: '#f5f5f5',  // 灰色背景
      color: '#909399',  // 灰色文字
      opacity: 0.8
    }
  }
  
  // 2. 正在上课
  if (
    cellDayNumber === currentDayNumber && // 当天
    currentPeriod === periodIndex // 当前课节
  ) {
    return {
      ...baseStyle,
      backgroundColor: '#e1f3d8',  // 绿色背景
      color: '#67c23a',  // 绿色文字
      fontWeight: 'bold',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.12)'
    }
  }
  
  // 3. 未上课程（包括其他天的课程）
  return {
    ...baseStyle,
    backgroundColor: getSubjectColor(subject),
    color: '#333'
  }
}

const fetchSchedule = async () => {
  const classCode = getClassCode()
  if (!classCode) {
    ElMessage.error('请先选择班级')
    return
  }

  loading.value = true
  try {
    const response = await api.get(`/api/schedule/${classCode}`, {
      params: { _ts: Date.now() }
    })
    if (response.data && response.data.schedule) {
      schedule.value = response.data.schedule
    } else {
      schedule.value = null
      ElMessage.warning('暂无课程表数据')
    }
  } catch (error) {
    console.error('Error fetching schedule:', error)
    ElMessage.error('获取课程表失败')
    schedule.value = null
  } finally {
    loading.value = false
  }
}

const fetchPeriods = async () => {
  try {
    const response = await api.get('/api/periods', {
      params: { _ts: Date.now() }
    })
    periods.value = response.data.periods
  } catch (error) {
    ElMessage.error('获取课程时间表失败')
  }
}


const getClassCode = () => {
  const code = document.cookie.split('; ').find(row => row.startsWith('classCode='))
  return code ? code.split('=')[1] : null
}
</script>

<style scoped>
.schedule-container {
  width: 100%;
  overflow-x: auto;
}

.schedule-table {
  width: 100%;
  min-width: 800px;  /* 确保在小屏幕上可以水平滚动 */
}

.schedule-table :deep(.el-table__header) {
  background-color: var(--background-color);
}

.schedule-table :deep(.el-table__row) {
  transition: all 0.3s ease;
}

.schedule-table :deep(.el-table__row:hover) {
  background-color: var(--background-color);
}

.schedule-table :deep(.el-table__cell) {
  text-align: center;
  height: 50px;
  padding: 8px;
}

/* 响应式布局 */
@media (max-width: 992px) {
  .schedule-table :deep(.el-table__cell) {
    padding: 6px;
    font-size: 14px;
  }
}

@media (max-width: 768px) {
  .schedule-table :deep(.el-table__cell) {
    padding: 4px;
    font-size: 12px;
  }
}

@media (max-width: 576px) {
  .schedule-container {
    margin: 0 -0.5rem;  /* 抵消父容器的padding */
  }
  
  .schedule-table :deep(.el-table__cell) {
    padding: 2px;
    font-size: 12px;
  }
}

/* 加载状态和空状态 */
.loading-container,
.empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}
</style>
