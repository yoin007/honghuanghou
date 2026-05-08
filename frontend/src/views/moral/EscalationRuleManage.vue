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
      width="900px"
      :close-on-click-modal="false"
      modal-class="escalation-dialog-modal"
    >
      <el-form :model="formData" label-width="100px" :rules="formRules" ref="formRef">
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

        <el-form-item label="累计周期" prop="time_window_days">
          <el-input-number
            v-model="formData.time_window_days"
            :min="1"
            :max="365"
            :step="1"
          />
          <span class="hint">天（1=当天累计，90=一学期累计）</span>
        </el-form-item>

        <el-form-item label="处罚阶梯" prop="rules">
          <el-table :data="formData.rules" size="small" border>
            <el-table-column prop="threshold" label="次数" width="70" align="center">
              <template #default="{ row }">
                <el-input-number v-model="row.threshold" :min="1" :max="100" size="small" controls-position="right" />
              </template>
            </el-table-column>
            <el-table-column label="处罚类型" width="150">
              <template #default="{ row }">
                <el-select v-model="row.action" size="small" @change="onActionChange(row)">
                  <el-option
                    v-for="type in punishmentTypes"
                    :key="type.action"
                    :value="type.action"
                    :label="type.name"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" width="100">
              <template #default="{ row }">
                <el-input v-model="row.description" size="small" />
              </template>
            </el-table-column>
            <el-table-column prop="score_penalty" label="扣分" width="80" align="center">
              <template #default="{ row }">
                <el-input-number v-model="row.score_penalty" :min="-50" :max="0" size="small" controls-position="right" />
              </template>
            </el-table-column>
            <el-table-column label="通知对象" width="160">
              <template #default="{ row }">
                <el-checkbox-group v-model="row.notify_roles" size="small">
                  <el-checkbox label="cleader">班主任</el-checkbox>
                  <el-checkbox label="g_leader">年级主任</el-checkbox>
                  <el-checkbox label="xuefa">学发部</el-checkbox>
                </el-checkbox-group>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ $index }">
                <el-button link type="danger" size="small" @click="removeRule($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button type="primary" size="small" @click="addRule" style="margin-top: 10px">添加阶梯</el-button>
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
  getPunishmentTypes,
} from '@/api/modules/moral'

const loading = ref(false)
const submitting = ref(false)
const ruleList = ref([])
const configurableEvents = ref([])
const punishmentTypes = ref([])  // 处罚类型列表（从配置获取）
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

// 触发类型改变时自动填充描述
const onActionChange = (row) => {
  const type = punishmentTypes.value.find(t => t.action === row.action)
  row.description = type ? type.name : ''
}

const fetchRules = async () => {
  loading.value = true
  try {
    const res = await getEscalationRules()
    if (res.success) ruleList.value = res.data
  } catch (error) {
    ElMessage.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

const fetchConfigurableEvents = async () => {
  try {
    const res = await getConfigurableEvents()
    if (res.success) configurableEvents.value = res.data
  } catch (error) {
    console.error('获取可配置事件失败:', error)
  }
}

const fetchPunishmentTypes = async () => {
  try {
    const res = await getPunishmentTypes()
    if (res.success) punishmentTypes.value = res.data
  } catch (error) {
    console.error('获取处罚类型失败:', error)
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
    action: r.action || 'warning',
    description: r.description || '',
    notify_roles: r.notify_roles || ['cleader'],
    score_penalty: r.score_penalty || 0
  })) || [createDefaultRule()]
  formData.rule_id = row.rule_id
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除事件"${row.event_name}"的累进规则吗？`, '确认删除', { type: 'warning' })
    const res = await deleteEscalationRule(row.rule_id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchRules()
    }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
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
        score_penalty: r.score_penalty
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

const createDefaultRule = () => {
  const firstType = punishmentTypes.value[0] || { action: 'warning', name: '警告' }
  return {
    threshold: 3,
    action: firstType.action,
    description: firstType.name,
    notify_roles: ['cleader', 'g_leader'],
    score_penalty: 0
  }
}

const addRule = () => {
  const lastThreshold = formData.rules.length > 0 ? Math.max(...formData.rules.map(r => r.threshold)) : 0
  const nextType = punishmentTypes.value[Math.min(formData.rules.length, punishmentTypes.value.length - 1)]
  formData.rules.push({
    threshold: lastThreshold + 2,
    action: nextType?.action || 'criticism',
    description: nextType?.name || '通报',
    notify_roles: ['cleader', 'g_leader', 'xuefa'],
    score_penalty: -5
  })
}

const removeRule = (index) => {
  formData.rules.splice(index, 1)
}

const getActionType = (action) => {
  if (action === 'warning') return 'warning'
  if (action === 'serious_warning') return 'warning'
  if (action === 'observation') return 'danger'
  return ''  // criticism, demerit 用默认样式
}

onMounted(() => {
  fetchRules()
  fetchConfigurableEvents()
  fetchPunishmentTypes()
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

.hint {
  color: #909399;
  font-size: 12px;
  margin-left: 10px;
}
</style>

<style>
.escalation-dialog-modal .el-dialog__body {
  padding: 15px 20px;
  max-height: 70vh;
  overflow-y: auto;
}

.escalation-dialog-modal .el-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.escalation-dialog-modal .el-table .el-input-number {
  width: 100%;
}

.escalation-dialog-modal .el-table .el-select {
  width: 100%;
}
</style>