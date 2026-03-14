<template>
  <div class="loudpk-container">
    <el-card class="box-card">
      <div class="card-header">
        <h2>大声PK</h2>
        <div class="controls">
          <el-select
            v-model="selectedMicId"
            placeholder="选择麦克风"
            :disabled="listening || initializing || micDevices.length === 0"
            class="mic-select"
          >
            <el-option
              v-for="device in micDevices"
              :key="device.deviceId"
              :label="device.label || `麦克风 ${device.deviceId.slice(0, 6)}`"
              :value="device.deviceId"
            />
          </el-select>
          <el-button
            type="primary"
            size="large"
            :loading="initializing"
            @click="toggleListening"
          >
            {{ listening ? '停止测量' : '开始测量' }}
          </el-button>
          <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
        </div>
      </div>

      <div class="meter-container">
        <div class="value-display">
          <span class="value">{{ currentDb.toFixed(1) }}</span>
          <span class="unit">dB</span>
        </div>
        <div class="bar-wrapper">
          <div class="bar-background">
            <div
              class="bar-foreground"
              :style="{ width: barWidth + '%' }"
            ></div>
          </div>
        </div>
        <div class="hint">
          请对着麦克风大声喊，看看谁的分贝最高
        </div>
      </div>
    </el-card>
    <el-card class="box-card chart-card">
      <div class="chart-header">
        班级实时PK柱状图
      </div>
      <div ref="chartRef" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import api from '../utils/api'

const listening = ref(false)
const initializing = ref(false)
const currentDb = ref(0)
const errorMessage = ref('')
const classCode = ref('')
const classStats = ref([])
const chartRef = ref(null)
const micDevices = ref([])
const selectedMicId = ref('')

let audioContext
let mediaStream
let analyser
let dataArray
let rafId
let syncInterval
let statsInterval

let chartInstance

const getClassCode = () => {
  const cookie = document.cookie.split('; ').find(row => row.startsWith('classCode='))
  return cookie ? cookie.split('=')[1] : ''
}

const refreshMicDevices = async () => {
  if (!(navigator.mediaDevices && navigator.mediaDevices.enumerateDevices)) {
    micDevices.value = []
    return
  }

  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    const inputs = devices.filter(d => d.kind === 'audioinput')
    micDevices.value = inputs
    if (!selectedMicId.value && inputs.length > 0) {
      selectedMicId.value = inputs[0].deviceId
    } else if (selectedMicId.value && inputs.length > 0) {
      const stillExists = inputs.some(d => d.deviceId === selectedMicId.value)
      if (!stillExists) {
        selectedMicId.value = inputs[0].deviceId
      }
    }
  } catch (error) {
    console.error('Failed to enumerate devices:', error)
    micDevices.value = []
  }
}

const isLocalhost = () => {
  const host = window.location.hostname
  return host === 'localhost' || host === '127.0.0.1' || host === '::1'
}

const checkMicAvailability = () => {
  if (!window.isSecureContext && !isLocalhost()) {
    return {
      ok: false,
      level: 'warning',
      message: '当前不是安全环境(https/localhost)，大概率无法弹出麦克风权限'
    }
  }

  const hasStandard = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
  const hasLegacy = !!(
    navigator.getUserMedia ||
    navigator.webkitGetUserMedia ||
    navigator.mozGetUserMedia ||
    navigator.msGetUserMedia
  )

  if (!hasStandard && !hasLegacy) {
    return {
      ok: false,
      level: 'error',
      message: '当前浏览器不支持麦克风采集，请更换 Chrome/Edge 或使用 https/localhost'
    }
  }

  return { ok: true, level: '', message: '' }
}

const getMicErrorMessage = (error) => {
  const name = error?.name
  const messageText =
    typeof error === 'string'
      ? error
      : typeof error?.message === 'string'
        ? error.message
        : ''

  const normalizedMessage = messageText.toLowerCase()

  if (
    normalizedMessage.includes('object can not be found') ||
    normalizedMessage.includes('object cannot be found') ||
    normalizedMessage.includes('notfounderror') ||
    normalizedMessage.includes('not found')
  ) {
    return '未检测到麦克风设备，请检查设备是否连接，或系统是否已禁用麦克风'
  }

  if (name === 'NotAllowedError' || name === 'PermissionDeniedError') {
    return '麦克风权限被拒绝，请在浏览器站点设置中允许麦克风'
  }
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError') {
    return '未检测到麦克风设备，请检查设备是否连接'
  }
  if (name === 'NotReadableError' || name === 'TrackStartError') {
    return '麦克风被占用或无法读取，请关闭其他占用麦克风的软件后重试'
  }
  if (name === 'SecurityError') {
    return '当前环境不允许使用麦克风，请使用 https 或 localhost 访问'
  }
  return '无法访问麦克风，请检查浏览器权限设置'
}

const syncDecibel = async () => {
  if (!classCode.value) return
  try {
    await api.post('/api/loudpk', {
      class_code: classCode.value,
      decibel: currentDb.value
    })
  } catch (error) {
    console.error('Error syncing loudpk value:', error)
  }
}

const startSync = () => {
  if (syncInterval) {
    clearInterval(syncInterval)
  }
  syncInterval = setInterval(syncDecibel, 1000)
}

const getItemClassCode = (item) => {
  const value = item?.class_code ?? item?.classCode ?? item?.name ?? ''
  if (typeof value === 'string') return value.trim()
  if (value == null) return ''
  return String(value).trim()
}

const getItemDecibel = (item) => {
  const candidates = [item?.decibel, item?.value, item?.max_decibel, item?.maxDecibel]
  for (const candidate of candidates) {
    if (typeof candidate === 'number' && Number.isFinite(candidate)) return candidate
    if (typeof candidate === 'string') {
      const parsed = Number.parseFloat(candidate)
      if (Number.isFinite(parsed)) return parsed
    }
  }
  return 0
}

const hashString = (text) => {
  let hash = 0
  for (let i = 0; i < text.length; i++) {
    hash = (hash << 5) - hash + text.charCodeAt(i)
    hash |= 0
  }
  return Math.abs(hash)
}

const barColors = [
  '#409EFF',
  '#67C23A',
  '#E6A23C',
  '#F56C6C',
  '#909399',
  '#4E79A7',
  '#59A14F',
  '#9C755F',
  '#B07AA1',
  '#EDC948'
]

const updateChart = () => {
  if (!chartInstance) return
  const rows = (Array.isArray(classStats.value) ? classStats.value : [])
    .map(item => ({
      classCode: getItemClassCode(item),
      value: getItemDecibel(item)
    }))
    .filter(item => item.classCode)
    .sort((a, b) =>
      a.classCode.localeCompare(b.classCode, undefined, { numeric: true, sensitivity: 'base' })
    )

  const classes = rows.map(item => item.classCode)
  const values = rows.map((item) => {
    const value = Number.isFinite(item.value) ? item.value : 0
    const rounded = Math.round(value * 10) / 10
    const color = barColors[hashString(item.classCode) % barColors.length]
    return {
      value: rounded,
      itemStyle: { color }
    }
  })

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params) => {
        const list = Array.isArray(params) ? params : []
        if (list.length === 0) return ''
        const title = list[0]?.axisValue ?? ''
        const lines = [title]
        for (const p of list) {
          const raw = typeof p?.value === 'object' ? p?.value?.value : p?.value
          const n = Number(raw)
          const v = Number.isFinite(n) ? n.toFixed(1) : '0.0'
          const name = p?.seriesName ? `${p.seriesName}: ` : ''
          lines.push(`${p.marker || ''}${name}${v} dB`)
        }
        return lines.join('<br/>')
      }
    },
    xAxis: {
      type: 'category',
      data: classes,
      axisLabel: {
        color: '#606266'
      }
    },
    yAxis: {
      type: 'value',
      name: 'dB',
      axisLabel: {
        color: '#606266'
      },
      min: 0
    },
    series: [
      {
        name: '分贝',
        type: 'bar',
        data: values,
        barWidth: '50%',
        label: {
          show: true,
          position: 'top',
          formatter: (params) => {
            const raw = typeof params?.value === 'object' ? params?.value?.value : params?.value
            const n = Number(raw)
            return Number.isFinite(n) ? n.toFixed(1) : '0.0'
          }
        }
      }
    ]
  }

  chartInstance.setOption(option, { notMerge: true })
}

const fetchStats = async () => {
  try {
    const response = await api.get('/api/loudpk', {
      params: { _ts: Date.now() }
    })
    const data = response.data
    let list = []
    if (Array.isArray(data)) {
      list = data
    } else if (data && Array.isArray(data.stats)) {
      list = data.stats
    } else if (data && Array.isArray(data.data)) {
      list = data.data
    }
    classStats.value = list
    if (chartInstance) {
      updateChart()
    }
  } catch (error) {
    console.error('Error fetching loudpk stats:', error)
  }
}

const initChart = () => {
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  updateChart()
}

const stopAudio = () => {
  listening.value = false
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  if (syncInterval) {
    clearInterval(syncInterval)
    syncInterval = null
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop())
    mediaStream = null
  }
  if (audioContext) {
    audioContext.close()
    audioContext = null
  }
}

const updateVolume = () => {
  if (!analyser || !dataArray) return

  analyser.getByteTimeDomainData(dataArray)

  let sum = 0
  for (let i = 0; i < dataArray.length; i++) {
    const value = (dataArray[i] - 128) / 128
    sum += value * value
  }

  const rms = Math.sqrt(sum / dataArray.length)
  const db = 20 * Math.log10(rms || 0.000001) + 100
  currentDb.value = Math.max(0, Math.min(db, 120))

  rafId = requestAnimationFrame(updateVolume)
}

const startAudio = async () => {
  initializing.value = true
  errorMessage.value = ''

  try {
    if (!classCode.value) {
      throw new Error('no classCode')
    }

    const check = checkMicAvailability()
    if (!check.ok) {
      errorMessage.value = check.message
      if (check.level === 'warning') {
        ElMessage.warning(check.message)
      } else {
        ElMessage.error(check.message)
        stopAudio()
        return
      }
    }

    if (typeof navigator === 'undefined') {
      throw new Error('navigator is undefined')
    }

    let getUserMediaFn

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      getUserMediaFn = (constraints) => navigator.mediaDevices.getUserMedia(constraints)
      await refreshMicDevices()
    } else {
      const legacyGetUserMedia =
        navigator.getUserMedia ||
        navigator.webkitGetUserMedia ||
        navigator.mozGetUserMedia ||
        navigator.msGetUserMedia

      if (!legacyGetUserMedia) {
        throw new Error('getUserMedia is not supported in this browser')
      }

      getUserMediaFn = (constraints) =>
        new Promise((resolve, reject) => {
          legacyGetUserMedia.call(navigator, constraints, resolve, reject)
        })
    }

    const audioConstraints = selectedMicId.value
      ? {
          deviceId: { exact: selectedMicId.value },
          echoCancellation: true,
          noiseSuppression: true
        }
      : {
          echoCancellation: true,
          noiseSuppression: true
        }

    mediaStream = await getUserMediaFn({ audio: audioConstraints })

    const AudioCtx = window.AudioContext || (window).webkitAudioContext
    audioContext = new AudioCtx()
    const source = audioContext.createMediaStreamSource(mediaStream)
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 2048
    const bufferLength = analyser.fftSize
    dataArray = new Uint8Array(bufferLength)

    source.connect(analyser)

    listening.value = true
    updateVolume()
    syncDecibel()
    startSync()
  } catch (error) {
    console.error('Failed to access microphone:', error)
    const message = getMicErrorMessage(error)
    errorMessage.value = message
    ElMessage.error(message)
    stopAudio()
  } finally {
    initializing.value = false
  }
}

const toggleListening = () => {
  if (listening.value) {
    stopAudio()
  } else {
    if (!classCode.value) {
      classCode.value = getClassCode()
    }
    if (!classCode.value) {
      ElMessage.error('请先选择班级')
      return
    }
    startAudio()
  }
}

const barWidth = computed(() => {
  const minDb = 40
  const maxDb = 110
  const value = Math.max(minDb, Math.min(currentDb.value, maxDb))
  return ((value - minDb) / (maxDb - minDb)) * 100
})

onMounted(() => {
  classCode.value = getClassCode()
  refreshMicDevices()
  initChart()
  fetchStats()
  statsInterval = setInterval(fetchStats, 3000)
  window.addEventListener('resize', () => {
    if (chartInstance) {
      chartInstance.resize()
    }
  })
})

onUnmounted(() => {
  stopAudio()
  if (statsInterval) {
    clearInterval(statsInterval)
    statsInterval = null
  }
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
})
</script>

<style scoped>
.loudpk-container {
  padding: 1rem;
}

.box-card {
  max-width: 800px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.card-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.controls {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.mic-select {
  width: 240px;
}

.error-text {
  color: #f56c6c;
  font-size: 14px;
}

.meter-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.value-display {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

.value {
  font-size: 3rem;
  font-weight: bold;
}

.unit {
  font-size: 1.2rem;
  color: #909399;
}

.bar-wrapper {
  width: 100%;
  max-width: 600px;
}

.bar-background {
  width: 100%;
  height: 24px;
  border-radius: 12px;
  background: #f2f6fc;
  overflow: hidden;
}

.bar-foreground {
  height: 100%;
  background: linear-gradient(90deg, #67c23a 0%, #e6a23c 50%, #f56c6c 100%);
  border-radius: 12px;
  transition: width 0.1s ease-out;
}

.hint {
  color: #909399;
  font-size: 0.9rem;
}

.chart-card {
  max-width: 800px;
  margin: 20px auto 0;
}

.chart-header {
  font-size: 1.2rem;
  font-weight: bold;
  margin-bottom: 15px;
  text-align: center;
}

.chart-container {
  width: 100%;
  height: 400px;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .loudpk-container {
    padding: 10px;
  }

  .card-header {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
    margin-bottom: 1rem;
  }
  
  .card-header h2 {
    text-align: center;
    font-size: 1.2rem;
  }

  .controls {
    flex-direction: column;
    width: 100%;
    gap: 10px;
  }

  .mic-select {
    width: 100%;
  }

  .el-button {
    width: 100%;
  }

  .value {
    font-size: 2.5rem;
  }
  
  .chart-container {
    height: 300px;
  }
}
</style>
