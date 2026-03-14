<template>
  <div class="routine-query-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>常规查询</span>
        </div>
      </template>

      <!-- 筛选区 -->
      <el-form :model="queryParams" class="filter-form" label-position="top">
        <el-row :gutter="20">
          <el-col :xs="24" :sm="8" :md="6">
            <el-form-item label="日期模式">
              <el-radio-group v-model="dateType" size="small">
                <el-radio-button value="date">按日</el-radio-button>
                <el-radio-button value="month">按月</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          
          <el-col :xs="24" :sm="16" :md="8">
            <el-form-item label="选择时间">
              <el-date-picker
                v-model="queryParams.date"
                :type="dateType"
                :placeholder="dateType === 'date' ? '选择日期' : '选择月份'"
                :format="dateType === 'date' ? 'YYYY-MM-DD' : 'YYYY-MM'"
                :value-format="dateType === 'date' ? 'YYYY-MM-DD' : 'YYYY-MM'"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="5">
            <el-form-item label="班级">
              <el-select 
                v-model="queryParams.class_code" 
                placeholder="全部班级" 
                clearable
                @change="handleClassChange"
                style="width: 100%"
              >
                <el-option
                  v-for="code in classCodes"
                  :key="code"
                  :label="code"
                  :value="code"
                />
              </el-select>
            </el-form-item>
          </el-col>

          <el-col :xs="24" :sm="12" :md="5">
            <el-form-item label="学生姓名">
              <el-select
                v-model="queryParams.name"
                placeholder="全部学生"
                clearable
                filterable
                :disabled="!queryParams.class_code"
                style="width: 100%"
              >
                <el-option
                  v-for="student in students"
                  :key="student.name"
                  :label="student.name"
                  :value="student.name"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <div class="filter-actions">
          <el-button type="primary" @click="handleQuery" :loading="loading" icon="Search">查询</el-button>
          <el-button type="success" @click="handleExport" :loading="exporting" icon="Download">导出结果</el-button>
        </div>
      </el-form>
    </el-card>

    <!-- 结果展示 -->
    <el-card class="box-card result-card">
      <el-table 
        :data="tableData" 
        style="width: 100%" 
        v-loading="loading"
        border
        stripe
      >
        <el-table-column prop="create_at" label="日期" width="120" sortable />
        <el-table-column prop="class_name" label="班级" width="100" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="style" label="类型" width="80">
          <template #default="scope">
            <el-tag :type="getStyleTag(scope.row.style)">{{ scope.row.style }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="event" label="事件" min-width="200" show-overflow-tooltip />
        <el-table-column prop="note" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column prop="recorder" label="记录人" width="100" />
      </el-table>
      
      <!-- 分页（如果API支持分页，后续可添加，目前需求未提及，假设一次性返回或由后端控制） -->
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Download } from '@element-plus/icons-vue'
import api from '../utils/api'

const dateType = ref('date')
const queryParams = ref({
  date: '',
  class_code: '',
  name: ''
})

const classCodes = ref([])
const students = ref([])
const tableData = ref([])
const loading = ref(false)
const exporting = ref(false)

// 切换日期模式时清空日期选择
watch(dateType, () => {
  queryParams.value.date = ''
})

// 获取班级列表
const fetchClassCodes = async () => {
  try {
    const response = await api.get('/api/class-codes/')
    classCodes.value = response.data['class_codes'] || []
  } catch (error) {
    console.error('Fetch class codes error:', error)
  }
}

// 班级改变时获取学生列表
const handleClassChange = async (val) => {
  queryParams.value.name = ''
  students.value = []
  if (!val) return

  try {
    const response = await api.get(`/api/students/${val}`)
    students.value = Array.isArray(response.data['students']) ? response.data['students'].map(name => ({ name })) : []
  } catch (error) {
    console.error('Fetch students error:', error)
  }
}

const getStyleTag = (style) => {
  const map = {
    '睡觉': 'success',
    '校服': 'danger',
    '其他': 'info'
  }
  return map[style] || 'info'
}

// 查询
const handleQuery = async () => {
  // 简单校验
  if (!queryParams.value.date && !queryParams.value.class_code && !queryParams.value.name) {
    ElMessage.warning('请至少选择一个查询条件')
    return
  }

  loading.value = true
  try {
    const response = await api.get('/api/get_dailies/', {
      params: {
        date: queryParams.value.date,
        class_code: queryParams.value.class_code,
        name: queryParams.value.name
      }
    })
    tableData.value = response.data
    if (tableData.value.length === 0) {
      ElMessage.info('未查询到相关记录')
    }
  } catch (error) {
    console.error('Query error:', error)
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

// 导出
const handleExport = async () => {
  if (!queryParams.value.date && !queryParams.value.class_code && !queryParams.value.name) {
    ElMessage.warning('请先选择导出条件')
    return
  }

  exporting.value = true
  try {
    const response = await api.get('/api/export_dailies/', {
      params: {
        date: queryParams.value.date,
        class_code: queryParams.value.class_code,
        name: queryParams.value.name
      },
      responseType: 'blob' // 重要：接收二进制流
    })

    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    // 尝试从header获取文件名，或者生成默认文件名
    const contentDisposition = response.headers['content-disposition']
    let fileName = '常规记录导出.xlsx'
    if (contentDisposition) {
      // Handle filename="xxx" or filename=xxx
      const match = contentDisposition.match(/filename=["']?([^;"']+)["']?/)
      if (match && match[1]) {
        fileName = decodeURIComponent(match[1])
      }
    }
    
    link.setAttribute('download', fileName)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('Export error:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

onMounted(() => {
  fetchClassCodes()
  // Set default date to today
  const today = new Date()
  const y = today.getFullYear()
  const m = String(today.getMonth() + 1).padStart(2, '0')
  const d = String(today.getDate()).padStart(2, '0')
  queryParams.value.date = `${y}-${m}-${d}`
})
</script>

<style scoped>
.routine-query-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.filter-form {
  margin-bottom: 20px;
}

.filter-actions {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
}

.result-card {
  margin-top: 20px;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .routine-query-container {
    padding: 10px;
  }
}
</style>