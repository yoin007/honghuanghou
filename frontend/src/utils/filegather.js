import ExcelJS from 'exceljs'

/**
 * 文件收集工具函数
 *
 * 统一：
 * - 文件打印状态映射（否/打印中/是 → tag type）
 * - Blob 文件下载逻辑
 * - 文件列表空值保护
 */

/**
 * 文件打印状态到 Element Plus Tag type 映射
 *
 * 用于 AdminFiles、MyFiles、AdminFilesDone 等页面的状态显示
 *
 * @param {string} status - 状态值：否/打印中/是
 * @returns {string} tag type：warning/primary/success/info
 */
export const getFileStatusType = (status) => {
  switch (status) {
    case '否': return 'warning'
    case '打印中': return 'primary'
    case '是': return 'success'
    default: return 'info'
  }
}

/**
 * 下载 Blob 文件
 *
 * 用于 AdminFiles、AdminFilesDone 等页面的文件下载
 *
 * @param {Blob} blob - 文件 Blob 对象
 * @param {string} filename - 下载文件名
 */
export const downloadBlob = (blob, filename) => {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * 下载 CSV 文件（添加 BOM 头以支持中文）
 *
 * 用于德育模块、学生管理等页面的 CSV 导出
 *
 * @param {string} csvContent - CSV 内容字符串
 * @param {string} filename - 下载文件名（不含 .csv 后缀）
 */
export const downloadCSV = (csvContent, filename) => {
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
  downloadBlob(blob, filename.endsWith('.csv') ? filename : `${filename}.csv`)
}

/**
 * 下载 Excel 文件（从 API 响应）
 *
 * 用于监考安排、模板下载等页面的 Excel 导出
 *
 * @param {ArrayBuffer|Blob} data - API 响应数据
 * @param {string} filename - 下载文件名（含 .xlsx 后缀）
 */
export const downloadExcel = (data, filename) => {
  const blob = new Blob([data])
  downloadBlob(blob, filename)
}

const normalizeExcelFilename = (filename) => (
  filename.endsWith('.xlsx') ? filename : `${filename}.xlsx`
)

const toExcelValue = (value) => {
  if (value == null) return ''
  return value
}

/**
 * 将表格数据导出为 Excel 文件。
 *
 * @param {object} options
 * @param {string} options.filename - 下载文件名
 * @param {string} [options.sheetName] - 工作表名称
 * @param {Array<string|{header:string,key:string,width?:number}>} options.columns - 表头配置
 * @param {Array<object|Array>} options.rows - 数据行
 * @param {string} [options.title] - 可选标题
 * @param {Array<Array>} [options.summaryRows] - 可选汇总行
 */
export const downloadRowsAsExcel = async ({
  filename,
  sheetName = '数据',
  columns,
  rows,
  title = '',
  summaryRows = []
}) => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet(sheetName)
  const normalizedColumns = columns.map(column => (
    typeof column === 'string' ? { header: column, key: column } : column
  ))

  if (title) {
    const titleRow = worksheet.addRow([title])
    titleRow.font = { bold: true, size: 14 }
    worksheet.mergeCells(1, 1, 1, Math.max(normalizedColumns.length, 1))
    worksheet.addRow([])
  }

  summaryRows.forEach(row => worksheet.addRow(row.map(toExcelValue)))
  if (summaryRows.length > 0) worksheet.addRow([])

  const headerRow = worksheet.addRow(normalizedColumns.map(column => column.header))
  headerRow.font = { bold: true }
  headerRow.eachCell(cell => {
    cell.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFEAF2FF' }
    }
  })

  rows.forEach(row => {
    worksheet.addRow(normalizedColumns.map((column, index) => {
      if (Array.isArray(row)) return toExcelValue(row[index])
      return toExcelValue(row[column.key])
    }))
  })

  normalizedColumns.forEach((column, index) => {
    worksheet.getColumn(index + 1).width = column.width || Math.max(String(column.header).length + 4, 12)
  })

  const buffer = await workbook.xlsx.writeBuffer()
  downloadExcel(buffer, normalizeExcelFilename(filename))
}

/**
 * 下载 API 响应中的文件数据。
 *
 * 保持现有页面行为：直接把 response.data 包装为 Blob 后下载。
 *
 * @param {object} response - API 响应
 * @param {string} filename - 下载文件名
 */
export const downloadResponseFile = (response, filename) => {
  const blob = new Blob([response?.data])
  downloadBlob(blob, filename)
}

/**
 * 获取文件列表的空值保护
 *
 * @param {object} response - API 响应
 * @returns {Array} 文件列表数组
 */
export const getFileListFromResponse = (response) => {
  return response?.data?.items || response?.data?.files || []
}

/**
 * 获取文件统计数据的空值保护
 *
 * @param {object} response - API 响应
 * @returns {object} 统计对象
 */
export const getFileStatsFromResponse = (response) => {
  return response?.data?.stats || response?.data || {}
}

/**
 * 从后端错误响应中提取 detail，保留原页面 fallback 文案。
 *
 * @param {object} error - API 错误
 * @param {string} fallback - 默认错误文案
 * @returns {string}
 */
export const getFileErrorMessage = (error, fallback) => {
  return error?.response?.data?.detail || fallback
}

/**
 * 从驾驶舱 cards 中读取指定指标值。
 *
 * @param {Array} cards - 驾驶舱 cards
 * @param {string} label - 指标 label
 * @param {*} fallback - 默认值
 * @returns {*}
 */
export const getDashboardCardValue = (cards, label, fallback = 0) => {
  const card = cards?.find(item => item.label === label)
  return card?.value ?? fallback
}
