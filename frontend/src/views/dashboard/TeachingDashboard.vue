<template>
  <DashboardLoadingState v-if="errorState === 'loading'" :metric-count="5" :chart-count="4" />
  <ErrorState v-else-if="errorState" :type="errorState" :show-retry="errorState === 'error'" @retry="fetchSummary" />
  <ForbiddenState v-else-if="forbidden" />
  <div v-else class="command-dashboard teaching-theme">
    <DashboardHero
      kicker="Teaching Operations"
      title="教务驾驶舱"
      description="围绕课表、教师课时和班级规模做可视化分析，指定时间段内的教师课时排行来自课表文件。"
    >
      <el-form :inline="true" class="filter-console">
        <el-form-item label="开始">
          <el-date-picker v-model="filters.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="结束">
          <el-date-picker v-model="filters.end_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="排行">
          <el-select v-model="filters.top_n" class="top-select">
            <el-option :value="5" label="Top 5" />
            <el-option :value="10" label="Top 10" />
            <el-option :value="15" label="Top 15" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="fetchSummary">查询</el-button>
        </el-form-item>
      </el-form>
    </DashboardHero>

    <DashboardMetricGrid :cards="summary.cards" :accents="accents" @click="go" />

    <section class="live-course-panel">
      <div class="live-header">
        <div>
          <span class="kicker">CURRENT CLASS SIGNAL</span>
          <h2>当前课程态势</h2>
          <p>{{ currentCourseText }}</p>
        </div>
        <button class="refresh-orb" type="button" :disabled="loading" @click="fetchSummary">
          <span>{{ summary.current_course?.active_class_count || 0 }}</span>
          <small>上课班级</small>
        </button>
      </div>

      <div v-if="currentClasses.length" class="course-grid">
        <article
          v-for="item in currentClasses"
          :key="item.class_name"
          class="course-card"
        >
          <span class="class-name">{{ item.class_name }}</span>
          <strong>{{ item.course || item.subject }}</strong>
          <div class="course-meta">
            <span>{{ item.teacher }}</span>
            <small>{{ item.period }} · {{ item.time_range }}</small>
          </div>
        </article>
      </div>
      <div v-else class="live-empty">
        <strong>当前不在上课时段</strong>
        <span>系统会在作息时间命中后自动呈现各班实时课程。</span>
      </div>
    </section>

    <section class="chart-grid">
      <DashboardChart
        :title="`指定时间段教师课时 Top${topN}`"
        :eyebrow="`WORKLOAD TOP${topN}`"
        :option="teacherWorkloadOption"
        :empty="isEmpty(teacherWorkloadRows, 'lesson_count')"
        emptyText="暂无教师课时排行数据"
      />
      <DashboardChart
        :title="`班级学生规模 Top${topN}`"
        eyebrow="CLASS SIZE"
        :option="classSizeOption"
        :empty="isEmpty(classSizeRows, 'student_count')"
        emptyText="暂无班级规模数据"
      />
      <DashboardChart
        title="教务资源结构"
        eyebrow="RESOURCE MIX"
        :option="resourceMixOption"
        :empty="isEmpty(summary.charts?.resource_mix)"
        emptyText="暂无教务资源数据"
      />
      <DashboardChart
        title="文件上传状态"
        eyebrow="FILE UPLOAD STATUS"
        :option="fileUploadStatusOption"
        :empty="isEmpty(summary.charts?.file_upload_status)"
        emptyText="暂无文件上传记录"
      />

      <section class="coverage-panel">
        <DashboardPanelHeader eyebrow="SCHEDULE COVERAGE" title="课表覆盖说明" />
        <div class="coverage-number">
          <strong>{{ summary.covered_dates?.length || 0 }}</strong>
          <span>天有可统计课表</span>
        </div>
        <p>{{ summary.message || '暂无统计说明' }}</p>
        <div class="date-tags">
          <span v-for="date in summary.covered_dates" :key="date">{{ date }}</span>
        </div>
      </section>
    </section>

    <TeachingFileUploadPanel
      :cards="summary.cards"
      :pending-files="pendingFileList"
      :top-users="fileUploadTopUsers"
    />

    <!-- Insights Panel -->
    <DashboardInsights
      v-if="insights.length"
      :insights="insights"
      title="教学运行态势"
      eyebrow="OPERATION INSIGHTS"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import DashboardLoadingState from '@/components/dashboard/DashboardLoadingState.vue'
import ErrorState from '@/components/dashboard/ErrorState.vue'
import ForbiddenState from '@/components/dashboard/ForbiddenState.vue'
import DashboardInsights from '@/components/dashboard/DashboardInsights.vue'
import TeachingFileUploadPanel from '@/components/dashboard/TeachingFileUploadPanel.vue'
import DashboardHero from '@/components/dashboard/DashboardHero.vue'
import DashboardMetricGrid from '@/components/dashboard/DashboardMetricGrid.vue'
import DashboardPanelHeader from '@/components/dashboard/DashboardPanelHeader.vue'
import { getTeachingDashboardSummary } from '@/api/modules/dashboard'
import { baseHorizontalBarOption, basePieOption } from '@/utils/charting'
import { useDashboardRequest } from '@/composables/useDashboardRequest'

const router = useRouter()
const today = new Date()
const weekStart = new Date(today)
weekStart.setDate(today.getDate() - ((today.getDay() + 6) % 7))
const weekEnd = new Date(weekStart)
weekEnd.setDate(weekStart.getDate() + 6)
const fmt = (d) => {
  const year = d.getFullYear()
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const filters = reactive({
  start_date: fmt(weekStart),
  end_date: fmt(weekEnd),
  top_n: 5
})
const summary = ref({ cards: [], charts: {}, tables: {}, message: '', covered_dates: [] })
const { loading, errorState, forbidden, execute } = useDashboardRequest()
const accents = ['#38bdf8', '#fbbf24', '#34d399', '#f472b6', '#f87171']

const go = (route) => route && router.push(route)
const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0)
const currentClasses = computed(() => summary.value.current_course?.current_classes || [])
const topN = computed(() => summary.value.top_n || filters.top_n)
const teacherWorkloadRows = computed(() => summary.value.charts?.teacher_workload_rank || [])
const classSizeRows = computed(() => summary.value.charts?.class_size_rank || [])
const currentCourseText = computed(() => {
  const current = summary.value.current_course || {}
  if (!current.current_period) return '当前时间没有命中课表作息时段。'
  return `${current.current_period} · ${current.current_time_range || '未配置时间段'}`
})

const teacherWorkloadOption = computed(() => {
  const rows = [...teacherWorkloadRows.value].reverse()
  return baseHorizontalBarOption({
    yAxisData: rows.map(item => item.teacher_name),
    seriesData: rows.map(item => item.lesson_count),
    grid: { left: 82, right: 24, top: 24, bottom: 28 },
    color: ['#38bdf8']
  })
})

const classSizeOption = computed(() => {
  const rows = [...classSizeRows.value].reverse()
  return baseHorizontalBarOption({
    yAxisData: rows.map(item => item.class_name),
    seriesData: rows.map(item => item.student_count),
    grid: { left: 96, right: 24, top: 24, bottom: 28 },
    color: ['#fbbf24']
  })
})

const resourceMixOption = computed(() => basePieOption({
  color: ['#38bdf8', '#34d399', '#fbbf24'],
  data: summary.value.charts?.resource_mix || []
}))

const fileUploadStatusOption = computed(() => basePieOption({
  color: ['#f472b6', '#34d399'],
  data: summary.value.charts?.file_upload_status || []
}))

const fileUploadTopUsers = computed(() => summary.value.tables?.file_upload_top_users || [])
const pendingFileList = computed(() => summary.value.tables?.pending_file_list || [])
const insights = computed(() => summary.value.insights || [])

const fetchSummary = () => execute(
  () => getTeachingDashboardSummary(filters),
  data => { summary.value = data }
)

onMounted(fetchSummary)
</script>

<style scoped>
.command-dashboard {
  --dashboard-chart-columns-desktop: repeat(2, minmax(0, 1fr));

  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 10% 8%, rgba(56, 189, 248, 0.2), transparent 30%),
    radial-gradient(circle at 92% 14%, rgba(251, 191, 36, 0.14), transparent 28%);
}

.filter-console {
  min-width: 480px;
  padding: 14px 14px 0;
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.74);
}

.filter-console :deep(.el-form-item__label) {
  color: #cbd5e1;
}

.top-select {
  width: 110px;
}

.live-course-panel {
  padding: 20px;
  margin-bottom: 18px;
  border: 1px solid rgba(56, 189, 248, 0.28);
  border-radius: 8px;
  background:
    linear-gradient(145deg, rgba(8, 47, 73, 0.58), rgba(7, 15, 30, 0.92)),
    radial-gradient(circle at 8% 8%, rgba(34, 211, 238, 0.22), transparent 34%),
    radial-gradient(circle at 92% 12%, rgba(251, 191, 36, 0.16), transparent 30%);
  box-shadow: 0 22px 70px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.live-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 16px;
}

.live-header h2 {
  margin: 6px 0;
  color: #f8fafc;
  font-size: 26px;
  line-height: 1.12;
}

.refresh-orb {
  display: grid;
  width: 118px;
  height: 118px;
  place-items: center;
  color: #ecfeff;
  cursor: pointer;
  border: 1px solid rgba(103, 232, 249, 0.42);
  border-radius: 999px;
  background: radial-gradient(circle, rgba(34, 211, 238, 0.28), rgba(15, 23, 42, 0.88) 70%);
  box-shadow: 0 0 42px rgba(34, 211, 238, 0.22);
}

.refresh-orb:disabled {
  cursor: wait;
  opacity: 0.72;
}

.refresh-orb span {
  align-self: end;
  font-size: 34px;
  font-weight: 800;
  line-height: 1;
}

.refresh-orb small {
  align-self: start;
  margin-top: 6px;
  color: #bae6fd;
}

.course-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.course-card {
  position: relative;
  min-height: 132px;
  padding: 15px;
  border: 1px solid rgba(125, 211, 252, 0.24);
  border-radius: 8px;
  background: linear-gradient(155deg, rgba(15, 23, 42, 0.92), rgba(14, 116, 144, 0.18));
  overflow: hidden;
}

.course-card::after {
  position: absolute;
  right: -34px;
  bottom: -38px;
  width: 104px;
  height: 104px;
  content: "";
  border-radius: 999px;
  background: rgba(34, 211, 238, 0.18);
  filter: blur(8px);
}

.class-name,
.course-card strong,
.course-meta {
  position: relative;
  z-index: 1;
}

.class-name {
  color: #67e8f9;
  font-size: 13px;
  font-weight: 700;
}

.course-card strong {
  display: block;
  margin-top: 12px;
  color: #f8fafc;
  font-size: 24px;
  line-height: 1.08;
}

.course-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 14px;
  color: #cbd5e1;
  font-size: 13px;
}

.course-meta small {
  color: #94a3b8;
}

.live-empty {
  display: grid;
  min-height: 150px;
  place-content: center;
  text-align: center;
  border: 1px dashed rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.36);
}

.live-empty strong {
  color: #f8fafc;
  font-size: 18px;
}

.live-empty span {
  margin-top: 8px;
  color: rgba(226, 232, 240, 0.68);
}

.coverage-panel {
  min-height: 320px;
  padding: 18px;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
  box-shadow: 0 18px 50px rgba(0, 0, 0, 0.26);
}

.coverage-number {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
}

.coverage-number strong {
  color: #f8fafc;
  font-size: 56px;
  line-height: 1;
}

.coverage-number span {
  color: #cbd5e1;
}

.date-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.date-tags span {
  padding: 6px 9px;
  color: #bfdbfe;
  border: 1px solid rgba(96, 165, 250, 0.28);
  border-radius: 999px;
  background: rgba(30, 64, 175, 0.2);
  font-size: 12px;
}

@media (max-width: 980px) {
  .filter-console {
    min-width: 0;
  }

  .live-header {
    align-items: flex-start;
    flex-direction: column;
  }

}
</style>
