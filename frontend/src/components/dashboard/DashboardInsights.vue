<template>
  <section v-if="insights.length" class="insights-panel">
    <div class="panel-header">
      <span v-if="eyebrow">{{ eyebrow }}</span>
      <h3>{{ title }}</h3>
    </div>
    <div class="insights-grid">
      <div
        v-for="insight in insights"
        :key="insight.title"
        class="insight-card"
        :class="[insight.type, { clickable: insight.action_route }]"
        @click="handleClick(insight)"
      >
        <span class="insight-icon">{{ iconMap[insight.type] || '•' }}</span>
        <div class="insight-content">
          <strong>{{ insight.title }}</strong>
          <p>{{ insight.message }}</p>
        </div>
        <span v-if="insight.action_route" class="action-arrow">→</span>
      </div>
    </div>
  </section>
</template>

<script setup>
import { useRouter } from 'vue-router'

defineProps({
  insights: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: '运行态势'
  },
  eyebrow: {
    type: String,
    default: ''
  }
})

const router = useRouter()

const iconMap = {
  warning: '⚠',
  info: 'ℹ',
  success: '✓'
}

const handleClick = (insight) => {
  if (insight.action_route) {
    router.push(insight.action_route)
  }
}
</script>

<style scoped>
.insights-panel {
  padding: 20px;
  margin-top: 18px;
  border: 1px solid rgba(34, 211, 238, 0.28);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(8, 47, 73, 0.58), rgba(7, 15, 30, 0.92));
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.26);
}

.insights-panel .panel-header {
  margin-bottom: 16px;
}

.insights-panel .panel-header span {
  display: block;
  margin-bottom: 4px;
  color: #67e8f9;
  font-size: 12px;
}

.insights-panel .panel-header h3 {
  margin: 0;
  color: #e5f6ff;
  font-size: 16px;
}

.insights-grid {
  display: grid;
  gap: 12px;
}

.insight-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.74);
  cursor: default;
  transition: all 0.2s ease;
}

.insight-card.clickable {
  cursor: pointer;
}

.insight-card.clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.insight-card.warning {
  border: 1px solid rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.08);
}

.insight-card.info {
  border: 1px solid rgba(56, 189, 248, 0.36);
  background: rgba(56, 189, 248, 0.06);
}

.insight-card.success {
  border: 1px solid rgba(52, 211, 153, 0.36);
  background: rgba(52, 211, 153, 0.06);
}

.insight-card.warning .insight-icon {
  color: #f87171;
  background: rgba(239, 68, 68, 0.2);
}

.insight-card.info .insight-icon {
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.2);
}

.insight-card.success .insight-icon {
  color: #34d399;
  background: rgba(52, 211, 153, 0.2);
}

.insight-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 16px;
  font-weight: 700;
}

.insight-content {
  flex: 1;
}

.insight-content strong {
  color: #f8fafc;
  font-size: 15px;
}

.insight-content p {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 13px;
}

.insight-card .action-arrow {
  color: #38bdf8;
  font-size: 18px;
}
</style>
