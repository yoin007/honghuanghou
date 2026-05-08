<template>
  <div class="time-chip">
    <span>{{ label }}</span>
    <strong>{{ value || fallback }}</strong>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    default: '数据更新'
  },
  value: {
    type: String,
    default: ''
  },
  fallback: {
    type: String,
    default: '-'
  }
})
</script>

<style scoped>
.time-chip {
  min-width: 180px;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
}

.time-chip span {
  display: block;
  margin-bottom: 8px;
  color: #94a3b8;
  font-size: 12px;
}

.time-chip strong {
  color: #f8fafc;
  font-size: 16px;
}
</style>