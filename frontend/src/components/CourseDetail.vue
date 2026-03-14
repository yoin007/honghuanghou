<script setup>
import { defineProps, defineEmits } from 'vue'
import { ElDialog, ElDescriptions, ElDescriptionsItem } from 'element-plus'

const props = defineProps({
  visible: {
    type: Boolean,
    required: true
  },
  course: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:visible'])

const handleClose = () => {
  emit('update:visible', false)
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    :title="course?.name"
    width="30%"
    @close="handleClose"
  >
    <el-descriptions :column="1" border>
      <el-descriptions-item label="课程名称">{{ course?.name }}</el-descriptions-item>
      <el-descriptions-item label="任课教师">{{ course?.teacher }}</el-descriptions-item>
      <el-descriptions-item label="上课时间">{{ course?.time }}</el-descriptions-item>
      <el-descriptions-item label="教室">{{ course?.room }}</el-descriptions-item>
    </el-descriptions>
  </el-dialog>
</template>
