<template>
  <DashboardLoadingState v-if="errorState === 'loading'" :metric-count="8" :chart-count="2" />
  <ErrorState v-else-if="errorState" :type="errorState" :show-retry="errorState === 'error'" @retry="fetchSummary" />
  <ForbiddenState v-else-if="forbidden" />
  <div v-else class="command-dashboard class-theme">
    <DashboardHero
      kicker="Class Intelligence"
      :title="classInfo.class_name || '班级驾驶舱'"
      description="班级人数结构、学习活动、德育表现、出勤事务和生日关怀汇总。"
    >
      <div v-if="_isManager" class="filter-console">
        <el-select v-model="selectedClassId" placeholder="选择班级" @change="onClassChange">
          <el-option v-for="c in classList" :key="c.class_id" :label="c.class_name" :value="c.class_id" />
        </el-select>
      </div>
      <DashboardTimeChip :value="summary.updated_at" />
    </DashboardHero>

    <DashboardMetricGrid :cards="summary.cards" :accents="accents" @click="go" />

    <section class="chart-grid">
      <DashboardChart
        title="班级性别结构"
        eyebrow="GENDER MIX"
        :option="genderMixOption"
        :empty="isEmpty(summary.charts?.gender_mix)"
        emptyText="暂无学生性别数据"
      />
      <DashboardChart
        title="德育分数段分布"
        eyebrow="SCORE BAND"
        :option="scoreBandOption"
        :empty="isEmpty(summary.charts?.score_band)"
        emptyText="暂无德育分分布数据"
      />
    </section>

    <!-- 班级得分趋势图 -->
    <section class="trend-section">
      <div class="trend-header">
        <h3>班级得分趋势</h3>
        <div class="trend-controls">
          <el-radio-group v-model="trendUnit" size="small" @change="onTrendUnitChange">
            <el-radio-button label="week">按周</el-radio-button>
            <el-radio-button label="month">按月</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <DashboardChart
        title="班级平均得分变化"
        eyebrow="CLASS TREND"
        :option="classTrendOption"
        :empty="!classTrendData.periods?.length"
        emptyText="暂无班级得分趋势数据"
        :loading="trendLoading"
      />
    </section>

    <!-- 学生个人得分趋势图 -->
    <section class="trend-section">
      <div class="trend-header">
        <h3>学生个人得分趋势</h3>
        <div class="trend-controls">
          <el-select v-model="selectedStudentId" placeholder="选择学生" clearable size="small" @change="onStudentChange" style="width: 180px">
            <el-option v-for="s in studentList" :key="s.student_id" :label="s.name" :value="s.student_id" />
          </el-select>
        </div>
      </div>
      <DashboardChart
        v-if="selectedStudentId"
        title="学生得分变化"
        eyebrow="STUDENT TREND"
        :option="studentTrendOption"
        :empty="!studentTrendData.periods?.length"
        emptyText="暂无学生得分趋势数据"
        :loading="trendLoading"
      />
      <DashboardEmptyStrip v-else text="请选择学生查看个人得分趋势。" />
    </section>

    <section class="info-panel">
      <DashboardPanelSection eyebrow="LOW SCORE ALERT" title="低分学生">
        <div v-if="lowStudents.length" class="risk-list">
          <div v-for="s in lowStudents" :key="s.student_id" class="risk-row">
            <span>{{ s.name }}</span>
            <b>{{ s.total_score }} 分</b>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="本班暂无低分学生。" />
      </DashboardPanelSection>

      <DashboardPanelSection variant="attendance">
        <DashboardLeaveList
          :students="leaveStudents"
          mode="class"
          eyebrow="ATTENDANCE STATUS"
          title="当前请假学生"
          empty-text="本班当前无请假学生，出勤正常。"
        />
      </DashboardPanelSection>

      <DashboardPanelSection eyebrow="BIRTHDAY CARE" title="本月生日">
        <div v-if="birthdayMonth.length" class="birthday-list">
          <div v-for="s in birthdayMonth" :key="s.name" class="birthday-item">
            <span>{{ s.name }}</span>
            <small>{{ s.birthday }}</small>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="本月暂无学生生日。" />
      </DashboardPanelSection>

      <DashboardPanelSection eyebrow="THIS WEEK" title="本周生日">
        <div v-if="birthdayWeek.length" class="birthday-list highlight">
          <div v-for="s in birthdayWeek" :key="s.name" class="birthday-item">
            <span>{{ s.name }}</span>
            <small>{{ s.birthday }}</small>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="本周暂无学生生日。" />
      </DashboardPanelSection>
    </section>

    <DashboardInsights
      :insights="insights"
      eyebrow="CLASS INSIGHTS"
      title="班级运行态势"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import DashboardEmptyStrip from '@/components/dashboard/DashboardEmptyStrip.vue'
import DashboardInsights from '@/components/dashboard/DashboardInsights.vue'
import DashboardLeaveList from '@/components/dashboard/DashboardLeaveList.vue'
import DashboardLoadingState from '@/components/dashboard/DashboardLoadingState.vue'
import ErrorState from '@/components/dashboard/ErrorState.vue'
import ForbiddenState from '@/components/dashboard/ForbiddenState.vue'
import DashboardHero from '@/components/dashboard/DashboardHero.vue'
import DashboardMetricGrid from '@/components/dashboard/DashboardMetricGrid.vue'
import DashboardTimeChip from '@/components/dashboard/DashboardTimeChip.vue'
import DashboardPanelSection from '@/components/dashboard/DashboardPanelSection.vue'
import { getClassDashboardSummary, getClassScoreTrend, getStudentScoreTrend } from '@/api/modules/dashboard'
import { getClasses, getStudents } from '@/api/modules/moral'
import { useAuthStore } from '@/stores/auth'
import { basePieOption } from '@/utils/charting'
import { useDashboardRequest } from '@/composables/useDashboardRequest'

const router = useRouter()
const authStore = useAuthStore()
const summary = ref({ cards: [], charts: {}, tables: {}, class_info: {} })
const classList = ref([])
const selectedClassId = ref(null)
const studentList = ref([])
const selectedStudentId = ref(null)
const trendUnit = ref('week')
const classTrendData = ref({ periods: [], labels: [], task_scores: [], record_scores: [], total_scores: [] })
const studentTrendData = ref({ periods: [], labels: [], task_scores: [], record_scores: [], total_scores: [] })
const trendLoading = ref(false)
const { loading, errorState, forbidden, execute } = useDashboardRequest()
const accents = ['#34d399', '#f472b6', '#67e8f9', '#fbbf24', '#fb7185', '#a78bfa', '#38bdf8', '#f59e0b']

const go = (route) => route && router.push(route)
const isEmpty = (items = []) => !items?.some(item => Number(item?.value) > 0)

// 切换班级时直接使用变更后的值
const onClassChange = (newClassId) => {
  if (newClassId) {
    selectedClassId.value = newClassId
    fetchSummary()
  }
}

// 教务/管理员/学发可切换班级（使用 authStore，与 App.vue 一致）
const _isManager = computed(() => {
  return authStore.isAdmin || authStore.isJiaowu || authStore.isXuefa
})

const classInfo = computed(() => summary.value.class_info || {})
const lowStudents = computed(() => summary.value.tables?.low_students || [])
const birthdayMonth = computed(() => summary.value.tables?.birthday_this_month || [])
const birthdayWeek = computed(() => summary.value.tables?.birthday_this_week || [])
const leaveStudents = computed(() => summary.value.tables?.leave_students || [])
const insights = computed(() => summary.value.insights || [])

const genderMixOption = computed(() => basePieOption({
  color: ['#34d399', '#f472b6', '#94a3b8'],
  data: summary.value.charts?.gender_mix || []
}))

const scoreBandOption = computed(() => basePieOption({
  color: ['#fb7185', '#34d399', '#94a3b8'],
  data: summary.value.charts?.score_band || []
}))

const classTrendOption = computed(() => {
  const data = classTrendData.value
  if (!data.periods?.length) return null
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['任务得分', '加减分', '总分'], top: 10 },
    xAxis: { type: 'category', data: data.labels },
    yAxis: { type: 'value', name: '平均得分' },
    series: [
      { name: '任务得分', type: 'line', data: data.task_scores, smooth: true, itemStyle: { color: '#34d399' } },
      { name: '加减分', type: 'line', data: data.record_scores, smooth: true, itemStyle: { color: '#fbbf24' } },
      { name: '总分', type: 'line', data: data.total_scores, smooth: true, itemStyle: { color: '#38bdf8' } }
    ]
  }
})

const studentTrendOption = computed(() => {
  const data = studentTrendData.value
  if (!data.periods?.length) return null
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['任务得分', '加减分', '总分'], top: 10 },
    xAxis: { type: 'category', data: data.labels },
    yAxis: { type: 'value', name: '得分' },
    series: [
      { name: '任务得分', type: 'line', data: data.task_scores, smooth: true, itemStyle: { color: '#34d399' } },
      { name: '加减分', type: 'line', data: data.record_scores, smooth: true, itemStyle: { color: '#fbbf24' } },
      { name: '总分', type: 'line', data: data.total_scores, smooth: true, itemStyle: { color: '#38bdf8' } }
    ]
  }
})

const fetchClassList = async () => {
  if (!_isManager.value) return
  const res = await getClasses()
  if (res.success) {
    classList.value = res.data.filter(c => c.is_active === 1)
  }
}

const fetchStudentList = async () => {
  if (!classInfo.value.class_id) return
  const res = await getStudents({ class_id: classInfo.value.class_id, page_size: 100 })
  if (res.success) {
    studentList.value = res.data.items || res.data || []
  }
}

const fetchClassTrend = async () => {
  if (!classInfo.value.class_id) return
  trendLoading.value = true
  try {
    const res = await getClassScoreTrend(classInfo.value.class_id, { unit: trendUnit.value })
    if (res.success) {
      classTrendData.value = res.data.trend
    }
  } catch (e) {
    console.error('获取班级趋势失败:', e)
  } finally {
    trendLoading.value = false
  }
}

const fetchStudentTrend = async () => {
  if (!selectedStudentId.value) {
    studentTrendData.value = { periods: [], labels: [], task_scores: [], record_scores: [], total_scores: [] }
    return
  }
  trendLoading.value = true
  try {
    const res = await getStudentScoreTrend(selectedStudentId.value, { unit: trendUnit.value })
    if (res.success) {
      studentTrendData.value = res.data.trend
    }
  } catch (e) {
    console.error('获取学生趋势失败:', e)
  } finally {
    trendLoading.value = false
  }
}

const onTrendUnitChange = () => {
  fetchClassTrend()
  fetchStudentTrend()
}

const onStudentChange = () => {
  fetchStudentTrend()
}

const fetchSummary = () => execute(
  () => getClassDashboardSummary(selectedClassId.value ? { class_id: selectedClassId.value } : {}),
  data => {
    summary.value = data
    if (!selectedClassId.value && data.class_info?.class_id) {
      selectedClassId.value = data.class_info.class_id
    }
    // 获取学生列表和趋势数据
    fetchStudentList()
    fetchClassTrend()
  }
)

onMounted(() => {
  fetchClassList()
  fetchSummary()
})
</script>

<style scoped>
.command-dashboard {
  --dashboard-chart-columns-desktop: repeat(2, minmax(0, 1fr));

  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 10% 8%, rgba(52, 211, 153, 0.2), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(244, 114, 182, 0.14), transparent 28%);
}

.filter-console {
  min-width: 180px;
}

.filter-console :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.74);
}

.info-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
}

.risk-list,
.birthday-list {
  display: grid;
  gap: 8px;
}

.risk-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid rgba(251, 113, 133, 0.2);
  border-radius: 6px;
  background: rgba(127, 29, 29, 0.18);
  color: #fecdd3;
}

.birthday-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid rgba(34, 211, 153, 0.2);
  border-radius: 6px;
  background: rgba(6, 78, 59, 0.18);
}

.birthday-item span {
  color: #bbf7d0;
}

.birthday-item small {
  color: #94a3b8;
}

.birthday-list.highlight .birthday-item {
  border-color: rgba(251, 191, 36, 0.28);
  background: rgba(120, 53, 15, 0.22);
}

.birthday-list.highlight .birthday-item span {
  color: #fde68a;
}

.trend-section {
  margin-top: 20px;
  padding: 16px;
  border: 1px solid rgba(52, 211, 153, 0.2);
  border-radius: 8px;
  background: rgba(6, 78, 59, 0.12);
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.trend-header h3 {
  color: #bbf7d0;
  font-size: 14px;
  font-weight: 600;
}

.trend-controls :deep(.el-radio-button__inner) {
  background: rgba(15, 23, 42, 0.74);
  border-color: rgba(52, 211, 153, 0.3);
}

.trend-controls :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #34d399;
  border-color: #34d399;
}

.trend-controls :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.74);
}
</style>
