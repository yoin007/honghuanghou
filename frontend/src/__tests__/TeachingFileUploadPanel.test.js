/**
 * TeachingFileUploadPanel 组件测试
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import TeachingFileUploadPanel from '@/components/dashboard/TeachingFileUploadPanel.vue'

const cards = [
  { label: '待处理文件', value: 3 },
  { label: '本月文件', value: 12 },
  { label: '已完成文件', value: 9 },
  { label: '完成率', value: 75 },
  { label: '逾期文件', value: 1 }
]

describe('TeachingFileUploadPanel', () => {
  it('renders metric card values and overdue warning state', () => {
    const wrapper = mount(TeachingFileUploadPanel, {
      props: { cards }
    })

    expect(wrapper.text()).toContain('待处理文件')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('完成率')
    expect(wrapper.text()).toContain('75%')
    expect(wrapper.find('.overdue-count').classes()).toContain('warning')
  })

  it('renders pending files with overdue and normal status', () => {
    const wrapper = mount(TeachingFileUploadPanel, {
      props: {
        cards,
        pendingFiles: [
          { id: 1, original_name: '德育材料.xlsx', username: '王老师', uploaded_at: '2026-05-06', overdue_days: 2 },
          { id: 2, original_name: '教务统计.docx', username: '李老师', uploaded_at: '2026-05-07', overdue_days: 0 }
        ]
      }
    })

    expect(wrapper.text()).toContain('德育材料.xlsx')
    expect(wrapper.text()).toContain('王老师')
    expect(wrapper.text()).toContain('逾期 2 天')
    expect(wrapper.text()).toContain('教务统计.docx')
    expect(wrapper.text()).toContain('待处理')
    expect(wrapper.findAll('.pending-file-item')).toHaveLength(2)
    expect(wrapper.find('.pending-file-item').classes()).toContain('overdue')
  })

  it('renders top users ranking', () => {
    const wrapper = mount(TeachingFileUploadPanel, {
      props: {
        cards,
        topUsers: [
          { username: '王老师', count: 8 },
          { username: '李老师', count: 5 }
        ]
      }
    })

    expect(wrapper.text()).toContain('上传排行')
    expect(wrapper.text()).toContain('王老师')
    expect(wrapper.text()).toContain('8 份')
    expect(wrapper.findAll('.user-item')).toHaveLength(2)
  })

  it('renders empty state when no pending files and no top users', () => {
    const wrapper = mount(TeachingFileUploadPanel)

    expect(wrapper.text()).toContain('本月暂无文件上传记录')
    expect(wrapper.find('.empty-users').exists()).toBe(true)
  })
})
