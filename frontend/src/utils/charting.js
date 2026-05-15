import { use, init } from 'echarts/core'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  BarChart,
  LineChart,
  PieChart,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer
])

// Dashboard 通用颜色常量
export const axisLabelColor = '#cbd5e1'
export const axisValueColor = '#94a3b8'
export const splitLineColor = 'rgba(148, 163, 184, 0.12)'
export const axisLineColor = 'rgba(148, 163, 184, 0.35)'
export const labelColor = '#e2e8f0'
export const pieBorderColor = '#07111f'

const toFiniteNumbers = (values) => {
  const source = Array.isArray(values) ? values.flat(Infinity) : [values]
  return source
    .map(value => Number(value))
    .filter(value => Number.isFinite(value))
}

const roundAxisNumber = (value) => {
  if (!Number.isFinite(value)) return value
  if (Math.abs(value) >= 10) return Math.round(value * 10) / 10
  return Math.round(value * 100) / 100
}

const niceStep = (rawStep, integer = false) => {
  if (!Number.isFinite(rawStep) || rawStep <= 0) return integer ? 1 : 1
  const exponent = Math.floor(Math.log10(rawStep))
  const magnitude = 10 ** exponent
  const residual = rawStep / magnitude
  const niceResidual = residual <= 1
    ? 1
    : residual <= 2
      ? 2
      : residual <= 2.5
        ? 2.5
        : residual <= 5
          ? 5
          : 10
  const step = niceResidual * magnitude
  return integer ? Math.max(1, Math.ceil(step)) : step
}

/**
 * 根据当前数据生成更细的数值轴，避免分数差距被 0-100 轴压扁。
 */
export function buildAdaptiveValueAxis(values, options = {}) {
  const {
    name = '',
    targetTicks = 5,
    minRange = 4,
    paddingRatio = 0.18,
    hardMin = null,
    hardMax = null,
    includeZero = false,
    integer = false,
    axisLabel = {},
    splitLine = {},
    extra = {}
  } = options

  const nums = toFiniteNumbers(values)
  const baseAxis = {
    type: 'value',
    name,
    axisLabel: { color: axisValueColor, ...axisLabel },
    splitLine: { lineStyle: { color: splitLineColor }, ...splitLine },
    ...extra
  }

  if (!nums.length) return baseAxis

  let min = Math.min(...nums)
  let max = Math.max(...nums)
  if (includeZero) min = Math.min(min, 0)

  const originalRange = Math.max(max - min, 0)
  const range = Math.max(originalRange, minRange)
  const padding = range * paddingRatio
  let axisMin = min - padding
  let axisMax = max + padding

  if (originalRange === 0) {
    axisMin = min - range / 2
    axisMax = max + range / 2
  }

  const step = niceStep((axisMax - axisMin) / targetTicks, integer)
  axisMin = Math.floor(axisMin / step) * step
  axisMax = Math.ceil(axisMax / step) * step

  if (integer) {
    axisMin = Math.floor(axisMin)
    axisMax = Math.ceil(axisMax)
  }

  if (hardMin !== null) axisMin = Math.max(hardMin, axisMin)
  if (hardMax !== null) axisMax = Math.min(hardMax, axisMax)

  if (axisMin >= axisMax) {
    axisMin = hardMin !== null ? hardMin : axisMin - step
    axisMax = hardMax !== null ? hardMax : axisMax + step
  }

  return {
    ...baseAxis,
    min: roundAxisNumber(axisMin),
    max: roundAxisNumber(axisMax),
    interval: roundAxisNumber(step)
  }
}

/**
 * 生成饼图基础配置（不含业务 data）
 * @param {Object} overrides - 覆盖项（如 color, radius）
 * @returns {Object} ECharts 饼图配置对象
 */
export function basePieOption(overrides = {}) {
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: axisLabelColor } },
    series: [{
      type: 'pie',
      radius: overrides.radius || ['45%', '70%'],
      center: overrides.center || ['50%', '44%'],
      label: { color: labelColor, formatter: '{b}\n{c}' },
      itemStyle: { borderColor: pieBorderColor, borderWidth: 3 },
      data: overrides.data || []
    }],
    color: overrides.color || []
  }
}

/**
 * 生成水平柱状图基础配置（y 轴分类，x 轴数值）
 * @param {Object} overrides - 覆盖项（如 grid, barWidth, borderRadius）
 * @returns {Object} ECharts 水平柱状图配置对象
 */
export function baseHorizontalBarOption(overrides = {}) {
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: overrides.grid || { left: 72, right: 24, top: 24, bottom: 28 },
    xAxis: {
      type: 'value',
      axisLabel: { color: axisValueColor },
      splitLine: { lineStyle: { color: splitLineColor } },
      ...(overrides.xAxis || {})
    },
    yAxis: {
      type: 'category',
      data: overrides.yAxisData || [],
      axisLabel: { color: axisLabelColor },
      axisLine: { show: false }
    },
    series: [{
      type: 'bar',
      data: overrides.seriesData || [],
      barWidth: overrides.barWidth || 18,
      label: { show: true, position: 'right', color: labelColor },
      itemStyle: { borderRadius: overrides.borderRadius || [0, 9, 9, 0] }
    }],
    color: overrides.color || []
  }
}

/**
 * 生成垂直柱状图基础配置（x 轴分类，y 轴数值）
 * @param {Object} overrides - 覆盖项（如 grid, barWidth, itemStyle）
 * @returns {Object} ECharts 垂直柱状图配置对象
 */
export function baseVerticalBarOption(overrides = {}) {
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: overrides.tooltipTrigger || 'axis' },
    grid: overrides.grid || { left: 36, right: 20, top: 28, bottom: 28 },
    xAxis: {
      type: 'category',
      data: overrides.xAxisData || [],
      axisLabel: { color: axisLabelColor },
      axisLine: { lineStyle: { color: axisLineColor } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: axisValueColor },
      splitLine: { lineStyle: { color: splitLineColor } },
      ...(overrides.yAxis || {})
    },
    series: [{
      type: 'bar',
      data: overrides.seriesData || [],
      barWidth: overrides.barWidth || 24,
      itemStyle: overrides.itemStyle || { borderRadius: [8, 8, 0, 0] }
    }],
    color: overrides.color || []
  }
}

/**
 * 生成折线图基础配置
 * @param {Object} overrides - 覆盖项（如 xAxisData, seriesData, color）
 * @returns {Object} ECharts 折线图配置对象
 */
export function baseLineOption(overrides = {}) {
  return {
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis' },
    grid: overrides.grid || { left: 38, right: 20, top: 28, bottom: 32 },
    xAxis: {
      type: 'category',
      data: overrides.xAxisData || [],
      axisLabel: { color: axisLabelColor },
      axisLine: { lineStyle: { color: axisLineColor } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: axisValueColor },
      splitLine: { lineStyle: { color: splitLineColor } },
      ...(overrides.yAxis || {})
    },
    series: [{
      type: 'line',
      smooth: true,
      symbolSize: 7,
      areaStyle: overrides.areaStyle || {},
      lineStyle: { width: 3 },
      data: overrides.seriesData || []
    }],
    color: overrides.color || ['#67e8f9']
  }
}

export { init }
