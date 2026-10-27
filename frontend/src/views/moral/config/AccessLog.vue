<template>
  <div class="access-log-page">
    <el-card>
      <template #header>
        <span>访问日志</span>
      </template>

      <!-- 筛选 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="用户">
          <el-input v-model="filterForm.username" placeholder="输入用户名" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="IP">
          <el-input v-model="filterForm.ip" placeholder="输入IP" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="路径">
          <el-input v-model="filterForm.path" placeholder="如 /api/moral" clearable style="width: 180px" />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 220px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="logList" v-loading="loading" stripe>
        <el-table-column prop="ts" label="时间" width="170" />
        <el-table-column prop="username" label="用户" width="110">
          <template #default="{ row }">
            <span v-if="row.username">{{ row.username }}</span>
            <span v-else class="dim">未登录</span>
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.role" size="small">{{ getRoleName(row.role) }}</el-tag>
            <span v-else class="dim">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip" label="IP" width="130" />
        <el-table-column prop="method" label="方法" width="80">
          <template #default="{ row }">
            <el-tag :type="getMethodType(row.method)" size="small" effect="plain">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status < 400 ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时" width="90">
          <template #default="{ row }">
            {{ row.duration_ms }}ms
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchLogs"
        @current-change="fetchLogs"
        class="pagination"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getAccessLogs } from '@/api/modules/moral'

const loading = ref(false)
const logList = ref([])

const filterForm = reactive({
  username: '',
  ip: '',
  path: '',
  dateRange: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const roleNames = {
  admin: '管理员',
  jiaowu: '教发部',
  xuefa: '学发部',
  cleader: '班主任',
  teacher: '教师'
}

const getRoleName = (role) => roleNames[role] || role

const getMethodType = (method) => {
  switch (method) {
    case 'GET': return 'info'
    case 'POST': return 'success'
    case 'PUT': return 'warning'
    case 'DELETE': return 'danger'
    default: return 'info'
  }
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterForm.username) params.username = filterForm.username
    if (filterForm.ip) params.ip = filterForm.ip
    if (filterForm.path) params.path = filterForm.path
    if (filterForm.dateRange && filterForm.dateRange.length === 2) {
      params.start_date = filterForm.dateRange[0]
      params.end_date = filterForm.dateRange[1]
    }

    const res = await getAccessLogs(params)
    if (res.success) {
      logList.value = res.data.items || []
      pagination.total = res.data.total || 0
    }
  } catch (error) {
    console.error('获取访问日志失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchLogs()
}

const handleReset = () => {
  filterForm.username = ''
  filterForm.ip = ''
  filterForm.path = ''
  filterForm.dateRange = null
  handleSearch()
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.access-log-page {
  padding: 20px;
}

.filter-form {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.dim {
  color: #c0c4cc;
}
</style>
