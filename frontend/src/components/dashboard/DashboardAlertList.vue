<template>
  <div v-if="items.length" class="dashboard-alert-list">
    <div
      v-for="(item, index) in items"
      :key="getKey(item, index)"
      class="dashboard-alert-row"
      :class="variant"
    >
      <slot :item="item" :index="index" />
    </div>
  </div>
  <DashboardEmptyStrip v-else :text="emptyText" />
</template>

<script setup>
import DashboardEmptyStrip from '@/components/dashboard/DashboardEmptyStrip.vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  variant: {
    type: String,
    default: 'info'
  },
  itemKey: {
    type: [String, Function],
    default: ''
  },
  emptyText: {
    type: String,
    default: '暂无数据。'
  }
})

const getKey = (item, index) => {
  if (typeof props.itemKey === 'function') return props.itemKey(item, index)
  if (props.itemKey) return item?.[props.itemKey] ?? index
  return index
}
</script>

<style scoped>
.dashboard-alert-list {
  display: grid;
  gap: 10px;
}

.dashboard-alert-row {
  display: flex;
  gap: 14px;
  padding: 12px;
  border-radius: 6px;
}

.dashboard-alert-row.warning {
  border: 1px solid rgba(251, 191, 36, 0.2);
  background: rgba(120, 53, 15, 0.22);
}

.dashboard-alert-row.danger {
  border: 1px solid rgba(251, 113, 133, 0.2);
  background: rgba(127, 29, 29, 0.18);
}

.dashboard-alert-row.info {
  border: 1px solid rgba(56, 189, 248, 0.2);
  background: rgba(30, 64, 175, 0.18);
}
</style>
