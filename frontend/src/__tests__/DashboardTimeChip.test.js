/**
 * DashboardTimeChip 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardTimeChip from '@/components/dashboard/DashboardTimeChip.vue'

describe('DashboardTimeChip', () => {
  it('renders default label and fallback when no value', () => {
    const wrapper = mount(DashboardTimeChip)
    expect(wrapper.find('span').text()).toBe('数据更新')
    expect(wrapper.find('strong').text()).toBe('-')
  })

  it('renders custom label and value', () => {
    const wrapper = mount(DashboardTimeChip, {
      props: { label: '数据更新时间', value: '2024-01-15 10:30' }
    })
    expect(wrapper.find('span').text()).toBe('数据更新时间')
    expect(wrapper.find('strong').text()).toBe('2024-01-15 10:30')
  })

  it('uses fallback when value is empty string', () => {
    const wrapper = mount(DashboardTimeChip, {
      props: { value: '', fallback: '暂无数据' }
    })
    expect(wrapper.find('strong').text()).toBe('暂无数据')
  })

  it('uses fallback when value is null/undefined', () => {
    const wrapper = mount(DashboardTimeChip, {
      props: { value: null, fallback: '未更新' }
    })
    expect(wrapper.find('strong').text()).toBe('未更新')
  })

  it('applies time-chip styling', () => {
    const wrapper = mount(DashboardTimeChip)
    expect(wrapper.find('.time-chip').exists()).toBe(true)
  })
})