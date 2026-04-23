<template>
  <div class="operation-log-page">
    <el-card>
      <template #header>
        <span>操作日志</span>
      </template>

      <!-- 筛选 -->
      <el-form :inline="true" class="filter-form">
        <el-form-item label="操作人">
          <el-input v-model="filterForm.operator" placeholder="输入操作人" clearable />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="filterForm.operation" placeholder="全部" clearable>
            <el-option label="新增" value="INSERT" />
            <el-option label="更新" value="UPDATE" />
            <el-option label="删除" value="DELETE" />
            <el-option label="批量新增" value="BATCH_INSERT" />
          </el-select>
        </el-form-item>
        <el-form-item label="操作表">
          <el-select v-model="filterForm.table_name" placeholder="全部" clearable>
            <el-option label="学生" value="student" />
            <el-option label="班级" value="class" />
            <el-option label="日常记录" value="daily_record" />
            <el-option label="校级事件" value="school_event" />
            <el-option label="处分" value="punishment" />
            <el-option label="任务" value="grade_moral_task" />
            <el-option label="系统配置" value="moral_config" />
          </el-select>
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
        <el-table-column prop="operator" label="操作人" width="100" />
        <el-table-column prop="operator_role" label="角色" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ getRoleName(row.operator_role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operation" label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getOperationType(row.operation)" size="small">
              {{ getOperationName(row.operation) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="table_name" label="操作表" width="120">
          <template #default="{ row }">
            {{ getTableName(row.table_name) }}
          </template>
        </el-table-column>
        <el-table-column prop="new_data" label="操作内容" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.new_data">{{ formatData(row.new_data) }}</span>
            <span v-else-if="row.old_data">删除: {{ formatData(row.old_data) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="ip_address" label="IP地址" width="120" />
        <el-table-column prop="created_at" label="操作时间" width="160" />
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
import { ElMessage } from 'element-plus'
import { getOperationLogs } from '@/api/modules/moral'

const loading = ref(false)
const logList = ref([])

const filterForm = reactive({
  operator: '',
  operation: null,
  table_name: null,
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

const tableNames = {
  student: '学生',
  class: '班级',
  daily_record: '日常记录',
  school_event: '校级事件',
  punishment: '处分',
  grade_moral_task: '德育任务',
  moral_config: '系统配置',
  api_permission_config: 'API权限'
}

const operationNames = {
  INSERT: '新增',
  UPDATE: '更新',
  DELETE: '删除',
  BATCH_INSERT: '批量新增',
  INIT: '初始化'
}

const getRoleName = (role) => roleNames[role] || role
const getTableName = (table) => tableNames[table] || table
const getOperationName = (op) => operationNames[op] || op

const getOperationType = (op) => {
  switch (op) {
    case 'INSERT': return 'success'
    case 'UPDATE': return 'warning'
    case 'DELETE': return 'danger'
    case 'BATCH_INSERT': return 'primary'
    default: return 'info'
  }
}

const formatData = (dataStr) => {
  try {
    const data = JSON.parse(dataStr)
    if (typeof data === 'object') {
      // 提取关键信息
      if (data.student_id && data.name) return `${data.student_id} - ${data.name}`
      if (data.class_name) return data.class_name
      if (data.success !== undefined) return `成功 ${data.success} 条`
      if (data.api_path) return data.api_path
      return Object.entries(data).slice(0, 3).map(([k, v]) => `${k}: ${v}`).join(', ')
    }
    return dataStr
  } catch {
    return dataStr
  }
}

const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterForm.operator) params.operator = filterForm.operator
    if (filterForm.operation) params.operation = filterForm.operation
    if (filterForm.table_name) params.table_name = filterForm.table_name
    if (filterForm.dateRange && filterForm.dateRange.length === 2) {
      params.start_date = filterForm.dateRange[0]
      params.end_date = filterForm.dateRange[1]
    }

    const res = await getOperationLogs(params)
    if (res.success) {
      logList.value = res.data.items || []
      pagination.total = res.data.total || 0
    }
  } catch (error) {
    console.error('获取操作日志失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchLogs()
}

const handleReset = () => {
  filterForm.operator = ''
  filterForm.operation = null
  filterForm.table_name = null
  filterForm.dateRange = null
  handleSearch()
}

onMounted(() => {
  fetchLogs()
})
</script>

<style scoped>
.operation-log-page {
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
</style>