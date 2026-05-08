/**
 * DashboardHero 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardHero from '@/components/dashboard/DashboardHero.vue'

describe('DashboardHero', () => {
  it('renders required title', () => {
    const wrapper = mount(DashboardHero, { props: { title: '教务驾驶舱' } })
    expect(wrapper.find('h1').text()).toBe('教务驾驶舱')
  })

  it('renders kicker when provided', () => {
    const wrapper = mount(DashboardHero, {
      props: { title: 'Test', kicker: 'Teaching Operations' }
    })
    expect(wrapper.find('.kicker').text()).toBe('Teaching Operations')
  })

  it('does not render kicker when empty', () => {
    const wrapper = mount(DashboardHero, { props: { title: 'Test' } })
    expect(wrapper.find('.kicker').exists()).toBe(false)
  })

  it('renders description when provided', () => {
    const wrapper = mount(DashboardHero, {
      props: { title: 'Test', description: '这是一个测试描述' }
    })
    expect(wrapper.find('p').text()).toBe('这是一个测试描述')
  })

  it('renders slot content in right side', () => {
    const wrapper = mount(DashboardHero, {
      props: { title: 'Test' },
      slots: { default: '<div class="custom-slot">Custom Content</div>' }
    })
    expect(wrapper.find('.custom-slot').exists()).toBe(true)
    expect(wrapper.find('.custom-slot').text()).toBe('Custom Content')
  })

  it('applies hero-band styling', () => {
    const wrapper = mount(DashboardHero, { props: { title: 'Test' } })
    expect(wrapper.find('.hero-band').exists()).toBe(true)
  })
})