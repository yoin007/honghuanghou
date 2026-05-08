/**
 * DashboardPanelSection 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardPanelSection from '@/components/dashboard/DashboardPanelSection.vue'

describe('DashboardPanelSection', () => {
  it('renders title, eyebrow and slot content', () => {
    const wrapper = mount(DashboardPanelSection, {
      props: { eyebrow: 'ALERT', title: '风险提示' },
      slots: { default: '<div class="content">业务内容</div>' }
    })

    expect(wrapper.text()).toContain('ALERT')
    expect(wrapper.text()).toContain('风险提示')
    expect(wrapper.find('.content').text()).toBe('业务内容')
  })

  it('renders without header when title is empty', () => {
    const wrapper = mount(DashboardPanelSection, {
      slots: { default: '<span>无标题内容</span>' }
    })

    expect(wrapper.find('.panel-header').exists()).toBe(false)
    expect(wrapper.text()).toContain('无标题内容')
  })

  it('applies minHeight and variant class', () => {
    const wrapper = mount(DashboardPanelSection, {
      props: { minHeight: 240, variant: 'danger' }
    })

    expect(wrapper.attributes('style')).toContain('min-height: 240px')
    expect(wrapper.classes()).toContain('danger')
  })
})
