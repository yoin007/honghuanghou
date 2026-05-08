/**
 * ErrorState 组件测试
 * 测试不同错误类型的渲染和重试机制
 */
import { afterEach, describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import ErrorState from '@/components/dashboard/ErrorState.vue'

// Mock useRouter
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    go: vi.fn()
  })
}))

describe('ErrorState', () => {
  // 全局注册 Element Plus
  const globalPlugins = {
    global: {
      plugins: [ElementPlus]
    }
  }

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows error icon and default text for error type', () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error'
      }
    })

    expect(wrapper.find('.error-icon span').text()).toBe('⚠')
    expect(wrapper.find('h2').text()).toBe('数据加载异常')
    expect(wrapper.find('p').text()).toContain('数据加载出现问题')
  })

  it('shows lock icon and unauthorized text for unauthorized type', () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'unauthorized'
      }
    })

    expect(wrapper.find('.error-icon span').text()).toBe('🔒')
    expect(wrapper.find('h2').text()).toBe('未登录或登录已过期')
    expect(wrapper.find('p').text()).toContain('请重新登录')
  })

  it('shows hourglass icon and loading text for loading type', () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'loading'
      }
    })

    expect(wrapper.find('.error-icon span').text()).toBe('⏳')
    expect(wrapper.find('h2').text()).toBe('正在加载...')
    expect(wrapper.find('p').text()).toContain('数据正在加载中')
  })

  it('shows custom title and message when provided', () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error',
        title: '自定义标题',
        message: '自定义描述信息'
      }
    })

    expect(wrapper.find('h2').text()).toBe('自定义标题')
    expect(wrapper.find('p').text()).toBe('自定义描述信息')
  })

  it('shows retry button when showRetry is true', () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error',
        showRetry: true
      }
    })

    const buttons = wrapper.findAll('.el-button')
    expect(buttons.length).toBe(2)
    expect(buttons[0].text()).toBe('重试')
  })

  it('emits retry event when retry button clicked', async () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error',
        showRetry: true
      }
    })

    await wrapper.findAll('.el-button')[0].trigger('click')
    expect(wrapper.emitted('retry')).toBeTruthy()
  })

  it('hides action buttons for loading type', () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'loading'
      }
    })

    const buttons = wrapper.findAll('.el-button')
    expect(buttons.length).toBe(0)
  })

  it('shows workbench button when explicitly enabled', () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error',
        showWorkbench: true
      }
    })

    const buttons = wrapper.findAll('.el-button')
    expect(buttons.length).toBe(2)
    expect(buttons[1].text()).toBe('教师工作台')
  })

  it('hides home button when showHome is false', () => {
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error',
        showHome: false
      }
    })

    const buttons = wrapper.findAll('.el-button')
    expect(buttons.length).toBe(0)
  })

  it('retry button shows disabled state after click', async () => {
    vi.useFakeTimers()
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error',
        showRetry: true
      }
    })

    const button = wrapper.findAll('.el-button')[0]
    expect(button.attributes('disabled')).toBeUndefined()
    expect(button.text()).toBe('重试')

    await button.trigger('click')
    expect(wrapper.emitted('retry')).toBeTruthy()
    expect(button.attributes('disabled')).toBeDefined()
    expect(button.text()).toBe('重试中...')

    // 等待 3 秒后恢复
    vi.advanceTimersByTime(3000)
    await wrapper.vm.$nextTick()
    expect(button.attributes('disabled')).toBeUndefined()
    expect(button.text()).toBe('重试')

    vi.useRealTimers()
  })

  it('does not emit retry again while disabled', async () => {
    vi.useFakeTimers()
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error',
        showRetry: true
      }
    })

    // 第一次点击
    const button = wrapper.findAll('.el-button')[0]
    await button.trigger('click')
    expect(wrapper.emitted('retry').length).toBe(1)

    await button.trigger('click')
    expect(wrapper.emitted('retry').length).toBe(1)
  })

  it('clears retry timer on unmount', async () => {
    vi.useFakeTimers()
    const clearTimeoutSpy = vi.spyOn(globalThis, 'clearTimeout')
    const wrapper = mount(ErrorState, {
      ...globalPlugins,
      props: {
        type: 'error',
        showRetry: true
      }
    })

    await wrapper.findAll('.el-button')[0].trigger('click')
    wrapper.unmount()

    expect(clearTimeoutSpy).toHaveBeenCalled()
    clearTimeoutSpy.mockRestore()
  })
})
