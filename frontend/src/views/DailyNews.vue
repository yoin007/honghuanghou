<template>
  <div class="daily-news-page">
    <!-- 顶部标题条 -->
    <header class="page-header">
      <div class="header-left">
        <div class="header-icon">📰</div>
        <div class="header-text">
          <h1>每日早报</h1>
          <p class="date-line">{{ displayDate }} · {{ displayWeekday }}</p>
        </div>
      </div>
      <div class="header-actions">
        <el-date-picker
          v-model="selectedDate"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="选择日期"
          size="large"
          :clearable="false"
          :disabled-date="disabledDate"
          :cell-class-name="cellClassName"
          class="date-picker"
          @change="handleDateChange"
        />
        <el-button
          v-if="isToday"
          :icon="Refresh"
          circle
          plain
          size="large"
          :loading="refreshing"
          @click="handleRefresh"
          title="强制刷新今日数据"
        />
      </div>
    </header>

    <!-- 加载态 -->
    <div v-if="loading" class="skeleton-wrap">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 出错态 / 空态 -->
    <el-empty
      v-else-if="loadError"
      :image-size="120"
      class="error-empty"
    >
      <template #description>
        <p class="empty-desc">{{ loadError }}</p>
      </template>
      <div class="empty-actions">
        <el-button type="primary" @click="fetchData(selectedDate)">重试</el-button>
        <el-button v-if="!isToday" @click="jumpToToday">返回今日</el-button>
      </div>
    </el-empty>

    <!-- 内容态 -->
    <div v-else-if="data" class="news-grid">
      <!-- 左列：头图 + 微语 + 音频 -->
      <aside class="side-col">
        <div v-if="headImage" class="head-image-card">
          <img :src="headImage" :alt="displayDate" @error="onImgError" />
        </div>

        <div v-if="weiyu" class="weiyu-card">
          <div class="weiyu-quote">“</div>
          <p class="weiyu-text">{{ weiyu }}</p>
          <div class="weiyu-sign">—— 今日微语</div>
        </div>

        <div v-if="audio" class="audio-card">
          <div class="audio-title">
            <span class="audio-icon">🔊</span>
            <span>早报音频</span>
          </div>
          <audio :src="audio" controls preload="none" class="audio-player" />
        </div>
      </aside>

      <!-- 右列：新闻列表 -->
      <section class="news-col">
        <div class="news-card">
          <div class="news-card-header">
            <span class="news-badge">今日要闻</span>
            <span class="news-count">共 {{ newsList.length }} 条</span>
          </div>

          <ol v-if="newsList.length" class="news-list">
            <li
              v-for="(item, idx) in newsList"
              :key="idx"
              class="news-item"
            >
              <span class="news-index">{{ String(idx + 1).padStart(2, '0') }}</span>
              <span class="news-text">{{ item }}</span>
            </li>
          </ol>

          <el-empty v-else description="今日暂无新闻" />
        </div>

        <p v-if="updatedAt" class="update-tip">
          数据首次入库时间：{{ updatedAt }}（同一天不再重复请求外部接口）
        </p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { dailyNewsApi } from '@/api/modules/dailyNews'

const loading = ref(false)
const refreshing = ref(false)
const loadError = ref('')
const data = ref(null)

// 当前查看的日期（YYYY-MM-DD），默认今日
const todayStr = formatDate(new Date())
const selectedDate = ref(todayStr)
// 已缓存的日期集合（用于 DatePicker 高亮）
const cachedDates = ref(new Set())

const isToday = computed(() => selectedDate.value === todayStr)

// —— 派生字段 ——
const headImage = computed(() => data.value?.head_image || data.value?.image || '')
const audio = computed(() => data.value?.audio || '')
const weiyu = computed(() => data.value?.weiyu || '')
const newsList = computed(() => Array.isArray(data.value?.news) ? data.value.news : [])
const updatedAt = computed(() => data.value?.updated_at || data.value?.date || '')

const displayDate = computed(() => {
  const raw = data.value?.date || selectedDate.value
  const parts = String(raw).split('-')
  if (parts.length === 3) return `${parts[0]}年${Number(parts[1])}月${Number(parts[2])}日`
  return raw
})

const displayWeekday = computed(() => {
  const raw = data.value?.date || selectedDate.value
  const d = raw ? new Date(String(raw).replace(/-/g, '/')) : new Date()
  return ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'][d.getDay()]
})

function formatDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// DatePicker：禁用未来日期
function disabledDate(date) {
  return date && date.getTime() > new Date(todayStr.replace(/-/g, '/')).getTime() + 86400000 - 1
}

// DatePicker：高亮已缓存的日期
function cellClassName(date) {
  return cachedDates.value.has(formatDate(date)) ? 'has-cached' : ''
}

async function loadCachedDates() {
  try {
    const res = await dailyNewsApi.listDates(120)
    const list = Array.isArray(res?.data) ? res.data : []
    cachedDates.value = new Set(list)
  } catch (err) {
    // 静默失败，不影响主流程
    console.warn('加载已缓存日期失败:', err)
  }
}

async function fetchData(date = selectedDate.value, { force = false } = {}) {
  const flag = force ? refreshing : loading
  flag.value = true
  loadError.value = ''
  data.value = null
  try {
    const params = {}
    if (date && date !== todayStr) params.date = date
    if (force) params.force = 1
    const res = await dailyNewsApi.getDailyNews(params)
    const payload = res?.data
    if (res?.success && payload) {
      data.value = payload
      if (force) ElMessage.success('已刷新为最新数据')
      // 命中一次就把这个日期加入缓存标记
      if (payload.date) cachedDates.value.add(payload.date)
    } else {
      loadError.value = res?.message || '数据加载失败'
    }
  } catch (err) {
    console.error('每日早报加载失败:', err)
    const status = err?.response?.status
    if (status === 404) {
      // 历史日期无数据：明确空态提示，不当错误
      loadError.value = `${date} 暂无早报数据\n（该日期未生成过缓存，请选择带 · 标记的日期查看）`
    } else {
      loadError.value = err?.response?.data?.detail || err?.message || '每日早报获取失败，请稍后再试'
    }
  } finally {
    flag.value = false
  }
}

function handleDateChange(val) {
  if (!val) return
  fetchData(val)
}

function handleRefresh() {
  fetchData(todayStr, { force: true })
}

function jumpToToday() {
  selectedDate.value = todayStr
  fetchData(todayStr)
}

function onImgError(e) {
  e.target.style.display = 'none'
}

onMounted(() => {
  loadCachedDates()
  fetchData()
})
</script>

<style scoped>
.daily-news-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px 48px;
  color: #1f2937;
}

/* 头部 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-radius: 16px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 60%, #ec4899 100%);
  color: #fff;
  box-shadow: 0 10px 30px rgba(99, 102, 241, 0.25);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(6px);
  display: grid;
  place-items: center;
  font-size: 30px;
}

.header-text h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 1px;
}

.date-line {
  margin: 4px 0 0;
  font-size: 13px;
  opacity: 0.85;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-actions :deep(.el-button) {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.12);
}

.header-actions :deep(.el-button:hover) {
  background: rgba(255, 255, 255, 0.25);
}

.date-picker {
  width: 168px;
}

.header-actions :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.18);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.35) inset;
}

.header-actions :deep(.el-input__inner),
.header-actions :deep(.el-input__prefix-inner) {
  color: #fff;
}

.header-actions :deep(.el-input__inner)::placeholder {
  color: rgba(255, 255, 255, 0.8);
}

.empty-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.empty-desc {
  margin: 0;
  white-space: pre-line;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
}

/* DatePicker 弹层：已缓存日期加个小圆点，用户一眼能看出哪些日期有数据 */
:global(.el-picker-panel .has-cached .el-date-table-cell__text)::after {
  content: '';
  position: absolute;
  bottom: 3px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #6366f1;
}
:global(.el-picker-panel .has-cached .el-date-table-cell) {
  position: relative;
}

/* 骨架/空态 */
.skeleton-wrap,
.error-empty {
  margin-top: 24px;
  padding: 24px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.04);
}

/* 主内容双列布局 */
.news-grid {
  margin-top: 20px;
  display: grid;
  grid-template-columns: minmax(260px, 340px) 1fr;
  gap: 20px;
  align-items: start;
}

.side-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 头图 */
.head-image-card {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
  background: #f3f4f6;
}

.head-image-card img {
  display: block;
  width: 100%;
  height: auto;
  object-fit: cover;
  transition: transform 0.4s ease;
}

.head-image-card:hover img {
  transform: scale(1.02);
}

/* 微语 */
.weiyu-card {
  position: relative;
  padding: 24px 22px 20px;
  border-radius: 16px;
  background: linear-gradient(135deg, #fff7ed 0%, #ffe4e6 100%);
  box-shadow: 0 4px 18px rgba(251, 146, 60, 0.12);
}

.weiyu-quote {
  position: absolute;
  top: 4px;
  left: 12px;
  font-size: 52px;
  line-height: 1;
  color: #fb923c;
  opacity: 0.35;
  font-family: serif;
}

.weiyu-text {
  position: relative;
  margin: 12px 0 8px;
  font-size: 16px;
  line-height: 1.75;
  color: #7c2d12;
  font-weight: 500;
}

.weiyu-sign {
  text-align: right;
  font-size: 12px;
  color: #9a3412;
  opacity: 0.75;
}

/* 音频 */
.audio-card {
  padding: 18px 20px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.05);
}

.audio-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #374151;
  font-weight: 600;
  margin-bottom: 10px;
}

.audio-icon {
  font-size: 18px;
}

.audio-player {
  width: 100%;
  height: 40px;
}

/* 新闻卡片 */
.news-card {
  padding: 24px 26px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.05);
}

.news-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 14px;
  margin-bottom: 8px;
  border-bottom: 1px dashed #e5e7eb;
}

.news-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 1px;
}

.news-count {
  font-size: 12px;
  color: #9ca3af;
}

.news-list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
}

.news-item {
  display: flex;
  gap: 14px;
  padding: 12px 4px;
  border-bottom: 1px solid #f3f4f6;
  transition: background 0.2s ease;
  border-radius: 8px;
}

.news-item:hover {
  background: #f9fafb;
}

.news-item:last-child {
  border-bottom: none;
}

.news-index {
  flex-shrink: 0;
  width: 28px;
  font-weight: 700;
  color: #a78bfa;
  font-variant-numeric: tabular-nums;
}

.news-text {
  color: #1f2937;
  line-height: 1.7;
  font-size: 14.5px;
}

.update-tip {
  margin: 14px 4px 0;
  font-size: 12px;
  color: #9ca3af;
  text-align: right;
}

/* 移动端适配 */
@media (max-width: 900px) {
  .news-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    padding: 16px 18px;
  }

  .header-text h1 {
    font-size: 20px;
  }

  .header-icon {
    width: 46px;
    height: 46px;
    font-size: 24px;
  }
}

@media (max-width: 480px) {
  .daily-news-page {
    padding: 16px 12px 32px;
  }

  .news-card {
    padding: 18px 16px;
  }

  .news-text {
    font-size: 14px;
  }
}
</style>
