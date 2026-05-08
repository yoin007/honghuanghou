/**
 * DashboardLeaveList 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardLeaveList from '@/components/dashboard/DashboardLeaveList.vue'

describe('DashboardLeaveList', () => {
  it('renders success empty state when no students', () => {
    const wrapper = mount(DashboardLeaveList, {
      props: { students: [], emptyText: '当前无请假学生' }
    })
    expect(wrapper.text()).toContain('当前无请假学生')
    expect(wrapper.find('.empty-strip').classes()).toContain('success')
  })

  it('renders class mode leave meta without class name', () => {
    const wrapper = mount(DashboardLeaveList, {
      props: {
        mode: 'class',
        students: [{ id: 1, name: '张三', style: '事假', days: 2, status: '已出校', create_at: '2026-05-07' }]
      }
    })
    expect(wrapper.text()).toContain('张三')
    expect(wrapper.text()).toContain('事假 · 2天 · 已出校')
    expect(wrapper.find('.leave-row').classes()).toContain('warning')
  })

  it('renders moral mode leave meta with class name', () => {
    const wrapper = mount(DashboardLeaveList, {
      props: {
        mode: 'moral',
        students: [{ id: 1, name: '李四', class_name: '高一1班', style: '病假', days: 1, status: '已请假', create_at: '2026-05-07' }]
      }
    })
    expect(wrapper.text()).toContain('高一1班 · 病假 · 1天')
    expect(wrapper.find('.leave-row').classes()).toContain('info')
  })
})
