<template>
  <div class="escalation-rule-page">
    <el-card class="header-card">
      <template #header>
        <div class="card-header">
          <span>违纪累进规则管理</span>
          <el-button type="primary" @click="handleAdd">新增规则</el-button>
        </div>
      </template>

      <el-table :data="ruleList" v-loading="loading" stripe>
        <el-table-column prop="event_name" label="违纪事件" width="150" />
        <el-table-column prop="time_window_days" label="累计周期(天)" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.time_window_days }}天</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="处罚阶梯" min-width="300">
          <template #default="{ row }">
            <div class="rule-steps">
              <template v-if="row.rules_parsed && row.rules_parsed.rules">
                <el-tag
                  v-for="(rule, index) in row.rules_parsed.rules"
                  :key="index"
                  :type="getActionType(rule.action)"
                  class="step-tag"
                >
                  {{ rule.threshold }}次 → {{ rule.description }}
                </el-tag>
              </template>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑累进规则' : '新增累进规则'"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" label-width="120px" :rules="formRules" ref="formRef">
        <el-form-item label="违纪事件" prop="event_id">
          <el-select
            v-model="formData.event_id"
            placeholder="选择违纪事件"
            :disabled="isEdit"
          >
            <el-option
              v-for="event in configurableEvents"
              :key="event.event_id"
              :label="event.event_name"
              :value="event.event_id"
              :disabled="event.has_rule && !isEdit"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="累计周期(天)" prop="time_window_days">
          <el-input-number
            v-model="formData.time_window_days"
            :min="1"
            :max="365"
            :step="1"
          />
          <span class="hint">例：1天=当天累计，90天=一学期累计</span>
        </el-form-item>

        <el-form-item label="处罚阶梯" prop="rules">
          <div class="rules-editor">
            <el-table :data="formData.rules" size="small">
              <el-table-column prop="threshold" label="次数阈值" width="100">
                <template #default="{ row, $index }">
                  <el-input-number
                    v-model="row.threshold"
                    :min="1"
                    :max="100"
                    size="small"
                  />
                </template>
              </el-table-column>
              <el-table-column prop="action" label="处罚类型" width="150">
                <template #default="{ row, $index }">
                  <el-select v-model="row.action" size="small">
                    <el-option value="warning" label="警告" />
                    <el-option value="criticism" label="通报批评" />
                    <el-option value="demerit" label="记过" />
                    <el-option value="serious_demerit" label="严重记过" />
                  </el-select>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="描述" width="120">
                <template #default="{ row, $index }">
                  <el-input v-model="row.description" size="small" placeholder="如：警告" />
                </template>
              </el-table-column>
              <el-table-column prop="score_penalty" label="额外扣分" width="100">
                <template #default="{ row, $index }">
                  <el-input-number
                    v-model="row.score_penalty"
                    :min="-50"
                    :max="0"
                    size="small"
                  />
                </template>
              </el-table-column>
              <el-table-column label="通知对象" width="150">
                <template #default="{ row, $index }">
                  <el-checkbox-group v-model="row.notify_roles" size="small">
                    <el-checkbox label="cleader">班主任</el-checkbox>
                    <el-checkbox label="xuefa">学发部</el-checkbox>
                  </el-checkbox-group>
                </template>
              </el-table-column>
              <el-table-column label="自动处分" width="100">
                <template #default="{ row, $index }">
                  <el-switch v-model="row.auto_create_punishment" size="small" />
                </template>
              </el-table-column>
              <el-table-column label="操作" width="60">
                <template #default="{ row, $index }">
                  <el-button
                    link
                    type="danger"
                    size="small"
                    @click="removeRule($index)"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <el-button type="primary" size="small" @click="addRule" class="add-rule-btn">
              添加阶梯
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getEscalationRules,
  createEscalationRule,
  updateEscalationRule,
  deleteEscalationRule,
  getConfigurableEvents,
} from '@/api/modules/moral'

// 数据
const loading = ref(false)
const submitting = ref(false)
const ruleList = ref([])
const configurableEvents = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const formData = reactive({
  event_id: null,
  time_window_days: 90,
  rules: []
})

const formRules = {
  event_id: [{ required: true, message: '请选择违纪事件', trigger: 'change' }],
  time_window_days: [{ required: true, message: '请设置累计周期', trigger: 'change' }],
  rules: [{ required: true, message: '请添加至少一个处罚阶梯', trigger: 'change' }]
}

// 方法
const fetchRules = async () => {
  loading.value = true
  try {
    const res = await getEscalationRules()
    if (res.success) {
      ruleList.value = res.data
    }
  } catch (error) {
    ElMessage.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

const fetchConfigurableEvents = async () => {
  try {
    const res = await getConfigurableEvents()
    if (res.success) {
      configurableEvents.value = res.data
    }
  } catch (error) {
    console.error('获取可配置事件失败:', error)
  }
}

const handleAdd = () => {
  isEdit.value = false
  formData.event_id = null
  formData.time_window_days = 90
  formData.rules = [createDefaultRule()]
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  formData.event_id = row.event_id
  formData.time_window_days = row.time_window_days
  formData.rules = row.rules_parsed?.rules?.map(r => ({
    threshold: r.threshold,
    action: r.action,
    description: r.description,
    notify_roles: r.notify_roles || ['cleader'],
    score_penalty: r.score_penalty || 0,
    auto_create_punishment: r.auto_create_punishment || false,
    punishment_level: r.punishment_level || null
  })) || [createDefaultRule()]
  formData.rule_id = row.rule_id
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除事件"${row.event_name}"的累进规则吗？`,
      '确认删除',
      { type: 'warning' }
    )

    const res = await deleteEscalationRule(row.rule_id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchRules()
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (formData.rules.length === 0) {
    ElMessage.warning('请添加至少一个处罚阶梯')
    return
  }

  // 验证阈值递增
  const thresholds = formData.rules.map(r => r.threshold).sort((a, b) => a - b)
  for (let i = 0; i < thresholds.length - 1; i++) {
    if (thresholds[i] === thresholds[i + 1]) {
      ElMessage.warning('阈值不能重复')
      return
    }
  }

  submitting.value = true
  try {
    const data = {
      event_id: formData.event_id,
      time_window_days: formData.time_window_days,
      rules: formData.rules.map(r => ({
        threshold: r.threshold,
        action: r.action,
        description: r.description,
        notify_roles: r.notify_roles,
        score_penalty: r.score_penalty,
        auto_create_punishment: r.auto_create_punishment,
        punishment_level: r.punishment_level
      }))
    }

    let res
    if (isEdit.value) {
      res = await updateEscalationRule(formData.rule_id, data)
    } else {
      res = await createEscalationRule(data)
    }

    if (res.success) {
      ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchRules()
    }
  } catch (error) {
    ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}

const createDefaultRule = () => ({
  threshold: 3,
  action: 'warning',
  description: '警告',
  notify_roles: ['cleader'],
  score_penalty: 0,
  auto_create_punishment: false,
  punishment_level: null
})

const addRule = () => {
  const lastThreshold = formData.rules.length > 0
    ? Math.max(...formData.rules.map(r => r.threshold))
    : 0
  formData.rules.push({
    threshold: lastThreshold + 2,
    action: 'criticism',
    description: '通报批评',
    notify_roles: ['cleader', 'xuefa'],
    score_penalty: -5,
    auto_create_punishment: false,
    punishment_level: null
  })
}

const removeRule = (index) => {
  formData.rules.splice(index, 1)
}

const getActionType = (action) => {
  const types = {
    warning: 'warning',
    criticism: 'danger',
    demerit: 'danger',
    serious_demerit: 'danger'
  }
  return types[action] || 'info'
}

onMounted(() => {
  fetchRules()
  fetchConfigurableEvents()
})
</script>

<style scoped>
.escalation-rule-page {
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rule-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.step-tag {
  margin-right: 8px;
}

.rules-editor {
  width: 100%;
}

.add-rule-btn {
  margin-top: 10px;
}

.hint {
  color: #909399;
  font-size: 12px;
  margin-left: 10px;
}
</style>