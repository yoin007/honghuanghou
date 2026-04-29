<template>
  <div class="command-dashboard teaching-theme">
    <header class="hero-band">
      <div>
        <span class="kicker">Teaching Operations</span>
        <h1>教务驾驶舱</h1>
        <p>围绕课表、教师课时和班级规模做可视化分析，指定时间段内的教师课时 Top5 来自当前系统已加载课表。</p>
      </div>
      <el-form :inline="true" class="filter-console">
        <el-form-item label="开始">
          <el-date-picker v-model="filters.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束">
          <el-date-picker v-model="filters.end_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="fetchSummary">查询</el-button>
        </el-form-item>
      </el-form>
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
        title="指定时间段教师课时 Top5"
        eyebrow="WORKLOAD TOP5"
        :option="teacherWorkloadOption"
        :empty="isEmpty(summary.charts?.teacher_workload_top5, 'lesson_count')"
      />
      <DashboardChart
        title="班级学生规模 Top5"
        eyebrow="CLASS SIZE"
        :option="classSizeOption"
        :empty="isEmpty(summary.charts?.class_size_top5, 'student_count')"
      />
      <DashboardChart
        title="教务资源结构"
        eyebrow="RESOURCE MIX"
        :option="resourceMixOption"
        :empty="isEmpty(summary.charts?.resource_mix)"
      />

      <section class="coverage-panel">
        <div class="panel-header">
          <span>SCHEDULE COVERAGE</span>
          <h3>课表覆盖说明</h3>
        </div>
        <div class="coverage-number">
          <strong>{{ summary.covered_dates?.length || 0 }}</strong>
          <span>天有可统计课表</span>
        </div>
        <p>{{ summary.message || '暂无统计说明' }}</p>
        <div class="date-tags">
          <span v-for="date in summary.covered_dates" :key="date">{{ date }}</span>
        </div>
      </section>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import { getTeachingDashboardSummary } from '@/api/modules/dashboard'

const router = useRouter()
const today = new Date()
const nextWeek = new Date()
nextWeek.setDate(today.getDate() + 6)
const fmt = (d) => d.toISOString().slice(0, 10)

const filters = reactive({
  start_date: fmt(today),
  end_date: fmt(nextWeek)
})
const summary = ref({ cards: [], charts: {}, tables: {}, message: '', covered_dates: [] })
const loading = ref(false)
const accents = ['#38bdf8', '#fbbf24', '#34d399', '#f472b6']

const go = (route) => route && router.push(route)
const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0)

const teacherWorkloadOption = computed(() => {
  const rows = [...(summary.value.charts?.teacher_workload_top5 || [])].reverse()
  return {
    backgroundColor: 'transparent',
    color: ['#38bdf8'],
    tooltip: { trigger: 'axis' },
    grid: { left: 82, right: 24, top: 24, bottom: 28 },
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
      data: rows.map(item => item.lesson_count),
      barWidth: 18,
      label: { show: true, position: 'right', color: '#e2e8f0' },
      itemStyle: { borderRadius: [0, 9, 9, 0] }
    }]
  }
})

const classSizeOption = computed(() => {
  const rows = [...(summary.value.charts?.class_size_top5 || [])].reverse()
  return {
    backgroundColor: 'transparent',
    color: ['#fbbf24'],
    tooltip: { trigger: 'axis' },
    grid: { left: 96, right: 24, top: 24, bottom: 28 },
    xAxis: {
      type: 'value',
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
      data: rows.map(item => item.student_count),
      barWidth: 18,
      label: { show: true, position: 'right', color: '#e2e8f0' },
      itemStyle: { borderRadius: [0, 9, 9, 0] }
    }]
  }
})

const resourceMixOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#38bdf8', '#34d399', '#fbbf24'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#cbd5e1' } },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '44%'],
    label: { color: '#e2e8f0', formatter: '{b}\n{c}' },
    itemStyle: { borderColor: '#07111f', borderWidth: 3 },
    data: summary.value.charts?.resource_mix || []
  }]
}))

const fetchSummary = async () => {
  loading.value = true
  try {
    const res = await getTeachingDashboardSummary(filters)
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
    radial-gradient(circle at 92% 14%, rgba(251, 191, 36, 0.14), transparent 28%);
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

.filter-console {
  min-width: 480px;
  padding: 14px 14px 0;
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.74);
}

.filter-console :deep(.el-form-item__label) {
  color: #cbd5e1;
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

.coverage-panel {
  min-height: 320px;
  padding: 18px;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.26);
}

.panel-header h3 {
  margin: 4px 0 20px;
  color: #e5f6ff;
  font-size: 17px;
}

.coverage-number {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
}

.coverage-number strong {
  color: #f8fafc;
  font-size: 56px;
  line-height: 1;
}

.coverage-number span {
  color: #cbd5e1;
}

.date-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.date-tags span {
  padding: 6px 9px;
  color: #bfdbfe;
  border: 1px solid rgba(96, 165, 250, 0.28);
  border-radius: 999px;
  background: rgba(30, 64, 175, 0.2);
  font-size: 12px;
}

@media (max-width: 980px) {
  .hero-band {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-console {
    min-width: 0;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 34px;
  }
}
</style>
