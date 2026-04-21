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