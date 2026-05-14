<template>
  <div class="punishment-period-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>处分期限配置</span>
          <el-button type="primary" @click="handleSaveAll" :loading="saving">保存配置</el-button>
        </div>
      </template>

      <el-table :data="periodConfigs" v-loading="loading" stripe>
        <el-table-column prop="punishment_type" label="处分类型" width="150">
          <template #default="{ row }">
            <el-tag :type="getPunishmentTagType(row.punishment_type)">
              {{ row.punishment_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="期限天数" width="150">
          <template #default="{ row }">
            <el-input-number v-model="row.period_days" :min="1" :max="3650" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="期限描述" width="150">
          <template #default="{ row }">
            <el-input v-model="row.period_description" size="small" placeholder="如：一个月" />
          </template>
        </el-table-column>
        <el-table-column label="允许申请撤销" width="120">
          <template #default="{ row }">
            <el-switch v-model="row.allow_revoke_apply" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="最少良好记录数" width="150">
          <template #default="{ row }">
            <el-input-number v-model="row.min_good_records" :min="0" :max="100" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.is_active" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
      </el-table>

      <el-alert type="info" :closable="false" style="margin-top: 20px">
        <template #title>
          <strong>配置说明</strong>
        </template>
        - 期限天数：处分生效后的观察期长度，到期后可申请撤销
        - 允许申请撤销：到期后是否允许班主任代学生发起撤销申请
        - 最少良好记录数：申请撤销所需的最少良好表现记录数（可选）
      </el-alert>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getPunishmentPeriods, updatePunishmentPeriod } from '@/api/modules/moral'

const loading = ref(false)
const saving = ref(false)
const periodConfigs = ref([])

const getPunishmentTagType = (type) => {
  const types = {
    '警告': 'info',
    '严重警告': 'warning',
    '记过': 'danger',
    '记大过': 'danger',
    '留校察看': 'danger'
  }
  return types[type] || 'info'
}

const fetchPeriodConfigs = async () => {
  loading.value = true
  try {
    const res = await getPunishmentPeriods()
    if (res.success) {
      periodConfigs.value = res.data || []
    }
  } catch (error) {
    ElMessage.error('获取配置失败')
  } finally {
    loading.value = false
  }
}

const handleSaveAll = async () => {
  saving.value = true
  try {
    const promises = periodConfigs.value.map(config =>
      updatePunishmentPeriod(config.id, {
        period_days: config.period_days,
        period_description: config.period_description,
        allow_revoke_apply: config.allow_revoke_apply,
        min_good_records: config.min_good_records,
        is_active: config.is_active
      })
    )
    await Promise.all(promises)
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchPeriodConfigs()
})
</script>

<style scoped>
.punishment-period-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>