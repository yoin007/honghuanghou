/**
 * 系统监控 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const systemApi = {
  getHealth() {
    return httpClient.get('/api/health')
  },
  getWsStatus() {
    return httpClient.get('/api/ws/status')
  }
}

export const getHealth = systemApi.getHealth
export const getWsStatus = systemApi.getWsStatus

export default systemApi