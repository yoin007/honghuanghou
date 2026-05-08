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
        <el-select v-model="selectedGradeId" placeholder="选择年级" @change="onGradeChange">
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
        :empty="isEmpty(summary.charts?.class_comparison)"
        emptyText="暂无班级对比数据"
      />
      <DashboardChart
        title="德育分数段分布"
        eyebrow="SCORE BAND"
        :option="scoreBandOption"
        :empty="isEmpty(summary.charts?.score_band)"
        emptyText="暂无德育分分布数据"
      />
    </section>

    <section class="info-panel">
      <DashboardPanelSection eyebrow="LOW SCORE ALERT" title="低分学生">
        <div v-if="lowStudents.length" class="risk-list">
          <div v-for="s in lowStudents" :key="s.student_id" class="risk-row">
            <span>{{ s.name }} ({{ s.class_name }})</span>
            <b>{{ s.total_score }} 分</b>
          </div>
        </div>
        <DashboardEmptyStrip v-else text="本年级暂无低分学生。" />
      </DashboardPanelSection>

      <DashboardPanelSection variant="attendance">
        <DashboardLeaveList
          :students="leaveStudents"
          mode="grade"
          eyebrow="ATTENDANCE STATUS"
          title="当前请假学生"
          empty-text="本年级当前无请假学生，出勤正常。"
        />
      </DashboardPanelSection>

      <DashboardPanelSection eyebrow="BIRTHDAY CARE" title="本月生日">
        <div v-if="birthdayMonth.length" class="birthday-list">
          <div v-for="s in birthdayMonth" :key="s.name" class="birthday-item">
            <span>{{ s.name }} ({{ s.class_name }})</span>
            <small>{{ s.birthday }}</small>
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
import { fetchGradeDashboardSummary, fetchGradeList } from '@/api/modules/dashboard'

const router = useRouter()
const authStore = useAuthStore()

const summary = ref({ cards: [], charts: {}, tables: {} })
const gradeList = ref([])
const selectedGradeId = ref(null)
const gradeInfo = ref({})
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

const classComparisonOption = computed(() => {
  const data = summary.value.charts?.class_comparison || []
  if (!data.length) return {}
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: data.map(d => d.class_name) },
    yAxis: { type: 'value' },
    series: [
      {
        name: '平均德育分',
        type: 'bar',
        data: data.map(d => d.avg_score),
        itemStyle: { color: '#409EFF' }
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
  if (grade) gradeInfo.value = grade
  fetchSummary()
}

async function loadGradeList() {
  try {
    const res = await fetchGradeList()
    if (res.success) {
      gradeList.value = res.data || []
      if (gradeList.value.length > 0 && !selectedGradeId.value) {
        selectedGradeId.value = gradeList.value[0].grade_id
        gradeInfo.value = gradeList.value[0]
        fetchSummary()
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
}

.filter-console {
  margin-top: 16px;
}

.risk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.risk-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--accent-light);
  border-radius: 4px;
}

.birthday-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.birthday-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.birthday-list.highlight .birthday-item {
  background: var(--accent-light);
}
</style>