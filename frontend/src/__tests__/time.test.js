/**
 * 时间工具函数测试
 */
import { describe, it, expect } from 'vitest'
import {
  getGMT8TimeString,
  getGMT8DateString,
  getGMT8ISOString,
  getGMT8Year,
  formatDateTimeLocal,
  formatDateTimeCompact,
  formatDateMonthDay,
  formatDateChinese,
  formatDateTimeSimple,
  generateRecentMonths,
  formatYearMonth,
  formatDateSlashMonthDay
} from '@/utils/time'

describe('GMT+8 时间获取', () => {
  it('getGMT8TimeString returns YYYY-MM-DD HH:mm format', () => {
    const result = getGMT8TimeString()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
  })

  it('getGMT8DateString returns YYYY-MM-DD format', () => {
    const result = getGMT8DateString()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('getGMT8ISOString returns ISO format', () => {
    const result = getGMT8ISOString()
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
  })

  it('getGMT8Year returns current year', () => {
    const result = getGMT8Year()
    expect(result).toBeGreaterThanOrEqual(2024)
    expect(result).toBeLessThanOrEqual(2030)
  })
})

describe('formatDateTimeLocal', () => {
  it('returns zh-CN format for valid datetime', () => {
    const result = formatDateTimeLocal('2024-01-15T14:30:00')
    expect(result).toMatch(/2024/)
    expect(result).toMatch(/1/)
    expect(result).toMatch(/15/)
  })

  it('returns dash for empty input', () => {
    expect(formatDateTimeLocal(null)).toBe('-')
    expect(formatDateTimeLocal('')).toBe('-')
    expect(formatDateTimeLocal(undefined)).toBe('-')
  })

  it('returns dash for invalid date', () => {
    expect(formatDateTimeLocal('invalid')).toBe('-')
  })
})

describe('formatDateTimeCompact', () => {
  it('returns YYYY-MM-DD HH:mm format', () => {
    const result = formatDateTimeCompact('2024-01-15T14:30:00', false)
    expect(result).toBe('2024-01-15 14:30')
  })

  it('handles UTC string with offset', () => {
    const result = formatDateTimeCompact('2024-01-15T14:30:00', true)
    expect(result).toBe('2024-01-15 22:30')
  })

  it('keeps legacy GMT+8 offset for space-separated datetime', () => {
    const result = formatDateTimeCompact('2024-01-15 14:30:00', true)
    expect(result).toBe('2024-01-15 22:30')
  })

  it('returns dash for empty input', () => {
    expect(formatDateTimeCompact(null)).toBe('-')
    expect(formatDateTimeCompact('')).toBe('-')
  })
})

describe('formatDateMonthDay', () => {
  it('returns MM-DD format without time', () => {
    const result = formatDateMonthDay('2024-01-15')
    expect(result).toBe('01-15')
  })

  it('returns month/day HH:mm format with time', () => {
    const result = formatDateMonthDay('2024-01-15T14:30:00', true)
    expect(result).toMatch(/1\/15/)
    expect(result).toMatch(/14:30/)
  })

  it('handles space-separated datetime', () => {
    const result = formatDateMonthDay('2024-01-15 14:30', true)
    expect(result).toMatch(/1\/15/)
    expect(result).toMatch(/14:30/)
  })

  it('returns empty string for empty input', () => {
    expect(formatDateMonthDay(null)).toBe('')
    expect(formatDateMonthDay('')).toBe('')
  })
})

describe('formatDateChinese', () => {
  it('returns X月X日 format', () => {
    const result = formatDateChinese('2024-01-15')
    expect(result).toBe('1月15日')
  })

  it('returns dash for empty input', () => {
    expect(formatDateChinese(null)).toBe('-')
    expect(formatDateChinese('')).toBe('-')
  })

  it('returns dash for invalid date', () => {
    expect(formatDateChinese('invalid')).toBe('-')
  })
})

describe('formatDateTimeSimple', () => {
  it('returns YYYY-MM-DD HH:mm from ISO string', () => {
    const result = formatDateTimeSimple('2024-01-15T14:30:00')
    expect(result).toBe('2024-01-15 14:30')
  })

  it('returns empty string for empty input', () => {
    expect(formatDateTimeSimple(null)).toBe('')
    expect(formatDateTimeSimple('')).toBe('')
  })

  it('returns dash for non-string input', () => {
    expect(formatDateTimeSimple(new Date())).toBe('-')
  })
})

describe('month helpers', () => {
  it('generates recent months in YYYYMM format', () => {
    const result = generateRecentMonths(3)
    expect(result).toHaveLength(3)
    expect(result[0]).toMatch(/^\d{6}$/)
  })

  it('formats YYYYMM as YYYY-MM', () => {
    expect(formatYearMonth('202401')).toBe('2024-01')
    expect(formatYearMonth('bad')).toBe('bad')
  })
})

describe('formatDateSlashMonthDay', () => {
  it('returns M/D format', () => {
    expect(formatDateSlashMonthDay('2024-01-15')).toBe('1/15')
  })

  it('keeps compact fallback for invalid strings', () => {
    expect(formatDateSlashMonthDay('2024-xx-15')).toBe('xx-15')
  })

  it('returns empty string for empty input', () => {
    expect(formatDateSlashMonthDay('')).toBe('')
  })
})
