/**
 * 公告管理 API
 */
import { httpClient } from '@/shared/api/httpClient'

export const announcementApi = {
  getAnnouncements(classCode) {
    return httpClient.get(`/api/announcements/${classCode}`)
  },
  updateAnnouncement(id, data) {
    return httpClient.put(`/api/announcement/${id}`, data)
  },
  deleteAnnouncement(id) {
    return httpClient.delete(`/api/announcement/${id}`)
  },
  createAnnouncement(data) {
    return httpClient.post('/api/announcement/', data)
  },

  /**
   * 发布公告（multipart/form-data）
   * @param {FormData} formData 公告数据
   * @returns {Promise}
   */
  publishAnnouncement(formData) {
    return httpClient.post('/api/announcement/', formData)
  }
}

export const getAnnouncements = announcementApi.getAnnouncements
export const updateAnnouncement = announcementApi.updateAnnouncement
export const deleteAnnouncement = announcementApi.deleteAnnouncement
export const createAnnouncement = announcementApi.createAnnouncement
export const publishAnnouncement = announcementApi.publishAnnouncement

export default announcementApi