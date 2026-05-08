/**
 * DashboardChart 组件测试
 * 测试 empty prop 和 emptyText prop 的渲染行为
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardChart from '@/components/dashboard/DashboardChart.vue'

vi.mock('@/utils/charting', () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn()
  }))
}))

describe('DashboardChart', () => {
  it('renders chart when hasData is true', () => {
    const wrapper = mount(DashboardChart, {
      props: {
        title: '测试图表',
        eyebrow: 'TEST',
        option: {},
        empty: false
      }
    })

    expect(wrapper.find('.chart-canvas').exists()).toBe(true)
    expect(wrapper.find('.empty-state').exists()).toBe(false)
  })

  it('renders empty state when empty is true', () => {
    const wrapper = mount(DashboardChart, {
      props: {
        title: '测试图表',
        eyebrow: 'TEST',
        option: {},
        empty: true
      }
    })

    expect(wrapper.find('.chart-canvas').exists()).toBe(false)
    expect(wrapper.find('.empty-state').exists()).toBe(true)
  })

  it('shows default empty text when emptyText not provided', () => {
    const wrapper = mount(DashboardChart, {
      props: {
        title: '测试图表',
        eyebrow: 'TEST',
        option: {},
        empty: true
      }
    })

    expect(wrapper.find('.empty-state span').text()).toBe('暂无可视化数据')
  })

  it('shows custom empty text when emptyText provided', () => {
    const wrapper = mount(DashboardChart, {
      props: {
        title: '测试图表',
        eyebrow: 'TEST',
        option: {},
        empty: true,
        emptyText: '当前无德育分数分布数据'
      }
    })

    expect(wrapper.find('.empty-state span').text()).toBe('当前无德育分数分布数据')
  })

  it('renders title and eyebrow correctly', () => {
    const wrapper = mount(DashboardChart, {
      props: {
        title: '德育分数段分布',
        eyebrow: 'SCORE BAND',
        option: {},
        empty: false
      }
    })

    expect(wrapper.find('h3').text()).toBe('德育分数段分布')
    expect(wrapper.find('.eyebrow').text()).toBe('SCORE BAND')
  })
})
