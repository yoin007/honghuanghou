<template>
  <div class="admin-files-done-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>已查阅文件</span>
          <div class="header-actions">
            <el-select
              v-model="selectedMonth"
              placeholder="选择月份"
              clearable
              style="width: 150px"
              @change="handleMonthChange"
            >
              <el-option
                v-for="month in months"
                :key="month"
                :label="formatMonth(month)"
                :value="month"
              />
            </el-select>
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

      <el-empty v-else-if="!loading && files.length === 0" description="暂无已完成文件" />

      <el-table v-else :data="files" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="uploaded_at" label="上传时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.uploaded_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="done_at" label="完成时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.done_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="username" label="上传者" width="100" />
        <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="copies" label="份数" width="80" />
        <el-table-column prop="use_date" label="使用日期" width="120" />
        <el-table-column prop="note" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              @click="handleDownload(row)"
            >
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
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
const months = ref([])
const selectedMonth = ref('')

// 生成最近12个月
const generateMonths = () => {
  const now = new Date()
  const result = []
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const month = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}`
    result.push(month)
  }
  return result
}

const formatMonth = (month) => {
  if (!month || month.length !== 6) return month
  return `${month.slice(0, 4)}-${month.slice(4)}`
}

const formatDateTime = (dt) => {
  if (!dt) return ''
  return dt.replace('T', ' ').slice(0, 16)
}

const fetchFiles = async () => {
  if (!isLoggedIn.value || !hasPermission.value) return
  loading.value = true
  try {
    const response = await filegatherApi.getDoneFiles(selectedMonth.value)
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

const handleMonthChange = () => {
  fetchFiles()
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
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

watch(() => authStore.isLoggedIn, (val) => {
  if (val && hasPermission.value) {
    fetchFiles()
  } else {
    files.value = []
  }
})

onMounted(() => {
  months.value = generateMonths()
  if (isLoggedIn.value && hasPermission.value) {
    fetchFiles()
  }
})
</script>

<style scoped>
.admin-files-done-container {
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

@media screen and (max-width: 768px) {
  .admin-files-done-container {
    padding: 10px;
  }

  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>