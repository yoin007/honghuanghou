<template>
  <div class="api-permission-page">
    <aside class="module-panel">
      <div class="panel-title">
        <span>权限模块</span>
        <el-button type="primary" :icon="Plus" circle @click="handleAddModule" />
      </div>
      <el-scrollbar class="module-list">
        <button
          class="module-item"
          :class="{ active: !selectedModuleId }"
          type="button"
          @click="selectModule(null)"
        >
          <span>全部API</span>
          <small>{{ permissions.length }}</small>
        </button>
        <button
          v-for="module in modules"
          :key="module.id"
          class="module-item"
          :class="{ active: selectedModuleId === module.id }"
          type="button"
          @click="selectModule(module.id)"
        >
          <span>{{ module.module_name }}</span>
          <small>{{ module.api_count || 0 }}</small>
        </button>
      </el-scrollbar>
    </aside>

    <section class="api-panel">
      <el-card>
        <template #header>
          <div class="card-header">
            <div>
              <span>API权限管理</span>
              <small v-if="selectedModule" class="header-subtitle">{{ selectedModule.module_name }}</small>
            </div>
            <div class="header-actions">
              <el-button @click="handleEditModule" :disabled="!selectedModule">编辑模块</el-button>
              <el-button @click="handleApplyModule" :disabled="!selectedModule">应用模块权限</el-button>
              <el-button @click="handleSyncLegacy" :loading="syncLoading">同步旧配置</el-button>
              <el-button type="primary" @click="handleInit" :loading="initLoading">初始化默认配置</el-button>
              <el-button type="success" @click="handleAdd">新增API</el-button>
            </div>
          </div>
        </template>

        <el-alert
          title="默认策略为角色和最低等级同时满足；公开API会跳过鉴权；继承模块的API会使用模块上的角色、等级和策略。"
          type="info"
          show-icon
          :closable="false"
          class="policy-alert"
        />

        <el-table :data="filteredPermissions" v-loading="loading" stripe>
          <el-table-column prop="api_name" label="API名称" min-width="150" />
          <el-table-column prop="api_path" label="API路径" min-width="230" />
          <el-table-column prop="module_name" label="模块" width="110">
            <template #default="{ row }">{{ row.module_name || row.api_group }}</template>
          </el-table-column>
          <el-table-column label="方法" width="80">
            <template #default="{ row }">{{ row.http_method || '*' }}</template>
          </el-table-column>
          <el-table-column label="匹配" width="90">
            <template #default="{ row }">{{ getMatchName(row.match_type) }}</template>
          </el-table-column>
          <el-table-column label="生效策略" min-width="280">
            <template #default="{ row }">
              <div class="policy-cell">
                <el-tag v-if="row.is_public" type="success" size="small">公开</el-tag>
                <el-tag v-else-if="row.inherit_from_module" type="warning" size="small">继承模块</el-tag>
                <el-tag v-else size="small">单独配置</el-tag>
                <span>{{ getPolicyName(row.effective_policy?.policy_mode || row.policy_mode) }}</span>
                <span>等级 {{ row.effective_policy?.min_level ?? row.min_level ?? 0 }}</span>
                <span class="role-list">
                  {{ formatRoles(row.effective_policy?.allowed_roles || row.allowed_roles) }}
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'">
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <el-dialog v-model="apiDialogVisible" :title="apiDialogTitle" width="640px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="116px">
        <el-form-item label="API路径" prop="api_path">
          <el-input v-model="form.api_path" placeholder="/api/moral/xxx 或 /api/moral/xxx/{id}" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="API名称" prop="api_name">
          <el-input v-model="form.api_name" placeholder="如：获取日常记录" />
        </el-form-item>
        <el-form-item label="所属模块" prop="module_id">
          <el-select v-model="form.module_id" placeholder="选择模块" filterable @change="syncApiGroup">
            <el-option v-for="module in modules" :key="module.id" :label="module.module_name" :value="module.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="API分组" prop="api_group">
          <el-input v-model="form.api_group" placeholder="兼容旧分组，默认同步模块名称" />
        </el-form-item>
        <el-form-item label="HTTP方法">
          <el-select v-model="form.http_method">
            <el-option label="全部" value="*" />
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
          </el-select>
        </el-form-item>
        <el-form-item label="路径匹配">
          <el-radio-group v-model="form.match_type">
            <el-radio-button label="exact">精确</el-radio-button>
            <el-radio-button label="prefix">前缀</el-radio-button>
            <el-radio-button label="pattern">参数模式</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="特殊设置">
          <el-checkbox v-model="form.is_public" :true-label="1" :false-label="0">公开API，无需鉴权</el-checkbox>
          <el-checkbox v-model="form.inherit_from_module" :true-label="1" :false-label="0">继承模块权限</el-checkbox>
          <el-checkbox v-model="form.enforce_backend" :true-label="1" :false-label="0">参与后端鉴权</el-checkbox>
        </el-form-item>
        <el-form-item label="数据范围">
          <el-input
            v-model="form.data_scope_rules_text"
            type="textarea"
            :rows="5"
            placeholder='{"teacher":["own_created"],"cleader":["own_created","own_class"],"xuefa":["all"]}'
          />
          <div class="scope-help">
            控制查询、编辑、删除时能操作哪些已有数据。可选值：all=全部，own_created=自己创建，own_class=自己班级，teaching_classes=任教班级。例：班主任查看自己创建+本班，填 {"cleader":["own_created","own_class"]}。
          </div>
        </el-form-item>
        <el-form-item label="目标范围">
          <el-input
            v-model="form.target_scope_rules_text"
            type="textarea"
            :rows="3"
            placeholder='{"teacher":["all_students"],"cleader":["all_students"]}'
          />
          <div class="scope-help">
            控制新增、录入时能选择哪些学生。可选值：all_students=全校学生，own_class=自己班级，teaching_classes=任教班级。若填 {"teacher":["teaching_classes"]}，有维护任教班级时按任教班级限制；未维护任教班级时默认全校。
          </div>
        </el-form-item>
        <template v-if="!form.inherit_from_module && !form.is_public">
          <el-form-item label="允许角色" prop="allowed_roles">
            <el-checkbox-group v-model="form.allowed_roles">
              <el-checkbox v-for="role in roleOptions" :key="role.value" :label="role.value">{{ role.label }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="最低等级">
            <el-input-number v-model="form.min_level" :min="0" :max="100" :step="10" />
          </el-form-item>
          <el-form-item label="鉴权策略">
            <el-select v-model="form.policy_mode">
              <el-option v-for="item in policyOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="是否启用" v-if="isEdit">
          <el-switch v-model="form.is_active" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="apiDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="moduleDialogVisible" :title="moduleDialogTitle" width="560px">
      <el-form :model="moduleForm" :rules="moduleRules" ref="moduleFormRef" label-width="116px">
        <el-form-item label="模块标识" prop="module_key">
          <el-input v-model="moduleForm.module_key" placeholder="如 moral_daily" />
        </el-form-item>
        <el-form-item label="模块名称" prop="module_name">
          <el-input v-model="moduleForm.module_name" placeholder="如 日常表现" />
        </el-form-item>
        <el-form-item label="允许角色">
          <el-checkbox-group v-model="moduleForm.allowed_roles">
            <el-checkbox v-for="role in roleOptions" :key="role.value" :label="role.value">{{ role.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="最低等级">
          <el-input-number v-model="moduleForm.min_level" :min="0" :max="100" :step="10" />
        </el-form-item>
        <el-form-item label="鉴权策略">
          <el-select v-model="moduleForm.policy_mode">
            <el-option v-for="item in policyOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="moduleForm.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="是否启用" v-if="isModuleEdit">
          <el-switch v-model="moduleForm.is_active" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="moduleForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleModuleSubmit" :loading="moduleSubmitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getApiPermissions,
  createApiPermission,
  updateApiPermission,
  deleteApiPermission,
  initApiPermissions,
  getApiPermissionModules,
  createApiPermissionModule,
  updateApiPermissionModule,
  applyApiPermissionModule,
  syncLegacyApiPermissions
} from '@/api/modules/moral'

const loading = ref(false)
const initLoading = ref(false)
const syncLoading = ref(false)
const submitLoading = ref(false)
const moduleSubmitLoading = ref(false)
const permissions = ref([])
const modules = ref([])
const selectedModuleId = ref(null)

const apiDialogVisible = ref(false)
const moduleDialogVisible = ref(false)
const isEdit = ref(false)
const isModuleEdit = ref(false)
const apiDialogTitle = computed(() => isEdit.value ? '编辑API权限' : '新增API权限')
const moduleDialogTitle = computed(() => isModuleEdit.value ? '编辑权限模块' : '新增权限模块')
const formRef = ref(null)
const moduleFormRef = ref(null)

const selectedModule = computed(() => modules.value.find(item => item.id === selectedModuleId.value))
const filteredPermissions = computed(() => {
  if (!selectedModuleId.value) return permissions.value
  return permissions.value.filter(item => item.module_id === selectedModuleId.value)
})

const roleOptions = [
  { value: 'admin', label: '管理员' },
  { value: 'jiaowu', label: '教发部' },
  { value: 'xuefa', label: '学发部' },
  { value: 'cleader', label: '班主任' },
  { value: 'teacher', label: '教师' },
  { value: 'student', label: '学生' },
  { value: 'parent', label: '家长' }
]

const policyOptions = [
  { value: 'role_and_level', label: '角色和等级同时满足' },
  { value: 'role_or_level', label: '角色或等级满足即可' },
  { value: 'role_only', label: '只看角色' },
  { value: 'level_only', label: '只看等级' }
]

const roleNames = Object.fromEntries(roleOptions.map(item => [item.value, item.label]))
const policyNames = Object.fromEntries(policyOptions.map(item => [item.value, item.label]))
const matchNames = { exact: '精确', prefix: '前缀', pattern: '参数' }

const form = reactive({
  id: null,
  api_path: '',
  api_name: '',
  api_group: '',
  module_id: null,
  http_method: '*',
  match_type: 'exact',
  allowed_roles: ['admin'],
  min_level: 0,
  policy_mode: 'role_and_level',
  inherit_from_module: 0,
  is_public: 0,
  enforce_backend: 1,
  data_scope_rules_text: '',
  target_scope_rules_text: '',
  description: '',
  is_active: 1
})

const moduleForm = reactive({
  id: null,
  module_key: '',
  module_name: '',
  allowed_roles: ['admin'],
  min_level: 0,
  policy_mode: 'role_and_level',
  sort_order: 0,
  description: '',
  is_active: 1
})

const rules = {
  api_path: [{ required: true, message: '请输入API路径', trigger: 'blur' }],
  api_name: [{ required: true, message: '请输入API名称', trigger: 'blur' }],
  api_group: [{ required: true, message: '请输入API分组', trigger: 'blur' }]
}

const moduleRules = {
  module_key: [{ required: true, message: '请输入模块标识', trigger: 'blur' }],
  module_name: [{ required: true, message: '请输入模块名称', trigger: 'blur' }]
}

const formatRoles = (roles = []) => {
  if (!roles.length) return '不限角色'
  return roles.map(role => roleNames[role] || role).join('、')
}

const getPolicyName = (policy) => policy === 'public' ? '公开' : (policyNames[policy] || policy)
const getMatchName = (matchType) => matchNames[matchType] || '精确'

const stringifyRules = (rules) => {
  if (!rules || Object.keys(rules).length === 0) return ''
  return JSON.stringify(rules, null, 2)
}

const parseRulesText = (text, label) => {
  if (!text || !text.trim()) return {}
  try {
    const parsed = JSON.parse(text)
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error(`${label}必须是对象`)
    }
    Object.entries(parsed).forEach(([role, scopes]) => {
      if (!Array.isArray(scopes)) {
        throw new Error(`${role} 的范围必须是数组`)
      }
    })
    return parsed
  } catch (error) {
    ElMessage.error(`${label}JSON格式错误：${error.message}`)
    throw error
  }
}

const fetchPermissions = async () => {
  loading.value = true
  try {
    const res = await getApiPermissions()
    if (res.success) permissions.value = res.data || []
  } catch (error) {
    console.error('获取权限配置失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchModules = async () => {
  try {
    const res = await getApiPermissionModules()
    if (res.success) modules.value = res.data || []
  } catch (error) {
    console.error('获取模块失败:', error)
  }
}

const refreshAll = async () => {
  await fetchModules()
  await fetchPermissions()
}

const selectModule = (moduleId) => {
  selectedModuleId.value = moduleId
}

const syncApiGroup = () => {
  const module = modules.value.find(item => item.id === form.module_id)
  if (module) form.api_group = module.module_name
}

const handleInit = async () => {
  try {
    await ElMessageBox.confirm('初始化将添加默认配置并补齐模块，已存在配置不会重复添加。确定继续？', '提示', { type: 'info' })
    initLoading.value = true
    const res = await initApiPermissions()
    if (res.success) {
      ElMessage.success(res.message)
      refreshAll()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('初始化失败:', error)
  } finally {
    initLoading.value = false
  }
}

const handleSyncLegacy = async () => {
  try {
    await ElMessageBox.confirm('确定同步 lesson/config/api_level.yaml 中的旧版接口权限？已有配置不会被删除。', '提示', { type: 'info' })
    syncLoading.value = true
    const res = await syncLegacyApiPermissions()
    if (res.success) {
      ElMessage.success(res.message)
      refreshAll()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('同步旧配置失败:', error)
  } finally {
    syncLoading.value = false
  }
}

const resetApiForm = () => {
  Object.assign(form, {
    id: null,
    api_path: '',
    api_name: '',
    api_group: selectedModule.value?.module_name || '',
    module_id: selectedModuleId.value,
    http_method: '*',
    match_type: 'exact',
    allowed_roles: selectedModule.value?.allowed_roles?.length ? [...selectedModule.value.allowed_roles] : ['admin'],
    min_level: selectedModule.value?.min_level || 0,
    policy_mode: selectedModule.value?.policy_mode || 'role_and_level',
    inherit_from_module: selectedModuleId.value ? 1 : 0,
    is_public: 0,
    enforce_backend: 1,
    data_scope_rules_text: '',
    target_scope_rules_text: '',
    description: '',
    is_active: 1
  })
}

const handleAdd = () => {
  isEdit.value = false
  resetApiForm()
  apiDialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, {
    id: row.id,
    api_path: row.api_path,
    api_name: row.api_name,
    api_group: row.api_group,
    module_id: row.module_id,
    http_method: row.http_method || '*',
    match_type: row.match_type || 'exact',
    allowed_roles: row.allowed_roles || ['admin'],
    min_level: row.min_level || 0,
    policy_mode: row.policy_mode || 'role_and_level',
    inherit_from_module: row.inherit_from_module || 0,
    is_public: row.is_public || 0,
    enforce_backend: row.enforce_backend ?? 1,
    data_scope_rules_text: stringifyRules(row.data_scope_rules),
    target_scope_rules_text: stringifyRules(row.target_scope_rules),
    description: row.description || '',
    is_active: row.is_active
  })
  apiDialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除配置 "${row.api_name}"？`, '提示', { type: 'warning' })
    const res = await deleteApiPermission(row.id)
    if (res.success) {
      ElMessage.success('删除成功')
      refreshAll()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('删除失败:', error)
  }
}

const apiPayload = () => ({
  api_path: form.api_path,
  api_name: form.api_name,
  api_group: form.api_group,
  module_id: form.module_id,
  http_method: form.http_method,
  match_type: form.match_type,
  allowed_roles: form.allowed_roles,
  min_level: form.min_level,
  policy_mode: form.policy_mode,
  inherit_from_module: form.inherit_from_module,
  is_public: form.is_public,
  enforce_backend: form.enforce_backend,
  data_scope_rules: parseRulesText(form.data_scope_rules_text, '数据范围'),
  target_scope_rules: parseRulesText(form.target_scope_rules_text, '目标范围'),
  description: form.description,
  is_active: form.is_active
})

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true
    const res = isEdit.value
      ? await updateApiPermission(form.id, apiPayload())
      : await createApiPermission(apiPayload())
    if (res.success) {
      ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
      apiDialogVisible.value = false
      refreshAll()
    }
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitLoading.value = false
  }
}

const resetModuleForm = () => {
  Object.assign(moduleForm, {
    id: null,
    module_key: '',
    module_name: '',
    allowed_roles: ['admin'],
    min_level: 0,
    policy_mode: 'role_and_level',
    sort_order: 0,
    description: '',
    is_active: 1
  })
}

const handleAddModule = () => {
  isModuleEdit.value = false
  resetModuleForm()
  moduleDialogVisible.value = true
}

const handleEditModule = () => {
  if (!selectedModule.value) return
  isModuleEdit.value = true
  Object.assign(moduleForm, {
    id: selectedModule.value.id,
    module_key: selectedModule.value.module_key,
    module_name: selectedModule.value.module_name,
    allowed_roles: selectedModule.value.allowed_roles || [],
    min_level: selectedModule.value.min_level || 0,
    policy_mode: selectedModule.value.policy_mode || 'role_and_level',
    sort_order: selectedModule.value.sort_order || 0,
    description: selectedModule.value.description || '',
    is_active: selectedModule.value.is_active
  })
  moduleDialogVisible.value = true
}

const handleModuleSubmit = async () => {
  try {
    await moduleFormRef.value.validate()
    moduleSubmitLoading.value = true
    const payload = {
      module_key: moduleForm.module_key,
      module_name: moduleForm.module_name,
      allowed_roles: moduleForm.allowed_roles,
      min_level: moduleForm.min_level,
      policy_mode: moduleForm.policy_mode,
      sort_order: moduleForm.sort_order,
      description: moduleForm.description,
      is_active: moduleForm.is_active
    }
    const res = isModuleEdit.value
      ? await updateApiPermissionModule(moduleForm.id, payload)
      : await createApiPermissionModule(payload)
    if (res.success) {
      ElMessage.success(isModuleEdit.value ? '模块更新成功' : '模块创建成功')
      moduleDialogVisible.value = false
      refreshAll()
    }
  } catch (error) {
    console.error('模块提交失败:', error)
  } finally {
    moduleSubmitLoading.value = false
  }
}

const handleApplyModule = async () => {
  if (!selectedModule.value) return
  try {
    await ElMessageBox.confirm(`确定把 "${selectedModule.value.module_name}" 的权限批量应用到模块内API？`, '提示', { type: 'warning' })
    const res = await applyApiPermissionModule(selectedModule.value.id)
    if (res.success) {
      ElMessage.success(res.message)
      refreshAll()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('应用模块权限失败:', error)
  }
}

onMounted(refreshAll)
</script>

<style scoped>
.api-permission-page {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 16px;
  min-height: calc(100vh - 120px);
  padding: 20px;
}

.module-panel,
.api-panel :deep(.el-card) {
  min-height: 100%;
}

.module-panel {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-bg-color);
  padding: 14px;
}

.panel-title,
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.header-subtitle {
  margin-left: 10px;
  color: var(--el-text-color-secondary);
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.module-list {
  height: calc(100vh - 190px);
  margin-top: 12px;
}

.module-item {
  display: flex;
  width: 100%;
  justify-content: space-between;
  align-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  padding: 10px 8px;
  color: var(--el-text-color-regular);
  cursor: pointer;
  text-align: left;
}

.module-item:hover,
.module-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.module-item small {
  color: var(--el-text-color-secondary);
}

.policy-alert {
  margin-bottom: 14px;
}

.scope-help {
  width: 100%;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.policy-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  line-height: 1.6;
}

.role-list {
  color: var(--el-text-color-secondary);
}

@media (max-width: 900px) {
  .api-permission-page {
    grid-template-columns: 1fr;
  }

  .module-list {
    height: auto;
    max-height: 240px;
  }
}
</style>
