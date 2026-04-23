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

        <el-divider content-position="left">权限配置</el-divider>

        <el-form-item label="日常记录角色">
          <el-select v-model="configForm.daily_record_roles" multiple placeholder="选择可录入日常记录的角色">
            <el-option label="教师" value="teacher" />
            <el-option label="班主任" value="cleader" />
            <el-option label="学发部" value="xuefa" />
            <el-option label="教务处" value="jiaowu" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>

        <el-form-item label="学生画像角色">
          <el-select v-model="configForm.student_profile_roles" multiple placeholder="选择可生成学生画像的角色">
            <el-option label="班主任" value="cleader" />
            <el-option label="学发部" value="xuefa" />
            <el-option label="教务处" value="jiaowu" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>

        <el-form-item label="AI诊疗角色">
          <el-select v-model="configForm.ai_consultation_roles" multiple placeholder="选择可使用AI诊疗的角色">
            <el-option label="班主任" value="cleader" />
            <el-option label="学发部" value="xuefa" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">其他配置</el-divider>

        <el-form-item label="学期结转">
          <el-switch v-model="configForm.semester_carryover_enabled" :active-value="1" :inactive-value="0" />
          <span class="hint">是否启用学期数据结转</span>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSystemConfig, updateSystemConfig } from '@/api/modules/moral'

const loading = ref(false)
const saving = ref(false)

const configForm = reactive({
  evaluation_base_score: 80,
  evaluation_excellent_line: 90,
  evaluation_good_line: 75,
  evaluation_pass_line: 60,
  birthday_reminder_days: 3,
  daily_record_roles: ['teacher', 'cleader'],
  student_profile_roles: ['admin', 'jiaowu', 'xuefa', 'cleader'],
  ai_consultation_roles: ['admin', 'xuefa', 'cleader'],
  semester_carryover_enabled: 1
})

const fetchConfig = async () => {
  loading.value = true
  try {
    const res = await getSystemConfig()
    if (res.success && res.data) {
      // 处理 roles 字段（字符串转数组）
      Object.keys(res.data).forEach(key => {
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