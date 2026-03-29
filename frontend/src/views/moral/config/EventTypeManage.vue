<template>
  <div class="event-type-manage-page">
    <el-card>
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 日常事件类型 -->
        <el-tab-pane label="日常事件类型" name="daily">
          <div class="tab-header">
            <el-radio-group v-model="dailyFilter.eventType" @change="fetchDailyTypes">
              <el-radio-button :label="null">全部</el-radio-button>
              <el-radio-button :label="1">积极事件</el-radio-button>
              <el-radio-button :label="2">消极事件</el-radio-button>
            </el-radio-group>
            <div>
              <el-button @click="downloadTemplate('daily')">下载模板</el-button>
              <el-button type="warning" @click="handleImport('daily')">批量导入</el-button>
              <el-button type="primary" @click="handleAddDaily">新增事件类型</el-button>
            </div>
          </div>

          <el-table :data="dailyTypes" v-loading="dailyLoading" stripe>
            <el-table-column prop="event_name" label="事件名称" width="200" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.event_type === 1 ? 'success' : 'danger'">
                  {{ row.event_type === 1 ? '积极' : '消极' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="分值" width="100">
              <template #default="{ row }">
                <span :class="row.score > 0 ? 'score-positive' : 'score-negative'">
                  {{ row.score > 0 ? '+' : '' }}{{ row.score }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleEditDaily(row)">编辑</el-button>
                <el-button
                  link
                  :type="row.is_active ? 'warning' : 'success'"
                  @click="handleToggleDaily(row)"
                >
                  {{ row.is_active ? '禁用' : '启用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- 校级事件类型 -->
        <el-tab-pane label="校级事件类型" name="school">
          <div class="tab-header">
            <el-radio-group v-model="schoolFilter.eventType" @change="fetchSchoolTypes">
              <el-radio-button :label="null">全部</el-radio-button>
              <el-radio-button :label="1">荣誉奖励</el-radio-button>
              <el-radio-button :label="2">违纪处分</el-radio-button>
            </el-radio-group>
            <div>
              <el-button @click="downloadTemplate('school')">下载模板</el-button>
              <el-button type="warning" @click="handleImport('school')">批量导入</el-button>
              <el-button type="primary" @click="handleAddSchool">新增事件类型</el-button>
            </div>
          </div>

          <el-table :data="schoolTypes" v-loading="schoolLoading" stripe>
            <el-table-column prop="event_name" label="事件名称" width="200" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.event_type === 1 ? 'success' : 'danger'">
                  {{ row.event_type === 1 ? '荣誉' : '处分' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="event_level" label="级别" width="100" />
            <el-table-column prop="score" label="分值" width="100">
              <template #default="{ row }">
                <span :class="row.score > 0 ? 'score-positive' : 'score-negative'">
                  {{ row.score > 0 ? '+' : '' }}{{ row.score }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleEditSchool(row)">编辑</el-button>
                <el-button
                  link
                  :type="row.is_active ? 'warning' : 'success'"
                  @click="handleToggleSchool(row)"
                >
                  {{ row.is_active ? '禁用' : '启用' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 日常事件类型对话框 -->
    <el-dialog v-model="dailyDialogVisible" :title="dailyDialogTitle" width="500px">
      <el-form :model="dailyForm" :rules="dailyRules" ref="dailyFormRef" label-width="100px">
        <el-form-item label="事件名称" prop="event_name">
          <el-input v-model="dailyForm.event_name" placeholder="输入事件名称" maxlength="50" />
        </el-form-item>
        <el-form-item label="事件类型" prop="event_type">
          <el-radio-group v-model="dailyForm.event_type">
            <el-radio :label="1">积极事件</el-radio>
            <el-radio :label="2">消极事件</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="分值" prop="score">
          <el-input-number v-model="dailyForm.score" :min="1" :max="100" />
          <span class="form-hint">自动按事件类型设置正负</span>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dailyForm.description" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dailyDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitDaily">确定</el-button>
      </template>
    </el-dialog>

    <!-- 校级事件类型对话框 -->
    <el-dialog v-model="schoolDialogVisible" :title="schoolDialogTitle" width="500px">
      <el-form :model="schoolForm" :rules="schoolRules" ref="schoolFormRef" label-width="100px">
        <el-form-item label="事件名称" prop="event_name">
          <el-input v-model="schoolForm.event_name" placeholder="输入事件名称" maxlength="50" />
        </el-form-item>
        <el-form-item label="事件类型" prop="event_type">
          <el-radio-group v-model="schoolForm.event_type">
            <el-radio :label="1">荣誉奖励</el-radio>
            <el-radio :label="2">违纪处分</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="事件级别" prop="event_level">
          <el-select v-model="schoolForm.event_level" placeholder="选择级别" style="width: 100%">
            <el-option label="国家级" value="国家级" />
            <el-option label="省级" value="省级" />
            <el-option label="市级" value="市级" />
            <el-option label="校级" value="校级" />
          </el-select>
        </el-form-item>
        <el-form-item label="分值" prop="score">
          <el-input-number v-model="schoolForm.score" :min="1" :max="100" />
          <span class="form-hint">自动按事件类型设置正负</span>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="schoolForm.description" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="schoolDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitSchool">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="批量导入" width="600px">
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 15px"
      >
        <template #title>
          请先下载模板，按模板格式填写数据后粘贴到下方文本框
        </template>
      </el-alert>

      <el-input
        v-model="importData"
        type="textarea"
        :rows="10"
        placeholder="粘贴CSV数据，格式：
事件名称,事件类型,分值,描述
拾金不昧,积极,3,主动上交拾得物品"
      />

      <el-alert
        v-if="importResult"
        :type="importResult.error_count > 0 ? 'warning' : 'success'"
        :closable="false"
        style="margin-top: 15px"
      >
        <template #title>
          导入结果：成功 {{ importResult.success_count }} 条，跳过 {{ importResult.skip_count }} 条
        </template>
        <div v-if="importResult.errors && importResult.errors.length > 0">
          <div v-for="(err, idx) in importResult.errors" :key="idx">{{ err }}</div>
        </div>
      </el-alert>

      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="importLoading" @click="handleImportSubmit">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getDailyEventTypes,
  createDailyEventType,
  updateDailyEventType,
  deleteDailyEventType,
  batchImportDailyEventTypes,
  getSchoolEventTypes,
  createSchoolEventType,
  updateSchoolEventType,
  deleteSchoolEventType,
  batchImportSchoolEventTypes
} from '@/api/modules/moral'

// Tab
const activeTab = ref('daily')

// 日常事件类型
const dailyLoading = ref(false)
const dailyTypes = ref([])
const dailyFilter = reactive({ eventType: null })
const dailyDialogVisible = ref(false)
const dailyDialogTitle = computed(() => dailyForm.event_id ? '编辑事件类型' : '新增事件类型')
const dailyFormRef = ref(null)
const dailyForm = reactive({
  event_id: null,
  event_name: '',
  event_type: 1,
  score: 5,
  description: ''
})
const dailyRules = {
  event_name: [{ required: true, message: '请输入事件名称', trigger: 'blur' }],
  event_type: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  score: [{ required: true, message: '请输入分值', trigger: 'blur' }]
}

// 校级事件类型
const schoolLoading = ref(false)
const schoolTypes = ref([])
const schoolFilter = reactive({ eventType: null })
const schoolDialogVisible = ref(false)
const schoolDialogTitle = computed(() => schoolForm.event_id ? '编辑事件类型' : '新增事件类型')
const schoolFormRef = ref(null)
const schoolForm = reactive({
  event_id: null,
  event_name: '',
  event_type: 1,
  event_level: '校级',
  score: 10,
  description: ''
})
const schoolRules = {
  event_name: [{ required: true, message: '请输入事件名称', trigger: 'blur' }],
  event_type: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  event_level: [{ required: true, message: '请选择事件级别', trigger: 'change' }],
  score: [{ required: true, message: '请输入分值', trigger: 'blur' }]
}

// 批量导入
const importDialogVisible = ref(false)
const importLoading = ref(false)
const importType = ref('daily') // 'daily' or 'school'
const importData = ref('')
const importResult = ref(null)

// 方法
const fetchDailyTypes = async () => {
  dailyLoading.value = true
  try {
    const params = { is_active: null }
    if (dailyFilter.eventType) params.event_type = dailyFilter.eventType
    const res = await getDailyEventTypes(params)
    if (res.success) dailyTypes.value = res.data
  } catch (error) {
    console.error('获取日常事件类型失败:', error)
  } finally {
    dailyLoading.value = false
  }
}

const fetchSchoolTypes = async () => {
  schoolLoading.value = true
  try {
    const params = { is_active: null }
    if (schoolFilter.eventType) params.event_type = schoolFilter.eventType
    const res = await getSchoolEventTypes(params)
    if (res.success) schoolTypes.value = res.data
  } catch (error) {
    console.error('获取校级事件类型失败:', error)
  } finally {
    schoolLoading.value = false
  }
}

const handleTabChange = (tab) => {
  if (tab === 'daily') fetchDailyTypes()
  else fetchSchoolTypes()
}

// 日常事件类型操作
const handleAddDaily = () => {
  Object.assign(dailyForm, {
    event_id: null,
    event_name: '',
    event_type: 1,
    score: 5,
    description: ''
  })
  dailyDialogVisible.value = true
}

const handleEditDaily = (row) => {
  Object.assign(dailyForm, {
    event_id: row.event_id,
    event_name: row.event_name,
    event_type: row.event_type,
    score: Math.abs(row.score),
    description: row.description
  })
  dailyDialogVisible.value = true
}

const handleSubmitDaily = async () => {
  try {
    await dailyFormRef.value.validate()
    const data = {
      event_name: dailyForm.event_name,
      event_type: dailyForm.event_type,
      score: dailyForm.score,
      description: dailyForm.description
    }

    let res
    if (dailyForm.event_id) {
      res = await updateDailyEventType(dailyForm.event_id, data)
    } else {
      res = await createDailyEventType(data)
    }

    if (res.success) {
      ElMessage.success(dailyForm.event_id ? '更新成功' : '创建成功')
      dailyDialogVisible.value = false
      fetchDailyTypes()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

const handleToggleDaily = async (row) => {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}该事件类型吗？`, '提示', { type: 'warning' })
    const res = await updateDailyEventType(row.event_id, { is_active: row.is_active ? 0 : 1 })
    if (res.success) {
      ElMessage.success(`${action}成功`)
      fetchDailyTypes()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('操作失败:', error)
  }
}

// 校级事件类型操作
const handleAddSchool = () => {
  Object.assign(schoolForm, {
    event_id: null,
    event_name: '',
    event_type: 1,
    event_level: '校级',
    score: 10,
    description: ''
  })
  schoolDialogVisible.value = true
}

const handleEditSchool = (row) => {
  Object.assign(schoolForm, {
    event_id: row.event_id,
    event_name: row.event_name,
    event_type: row.event_type,
    event_level: row.event_level,
    score: Math.abs(row.score),
    description: row.description
  })
  schoolDialogVisible.value = true
}

const handleSubmitSchool = async () => {
  try {
    await schoolFormRef.value.validate()
    const data = {
      event_name: schoolForm.event_name,
      event_type: schoolForm.event_type,
      event_level: schoolForm.event_level,
      score: schoolForm.score,
      description: schoolForm.description
    }

    let res
    if (schoolForm.event_id) {
      res = await updateSchoolEventType(schoolForm.event_id, data)
    } else {
      res = await createSchoolEventType(data)
    }

    if (res.success) {
      ElMessage.success(schoolForm.event_id ? '更新成功' : '创建成功')
      schoolDialogVisible.value = false
      fetchSchoolTypes()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

const handleToggleSchool = async (row) => {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}该事件类型吗？`, '提示', { type: 'warning' })
    const res = await updateSchoolEventType(row.event_id, { is_active: row.is_active ? 0 : 1 })
    if (res.success) {
      ElMessage.success(`${action}成功`)
      fetchSchoolTypes()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('操作失败:', error)
  }
}

// 模板下载
const downloadTemplate = (type) => {
  const templates = {
    daily: '/templates/daily_events.csv',
    school: '/templates/school_events.csv'
  }
  const link = document.createElement('a')
  link.href = templates[type]
  link.download = type === 'daily' ? '日常事件类型模板.csv' : '校级事件类型模板.csv'
  link.click()
  ElMessage.success('模板下载中...')
}

// 批量导入
const handleImport = (type) => {
  importType.value = type
  importData.value = ''
  importResult.value = null
  importDialogVisible.value = true
}

const parseCSV = (csvText, type) => {
  const lines = csvText.trim().split('\n')
  const items = []

  // 跳过标题行
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map(col => col.trim())
    if (cols.length < 3) continue

    if (type === 'daily') {
      items.push({
        event_name: cols[0],
        event_type: cols[1],
        score: parseInt(cols[2]) || 0,
        description: cols[3] || ''
      })
    } else {
      items.push({
        event_name: cols[0],
        event_type: cols[1],
        event_level: cols[2] || '校级',
        score: parseInt(cols[3]) || 0,
        description: cols[4] || ''
      })
    }
  }
  return items
}

const handleImportSubmit = async () => {
  if (!importData.value.trim()) {
    ElMessage.warning('请粘贴CSV数据')
    return
  }

  importLoading.value = true
  importResult.value = null

  try {
    const items = parseCSV(importData.value, importType.value)
    if (items.length === 0) {
      ElMessage.warning('未解析到有效数据，请检查格式')
      return
    }

    let res
    if (importType.value === 'daily') {
      res = await batchImportDailyEventTypes(items)
    } else {
      res = await batchImportSchoolEventTypes(items)
    }

    if (res.success) {
      importResult.value = res.data
      ElMessage.success(res.message)
      if (importType.value === 'daily') {
        fetchDailyTypes()
      } else {
        fetchSchoolTypes()
      }
    }
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败，请检查数据格式')
  } finally {
    importLoading.value = false
  }
}

// 生命周期
onMounted(() => {
  fetchDailyTypes()
})
</script>

<style scoped>
.event-type-manage-page {
  padding: 20px;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.score-positive {
  color: #67c23a;
  font-weight: bold;
}

.score-negative {
  color: #f56c6c;
  font-weight: bold;
}

.form-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}
</style>