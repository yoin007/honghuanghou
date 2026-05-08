/**
 * DashboardLoadingState 组件测试
 * 测试骨架屏渲染和 props
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardLoadingState from '@/components/dashboard/DashboardLoadingState.vue'

describe('DashboardLoadingState', () => {
  it('renders default metric and chart count', () => {
    const wrapper = mount(DashboardLoadingState)

    expect(wrapper.findAll('.skeleton-card').length).toBe(4)
    expect(wrapper.findAll('.skeleton-chart').length).toBe(2)
  })

  it('renders custom metric count', () => {
    const wrapper = mount(DashboardLoadingState, {
      props: {
        metricCount: 8,
        chartCount: 5
      }
    })

    expect(wrapper.findAll('.skeleton-card').length).toBe(8)
    expect(wrapper.findAll('.skeleton-chart').length).toBe(5)
  })

  it('renders skeleton hero section', () => {
    const wrapper = mount(DashboardLoadingState)

    expect(wrapper.find('.skeleton-hero').exists()).toBe(true)
    expect(wrapper.find('.skeleton-kicker').exists()).toBe(true)
    expect(wrapper.find('.skeleton-title').exists()).toBe(true)
    expect(wrapper.find('.skeleton-desc').exists()).toBe(true)
  })

  it('renders shimmer animation elements', () => {
    const wrapper = mount(DashboardLoadingState)

    const shimmerElements = wrapper.findAll('.skeleton-text')
    expect(shimmerElements.length).toBeGreaterThan(0)
  })

  it('renders skeleton orb in each card', () => {
    const wrapper = mount(DashboardLoadingState, {
      props: {
        metricCount: 3
      }
    })

    expect(wrapper.findAll('.skeleton-orb').length).toBe(3)
  })

  it('renders skeleton canvas in each chart', () => {
    const wrapper = mount(DashboardLoadingState, {
      props: {
        chartCount: 3
      }
    })

    expect(wrapper.findAll('.skeleton-canvas').length).toBe(3)
  })
})