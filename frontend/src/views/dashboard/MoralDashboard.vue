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

    <DashboardInsights
      :insights="insights"
      eyebrow="MORAL INSIGHTS"
      title="德育运行态势"
    />

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
      <div class="class-score-chart-wrapper">
        <DashboardChart
          title="班级得分对比"
          eyebrow="CLASS SCORES"
          :option="classRankOption"
          :empty="isEmpty(classScoreRows, 'avg_score')"
          emptyText="当前无班级德育分数据"
        />
        <div class="score-legend">
          <span class="legend-item excellent">80+优秀</span>
          <span class="legend-item good">70-79良好</span>
          <span class="legend-item pass">60-69及格</span>
          <span class="legend-item fail">&lt;60不及格</span>
        </div>
      </div>
      <DashboardChart
        title="请假人数班级分布"
        eyebrow="LEAVE BY CLASS"
        :option="leaveByClassOption"
        :empty="isEmpty(summary.charts?.leave_by_class)"
        emptyText="当前无请假数据"
      />
      <DashboardChart
        :title="`教师德育记录分布 Top${effectiveTopN}`"
        eyebrow="TEACHER RECORDS"
        :option="teacherRecordOption"
        :empty="isEmpty(summary.charts?.teacher_record_distribution)"
        emptyText="当前无教师德育记录数据"
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
const topN = ref(50) // 默认50，获取全部班级对比
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
  // 按班级名称排序：高一1班 < 高一2班 < 高二1班...
  const rows = [...classScoreRows.value].sort((a, b) => {
    // 提取年级和班级号进行排序
    const parseClass = (name) => {
      const gradeMatch = name.match(/高?([一二三])/)
      const numMatch = name.match(/(\d+)班/)
      const gradeOrder = { '一': 1, '二': 2, '三': 3 }
      return {
        grade: gradeOrder[gradeMatch?.[1]] || 0,
        num: parseInt(numMatch?.[1]) || 0
      }
    }
    const aInfo = parseClass(a.class_name)
    const bInfo = parseClass(b.class_name)
    return aInfo.grade * 100 + aInfo.num - (bInfo.grade * 100 + bInfo.num)
  })

  // 根据分数段分配颜色：80+绿, 70-79蓝, 60-69黄, <60红
  const getColor = (score) => {
    if (score >= 80) return '#22c55e'  // 优秀-绿色
    if (score >= 70) return '#3b82f6'  // 良好-蓝色
    if (score >= 60) return '#f59e0b'  // 及格-黄色
    return '#ef4444'  // 不及格-红色
  }
  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const d = params[0]
        return `${d.name}<br/>平均分: ${d.value}<br/>学生数: ${rows[d.dataIndex]?.student_count || '-'}`
      }
    },
    grid: { left: 24, right: 24, top: 32, bottom: 48 },
    xAxis: {
      type: 'category',
      data: rows.map(item => item.class_name),
      axisLabel: { rotate: 30, fontSize: 11 },
      axisTick: { alignWithLabel: true }
    },
    yAxis: {
      type: 'value',
      name: '平均分',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { type: 'dashed', color: 'rgba(148,163,184,0.3)' } }
    },
    series: [{
      type: 'bar',
      data: rows.map(item => ({
        value: item.avg_score,
        itemStyle: {
          color: getColor(item.avg_score),
          borderRadius: [6, 6, 0, 0]
        }
      })),
      barWidth: 24,
      label: {
        show: true,
        position: 'top',
        formatter: '{c}',
        fontSize: 10,
        color: '#94a3b8'
      }
    }],
    // 分数段参考线
    markLine: {
      silent: true,
      data: [
        { yAxis: 80, lineStyle: { color: '#22c55e', type: 'dashed' }, label: { formatter: '优秀线' } },
        { yAxis: 70, lineStyle: { color: '#3b82f6', type: 'dashed' }, label: { formatter: '良好线' } },
        { yAxis: 60, lineStyle: { color: '#f59e0b', type: 'dashed' }, label: { formatter: '及格线' } }
      ]
    }
  }
})

const leaveByClassOption = computed(() => {
  const rows = [...(summary.value.charts?.leave_by_class || [])]
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 24, top: 32, bottom: 48 },
    xAxis: {
      type: 'category',
      data: rows.map(item => item.name),
      axisLabel: { color: '#94a3b8', rotate: 30, fontSize: 11 },
      axisLine: { lineStyle: { color: '#334155' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b' },
      splitLine: { lineStyle: { color: 'rgba(148,163,184,0.3)' } }
    },
    series: [{
      type: 'bar',
      data: rows.map(item => item.value),
      barWidth: 20,
      itemStyle: { borderRadius: [8, 8, 0, 0], color: '#fb7185' }
    }]
  }
})

// 教师德育记录分布图表（使用topN参数）
const teacherRecordOption = computed(() => {
  const rows = [...(summary.value.charts?.teacher_record_distribution || [])].sort((a, b) => b.value - a.value)
  return baseHorizontalBarOption({
    yAxisData: rows.map(item => item.name),
    seriesData: rows.map(item => item.value),
    grid: { left: 88, right: 24, top: 22, bottom: 28 },
    barWidth: 16,
    borderRadius: [0, 8, 8, 0],
    color: ['#22d3ee']
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

.class-score-chart-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.score-legend {
  display: flex;
  gap: 16px;
  padding: 8px 20px;
  background: rgba(30, 41, 59, 0.5);
  border-radius: 6px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #94a3b8;
}

.legend-item::before {
  content: '';
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.legend-item.excellent::before { background: #22c55e; }
.legend-item.good::before { background: #3b82f6; }
.legend-item.pass::before { background: #f59e0b; }
.legend-item.fail::before { background: #ef4444; }
</style>
