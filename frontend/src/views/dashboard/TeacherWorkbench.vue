<template>
  <DashboardLoadingState v-if="errorState === 'loading'" :metric-count="5" :chart-count="0" />
  <ErrorState v-else-if="errorState" :type="errorState" :show-retry="errorState === 'error'" @retry="fetchSummary" />
  <ForbiddenState v-else-if="forbidden" />
  <div v-else class="command-dashboard teacher-theme">
    <DashboardHero
      kicker="Teacher Workbench"
      :title="selectedTeacherName ? `${selectedTeacherName}的工作台` : '教师工作台'"
      description="聚合今日课程、发布内容、德育参与和监考任务，一目了然掌握个人工作状态。"
    >
      <div v-if="_isManager" class="filter-console">
        <el-select v-model="selectedTeacherName" placeholder="选择教师" clearable filterable @change="onTeacherChange">
          <el-option v-for="t in teacherList" :key="t.username" :label="t.username" :value="t.username" />
        </el-select>
      </div>
      <DashboardTimeChip :value="summary.updated_at" />
    </DashboardHero>

    <DashboardMetricGrid :cards="summary.cards" :accents="accents" @click="go" />

    <section class="info-grid">
      <DashboardPanelSection eyebrow="TODAY SCHEDULE" title="今日课程" :min-height="280">
        <div v-if="todayLessons.length" class="lesson-list">
          <div v-for="(lesson, idx) in todayLessons" :key="idx" class="lesson-item">
            <div class="lesson-time">{{ lesson.time }}</div>
            <div class="lesson-info">
              <strong>{{ lesson.class_name }}</strong>
              <span>{{ lesson.subject }}</span>
            </div>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="今日暂无课程安排。" />
      </DashboardPanelSection>

      <DashboardPanelSection eyebrow="UPCOMING TODOS" title="即将待办" :min-height="280" class="todo-panel">
        <div v-if="upcomingTodos.length" class="todo-list-mini">
          <div v-for="todo in upcomingTodos" :key="todo.occurrence_id || todo.series_id" class="todo-item-mini" @click="go('/teacher/todo')">
            <div class="todo-date-mini">{{ todo.occurrence_date }}</div>
            <div class="todo-info-mini">
              <strong>{{ todo.title }}</strong>
              <span v-if="todo.todo_type !== 'one_off'" class="todo-type-tag">{{ todoTypeLabel(todo.todo_type) }}</span>
            </div>
            <el-button link type="primary" size="small">查看</el-button>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="暂无即将到期的待办事项。" />
      </DashboardPanelSection>
    </section>

    <section class="shortcut-grid">
      <button class="shortcut-entry" type="button" @click="go('/publish-homework')">
        <span>发布作业</span>
        <el-icon><EditPen /></el-icon>
      </button>
      <button class="shortcut-entry" type="button" @click="go('/moral/daily-record')">
        <span>日常记录</span>
        <el-icon><Document /></el-icon>
      </button>
      <button class="shortcut-entry" type="button" @click="go('/moral/moment')">
        <span>点滴记录</span>
        <el-icon><ChatDotSquare /></el-icon>
      </button>
      <button class="shortcut-entry" type="button" @click="go('/file-upload')">
        <span>文件打印</span>
        <el-icon><Upload /></el-icon>
      </button>
    </section>

    <!-- 教师德育记录趋势图 -->
    <section class="trend-section">
      <div class="trend-header">
        <div class="trend-title">
          <span class="kicker">MORAL RECORDS TREND</span>
          <h2>{{ selectedTeacherName ? `${selectedTeacherName}的德育记录趋势` : '我的德育记录趋势' }}</h2>
        </div>
        <div class="trend-controls">
          <el-radio-group v-model="trendUnit" size="small" @change="onTrendUnitChange">
            <el-radio-button label="week">按周</el-radio-button>
            <el-radio-button label="month">按月</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <div v-if="teacherTrendOption" class="trend-chart-wrapper">
        <DashboardChart
          title=""
          :option="teacherTrendOption"
          :empty="!teacherTrendData.periods?.length"
          emptyText="暂无德育记录趋势数据"
          :loading="trendLoading"
        />
      </div>
      <DashboardEmptyStrip v-else text="暂无德育记录趋势数据。" />
    </section>

    <section class="workload-section">
      <div class="workload-header">
        <div class="workload-title">
          <span class="kicker">PERSONAL WORKLOAD</span>
          <h2>{{ selectedTeacherName ? `${selectedTeacherName}的区间课时` : '我的区间课时' }}</h2>
        </div>
        <div class="workload-filter">
          <el-date-picker v-model="filters.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
          <span class="filter-sep">至</span>
          <el-date-picker v-model="filters.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
          <el-button type="primary" :loading="loading" @click="fetchSummary">查询</el-button>
        </div>
      </div>

      <div class="workload-summary">
        <div class="workload-stat">
          <div class="stat-orb">
            <strong>{{ summary.workload?.lesson_count || 0 }}</strong>
            <span>节课</span>
          </div>
          <div class="stat-desc">
            <p>{{ workloadText }}</p>
            <small>{{ summary.workload?.message || '按当前周课表统计' }}</small>
          </div>
        </div>
        <div class="workload-meta-row">
          <div class="meta-item">
            <span>覆盖日期</span>
            <strong>{{ summary.workload?.covered_dates?.length || 0 }} 天</strong>
          </div>
          <div class="meta-item">
            <span>涉及班级</span>
            <strong>{{ uniqueClasses.length }} 个</strong>
          </div>
          <div class="meta-item">
            <span>日均课时</span>
            <strong>{{ avgDaily }} 节</strong>
          </div>
        </div>
      </div>

      <div class="workload-detail">
        <DashboardPanelHeader eyebrow="WORKLOAD SCHEDULE" title="课时明细" />
        <div v-if="workloadLessons.length" class="workload-table">
          <div class="table-header">
            <span>日期</span>
            <span>星期</span>
            <span>班级</span>
            <span>学科</span>
            <span>节次</span>
            <span>时段</span>
          </div>
          <div v-for="lesson in workloadLessons" :key="`${lesson.date}-${lesson.period_order}-${lesson.class_name}`" class="table-row">
            <span class="col-date">{{ lesson.date }}</span>
            <span class="col-weekday">星期{{ weekdayText[lesson.weekday] || lesson.weekday }}</span>
            <span class="col-class">{{ lesson.class_name }}</span>
            <span class="col-subject">{{ lesson.subject }}</span>
            <span class="col-period">{{ lesson.period }}</span>
            <span class="col-time">{{ lesson.time_range }}</span>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="当前区间暂无课时明细。" />
      </div>
    </section>

    <!-- 监考任务区块 -->
    <section class="invigilation-section">
      <DashboardPanelHeader eyebrow="INVIGILATION DUTY" title="监考任务" />
      <div v-if="invigilationTasks.length" class="invigilation-list">
        <div v-for="task in invigilationTasks" :key="task.exam_date + task.start_time" class="invigilation-item">
          <div class="invigilation-date">{{ task.exam_date }}</div>
          <div class="invigilation-info">
            <strong>{{ task.project_name }}</strong>
            <span>{{ task.grade_name }} · {{ task.subject }} · {{ task.room_name }}</span>
            <small>{{ task.start_time }} - {{ task.end_time }}</small>
          </div>
        </div>
      </div>
      <DashboardEmptyStrip v-else text="暂无监考任务安排。" />
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { EditPen, Document, ChatDotSquare, Upload } from '@element-plus/icons-vue'
import DashboardEmptyStrip from '@/components/dashboard/DashboardEmptyStrip.vue'
import DashboardLoadingState from '@/components/dashboard/DashboardLoadingState.vue'
import ErrorState from '@/components/dashboard/ErrorState.vue'
import ForbiddenState from '@/components/dashboard/ForbiddenState.vue'
import DashboardHero from '@/components/dashboard/DashboardHero.vue'
import DashboardMetricGrid from '@/components/dashboard/DashboardMetricGrid.vue'
import DashboardPanelHeader from '@/components/dashboard/DashboardPanelHeader.vue'
import DashboardTimeChip from '@/components/dashboard/DashboardTimeChip.vue'
import DashboardPanelSection from '@/components/dashboard/DashboardPanelSection.vue'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import { getTeacherWorkbench, getTeacherRecordTrend } from '@/api/modules/dashboard'
import { getUpcomingTodos } from '@/api/modules/teacherTodo'
import { teacherApi } from '@/api/modules/teacher'
import { useAuthStore } from '@/stores/auth'
import { useDashboardRequest } from '@/composables/useDashboardRequest'
import { buildAdaptiveValueAxis } from '@/utils/charting'

const router = useRouter()
const authStore = useAuthStore()
const today = new Date()
const weekStart = new Date(today)
weekStart.setDate(today.getDate() - ((today.getDay() + 6) % 7))
const weekEnd = new Date(weekStart)
weekEnd.setDate(weekStart.getDate() + 6)
const fmt = (d) => {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const filters = reactive({
  start_date: fmt(weekStart),
  end_date: fmt(weekEnd)
})
const summary = ref({ cards: [], tables: {}, workload: {}, range: {} })
const trendUnit = ref('week')
const teacherTrendData = ref({ periods: [], labels: [], daily_count: [], moment_count: [], total_count: [] })
const trendLoading = ref(false)
const teacherList = ref([])
const selectedTeacherName = ref(null)
const { loading, errorState, forbidden, execute } = useDashboardRequest()
const accents = ['#38bdf8', '#fbbf24', '#67e8f9', '#fb7185', '#a78bfa']

const go = (route) => route && router.push(route)

// 管理员/年级主任可切换教师
const _isManager = computed(() => {
  return authStore.isAdmin || authStore.isXuefa || authStore.isJiaowu || authStore.roles?.includes('g_leader')
})

// 教师选择变化
const onTeacherChange = (newTeacher) => {
  if (newTeacher) {
    selectedTeacherName.value = newTeacher
  } else {
    selectedTeacherName.value = null
  }
  fetchSummary()
  fetchTeacherTrend()
}

// 获取教师列表
const fetchTeacherList = async () => {
  if (!_isManager.value) return
  try {
    const res = await teacherApi.getTeachers()
    // 后端返回格式：{ teachers: [...], total: N }
    teacherList.value = res.teachers || res.data?.teachers || []
  } catch (e) {
    console.error('获取教师列表失败:', e)
  }
}

const todayLessons = computed(() => summary.value.tables?.today_lessons || [])
const invigilationTasks = computed(() => summary.value.tables?.invigilation_tasks || [])
const upcomingTodos = ref([])
const workloadLessons = computed(() => summary.value.tables?.workload_lessons || [])
const weekdayText = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '日' }
const workloadText = computed(() => {
  const range = summary.value.range || filters
  return `${range.start_date || filters.start_date} 至 ${range.end_date || filters.end_date}`
})
const uniqueClasses = computed(() => {
  const classes = new Set()
  workloadLessons.value.forEach(l => classes.add(l.class_name))
  return Array.from(classes)
})
const avgDaily = computed(() => {
  const days = summary.value.workload?.covered_dates?.length || 1
  const total = summary.value.workload?.lesson_count || 0
  return days > 0 ? Math.round(total / days * 10) / 10 : 0
})

const teacherTrendOption = computed(() => {
  const data = teacherTrendData.value
  if (!data.periods?.length) return null
  const counts = [data.daily_count, data.moment_count, data.total_count]
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['日常记录', '点滴记录', '总计'], top: 10 },
    xAxis: { type: 'category', data: data.labels },
    yAxis: buildAdaptiveValueAxis(counts, {
      name: '记录数',
      hardMin: 0,
      includeZero: true,
      integer: true,
      minRange: 3
    }),
    series: [
      { name: '日常记录', type: 'line', data: data.daily_count, smooth: true, itemStyle: { color: '#67e8f9' } },
      { name: '点滴记录', type: 'line', data: data.moment_count, smooth: true, itemStyle: { color: '#fbbf24' } },
      { name: '总计', type: 'line', data: data.total_count, smooth: true, itemStyle: { color: '#a78bfa' } }
    ]
  }
})

const fetchTeacherTrend = async () => {
  trendLoading.value = true
  try {
    const params = { unit: trendUnit.value }
    if (selectedTeacherName.value) {
      params.teacher_name = selectedTeacherName.value
    }
    const res = await getTeacherRecordTrend(params)
    if (res.success) {
      teacherTrendData.value = res.data.trend
    }
  } catch (e) {
    console.error('获取教师记录趋势失败:', e)
  } finally {
    trendLoading.value = false
  }
}

const onTrendUnitChange = () => {
  fetchTeacherTrend()
}

const todoTypeLabel = (type) => {
  const labels = { one_off: '一次性', weekly: '每周', monthly: '每月', yearly: '每年' }
  return labels[type] || type
}

const fetchUpcomingTodos = async () => {
  try {
    const res = await getUpcomingTodos({ days: 7, limit: 5 })
    if (res.success) {
      upcomingTodos.value = res.data.todos || []
    }
  } catch (e) {
    // 静默失败
  }
}

const fetchSummary = () => {
  const params = { ...filters }
  if (selectedTeacherName.value) {
    params.teacher_name = selectedTeacherName.value
  }
  execute(
    () => getTeacherWorkbench(params),
    data => { summary.value = data }
  )
}

onMounted(() => {
  fetchTeacherList()
  fetchSummary()
  fetchTeacherTrend()
  fetchUpcomingTodos()
})
</script>

<style scoped>
.command-dashboard {
  --dashboard-info-columns-desktop: repeat(2, minmax(0, 1fr));

  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 10% 8%, rgba(56, 189, 248, 0.2), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(251, 191, 36, 0.14), transparent 28%);
}

.filter-console {
  min-width: 200px;
  margin-right: 16px;
}

.filter-console :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.74);
  border-color: rgba(56, 189, 248, 0.3);
}

.filter-console :deep(.el-input__inner) {
  color: #e2e8f0;
}

.kicker {
  color: #67e8f9;
  font-size: 12px;
}

p {
  max-width: 720px;
  margin: 0;
  color: rgba(226, 232, 240, 0.72);
}

.lesson-list,
.invigilation-list {
  display: grid;
  gap: 10px;
}

.lesson-item,
.invigilation-item {
  display: flex;
  gap: 14px;
  padding: 12px;
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 6px;
  background: rgba(30, 64, 175, 0.18);
}

.lesson-time,
.invigilation-date {
  min-width: 80px;
  color: #bfdbfe;
  font-size: 14px;
}

.invigilation-date {
  color: #fbbf24;
}

.lesson-info strong,
.invigilation-info strong {
  display: block;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.lesson-info span,
.invigilation-info span {
  color: #94a3b8;
  font-size: 13px;
}

.invigilation-info small {
  display: block;
  margin-top: 6px;
  color: #67e8f9;
  font-size: 12px;
}

/* 待办区块样式 */
.todo-panel {
  --panel-border: rgba(251, 191, 36, 0.3);
}

.todo-list-mini {
  display: grid;
  gap: 10px;
}

.todo-item-mini {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border: 1px solid rgba(251, 191, 36, 0.25);
  border-radius: 6px;
  background: rgba(180, 83, 9, 0.15);
  cursor: pointer;
  transition: background 0.2s;
}

.todo-item-mini:hover {
  background: rgba(180, 83, 9, 0.25);
}

.todo-date-mini {
  min-width: 90px;
  color: #fbbf24;
  font-size: 14px;
}

.todo-info-mini strong {
  display: block;
  color: #fef3c7;
}

.todo-info-mini span {
  color: #94a3b8;
  font-size: 13px;
}

.todo-type-tag {
  display: inline-block;
  padding: 2px 6px;
  margin-left: 8px;
  border-radius: 4px;
  background: rgba(251, 191, 36, 0.2);
  color: #fbbf24;
  font-size: 11px;
}

.shortcut-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}

.shortcut-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  color: #e2e8f0;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
}

.shortcut-entry .el-icon {
  color: #67e8f9;
}

/* 区间课时区块 - 底部 */
.workload-section {
  padding: 20px;
  border: 1px solid rgba(251, 191, 36, 0.28);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(71, 42, 10, 0.35), rgba(7, 15, 30, 0.92)),
    radial-gradient(circle at 8% 10%, rgba(251, 191, 36, 0.16), transparent 40%);
}

.workload-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(251, 191, 36, 0.18);
}

.workload-title h2 {
  margin: 6px 0;
  color: #f8fafc;
  font-size: 24px;
}

.workload-filter {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-sep {
  color: #94a3b8;
  font-size: 13px;
}

.workload-summary {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: 20px;
  margin-bottom: 18px;
}

.workload-stat {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-orb {
  display: grid;
  width: 100px;
  height: 100px;
  place-items: center;
  text-align: center;
  border: 2px solid rgba(251, 191, 36, 0.5);
  border-radius: 999px;
  background: radial-gradient(circle, rgba(251, 191, 36, 0.25), rgba(15, 23, 42, 0.88) 70%);
}

.stat-orb strong {
  align-self: end;
  color: #fef3c7;
  font-size: 32px;
  line-height: 1;
}

.stat-orb span {
  align-self: start;
  margin-top: 4px;
  color: #fde68a;
  font-size: 13px;
}

.stat-desc p {
  color: #e2e8f0;
  font-size: 15px;
  margin: 0;
}

.stat-desc small {
  color: #94a3b8;
  font-size: 12px;
}

.workload-meta-row {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: grid;
  gap: 4px;
  padding: 12px 16px;
  border: 1px solid rgba(251, 191, 36, 0.2);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.5);
}

.meta-item span {
  color: #94a3b8;
  font-size: 12px;
}

.meta-item strong {
  color: #fbbf24;
  font-size: 18px;
}

.workload-detail {
  padding: 18px;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
}

.workload-table {
  display: grid;
  gap: 8px;
}

.table-header,
.table-row {
  display: grid;
  grid-template-columns: 110px 80px minmax(0, 1fr) 100px 80px 120px;
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
}

.table-header {
  color: #67e8f9;
  font-size: 12px;
  font-weight: 500;
  border-bottom: 1px solid rgba(99, 179, 237, 0.3);
}

.table-row {
  border: 1px solid rgba(56, 189, 248, 0.15);
  border-radius: 4px;
  background: rgba(30, 64, 175, 0.12);
}

.table-row span {
  color: #e2e8f0;
  font-size: 13px;
}

.col-date {
  color: #bfdbfe;
}

.col-weekday {
  color: #94a3b8;
}

.col-subject {
  color: #a78bfa;
}

/* 趋势图区块 */
.trend-section {
  margin-top: 24px;
  padding: 20px;
  border: 1px solid rgba(167, 139, 250, 0.28);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9)),
    radial-gradient(circle at 8% 10%, rgba(167, 139, 250, 0.16), transparent 40%);
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  margin-bottom: 18px;
}

.trend-title h2 {
  margin: 6px 0;
  color: #f8fafc;
  font-size: 20px;
}

.trend-controls :deep(.el-radio-button__inner) {
  background: rgba(15, 23, 42, 0.74);
  border-color: rgba(167, 139, 250, 0.3);
}

.trend-controls :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #a78bfa;
  border-color: #a78bfa;
}

.trend-chart-wrapper {
  height: 220px;
}

/* 监考任务区块 - 底部 */
.invigilation-section {
  padding: 20px;
  border: 1px solid rgba(34, 211, 238, 0.28);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9)),
    radial-gradient(circle at 8% 10%, rgba(34, 211, 238, 0.16), transparent 40%);
}

.invigilation-section .invigilation-list {
  display: grid;
  gap: 10px;
}

.invigilation-section .invigilation-item {
  display: flex;
  gap: 14px;
  padding: 12px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  border-radius: 6px;
  background: rgba(30, 64, 175, 0.18);
}

.invigilation-section .invigilation-date {
  min-width: 80px;
  color: #bfdbfe;
  font-size: 14px;
}

.invigilation-section .invigilation-info strong {
  display: block;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.invigilation-section .invigilation-info span {
  color: #94a3b8;
  font-size: 13px;
}

.invigilation-section .invigilation-info small {
  display: block;
  margin-top: 6px;
  color: #67e8f9;
  font-size: 12px;
}

@media (max-width: 900px) {
  .workload-header {
    flex-direction: column;
    align-items: stretch;
  }

  .workload-summary {
    grid-template-columns: 1fr;
  }

  .workload-meta-row {
    flex-wrap: wrap;
  }

  .table-header,
  .table-row {
    grid-template-columns: 1fr;
    gap: 4px;
  }

}
</style>
