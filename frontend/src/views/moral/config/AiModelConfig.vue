<template>
  <div class="ai-model-config-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>大模型配置</span>
          <el-button type="primary" size="small" @click="handleAiInit" v-if="aiConfigs.length === 0" :loading="aiInitLoading">初始化配置</el-button>
        </div>
      </template>

      <el-table :data="aiConfigs" v-loading="aiLoading" stripe>
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
            <el-button type="primary" link @click="openAiEditDialog(row)">修改</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 大模型修改对话框 -->
    <el-dialog v-model="aiEditDialogVisible" title="修改模型配置" width="500px">
      <el-form :model="aiEditForm" label-width="100px">
        <el-form-item label="功能模块">
          <el-input :value="aiEditForm.display_name" disabled />
        </el-form-item>
        <el-form-item label="当前模型">
          <el-input :value="aiEditForm.current_model" disabled />
        </el-form-item>
        <el-form-item label="选择模型">
          <el-cascader
            v-model="aiEditForm.selected_model"
            :options="aiModelOptions"
            :props="{ value: 'name', label: 'name', children: 'models', emitPath: false }"
            placeholder="请选择模型"
            style="width: 100%"
            filterable
          />
        </el-form-item>
        <el-form-item label="模型能力">
          <el-tag v-for="cap in selectedAiModelCapabilities" :key="cap" size="small" style="margin-right: 8px">
            {{ cap }}
          </el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="aiEditDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAiUpdate" :loading="aiUpdating">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getAiModelConfigs,
  getAvailableModels,
  updateAiModelConfig,
  initAiModelConfig
} from '@/api/modules/moral'

// 大模型配置
const aiConfigs = ref([])
const aiAvailableModels = ref({})
const aiLoading = ref(false)
const aiUpdating = ref(false)
const aiInitLoading = ref(false)
const aiEditDialogVisible = ref(false)
const aiEditForm = ref({
  module_name: '',
  display_name: '',
  current_model: '',
  selected_model: ''
})

const aiModelOptions = computed(() => {
  return Object.entries(aiAvailableModels.value).map(([vendor, models]) => ({
    name: vendor,
    models: models.map(m => ({
      name: m.name,
      label: m.name,
      value: m.name,
      capabilities: m.capabilities
    }))
  }))
})

const selectedAiModelCapabilities = computed(() => {
  if (!aiEditForm.value.selected_model) return []
  for (const models of Object.values(aiAvailableModels.value)) {
    const model = models.find(m => m.name === aiEditForm.value.selected_model)
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

const fetchAiConfigs = async () => {
  aiLoading.value = true
  try {
    const res = await getAiModelConfigs()
    if (res.success) {
      aiConfigs.value = res.data
    }
  } catch (error) {
    console.error('获取大模型配置失败:', error)
    ElMessage.error('获取大模型配置失败')
  } finally {
    aiLoading.value = false
  }
}

const fetchAiModels = async () => {
  try {
    const res = await getAvailableModels()
    if (res.success) {
      aiAvailableModels.value = res.data
    }
  } catch (error) {
    console.error('获取模型列表失败:', error)
  }
}

const openAiEditDialog = (row) => {
  aiEditForm.value = {
    module_name: row.module_name,
    display_name: row.display_name,
    current_model: row.current_model,
    selected_model: row.current_model
  }
  aiEditDialogVisible.value = true
}

const handleAiUpdate = async () => {
  if (!aiEditForm.value.selected_model) {
    ElMessage.warning('请选择模型')
    return
  }

  aiUpdating.value = true
  try {
    const res = await updateAiModelConfig(aiEditForm.value.module_name, {
      current_model: aiEditForm.value.selected_model
    })
    if (res.success) {
      ElMessage.success(res.message || '配置已更新')
      aiEditDialogVisible.value = false
      fetchAiConfigs()
    }
  } catch (error) {
    console.error('更新配置失败:', error)
    ElMessage.error('更新失败：' + (error.response?.data?.detail || '未知错误'))
  } finally {
    aiUpdating.value = false
  }
}

const handleAiInit = async () => {
  aiInitLoading.value = true
  try {
    const res = await initAiModelConfig()
    if (res.success) {
      ElMessage.success(res.message)
      fetchAiConfigs()
    }
  } catch (error) {
    console.error('初始化失败:', error)
    ElMessage.error('初始化失败')
  } finally {
    aiInitLoading.value = false
  }
}

onMounted(() => {
  fetchAiConfigs()
  fetchAiModels()
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
