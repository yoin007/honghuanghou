/**
 * DashboardEmptyStrip 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardEmptyStrip from '@/components/dashboard/DashboardEmptyStrip.vue'

describe('DashboardEmptyStrip', () => {
  it('renders default text', () => {
    const wrapper = mount(DashboardEmptyStrip)
    expect(wrapper.text()).toBe('暂无数据')
  })

  it('renders custom text', () => {
    const wrapper = mount(DashboardEmptyStrip, {
      props: { text: '暂无低分学生' }
    })
    expect(wrapper.text()).toBe('暂无低分学生')
  })

  it('applies success variant', () => {
    const wrapper = mount(DashboardEmptyStrip, {
      props: { variant: 'success' }
    })
    expect(wrapper.find('.empty-strip').classes()).toContain('success')
  })

  it('applies default variant when not specified', () => {
    const wrapper = mount(DashboardEmptyStrip)
    expect(wrapper.find('.empty-strip').classes()).not.toContain('success')
  })
})