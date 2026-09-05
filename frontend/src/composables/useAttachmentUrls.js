import { reactive, onUnmounted } from 'vue'
import { fetchAttachmentBlob } from '@/api/modules/moral'
import { downloadBlob } from '@/utils/filegather'

/**
 * 附件对象 URL 管理
 *
 * 附件下载接口需要 Authorization 头鉴权，<img src>、<a href> 等浏览器
 * 原生请求无法携带该头，因此统一用 axios 拉取 Blob 再 createObjectURL。
 * - urls 为响应式映射：key 为 `${id}`（原图）或 `${id}_t`（缩略图）
 * - 组件卸载时自动释放全部对象 URL，避免内存泄漏
 */
export function useAttachmentUrls() {
  const urls = reactive({})
  const pending = new Map()

  function cacheKey(id, thumbnail) {
    return thumbnail ? `${id}_t` : `${id}`
  }

  /**
   * 确保附件的对象 URL 已就绪，返回 Promise<string|null>
   * 重复调用同 id 会复用进行中的请求，不重复拉取
   */
  function ensure(id, thumbnail = false) {
    if (!id) return Promise.resolve(null)
    const key = cacheKey(id, thumbnail)
    if (urls[key]) return Promise.resolve(urls[key])
    if (!pending.has(key)) {
      const request = fetchAttachmentBlob(id, thumbnail)
        .then((res) => {
          urls[key] = window.URL.createObjectURL(res.data)
          pending.delete(key)
          return urls[key]
        })
        .catch((err) => {
          pending.delete(key)
          throw err
        })
      pending.set(key, request)
    }
    return pending.get(key)
  }

  /** 释放单个附件的对象 URL（文件从列表移除时调用） */
  function revoke(id, thumbnail = false) {
    const key = cacheKey(id, thumbnail)
    if (urls[key]) {
      window.URL.revokeObjectURL(urls[key])
      delete urls[key]
    }
  }

  /** 拉取附件 Blob 并触发浏览器下载 */
  async function download(att) {
    const res = await fetchAttachmentBlob(att.id, false)
    downloadBlob(res.data, att.original_name || att.name || `attachment_${att.id}`)
  }

  onUnmounted(() => {
    Object.values(urls).forEach((u) => window.URL.revokeObjectURL(u))
    Object.keys(urls).forEach((k) => delete urls[k])
  })

  return {
    urls,
    ensure,
    revoke,
    download
  }
}
