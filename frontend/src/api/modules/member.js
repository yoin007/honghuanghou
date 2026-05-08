/**
 * 成员管理 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const memberApi = {
  getMembers(params = {}) {
    return httpClient.get('/api/members', { params })
  },
  createMember(data) {
    return httpClient.post('/api/members', data)
  },
  updateMember(uuid, data) {
    return httpClient.put(`/api/members/${uuid}`, data)
  },
  deleteMember(uuid) {
    return httpClient.delete(`/api/members/${uuid}`)
  }
}

export const getMembers = memberApi.getMembers
export const createMember = memberApi.createMember
export const updateMember = memberApi.updateMember
export const deleteMember = memberApi.deleteMember

export default memberApi