<template>
  <div class="panel-header">
    <span v-if="eyebrow" class="eyebrow">{{ eyebrow }}</span>
    <h3>{{ title }}</h3>
  </div>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    required: true
  }
})
</script>

<style scoped>
.panel-header {
  margin-bottom: 16px;
}

.panel-header .eyebrow {
  display: block;
  margin-bottom: 4px;
  color: #67e8f9;
  font-size: 12px;
}

.panel-header h3 {
  margin: 0;
  color: #e5f6ff;
  font-size: 16px;
}
</style>