<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2>教务驾驶舱</h2>
      <span>{{ summary.updated_at || '-' }}</span>
    </div>

    <el-form :inline="true" class="filter-bar">
      <el-form-item label="开始日期">
        <el-date-picker v-model="filters.start_date" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="filters.end_date" type="date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchSummary">查询</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="12">
      <el-col v-for="card in summary.cards" :key="card.label" :xs="12" :sm="8" :md="6">
        <button class="metric-card" type="button" @click="go(card.route)">
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}<small>{{ card.unit }}</small></strong>
        </button>
      </el-col>
    </el-row>

    <el-alert :title="summary.message" type="info" show-icon :closable="false" class="hint" />

    <el-card>
      <template #header>指定时间段教师课时 Top5</template>
      <el-table :data="summary.tables?.teacher_workload_top5 || []" stripe>
        <el-table-column type="index" label="排名" width="80" />
        <el-table-column prop="teacher_name" label="教师" />
        <el-table-column prop="lesson_count" label="总节数" width="120" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
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
const summary = ref({ cards: [], tables: {}, message: '' })
const go = (route) => route && router.push(route)

const fetchSummary = async () => {
  const res = await getTeachingDashboardSummary(filters)
  if (res.success) summary.value = res.data
}

onMounted(fetchSummary)
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

.page-header span,
.hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.filter-bar {
  margin-bottom: 10px;
}

.metric-card {
  width: 100%;
  min-height: 86px;
  padding: 14px;
  margin-bottom: 12px;
  border: 1px solid var(--el-border-color-light);
  background: var(--el-bg-color);
  border-radius: 6px;
  text-align: left;
  cursor: pointer;
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

.hint {
  margin-bottom: 12px;
}
</style>
