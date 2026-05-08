/**
 * charting.js 单元测试
 */
import { describe, it, expect } from 'vitest'
import {
  basePieOption,
  baseHorizontalBarOption,
  baseVerticalBarOption,
  baseLineOption,
  axisLabelColor,
  axisValueColor,
  splitLineColor,
  labelColor,
  pieBorderColor
} from '@/utils/charting'

describe('charting color constants', () => {
  it('exports correct axis label colors', () => {
    expect(axisLabelColor).toBe('#cbd5e1')
    expect(axisValueColor).toBe('#94a3b8')
  })

  it('exports correct line colors', () => {
    expect(splitLineColor).toBe('rgba(148, 163, 184, 0.12)')
    expect(labelColor).toBe('#e2e8f0')
    expect(pieBorderColor).toBe('#07111f')
  })
})

describe('basePieOption', () => {
  it('returns base pie config with transparent background', () => {
    const option = basePieOption()
    expect(option.backgroundColor).toBe('transparent')
    expect(option.tooltip.trigger).toBe('item')
    expect(option.legend.bottom).toBe(0)
  })

  it('uses default radius and center', () => {
    const option = basePieOption()
    const series = option.series[0]
    expect(series.type).toBe('pie')
    expect(series.radius).toEqual(['45%', '70%'])
    expect(series.center).toEqual(['50%', '44%'])
  })

  it('applies custom overrides', () => {
    const option = basePieOption({
      color: ['#38bdf8', '#fbbf24'],
      radius: ['50%', '80%'],
      data: [{ name: 'Test', value: 10 }]
    })
    expect(option.color).toEqual(['#38bdf8', '#fbbf24'])
    expect(option.series[0].radius).toEqual(['50%', '80%'])
    expect(option.series[0].data).toEqual([{ name: 'Test', value: 10 }])
  })

  it('sets correct label and itemStyle', () => {
    const option = basePieOption()
    const series = option.series[0]
    expect(series.label.color).toBe(labelColor)
    expect(series.label.formatter).toBe('{b}\n{c}')
    expect(series.itemStyle.borderColor).toBe(pieBorderColor)
    expect(series.itemStyle.borderWidth).toBe(3)
  })
})

describe('baseHorizontalBarOption', () => {
  it('returns horizontal bar config with axis trigger', () => {
    const option = baseHorizontalBarOption()
    expect(option.backgroundColor).toBe('transparent')
    expect(option.tooltip.trigger).toBe('axis')
    expect(option.xAxis.type).toBe('value')
    expect(option.yAxis.type).toBe('category')
  })

  it('uses default grid and barWidth', () => {
    const option = baseHorizontalBarOption()
    expect(option.grid.left).toBe(72)
    expect(option.series[0].barWidth).toBe(18)
  })

  it('applies custom data overrides', () => {
    const option = baseHorizontalBarOption({
      yAxisData: ['Class A', 'Class B'],
      seriesData: [10, 20],
      color: ['#34d399']
    })
    expect(option.yAxis.data).toEqual(['Class A', 'Class B'])
    expect(option.series[0].data).toEqual([10, 20])
    expect(option.color).toEqual(['#34d399'])
  })

  it('sets correct axis label colors', () => {
    const option = baseHorizontalBarOption()
    expect(option.xAxis.axisLabel.color).toBe(axisValueColor)
    expect(option.yAxis.axisLabel.color).toBe(axisLabelColor)
    expect(option.yAxis.axisLine.show).toBe(false)
  })

  it('applies custom borderRadius', () => {
    const option = baseHorizontalBarOption({ borderRadius: [0, 8, 8, 0] })
    expect(option.series[0].itemStyle.borderRadius).toEqual([0, 8, 8, 0])
  })
})

describe('baseVerticalBarOption', () => {
  it('returns vertical bar config with category x-axis', () => {
    const option = baseVerticalBarOption()
    expect(option.backgroundColor).toBe('transparent')
    expect(option.tooltip.trigger).toBe('axis')
    expect(option.xAxis.type).toBe('category')
    expect(option.yAxis.type).toBe('value')
    expect(option.series[0].type).toBe('bar')
  })

  it('applies custom data, color and tooltip trigger', () => {
    const option = baseVerticalBarOption({
      xAxisData: ['0-59', '60-79'],
      seriesData: [2, 8],
      tooltipTrigger: 'item',
      color: ['#22d3ee']
    })

    expect(option.xAxis.data).toEqual(['0-59', '60-79'])
    expect(option.series[0].data).toEqual([2, 8])
    expect(option.tooltip.trigger).toBe('item')
    expect(option.color).toEqual(['#22d3ee'])
  })

  it('keeps custom itemStyle for business color mapping', () => {
    const itemStyle = {
      borderRadius: [8, 8, 0, 0],
      color: params => params.dataIndex
    }
    const option = baseVerticalBarOption({ itemStyle })

    expect(option.series[0].itemStyle).toBe(itemStyle)
  })
})

describe('baseLineOption', () => {
  it('returns line chart config with axis trigger', () => {
    const option = baseLineOption()
    expect(option.backgroundColor).toBe('transparent')
    expect(option.tooltip.trigger).toBe('axis')
    expect(option.series[0].type).toBe('line')
  })

  it('uses default grid and smooth settings', () => {
    const option = baseLineOption()
    expect(option.grid.left).toBe(38)
    expect(option.series[0].smooth).toBe(true)
    expect(option.series[0].symbolSize).toBe(7)
    expect(option.series[0].lineStyle.width).toBe(3)
  })

  it('applies custom axis and series data', () => {
    const option = baseLineOption({
      xAxisData: ['Mon', 'Tue', 'Wed'],
      seriesData: [5, 10, 8],
      color: ['#a78bfa']
    })
    expect(option.xAxis.data).toEqual(['Mon', 'Tue', 'Wed'])
    expect(option.series[0].data).toEqual([5, 10, 8])
    expect(option.color).toEqual(['#a78bfa'])
  })

  it('sets correct axis styling', () => {
    const option = baseLineOption()
    expect(option.xAxis.axisLabel.color).toBe(axisLabelColor)
    expect(option.yAxis.axisLabel.color).toBe(axisValueColor)
    expect(option.yAxis.splitLine.lineStyle.color).toBe(splitLineColor)
  })
})
