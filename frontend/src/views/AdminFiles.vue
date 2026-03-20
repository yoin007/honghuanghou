<template>
  <div class="admin-files-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>文件管理 - 待处理</span>
          <div class="header-actions">
            <el-button size="small" @click="fetchFiles" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>

      <div v-if="!isLoggedIn" class="login-tip">
        <el-result
          icon="warning"
          title="需要登录"
          sub-title="请先登录教务账号以使用此功能"
        >
        </el-result>
      </div>

      <div v-else-if="!hasPermission" class="login-tip">
        <el-result
          icon="error"
          title="无权限"
          sub-title="仅教务或管理员可访问此页面"
        >
        </el-result>
      </div>

      <el-empty v-else-if="!loading && files.length === 0" description="暂无待处理文件" />

      <el-table v-else :data="files" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="uploaded_at" label="上传时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.uploaded_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="username" label="上传者" width="100" />
        <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="copies" label="份数" width="80" />
        <el-table-column prop="use_date" label="使用日期" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleDownload(row)"
            >
              下载
            </el-button>
            <el-button
              type="success"
              size="small"
              :loading="markingId === row.id"
              @click="handleMarkDone(row)"
            >
              完成
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 统计卡片 -->
    <el-card v-if="isLoggedIn && hasPermission" class="stats-card">
      <template #header>
        <span>统计信息</span>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-value">{{ stats.pending_files || 0 }}</div>
            <div class="stat-label">待处理文件</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-value">{{ stats.done_files || 0 }}</div>
            <div class="stat-label">已完成文件</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-value">{{ stats.total_files || 0 }}</div>
            <div class="stat-label">总文件数</div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { filegatherApi } from '../api/modules/filegather'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isLoggedIn)
const userRole = computed(() => authStore.role)

const hasPermission = computed(() => {
  const role = userRole.value
  return role === 'jiaowu' || role?.includes('jiaowu') || authStore.isAdmin
})

const loading = ref(false)
const files = ref([])
const markingId = ref(null)
const stats = ref({})

const formatDateTime = (dt) => {
  if (!dt) return ''
  // 将 UTC 时间转换为东八区时间
  const date = new Date(dt)
  // 加8小时转换为东八区
  date.setHours(date.getHours() + 8)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}`
}

const getStatusType = (status) => {
  switch (status) {
    case '否': return 'warning'
    case '打印中': return 'primary'
    case '是': return 'success'
    default: return 'info'
  }
}

const fetchFiles = async () => {
  if (!isLoggedIn.value || !hasPermission.value) return
  loading.value = true
  try {
    const response = await filegatherApi.getPendingFiles()
    files.value = response.data?.items || []
  } catch (error) {
    if (error?.response?.status === 403) {
      ElMessage.error('无权限访问')
    } else {
      ElMessage.error('获取文件列表失败')
    }
  } finally {
    loading.value = false
  }
}

const fetchStats = async () => {
  if (!isLoggedIn.value || !hasPermission.value) return
  try {
    const response = await filegatherApi.getStatistics()
    stats.value = response.data || {}
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

const handleDownload = async (row) => {
  try {
    const response = await filegatherApi.downloadFile(row.id)
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = row.original_name
    link.click()
    window.URL.revokeObjectURL(url)
    // 刷新列表以更新状态
    await fetchFiles()
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const handleMarkDone = async (row) => {
  try {
    await ElMessageBox.confirm('确定要将此文件标记为已完成吗？', '确认', {
      type: 'success'
    })
    markingId.value = row.id
    await filegatherApi.markDone(row.id)
    ElMessage.success('已标记为完成')
    await fetchFiles()
    await fetchStats()
  } catch (error) {
    if (error !== 'cancel') {
      const detail = error?.response?.data?.detail || '操作失败'
      ElMessage.error(detail)
    }
  } finally {
    markingId.value = null
  }
}

watch(() => authStore.isLoggedIn, (val) => {
  if (val && hasPermission.value) {
    fetchFiles()
    fetchStats()
  } else {
    files.value = []
    stats.value = {}
  }
})

onMounted(() => {
  if (isLoggedIn.value && hasPermission.value) {
    fetchFiles()
    fetchStats()
  }
})
</script>

<style scoped>
.admin-files-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.login-tip {
  text-align: center;
  padding: 40px 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stats-card {
  margin-top: 20px;
}

.stat-item {
  text-align: center;
  padding: 20px 0;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

@media screen and (max-width: 768px) {
  .admin-files-container {
    padding: 10px;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .stat-value {
    font-size: 24px;
  }
}
</style>