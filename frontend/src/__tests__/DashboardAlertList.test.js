/**
 * DashboardAlertList 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardAlertList from '@/components/dashboard/DashboardAlertList.vue'

describe('DashboardAlertList', () => {
  it('renders empty state when items are empty', () => {
    const wrapper = mount(DashboardAlertList, {
      props: { items: [], emptyText: '暂无预警' }
    })

    expect(wrapper.text()).toContain('暂无预警')
    expect(wrapper.find('.empty-strip').exists()).toBe(true)
  })

  it('renders multiple items with slot content', () => {
    const wrapper = mount(DashboardAlertList, {
      props: {
        items: [{ name: '张老师' }, { name: '李老师' }],
        variant: 'warning'
      },
      slots: {
        default: '<template #default="{ item }"><strong>{{ item.name }}</strong></template>'
      }
    })

    expect(wrapper.findAll('.dashboard-alert-row')).toHaveLength(2)
    expect(wrapper.text()).toContain('张老师')
    expect(wrapper.text()).toContain('李老师')
    expect(wrapper.find('.dashboard-alert-row').classes()).toContain('warning')
  })

  it('uses itemKey field for stable row keys', () => {
    const wrapper = mount(DashboardAlertList, {
      props: {
        items: [{ id: 'a', name: 'A' }],
        itemKey: 'id'
      },
      slots: {
        default: '<template #default="{ item }">{{ item.name }}</template>'
      }
    })

    expect(wrapper.text()).toContain('A')
  })
})
