/**
 * DashboardInsights 组件测试
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import DashboardInsights from '@/components/dashboard/DashboardInsights.vue'

// Mock router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/test', component: { template: '<div />' } }
  ]
})

describe('DashboardInsights', () => {
  it('renders nothing when insights is empty', () => {
    const wrapper = mount(DashboardInsights, {
      props: { insights: [] },
      global: { plugins: [router] }
    })
    expect(wrapper.find('.insights-panel').exists()).toBe(false)
  })

  it('renders insights panel with title and eyebrow', () => {
    const insights = [{ title: 'Test', message: 'Message', type: 'info' }]
    const wrapper = mount(DashboardInsights, {
      props: {
        insights,
        title: '运行态势',
        eyebrow: 'OPERATION INSIGHTS'
      },
      global: { plugins: [router] }
    })
    expect(wrapper.find('.insights-panel').exists()).toBe(true)
    expect(wrapper.find('h3').text()).toBe('运行态势')
    expect(wrapper.find('.panel-header span').text()).toBe('OPERATION INSIGHTS')
  })

  it('renders insight cards with correct type class', () => {
    const insights = [
      { title: 'Warning', message: 'Msg', type: 'warning' },
      { title: 'Info', message: 'Msg', type: 'info' },
      { title: 'Success', message: 'Msg', type: 'success' }
    ]
    const wrapper = mount(DashboardInsights, {
      props: { insights },
      global: { plugins: [router] }
    })
    const cards = wrapper.findAll('.insight-card')
    expect(cards).toHaveLength(3)
    expect(cards[0].classes()).toContain('warning')
    expect(cards[1].classes()).toContain('info')
    expect(cards[2].classes()).toContain('success')
  })

  it('renders action arrow when action_route is set', () => {
    const insights = [{ title: 'Test', message: 'Msg', type: 'info', action_route: '/test' }]
    const wrapper = mount(DashboardInsights, {
      props: { insights },
      global: { plugins: [router] }
    })
    expect(wrapper.find('.action-arrow').exists()).toBe(true)
    expect(wrapper.find('.insight-card').classes()).toContain('clickable')
  })

  it('does not render action arrow when action_route is missing', () => {
    const insights = [{ title: 'Test', message: 'Msg', type: 'info' }]
    const wrapper = mount(DashboardInsights, {
      props: { insights },
      global: { plugins: [router] }
    })
    expect(wrapper.find('.action-arrow').exists()).toBe(false)
    expect(wrapper.find('.insight-card').classes()).not.toContain('clickable')
  })

  it('navigates when clicking clickable insight', async () => {
    const pushSpy = vi.spyOn(router, 'push')
    const insights = [{ title: 'Test', message: 'Msg', type: 'info', action_route: '/test' }]
    const wrapper = mount(DashboardInsights, {
      props: { insights },
      global: { plugins: [router] }
    })
    await wrapper.find('.insight-card').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith('/test')
  })
})