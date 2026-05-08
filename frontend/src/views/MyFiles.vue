<template>
  <div class="my-files-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>我的文件</span>
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
                :label="formatYearMonth(month)"
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
          sub-title="请先登录教师账号以使用此功能"
        >
        </el-result>
      </div>

      <el-empty v-else-if="!loading && files.length === 0" description="暂无文件记录" />

      <el-table v-else :data="files" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="uploaded_at" label="上传时间" width="160">
          <template #default="{ row }">
            {{ formatDateTimeSimple(row.uploaded_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="copies" label="份数" width="80" />
        <el-table-column prop="use_date" label="使用日期" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getFileStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="note" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === '否'"
              type="danger"
              size="small"
              :loading="deletingId === row.id"
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { filegatherApi } from '../api/modules/filegather'
import { useAuthStore } from '../stores/auth'
import { formatDateTimeSimple, formatYearMonth, generateRecentMonths } from '@/utils/time'
import {
  getFileErrorMessage,
  getFileListFromResponse,
  getFileStatusType
} from '@/utils/filegather'

const authStore = useAuthStore()
const isLoggedIn = computed(() => authStore.isLoggedIn)

const loading = ref(false)
const files = ref([])
const months = ref([])
const selectedMonth = ref('')
const deletingId = ref(null)

const fetchFiles = async () => {
  if (!isLoggedIn.value) return
  loading.value = true
  try {
    const response = await filegatherApi.getMyFiles(selectedMonth.value)
    files.value = getFileListFromResponse(response)
  } catch (error) {
    ElMessage.error('获取文件列表失败')
  } finally {
    loading.value = false
  }
}

const handleMonthChange = () => {
  fetchFiles()
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此文件吗？', '确认删除', {
      type: 'warning'
    })
    deletingId.value = row.id
    await filegatherApi.deleteFile(row.id)
    ElMessage.success('删除成功')
    await fetchFiles()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(getFileErrorMessage(error, '删除失败'))
    }
  } finally {
    deletingId.value = null
  }
}

watch(() => authStore.isLoggedIn, (val) => {
  if (val) {
    fetchFiles()
  } else {
    files.value = []
  }
})

onMounted(() => {
  months.value = generateRecentMonths()
  if (isLoggedIn.value) {
    fetchFiles()
  }
})
</script>

<style scoped>
.my-files-container {
  padding: 20px;
  max-width: 1200px;
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
  .my-files-container {
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
