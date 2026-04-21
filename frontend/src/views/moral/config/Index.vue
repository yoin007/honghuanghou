<template>
  <div class="config-index-page">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="config-card" @click="navigateTo('grade')">
          <div class="card-content">
            <el-icon class="card-icon"><School /></el-icon>
            <div class="card-title">级号管理</div>
            <div class="card-count">{{ stats.gradeCount }} 个级号</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="config-card" @click="navigateTo('class')">
          <div class="card-content">
            <el-icon class="card-icon"><ClassRoom /></el-icon>
            <div class="card-title">班级管理</div>
            <div class="card-count">{{ stats.classCount }} 个班级</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="config-card" @click="navigateTo('student')">
          <div class="card-content">
            <el-icon class="card-icon"><User /></el-icon>
            <div class="card-title">学生管理</div>
            <div class="card-count">{{ stats.studentCount }} 名学生</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="config-card" @click="navigateTo('semester')">
          <div class="card-content">
            <el-icon class="card-icon"><Calendar /></el-icon>
            <div class="card-title">学年学期</div>
            <div class="card-count">{{ stats.semesterCount }} 个学期</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card shadow="hover" class="config-card" @click="navigateTo('event-type')">
          <div class="card-content">
            <el-icon class="card-icon"><Document /></el-icon>
            <div class="card-title">事件类型</div>
            <div class="card-count">{{ stats.eventTypeCount }} 种类型</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="config-card" @click="navigateTo('escalation')">
          <div class="card-content">
            <el-icon class="card-icon"><Warning /></el-icon>
            <div class="card-title">累进规则</div>
            <div class="card-count">{{ stats.escalationCount }} 条规则</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="config-card disabled">
          <div class="card-content">
            <el-icon class="card-icon"><Notebook /></el-icon>
            <div class="card-title">操作日志</div>
            <div class="card-count">待开发</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="config-card" @click="navigateTo('config')">
          <div class="card-content">
            <el-icon class="card-icon"><Setting /></el-icon>
            <div class="card-title">系统配置</div>
            <div class="card-count">参数设置</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 30px">
      <template #header>
        <span>当前学期信息</span>
      </template>
      <el-descriptions :column="3" border v-if="currentSemester">
        <el-descriptions-item label="当前学期">{{ currentSemester.semester_name }}</el-descriptions-item>
        <el-descriptions-item label="开始日期">{{ currentSemester.start_date }}</el-descriptions-item>
        <el-descriptions-item label="结束日期">{{ currentSemester.end_date }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="未设置当前学期" />
    </el-card>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card shadow="hover" class="config-card" @click="navigateTo('api-permission')">
          <div class="card-content">
            <el-icon class="card-icon"><Lock /></el-icon>
            <div class="card-title">API权限</div>
            <div class="card-count">{{ stats.apiPermissionCount }} 条配置</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="config-card disabled">
          <div class="card-content">
            <el-icon class="card-icon"><Notebook /></el-icon>
            <div class="card-title">操作日志</div>
            <div class="card-count">待开发</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12"></el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { School, User, Calendar, Document, Notebook, Setting, Warning, Lock } from '@element-plus/icons-vue'
import { getGrades, getClasses, getStudents, getSemesters, getDailyEventTypes, getSchoolEventTypes, getEscalationRules, getApiPermissions } from '@/api/modules/moral'

const router = useRouter()

const stats = reactive({
  gradeCount: 0,
  classCount: 0,
  studentCount: 0,
  semesterCount: 0,
  eventTypeCount: 0,
  escalationCount: 0,
  apiPermissionCount: 0
})

const currentSemester = ref(null)

const fetchStats = async () => {
  try {
    const [grades, classes, students, semesters, dailyTypes, schoolTypes, escalationRules, apiPermissions] = await Promise.all([
      getGrades(),
      getClasses(),
      getStudents({ page_size: 1 }),
      getSemesters(),
      getDailyEventTypes(),
      getSchoolEventTypes(),
      getEscalationRules(),
      getApiPermissions()
    ])

    stats.gradeCount = grades.success ? (grades.data?.length || 0) : 0
    stats.classCount = classes.success ? (classes.data?.length || 0) : 0
    stats.studentCount = students.success ? (students.data?.total || 0) : 0
    stats.semesterCount = semesters.success ? (semesters.data?.length || 0) : 0
    stats.eventTypeCount = (dailyTypes.success ? (dailyTypes.data?.length || 0) : 0) + (schoolTypes.success ? (schoolTypes.data?.length || 0) : 0)
    stats.escalationCount = escalationRules.success ? (escalationRules.data?.length || 0) : 0
    stats.apiPermissionCount = apiPermissions.success ? (apiPermissions.data?.length || 0) : 0

    if (semesters.success && semesters.data) {
      currentSemester.value = semesters.data.find(s => s.is_current)
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

const navigateTo = (type) => {
  const routes = {
    'grade': '/moral/config/grade',
    'class': '/moral/config/class',
    'student': '/moral/config/student',
    'semester': '/moral/config/semester',
    'event-type': '/moral/config/event-type',
    'escalation': '/moral/config/escalation',
    'config': '/moral/config/settings',
    'api-permission': '/moral/config/api-permission'
  }
  router.push(routes[type])
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
.config-index-page {
  padding: 20px;
}

.config-card {
  cursor: pointer;
  transition: transform 0.2s;
}

.config-card:hover {
  transform: translateY(-5px);
}

.card-content {
  text-align: center;
  padding: 20px;
}

.card-icon {
  font-size: 48px;
  color: var(--el-color-primary);
  margin-bottom: 15px;
}

.card-title {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 10px;
}

.card-count {
  font-size: 14px;
  color: #909399;
}

.config-card.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.config-card.disabled:hover {
  transform: none;
}
</style>