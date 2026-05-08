<template>
  <DashboardLoadingState v-if="errorState === 'loading'" :metric-count="6" :chart-count="3" />
  <ErrorState v-else-if="errorState" :type="errorState" :show-retry="errorState === 'error'" @retry="fetchSummary" />
  <ForbiddenState v-else-if="forbidden" />
  <div v-else class="command-dashboard invigilation-theme">
    <DashboardHero
      kicker="Invigilation Operations"
      title="监考驾驶舱"
      description="考试项目状态、安排完整度、通知成功率、教师监考负载分析和冲突预警一览。"
    >
      <DashboardTimeChip :value="summary.updated_at" />
      <DashboardTopNSelect v-model="topN" @change="fetchSummary" />
    </DashboardHero>

    <DashboardMetricGrid :cards="summary.cards" :accents="accents" @click="go" />

    <section class="chart-grid">
      <DashboardChart
        title="考试项目状态分布"
        eyebrow="PROJECT STATUS"
        :option="projectStatusOption"
        :empty="isEmpty(summary.charts?.project_status)"
        emptyText="暂无考试项目数据"
      />
      <DashboardChart
        title="通知发送状态"
        eyebrow="NOTIFICATION STATUS"
        :option="notificationStatusOption"
        :empty="isEmpty(summary.charts?.notification_status)"
        emptyText="暂无通知记录"
      />
      <DashboardChart
        :title="`教师监考负载 Top${effectiveTopN}`"
        :eyebrow="`WORKLOAD TOP${effectiveTopN}`"
        :option="teacherWorkloadOption"
        :empty="isEmpty(teacherWorkloadRows, 'invigilation_count')"
        emptyText="暂无教师监考负载数据"
      />
    </section>

    <section class="alert-grid">
      <DashboardPanelSection eyebrow="UNARRANGED ALERT" title="未安排场次" :min-height="240">
        <DashboardAlertList :items="unarrangedSlots" variant="warning" empty-text="暂无未安排场次。">
          <template #default="{ item: slot }">
            <div class="alert-date">{{ slot.exam_date }}</div>
            <div class="alert-info">
              <strong>{{ slot.project_name || '未知项目' }}</strong>
              <span>{{ slot.subject }} · {{ slot.room_name }}</span>
              <small>{{ slot.start_time }} - {{ slot.end_time }}</small>
            </div>
          </template>
        </DashboardAlertList>
      </DashboardPanelSection>

      <DashboardPanelSection eyebrow="CONFLICT ALERT" title="教师时间冲突" :min-height="240">
        <DashboardAlertList :items="conflictSlots" variant="danger" empty-text="暂无教师时间冲突。">
          <template #default="{ item: slot }">
            <div class="alert-date">{{ slot.exam_date }}</div>
            <div class="alert-info">
              <strong>{{ slot.teacher_name }}</strong>
              <span>{{ slot.start_time }} 时段冲突</span>
              <small>{{ slot.subjects }}</small>
            </div>
          </template>
        </DashboardAlertList>
      </DashboardPanelSection>

      <DashboardPanelSection eyebrow="NOTIFICATION FAILED" title="通知失败记录" :min-height="240">
        <DashboardAlertList :items="notificationFailed" variant="info" empty-text="暂无通知失败记录。">
          <template #default="{ item: log }">
            <div class="alert-info">
              <strong>{{ log.teacher_name }}</strong>
              <span>{{ log.project_name || '未知项目' }}</span>
              <small>{{ log.sent_status }} · {{ log.error_message || '无详情' }}</small>
            </div>
          </template>
        </DashboardAlertList>
      </DashboardPanelSection>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import DashboardLoadingState from '@/components/dashboard/DashboardLoadingState.vue'
import ErrorState from '@/components/dashboard/ErrorState.vue'
import ForbiddenState from '@/components/dashboard/ForbiddenState.vue'
import DashboardHero from '@/components/dashboard/DashboardHero.vue'
import DashboardMetricGrid from '@/components/dashboard/DashboardMetricGrid.vue'
import DashboardTimeChip from '@/components/dashboard/DashboardTimeChip.vue'
import DashboardTopNSelect from '@/components/dashboard/DashboardTopNSelect.vue'
import DashboardPanelSection from '@/components/dashboard/DashboardPanelSection.vue'
import DashboardAlertList from '@/components/dashboard/DashboardAlertList.vue'
import { getInvigilationDashboardSummary } from '@/api/modules/dashboard'
import { basePieOption, baseHorizontalBarOption } from '@/utils/charting'
import { useDashboardRequest } from '@/composables/useDashboardRequest'

const router = useRouter()
const summary = ref({ cards: [], charts: {}, tables: {} })
const topN = ref(5)
const { loading, errorState, forbidden, execute } = useDashboardRequest()
const accents = ['#fb7185', '#fbbf24', '#34d399', '#67e8f9', '#a78bfa', '#38bdf8']

const go = (route) => route && router.push(route)
const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0)

const unarrangedSlots = computed(() => summary.value.tables?.unarranged_slots || [])
const conflictSlots = computed(() => summary.value.tables?.conflict_slots || [])
const notificationFailed = computed(() => summary.value.tables?.notification_failed || [])
const effectiveTopN = computed(() => summary.value.top_n || topN.value)
const teacherWorkloadRows = computed(() => summary.value.charts?.teacher_workload_rank || [])

const projectStatusOption = computed(() => basePieOption({
  color: ['#fbbf24', '#67e8f9', '#34d399'],
  data: summary.value.charts?.project_status || []
}))

const notificationStatusOption = computed(() => basePieOption({
  color: ['#34d399', '#fb7185', '#fbbf24', '#94a3b8'],
  data: summary.value.charts?.notification_status || []
}))

const teacherWorkloadOption = computed(() => {
  const rows = [...teacherWorkloadRows.value].reverse()
  return baseHorizontalBarOption({
    yAxisData: rows.map(item => item.teacher_name),
    seriesData: rows.map(item => item.invigilation_count),
    grid: { left: 96, right: 24, top: 24, bottom: 28 },
    color: ['#a78bfa']
  })
})

const fetchSummary = () => execute(
  () => getInvigilationDashboardSummary({ top_n: topN.value }),
  data => { summary.value = data }
)

onMounted(fetchSummary)
</script>

<style scoped>
.command-dashboard {
  --dashboard-chart-columns-desktop: repeat(3, minmax(0, 1fr));

  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 10% 8%, rgba(251, 113, 133, 0.18), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(251, 191, 36, 0.14), transparent 28%);
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

</style>
