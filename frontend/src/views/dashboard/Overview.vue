<template>
  <DashboardLoadingState v-if="errorState === 'loading'" :metric-count="5" :chart-count="1" />
  <ErrorState v-else-if="errorState" :type="errorState" :show-retry="errorState === 'error'" @retry="fetchOverview" />
  <ForbiddenState v-else-if="forbidden" />
  <div v-else class="command-dashboard">
    <DashboardHero
      kicker="Campus Operations"
      title="数据驾驶舱"
      description="聚合当前账号可见的数据范围，呈现校园运行态势、风险提示和业务入口。"
    >
      <DashboardTimeChip label="数据更新时间" :value="overview.updated_at" />
    </DashboardHero>

    <DashboardMetricGrid :cards="overview.cards" :accents="accents" @click="go" />

    <section class="visual-grid">
      <DashboardChart
        title="系统资源结构"
        eyebrow="LIVE MIX"
        :option="resourceOption"
        :empty="overview.cards.length === 0"
        emptyText="暂无系统资源数据"
      />

      <div class="radar-panel">
        <DashboardPanelHeader eyebrow="ALERT STREAM" title="风险提示" />
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
import DashboardLoadingState from '@/components/dashboard/DashboardLoadingState.vue'
import ErrorState from '@/components/dashboard/ErrorState.vue'
import ForbiddenState from '@/components/dashboard/ForbiddenState.vue'
import DashboardHero from '@/components/dashboard/DashboardHero.vue'
import DashboardMetricGrid from '@/components/dashboard/DashboardMetricGrid.vue'
import DashboardPanelHeader from '@/components/dashboard/DashboardPanelHeader.vue'
import DashboardTimeChip from '@/components/dashboard/DashboardTimeChip.vue'
import { getDashboardOverview } from '@/api/modules/dashboard'
import { basePieOption } from '@/utils/charting'
import { useDashboardRequest } from '@/composables/useDashboardRequest'

const router = useRouter()
const overview = ref({ cards: [], modules: [], alerts: [] })
const { loading, errorState, forbidden, execute } = useDashboardRequest()
const accents = ['#22d3ee', '#a3e635', '#f59e0b', '#f472b6', '#818cf8']

const go = (route) => {
  if (route) router.push(route)
}

const resourceOption = computed(() => {
  const data = (overview.value.cards || []).map(card => ({
    name: card.label,
    value: Number(card.value) || 0
  }))
  return basePieOption({
    color: accents,
    radius: ['45%', '70%'],
    center: ['50%', '45%'],
    data
  })
})

const fetchOverview = () => execute(
  () => getDashboardOverview(),
  data => { overview.value = data }
)

onMounted(fetchOverview)
</script>

<style scoped>
.command-dashboard {
  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 8% 12%, rgba(34, 211, 238, 0.2), transparent 28%),
    radial-gradient(circle at 92% 10%, rgba(163, 230, 53, 0.13), transparent 26%);
}

p {
  max-width: 680px;
  margin: 0;
  color: rgba(226, 232, 240, 0.72);
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

</style>
