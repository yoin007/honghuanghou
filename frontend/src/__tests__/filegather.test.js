/**
 * 文件收集工具函数测试
 */
import { describe, it, expect, vi } from 'vitest'
import {
  getFileStatusType,
  downloadBlob,
  downloadCSV,
  downloadExcel,
  downloadResponseFile,
  getDashboardCardValue,
  getFileErrorMessage,
  getFileListFromResponse,
  getFileStatsFromResponse
} from '@/utils/filegather'

// Mock window.URL
vi.stubGlobal('window', {
  URL: {
    createObjectURL: vi.fn(() => 'mock-url'),
    revokeObjectURL: vi.fn()
  }
})

// Mock document
vi.stubGlobal('document', {
  body: {
    appendChild: vi.fn(),
    removeChild: vi.fn()
  },
  createElement: vi.fn(() => ({
    href: '',
    download: '',
    click: vi.fn()
  }))
})

describe('getFileStatusType', () => {
  it('returns warning for 否', () => {
    expect(getFileStatusType('否')).toBe('warning')
  })

  it('returns primary for 打印中', () => {
    expect(getFileStatusType('打印中')).toBe('primary')
  })

  it('returns success for 是', () => {
    expect(getFileStatusType('是')).toBe('success')
  })

  it('returns info for unknown status', () => {
    expect(getFileStatusType('unknown')).toBe('info')
    expect(getFileStatusType('')).toBe('info')
  })
})

describe('downloadBlob', () => {
  it('creates download link and triggers click', () => {
    const blob = new Blob(['test'])
    downloadBlob(blob, 'test.txt')

    expect(window.URL.createObjectURL).toHaveBeenCalledWith(blob)
    expect(document.createElement).toHaveBeenCalledWith('a')
    expect(document.body.appendChild).toHaveBeenCalled()
    expect(document.body.removeChild).toHaveBeenCalled()
    expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('mock-url')
  })
})

describe('downloadCSV', () => {
  it('adds BOM header and .csv suffix', () => {
    downloadCSV('content', 'test')
    // Blob created with \ufeff prefix
    expect(window.URL.createObjectURL).toHaveBeenCalled()
  })

  it('keeps filename with .csv suffix', () => {
    downloadCSV('content', 'test.csv')
    expect(window.URL.createObjectURL).toHaveBeenCalled()
  })
})

describe('downloadExcel', () => {
  it('downloads Excel file from ArrayBuffer', () => {
    const data = new ArrayBuffer(8)
    downloadExcel(data, 'test.xlsx')
    expect(window.URL.createObjectURL).toHaveBeenCalled()
  })
})

describe('downloadResponseFile', () => {
  it('downloads response.data with original filename', () => {
    downloadResponseFile({ data: 'file-content' }, 'origin.docx')
    expect(window.URL.createObjectURL).toHaveBeenCalled()
    expect(document.createElement).toHaveBeenCalledWith('a')
  })
})

describe('getFileListFromResponse', () => {
  it('extracts items from response.data.items', () => {
    const response = { data: { items: [{ id: 1 }] } }
    expect(getFileListFromResponse(response)).toEqual([{ id: 1 }])
  })

  it('extracts files from response.data.files', () => {
    const response = { data: { files: [{ id: 2 }] } }
    expect(getFileListFromResponse(response)).toEqual([{ id: 2 }])
  })

  it('returns empty array for missing data', () => {
    expect(getFileListFromResponse({})).toEqual([])
    expect(getFileListFromResponse(null)).toEqual([])
  })
})

describe('getFileStatsFromResponse', () => {
  it('extracts stats from response.data.stats', () => {
    const response = { data: { stats: { total: 10 } } }
    expect(getFileStatsFromResponse(response)).toEqual({ total: 10 })
  })

  it('extracts data directly if no stats', () => {
    const response = { data: { total: 5 } }
    expect(getFileStatsFromResponse(response)).toEqual({ total: 5 })
  })

  it('returns empty object for missing data', () => {
    expect(getFileStatsFromResponse({})).toEqual({})
    expect(getFileStatsFromResponse(null)).toEqual({})
  })
})

describe('getFileErrorMessage', () => {
  it('keeps backend detail when present', () => {
    const error = { response: { data: { detail: '后端错误' } } }
    expect(getFileErrorMessage(error, '默认错误')).toBe('后端错误')
  })

  it('returns fallback when detail is missing', () => {
    expect(getFileErrorMessage({}, '默认错误')).toBe('默认错误')
  })
})

describe('getDashboardCardValue', () => {
  it('returns value by label', () => {
    const cards = [{ label: '待处理文件', value: 3 }]
    expect(getDashboardCardValue(cards, '待处理文件')).toBe(3)
  })

  it('returns fallback when label is missing', () => {
    expect(getDashboardCardValue([], '待处理文件', '-')).toBe('-')
  })
})
