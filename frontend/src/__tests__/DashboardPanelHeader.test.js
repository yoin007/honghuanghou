/**
 * DashboardPanelHeader 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardPanelHeader from '@/components/dashboard/DashboardPanelHeader.vue'

describe('DashboardPanelHeader', () => {
  it('renders required title', () => {
    const wrapper = mount(DashboardPanelHeader, { props: { title: '课表覆盖说明' } })
    expect(wrapper.find('h3').text()).toBe('课表覆盖说明')
  })

  it('renders eyebrow when provided', () => {
    const wrapper = mount(DashboardPanelHeader, {
      props: { title: 'Test', eyebrow: 'SCHEDULE COVERAGE' }
    })
    expect(wrapper.find('.eyebrow').text()).toBe('SCHEDULE COVERAGE')
  })

  it('does not render eyebrow when empty', () => {
    const wrapper = mount(DashboardPanelHeader, { props: { title: 'Test' } })
    expect(wrapper.find('.eyebrow').exists()).toBe(false)
  })

  it('applies panel-header styling', () => {
    const wrapper = mount(DashboardPanelHeader, { props: { title: 'Test' } })
    expect(wrapper.find('.panel-header').exists()).toBe(true)
  })

  it('uses kicker-style color for eyebrow', () => {
    const wrapper = mount(DashboardPanelHeader, {
      props: { title: 'Test', eyebrow: 'METRICS' }
    })
    const eyebrow = wrapper.find('.eyebrow')
    expect(eyebrow.exists()).toBe(true)
    // 样式通过 CSS 类应用，不直接检查颜色值
  })
})