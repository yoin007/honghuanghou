/**
 * 教师留言 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const messageApi = {
  getMessages(classCode) {
    return httpClient.get(`/api/messages/${classCode}`)
  }
}

export const getMessages = messageApi.getMessages

export default messageApi