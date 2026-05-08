<template>
  <section class="chart-panel">
    <div class="panel-header">
      <div>
        <span v-if="eyebrow" class="eyebrow">{{ eyebrow }}</span>
        <h3>{{ title }}</h3>
      </div>
      <slot name="action" />
    </div>
    <div v-if="hasData" ref="chartRef" class="chart-canvas"></div>
    <div v-else class="empty-state">
      <span>{{ emptyText }}</span>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init as initChart } from '@/utils/charting'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  eyebrow: {
    type: String,
    default: ''
  },
  option: {
    type: Object,
    required: true
  },
  empty: {
    type: Boolean,
    default: false
  },
  emptyText: {
    type: String,
    default: '暂无可视化数据'
  }
})

const chartRef = ref(null)
let chartInstance = null

const hasData = computed(() => !props.empty)

const renderChart = async () => {
  await nextTick()
  if (!chartRef.value || !hasData.value) return
  if (!chartInstance) {
    chartInstance = initChart(chartRef.value)
  }
  chartInstance.setOption(props.option, true)
}

const resizeChart = () => {
  if (chartInstance) chartInstance.resize()
}

watch(
  () => [props.option, props.empty],
  () => {
    if (props.empty && chartInstance) {
      chartInstance.dispose()
      chartInstance = null
      return
    }
    renderChart()
  },
  { deep: true }
)

onMounted(() => {
  renderChart()
  window.addEventListener('resize', resizeChart)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeChart)
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.chart-panel {
  min-height: 320px;
  padding: 18px;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9)),
    radial-gradient(circle at 20% 0%, rgba(45, 212, 191, 0.18), transparent 34%);
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.26), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.eyebrow {
  display: block;
  margin-bottom: 4px;
  color: #67e8f9;
  font-size: 12px;
}

h3 {
  margin: 0;
  color: #e5f6ff;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0;
}

.chart-canvas {
  width: 100%;
  height: 250px;
}

.empty-state {
  display: grid;
  height: 250px;
  place-items: center;
  color: rgba(226, 232, 240, 0.62);
  border: 1px dashed rgba(148, 163, 184, 0.25);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.34);
}
</style>
