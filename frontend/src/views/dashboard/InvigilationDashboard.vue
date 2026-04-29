<template>
  <div class="command-dashboard invigilation-theme">
    <header class="hero-band">
      <div>
        <span class="kicker">Invigilation Operations</span>
        <h1>监考驾驶舱</h1>
        <p>考试项目状态、安排完整度、通知成功率、教师监考负载分析和冲突预警一览。</p>
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

    <section class="chart-grid">
      <DashboardChart
        title="考试项目状态分布"
        eyebrow="PROJECT STATUS"
        :option="projectStatusOption"
        :empty="isEmpty(summary.charts?.project_status)"
      />
      <DashboardChart
        title="通知发送状态"
        eyebrow="NOTIFICATION STATUS"
        :option="notificationStatusOption"
        :empty="isEmpty(summary.charts?.notification_status)"
      />
      <DashboardChart
        title="教师监考负载 Top5"
        eyebrow="WORKLOAD TOP5"
        :option="teacherWorkloadOption"
        :empty="isEmpty(summary.charts?.teacher_workload_top5, 'invigilation_count')"
      />
    </section>

    <section class="alert-grid">
      <div class="panel-section">
        <div class="panel-header">
          <span>UNARRANGED ALERT</span>
          <h3>未安排场次</h3>
        </div>
        <div v-if="unarrangedSlots.length" class="alert-list">
          <div v-for="slot in unarrangedSlots" :key="slot.exam_date + slot.start_time + slot.room_name" class="alert-row warning">
            <div class="alert-date">{{ slot.exam_date }}</div>
            <div class="alert-info">
              <strong>{{ slot.project_name || '未知项目' }}</strong>
              <span>{{ slot.subject }} · {{ slot.room_name }}</span>
              <small>{{ slot.start_time }} - {{ slot.end_time }}</small>
            </div>
          </div>
        </div>
        <div v-else class="empty-strip">暂无未安排场次。</div>
      </div>

      <div class="panel-section">
        <div class="panel-header">
          <span>CONFLICT ALERT</span>
          <h3>教师时间冲突</h3>
        </div>
        <div v-if="conflictSlots.length" class="alert-list">
          <div v-for="slot in conflictSlots" :key="slot.teacher_name + slot.exam_date + slot.start_time" class="alert-row danger">
            <div class="alert-date">{{ slot.exam_date }}</div>
            <div class="alert-info">
              <strong>{{ slot.teacher_name }}</strong>
              <span>{{ slot.start_time }} 时段冲突</span>
              <small>{{ slot.subjects }}</small>
            </div>
          </div>
        </div>
        <div v-else class="empty-strip">暂无教师时间冲突。</div>
      </div>

      <div class="panel-section">
        <div class="panel-header">
          <span>NOTIFICATION FAILED</span>
          <h3>通知失败记录</h3>
        </div>
        <div v-if="notificationFailed.length" class="alert-list">
          <div v-for="log in notificationFailed" :key="log.teacher_name + log.sent_at" class="alert-row info">
            <div class="alert-info">
              <strong>{{ log.teacher_name }}</strong>
              <span>{{ log.project_name || '未知项目' }}</span>
              <small>{{ log.sent_status }} · {{ log.error_message || '无详情' }}</small>
            </div>
          </div>
        </div>
        <div v-else class="empty-strip">暂无通知失败记录。</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import { getInvigilationDashboardSummary } from '@/api/modules/dashboard'

const router = useRouter()
const summary = ref({ cards: [], charts: {}, tables: {} })
const accents = ['#fb7185', '#fbbf24', '#34d399', '#67e8f9', '#a78bfa', '#38bdf8']

const go = (route) => route && router.push(route)
const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0)

const unarrangedSlots = computed(() => summary.value.tables?.unarranged_slots || [])
const conflictSlots = computed(() => summary.value.tables?.conflict_slots || [])
const notificationFailed = computed(() => summary.value.tables?.notification_failed || [])

const projectStatusOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#fbbf24', '#67e8f9', '#34d399'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#cbd5e1' } },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '44%'],
    label: { color: '#e2e8f0', formatter: '{b}\n{c}' },
    itemStyle: { borderColor: '#07111f', borderWidth: 3 },
    data: summary.value.charts?.project_status || []
  }]
}))

const notificationStatusOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#34d399', '#fb7185', '#fbbf24', '#94a3b8'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#cbd5e1' } },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '44%'],
    label: { color: '#e2e8f0', formatter: '{b}\n{c}' },
    itemStyle: { borderColor: '#07111f', borderWidth: 3 },
    data: summary.value.charts?.notification_status || []
  }]
}))

const teacherWorkloadOption = computed(() => {
  const rows = [...(summary.value.charts?.teacher_workload_top5 || [])].reverse()
  return {
    backgroundColor: 'transparent',
    color: ['#a78bfa'],
    tooltip: { trigger: 'axis' },
    grid: { left: 96, right: 24, top: 24, bottom: 28 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
    },
    yAxis: {
      type: 'category',
      data: rows.map(item => item.teacher_name),
      axisLabel: { color: '#cbd5e1' },
      axisLine: { show: false }
    },
    series: [{
      type: 'bar',
      data: rows.map(item => item.invigilation_count),
      barWidth: 18,
      label: { show: true, position: 'right', color: '#e2e8f0' },
      itemStyle: { borderRadius: [0, 9, 9, 0] }
    }]
  }
})

const fetchSummary = async () => {
  const res = await getInvigilationDashboardSummary()
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
    radial-gradient(circle at 10% 8%, rgba(251, 113, 133, 0.18), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(251, 191, 36, 0.14), transparent 28%);
}

.hero-band {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 26px;
  margin-bottom: 18px;
  border: 1px solid rgba(251, 113, 133, 0.25);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(2, 6, 23, 0.72));
}

.kicker {
  color: #fbbf24;
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
  font-size: 28px;
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

.chart-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.alert-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 14px;
}

.panel-section {
  min-height: 240px;
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

.alert-list {
  display: grid;
  gap: 10px;
}

.alert-row {
  display: flex;
  gap: 14px;
  padding: 12px;
  border-radius: 6px;
}

.alert-row.warning {
  border: 1px solid rgba(251, 191, 36, 0.2);
  background: rgba(120, 53, 15, 0.22);
}

.alert-row.danger {
  border: 1px solid rgba(251, 113, 133, 0.2);
  background: rgba(127, 29, 29, 0.18);
}

.alert-row.info {
  border: 1px solid rgba(56, 189, 248, 0.2);
  background: rgba(30, 64, 175, 0.18);
}

.alert-date {
  min-width: 90px;
  color: #fbbf24;
  font-size: 14px;
}

.alert-info strong {
  display: block;
  color: #e2e8f0;
  margin-bottom: 4px;
}

.alert-info span {
  color: #94a3b8;
  font-size: 13px;
}

.alert-info small {
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

@media (max-width: 900px) {
  .hero-band {
    flex-direction: column;
    align-items: stretch;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 34px;
  }
}
</style>