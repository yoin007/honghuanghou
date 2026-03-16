<template>
  <div class="system-monitor-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>系统监控</span>
          <el-tag :type="statusType" effect="dark">{{ statusText }}</el-tag>
        </div>
      </template>

      <!-- 系统状态概览 -->
      <el-row :gutter="20" class="status-overview">
        <el-col :xs="24" :sm="12" :md="6">
          <div class="status-card">
            <div class="status-icon cpu">
              <Cpu />
            </div>
            <div class="status-info">
              <div class="status-label">CPU 使用率</div>
              <div class="status-value">{{ systemInfo.cpu_percent || 0 }}%</div>
              <el-progress
                :percentage="systemInfo.cpu_percent || 0"
                :color="getProgressColor(systemInfo.cpu_percent)"
                :stroke-width="8"
              />
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="status-card">
            <div class="status-icon memory">
              <Monitor />
            </div>
            <div class="status-info">
              <div class="status-label">内存使用</div>
              <div class="status-value">{{ formatBytes(systemInfo.memory_used) }} / {{ formatBytes(systemInfo.memory_total) }}</div>
              <el-progress
                :percentage="memoryPercent"
                :color="getProgressColor(memoryPercent)"
                :stroke-width="8"
              />
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="status-card">
            <div class="status-icon disk">
              <Folder />
            </div>
            <div class="status-info">
              <div class="status-label">磁盘使用</div>
              <div class="status-value">{{ formatBytes(systemInfo.disk_used) }} / {{ formatBytes(systemInfo.disk_total) }}</div>
              <el-progress
                :percentage="diskPercent"
                :color="getProgressColor(diskPercent)"
                :stroke-width="8"
              />
            </div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12" :md="6">
          <div class="status-card">
            <div class="status-icon websocket">
              <Connection />
            </div>
            <div class="status-info">
              <div class="status-label">WebSocket 连接</div>
              <div class="status-value">{{ wsInfo.active_connections || 0 }}</div>
              <div class="status-detail">在线</div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 详细信息 -->
      <el-row :gutter="20" class="detail-info">
        <el-col :xs="24" :sm="12">
          <div class="detail-item">
            <span class="detail-label">主机名:</span>
            <span class="detail-value">{{ systemInfo.hostname || '-' }}</span>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12">
          <div class="detail-item">
            <span class="detail-label">操作系统:</span>
            <span class="detail-value">{{ systemInfo.platform || '-' }}</span>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12">
          <div class="detail-item">
            <span class="detail-label">CPU 核心数:</span>
            <span class="detail-value">{{ systemInfo.cpu_count || 1 }}</span>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12">
          <div class="detail-item">
            <span class="detail-label">服务器运行时间:</span>
            <span class="detail-value">{{ systemInfo.uptime || '-' }}</span>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12">
          <div class="detail-item">
            <span class="detail-label">负载平均:</span>
            <span class="detail-value">{{ formatLoadAvg(systemInfo.load_avg) }}</span>
          </div>
        </el-col>
        <el-col :xs="24" :sm="12">
          <div class="detail-item">
            <span class="detail-label">最后更新时间:</span>
            <span class="detail-value">{{ lastUpdateTime }}</span>
          </div>
        </el-col>
      </el-row>

      <!-- 进程信息 -->
      <div class="process-section">
        <h3>进程信息</h3>
        <el-table :data="processList" v-loading="loading" style="width: 100%" border stripe size="small">
          <el-table-column prop="pid" label="PID" width="100" align="center" />
          <el-table-column prop="name" label="进程名称" min-width="150" show-overflow-tooltip />
          <el-table-column prop="memory_mb" label="内存 (MB)" width="120" align="right">
            <template #default="scope">
              {{ scope.row.memory_mb?.toFixed(1) || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="cpu_percent" label="CPU %" width="100" align="right">
            <template #default="scope">
              {{ scope.row.cpu_percent?.toFixed(1) || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="threads" label="线程数" width="100" align="center" />
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="scope">
              <el-tag :type="getProcessStatusType(scope.row.status)" size="small">
                {{ scope.row.status || 'running' }}
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Cpu, Monitor, Folder, Connection } from '@element-plus/icons-vue'
import api from '../utils/api'

// 数据
const loading = ref(false)
const systemInfo = ref({})
const wsInfo = ref({})
const processList = ref([])
const lastUpdateTime = ref('')
let refreshTimer = null

// 计算属性
const memoryPercent = computed(() => {
  if (!systemInfo.value.memory_total) return 0
  return Math.round((systemInfo.value.memory_used / systemInfo.value.memory_total) * 100)
})

const diskPercent = computed(() => {
  if (!systemInfo.value.disk_total) return 0
  return Math.round((systemInfo.value.disk_used / systemInfo.value.disk_total) * 100)
})

const statusType = computed(() => {
  const maxPercent = Math.max(
    systemInfo.value.cpu_percent || 0,
    memoryPercent.value,
    diskPercent.value
  )
  if (maxPercent >= 90) return 'danger'
  if (maxPercent >= 70) return 'warning'
  return 'success'
})

const statusText = computed(() => {
  const maxPercent = Math.max(
    systemInfo.value.cpu_percent || 0,
    memoryPercent.value,
    diskPercent.value
  )
  if (maxPercent >= 90) return '告警'
  if (maxPercent >= 70) return '警告'
  return '正常'
})

// 方法
const formatBytes = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024
    i++
  }
  return `${bytes.toFixed(1)} ${units[i]}`
}

const formatLoadAvg = (loadAvg) => {
  if (!loadAvg || !Array.isArray(loadAvg)) return '-'
  return `${loadAvg[0].toFixed(2)}, ${loadAvg[1].toFixed(2)}, ${loadAvg[2].toFixed(2)}`
}

const getProgressColor = (percent) => {
  if (percent >= 90) return '#f56c6c'
  if (percent >= 70) return '#e6a23c'
  return '#67c23a'
}

const getProcessStatusType = (status) => {
  const statusMap = {
    running: 'success',
    sleeping: 'info',
    stopped: 'danger',
    zombie: 'warning'
  }
  return statusMap[status] || 'info'
}

// 获取系统健康信息
const fetchHealthInfo = async () => {
  try {
    const res = await api.get('/api/health')
    const metrics = res.data.metrics || {}

    // 优先使用后端直接返回的值，否则计算
    const memPercent = metrics.memory_percent || 0
    const memTotal = metrics.memory_total_mb || 0
    const memUsed = metrics.memory_used_mb || 0
    const memAvailable = metrics.memory_available_mb || 0

    const diskPercent = metrics.disk_percent || 0
    const diskTotal = metrics.disk_total_gb || 0
    const diskUsed = metrics.disk_used_gb || 0
    const diskFree = metrics.disk_free_gb || 0

    // 适配后端返回的数据结构
    systemInfo.value = {
      cpu_percent: metrics.cpu_percent || 0,
      cpu_count: metrics.cpu_count || 1,
      load_avg: metrics.load_avg || null,
      platform: metrics.platform || 'Unknown',
      hostname: metrics.hostname || '',
      memory_percent: memPercent,
      memory_used: memUsed * 1024 * 1024, // MB 转换为 bytes
      memory_total: memTotal * 1024 * 1024, // MB 转换为 bytes
      memory_available_mb: memAvailable,
      disk_percent: diskPercent,
      disk_used: diskUsed * 1024 * 1024 * 1024, // GB 转换为 bytes
      disk_total: diskTotal * 1024 * 1024 * 1024, // GB 转换为 bytes
      disk_free_gb: diskFree,
      uptime: metrics.uptime || '-',
      uptime_seconds: metrics.uptime_seconds || 0,
      process: metrics.process || {}
    }
    lastUpdateTime.value = new Date().toLocaleString('zh-CN')
  } catch (error) {
    console.error('获取系统健康信息失败:', error)
    ElMessage.error('获取系统信息失败')
  }
}

// 获取 WebSocket 状态
const fetchWsStatus = async () => {
  try {
    const res = await api.get('/api/ws/status')
    wsInfo.value = res.data
  } catch (error) {
    console.error('获取WebSocket状态失败:', error)
  }
}

// 获取进程信息
const fetchProcessList = async () => {
  loading.value = true
  try {
    // 后端没有独立的进程列表API，从health API获取当前进程信息
    const res = await api.get('/api/health')
    const processInfo = res.data.metrics?.process || {}
    // 构建进程列表（只有一个主进程）
    processList.value = [{
      pid: processInfo.pid || 0,
      name: 'Python Main Process',
      memory_mb: processInfo.memory_mb || 0,
      cpu_percent: 0,
      threads: processInfo.num_threads || 1,
      status: 'running'
    }]
  } catch (error) {
    console.error('获取进程信息失败:', error)
    processList.value = []
  } finally {
    loading.value = false
  }
}

// 刷新所有数据
const refreshData = async () => {
  await Promise.all([
    fetchHealthInfo(),
    fetchWsStatus()
  ])
  // 进程信息从health API获取，不需要单独请求
  await fetchProcessList()
}

onMounted(() => {
  refreshData()
  // 每10秒刷新一次
  refreshTimer = setInterval(refreshData, 10000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.system-monitor-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-overview {
  margin-bottom: 20px;
}

.status-card {
  display: flex;
  align-items: center;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 15px;
}

.status-icon {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  flex-shrink: 0;
}

.status-icon.cpu {
  background: #ecf5ff;
  color: #409eff;
}

.status-icon.memory {
  background: #f0f9ff;
  color: #00a0e9;
}

.status-icon.disk {
  background: #fef0f0;
  color: #f56c6c;
}

.status-icon.websocket {
  background: #f0f9eb;
  color: #67c23a;
}

.status-info {
  flex: 1;
  min-width: 0;
}

.status-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.status-value {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.status-detail {
  font-size: 12px;
  color: #67c23a;
}

.detail-info {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 5px 0;
}

.detail-label {
  color: #909399;
}

.detail-value {
  color: #303133;
  font-weight: 500;
}

.process-section h3 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #303133;
}

@media (max-width: 768px) {
  .status-card {
    flex-direction: column;
    text-align: center;
  }

  .status-icon {
    margin-right: 0;
    margin-bottom: 10px;
  }
}
</style>
