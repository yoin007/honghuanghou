<!-- Mobile Card View Component -->
<!-- 当在移动端时，将表格数据转换为卡片视图 -->
<template>
  <div class="card-view">
    <!-- 桌面端表格视图 -->
    <div v-if="!isMobile" class="table-view">
      <slot name="table"></slot>
    </div>

    <!-- 移动端卡片视图 -->
    <div v-else class="mobile-cards">
      <div
        v-for="(item, index) in data"
        :key="index"
        class="data-card"
        :class="{ 'selected': selectedIds?.includes(item[idKey]) }"
        @click="handleClick(item)"
      >
        <div v-if="showSelection" class="card-checkbox">
          <el-checkbox
            :model-value="selectedIds?.includes(item[idKey])"
            @click.stop
            @change="handleSelect(item)"
          />
        </div>

        <div class="card-content">
          <div
            v-for="col in visibleColumns"
            :key="col.prop"
            class="card-row"
          >
            <span class="card-label">{{ col.label }}</span>
            <span class="card-value">
              <slot :name="`cell-${col.prop}`" :row="item" :value="item[col.prop]">
                {{ item[col.prop] }}
              </slot>
            </span>
          </div>
        </div>

        <div v-if="$slots.actions" class="card-actions" @click.stop>
          <slot name="actions" :row="item"></slot>
        </div>
      </div>

      <el-empty v-if="data.length === 0" :description="emptyText" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  columns: {
    type: Array,
    default: () => []
  },
  idKey: {
    type: String,
    default: 'id'
  },
  showSelection: {
    type: Boolean,
    default: false
  },
  selectedIds: {
    type: Array,
    default: () => []
  },
  emptyText: {
    type: String,
    default: '暂无数据'
  },
  mobileBreakpoint: {
    type: Number,
    default: 768
  }
})

const emit = defineEmits(['select', 'click'])

const isMobile = ref(window.innerWidth <= props.mobileBreakpoint)

const handleResize = () => {
  isMobile.value = window.innerWidth <= props.mobileBreakpoint
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})

const visibleColumns = computed(() => {
  return props.columns.filter(col => !col.hideOnMobile)
})

const handleSelect = (item) => {
  emit('select', item)
}

const handleClick = (item) => {
  emit('click', item)
}
</script>

<style scoped>
.table-view {
  width: 100%;
}

.mobile-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 10px;
}

.data-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  position: relative;
}

.data-card.selected {
  border: 2px solid #409eff;
}

.card-checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
}

.card-content {
  margin-top: 8px;
}

.card-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.card-row:last-child {
  border-bottom: none;
}

.card-label {
  color: #909399;
  font-size: 13px;
  flex-shrink: 0;
}

.card-value {
  color: #303133;
  font-size: 14px;
  text-align: right;
  word-break: break-all;
}

.card-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media screen and (max-width: 576px) {
  .mobile-cards {
    padding: 0 8px;
  }

  .data-card {
    padding: 10px;
  }

  .card-row {
    padding: 6px 0;
  }

  .card-label {
    font-size: 12px;
  }

  .card-value {
    font-size: 13px;
  }
}
</style>
