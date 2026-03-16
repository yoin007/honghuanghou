<template>
  <div class="skeleton-container">
    <div v-if="type === 'table'" class="skeleton-table">
      <div class="skeleton-header">
        <div
          v-for="n in columns"
          :key="n"
          class="skeleton-cell header-cell"
          :style="{ width: getRandomWidth() }"
        ></div>
      </div>
      <div v-for="row in rows" :key="row" class="skeleton-row">
        <div
          v-for="col in columns"
          :key="col"
          class="skeleton-cell"
          :style="{ width: getRandomWidth() }"
        ></div>
      </div>
    </div>

    <div v-else-if="type === 'card'" class="skeleton-cards">
      <div v-for="n in rows" :key="n" class="skeleton-card">
        <div class="skeleton-card-image"></div>
        <div class="skeleton-card-title"></div>
        <div class="skeleton-card-text"></div>
        <div class="skeleton-card-text short"></div>
      </div>
    </div>

    <div v-else-if="type === 'list'" class="skeleton-list">
      <div v-for="n in rows" :key="n" class="skeleton-list-item">
        <div class="skeleton-avatar"></div>
        <div class="skeleton-content">
          <div class="skeleton-title"></div>
          <div class="skeleton-description"></div>
        </div>
      </div>
    </div>

    <div v-else class="skeleton-block" :style="{ height: height, width: width }"></div>
  </div>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'block' // block, table, card, list
  },
  rows: {
    type: Number,
    default: 5
  },
  columns: {
    type: Number,
    default: 4
  },
  height: {
    type: String,
    default: '20px'
  },
  width: {
    type: String,
    default: '100%'
  }
})

const getRandomWidth = () => {
  const widths = ['60%', '80%', '70%', '90%', '50%']
  return widths[Math.floor(Math.random() * widths.length)]
}
</script>

<style scoped>
.skeleton-container {
  width: 100%;
}

/* Block skeleton */
.skeleton-block {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
}

/* Table skeleton */
.skeleton-table {
  width: 100%;
}

.skeleton-header {
  display: flex;
  padding: 12px 8px;
  gap: 8px;
  border-bottom: 1px solid #ebeef5;
}

.skeleton-row {
  display: flex;
  padding: 12px 8px;
  gap: 8px;
  border-bottom: 1px solid #f5f7fa;
}

.skeleton-cell {
  height: 16px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
  flex-shrink: 0;
}

.header-cell {
  height: 14px;
  background: #e8e8e8;
}

/* Card skeleton */
.skeleton-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.skeleton-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

.skeleton-card-image {
  height: 120px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 12px;
}

.skeleton-card-title {
  height: 20px;
  width: 60%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 8px;
}

.skeleton-card-text {
  height: 14px;
  width: 90%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 6px;
}

.skeleton-card-text.short {
  width: 50%;
}

/* List skeleton */
.skeleton-list {
  width: 100%;
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  gap: 12px;
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  flex-shrink: 0;
}

.skeleton-content {
  flex: 1;
}

.skeleton-title {
  height: 16px;
  width: 30%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 8px;
}

.skeleton-description {
  height: 12px;
  width: 60%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
