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
      <button class="shortcut-entry" type="button" @click="go('/homework')">
        <span>发布作业</span>
        <el-icon><EditPen /></el-icon>
      </button>
      <button class="shortcut-entry" type="button" @click="go('/moral/daily-record')">
        <span>日常记录</span>
        <el-icon><Document /></el-icon>
      </button>
      <button class="shortcut-entry" type="button" @click="go('/moral/moment-record')">
        <span>点滴记录</span>
        <el-icon><ChatDotSquare /></el-icon>
      </button>
      <button class="shortcut-entry" type="button" @click="go('/invigilation')">
        <span>监考安排</span>
        <el-icon><Calendar /></el-icon>
      </button>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { EditPen, Document, ChatDotSquare, Calendar } from '@element-plus/icons-vue'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import { getTeacherWorkbench } from '@/api/modules/dashboard'

const router = useRouter()
const summary = ref({ cards: [], tables: {} })
const accents = ['#38bdf8', '#fbbf24', '#67e8f9', '#fb7185', '#a78bfa']

const go = (route) => route && router.push(route)

const todayLessons = computed(() => summary.value.tables?.today_lessons || [])
const invigilationTasks = computed(() => summary.value.tables?.invigilation_tasks || [])

const fetchSummary = async () => {
  const res = await getTeacherWorkbench()
  if (res.success) summary.value = res.data
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

@media (max-width: 900px) {
  .hero-band {
    flex-direction: column;
    align-items: stretch;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 34px;
  }
}
</style>