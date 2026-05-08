<template>
  <section class="leave-panel" :class="mode">
    <div class="panel-header">
      <span v-if="eyebrow">{{ eyebrow }}</span>
      <h3>{{ title }}</h3>
    </div>
    <div v-if="students.length" class="leave-list">
      <div
        v-for="student in students"
        :key="student.id || student.student_id || student.name"
        class="leave-row"
        :class="{ warning: student.status === '已出校', info: student.status === '已请假' }"
      >
        <div class="leave-info">
          <strong>{{ student.name || '未知' }}</strong>
          <span>{{ getMeta(student) }}</span>
        </div>
        <div class="leave-status">
          <span class="status-tag" :class="student.status">{{ student.status }}</span>
          <small>{{ formatDateSlashMonthDay(student.create_at) }}</small>
        </div>
      </div>
    </div>
    <DashboardEmptyStrip
      v-else
      :text="emptyText"
      variant="success"
    />
  </section>
</template>

<script setup>
import DashboardEmptyStrip from './DashboardEmptyStrip.vue'
import { formatDateSlashMonthDay } from '@/utils/time'

const props = defineProps({
  students: {
    type: Array,
    default: () => []
  },
  mode: {
    type: String,
    default: 'class',
    validator: value => ['class', 'moral'].includes(value)
  },
  eyebrow: {
    type: String,
    default: ''
  },
  title: {
    type: String,
    default: '当前请假学生'
  },
  emptyText: {
    type: String,
    default: '当前无请假学生，出勤正常'
  }
})

const getMeta = (student) => {
  const pieces = []
  if (props.mode === 'moral' && student.class_name) pieces.push(student.class_name)
  if (student.style) pieces.push(student.style)
  if (student.days !== undefined && student.days !== null) pieces.push(`${student.days}天`)
  if (props.mode === 'class' && student.status) pieces.push(student.status)
  return pieces.join(' · ')
}
</script>

<style scoped>
.leave-panel {
  padding: 18px;
  margin-top: 18px;
  border: 1px solid rgba(251, 113, 133, 0.28);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(48, 18, 35, 0.82), rgba(7, 15, 30, 0.9));
}

.leave-panel.class {
  padding: 0;
  margin-top: 0;
  border: 0;
  background: transparent;
}

.panel-header span {
  color: #67e8f9;
  font-size: 12px;
}

.leave-panel .panel-header h3 {
  margin: 4px 0 14px;
  color: #e5f6ff;
  font-size: 16px;
}

.leave-list {
  display: grid;
  gap: 8px;
}

.leave-panel.moral .leave-list {
  gap: 10px;
}

.leave-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.6);
}

.leave-panel.moral .leave-row {
  padding: 13px 14px;
  border-radius: 8px;
}

.leave-row.warning {
  border-color: rgba(251, 113, 133, 0.36);
  background: rgba(127, 29, 29, 0.16);
}

.leave-row.info {
  border-color: rgba(56, 189, 248, 0.36);
  background: rgba(14, 116, 144, 0.12);
}

.leave-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.leave-info strong {
  color: #e2e8f0;
  font-weight: 500;
}

.leave-info span {
  color: #94a3b8;
  font-size: 13px;
}

.leave-status {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.status-tag {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.status-tag.已请假 {
  color: #f87171;
  background: rgba(239, 68, 68, 0.2);
}

.status-tag.已出校 {
  color: #fbbf24;
  background: rgba(251, 191, 36, 0.2);
}

.leave-status small {
  color: #64748b;
  font-size: 12px;
}
</style>
