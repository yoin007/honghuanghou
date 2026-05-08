<template>
  <section class="file-upload-panel">
    <div class="panel-header">
      <span>FILE UPLOAD METRICS</span>
      <h3>文件上传统计</h3>
    </div>
    <div class="file-upload-stats">
      <div v-for="metric in metrics" :key="metric.label" class="stat-item" :class="metric.className">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}<small v-if="metric.unit">{{ metric.unit }}</small></strong>
      </div>
    </div>

    <div v-if="pendingFiles.length" class="pending-files-section">
      <h4>待处理文件 <small>逾期文件已标记</small></h4>
      <div
        v-for="file in pendingFiles"
        :key="file.id"
        class="pending-file-item"
        :class="{ overdue: file.overdue_days > 0 }"
      >
        <span class="file-name">{{ file.original_name }}</span>
        <span class="file-user">{{ file.username }}</span>
        <span class="file-date">{{ formatDateSlashMonthDay(file.uploaded_at) }}</span>
        <span v-if="file.overdue_days > 0" class="file-overdue">
          <strong>逾期 {{ file.overdue_days }} 天</strong>
        </span>
        <span v-else class="file-status">待处理</span>
      </div>
    </div>

    <div v-if="topUsers.length" class="top-users-list">
      <h4>上传排行</h4>
      <div v-for="(user, idx) in topUsers" :key="user.username" class="user-item">
        <span class="rank">{{ idx + 1 }}</span>
        <span class="name">{{ user.username }}</span>
        <span class="count">{{ user.count }} 份</span>
      </div>
    </div>
    <div v-else-if="!pendingFiles.length" class="empty-users">
      <span>本月暂无文件上传记录</span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { getDashboardCardValue } from '@/utils/filegather'
import { formatDateSlashMonthDay } from '@/utils/time'

const props = defineProps({
  cards: {
    type: Array,
    default: () => []
  },
  pendingFiles: {
    type: Array,
    default: () => []
  },
  topUsers: {
    type: Array,
    default: () => []
  }
})

const getValue = (label) => getDashboardCardValue(props.cards, label) || 0
const hasOverdueFiles = computed(() => getValue('逾期文件') > 0)

const metrics = computed(() => [
  { label: '待处理文件', value: getValue('待处理文件') },
  { label: '本月文件', value: getValue('本月文件') },
  { label: '已完成文件', value: getValue('已完成文件') },
  { label: '完成率', value: getValue('完成率'), unit: '%', className: 'completion-rate' },
  { label: '逾期文件', value: getValue('逾期文件'), className: ['overdue-count', { warning: hasOverdueFiles.value }] }
])
</script>

<style scoped>
.file-upload-panel {
  padding: 20px;
  margin-bottom: 18px;
  border: 1px solid rgba(244, 114, 182, 0.28);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.26);
}

.panel-header span {
  color: #67e8f9;
  font-size: 12px;
}

.panel-header h3 {
  margin: 4px 0 20px;
  color: #e5f6ff;
  font-size: 17px;
}

.file-upload-stats {
  display: flex;
  gap: 24px;
  margin: 20px 0;
}

.stat-item {
  flex: 1;
  padding: 16px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.74);
  text-align: center;
}

.stat-item span {
  color: #94a3b8;
  font-size: 14px;
}

.stat-item strong {
  display: block;
  margin-top: 10px;
  color: #f8fafc;
  font-size: 28px;
}

.stat-item.completion-rate strong {
  color: #34d399;
}

.stat-item.overdue-count.warning {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.12);
}

.stat-item.overdue-count.warning strong {
  color: #f87171;
}

.pending-files-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
}

.pending-files-section h4,
.top-users-list h4 {
  margin: 0 0 12px;
  color: #e5f6ff;
  font-size: 16px;
}

.pending-files-section h4 small {
  color: #94a3b8;
  font-size: 12px;
}

.pending-file-item,
.user-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 6px;
  background: rgba(15, 23, 42, 0.6);
}

.pending-file-item {
  font-size: 13px;
}

.pending-file-item.overdue {
  border-color: rgba(239, 68, 68, 0.36);
  background: rgba(239, 68, 68, 0.08);
}

.pending-file-item .file-name {
  flex: 1;
  color: #e2e8f0;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pending-file-item .file-user {
  color: #94a3b8;
}

.pending-file-item .file-date {
  color: #64748b;
  font-size: 12px;
}

.pending-file-item .file-overdue strong {
  color: #f87171;
  font-size: 12px;
}

.pending-file-item .file-status {
  color: #fbbf24;
  font-size: 12px;
}

.top-users-list {
  margin-top: 20px;
}

.user-item .rank {
  width: 24px;
  height: 24px;
  color: #f8fafc;
  border-radius: 999px;
  background: rgba(244, 114, 182, 0.4);
  font-size: 12px;
  font-weight: 700;
  line-height: 24px;
  text-align: center;
}

.user-item .name {
  color: #e2e8f0;
  font-weight: 500;
}

.user-item .count {
  margin-left: auto;
  color: #94a3b8;
  font-size: 13px;
}

.empty-users {
  padding: 20px;
  border: 1px dashed rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.36);
  text-align: center;
}

.empty-users span {
  color: rgba(226, 232, 240, 0.68);
}

@media (max-width: 980px) {
  .file-upload-stats {
    flex-wrap: wrap;
    gap: 12px;
  }

  .stat-item {
    min-width: calc(50% - 6px);
  }

  .pending-file-item {
    flex-wrap: wrap;
  }

  .pending-file-item .file-name {
    flex: 100%;
  }
}
</style>
