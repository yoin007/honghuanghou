<template>
  <div class="command-dashboard teacher-theme">
    <header class="hero-band">
      <div>
        <span class="kicker">Teacher Workbench</span>
        <h1>教师工作台</h1>
        <p>聚合今日课程、发布内容、德育参与和监考任务，一目了然掌握个人工作状态。</p>
      </div>
      <div class="time-chip">
        <span>数据更新</span>
        <strong>{{ summary.updated_at || '-' }}</strong>
      </div>
    </header>

    <section class="metric-grid">
      <button
        v-for="(card, index) in summary.cards"
        :key="card.label"
        class="metric-card"
        :style="{ '--accent': accents[index % accents.length] }"
        type="button"
        @click="go(card.route)"
      >
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}<small>{{ card.unit }}</small></strong>
        <i></i>
      </button>
    </section>

    <section class="info-grid">
      <div class="info-section">
        <div class="panel-header">
          <span>TODAY SCHEDULE</span>
          <h3>今日课程</h3>
        </div>
        <div v-if="todayLessons.length" class="lesson-list">
          <div v-for="(lesson, idx) in todayLessons" :key="idx" class="lesson-item">
            <div class="lesson-time">{{ lesson.time }}</div>
            <div class="lesson-info">
              <strong>{{ lesson.class_name }}</strong>
              <span>{{ lesson.subject }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-strip">今日暂无课程安排。</div>
      </div>

      <div class="info-section">
        <div class="panel-header">
          <span>INVIGILATION</span>
          <h3>监考任务</h3>
        </div>
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
        <div v-else class="empty-strip">暂无监考任务安排。</div>
      </div>
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

    <section class="workload-section">
      <div class="workload-header">
        <div class="workload-title">
          <span class="kicker">PERSONAL WORKLOAD</span>
          <h2>我的区间课时</h2>
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
        <div class="panel-header">
          <span>WORKLOAD SCHEDULE</span>
          <h3>课时明细</h3>
        </div>
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
        <div v-else class="empty-strip">当前区间暂无课时明细。</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { EditPen, Document, ChatDotSquare, Upload } from '@element-plus/icons-vue'
import { getTeacherWorkbench } from '@/api/modules/dashboard'

const router = useRouter()
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
const loading = ref(false)
const accents = ['#38bdf8', '#fbbf24', '#67e8f9', '#fb7185', '#a78bfa']

const go = (route) => route && router.push(route)

const todayLessons = computed(() => summary.value.tables?.today_lessons || [])
const invigilationTasks = computed(() => summary.value.tables?.invigilation_tasks || [])
const workloadLessons = computed(() => summary.value.workload?.lessons || summary.value.tables?.workload_lessons || [])
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

const fetchSummary = async () => {
  loading.value = true
  try {
    const res = await getTeacherWorkbench(filters)
    if (res.success) summary.value = res.data
  } finally {
    loading.value = false
  }
}

onMounted(fetchSummary)
</script>

<style scoped>
.command-dashboard {
  min-height: calc(100vh - 80px);
  padding: 24px;
  color: #e2e8f0;
  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 10% 8%, rgba(56, 189, 248, 0.2), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(251, 191, 36, 0.14), transparent 28%);
}

.hero-band {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 26px;
  margin-bottom: 18px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(2, 6, 23, 0.72));
}

.kicker {
  color: #67e8f9;
  font-size: 12px;
}

h1 {
  margin: 8px 0;
  color: #f8fafc;
  font-size: 40px;
  line-height: 1.08;
}

p {
  max-width: 720px;
  margin: 0;
  color: rgba(226, 232, 240, 0.72);
}

.time-chip {
  min-width: 180px;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
}

.time-chip span {
  display: block;
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.time-chip strong {
  color: #f8fafc;
  font-size: 16px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.metric-card {
  position: relative;
  min-height: 108px;
  padding: 16px;
  color: #e2e8f0;
  text-align: left;
  cursor: pointer;
  border: 1px solid color-mix(in srgb, var(--accent), transparent 62%);
  border-radius: 8px;
  background: linear-gradient(155deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.62));
  overflow: hidden;
}

.metric-card span {
  color: #94a3b8;
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin-top: 12px;
  color: #f8fafc;
  font-size: 30px;
  line-height: 1;
}

.metric-card small {
  margin-left: 4px;
  color: #cbd5e1;
  font-size: 13px;
}

.metric-card i {
  position: absolute;
  right: -30px;
  bottom: -34px;
  width: 90px;
  height: 90px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent), transparent 74%);
  filter: blur(8px);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.info-section {
  min-height: 280px;
  padding: 18px;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
}

.panel-header span {
  color: #67e8f9;
  font-size: 12px;
}

.panel-header h3 {
  margin: 4px 0 14px;
  color: #e5f6ff;
  font-size: 16px;
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

.empty-strip {
  padding: 18px;
  color: rgba(226, 232, 240, 0.66);
  border: 1px dashed rgba(148, 163, 184, 0.25);
  border-radius: 6px;
  text-align: center;
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

@media (max-width: 900px) {
  .hero-band {
    flex-direction: column;
    align-items: stretch;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

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

  h1 {
    font-size: 34px;
  }
}
</style>
