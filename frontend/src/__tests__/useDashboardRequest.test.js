/**
 * useDashboardRequest composable 单元测试
 */
import { describe, it, expect, vi } from 'vitest'
import { useDashboardRequest } from '@/composables/useDashboardRequest'

describe('useDashboardRequest', () => {
  it('initializes with null errorState and false loading/forbidden', () => {
    const { loading, errorState, forbidden } = useDashboardRequest()
    expect(loading.value).toBe(false)
    expect(errorState.value).toBe(null)
    expect(forbidden.value).toBe(false)
  })

  it('sets loading state during request', async () => {
    const { loading, errorState, execute } = useDashboardRequest()
    const slowRequest = () => new Promise(resolve => {
      setTimeout(() => resolve({ success: true, data: {} }), 50)
    })

    const promise = execute(slowRequest, () => {})
    expect(loading.value).toBe(true)
    expect(errorState.value).toBe('loading')
    await promise
    expect(loading.value).toBe(false)
  })

  it('clears errorState on successful request', async () => {
    const { errorState, execute } = useDashboardRequest()
    const onSuccess = vi.fn()

    await execute(
      () => Promise.resolve({ success: true, data: { cards: [] } }),
      onSuccess
    )

    expect(errorState.value).toBe(null)
    expect(onSuccess).toHaveBeenCalledWith({ cards: [] })
  })

  it('applies error handling when success=false', async () => {
    const { errorState, forbidden, execute } = useDashboardRequest()

    await execute(
      () => Promise.resolve({ success: false, status: 500 }),
      () => {}
    )

    expect(errorState.value).toBe('error')
    expect(forbidden.value).toBe(false)
  })

  it('sets forbidden state on 403 response', async () => {
    const { errorState, forbidden, execute } = useDashboardRequest()

    await execute(
      () => Promise.resolve({ success: false, status: 403 }),
      () => {}
    )

    expect(forbidden.value).toBe(true)
    expect(errorState.value).toBe(null)
  })

  it('handles thrown exceptions', async () => {
    const { errorState, forbidden, execute } = useDashboardRequest()

    await execute(
      () => Promise.reject(new Error('Network error')),
      () => {}
    )

    expect(errorState.value).toBe('error')
    expect(forbidden.value).toBe(false)
  })

  it('always closes loading in finally block', async () => {
    const { loading, execute } = useDashboardRequest()

    // 成功情况
    await execute(() => Promise.resolve({ success: true, data: {} }), () => {})
    expect(loading.value).toBe(false)

    // 失败情况
    await execute(() => Promise.reject(new Error('fail')), () => {})
    expect(loading.value).toBe(false)
  })

  it('maps 401 to unauthorized and keeps forbidden=false', async () => {
    const { errorState, forbidden, execute } = useDashboardRequest()

    await execute(
      () => Promise.resolve({ success: false, status: 401 }),
      () => {}
    )

    expect(forbidden.value).toBe(false)
    expect(errorState.value).toBe('unauthorized')
  })

  it('calls onSuccess with data from response', async () => {
    const { execute } = useDashboardRequest()
    const onSuccess = vi.fn()
    const mockData = { cards: [{ label: 'Test', value: 10 }], charts: {} }

    await execute(
      () => Promise.resolve({ success: true, data: mockData }),
      onSuccess
    )

    expect(onSuccess).toHaveBeenCalledTimes(1)
    expect(onSuccess).toHaveBeenCalledWith(mockData)
  })
})
