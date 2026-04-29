<template>
  <div class="command-dashboard class-theme">
    <header class="hero-band">
      <div>
        <span class="kicker">Class Intelligence</span>
        <h1>{{ classInfo.class_name || '班级驾驶舱' }}</h1>
        <p>班级人数结构、学习活动、德育表现、出勤事务和生日关怀汇总。</p>
      </div>
      <div v-if="_isManager" class="filter-console">
        <el-select v-model="selectedClassId" placeholder="选择班级" @change="onClassChange">
          <el-option v-for="c in classList" :key="c.class_id" :label="c.class_name" :value="c.class_id" />
        </el-select>
      </div>
      <div class="time-chip">
        <span>数据更新</span>
        <strong>{{ summary.updated_at || '-' }}</strong>
      </div>
    </header>

    <section class="metric-grid">
      <button
        v-for="(card, index) in summary.cards"
        :key="card.label"
        class="metric-card"
        :style="{ '--accent': accents[index % accents.length] }"
        type="button"
        @click="go(card.route)"
      >
        <span>{{ card.label }}</span>
        <strong>{{ card.value }}<small>{{ card.unit }}</small></strong>
        <i></i>
      </button>
    </section>

    <section class="chart-grid">
      <DashboardChart
        title="班级性别结构"
        eyebrow="GENDER MIX"
        :option="genderMixOption"
        :empty="isEmpty(summary.charts?.gender_mix)"
      />
      <DashboardChart
        title="德育分数段分布"
        eyebrow="SCORE BAND"
        :option="scoreBandOption"
        :empty="isEmpty(summary.charts?.score_band)"
      />
    </section>

    <section class="info-panel">
      <div class="panel-section">
        <div class="panel-header">
          <span>LOW SCORE ALERT</span>
          <h3>低分学生</h3>
        </div>
        <div v-if="lowStudents.length" class="risk-list">
          <div v-for="s in lowStudents" :key="s.student_id" class="risk-row">
            <span>{{ s.name }}</span>
            <b>{{ s.total_score }} 分</b>
          </div>
        </div>
        <div v-else class="empty-strip">本班暂无低分学生。</div>
      </div>

      <div class="panel-section">
        <div class="panel-header">
          <span>BIRTHDAY CARE</span>
          <h3>本月生日</h3>
        </div>
        <div v-if="birthdayMonth.length" class="birthday-list">
          <div v-for="s in birthdayMonth" :key="s.name" class="birthday-item">
            <span>{{ s.name }}</span>
            <small>{{ s.birthday }}</small>
          </div>
        </div>
        <div v-else class="empty-strip">本月暂无学生生日。</div>
      </div>

      <div class="panel-section">
        <div class="panel-header">
          <span>THIS WEEK</span>
          <h3>本周生日</h3>
        </div>
        <div v-if="birthdayWeek.length" class="birthday-list highlight">
          <div v-for="s in birthdayWeek" :key="s.name" class="birthday-item">
            <span>{{ s.name }}</span>
            <small>{{ s.birthday }}</small>
          </div>
        </div>
        <div v-else class="empty-strip">本周暂无学生生日。</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'
import { getClassDashboardSummary } from '@/api/modules/dashboard'
import api from '@/utils/api'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const summary = ref({ cards: [], charts: {}, tables: {}, class_info: {} })
const classList = ref([])
const selectedClassId = ref(null)
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

const genderMixOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#34d399', '#f472b6', '#94a3b8'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#cbd5e1' } },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '44%'],
    label: { color: '#e2e8f0', formatter: '{b}\n{c}' },
    itemStyle: { borderColor: '#07111f', borderWidth: 3 },
    data: summary.value.charts?.gender_mix || []
  }]
}))

const scoreBandOption = computed(() => ({
  backgroundColor: 'transparent',
  color: ['#fb7185', '#34d399', '#94a3b8'],
  tooltip: { trigger: 'item' },
  legend: { bottom: 0, textStyle: { color: '#cbd5e1' } },
  series: [{
    type: 'pie',
    radius: ['45%', '70%'],
    center: ['50%', '44%'],
    label: { color: '#e2e8f0', formatter: '{b}\n{c}' },
    itemStyle: { borderColor: '#07111f', borderWidth: 3 },
    data: summary.value.charts?.score_band || []
  }]
}))

const fetchClassList = async () => {
  if (!_isManager.value) return
  const res = await api.get('/api/moral/admin/classes')
  if (res.success) {
    classList.value = res.data.filter(c => c.is_active === 1)
  }
}

const fetchSummary = async () => {
  const params = selectedClassId.value ? { class_id: selectedClassId.value } : {}
  const res = await getClassDashboardSummary(params)
  if (res.success) {
    summary.value = res.data
    if (!selectedClassId.value && res.data.class_info?.class_id) {
      selectedClassId.value = res.data.class_info.class_id
    }
  }
}

onMounted(() => {
  fetchClassList()
  fetchSummary()
})
</script>

<style scoped>
.command-dashboard {
  min-height: calc(100vh - 80px);
  padding: 24px;
  color: #e2e8f0;
  background:
    linear-gradient(135deg, rgba(8, 16, 32, 0.98), rgba(12, 22, 42, 0.96)),
    radial-gradient(circle at 10% 8%, rgba(52, 211, 153, 0.2), transparent 30%),
    radial-gradient(circle at 90% 14%, rgba(244, 114, 182, 0.14), transparent 28%);
}

.hero-band {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  padding: 26px;
  margin-bottom: 18px;
  border: 1px solid rgba(125, 211, 252, 0.25);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.88), rgba(2, 6, 23, 0.72));
}

.kicker {
  color: #34d399;
  font-size: 12px;
}

h1 {
  margin: 8px 0;
  color: #f8fafc;
  font-size: 40px;
  line-height: 1.08;
}

p {
  max-width: 720px;
  margin: 0;
  color: rgba(226, 232, 240, 0.72);
}

.filter-console {
  min-width: 180px;
}

.filter-console :deep(.el-input__wrapper) {
  background: rgba(15, 23, 42, 0.74);
}

.time-chip {
  min-width: 180px;
  padding: 14px 16px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.72);
}

.time-chip span {
  display: block;
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.time-chip strong {
  color: #f8fafc;
  font-size: 16px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.metric-card {
  position: relative;
  min-height: 100px;
  padding: 16px;
  color: #e2e8f0;
  text-align: left;
  cursor: pointer;
  border: 1px solid color-mix(in srgb, var(--accent), transparent 62%);
  border-radius: 8px;
  background: linear-gradient(155deg, rgba(15, 23, 42, 0.98), rgba(15, 23, 42, 0.62));
  overflow: hidden;
}

.metric-card span {
  color: #94a3b8;
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin-top: 12px;
  color: #f8fafc;
  font-size: 28px;
  line-height: 1;
}

.metric-card small {
  margin-left: 4px;
  color: #cbd5e1;
  font-size: 13px;
}

.metric-card i {
  position: absolute;
  right: -30px;
  bottom: -34px;
  width: 90px;
  height: 90px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--accent), transparent 74%);
  filter: blur(8px);
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.info-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
}

.panel-section {
  padding: 18px;
  border: 1px solid rgba(99, 179, 237, 0.24);
  border-radius: 8px;
  background: linear-gradient(145deg, rgba(12, 26, 48, 0.94), rgba(7, 15, 30, 0.9));
}

.panel-header span {
  color: #67e8f9;
  font-size: 12px;
}

.panel-header h3 {
  margin: 4px 0 14px;
  color: #e5f6ff;
  font-size: 16px;
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

.empty-strip {
  padding: 14px;
  color: rgba(226, 232, 240, 0.66);
  border: 1px dashed rgba(148, 163, 184, 0.25);
  border-radius: 6px;
  text-align: center;
}

@media (max-width: 900px) {
  .hero-band {
    flex-direction: column;
    align-items: stretch;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  h1 {
    font-size: 34px;
  }
}
</style>
