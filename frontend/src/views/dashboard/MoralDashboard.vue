<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2>德育驾驶舱</h2>
      <span>{{ summary.updated_at || '-' }}</span>
    </div>

    <el-row :gutter="12">
      <el-col v-for="card in summary.cards" :key="card.label" :xs="12" :sm="8" :md="6">
        <button class="metric-card" type="button" @click="go(card.route)">
          <span>{{ card.label }}</span>
          <strong>{{ card.value }}<small>{{ card.unit }}</small></strong>
        </button>
      </el-col>
    </el-row>

    <el-card>
      <template #header>低分学生 Top5</template>
      <el-table :data="summary.tables?.low_students || []" stripe>
        <el-table-column prop="student_id" label="学号" width="130" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级" />
        <el-table-column prop="total_score" label="总分" width="100" />
        <el-table-column prop="level" label="等级" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getMoralDashboardSummary } from '@/api/modules/dashboard'

const router = useRouter()
const summary = ref({ cards: [], tables: {} })
const go = (route) => route && router.push(route)

const fetchSummary = async () => {
  const res = await getMoralDashboardSummary()
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

.page-header span {
  color: var(--el-text-color-secondary);
  font-size: 13px;
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
</style>
