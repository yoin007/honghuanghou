<template>
  <div class="config-index-page">
    <!-- 配置管理卡片网格 -->
    <div class="config-grid">
      <el-card shadow="hover" class="config-card" @click="navigateTo('grade')">
        <div class="card-content">
          <el-icon class="card-icon"><School /></el-icon>
          <div class="card-title">级号管理</div>
          <div class="card-count">{{ stats.gradeCount }} 个级号</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="config-card" @click="navigateTo('class')">
        <div class="card-content">
          <el-icon class="card-icon"><House /></el-icon>
          <div class="card-title">班级管理</div>
          <div class="card-count">{{ stats.classCount }} 个班级</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="config-card" @click="navigateTo('student')">
        <div class="card-content">
          <el-icon class="card-icon"><User /></el-icon>
          <div class="card-title">学生管理</div>
          <div class="card-count">{{ stats.studentCount }} 名学生</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="config-card" @click="navigateTo('semester')">
        <div class="card-content">
          <el-icon class="card-icon"><Calendar /></el-icon>
          <div class="card-title">学年学期</div>
          <div class="card-count">{{ stats.semesterCount }} 个学期</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="config-card" @click="navigateTo('event-type')">
        <div class="card-content">
          <el-icon class="card-icon"><Document /></el-icon>
          <div class="card-title">事件类型</div>
          <div class="card-count">{{ stats.eventTypeCount }} 种类型</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="config-card" @click="navigateTo('escalation')">
        <div class="card-content">
          <el-icon class="card-icon"><Warning /></el-icon>
          <div class="card-title">累进规则</div>
          <div class="card-count">{{ stats.escalationCount }} 条规则</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="config-card" @click="navigateTo('config')">
        <div class="card-content">
          <el-icon class="card-icon"><Setting /></el-icon>
          <div class="card-title">系统配置</div>
          <div class="card-count">参数设置</div>
        </div>
      </el-card>

      <el-card shadow="hover" class="config-card" @click="navigateTo('operation-log')" v-if="isAdmin">
        <div class="card-content">
          <el-icon class="card-icon"><Notebook /></el-icon>
          <div class="card-title">操作日志</div>
          <div class="card-count">审计追踪</div>
        </div>
      </el-card>
    </div>

    <!-- 当前学期信息 -->
    <el-card class="semester-card">
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
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { School, User, Calendar, Document, Notebook, Setting, Warning, House } from '@element-plus/icons-vue'
import { getGrades, getClasses, getStudents, getSemesters, getDailyEventTypes, getSchoolEventTypes, getEscalationRules } from '@/api/modules/moral'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.isAdmin)

const stats = reactive({
  gradeCount: 0,
  classCount: 0,
  studentCount: 0,
  semesterCount: 0,
  eventTypeCount: 0,
  escalationCount: 0
})

const currentSemester = ref(null)

const fetchStats = async () => {
  try {
    const [grades, classes, students, semesters, dailyTypes, schoolTypes, escalationRules] = await Promise.all([
      getGrades(),
      getClasses(),
      getStudents({ page_size: 1 }),
      getSemesters(),
      getDailyEventTypes(),
      getSchoolEventTypes(),
      getEscalationRules()
    ])

    stats.gradeCount = grades.success ? (grades.data?.length || 0) : 0
    stats.classCount = classes.success ? (classes.data?.length || 0) : 0
    stats.studentCount = students.success ? (students.data?.total || 0) : 0
    stats.semesterCount = semesters.success ? (semesters.data?.length || 0) : 0
    stats.eventTypeCount = (dailyTypes.success ? (dailyTypes.data?.length || 0) : 0) + (schoolTypes.success ? (schoolTypes.data?.length || 0) : 0)
    stats.escalationCount = escalationRules.success ? (escalationRules.data?.length || 0) : 0

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
    'operation-log': '/moral/config/operation-log'
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

.config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.config-card {
  cursor: pointer;
  transition: all 0.3s ease;
  height: 100%;
}

.config-card:hover:not(.disabled) {
  transform: translateY(-5px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-content {
  text-align: center;
  padding: 30px 20px;
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
  opacity: 0.5;
  cursor: not-allowed;
}

.config-card.disabled:hover {
  transform: none;
}

.semester-card {
  margin-top: 30px;
}

/* 响应式布局 */
@media screen and (max-width: 1200px) {
  .config-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media screen and (max-width: 900px) {
  .config-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media screen and (max-width: 600px) {
  .config-grid {
    grid-template-columns: 1fr;
  }

  .config-index-page {
    padding: 10px;
  }

  .card-content {
    padding: 20px 15px;
  }

  .card-icon {
    font-size: 36px;
    margin-bottom: 10px;
  }
}
</style>