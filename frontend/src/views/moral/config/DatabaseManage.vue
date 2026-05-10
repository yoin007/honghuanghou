<template>
  <div class="database-manage-page">
    <!-- 完整性检查区域 -->
    <el-card class="integrity-card">
      <template #header>
        <div class="card-header">
          <span>数据库完整性检查</span>
          <el-button type="primary" size="small" @click="handleCheckIntegrity" :loading="checkLoading">
            执行检查
          </el-button>
        </div>
      </template>
      <div v-if="integrityResult">
        <el-alert v-if="integrityResult.status === 'ok'" type="success" title="所有表和字段完整" :closable="false" />
        <el-alert v-else :type="integrityResult.status === 'error' ? 'danger' : 'warning'" :closable="false">
          <template #title>
            发现 {{ integrityResult.missing_tables?.length || 0 }} 个缺失表，
            {{ integrityResult.missing_columns?.length || 0 }} 个表缺失字段
          </template>
          <div v-if="integrityResult.missing_tables?.length" class="missing-list">
            <p><strong>缺失表：</strong></p>
            <ul>
              <li v-for="item in integrityResult.missing_tables.slice(0, 10)" :key="item.table">
                {{ item.database }}.{{ item.table }} - {{ item.reason }}
              </li>
            </ul>
          </div>
          <div v-if="integrityResult.missing_columns?.length" class="missing-list">
            <p><strong>缺失字段：</strong></p>
            <ul>
              <li v-for="item in integrityResult.missing_columns.slice(0, 10)" :key="item.table">
                {{ item.database }}.{{ item.table }} - 缺失: {{ item.missing?.join(', ') }}
              </li>
            </ul>
          </div>
        </el-alert>
      </div>
    </el-card>

    <!-- 数据库列表区域 -->
    <el-card class="database-list-card">
      <template #header>
        <span>数据库文件列表</span>
      </template>
      <el-row :gutter="16">
        <el-col v-for="db in databases" :key="db.name" :xs="24" :sm="12" :md="8" :lg="6">
          <el-card
            class="database-card"
            :class="{ selected: selectedDb?.name === db.name }"
            @click="selectDatabase(db)"
            shadow="hover"
          >
            <div class="db-header">
              <el-icon size="24"><Coin /></el-icon>
              <span class="db-name">{{ db.name }}</span>
            </div>
            <div class="db-meta">
              <span>{{ formatSize(db.size) }}</span>
              <span>{{ db.table_count }} 个表</span>
            </div>
            <el-tag :type="db.status === 'ok' ? 'success' : 'danger'" size="small">
              {{ db.status === 'ok' ? '正常' : '异常' }}
            </el-tag>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 表详情区域 -->
    <el-card v-if="selectedDb" class="table-detail-card">
      <template #header>
        <div class="card-header">
          <span>{{ selectedDb.name }} - 表列表</span>
          <el-button
            v-if="selectedTables.length > 0"
            type="danger"
            size="small"
            @click="startClearProcess"
          >
            清空选中的 {{ selectedTables.length }} 个表
          </el-button>
        </div>
      </template>
      <el-table :data="tables" v-loading="tablesLoading" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" :selectable="canSelectRow" />
        <el-table-column prop="name" label="表名" width="200" />
        <el-table-column prop="display_name" label="中文名" width="150">
          <template #default="{ row }">
            {{ row.display_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="row_count" label="记录数" width="100" align="right" />
        <el-table-column prop="protected" label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.protected" type="danger" size="small">受保护</el-tag>
            <el-tag v-else type="success" size="small">可操作</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button
              v-if="!row.protected && row.row_count > 0"
              type="primary"
              link
              size="small"
              @click="previewClearSingle(row)"
            >
              清空
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 清空确认对话框 -->
    <el-dialog v-model="clearDialogVisible" title="清空表数据确认" width="500px">
      <div v-if="clearStep === 1">
        <el-alert type="warning" :closable="false">
          <template #title>
            <strong>第 1 步确认：以下表将被清空</strong>
          </template>
        </el-alert>
        <ul class="clear-table-list">
          <li v-for="table in tablesToClear" :key="table.name">
            {{ table.name }} ({{ table.display_name || '-' }}) - {{ table.row_count }} 条记录
          </li>
        </ul>
        <p class="warning-text">此操作不可恢复，请谨慎操作！</p>
      </div>
      <div v-if="clearStep === 2">
        <el-alert type="danger" :closable="false">
          <template #title>
            <strong>第 2 步确认：请输入"确认清空"</strong>
          </template>
        </el-alert>
        <el-input
          v-model="confirmInput"
          placeholder="请输入：确认清空"
          style="margin-top: 15px"
        />
      </div>
      <div v-if="clearStep === 3">
        <el-alert type="danger" :closable="false">
          <template #title>
            <strong>第 3 步确认：最终确认</strong>
          </template>
        </el-alert>
        <p style="margin-top: 15px; color: #f56c6c;">
          您即将清空 {{ tablesToClear.length }} 个表，共计 {{ totalRowsToDelete }} 条记录。
          <br />
          <strong>此操作将永久删除数据，无法恢复！</strong>
        </p>
      </div>
      <template #footer>
        <el-button @click="clearDialogVisible = false">取消</el-button>
        <el-button
          v-if="clearStep === 1"
          type="warning"
          @click="clearStep = 2"
        >
          继续确认
        </el-button>
        <el-button
          v-if="clearStep === 2"
          type="danger"
          :disabled="confirmInput !== '确认清空'"
          @click="clearStep = 3"
        >
          继续确认
        </el-button>
        <el-button
          v-if="clearStep === 3"
          type="danger"
          :loading="clearLoading"
          @click="executeClear"
        >
          执行清空
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Coin, FolderOpened } from '@element-plus/icons-vue'
import {
  listDatabases,
  getDatabaseTables,
  generateClearToken,
  clearTable,
  checkDatabaseIntegrity
} from '@/api/modules/database'

// 数据
const databases = ref([])
const selectedDb = ref(null)
const tables = ref([])
const selectedTables = ref([])
const tablesLoading = ref(false)
const checkLoading = ref(false)
const clearLoading = ref(false)
const integrityResult = ref(null)

// 清空流程
const clearDialogVisible = ref(false)
const clearStep = ref(1)
const tablesToClear = ref([])
const confirmInput = ref('')
const clearTokens = ref({})

// 计算属性
const totalRowsToDelete = computed(() =>
  tablesToClear.value.reduce((sum, t) => sum + t.row_count, 0)
)

// 方法
const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1024 / 1024).toFixed(1) + ' MB'
}

const canSelectRow = (row) => {
  return !row.protected && row.row_count > 0
}

const fetchDatabases = async () => {
  try {
    const res = await listDatabases()
    if (res.success) {
      databases.value = res.data
    }
  } catch (error) {
    ElMessage.error('获取数据库列表失败')
    console.error(error)
  }
}

const selectDatabase = async (db) => {
  selectedDb.value = db
  tablesLoading.value = true
  selectedTables.value = []
  try {
    const res = await getDatabaseTables(db.name)
    if (res.success) {
      tables.value = res.data
    }
  } catch (error) {
    ElMessage.error('获取表列表失败')
    console.error(error)
  } finally {
    tablesLoading.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedTables.value = selection
}

const handleCheckIntegrity = async () => {
  checkLoading.value = true
  try {
    const res = await checkDatabaseIntegrity()
    if (res.success) {
      integrityResult.value = res.data
      if (res.data.status === 'ok') {
        ElMessage.success('数据库完整性检查通过')
      } else {
        ElMessage.warning('发现数据库完整性问题')
      }
    }
  } catch (error) {
    ElMessage.error('完整性检查失败')
    console.error(error)
  } finally {
    checkLoading.value = false
  }
}

const startClearProcess = () => {
  if (selectedTables.value.length === 0) {
    ElMessage.warning('请先选择要清空的表')
    return
  }
  tablesToClear.value = selectedTables.value
  clearStep.value = 1
  confirmInput.value = ''
  clearDialogVisible.value = true
}

const previewClearSingle = (table) => {
  tablesToClear.value = [table]
  clearStep.value = 1
  confirmInput.value = ''
  clearDialogVisible.value = true
}

const executeClear = async () => {
  clearLoading.value = true
  let successCount = 0
  let failCount = 0
  const results = []

  for (const table of tablesToClear.value) {
    try {
      // 先获取确认令牌
      const tokenRes = await generateClearToken(selectedDb.value.name, table.name)
      if (!tokenRes.success) {
        failCount++
        results.push({ table: table.name, success: false, reason: '获取令牌失败' })
        continue
      }

      // 执行清空
      const clearRes = await clearTable(selectedDb.value.name, table.name, tokenRes.data.token)
      if (clearRes.success) {
        successCount++
        results.push({ table: table.name, success: true, deleted: clearRes.data.deleted_count })
      } else {
        failCount++
        results.push({ table: table.name, success: false, reason: clearRes.message })
      }
    } catch (error) {
      failCount++
      results.push({ table: table.name, success: false, reason: error.message })
    }
  }

  clearLoading.value = false
  clearDialogVisible.value = false

  if (successCount === tablesToClear.value.length) {
    ElMessage.success(`成功清空 ${successCount} 个表`)
  } else if (successCount > 0) {
    ElMessage.warning(`清空 ${successCount} 个成功，${failCount} 个失败`)
  } else {
    ElMessage.error('清空操作全部失败')
  }

  // 刷新表列表
  selectDatabase(selectedDb.value)
}

onMounted(() => {
  fetchDatabases()
})
</script>

<style scoped>
.database-manage-page {
  padding: 20px;
}

.integrity-card {
  margin-bottom: 20px;
}

.database-list-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.database-card {
  cursor: pointer;
  transition: all 0.3s;
}

.database-card.selected {
  border-color: #409eff;
  box-shadow: 0 0 10px rgba(64, 158, 255, 0.3);
}

.database-card:hover {
  transform: translateY(-2px);
}

.db-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.db-name {
  font-weight: 500;
  color: #303133;
}

.db-meta {
  display: flex;
  gap: 12px;
  color: #909399;
  font-size: 13px;
  margin-bottom: 8px;
}

.missing-list {
  margin-top: 10px;
  font-size: 13px;
}

.missing-list ul {
  margin: 5px 0;
  padding-left: 20px;
}

.clear-table-list {
  margin: 15px 0;
  padding-left: 20px;
}

.clear-table-list li {
  margin: 5px 0;
}

.warning-text {
  color: #f56c6c;
  font-weight: 500;
  margin-top: 15px;
}
</style>