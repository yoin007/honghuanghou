/**
 * 时间工具函数 - 东八区时间处理
 */

/**
 * 获取东八区当前时间字符串 (YYYY-MM-DD HH:mm)
 * @returns {string}
 */
export const getGMT8TimeString = () => {
  const now = new Date()
  // 东八区偏移 +8小时
  const gmt8 = new Date(now.getTime() + 8 * 60 * 60 * 1000)
  return gmt8.toISOString().slice(0, 16).replace('T', ' ')
}

/**
 * 获取东八区当前日期字符串 (YYYY-MM-DD)
 * @returns {string}
 */
export const getGMT8DateString = () => {
  const now = new Date()
  const gmt8 = new Date(now.getTime() + 8 * 60 * 60 * 1000)
  return gmt8.toISOString().slice(0, 10)
}

/**
 * 获取东八区当前完整时间 ISO格式
 * @returns {string}
 */
export const getGMT8ISOString = () => {
  const now = new Date()
  const gmt8 = new Date(now.getTime() + 8 * 60 * 60 * 1000)
  return gmt8.toISOString()
}

/**
 * 获取东八区当前年份
 * @returns {number}
 */
export const getGMT8Year = () => {
  const now = new Date()
  const gmt8 = new Date(now.getTime() + 8 * 60 * 60 * 1000)
  return gmt8.getFullYear()
}

/**
 * 格式化日期时间为本地显示格式 (zh-CN)
 *
 * 用于 AdminFiles、AdminFilesDone、StudentProfile、TeacherManage 等页面的时间显示
 *
 * @param {string|Date} datetime - ISO 时间字符串或 Date 对象
 * @returns {string} zh-CN 格式的日期时间，如 "2024/1/15 14:30:00"
 */
export const formatDateTimeLocal = (datetime) => {
  if (!datetime) return '-'
  const date = new Date(datetime)
  if (isNaN(date.getTime())) return '-'
  return date.toLocaleString('zh-CN')
}

/**
 * 格式化日期时间为紧凑格式 (YYYY-MM-DD HH:mm)
 *
 * 用于 AdminFiles、AdminFilesDone 等页面的时间显示（UTC 转 GMT+8）
 *
 * @param {string|Date} datetime - ISO 时间字符串或 Date 对象
 * @param {boolean} addGMT8 - 是否添加东八区偏移（默认 true）
 * @returns {string} YYYY-MM-DD HH:mm 格式
 */
export const formatDateTimeCompact = (datetime, addGMT8 = true) => {
  if (!datetime) return '-'
  const date = new Date(datetime)
  if (isNaN(date.getTime())) return '-'

  // 保持历史页面行为：文件管理时间统一在原值基础上加 8 小时显示。
  if (addGMT8) {
    date.setHours(date.getHours() + 8)
  }

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')

  return `${year}-${month}-${day} ${hour}:${minute}`
}

/**
 * 格式化日期为月日格式 (MM-DD)
 *
 * 用于 Homework 等页面的截止日期显示
 *
 * @param {string|Date} date - ISO 日期字符串或 Date 对象
 * @param {boolean} includeTime - 是否包含时间（默认 false）
 * @returns {string} MM-DD 格式，或 月/日 时:分 格式
 */
export const formatDateMonthDay = (date, includeTime = false) => {
  if (!date) return ''
  const d = new Date(typeof date === 'string' ? date.replace(' ', 'T') : date)
  if (isNaN(d.getTime())) return ''

  const month = d.getMonth() + 1
  const day = d.getDate()

  if (includeTime) {
    const hours = String(d.getHours()).padStart(2, '0')
    const minutes = String(d.getMinutes()).padStart(2, '0')
    return `${month}/${day} ${hours}:${minutes}`
  }

  return `${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

/**
 * 格式化日期为中文月日格式 (X月X日)
 *
 * 用于 Birthday 等页面的生日显示
 *
 * @param {string|Date} date - ISO 日期字符串或 Date 对象
 * @returns {string} X月X日 格式，如 "1月15日"
 */
export const formatDateChinese = (date) => {
  if (!date) return '-'
  const d = new Date(date)
  if (isNaN(d.getTime())) return '-'

  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/**
 * 格式化 ISO 时间字符串为显示格式（直接截断）
 *
 * 用于 MyFiles 等页面的简单显示（不转换时区）
 *
 * @param {string} datetime - ISO 时间字符串
 * @returns {string} YYYY-MM-DD HH:mm 格式
 */
export const formatDateTimeSimple = (datetime) => {
  if (!datetime) return ''
  if (typeof datetime !== 'string') return '-'
  return datetime.replace('T', ' ').slice(0, 16)
}

/**
 * 生成最近 N 个月份值。
 *
 * 用于文件列表月份筛选，格式保持为 YYYYMM。
 *
 * @param {number} count - 月份数量
 * @returns {string[]} YYYYMM 列表
 */
export const generateRecentMonths = (count = 12) => {
  const now = new Date()
  const result = []
  for (let i = 0; i < count; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const month = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}`
    result.push(month)
  }
  return result
}

/**
 * 格式化 YYYYMM 为 YYYY-MM。
 *
 * @param {string} month - YYYYMM
 * @returns {string}
 */
export const formatYearMonth = (month) => {
  if (!month || month.length !== 6) return month
  return `${month.slice(0, 4)}-${month.slice(4)}`
}

/**
 * 格式化日期为 M/D。
 *
 * 用于驾驶舱紧凑列表日期显示，保持原有不补零格式。
 *
 * @param {string|Date} date - 日期
 * @returns {string}
 */
export const formatDateSlashMonthDay = (date) => {
  if (!date) return ''
  const d = new Date(date)
  if (isNaN(d.getTime())) {
    return typeof date === 'string' ? (date.slice(5, 10) || '') : ''
  }
  return `${d.getMonth() + 1}/${d.getDate()}`
}
