<template>
  <DashboardLoadingState v-if="errorState === 'loading'" :metric-count="8" :chart-count="2" />
  <ErrorState v-else-if="errorState" :type="errorState" :show-retry="errorState === 'error'" @retry="fetchSummary" />
  <ForbiddenState v-else-if="forbidden" />
  <div v-else class="command-dashboard grade-theme">
    <DashboardHero
      kicker="Grade Intelligence"
      :title="gradeInfo.grade_name || '年级驾驶舱'"
      description="年级整体数据、班级对比、德育表现和出勤事务汇总。"
    >
      <div v-if="_isManager" class="filter-console">
        <el-select v-model="selectedGradeId" placeholder="选择年级" @change="onGradeChange" style="width: 140px">
          <el-option v-for="g in gradeList" :key="g.grade_id" :label="g.grade_name" :value="g.grade_id" />
        </el-select>
      </div>
      <DashboardTimeChip :value="summary.updated_at" />
    </DashboardHero>

    <DashboardMetricGrid :cards="summary.cards" :accents="accents" @click="go" />

    <section class="chart-grid">
      <DashboardChart
        title="年级班级对比"
        eyebrow="CLASS COMPARISON"
        :option="classComparisonOption"
        :empty="!summary.charts?.class_comparison?.length"
        emptyText="暂无班级对比数据"
      />
      <DashboardChart
        title="德育分数段分布"
        eyebrow="SCORE BAND"
        :option="scoreBandOption"
        :empty="!summary.charts?.score_band?.length"
        emptyText="暂无德育分分布数据"
      />
    </section>

    <!-- 班级对比趋势图 -->
    <section class="trend-section">
      <div class="trend-header">
        <h3>班级得分对比趋势</h3>
        <div class="trend-controls">
          <el-radio-group v-model="trendUnit" size="small" @change="onTrendUnitChange">
            <el-radio-button label="week">按周</el-radio-button>
            <el-radio-button label="month">按月</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <DashboardChart
        title="班级德育总分变化"
        eyebrow="CLASS TREND"
        :option="gradeClassTrendOption"
        :empty="!gradeClassTrendData.periods?.length"
        emptyText="暂无班级对比趋势数据"
        :loading="classTrendLoading"
      />
    </section>

    <!-- 年级得分趋势图 -->
    <section class="trend-section">
      <div class="trend-header">
        <h3>年级得分趋势</h3>
        <div class="trend-controls">
          <el-radio-group v-model="trendUnit" size="small" @change="onTrendUnitChange">
            <el-radio-button label="week">按周</el-radio-button>
            <el-radio-button label="month">按月</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <DashboardChart
        title="年级平均得分变化"
        eyebrow="GRADE TREND"
        :option="gradeTrendOption"
        :empty="!gradeTrendData.periods?.length"
        emptyText="暂无年级得分趋势数据"
        :loading="trendLoading"
      />
    </section>

    <!-- 学生个人得分趋势图 -->
    <section class="trend-section">
      <div class="trend-header">
        <h3>学生个人得分趋势</h3>
        <div class="trend-controls">
          <el-select v-model="selectedStudentId" placeholder="选择学生" clearable filterable size="small" @change="onStudentChange" style="width: 180px">
            <el-option v-for="s in studentList" :key="s.student_id" :label="`${s.name} (${s.class_name})`" :value="s.student_id" />
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
      <!-- 低分学生 -->
      <DashboardPanelSection eyebrow="LOW SCORE ALERT" title="低分学生" variant="danger">
        <div v-if="lowStudents.length" class="risk-list">
          <div v-for="(s, idx) in lowStudents" :key="s.student_id" class="risk-card">
            <div class="risk-rank">{{ idx + 1 }}</div>
            <div class="risk-info">
              <strong>{{ s.name }}</strong>
              <span class="risk-class">{{ s.class_name }}</span>
            </div>
            <div class="risk-score" :class="scoreClass(s.total_score)">
              <b>{{ s.total_score }}</b>
              <small>分</small>
            </div>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="本年级暂无低分学生，德育表现良好。" />
      </DashboardPanelSection>

      <!-- 当前请假 -->
      <DashboardPanelSection variant="attendance">
        <DashboardLeaveList
          :students="leaveStudents"
          mode="grade"
          eyebrow="ATTENDANCE STATUS"
          title="当前请假学生"
          empty-text="本年级当前无请假学生，出勤正常。"
        />
      </DashboardPanelSection>

      <!-- 本月生日 -->
      <DashboardPanelSection eyebrow="BIRTHDAY CARE" title="本月生日" variant="success">
        <div v-if="birthdayMonth.length" class="birthday-list">
          <div v-for="s in birthdayMonth" :key="s.name" class="birthday-card">
            <div class="birthday-icon">🎂</div>
            <div class="birthday-info">
              <strong>{{ s.name }}</strong>
              <span class="birthday-class">{{ s.class_name }}</span>
            </div>
            <div class="birthday-date">
              <small>{{ formatBirthday(s.birthday) }}</small>
            </div>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="本月暂无学生生日。" />
      </DashboardPanelSection>
    </section>

    <DashboardInsights
      :insights="insights"
      eyebrow="GRADE INSIGHTS"
      title="年级运行态势"
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
import { useAuthStore } from '@/stores/auth'
import { useDashboardRequest } from '@/composables/useDashboardRequest'
import { fetchGradeDashboardSummary, fetchGradeList, getGradeScoreTrend, getStudentScoreTrend, getGradeClassesScoreTrend } from '@/api/modules/dashboard'
import { getStudents } from '@/api/modules/moral'
import { buildAdaptiveValueAxis } from '@/utils/charting'

const router = useRouter()
const authStore = useAuthStore()

const summary = ref({ cards: [], charts: {}, tables: {} })
const gradeList = ref([])
const selectedGradeId = ref(null) // 直接使用数据库 ID
const gradeInfo = ref({})
const studentList = ref([])
const selectedStudentId = ref(null)
const trendUnit = ref('week')
const gradeTrendData = ref({ periods: [], labels: [], daily_scores: [], school_scores: [], task_scores: [], collective_scores: [], punishment_scores: [], total_scores: [] })
const studentTrendData = ref({ periods: [], labels: [], daily_scores: [], school_scores: [], task_scores: [], collective_scores: [], punishment_scores: [], total_scores: [] })
const gradeClassTrendData = ref({ periods: [], labels: [], classes: [] })
const trendLoading = ref(false)
const classTrendLoading = ref(false)
const { loading, errorState, forbidden, execute } = useDashboardRequest()
const accents = ['#E6A23C', '#67C23A', '#409EFF', '#F56C6C', '#909399', '#E6A23C', '#409EFF', '#67C23A']

const isEmpty = (items = []) => !items?.some(item => Number(item?.value) > 0)

const lowStudents = computed(() => summary.value.tables?.low_students || [])
const leaveStudents = computed(() => summary.value.tables?.leave_students || [])
const birthdayMonth = computed(() => summary.value.tables?.birthday_month || [])
const insights = computed(() => summary.value.insights || [])

const _isManager = computed(() => {
  return authStore.isAdmin || authStore.isJiaowu || authStore.isXuefa || authStore.isGleader
})

// 分数颜色类
function scoreClass(score) {
  if (score < 30) return 'critical'
  if (score < 50) return 'severe'
  return 'warning'
}

// 生日格式化
function formatBirthday(birthday) {
  if (!birthday) return ''
  // 只显示月日
  const parts = birthday.split('-')
  if (parts.length >= 3) {
    return `${parseInt(parts[1])}月${parseInt(parts[2])}日`
  }
  return birthday
}

const classComparisonOption = computed(() => {
  const data = summary.value.charts?.class_comparison || []
  if (!data.length) return {}

  // 按班级名称排序：高一1班 < 高一2班 < 高二1班...
  const sorted = [...data].sort((a, b) => {
    const parseClass = (name) => {
      const gradeMatch = name.match(/高?([一二三])/)
      const numMatch = name.match(/(\d+)班/)
      const gradeOrder = { '一': 1, '二': 2, '三': 3 }
      return {
        grade: gradeOrder[gradeMatch?.[1]] || 0,
        num: parseInt(numMatch?.[1]) || 0
      }
    }
    const aInfo = parseClass(a.class_name)
    const bInfo = parseClass(b.class_name)
    return aInfo.grade * 100 + aInfo.num - (bInfo.grade * 100 + bInfo.num)
  })

  return {
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const d = params[0]
        const item = sorted[d.dataIndex]
        return `${d.name}<br/>平均分: ${d.value.toFixed(1)}<br/>学生数: ${item?.student_count || '-'}`
      }
    },
    xAxis: { type: 'category', data: sorted.map(d => d.class_name), axisLabel: { rotate: 30, fontSize: 11 } },
    yAxis: buildAdaptiveValueAxis(sorted.map(d => d.avg_score), {
      name: '平均分',
      hardMin: 0,
      minRange: 4,
      targetTicks: 5
    }),
    series: [
      {
        name: '平均德育分',
        type: 'bar',
        data: sorted.map(d => ({
          value: d.avg_score,
          itemStyle: {
            color: d.avg_score >= 80 ? '#22c55e' : d.avg_score >= 60 ? '#3b82f6' : '#ef4444',
            borderRadius: [6, 6, 0, 0]
          }
        })),
        barWidth: 24,
        label: { show: true, position: 'top', formatter: (p) => p.value.toFixed(1), fontSize: 11, color: '#94a3b8' }
      }
    ]
  }
})

const scoreBandOption = computed(() => {
  const data = summary.value.charts?.score_band || []
  if (!data.length) return {}
  return {
    tooltip: { trigger: 'item' },
    series: [
      {
        name: '分数段',
        type: 'pie',
        radius: ['40%', '70%'],
        data: data.map(d => ({ name: d.label, value: d.count })),
        label: { show: true, formatter: '{b}: {c}' }
      }
    ]
  }
})

const gradeTrendOption = computed(() => {
  const data = gradeTrendData.value
  if (!data.periods?.length) return null

  // 无变化记录时显示基础分 + 提示
  const hasChanges = data.has_changes !== false
  const subtitleText = hasChanges ? '' : `年级德育平均分保持在基础分 ${data.total_scores?.[0] || 80} 分`
  const componentScores = [
    data.daily_scores,
    data.school_scores,
    data.task_scores,
    data.collective_scores,
    data.punishment_scores
  ]

  return {
    title: {
      text: subtitleText,
      left: 'center',
      top: 0,
      textStyle: { color: '#94a3b8', fontSize: 12, fontWeight: 'normal' }
    },
    tooltip: { trigger: 'axis' },
    legend: { data: ['德育总分', '日常记录', '校级事件', '任务完成', '集体活动', '处分扣分'], top: subtitleText ? 28 : 10 },
    xAxis: { type: 'category', data: data.labels },
    grid: { left: 48, right: 56, top: subtitleText ? 72 : 56, bottom: 32 },
    yAxis: [
      buildAdaptiveValueAxis(data.total_scores, {
        name: '总分',
        hardMin: 0,
        minRange: 4,
        targetTicks: 5
      }),
      buildAdaptiveValueAxis(componentScores, {
        name: '分项',
        hardMin: 0,
        includeZero: true,
        minRange: 4,
        targetTicks: 4,
        splitLine: { show: false },
        axisLabel: { color: '#64748b' },
        extra: { position: 'right' }
      })
    ],
    series: [
      { name: '德育总分', type: 'line', data: data.total_scores, smooth: true, itemStyle: { color: '#38bdf8' }, lineStyle: { width: 3 } },
      { name: '日常记录', type: 'line', yAxisIndex: 1, data: data.daily_scores, smooth: true, itemStyle: { color: '#34d399' } },
      { name: '校级事件', type: 'line', yAxisIndex: 1, data: data.school_scores, smooth: true, itemStyle: { color: '#fbbf24' } },
      { name: '任务完成', type: 'line', yAxisIndex: 1, data: data.task_scores, smooth: true, itemStyle: { color: '#a78bfa' } },
      { name: '集体活动', type: 'line', yAxisIndex: 1, data: data.collective_scores, smooth: true, itemStyle: { color: '#f472b6' } },
      { name: '处分扣分', type: 'line', yAxisIndex: 1, data: data.punishment_scores, smooth: true, itemStyle: { color: '#fb7185' } }
    ]
  }
})

const studentTrendOption = computed(() => {
  const data = studentTrendData.value
  if (!data.periods?.length) return null

  // 无变化记录时显示基础分 + 提示
  const hasChanges = data.has_changes !== false
  const subtitleText = hasChanges ? '' : `学生德育总分保持在基础分 ${data.total_scores?.[0] || 80} 分`
  const componentScores = [
    data.daily_scores,
    data.school_scores,
    data.task_scores,
    data.collective_scores,
    data.punishment_scores
  ]

  return {
    title: {
      text: subtitleText,
      left: 'center',
      top: 0,
      textStyle: { color: '#94a3b8', fontSize: 12, fontWeight: 'normal' }
    },
    tooltip: { trigger: 'axis' },
    legend: { data: ['德育总分', '日常记录', '校级事件', '任务完成', '集体活动', '处分扣分'], top: subtitleText ? 28 : 10 },
    xAxis: { type: 'category', data: data.labels },
    grid: { left: 48, right: 56, top: subtitleText ? 72 : 56, bottom: 32 },
    yAxis: [
      buildAdaptiveValueAxis(data.total_scores, {
        name: '总分',
        hardMin: 0,
        minRange: 4,
        targetTicks: 5
      }),
      buildAdaptiveValueAxis(componentScores, {
        name: '分项',
        hardMin: 0,
        includeZero: true,
        minRange: 4,
        targetTicks: 4,
        splitLine: { show: false },
        axisLabel: { color: '#64748b' },
        extra: { position: 'right' }
      })
    ],
    series: [
      { name: '德育总分', type: 'line', data: data.total_scores, smooth: true, itemStyle: { color: '#38bdf8' }, lineStyle: { width: 3 } },
      { name: '日常记录', type: 'line', yAxisIndex: 1, data: data.daily_scores, smooth: true, itemStyle: { color: '#34d399' } },
      { name: '校级事件', type: 'line', yAxisIndex: 1, data: data.school_scores, smooth: true, itemStyle: { color: '#fbbf24' } },
      { name: '任务完成', type: 'line', yAxisIndex: 1, data: data.task_scores, smooth: true, itemStyle: { color: '#a78bfa' } },
      { name: '集体活动', type: 'line', yAxisIndex: 1, data: data.collective_scores, smooth: true, itemStyle: { color: '#f472b6' } },
      { name: '处分扣分', type: 'line', yAxisIndex: 1, data: data.punishment_scores, smooth: true, itemStyle: { color: '#fb7185' } }
    ]
  }
})

const gradeClassTrendOption = computed(() => {
  const data = gradeClassTrendData.value
  if (!data.periods?.length) return null

  // 按 class_code 排序班级
  const sortedClasses = [...(data.classes || [])].sort((a, b) =>
    a.class_code.localeCompare(b.class_code)
  )

  // 预定义颜色数组
  const colors = ['#38bdf8', '#34d399', '#fbbf24', '#a78bfa', '#f472b6',
                  '#fb7185', '#22d3ee', '#84cc16', '#f59e0b', '#818cf8']

  const allScores = sortedClasses.flatMap(cls => cls.trend?.total_scores || [])

  return {
    tooltip: { trigger: 'axis' },
    legend: {
      data: sortedClasses.map(c => c.class_name),
      type: 'scroll',
      top: 10,
      height: 28,
      pageButtonItemGap: 5
    },
    grid: { left: 48, right: 24, top: 56, bottom: 32 },
    xAxis: {
      type: 'category',
      data: data.labels,
      axisLabel: { color: '#94a3b8' }
    },
    yAxis: {
      type: 'value',
      name: '德育总分',
      ...buildAdaptiveValueAxis(allScores, {
        name: '德育总分',
        hardMin: 0,
        minRange: 4,
        targetTicks: 5,
        axisLabel: { color: '#94a3b8' }
      }),
      axisLabel: { color: '#94a3b8' }
    },
    series: sortedClasses.map((cls, idx) => ({
      name: cls.class_name,
      type: 'line',
      smooth: true,
      data: cls.trend?.total_scores || [],
      itemStyle: { color: colors[idx % colors.length] },
      lineStyle: { width: 2 }
    }))
  }
})

function go(card) {
  if (card?.route) {
    router.push(card.route)
  }
}

const fetchSummary = async (filters = {}) => {
  await execute(
    () => fetchGradeDashboardSummary({ grade_id: selectedGradeId.value, ...filters }),
    (data) => {
      summary.value = data
      gradeInfo.value = { grade_name: data.grade_name }
    }
  )
}

function onGradeChange(gradeId) {
  selectedGradeId.value = gradeId
  const grade = gradeList.value.find(g => g.grade_id === gradeId)
  if (grade) {
    gradeInfo.value = grade
  }
  fetchSummary()
  fetchGradeStudentList()
  fetchGradeTrend()
  fetchGradeClassesTrend()
}

const fetchGradeStudentList = async () => {
  if (!selectedGradeId.value) return
  try {
    // 直接传递 grade_id 参数获取该年级学生（后端会根据权限过滤）
    const res = await getStudents({ grade_id: selectedGradeId.value, page_size: 500 })
    if (res.success) {
      studentList.value = res.data.items || res.data || []
    }
  } catch (e) {
    console.error('获取年级学生列表失败:', e)
  }
}

const fetchGradeTrend = async () => {
  // 使用数据库年级 ID（selectedGradeId 就是数据库 ID）
  if (!selectedGradeId.value) return
  trendLoading.value = true
  try {
    const res = await getGradeScoreTrend(selectedGradeId.value, { unit: trendUnit.value })
    if (res.success) {
      gradeTrendData.value = res.data.trend
    }
  } catch (e) {
    console.error('获取年级趋势失败:', e)
  } finally {
    trendLoading.value = false
  }
}

const fetchGradeClassesTrend = async () => {
  if (!selectedGradeId.value) return
  classTrendLoading.value = true
  try {
    const res = await getGradeClassesScoreTrend(selectedGradeId.value, { unit: trendUnit.value })
    if (res.success) {
      gradeClassTrendData.value = res.data
    }
  } catch (e) {
    console.error('获取班级对比趋势失败:', e)
  } finally {
    classTrendLoading.value = false
  }
}

const fetchStudentTrend = async () => {
  if (!selectedStudentId.value) {
    studentTrendData.value = { periods: [], labels: [], daily_scores: [], school_scores: [], task_scores: [], collective_scores: [], punishment_scores: [], total_scores: [] }
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
  fetchGradeTrend()
  fetchGradeClassesTrend()
  fetchStudentTrend()
}

const onStudentChange = () => {
  fetchStudentTrend()
}

async function loadGradeList() {
  try {
    const res = await fetchGradeList()
    if (res.success) {
      gradeList.value = res.data || []
      if (gradeList.value.length > 0 && !selectedGradeId.value) {
        const firstGrade = gradeList.value[0]
        selectedGradeId.value = firstGrade.grade_id // 直接使用数据库 ID
        gradeInfo.value = firstGrade
        fetchSummary()
        fetchGradeStudentList()
        fetchGradeTrend()
        fetchGradeClassesTrend()
      }
    }
  } catch (e) {
    console.error('Failed to load grade list:', e)
  }
}

onMounted(() => {
  loadGradeList()
})
</script>

<style scoped>
.grade-theme {
  --accent: #E6A23C;
  --accent-light: #FAECD8;
  --accent-bg: linear-gradient(135deg, #E6A23C 0%, #F5D442 100%);
  --dashboard-info-columns-desktop: repeat(3, minmax(0, 1fr));
}

.command-dashboard {
  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 10% 8%, rgba(230, 162, 60, 0.22), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(103, 194, 58, 0.16), transparent 28%);
}

.filter-console {
  min-width: 160px;
  margin-top: 12px;
}

.filter-console :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.74);
  border-color: rgba(230, 162, 60, 0.32);
}

.filter-console :deep(.el-input__inner) {
  color: #e2e8f0;
}

.info-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 28px;
}

/* ===== 低分学生卡片 ===== */
.risk-list {
  display: grid;
  gap: 12px;
}

.risk-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1px solid rgba(239, 68, 68, 0.24);
  border-radius: 8px;
  background: rgba(127, 29, 29, 0.18);
  transition: all 0.2s ease;
}

.risk-card:hover {
  border-color: rgba(239, 68, 68, 0.36);
  background: rgba(127, 29, 29, 0.24);
}

.risk-rank {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  background: rgba(239, 68, 68, 0.28);
  color: #fecdd3;
  font-size: 14px;
  font-weight: 600;
}

.risk-info {
  flex: 1;
  min-width: 0;
}

.risk-info strong {
  display: block;
  color: #f8fafc;
  font-size: 15px;
  font-weight: 600;
}

.risk-class {
  color: #94a3b8;
  font-size: 13px;
}

.risk-score {
  display: flex;
  align-items: baseline;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 6px;
}

.risk-score.critical {
  background: rgba(239, 68, 68, 0.28);
}

.risk-score.critical b {
  color: #fca5a5;
}

.risk-score.severe {
  background: rgba(249, 115, 22, 0.22);
}

.risk-score.severe b {
  color: #fdba74;
}

.risk-score.warning {
  background: rgba(251, 191, 36, 0.18);
}

.risk-score.warning b {
  color: #fde68a;
}

.risk-score b {
  font-size: 18px;
  font-weight: 700;
}

.risk-score small {
  color: #94a3b8;
  font-size: 12px;
}

/* ===== 本月生日卡片 ===== */
.birthday-list {
  display: grid;
  gap: 10px;
}

.birthday-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border: 1px solid rgba(34, 197, 94, 0.24);
  border-radius: 8px;
  background: rgba(6, 78, 59, 0.18);
  transition: all 0.2s ease;
}

.birthday-card:hover {
  border-color: rgba(34, 197, 94, 0.36);
  background: rgba(6, 78, 59, 0.24);
}

.birthday-icon {
  font-size: 24px;
}

.birthday-info {
  flex: 1;
  min-width: 0;
}

.birthday-info strong {
  display: block;
  color: #bbf7d0;
  font-size: 15px;
  font-weight: 600;
}

.birthday-class {
  color: #94a3b8;
  font-size: 13px;
}

.birthday-date {
  padding: 4px 10px;
  border-radius: 4px;
  background: rgba(34, 197, 94, 0.18);
}

.birthday-date small {
  color: #86efac;
  font-size: 13px;
}

/* ===== 趋势区块 ===== */
.trend-section {
  margin-top: 24px;
  padding: 20px;
  border: 1px solid rgba(230, 162, 60, 0.28);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9)),
    radial-gradient(circle at 8% 10%, rgba(230, 162, 60, 0.18), transparent 42%);
}

.trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.trend-header h3 {
  color: #f8fafc;
  font-size: 16px;
  font-weight: 600;
}

.trend-controls :deep(.el-radio-button__inner) {
  background: rgba(15, 23, 42, 0.74);
  border-color: rgba(230, 162, 60, 0.32);
  color: #e2e8f0;
}

.trend-controls :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #E6A23C;
  border-color: #E6A23C;
  color: #fff;
}

.trend-controls :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.74);
  border-color: rgba(230, 162, 60, 0.32);
}

.trend-controls :deep(.el-input__inner) {
  color: #e2e8f0;
}
</style>
