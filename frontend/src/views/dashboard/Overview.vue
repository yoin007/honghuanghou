<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2>数据驾驶舱</h2>
      <span>{{ overview.updated_at || '-' }}</span>
    </div>

    <el-row :gutter="12">
      <el-col v-for="card in overview.cards" :key="card.label" :xs="12" :sm="8" :md="6">
        <button class="metric-card" type="button" @click="go(card.route)">
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}<small>{{ card.unit }}</small></strong>
        </button>
      </el-col>
    </el-row>

    <el-alert
      v-for="alert in overview.alerts"
      :key="alert.title"
      :title="alert.title"
      :description="alert.message"
      :type="alert.level || 'info'"
      show-icon
      class="dashboard-alert"
    />

    <div class="module-grid">
      <button v-for="module in overview.modules" :key="module.route" class="module-entry" type="button" @click="go(module.route)">
        <span>{{ module.title }}</span>
        <el-icon><ArrowRight /></el-icon>
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'
import { getDashboardOverview } from '@/api/modules/dashboard'

const router = useRouter()
const overview = ref({ cards: [], modules: [], alerts: [] })

const go = (route) => {
  if (route) router.push(route)
}

const fetchOverview = async () => {
  const res = await getDashboardOverview()
  if (res.success) overview.value = res.data
}

onMounted(fetchOverview)
</script>

<style scoped>
.dashboard-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.page-header h2 {
  margin: 0;
  font-size: 22px;
}

.page-header span {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.metric-card,
.module-entry {
  width: 100%;
  border: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
  border-radius: 6px;
  text-align: left;
  cursor: pointer;
}

.metric-card {
  min-height: 86px;
  padding: 14px;
  margin-bottom: 12px;
}

.metric-card span {
  color: var(--el-text-color-secondary);
}

.metric-card strong {
  display: block;
  margin-top: 10px;
  font-size: 26px;
}

.metric-card small {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 400;
}

.dashboard-alert {
  margin: 8px 0;
}

.module-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.module-entry {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  font-weight: 600;
}
</style>
