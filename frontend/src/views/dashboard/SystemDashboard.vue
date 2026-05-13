<template>
  <DashboardLoadingState v-if="errorState === 'loading'" :metric-count="6" :chart-count="3" />
  <ErrorState v-else-if="errorState" :type="errorState" :show-retry="errorState === 'error'" @retry="fetchSummary" />
  <ForbiddenState v-else-if="forbidden" />
  <div v-else class="command-dashboard system-theme">
    <DashboardHero
      kicker="System Operations"
      title="系统运维驾驶舱"
      description="数据库状态、用户权限、API 权限风险和操作审计一览，系统管理员专属视图。"
    >
      <DashboardTimeChip :value="summary.updated_at" />
    </DashboardHero>

    <DashboardMetricGrid :cards="summary.cards" :accents="accents" @click="go" />

    <section class="chart-grid">
      <DashboardChart
        title="角色分布"
        eyebrow="ROLE DISTRIBUTION"
        :option="roleDistributionOption"
        :empty="isEmpty(summary.charts?.role_distribution, 'count')"
        emptyText="暂无角色分布数据"
      />
      <DashboardChart
        title="教师身份分布"
        eyebrow="IDENTITY MIX"
        :option="identityMixOption"
        :empty="isEmpty(summary.charts?.teacher_identity)"
        emptyText="暂无教师身份数据"
      />
      <DashboardChart
        title="操作类型统计"
        eyebrow="OPERATION STATS"
        :option="operationStatsOption"
        :empty="isEmpty(summary.charts?.operation_stats, 'count')"
        emptyText="暂无操作统计数据"
      />
    </section>

    <section class="info-grid">
      <DashboardPanelSection eyebrow="DATABASE FILES" title="数据库文件" :min-height="240">
        <div v-if="dbFiles.length" class="db-list">
          <div v-for="db in dbFiles" :key="db.name" class="db-row">
            <strong>{{ db.name }}</strong>
            <span>{{ db.exists ? `${db.size_kb} KB` : '不存在' }}</span>
            <small>{{ db.exists ? `${db.tables?.length || 0} 表` : '-' }}</small>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="暂无数据库统计。" />
      </DashboardPanelSection>

      <DashboardPanelSection eyebrow="API PERMISSION RISKS" title="权限风险项" :min-height="240">
        <div v-if="apiRisks.length" class="risk-list">
          <div v-for="risk in apiRisks" :key="risk.api_path" class="risk-row">
            <strong>{{ risk.api_path }}</strong>
            <span>{{ risk.policy_mode }}</span>
            <small>{{ risk.allowed_roles }}</small>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="无权限风险项。" variant="success" />
      </DashboardPanelSection>

      <DashboardPanelSection eyebrow="RECENT OPERATIONS" title="最近敏感操作" :min-height="240">
        <div v-if="recentOps.length" class="ops-list">
          <div v-for="op in recentOps" :key="op.operated_at + op.record_id" class="ops-row">
            <div class="ops-type">{{ op.operation_type }}</div>
            <div class="ops-info">
              <strong>{{ op.table_name }} #{{ op.record_id }}</strong>
              <span>{{ op.operator }} · {{ op.operated_at }}</span>
            </div>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="暂无敏感操作记录。" />
      </DashboardPanelSection>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import DashboardEmptyStrip from '@/components/dashboard/DashboardEmptyStrip.vue'
import DashboardLoadingState from '@/components/dashboard/DashboardLoadingState.vue'
import ErrorState from '@/components/dashboard/ErrorState.vue'
import ForbiddenState from '@/components/dashboard/ForbiddenState.vue'
import DashboardHero from '@/components/dashboard/DashboardHero.vue'
import DashboardMetricGrid from '@/components/dashboard/DashboardMetricGrid.vue'
import DashboardTimeChip from '@/components/dashboard/DashboardTimeChip.vue'
import DashboardPanelSection from '@/components/dashboard/DashboardPanelSection.vue'
import { getSystemDashboardSummary } from '@/api/modules/dashboard'
import { basePieOption, baseHorizontalBarOption } from '@/utils/charting'
import { useDashboardRequest } from '@/composables/useDashboardRequest'

const router = useRouter()
const summary = ref({ cards: [], charts: {}, tables: {} })
const { loading, errorState, forbidden, execute } = useDashboardRequest()
const accents = ['#a78bfa', '#38bdf8', '#34d399', '#fbbf24', '#fb7185', '#f472b6']

const go = (route) => route && router.push(route)
const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0)

const dbFiles = computed(() => summary.value.tables?.db_files || [])
const apiRisks = computed(() => summary.value.tables?.api_permission_risks || [])
const recentOps = computed(() => summary.value.tables?.recent_operations || [])

const roleNames = {
    admin: '管理员',
    teacher: '教师',
    'teacher/cleader': '教师/班主任',
    'teacher/jiaowu': '教师/教务',
    'teacher/xuefa': '教师/学发',
    'teacher/g_leader': '教师/年级主任',
    'teacher/cleader/g_leader': '教师/班主任/年级主任',
    cleader: '班主任',
    jiaowu: '教务',
    xuefa: '学发',
    g_leader: '年级主任',
    member: '会员'
  }
  const roleDistributionOption = computed(() => basePieOption({
  color: ['#a78bfa', '#38bdf8', '#34d399', '#fbbf24'],
  data: (summary.value.charts?.role_distribution || []).map(item => ({
    name: roleNames[item.role] || item.role,
    value: item.count
  }))
}))

const identityMixOption = computed(() => basePieOption({
  color: ['#38bdf8', '#a78bfa', '#94a3b8'],
  data: summary.value.charts?.teacher_identity || []
}))

const operationStatsOption = computed(() => {
  const rows = [...(summary.value.charts?.operation_stats || [])].reverse()
  return baseHorizontalBarOption({
    yAxisData: rows.map(item => item.type),
    seriesData: rows.map(item => item.count),
    grid: { left: 72, right: 24, top: 24, bottom: 28 },
    color: ['#34d399']
  })
})

const fetchSummary = () => execute(
  () => getSystemDashboardSummary(),
  data => { summary.value = data }
)

onMounted(fetchSummary)
</script>

<style scoped>
.command-dashboard {
  --dashboard-chart-columns-desktop: repeat(3, minmax(0, 1fr));

  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 10% 8%, rgba(167, 139, 250, 0.18), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(56, 189, 248, 0.14), transparent 28%);
}

.db-list,
.risk-list,
.ops-list {
  display: grid;
  gap: 10px;
}

.db-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border: 1px solid rgba(56, 189, 248, 0.2);
  border-radius: 6px;
  background: rgba(30, 64, 175, 0.18);
}

.db-row strong {
  color: #e2e8f0;
}

.db-row span {
  color: #67e8f9;
  font-size: 13px;
}

.db-row small {
  color: #94a3b8;
  font-size: 12px;
}

.risk-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border: 1px solid rgba(251, 113, 133, 0.2);
  border-radius: 6px;
  background: rgba(127, 29, 29, 0.18);
}

.risk-row strong {
  color: #fecdd3;
  font-size: 13px;
}

.risk-row span {
  color: #fbbf24;
  font-size: 12px;
}

.risk-row small {
  color: #94a3b8;
  font-size: 12px;
}

.ops-row {
  display: flex;
  gap: 14px;
  padding: 12px;
  border: 1px solid rgba(167, 139, 250, 0.2);
  border-radius: 6px;
  background: rgba(88, 28, 135, 0.18);
}

.ops-type {
  min-width: 60px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(167, 139, 250, 0.3);
  color: #e9d5ff;
  font-size: 12px;
  text-align: center;
}

.ops-info strong {
  display: block;
  color: #e2e8f0;
  font-size: 13px;
}

.ops-info span {
  color: #94a3b8;
  font-size: 12px;
}

</style>
