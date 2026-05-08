<template>
  <div class="empty-strip" :class="variant">
    {{ text }}
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    default: '暂无数据'
  },
  variant: {
    type: String,
    default: '',
    validator: (v) => ['', 'success'].includes(v)
  }
})
</script>

<style scoped>
.empty-strip {
  padding: 1rem 1.5rem;
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.26);
  border: 1px dashed rgba(148, 163, 184, 0.28);
  color: rgba(226, 232, 240, 0.55);
  font-size: 14px;
  text-align: center;
}

.empty-strip.success {
  background: rgba(16, 185, 129, 0.18);
  border-color: rgba(16, 185, 129, 0.28);
  color: rgba(134, 239, 172, 0.75);
}
</style>
