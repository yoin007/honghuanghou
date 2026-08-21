<template>
  <div class="warning-config-page">
    <el-card class="header-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>预警规则配置</span>
            <el-tag type="info" size="small" effect="plain">规则变更后次日定时任务生效</el-tag>
          </div>
          <el-button type="primary" @click="handleAdd">新增规则</el-button>
        </div>
      </template>

      <el-table :data="ruleList" v-loading="loading" stripe>
        <el-table-column prop="rule_name" label="规则名称" width="160" />
        <el-table-column label="触发类型" width="180">
          <template #default="{ row }">
            <el-tag :type="triggerTypeTag(row.trigger_type, row.trigger_value)" effect="light">
              {{ triggerTypeLabel(row.trigger_type, row.trigger_value) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发阈值" width="160">
          <template #default="{ row }">
            <span class="threshold-value">
              {{ formatThreshold(row.trigger_type, row.trigger_value) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="时间窗口" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.time_window_days" size="small" type="info" effect="plain">
              {{ row.time_window_days }} 天
            </el-tag>
            <el-tag v-else size="small" effect="plain">不限制</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="通知角色" min-width="240">
          <template #default="{ row }">
            <div class="notify-roles">
              <el-tag
                v-for="role in row.notify_roles"
                :key="role"
                size="small"
                effect="plain"
                class="role-tag"
              >
                {{ roleLabel(role) }}
              </el-tag>
              <span v-if="!row.notify_roles?.length" class="empty-text">未配置</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :active-value="1"
              :inactive-value="0"
              @change="(val) => handleToggleActive(row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right" align="center">
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
      :title="isEdit ? '编辑预警规则' : '新增预警规则'"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form :model="formData" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="规则名称" prop="rule_name">
          <el-input v-model="formData.rule_name" placeholder="如：德育分过低" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="触发类型" prop="trigger_type_selector">
          <el-radio-group v-model="formData.trigger_type_selector" @change="onTriggerTypeChange">
            <el-radio value="score_low">分数低于阈值</el-radio>
            <el-radio value="score_deduction">扣分过多</el-radio>
            <el-radio value="count_threshold">违纪次数超标</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="触发阈值" prop="trigger_value">
          <el-input-number
            v-model="formData.trigger_value"
            :min="1"
            :max="999"
            :step="1"
            :controls-position="'right'"
            style="width: 200px"
          />
          <span class="hint">{{ thresholdHint }}</span>
        </el-form-item>

        <el-form-item label="时间窗口" v-if="formData.trigger_type_selector !== 'score_low'">
          <el-input-number
            v-model="formData.time_window_days"
            :min="1"
            :max="365"
            :step="1"
            :controls-position="'right'"
            style="width: 200px"
          />
          <span class="hint">天（统计最近 N 天的累计数据）</span>
          <div class="form-hint-small">
            不限制（整个学期）将 <el-button link type="primary" size="small" @click="formData.time_window_days = 0">设为 0</el-button>
          </div>
        </el-form-item>

        <el-form-item label="通知角色" prop="notify_roles">
          <el-checkbox-group v-model="formData.notify_roles">
            <el-checkbox label="cleader">班主任</el-checkbox>
            <el-checkbox label="g_leader">年级主任</el-checkbox>
            <el-checkbox label="xuefa">学发部</el-checkbox>
            <el-checkbox label="jiaowu">教务处</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="启用状态">
          <el-switch v-model="formData.is_active" :active-value="1" :inactive-value="0" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getWarningConfigList,
  createWarningRule,
  updateWarningRule,
  deleteWarningRule,
} from '@/api/modules/moral'

const loading = ref(false)
const submitting = ref(false)
const ruleList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const formData = reactive({
  rule_name: '',
  trigger_type_selector: 'score_low',  // 前端用的选择器：score_low / score_deduction / count_threshold
  trigger_value: 60,
  time_window_days: 7,  // 0 = 不限制，>0 = 天数
  notify_roles: ['cleader'],
  is_active: 1,
  rule_id: null,
})

const formRules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  trigger_value: [{ required: true, message: '请设置触发阈值', trigger: 'change' }],
  notify_roles: [{ required: true, message: '请选择至少一个通知角色', trigger: 'change' }],
}

const thresholdHint = computed(() => {
  switch (formData.trigger_type_selector) {
    case 'score_low':
      return '分 — 当学生德育总分低于此值时触发预警'
    case 'score_deduction':
      return '分 — 当累计扣分数超过此值时触发预警'
    case 'count_threshold':
      return '次 — 当消极记录次数达到此值时触发预警'
    default:
      return ''
  }
})

// 触发类型显示
const triggerTypeLabel = (type, value) => {
  if (type === 'score_threshold') {
    return value < 0 ? '扣分过多' : '分数低于阈值'
  }
  if (type === 'count_threshold') {
    return '违纪次数超标'
  }
  return type
}

const triggerTypeTag = (type, value) => {
  if (type === 'score_threshold') {
    return value < 0 ? 'warning' : 'danger'
  }
  if (type === 'count_threshold') {
    return 'warning'
  }
  return 'info'
}

const formatThreshold = (type, value) => {
  if (type === 'score_threshold' && value < 0) {
    return `累计扣分 ≥ ${Math.abs(value)} 分`
  }
  if (type === 'score_threshold') {
    return `总分 < ${value} 分`
  }
  if (type === 'count_threshold') {
    return `≥ ${value} 次`
  }
  return value
}

const roleLabel = (role) => {
  const map = {
    cleader: '班主任',
    g_leader: '年级主任',
    xuefa: '学发部',
    jiaowu: '教务处',
  }
  return map[role] || role
}

const onTriggerTypeChange = () => {
  // 切换类型时给一个合理的默认阈值和时间窗口
  switch (formData.trigger_type_selector) {
    case 'score_low':
      if (formData.trigger_value < 0) formData.trigger_value = 60
      // 低分预警看当前总分，不需要时间窗口
      formData.time_window_days = 0
      break
    case 'score_deduction':
      if (formData.trigger_value < 0) formData.trigger_value = Math.abs(formData.trigger_value)
      if (!formData.trigger_value || formData.trigger_value === 60) formData.trigger_value = 20
      formData.time_window_days = 30
      break
    case 'count_threshold':
      if (!formData.trigger_value || formData.trigger_value > 100) formData.trigger_value = 5
      formData.time_window_days = 7
      break
  }
}

const fetchRules = async () => {
  loading.value = true
  try {
    const res = await getWarningConfigList()
    if (res.success) ruleList.value = res.data
  } catch (error) {
    ElMessage.error('获取规则列表失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  formData.rule_name = ''
  formData.trigger_type_selector = 'score_low'
  formData.trigger_value = 60
  formData.time_window_days = 0
  formData.notify_roles = ['cleader']
  formData.is_active = 1
  formData.rule_id = null
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  formData.rule_id = row.id
  formData.rule_name = row.rule_name
  formData.trigger_value = Math.abs(row.trigger_value)

  // 从数据库值反推前端选择器
  if (row.trigger_type === 'score_threshold' && row.trigger_value < 0) {
    formData.trigger_type_selector = 'score_deduction'
  } else if (row.trigger_type === 'score_threshold') {
    formData.trigger_type_selector = 'score_low'
  } else {
    formData.trigger_type_selector = 'count_threshold'
  }

  formData.notify_roles = [...(row.notify_roles || [])]
  formData.is_active = row.is_active
  formData.time_window_days = row.time_window_days || 0
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除规则"${row.rule_name}"吗？删除后该规则将不再触发预警。`,
      '确认删除',
      { type: 'warning' }
    )
    const res = await deleteWarningRule(row.id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchRules()
    }
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const handleToggleActive = async (row, val) => {
  try {
    const res = await updateWarningRule(row.id, { is_active: val })
    if (res.success) {
      ElMessage.success(val ? '已启用' : '已停用')
    } else {
      // 回滚
      row.is_active = row.is_active === 1 ? 0 : 1
      ElMessage.error('操作失败')
    }
  } catch (error) {
    row.is_active = row.is_active === 1 ? 0 : 1
    ElMessage.error('操作失败')
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  // 前端选择器 → 后端存储值
  let trigger_type
  let trigger_value

  switch (formData.trigger_type_selector) {
    case 'score_low':
      trigger_type = 'score_threshold'
      trigger_value = Math.abs(formData.trigger_value)
      break
    case 'score_deduction':
      trigger_type = 'score_threshold'
      trigger_value = -Math.abs(formData.trigger_value)
      break
    case 'count_threshold':
      trigger_type = 'count_threshold'
      trigger_value = Math.abs(formData.trigger_value)
      break
  }

  submitting.value = true
  try {
    const data = {
      rule_name: formData.rule_name,
      trigger_type,
      trigger_value,
      time_window_days: formData.time_window_days,
      notify_roles: formData.notify_roles,
      is_active: formData.is_active,
    }

    let res
    if (isEdit.value) {
      res = await updateWarningRule(formData.rule_id, data)
    } else {
      res = await createWarningRule(data)
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

onMounted(() => {
  fetchRules()
})
</script>

<style scoped>
.warning-config-page {
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

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.threshold-value {
  font-weight: 500;
  color: #303133;
}

.notify-roles {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.role-tag {
  margin: 0;
}

.empty-text {
  color: #c0c4cc;
  font-size: 13px;
}

.hint {
  color: #909399;
  font-size: 12px;
  margin-left: 10px;
}

.form-hint-small {
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
}
</style>
