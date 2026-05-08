<template>
  <DashboardLoadingState v-if="errorState === 'loading'" :metric-count="4" :chart-count="5" />
  <ErrorState v-else-if="errorState" :type="errorState" :show-retry="errorState === 'error'" @retry="fetchSummary" />
  <ForbiddenState v-else-if="forbidden" />
  <div v-else class="command-dashboard moral-theme">
    <DashboardHero
      kicker="Moral Intelligence"
      title="德育驾驶舱"
      description="以当前账号可见范围统计德育分、日常表现和风险学生，所有指标均来自后端权限裁剪后的真实数据。"
    >
      <div class="score-orb">
        <span>平均德育分</span>
        <strong>{{ avgScore }}</strong>
      </div>
      <DashboardTopNSelect v-model="topN" @change="fetchSummary" />
    </DashboardHero>

    <DashboardMetricGrid :cards="summary.cards" :accents="accents" @click="go" />

    <section class="chart-grid">
      <DashboardChart
        title="德育分数段分布"
        eyebrow="SCORE BAND"
        :option="scoreDistributionOption"
        :empty="isEmpty(summary.charts?.score_distribution)"
        emptyText="当前无德育分数分布数据"
      />
      <DashboardChart
        title="日常表现正负占比"
        eyebrow="EVENT MIX"
        :option="eventMixOption"
        :empty="isEmpty(summary.charts?.daily_event_mix)"
        emptyText="当前无日常表现记录"
      />
      <DashboardChart
        title="近 14 天日常记录趋势"
        eyebrow="14 DAY TREND"
        :option="dailyTrendOption"
        :empty="isEmpty(summary.charts?.daily_record_trend, 'count')"
        emptyText="近 14 天暂无日常记录数据"
      />
      <DashboardChart
        :title="`班级平均分 Top${effectiveTopN}`"
        :eyebrow="`CLASS TOP${effectiveTopN}`"
        :option="classRankOption"
        :empty="isEmpty(classScoreRows, 'avg_score')"
        emptyText="当前无班级德育分排行数据"
      />
      <DashboardChart
        title="请假人数班级分布"
        eyebrow="LEAVE BY CLASS"
        :option="leaveByClassOption"
        :empty="isEmpty(summary.charts?.leave_by_class)"
        emptyText="当前无请假数据"
      />
    </section>

    <DashboardPanelSection class="risk-panel" variant="danger" eyebrow="ATTENTION LIST" :title="`低分学生 Top${effectiveTopN}`">
      <div v-if="lowStudents.length" class="risk-list">
        <div v-for="student in lowStudents" :key="student.student_id" class="risk-row">
          <div>
            <strong>{{ student.name }}</strong>
            <span>{{ student.class_name }} · {{ student.student_id }}</span>
          </div>
          <b>{{ student.total_score }} 分</b>
        </div>
      </div>
      <DashboardEmptyStrip v-else text="当前可见范围内暂无 60 分以下学生。" />
    </DashboardPanelSection>

    <DashboardLeaveList
      :students="leaveStudents"
      mode="moral"
      eyebrow="ATTENDANCE RISK"
      title="当前请假学生"
      empty-text="当前可见范围内无请假学生，出勤正常。"
    />

    <DashboardInsights
      :insights="insights"
      eyebrow="MORAL INSIGHTS"
      title="德育运行态势"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import DashboardEmptyStrip from '@/components/dashboard/DashboardEmptyStrip.vue'
import DashboardInsights from '@/components/dashboard/DashboardInsights.vue'
import DashboardLeaveList from '@/components/dashboard/DashboardLeaveList.vue'
import DashboardLoadingState from '@/components/dashboard/DashboardLoadingState.vue'
import ErrorState from '@/components/dashboard/ErrorState.vue'
import ForbiddenState from '@/components/dashboard/ForbiddenState.vue'
import DashboardHero from '@/components/dashboard/DashboardHero.vue'
import DashboardMetricGrid from '@/components/dashboard/DashboardMetricGrid.vue'
import DashboardPanelSection from '@/components/dashboard/DashboardPanelSection.vue'
import DashboardTopNSelect from '@/components/dashboard/DashboardTopNSelect.vue'
import { getMoralDashboardSummary } from '@/api/modules/dashboard'
import { basePieOption, baseHorizontalBarOption, baseLineOption, baseVerticalBarOption } from '@/utils/charting'
import { useDashboardRequest } from '@/composables/useDashboardRequest'

const router = useRouter()
const summary = ref({ cards: [], charts: {}, tables: {} })
const topN = ref(5)
const { loading, errorState, forbidden, execute } = useDashboardRequest()
const accents = ['#22d3ee', '#a3e635', '#f59e0b', '#fb7185']
const chartColors = ['#22d3ee', '#84cc16', '#f59e0b', '#fb7185', '#818cf8']

const go = (route) => route && router.push(route)

const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0)

const avgScore = computed(() => {
  const card = summary.value.cards?.find(item => item.label === '平均德育分')
  return card ? `${card.value}` : '-'
})

const lowStudents = computed(() => summary.value.tables?.low_students || [])
const leaveStudents = computed(() => summary.value.tables?.leave_students || [])
const insights = computed(() => summary.value.insights || [])
const effectiveTopN = computed(() => summary.value.top_n || topN.value)
const classScoreRows = computed(() => summary.value.charts?.class_score_rank || [])

const scoreDistributionOption = computed(() => baseVerticalBarOption({
  xAxisData: (summary.value.charts?.score_distribution || []).map(item => item.name),
  seriesData: (summary.value.charts?.score_distribution || []).map(item => item.value),
  tooltipTrigger: 'item',
  color: chartColors,
  itemStyle: {
    borderRadius: [8, 8, 0, 0],
    color: params => chartColors[params.dataIndex % chartColors.length]
  }
}))

const eventMixOption = computed(() => basePieOption({
  color: ['#22d3ee', '#fb7185'],
  radius: ['46%', '70%'],
  data: summary.value.charts?.daily_event_mix || []
}))

const dailyTrendOption = computed(() => baseLineOption({
  xAxisData: (summary.value.charts?.daily_record_trend || []).map(item => item.date?.slice(5)),
  seriesData: (summary.value.charts?.daily_record_trend || []).map(item => item.count),
  areaStyle: { color: 'rgba(34, 211, 238, 0.16)' },
  color: ['#67e8f9']
}))

const classRankOption = computed(() => {
  const rows = [...classScoreRows.value].reverse()
  return baseHorizontalBarOption({
    yAxisData: rows.map(item => item.class_name),
    seriesData: rows.map(item => item.avg_score),
    grid: { left: 88, right: 24, top: 22, bottom: 28 },
    barWidth: 16,
    borderRadius: [0, 8, 8, 0],
    color: ['#a3e635']
  })
})

const leaveByClassOption = computed(() => {
  const rows = [...(summary.value.charts?.leave_by_class || [])].reverse()
  return baseHorizontalBarOption({
    yAxisData: rows.map(item => item.name),
    seriesData: rows.map(item => item.value),
    grid: { left: 88, right: 24, top: 22, bottom: 28 },
    barWidth: 16,
    borderRadius: [0, 8, 8, 0],
    color: ['#fb7185']
  })
})

const fetchSummary = () => execute(
  () => getMoralDashboardSummary({ top_n: topN.value }),
  data => { summary.value = data }
)

onMounted(fetchSummary)
</script>

<style scoped>
.command-dashboard {
  --dashboard-chart-columns-desktop: repeat(2, minmax(0, 1fr));

  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 9% 8%, rgba(34, 211, 238, 0.2), transparent 28%),
    radial-gradient(circle at 91% 14%, rgba(244, 114, 182, 0.13), transparent 28%);
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

</style>
