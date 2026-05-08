<template>
  <el-select
    :model-value="classCode"
    placeholder="选择班级"
    @change="handleChange"
    class="class-select"
  >
    <el-option
      v-for="code in classCodes"
      :key="code"
      :label="code"
      :value="code"
    />
  </el-select>
</template>

<script setup>
defineProps({
  classCode: {
    type: String,
    default: ''
  },
  classCodes: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['change'])

const handleChange = (value) => {
  emit('change', value)
}
</script>

<style scoped>
.class-select {
  width: 150px;
}

@media screen and (max-width: 768px) {
  .class-select {
    width: 100%;
  }
}
</style>
