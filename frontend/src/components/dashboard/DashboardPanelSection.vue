<template>
  <section class="dashboard-panel-section" :class="variant" :style="sectionStyle">
    <DashboardPanelHeader v-if="title" :eyebrow="eyebrow" :title="title" />
    <slot />
  </section>
</template>

<script setup>
import { computed } from 'vue'
import DashboardPanelHeader from '@/components/dashboard/DashboardPanelHeader.vue'

const props = defineProps({
  eyebrow: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: ''
  },
  variant: {
    type: String,
    default: ''
  },
  minHeight: {
    type: [Number, String],
    default: ''
  }
})

const sectionStyle = computed(() => {
  if (!props.minHeight) return {}
  const minHeight = typeof props.minHeight === 'number' ? `${props.minHeight}px` : props.minHeight
  return { minHeight }
})
</script>

<style scoped>
.dashboard-panel-section {
  padding: 18px;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
}

.dashboard-panel-section.attendance {
  border-color: rgba(251, 113, 133, 0.28);
}

.dashboard-panel-section.danger {
  border-color: rgba(251, 113, 133, 0.28);
  background: linear-gradient(145deg, rgba(48, 18, 35, 0.82), rgba(7, 15, 30, 0.9));
}
</style>
