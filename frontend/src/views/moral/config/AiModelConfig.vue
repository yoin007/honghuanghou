<template>
  <div class="ai-model-config-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>大模型配置</span>
          <el-button type="primary" size="small" @click="handleInit" v-if="configs.length === 0">初始化配置</el-button>
        </div>
      </template>

      <el-table :data="configs" v-loading="loading" stripe>
        <el-table-column prop="display_name" label="功能模块" min-width="150" />
        <el-table-column prop="current_model" label="当前模型" min-width="180">
          <template #default="{ row }">
            <el-tag :type="getModelTagType(row.current_model)">
              {{ row.current_model }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="功能说明" min-width="200" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column prop="updated_by" label="更新人" width="100" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEditDialog(row)">修改</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 修改配置对话框 -->
    <el-dialog v-model="editDialogVisible" title="修改模型配置" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="功能模块">
          <el-input :value="editForm.display_name" disabled />
        </el-form-item>
        <el-form-item label="当前模型">
          <el-input :value="editForm.current_model" disabled />
        </el-form-item>
        <el-form-item label="选择模型">
          <el-cascader
            v-model="editForm.selected_model"
            :options="modelOptions"
            :props="{ value: 'name', label: 'name', children: 'models', emitPath: false }"
            placeholder="请选择模型"
            style="width: 100%"
            filterable
          />
        </el-form-item>
        <el-form-item label="模型能力">
          <el-tag v-for="cap in selectedModelCapabilities" :key="cap" size="small" style="margin-right: 8px">
            {{ cap }}
          </el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate" :loading="updating">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAiModelConfigs, getAvailableModels, updateAiModelConfig, initAiModelConfig } from '@/api/modules/moral'

const configs = ref([])
const availableModels = ref({})
const loading = ref(false)
const updating = ref(false)
const editDialogVisible = ref(false)
const editForm = ref({
  module_name: '',
  display_name: '',
  current_model: '',
  selected_model: ''
})

const modelOptions = computed(() => {
  return Object.entries(availableModels.value).map(([vendor, models]) => ({
    name: vendor,
    models: models.map(m => ({
      name: m.name,
      label: m.name,
      value: m.name,
      capabilities: m.capabilities
    }))
  }))
})

const selectedModelCapabilities = computed(() => {
  if (!editForm.value.selected_model) return []
  for (const models of Object.values(availableModels.value)) {
    const model = models.find(m => m.name === editForm.value.selected_model)
    if (model) return model.capabilities
  }
  return []
})

const getModelTagType = (modelName) => {
  if (modelName.startsWith('qwen')) return 'primary'
  if (modelName.startsWith('glm')) return 'success'
  if (modelName.startsWith('kimi')) return 'warning'
  if (modelName.startsWith('MiniMax')) return 'info'
  return ''
}

const fetchConfigs = async () => {
  loading.value = true
  try {
    const res = await getAiModelConfigs()
    if (res.success) {
      configs.value = res.data
    }
  } catch (error) {
    console.error('获取配置失败:', error)
    ElMessage.error('获取配置失败')
  } finally {
    loading.value = false
  }
}

const fetchModels = async () => {
  try {
    const res = await getAvailableModels()
    if (res.success) {
      availableModels.value = res.data
    }
  } catch (error) {
    console.error('获取模型列表失败:', error)
  }
}

const openEditDialog = (row) => {
  editForm.value = {
    module_name: row.module_name,
    display_name: row.display_name,
    current_model: row.current_model,
    selected_model: row.current_model
  }
  editDialogVisible.value = true
}

const handleUpdate = async () => {
  if (!editForm.value.selected_model) {
    ElMessage.warning('请选择模型')
    return
  }

  updating.value = true
  try {
    const res = await updateAiModelConfig(editForm.value.module_name, {
      current_model: editForm.value.selected_model
    })
    if (res.success) {
      ElMessage.success(res.message || '配置已更新')
      editDialogVisible.value = false
      fetchConfigs()
    }
  } catch (error) {
    console.error('更新配置失败:', error)
    ElMessage.error('更新失败：' + (error.response?.data?.detail || '未知错误'))
  } finally {
    updating.value = false
  }
}

const handleInit = async () => {
  try {
    const res = await initAiModelConfig()
    if (res.success) {
      ElMessage.success(res.message)
      fetchConfigs()
    }
  } catch (error) {
    console.error('初始化失败:', error)
    ElMessage.error('初始化失败')
  }
}

onMounted(() => {
  fetchConfigs()
  fetchModels()
})
</script>

<style scoped>
.ai-model-config-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>