<template>
  <div class="command-dashboard system-theme">
    <header class="hero-band">
      <div>
        <span class="kicker">System Operations</span>
        <h1>系统运维驾驶舱</h1>
        <p>数据库状态、用户权限、API 权限风险和操作审计一览，系统管理员专属视图。</p>
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
        title="角色分布"
        eyebrow="ROLE DISTRIBUTION"
        :option="roleDistributionOption"
        :empty="isEmpty(summary.charts?.role_distribution, 'count')"
      />
      <DashboardChart
        title="教师身份分布"
        eyebrow="IDENTITY MIX"
        :option="identityMixOption"
        :empty="isEmpty(summary.charts?.teacher_identity)"
      />
      <DashboardChart
        title="操作类型统计"
        eyebrow="OPERATION STATS"
        :option="operationStatsOption"
        :empty="isEmpty(summary.charts?.operation_stats, 'count')"
      />
    </section>

    <section class="info-grid">
      <div class="panel-section">
        <div class="panel-header">
          <span>DATABASE FILES</span>
          <h3>数据库文件</h3>
        </div>
        <div v-if="dbFiles.length" class="db-list">
          <div v-for="db in dbFiles" :key="db.name" class="db-row">
            <strong>{{ db.name }}</strong>
            <span>{{ db.exists ? `${db.size_kb} KB` : '不存在' }}</span>
            <small>{{ db.exists ? `${db.tables?.length || 0} 表` : '-' }}</small>
          </div>
        </div>
        <div v-else class="empty-strip">暂无数据库统计。</div>
      </div>

      <div class="panel-section">
        <div class="panel-header">
          <span>API PERMISSION RISKS</span>
          <h3>权限风险项</h3>
        </div>
        <div v-if="apiRisks.length" class="risk-list">
          <div v-for="risk in apiRisks" :key="risk.api_path" class="risk-row">
            <strong>{{ risk.api_path }}</strong>
            <span>{{ risk.policy_mode }}</span>
            <small>{{ risk.allowed_roles }}</small>
          </div>
        </div>
        <div v-else class="empty-strip success">无权限风险项。</div>
      </div>

      <div class="panel-section">
        <div class="panel-header">
          <span>RECENT OPERATIONS</span>
          <h3>最近敏感操作</h3>
        </div>
        <div v-if="recentOps.length" class="ops-list">
          <div v-for="op in recentOps" :key="op.operated_at + op.record_id" class="ops-row">
            <div class="ops-type">{{ op.operation_type }}</div>
            <div class="ops-info">
              <strong>{{ op.table_name }} #{{ op.record_id }}</strong>
              <span>{{ op.operator }} · {{ op.operated_at }}</span>
            </div>
          </div>
        </div>
        <div v-else class="empty-strip">暂无敏感操作记录。</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import { getSystemDashboardSummary } from '@/api/modules/dashboard'

const router = useRouter()
const summary = ref({ cards: [], charts: {}, tables: {} })
const accents = ['#a78bfa', '#38bdf8', '#34d399', '#fbbf24', '#fb7185', '#f472b6']

const go = (route) => route && router.push(route)
const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0)

const dbFiles = computed(() => summary.value.tables?.db_files || [])
const apiRisks = computed(() => summary.value.tables?.api_permission_risks || [])
const recentOps = computed(() => summary.value.tables?.recent_operations || [])

const roleDistributionOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#a78bfa', '#38bdf8', '#34d399', '#fbbf24'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#cbd5e1' } },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '44%'],
    label: { color: '#e2e8f0', formatter: '{b}\n{c}' },
    itemStyle: { borderColor: '#07111f', borderWidth: 3 },
    data: (summary.value.charts?.role_distribution || []).map(item => ({
      name: item.role,
      value: item.count
    }))
  }]
}))

const identityMixOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#38bdf8', '#a78bfa', '#94a3b8'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#cbd5e1' } },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '44%'],
    label: { color: '#e2e8f0', formatter: '{b}\n{c}' },
    itemStyle: { borderColor: '#07111f', borderWidth: 3 },
    data: summary.value.charts?.teacher_identity || []
  }]
}))

const operationStatsOption = computed(() => {
  const rows = [...(summary.value.charts?.operation_stats || [])].reverse()
  return {
    backgroundColor: 'transparent',
    color: ['#34d399'],
    tooltip: { trigger: 'axis' },
    grid: { left: 72, right: 24, top: 24, bottom: 28 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: 'rgba(148, 163, 184, 0.12)' } }
    },
    yAxis: {
      type: 'category',
      data: rows.map(item => item.type),
      axisLabel: { color: '#cbd5e1' },
      axisLine: { show: false }
    },
    series: [{
      type: 'bar',
      data: rows.map(item => item.count),
      barWidth: 18,
      label: { show: true, position: 'right', color: '#e2e8f0' },
      itemStyle: { borderRadius: [0, 9, 9, 0] }
    }]
  }
})

const fetchSummary = async () => {
  const res = await getSystemDashboardSummary()
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
    radial-gradient(circle at 10% 8%, rgba(167, 139, 250, 0.18), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(56, 189, 248, 0.14), transparent 28%);
}

.hero-band {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 26px;
  margin-bottom: 18px;
  border: 1px solid rgba(167, 139, 250, 0.25);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(2, 6, 23, 0.72));
}

.kicker {
  color: #a78bfa;
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
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.metric-card {
  position: relative;
  min-height: 100px;
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
  font-size: 26px;
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

.info-grid {
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

.empty-strip {
  padding: 18px;
  color: rgba(226, 232, 240, 0.66);
  border: 1px dashed rgba(148, 163, 184, 0.25);
  border-radius: 6px;
  text-align: center;
}

.empty-strip.success {
  color: #34d399;
  border-color: rgba(52, 211, 153, 0.3);
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