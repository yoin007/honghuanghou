<template>
  <div class="command-dashboard">
    <header class="hero-band">
      <div>
        <span class="kicker">Campus Operations</span>
        <h1>数据驾驶舱</h1>
        <p>聚合当前账号可见的数据范围，呈现校园运行态势、风险提示和业务入口。</p>
      </div>
      <div class="time-chip">
        <span>数据更新时间</span>
        <strong>{{ overview.updated_at || '-' }}</strong>
      </div>
    </header>

    <section class="metric-grid">
      <button
        v-for="(card, index) in overview.cards"
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

    <section class="visual-grid">
      <DashboardChart
        title="系统资源结构"
        eyebrow="LIVE MIX"
        :option="resourceOption"
        :empty="overview.cards.length === 0"
      />

      <div class="radar-panel">
        <div class="panel-header">
          <span>ALERT STREAM</span>
          <h3>风险提示</h3>
        </div>
        <div v-if="overview.alerts?.length" class="alert-list">
          <button
            v-for="alert in overview.alerts"
            :key="alert.title"
            class="alert-item"
            type="button"
            @click="go(alert.route)"
          >
            <strong>{{ alert.title }}</strong>
            <span>{{ alert.message }}</span>
          </button>
        </div>
        <div v-else class="quiet-state">
          <strong>运行平稳</strong>
          <span>当前可见范围内暂无需要突出处理的预警。</span>
        </div>
      </div>
    </section>

    <section class="module-grid">
      <button
        v-for="module in overview.modules"
        :key="module.route"
        class="module-entry"
        type="button"
        @click="go(module.route)"
      >
        <span>{{ module.title }}</span>
        <el-icon><ArrowRight /></el-icon>
      </button>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import { getDashboardOverview } from '@/api/modules/dashboard'

const router = useRouter()
const overview = ref({ cards: [], modules: [], alerts: [] })
const accents = ['#22d3ee', '#a3e635', '#f59e0b', '#f472b6', '#818cf8']

const go = (route) => {
  if (route) router.push(route)
}

const resourceOption = computed(() => {
  const data = (overview.value.cards || []).map(card => ({
    name: card.label,
    value: Number(card.value) || 0
  }))
  return {
    backgroundColor: 'transparent',
    color: accents,
    tooltip: { trigger: 'item' },
    legend: {
      bottom: 0,
      textStyle: { color: '#cbd5e1' }
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderColor: '#07111f',
          borderWidth: 3
        },
        label: {
          color: '#e2e8f0',
          formatter: '{b}\n{c}'
        },
        data
      }
    ]
  }
})

const fetchOverview = async () => {
  const res = await getDashboardOverview()
  if (res.success) overview.value = res.data
}

onMounted(fetchOverview)
</script>

<style scoped>
.command-dashboard {
  min-height: calc(100vh - 80px);
  padding: 24px;
  color: #e2e8f0;
  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 8% 12%, rgba(34, 211, 238, 0.2), transparent 28%),
    radial-gradient(circle at 92% 10%, rgba(163, 230, 53, 0.13), transparent 26%);
}

.hero-band {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  min-height: 190px;
  padding: 26px;
  margin-bottom: 18px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 8px;
  background:
    linear-gradient(120deg, rgba(14, 165, 233, 0.16), transparent 42%),
    linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(2, 6, 23, 0.72));
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.32);
}

.kicker,
.panel-header span {
  color: #67e8f9;
  font-size: 12px;
}

h1 {
  margin: 8px 0 8px;
  color: #f8fafc;
  font-size: 42px;
  line-height: 1.08;
  letter-spacing: 0;
}

p {
  max-width: 680px;
  margin: 0;
  color: rgba(226, 232, 240, 0.72);
}

.time-chip {
  min-width: 210px;
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
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.metric-card {
  position: relative;
  min-height: 118px;
  padding: 18px;
  color: #e2e8f0;
  text-align: left;
  cursor: pointer;
  border: 1px solid color-mix(in srgb, var(--accent), transparent 62%);
  border-radius: 8px;
  background: linear-gradient(155deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.62));
  box-shadow: 0 0 28px color-mix(in srgb, var(--accent), transparent 84%);
  overflow: hidden;
}

.metric-card span {
  position: relative;
  z-index: 1;
  color: #94a3b8;
}

.metric-card strong {
  position: relative;
  z-index: 1;
  display: block;
  margin-top: 16px;
  color: #f8fafc;
  font-size: 34px;
  line-height: 1;
}

.metric-card small {
  margin-left: 5px;
  color: #cbd5e1;
  font-size: 14px;
  font-weight: 500;
}

.metric-card i {
  position: absolute;
  right: -32px;
  bottom: -36px;
  width: 112px;
  height: 112px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent), transparent 72%);
  filter: blur(8px);
}

.visual-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 16px;
  margin-bottom: 18px;
}

.radar-panel,
.module-entry {
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.26);
}

.radar-panel {
  min-height: 320px;
  padding: 18px;
}

.panel-header h3 {
  margin: 4px 0 14px;
  color: #e5f6ff;
  font-size: 17px;
}

.alert-list {
  display: grid;
  gap: 10px;
}

.alert-item,
.module-entry {
  width: 100%;
  color: #e2e8f0;
  text-align: left;
  cursor: pointer;
}

.alert-item {
  padding: 13px;
  border: 1px solid rgba(251, 191, 36, 0.26);
  border-radius: 8px;
  background: rgba(120, 53, 15, 0.22);
}

.alert-item strong,
.quiet-state strong {
  display: block;
  color: #fde68a;
}

.alert-item span,
.quiet-state span {
  display: block;
  margin-top: 6px;
  color: rgba(226, 232, 240, 0.72);
  font-size: 13px;
}

.quiet-state {
  display: grid;
  min-height: 210px;
  place-content: center;
  text-align: center;
  border: 1px dashed rgba(148, 163, 184, 0.25);
  border-radius: 8px;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px;
}

.module-entry {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px;
  font-weight: 700;
}

@media (max-width: 900px) {
  .hero-band,
  .visual-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
    align-items: stretch;
  }

  h1 {
    font-size: 34px;
  }
}
</style>
