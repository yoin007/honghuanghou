/**
 * 每日早报 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const dailyNewsApi = {
  /** 获取早报，params 支持 { date: 'YYYY-MM-DD' }。历史日期无数据时后端返回 404，
   *  这里抑制全局错误弹窗，由页面自行显示"该日期暂无数据"的空态。 */
  getDailyNews(params = {}) {
    return httpClient.get('/api/daily-news', { params, silentStatuses: [404] })
  },
  /** 强制刷新当日（忽略缓存） */
  refresh() {
    return httpClient.get('/api/daily-news', { params: { force: 1 } })
  },
  /** 已缓存的日期列表 */
  listDates(limit = 90) {
    return httpClient.get('/api/daily-news/dates', { params: { limit } })
  }
}

export const getDailyNews = dailyNewsApi.getDailyNews
export const refreshDailyNews = dailyNewsApi.refresh
export const listDailyNewsDates = dailyNewsApi.listDates

export default dailyNewsApi
