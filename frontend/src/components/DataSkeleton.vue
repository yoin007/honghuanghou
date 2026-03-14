<!-- Data Skeleton Loader Component -->
<template>
  <div class="skeleton-container">
    <!-- 表格骨架屏 -->
    <div v-if="type === 'table'" class="skeleton-table">
      <!-- 表头 -->
      <div v-if="showHeader" class="skeleton-header">
        <div
          v-for="col in columns"
          :key="col.prop"
          class="skeleton-cell header-cell"
          :style="{ width: col.width || '100px', flex: col.width ? 'none' : 1 }"
        ></div>
      </div>

      <!-- 表格行 -->
      <div
        v-for="i in rows"
        :key="i"
        class="skeleton-row"
      >
        <div
          v-for="col in columns"
          :key="col.prop"
          class="skeleton-cell"
          :style="{ width: col.width || '100px', flex: col.width ? 'none' : 1 }"
        >
          <div class="skeleton-text" :style="{ width: getRandomWidth() }"></div>
        </div>
      </div>
    </div>

    <!-- 卡片骨架屏 -->
    <div v-else-if="type === 'card'" class="skeleton-cards">
      <div
        v-for="i in rows"
        :key="i"
        class="skeleton-card"
      >
        <div class="skeleton-card-header"></div>
        <div class="skeleton-card-body">
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </div>
      </div>
    </div>

    <!-- 列表骨架屏 -->
    <div v-else-if="type === 'list'" class="skeleton-list">
      <div
        v-for="i in rows"
        :key="i"
        class="skeleton-list-item"
      >
        <div class="skeleton-avatar"></div>
        <div class="skeleton-list-content">
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </div>
      </div>
    </div>

    <!-- 统计卡片骨架屏 -->
    <div v-else class="skeleton-stats">
      <div
        v-for="i in rows"
        :key="i"
        class="skeleton-stat-card"
      >
        <div class="skeleton-stat-value"></div>
        <div class="skeleton-stat-label"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'table' // table, card, list, stats
  },
  rows: {
    type: Number,
    default: 5
  },
  columns: {
    type: Array,
    default: () => [
      { prop: 'col1', label: '列1', width: '100px' },
      { prop: 'col2', label: '列2', width: '120px' },
      { prop: 'col3', label: '列3' }
    ]
  },
  showHeader: {
    type: Boolean,
    default: true
  }
})

const getRandomWidth = () => {
  const widths = ['60%', '70%', '80%', '90%', '100%']
  return widths[Math.floor(Math.random() * widths.length)]
}
</script>

<style scoped>
.skeleton-container {
  width: 100%;
}

/* 表格骨架屏 */
.skeleton-table {
  background: #fff;
  border-radius: 4px;
}

.skeleton-header {
  display: flex;
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
}

.skeleton-row {
  display: flex;
  padding: 14px 0;
  border-bottom: 1px solid #f5f5f5;
}

.skeleton-cell {
  padding: 0 10px;
}

.skeleton-text {
  height: 14px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e6e6e6 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 2px;
}

@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* 卡片骨架屏 */
.skeleton-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.skeleton-card {
  width: calc(33.333% - 16px);
  min-width: 200px;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.skeleton-card-header {
  height: 20px;
  width: 60%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e6e6e6 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
  margin-bottom: 12px;
}

.skeleton-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 12px;
  width: 100%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e6e6e6 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 2px;
}

.skeleton-line.short {
  width: 60%;
}

/* 列表骨架屏 */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: #fff;
  border-radius: 8px;
}

.skeleton-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(90deg, #f0f0f0 25%, #e6e6e6 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  flex-shrink: 0;
}

.skeleton-list-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 统计卡片骨架屏 */
.skeleton-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
}

.skeleton-stat-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.skeleton-stat-value {
  height: 32px;
  width: 60px;
  margin: 0 auto 12px;
  background: linear-gradient(90deg, #f0f0f0 25%, #e6e6e6 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 4px;
}

.skeleton-stat-label {
  height: 14px;
  width: 80px;
  margin: 0 auto;
  background: linear-gradient(90deg, #f0f0f0 25%, #e6e6e6 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: skeleton-loading 1.5s infinite;
  border-radius: 2px;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .skeleton-card {
    width: 100%;
  }

  .skeleton-cell {
    padding: 0 6px;
  }

  .skeleton-header,
  .skeleton-row {
    padding: 10px 0;
  }
}
</style>
