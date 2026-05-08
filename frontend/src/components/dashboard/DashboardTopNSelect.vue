<template>
  <div class="topn-select">
    <span>{{ label }}</span>
    <el-select :model-value="modelValue" class="top-select" @change="handleChange">
      <el-option v-for="option in options" :key="option" :value="option" :label="`Top ${option}`" />
    </el-select>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: Number,
    default: 5
  },
  label: {
    type: String,
    default: '排行规模'
  },
  options: {
    type: Array,
    default: () => [5, 10, 15]
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const handleChange = (value) => {
  emit('update:modelValue', value)
  emit('change', value)
}
</script>

<style scoped>
.topn-select {
  display: grid;
  gap: 8px;
  min-width: 130px;
  padding: 14px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
}

.topn-select span {
  color: #94a3b8;
  font-size: 12px;
}

.top-select {
  width: 110px;
}
</style>
