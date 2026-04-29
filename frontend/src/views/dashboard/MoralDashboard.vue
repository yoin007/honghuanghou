<template>
  <div class="command-dashboard moral-theme">
    <header class="hero-band">
      <div>
        <span class="kicker">Moral Intelligence</span>
        <h1>德育驾驶舱</h1>
        <p>以当前账号可见范围统计德育分、日常表现和风险学生，所有指标均来自后端权限裁剪后的真实数据。</p>
      </div>
      <div class="score-orb">
        <span>平均德育分</span>
        <strong>{{ avgScore }}</strong>
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
        title="德育分数段分布"
        eyebrow="SCORE BAND"
        :option="scoreDistributionOption"
        :empty="isEmpty(summary.charts?.score_distribution)"
      />
      <DashboardChart
        title="日常表现正负占比"
        eyebrow="EVENT MIX"
        :option="eventMixOption"
        :empty="isEmpty(summary.charts?.daily_event_mix)"
      />
      <DashboardChart
        title="近 14 天日常记录趋势"
        eyebrow="14 DAY TREND"
        :option="dailyTrendOption"
        :empty="isEmpty(summary.charts?.daily_record_trend, 'count')"
      />
      <DashboardChart
        title="班级平均分 Top5"
        eyebrow="CLASS RANK"
        :option="classRankOption"
        :empty="isEmpty(summary.charts?.class_score_top5, 'avg_score')"
      />
    </section>

    <section class="risk-panel">
      <div class="panel-header">
        <span>ATTENTION LIST</span>
        <h3>低分学生 Top5</h3>
      </div>
      <div v-if="lowStudents.length" class="risk-list">
        <div v-for="student in lowStudents" :key="student.student_id" class="risk-row">
          <div>
            <strong>{{ student.name }}</strong>
            <span>{{ student.class_name }} · {{ student.student_id }}</span>
          </div>
          <b>{{ student.total_score }} 分</b>
        </div>
      </div>
      <div v-else class="empty-strip">当前可见范围内暂无 60 分以下学生。</div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import { getMoralDashboardSummary } from '@/api/modules/dashboard'

const router = useRouter()
const summary = ref({ cards: [], charts: {}, tables: {} })
const accents = ['#22d3ee', '#a3e635', '#f59e0b', '#fb7185']
const chartColors = ['#22d3ee', '#84cc16', '#f59e0b', '#fb7185', '#818cf8']

const go = (route) => route && router.push(route)

const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0)

const avgScore = computed(() => {
  const card = summary.value.cards?.find(item => item.label === '平均德育分')
  return card ? `${card.value}` : '-'
})

const lowStudents = computed(() => summary.value.tables?.low_students || [])

const scoreDistributionOption = computed(() => ({
  backgroundColor: 'transparent',
  color: chartColors,
  tooltip: { trigger: 'item' },
  grid: { left: 36, right: 20, top: 28, bottom: 28 },
  xAxis: {
    type: 'category',
    data: (summary.value.charts?.score_distribution || []).map(item => item.name),
    axisLabel: { color: '#cbd5e1' },
    axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.35)' } }
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#94a3b8' },
    splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
  },
  series: [{
    type: 'bar',
    barWidth: 24,
    data: (summary.value.charts?.score_distribution || []).map(item => item.value),
    itemStyle: {
      borderRadius: [8, 8, 0, 0],
      color: params => chartColors[params.dataIndex % chartColors.length]
    }
  }]
}))

const eventMixOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#22d3ee', '#fb7185'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#cbd5e1' } },
  series: [{
    type: 'pie',
    radius: ['46%', '70%'],
    center: ['50%', '44%'],
    label: { color: '#e2e8f0', formatter: '{b}\n{c}' },
    itemStyle: { borderColor: '#07111f', borderWidth: 3 },
    data: summary.value.charts?.daily_event_mix || []
  }]
}))

const dailyTrendOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#67e8f9'],
  tooltip: { trigger: 'axis' },
  grid: { left: 38, right: 20, top: 28, bottom: 32 },
  xAxis: {
    type: 'category',
    data: (summary.value.charts?.daily_record_trend || []).map(item => item.date?.slice(5)),
    axisLabel: { color: '#cbd5e1' },
    axisLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.35)' } }
  },
  yAxis: {
    type: 'value',
    axisLabel: { color: '#94a3b8' },
    splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
  },
  series: [{
    type: 'line',
    smooth: true,
    symbolSize: 7,
    areaStyle: { color: 'rgba(34, 211, 238, 0.16)' },
    lineStyle: { width: 3 },
    data: (summary.value.charts?.daily_record_trend || []).map(item => item.count)
  }]
}))

const classRankOption = computed(() => {
  const rows = [...(summary.value.charts?.class_score_top5 || [])].reverse()
  return {
    backgroundColor: 'transparent',
    color: ['#a3e635'],
    tooltip: { trigger: 'axis' },
    grid: { left: 88, right: 24, top: 22, bottom: 28 },
    xAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
    },
    yAxis: {
      type: 'category',
      data: rows.map(item => item.class_name),
      axisLabel: { color: '#cbd5e1' },
      axisLine: { show: false }
    },
    series: [{
      type: 'bar',
      data: rows.map(item => item.avg_score),
      barWidth: 16,
      label: { show: true, position: 'right', color: '#e2e8f0' },
      itemStyle: { borderRadius: [0, 8, 8, 0] }
    }]
  }
})

const fetchSummary = async () => {
  const res = await getMoralDashboardSummary()
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
    radial-gradient(circle at 9% 8%, rgba(34, 211, 238, 0.2), transparent 28%),
    radial-gradient(circle at 91% 14%, rgba(244, 114, 182, 0.13), transparent 28%);
}

.hero-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 26px;
  margin-bottom: 18px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(2, 6, 23, 0.72));
}

.kicker,
.panel-header span {
  color: #67e8f9;
  font-size: 12px;
}

h1 {
  margin: 8px 0;
  color: #f8fafc;
  font-size: 40px;
  line-height: 1.08;
  letter-spacing: 0;
}

p {
  max-width: 720px;
  margin: 0;
  color: rgba(226, 232, 240, 0.72);
}

.score-orb {
  display: grid;
  width: 150px;
  height: 150px;
  place-items: center;
  text-align: center;
  border: 1px solid rgba(34, 211, 238, 0.42);
  border-radius: 999px;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.24), rgba(15, 23, 42, 0.82) 68%);
  box-shadow: 0 0 44px rgba(34, 211, 238, 0.22);
}

.score-orb span {
  align-self: end;
  color: #94a3b8;
  font-size: 12px;
}

.score-orb strong {
  align-self: start;
  color: #f8fafc;
  font-size: 34px;
}

.metric-grid,
.chart-grid {
  display: grid;
  gap: 14px;
  margin-bottom: 18px;
}

.metric-grid {
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
}

.chart-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.metric-card {
  position: relative;
  min-height: 112px;
  padding: 18px;
  color: #e2e8f0;
  text-align: left;
  cursor: pointer;
  border: 1px solid color-mix(in srgb, var(--accent), transparent 62%);
  border-radius: 8px;
  background: linear-gradient(155deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.62));
  overflow: hidden;
}

.metric-card span,
.metric-card strong {
  position: relative;
  z-index: 1;
}

.metric-card span {
  color: #94a3b8;
}

.metric-card strong {
  display: block;
  margin-top: 16px;
  color: #f8fafc;
  font-size: 32px;
  line-height: 1;
}

.metric-card small {
  margin-left: 5px;
  color: #cbd5e1;
  font-size: 14px;
}

.metric-card i {
  position: absolute;
  right: -34px;
  bottom: -38px;
  width: 110px;
  height: 110px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent), transparent 74%);
  filter: blur(8px);
}

.risk-panel {
  padding: 18px;
  border: 1px solid rgba(251, 113, 133, 0.28);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(48, 18, 35, 0.82), rgba(7, 15, 30, 0.9));
}

.panel-header h3 {
  margin: 4px 0 14px;
  color: #e5f6ff;
  font-size: 17px;
}

.risk-list {
  display: grid;
  gap: 10px;
}

.risk-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 13px 14px;
  border: 1px solid rgba(251, 113, 133, 0.2);
  border-radius: 8px;
  background: rgba(127, 29, 29, 0.2);
}

.risk-row strong,
.risk-row b {
  color: #fecdd3;
}

.risk-row span {
  display: block;
  margin-top: 4px;
  color: rgba(226, 232, 240, 0.66);
  font-size: 13px;
}

.empty-strip {
  padding: 18px;
  color: rgba(226, 232, 240, 0.66);
  border: 1px dashed rgba(148, 163, 184, 0.25);
  border-radius: 8px;
  text-align: center;
}

@media (max-width: 900px) {
  .hero-band {
    flex-direction: column;
    align-items: flex-start;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 34px;
  }
}
</style>
