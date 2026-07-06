<template>
  <div class="menu-permission-page">
    <!-- 操作区域 -->
    <el-card class="action-card">
      <div class="action-bar">
        <div class="filters">
          <el-select v-model="selectedGroup" placeholder="选择分组" clearable style="width: 150px">
            <el-option label="全部" value="" />
            <el-option v-for="group in groups" :key="group" :label="group" :value="group" />
          </el-select>
          <el-button type="primary" @click="fetchConfig" :loading="loading">刷新</el-button>
        </div>
        <div class="actions">
          <el-button type="success" @click="handleInit" :loading="initLoading">初始化配置</el-button>
          <el-button type="warning" @click="handleReset">重置默认</el-button>
          <el-button type="primary" @click="handleAdd">新增菜单</el-button>
        </div>
      </div>

      <!-- 批量操作区域 -->
      <div v-if="selectedRows.length > 0" class="batch-actions">
        <span>已选择 {{ selectedRows.length }} 个菜单</span>
        <el-button type="primary" size="small" @click="handleBatchUpdate">批量设置角色</el-button>
      </div>
    </el-card>

    <!-- 配置表格 -->
    <el-card class="table-card">
      <el-table
        :data="filteredConfigs"
        v-loading="loading"
        @selection-change="handleSelectionChange"
        row-key="menu_key"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="menu_key" label="菜单标识" width="180" />
        <el-table-column prop="menu_label" label="菜单名称" width="120" />
        <el-table-column prop="menu_route" label="路由路径" width="180" />
        <el-table-column prop="menu_group" label="分组" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.menu_group }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="allowed_roles" label="允许角色" min-width="280">
          <template #default="{ row }">
            <div class="role-tags">
              <el-tag
                v-for="role in row.allowed_roles"
                :key="role"
                :type="getRoleTagType(role)"
                size="small"
                class="role-tag"
              >
                {{ getRoleLabel(role) }}
              </el-tag>
              <el-tag v-if="row.is_public" type="success" size="small">公开</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="handleToggleActive(row)"
              :loading="row.toggleLoading"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="editDialogVisible" :title="editMode === 'add' ? '新增菜单' : '编辑菜单'" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="菜单标识" required>
          <el-input v-model="editForm.menu_key" :disabled="editMode === 'edit'" placeholder="如：moral-daily" />
        </el-form-item>
        <el-form-item label="菜单名称" required>
          <el-input v-model="editForm.menu_label" placeholder="如：日常表现" />
        </el-form-item>
        <el-form-item label="路由路径" required>
          <el-input v-model="editForm.menu_route" placeholder="如：/moral/daily-record" />
          <div class="form-tip route-tip">
            <el-icon><Warning /></el-icon>
            <span>该路径必须已在前端 <code>frontend/src/router/index.js</code> 里注册对应组件，否则用户点击后会打开空白页。</span>
          </div>
        </el-form-item>
        <el-form-item label="所属分组" required>
          <el-select v-model="editForm.menu_group" style="width: 100%">
            <el-option v-for="group in groups" :key="group" :label="group" :value="group" />
          </el-select>
        </el-form-item>
        <el-form-item label="允许角色">
          <el-checkbox-group v-model="editForm.allowed_roles">
            <el-checkbox v-for="role in roles" :key="role" :label="role">
              {{ getRoleLabel(role) }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="公开访问">
          <el-switch v-model="editForm.is_public" />
          <span class="form-tip">公开菜单无需登录即可访问</span>
        </el-form-item>
        <el-form-item label="排序权重">
          <el-input-number v-model="editForm.sort_order" :min="0" :max="100" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量编辑对话框 -->
    <el-dialog v-model="batchDialogVisible" title="批量设置角色" width="400px">
      <p>将为选中的 {{ selectedRows.length }} 个菜单设置以下角色：</p>
      <el-checkbox-group v-model="batchRoles" style="margin-top: 15px">
        <el-checkbox v-for="role in roles" :key="role" :label="role">
          {{ getRoleLabel(role) }}
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchSubmit" :loading="batchLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Warning } from '@element-plus/icons-vue'
import {
  getMenuConfigList,
  getMenuGroups,
  getAllRoles,
  createMenuConfig,
  updateMenuConfig,
  deleteMenuConfig,
  batchUpdateMenuRoles,
  initDefaultMenuConfig,
  resetToDefault
} from '@/api/modules/menu'

const router = useRouter()

// 检查某个路径是否已在前端 router 中注册组件。
// 用来在新增/修改菜单后，及时提醒管理员是否遗漏了路由注册。
function isRouteRegistered(path) {
  if (!path) return false
  try {
    const resolved = router.resolve(path)
    // 未匹配到任何路由时，vue-router 会返回一个 matched 为空的空壳
    return Array.isArray(resolved.matched) && resolved.matched.length > 0
  } catch {
    return false
  }
}

// 数据
const configs = ref([])
const groups = ref([])
const roles = ref([])
const loading = ref(false)
const initLoading = ref(false)
const submitLoading = ref(false)
const batchLoading = ref(false)
const selectedGroup = ref('')
const selectedRows = ref([])

// 编辑相关
const editDialogVisible = ref(false)
const editMode = ref('add')
// 编辑模式下记住原始路由路径，用于判断路径是否被修改
const editingOriginalRoute = ref('')
const editForm = reactive({
  menu_key: '',
  menu_label: '',
  menu_route: '',
  menu_group: 'moral',
  allowed_roles: [],
  is_public: false,
  sort_order: 0,
  description: ''
})

// 批量编辑
const batchDialogVisible = ref(false)
const batchRoles = ref([])

// 角色映射
const roleLabels = {
  'teacher': '教师',
  'cleader': '班主任',
  'g_leader': '年级主任',
  'xuefa': '学发部',
  'jiaowu': '教务',
  'admin': '管理员'
}

const getRoleLabel = (role) => roleLabels[role] || role

const getRoleTagType = (role) => {
  const types = {
    'admin': 'danger',
    'jiaowu': 'warning',
    'xuefa': '',
    'g_leader': 'success',
    'cleader': 'info',
    'teacher': ''
  }
  return types[role] || ''
}

// 过滤后的配置
const filteredConfigs = computed(() => {
  if (!selectedGroup.value) return configs.value
  return configs.value.filter(c => c.menu_group === selectedGroup.value)
})

// 方法
const fetchConfig = async () => {
  loading.value = true
  try {
    const [configRes, groupRes, roleRes] = await Promise.all([
      getMenuConfigList(),
      getMenuGroups(),
      getAllRoles()
    ])
    if (configRes.success) configs.value = configRes.data
    if (groupRes.success) groups.value = groupRes.data
    if (roleRes.success) roles.value = roleRes.data
  } catch (error) {
    ElMessage.error('获取配置失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const handleInit = async () => {
  try {
    await ElMessageBox.confirm('初始化将从静态配置导入菜单项，已有配置不会重复。确定继续？', '初始化配置')
    initLoading.value = true
    const res = await initDefaultMenuConfig()
    if (res.success) {
      ElMessage.success(res.message)
      fetchConfig()
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('初始化失败')
      console.error(e)
    }
  } finally {
    initLoading.value = false
  }
}

const handleReset = async () => {
  try {
    await ElMessageBox.confirm('重置将清空所有现有配置并恢复默认值。此操作不可恢复！', '重置配置', {
      type: 'warning',
      confirmButtonText: '确定重置',
      cancelButtonText: '取消'
    })
    const res = await resetToDefault()
    if (res.success) {
      ElMessage.success(res.message)
      fetchConfig()
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('重置失败')
      console.error(e)
    }
  }
}

const handleAdd = () => {
  editMode.value = 'add'
  editingOriginalRoute.value = ''
  Object.assign(editForm, {
    menu_key: '',
    menu_label: '',
    menu_route: '',
    menu_group: 'moral',
    allowed_roles: [],
    is_public: false,
    sort_order: 0,
    description: ''
  })
  editDialogVisible.value = true
}

const handleEdit = (row) => {
  editMode.value = 'edit'
  editingOriginalRoute.value = row.menu_route
  Object.assign(editForm, {
    menu_key: row.menu_key,
    menu_label: row.menu_label,
    menu_route: row.menu_route,
    menu_group: row.menu_group,
    allowed_roles: [...row.allowed_roles],
    is_public: row.is_public,
    sort_order: row.sort_order,
    description: row.description || ''
  })
  editDialogVisible.value = true
}

const handleSubmit = async () => {
  if (!editForm.menu_key || !editForm.menu_label || !editForm.menu_route || !editForm.menu_group) {
    ElMessage.warning('请填写必填项')
    return
  }

  submitLoading.value = true
  try {
    let res
    const isAdd = editMode.value === 'add'
    if (isAdd) {
      res = await createMenuConfig(editForm)
    } else {
      res = await updateMenuConfig(editForm.menu_key, editForm)
    }
    if (res.success) {
      ElMessage.success(res.message)
      editDialogVisible.value = false
      fetchConfig()
      // 新增 或 修改了路由路径 → 检查前端是否已注册对应组件
      const routeChanged = isAdd || (editingOriginalRoute.value && editingOriginalRoute.value !== editForm.menu_route)
      if (routeChanged && !isRouteRegistered(editForm.menu_route)) {
        warnRouteNotRegistered(editForm.menu_route, editForm.menu_label)
      }
    }
  } catch (error) {
    ElMessage.error(editMode.value === 'add' ? '创建失败' : '更新失败')
    console.error(error)
  } finally {
    submitLoading.value = false
  }
}

// 前端未注册对应路由时弹出的显眼警告
function warnRouteNotRegistered(path, label) {
  ElMessageBox.alert(
    `路径 <code style="background:#fef3c7;padding:2px 6px;border-radius:3px;color:#92400e;">${path}</code> 在前端<b>尚未注册组件</b>，用户点击该菜单会打开空白页。<br/><br/>
    请让开发者在 <code style="background:#f3f4f6;padding:2px 6px;border-radius:3px;">frontend/src/router/index.js</code> 中添加：
    <pre style="background:#1f2937;color:#e5e7eb;padding:12px;border-radius:6px;margin-top:8px;font-size:12px;line-height:1.6;overflow-x:auto;">{
  path: '${path}',
  name: '${(label || 'NewPage').replace(/\\s+/g, '')}',
  component: () => import('../views/YourPage.vue'),
  meta: { title: '${label || ''}' }
}</pre>
    并创建对应的 <code style="background:#f3f4f6;padding:2px 6px;border-radius:3px;">.vue</code> 页面文件。<br/><br/>
    <span style="color:#6b7280;font-size:13px;">SPA 架构下路由与组件的映射需要在代码中声明，无法仅通过数据库配置生成新页面。</span>`,
    '⚠️ 需要开发者补全前端代码',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '知道了',
      customClass: 'route-warning-dialog',
      customStyle: { width: '560px' },
    }
  ).catch(() => {})
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除菜单 "${row.menu_label}"？此操作不可恢复。`, '删除确认', {
      type: 'warning'
    })
    const res = await deleteMenuConfig(row.menu_key)
    if (res.success) {
      ElMessage.success(res.message)
      fetchConfig()
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(e)
    }
  }
}

const handleToggleActive = async (row) => {
  row.toggleLoading = true
  try {
    const res = await updateMenuConfig(row.menu_key, {
      ...row,
      allowed_roles: row.allowed_roles
    })
    if (!res.success) {
      row.is_active = !row.is_active // 恢复原状态
      ElMessage.error('更新失败')
    }
  } catch (error) {
    row.is_active = !row.is_active
    ElMessage.error('更新失败')
    console.error(error)
  } finally {
    row.toggleLoading = false
  }
}

const handleBatchUpdate = () => {
  batchRoles.value = []
  batchDialogVisible.value = true
}

const handleBatchSubmit = async () => {
  batchLoading.value = true
  try {
    const menuKeys = selectedRows.value.map(r => r.menu_key)
    const res = await batchUpdateMenuRoles(menuKeys, batchRoles.value)
    if (res.success) {
      ElMessage.success(res.message)
      batchDialogVisible.value = false
      fetchConfig()
    }
  } catch (error) {
    ElMessage.error('批量更新失败')
    console.error(error)
  } finally {
    batchLoading.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.menu-permission-page {
  padding: 20px;
}

.action-card {
  margin-bottom: 20px;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  display: flex;
  gap: 10px;
}

.actions {
  display: flex;
  gap: 10px;
}

.batch-actions {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 15px;
  align-items: center;
}

.role-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.role-tag {
  margin: 2px;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.route-tip {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin: 6px 0 0;
  padding: 8px 10px;
  background: #fef3c7;
  border-left: 3px solid #f59e0b;
  border-radius: 4px;
  color: #92400e;
  font-size: 12px;
  line-height: 1.6;
}

.route-tip .el-icon {
  flex-shrink: 0;
  margin-top: 2px;
  color: #d97706;
}

.route-tip code {
  background: rgba(255, 255, 255, 0.7);
  padding: 1px 5px;
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 11px;
  color: #7c2d12;
}
</style>