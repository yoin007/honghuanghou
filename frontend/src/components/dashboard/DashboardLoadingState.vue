<template>
  <div class="loading-dashboard">
    <header class="skeleton-hero">
      <div class="skeleton-text skeleton-kicker"></div>
      <div class="skeleton-text skeleton-title"></div>
      <div class="skeleton-text skeleton-desc"></div>
    </header>

    <section class="skeleton-metric-grid">
      <div v-for="i in metricCount" :key="i" class="skeleton-card">
        <div class="skeleton-text skeleton-label"></div>
        <div class="skeleton-number"></div>
        <div class="skeleton-orb"></div>
      </div>
    </section>

    <section class="skeleton-chart-grid">
      <div v-for="i in chartCount" :key="i" class="skeleton-chart">
        <div class="skeleton-header">
          <div class="skeleton-text skeleton-eyebrow"></div>
          <div class="skeleton-text skeleton-chart-title"></div>
        </div>
        <div class="skeleton-canvas"></div>
      </div>
    </section>
  </div>
</template>

<script setup>
defineProps({
  metricCount: {
    type: Number,
    default: 4
  },
  chartCount: {
    type: Number,
    default: 2
  }
})
</script>

<style scoped>
.loading-dashboard {
  min-height: calc(100vh - 80px);
  padding: 24px;
  background: linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96));
}

.skeleton-hero {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 26px;
  margin-bottom: 18px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.88);
}

.skeleton-text {
  max-width: 100%;
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(55, 65, 81, 0.5), rgba(55, 65, 81, 0.3), rgba(55, 65, 81, 0.5));
  animation: shimmer 1.5s infinite;
}

.skeleton-kicker {
  width: 120px;
  height: 14px;
}

.skeleton-title {
  width: 260px;
  height: 42px;
}

.skeleton-desc {
  width: 500px;
  height: 18px;
}

.skeleton-metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.skeleton-card {
  position: relative;
  min-height: 100px;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
  overflow: hidden;
}

.skeleton-label {
  width: 80px;
  height: 14px;
  margin-bottom: 12px;
}

.skeleton-number {
  max-width: 100%;
  width: 60px;
  height: 32px;
  border-radius: 4px;
  background: linear-gradient(90deg, rgba(55, 65, 81, 0.5), rgba(55, 65, 81, 0.3), rgba(55, 65, 81, 0.5));
  animation: shimmer 1.5s infinite;
}

.skeleton-orb {
  position: absolute;
  right: -30px;
  bottom: -34px;
  width: 90px;
  height: 90px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.15);
  filter: blur(8px);
}

.skeleton-chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.skeleton-chart {
  min-height: 320px;
  padding: 18px;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
}

.skeleton-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.skeleton-eyebrow {
  width: 100px;
  height: 12px;
}

.skeleton-chart-title {
  width: 180px;
  height: 17px;
}

.skeleton-canvas {
  width: 100%;
  height: 250px;
  border-radius: 8px;
  border: 1px dashed rgba(148, 163, 184, 0.25);
  background: rgba(15, 23, 42, 0.34);
}

@keyframes shimmer {
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: 200px 0;
  }
}

@media (max-width: 900px) {
  .skeleton-chart-grid {
    grid-template-columns: 1fr;
  }

  .skeleton-desc {
    width: 100%;
  }
}
</style>
