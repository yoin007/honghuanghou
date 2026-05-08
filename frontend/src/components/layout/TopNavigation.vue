<template>
  <el-menu
    :default-active="activeIndex"
    mode="horizontal"
    class="top-nav-menu"
    @select="handleSelect"
  >
    <el-sub-menu v-for="group in visibleMenuGroups" :key="group.key" :index="group.key">
      <template #title>{{ group.label }}</template>
      <el-menu-item
        v-for="item in group.items"
        :key="item.key"
        :index="item.route"
      >
        {{ item.label }}
      </el-menu-item>
    </el-sub-menu>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useResourcePermissionStore } from '@/stores/resourcePermission'

const props = defineProps({
  activeIndex: {
    type: String,
    default: '/'
  }
})

const emit = defineEmits(['select'])

const resourceStore = useResourcePermissionStore()

// 动态构建可见菜单树
const visibleMenuGroups = computed(() => {
  return resourceStore.buildMenuTree()
})

const handleSelect = (index) => {
  emit('select', index)
}
</script>

<style scoped>
.top-nav-menu {
  border-bottom: none;
  background-color: transparent;
}

.top-nav-menu :deep(.el-menu-item),
.top-nav-menu :deep(.el-sub-menu__title) {
  color: #fff;
  font-weight: 500;
}

.top-nav-menu :deep(.el-menu-item.is-active),
.top-nav-menu :deep(.el-sub-menu.is-active .el-sub-menu__title) {
  background-color: rgba(255, 255, 255, 0.15) !important;
  color: #fff;
}

.top-nav-menu :deep(.el-menu-item:hover),
.top-nav-menu :deep(.el-sub-menu__title:hover) {
  color: #fff;
  background-color: rgba(255, 255, 255, 0.1) !important;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .top-nav-menu {
    display: flex;
    overflow-x: auto;
    white-space: nowrap;
    width: 100%;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }

  .top-nav-menu::-webkit-scrollbar {
    display: none;
  }

  .top-nav-menu :deep(.el-menu-item),
  .top-nav-menu :deep(.el-sub-menu),
  .top-nav-menu :deep(.el-sub-menu__title) {
    display: inline-flex;
    flex-shrink: 0;
  }
}
</style>