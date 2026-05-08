/**
 * LoudPK API
 */
import { httpClient } from '@/shared/api/httpClient'

export const loudpkApi = {
  createLoudpk(data) {
    return httpClient.post('/api/loudpk', data)
  },
  getLoudpkList(params = {}) {
    return httpClient.get('/api/loudpk', { params })
  }
}

export const createLoudpk = loudpkApi.createLoudpk
export const getLoudpkList = loudpkApi.getLoudpkList

export default loudpkApi