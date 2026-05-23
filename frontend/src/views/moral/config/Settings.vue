<template>
  <div class="settings-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>德育评价系统配置</span>
          <el-button type="primary" @click="handleSave" :loading="saving">保存配置</el-button>
        </div>
      </template>

      <el-form :model="configForm" label-width="180px" v-loading="loading">
        <el-divider content-position="left">评价分值配置</el-divider>

        <el-form-item label="评价基础分">
          <el-input-number v-model="configForm.evaluation_base_score" :min="0" :max="200" :step="5" />
          <span class="hint">学生德育评价起始分数（当前：{{ configForm.evaluation_base_score }}分）</span>
        </el-form-item>

        <el-form-item label="优秀分数线">
          <el-input-number v-model="configForm.evaluation_excellent_line" :min="0" :max="100" :step="5" />
          <span class="hint">达到此分数评为优秀</span>
        </el-form-item>

        <el-form-item label="良好分数线">
          <el-input-number v-model="configForm.evaluation_good_line" :min="0" :max="100" :step="5" />
          <span class="hint">达到此分数评为良好</span>
        </el-form-item>

        <el-form-item label="及格分数线">
          <el-input-number v-model="configForm.evaluation_pass_line" :min="0" :max="100" :step="5" />
          <span class="hint">达到此分数评为及格</span>
        </el-form-item>

        <el-divider content-position="left">生日提醒配置</el-divider>

        <el-form-item label="提前提醒天数">
          <el-input-number v-model="configForm.birthday_reminder_days" :min="1" :max="30" :step="1" />
          <span class="hint">提前多少天提醒班主任</span>
        </el-form-item>

        <el-divider content-position="left">处罚类型配置</el-divider>

        <el-form-item label="处罚类型列表">
          <el-table :data="configForm.punishment_types" size="small" border style="width: 600px">
            <el-table-column prop="name" label="处分类型" width="120" />
            <el-table-column prop="period_days" label="期限天数" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.period_days }}天</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="period_description" label="期限说明" width="120" />
            <el-table-column prop="allow_revoke_apply" label="可申请撤销" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.allow_revoke_apply ? 'success' : 'danger'">
                  {{ row.allow_revoke_apply ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="min_good_records" label="良好记录数" width="100" align="center" />
          </el-table>
          <div style="margin-top: 10px;">
            <el-button type="primary" size="small" @click="$router.push('/moral/config/punishment-period')">
              管理处罚期限配置
            </el-button>
            <span class="hint" style="margin-left: 10px;">处罚类型统一在「处罚期限配置」页面管理</span>
          </div>
        </el-form-item>

        <el-divider content-position="left">升年级管理</el-divider>

        <el-form-item label="升年级操作">
          <el-button type="info" @click="handlePreviewPromotion" :loading="promotionLoading">
            预览升年级情况
          </el-button>
          <el-button type="danger" @click="handleExecutePromotion" :loading="promotionLoading" :disabled="!promotionData">
            执行升年级
          </el-button>
          <span class="hint">高三毕业归档，高一/高二升级</span>
        </el-form-item>

        <el-form-item label="升年级预览" v-if="promotionData">
          <el-descriptions :column="3" border size="small">
            <el-descriptions-item label="即将毕业学生">{{ promotionData.graduating_count || 0 }} 人</el-descriptions-item>
            <el-descriptions-item label="即将归档年级">{{ promotionData.graduating_grades?.length || 0 }} 个</el-descriptions-item>
            <el-descriptions-item label="下一学年">{{ promotionData.has_next_year ? '已创建' : '未创建' }}</el-descriptions-item>
          </el-descriptions>
          <el-table v-if="promotionData.graduating_grades?.length" :data="promotionData.graduating_grades" size="small" style="margin-top: 10px">
            <el-table-column prop="grade_name" label="年级" width="120" />
            <el-table-column prop="student_count" label="学生数" width="100" />
            <el-table-column prop="current_level" label="当前层级" width="100" />
          </el-table>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getSystemConfig,
  updateSystemConfig,
  previewGradePromotion,
  executeGradePromotion
} from '@/api/modules/moral'

const loading = ref(false)
const saving = ref(false)
const promotionLoading = ref(false)
const promotionData = ref(null)

const configForm = reactive({
  evaluation_base_score: 80,
  evaluation_excellent_line: 90,
  evaluation_good_line: 75,
  evaluation_pass_line: 60,
  birthday_reminder_days: 3,
  punishment_types: []  // 从 punishment_period_config 动态读取
})
const configKeys = new Set(Object.keys(configForm))

const fetchConfig = async () => {
  loading.value = true
  try {
    const res = await getSystemConfig()
    if (res.success && res.data) {
      // 处理 roles 字段（字符串转数组）
      Object.keys(res.data).forEach(key => {
        if (!configKeys.has(key)) return
        if (key.endsWith('_roles') && typeof res.data[key] === 'string') {
          configForm[key] = res.data[key].split(',')
        } else {
          configForm[key] = res.data[key]
        }
      })
    }
  } catch (error) {
    console.error('获取配置失败:', error)
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  saving.value = true
  try {
    // 处理 roles 字段（数组转字符串）
    const submitData = {}
    Object.keys(configForm).forEach(key => {
      if (key.endsWith('_roles') && Array.isArray(configForm[key])) {
        submitData[key] = configForm[key].join(',')
      } else {
        submitData[key] = configForm[key]
      }
    })

    const res = await updateSystemConfig(submitData)
    if (res.success) {
      ElMessage.success('配置保存成功')
    }
  } catch (error) {
    ElMessage.error('保存失败')
    console.error('保存配置失败:', error)
  } finally {
    saving.value = false
  }
}

// 升年级预览
const handlePreviewPromotion = async () => {
  promotionLoading.value = true
  try {
    const res = await previewGradePromotion()
    if (res.success) {
      promotionData.value = res.data
      if (res.data.graduating_count === 0) {
        ElMessage.info('当前没有即将毕业的年级')
      }
    }
  } catch (error) {
    ElMessage.error('获取升年级预览失败')
    console.error('升年级预览失败:', error)
  } finally {
    promotionLoading.value = false
  }
}

// 执行升年级
const handleExecutePromotion = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要执行升年级吗？将毕业 ${promotionData.value.graduating_count || 0} 名学生，归档 ${promotionData.value.graduating_grades?.length || 0} 个年级`,
      '升年级确认',
      { type: 'warning' }
    )
    promotionLoading.value = true
    const res = await executeGradePromotion({
      next_year_id: promotionData.value.next_school_year?.school_year_id || null
    })
    if (res.success) {
      ElMessage.success(res.message || '升年级执行成功')
      promotionData.value = null
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('升年级执行失败')
      console.error('升年级执行失败:', error)
    }
  } finally {
    promotionLoading.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<style scoped>
.settings-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hint {
  color: #909399;
  font-size: 12px;
  margin-left: 10px;
}

.el-divider {
  margin: 30px 0 20px;
}
</style>
