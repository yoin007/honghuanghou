/**
 * DashboardTopNSelect 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DashboardTopNSelect from '@/components/dashboard/DashboardTopNSelect.vue'

const mountSelect = (options = {}) => mount(DashboardTopNSelect, {
  ...options,
  global: {
    stubs: {
      ElSelect: {
        name: 'ElSelect',
        props: ['modelValue'],
        emits: ['change'],
        template: '<div class="el-select-stub"><slot /></div>'
      },
      ElOption: {
        name: 'ElOption',
        props: ['label', 'value'],
        template: '<span class="el-option-stub">{{ label }}</span>'
      }
    }
  }
})

describe('DashboardTopNSelect', () => {
  it('renders default label and options', () => {
    const wrapper = mountSelect()
    expect(wrapper.text()).toContain('排行规模')
    expect(wrapper.text()).toContain('Top 5')
    expect(wrapper.text()).toContain('Top 10')
    expect(wrapper.text()).toContain('Top 15')
  })

  it('emits update and change when value changes', async () => {
    const wrapper = mountSelect({ props: { modelValue: 5 } })
    await wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('change', 10)

    expect(wrapper.emitted('update:modelValue')[0]).toEqual([10])
    expect(wrapper.emitted('change')[0]).toEqual([10])
  })

  it('renders custom label and options', () => {
    const wrapper = mountSelect({
      props: { label: '数量', options: [3, 6] }
    })

    expect(wrapper.text()).toContain('数量')
    expect(wrapper.text()).toContain('Top 3')
    expect(wrapper.text()).toContain('Top 6')
  })
})
