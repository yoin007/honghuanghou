<template>
  <div class="backup-page">
    <!-- 备份配置 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>备份配置</span>
          <el-button type="primary" size="small" @click="saveConfig" :loading="configLoading">保存配置</el-button>
        </div>
      </template>
      <el-form :model="backupConfig" label-width="120px" v-loading="configLoading">
        <el-form-item label="备份目录">
          <el-input v-model="backupConfig.backup_dir" placeholder="如 ~/backups 或 C:\backups" />
          <div class="form-tip">支持 ~ 符号（Mac/Linux）和绝对路径</div>
        </el-form-item>
        <el-form-item label="最大备份数量">
          <el-input-number v-model="backupConfig.max_backups" :min="1" :max="100" />
          <div class="form-tip">超过此数量将自动删除最旧的备份</div>
        </el-form-item>
        <el-form-item label="包含 WAL 文件">
          <el-switch v-model="backupConfig.include_wal" />
          <div class="form-tip">包含实时写入缓存文件，确保数据完整性</div>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 定时备份配置 -->
    <el-card class="schedule-card">
      <template #header>
        <span>定时备份</span>
      </template>
      <el-form :model="scheduleConfig" label-width="120px" v-loading="scheduleLoading">
        <el-form-item label="启用定时备份">
          <el-switch v-model="scheduleConfig.enabled" @change="saveSchedule" />
        </el-form-item>
        <el-form-item label="备份时间" v-if="scheduleConfig.enabled">
          <el-select v-model="scheduleConfig.day_of_week" style="width: 120px; margin-right: 10px">
            <el-option label="每天" value="*" />
            <el-option label="周一" value="mon" />
            <el-option label="周二" value="tue" />
            <el-option label="周三" value="wed" />
            <el-option label="周四" value="thu" />
            <el-option label="周五" value="fri" />
            <el-option label="周六" value="sat" />
            <el-option label="周日" value="sun" />
          </el-select>
          <el-time-select
            v-model="scheduleTime"
            max-time="23:59"
            min-time="00:00"
            placeholder="选择时间"
            style="width: 120px"
            @change="updateScheduleTime"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 手动备份 -->
    <el-card class="manual-card">
      <template #header>
        <div class="card-header">
          <span>手动备份</span>
          <el-button type="primary" @click="executeBackup" :loading="backupLoading">立即备份</el-button>
        </div>
      </template>
      <el-alert v-if="backupResult" :title="backupResult.message" :type="backupResult.success ? 'success' : 'error'" show-icon :closable="true" @close="backupResult = null" />
      <el-progress v-if="backupLoading" :percentage="100" :indeterminate="true" />
    </el-card>

    <!-- 备份历史 -->
    <el-card class="history-card">
      <template #header>
        <span>备份历史</span>
      </template>
      <el-table :data="backupList" v-loading="historyLoading" stripe>
        <el-table-column prop="backup_name" label="备份文件" min-width="220" />
        <el-table-column prop="backup_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.backup_type === 'manual' ? '' : 'success'" size="small">
              {{ row.backup_type === 'manual' ? '手动' : '定时' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="file_count" label="文件数" width="80" />
        <el-table-column prop="backup_status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.backup_status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.backup_status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="操作者" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="160" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleDownload(row)" v-if="row.backup_status === 'success'">下载</el-button>
            <el-button type="danger" link size="small" @click="confirmDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadHistory"
        @current-change="loadHistory"
        style="margin-top: 16px"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getBackupConfig,
  updateBackupConfig,
  executeManualBackup,
  getBackupHistory,
  deleteBackup,
  downloadBackup,
  getBackupSchedule,
  updateBackupSchedule
} from '@/api/modules/databaseBackup'

// 备份配置
const backupConfig = reactive({
  backup_dir: '~/backups',
  max_backups: 10,
  include_wal: true
})
const configLoading = ref(false)

// 定时备份配置
const scheduleConfig = reactive({
  enabled: false,
  day_of_week: 'sun',
  hour: 3,
  minute: 0
})
const scheduleLoading = ref(false)
const scheduleTime = computed({
  get: () => `${String(scheduleConfig.hour).padStart(2, '0')}:${String(scheduleConfig.minute).padStart(2, '0')}`,
  set: (val) => {
    if (val) {
      const [h, m] = val.split(':')
      scheduleConfig.hour = parseInt(h)
      scheduleConfig.minute = parseInt(m)
    }
  }
})

// 手动备份
const backupLoading = ref(false)
const backupResult = ref(null)

// 备份历史
const backupList = ref([])
const historyLoading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 加载配置
const loadConfig = async () => {
  configLoading.value = true
  try {
    const res = await getBackupConfig()
    if (res.success) {
      Object.assign(backupConfig, res.data)
    }
  } catch (e) {
    console.error('加载备份配置失败:', e)
  } finally {
    configLoading.value = false
  }
}

const loadSchedule = async () => {
  scheduleLoading.value = true
  try {
    const res = await getBackupSchedule()
    if (res.success) {
      Object.assign(scheduleConfig, res.data)
    }
  } catch (e) {
    console.error('加载定时备份配置失败:', e)
  } finally {
    scheduleLoading.value = false
  }
}

const loadHistory = async () => {
  historyLoading.value = true
  try {
    const res = await getBackupHistory({ page: page.value, size: pageSize.value })
    if (res.success) {
      backupList.value = res.data.backups || []
      total.value = res.data.total || 0
    }
  } catch (e) {
    console.error('加载备份历史失败:', e)
  } finally {
    historyLoading.value = false
  }
}

// 保存配置
const saveConfig = async () => {
  configLoading.value = true
  try {
    const res = await updateBackupConfig(backupConfig)
    if (res.success) {
      ElMessage.success('备份配置已保存')
    }
  } catch (e) {
    ElMessage.error('保存配置失败: ' + e.message)
  } finally {
    configLoading.value = false
  }
}

const saveSchedule = async () => {
  scheduleLoading.value = true
  try {
    const res = await updateBackupSchedule(scheduleConfig)
    if (res.success) {
      ElMessage.success(scheduleConfig.enabled ? '定时备份已启用' : '定时备份已禁用')
    }
  } catch (e) {
    ElMessage.error('保存配置失败: ' + e.message)
  } finally {
    scheduleLoading.value = false
  }
}

const updateScheduleTime = () => {
  saveSchedule()
}

// 执行备份
const executeBackup = async () => {
  backupLoading.value = true
  backupResult.value = null
  try {
    const res = await executeManualBackup()
    if (res.success) {
      backupResult.value = { success: true, message: res.message }
      ElMessage.success(res.message)
      loadHistory()
    }
  } catch (e) {
    backupResult.value = { success: false, message: e.message || '备份失败' }
    ElMessage.error('备份失败')
  } finally {
    backupLoading.value = false
  }
}

// 下载备份
const handleDownload = async (row) => {
  try {
    const blob = await downloadBackup(row.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = row.backup_name
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

// 删除备份
const confirmDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除备份 ${row.backup_name}？`, '删除确认', { type: 'warning' })
    const res = await deleteBackup(row.id)
    if (res.success) {
      ElMessage.success('已删除')
      loadHistory()
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 格式化大小
const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

onMounted(() => {
  loadConfig()
  loadSchedule()
  loadHistory()
})
</script>

<style scoped>
.backup-page {
  padding: 20px;
}

.config-card,
.schedule-card,
.manual-card,
.history-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>