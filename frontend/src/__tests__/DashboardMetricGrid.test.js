/**
 * DashboardMetricGrid 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardMetricGrid from '@/components/dashboard/DashboardMetricGrid.vue'

describe('DashboardMetricGrid', () => {
  it('renders empty grid when no cards', () => {
    const wrapper = mount(DashboardMetricGrid)
    expect(wrapper.find('.metric-grid').exists()).toBe(true)
    expect(wrapper.findAll('.metric-card')).toHaveLength(0)
  })

  it('renders cards with label/value/unit', () => {
    const cards = [
      { label: '教师数', value: 42, unit: '人' },
      { label: '班级数', value: 15, unit: '个' }
    ]
    const wrapper = mount(DashboardMetricGrid, { props: { cards } })

    const cardElements = wrapper.findAll('.metric-card')
    expect(cardElements).toHaveLength(2)
    expect(cardElements[0].find('span').text()).toBe('教师数')
    expect(cardElements[0].find('strong').text()).toContain('42')
    expect(cardElements[0].find('small').text()).toBe('人')
  })

  it('applies accent colors in rotation', () => {
    const cards = [{ label: 'A', value: 1 }, { label: 'B', value: 2 }, { label: 'C', value: 3 }]
    const accents = ['#38bdf8', '#fbbf24', '#34d399']
    const wrapper = mount(DashboardMetricGrid, { props: { cards, accents } })

    const cardElements = wrapper.findAll('.metric-card')
    expect(cardElements[0].attributes('style')).toContain('--accent: #38bdf8')
    expect(cardElements[1].attributes('style')).toContain('--accent: #fbbf24')
    expect(cardElements[2].attributes('style')).toContain('--accent: #34d399')
  })

  it('emits click event with route and card data', async () => {
    const cards = [{ label: 'Test', value: 10, route: '/test' }]
    const wrapper = mount(DashboardMetricGrid, { props: { cards } })

    await wrapper.find('.metric-card').trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
    expect(wrapper.emitted('click')[0][0]).toBe('/test')
    expect(wrapper.emitted('click')[0][1]).toEqual(cards[0])
  })

  it('uses default accents when not provided', () => {
    const wrapper = mount(DashboardMetricGrid)
    expect(wrapper.props('accents')).toEqual(['#38bdf8', '#fbbf24', '#34d399', '#f472b6', '#f87171'])
  })

  it('renders sub text only when provided', () => {
    const cards = [
      { label: '总记录数', value: 9930, unit: '条', sub: '业务 5300 · 日志 4295 · 其他 335' },
      { label: '教师账号', value: 65, unit: '人' }
    ]
    const wrapper = mount(DashboardMetricGrid, { props: { cards } })

    const cardElements = wrapper.findAll('.metric-card')
    expect(cardElements[0].find('.metric-sub').exists()).toBe(true)
    expect(cardElements[0].find('.metric-sub').text()).toBe('业务 5300 · 日志 4295 · 其他 335')
    // 无 sub 的卡片不渲染该行，且第一个 small 仍是单位
    expect(cardElements[1].find('.metric-sub').exists()).toBe(false)
    expect(cardElements[1].find('small').text()).toBe('人')
  })
})
