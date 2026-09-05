<template>
  <div class="attachment-upload">
    <el-upload
      ref="uploadRef"
      v-model:file-list="fileList"
      action="#"
      :limit="3"
      :multiple="true"
      :accept="acceptTypes"
      :before-upload="beforeUpload"
      :http-request="handleUpload"
      :on-remove="handleRemove"
      :on-exceed="handleExceed"
      list-type="text"
      class="attachment-uploader"
    >
      <el-button type="primary" :icon="Paperclip" :loading="uploading">
        添加附件
      </el-button>
      <template #tip>
        <div class="upload-tip">
          最多 3 个附件，单个不超过 10MB；支持图片、PDF、Office 文档、MP3/WAV
        </div>
      </template>
      <template #file="{ file }">
        <div class="attachment-file-item">
          <template v-if="isImage(file)">
            <el-image
              :src="getPreviewUrl(file)"
              :preview-src-list="imagePreviewList"
              fit="cover"
              class="attachment-thumb"
            />
          </template>
          <template v-else>
            <el-icon class="file-icon" :size="28">
              <Document v-if="isDocument(file)" />
              <Headset v-else-if="isAudio(file)" />
              <Files v-else />
            </el-icon>
          </template>
          <div class="file-info">
            <div class="file-name" :title="fileName(file)">{{ fileName(file) }}</div>
            <div class="file-actions">
              <el-button
                v-if="isImage(file)"
                link
                type="primary"
                size="small"
                @click="previewImage(file)"
              >
                预览
              </el-button>
              <el-button
                link
                type="primary"
                size="small"
                @click="downloadFile(file)"
              >
                下载
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                @click="removeFile(file)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
      </template>
    </el-upload>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Paperclip, Document, Headset, Files } from '@element-plus/icons-vue'
import { uploadAttachments, deleteAttachment } from '@/api/modules/moral'
import { useAttachmentUrls } from '@/composables/useAttachmentUrls'

// 附件接口需 Authorization 头鉴权，图片/下载统一走 Blob 对象 URL
const { urls, ensure, revoke, download: downloadAttachmentFile } = useAttachmentUrls()

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  existingAttachments: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const MAX_FILE_SIZE = 10 * 1024 * 1024
const acceptTypes = '.jpg,.jpeg,.png,.gif,.webp,.bmp,.pdf,.xlsx,.xls,.docx,.doc,.pptx,.ppt,.mp3,.wav,image/*'

const uploadRef = ref(null)
const uploading = ref(false)

const extensionTypeMap = {
  jpg: 'image', jpeg: 'image', png: 'image', gif: 'image',
  webp: 'image', bmp: 'image',
  pdf: 'document',
  xlsx: 'document', xls: 'document', docx: 'document', doc: 'document',
  pptx: 'document', ppt: 'document',
  mp3: 'audio', wav: 'audio'
}

const allowedExtensions = Object.keys(extensionTypeMap)

function getExtension(filename = '') {
  const ext = filename.split('.').pop().toLowerCase()
  return ext
}

function fileType(file) {
  if (file.fileType) return file.fileType
  if (file.raw?.type) {
    if (file.raw.type.startsWith('image/')) return 'image'
    if (file.raw.type.startsWith('audio/')) return 'audio'
    return 'document'
  }
  return extensionTypeMap[getExtension(fileName(file))] || 'file'
}

function isImage(file) {
  return fileType(file) === 'image'
}

function isDocument(file) {
  return fileType(file) === 'document'
}

function isAudio(file) {
  return fileType(file) === 'audio'
}

function fileName(file) {
  return file.name || file.original_name || file.fileName || '未命名文件'
}

function getFileId(file) {
  // el-upload 的 onSuccess(uploaded) 会把 uploaded 挂到 file.response
  return file.attachmentId || file.id || file.response?.id
}

function getPreviewUrl(file) {
  const id = getFileId(file)
  // 优先缩略图对象 URL，原图 URL 未就绪时兜底用缩略图
  return id ? (urls[`${id}_t`] || urls[`${id}`] || '') : (file.url || '')
}

const imagePreviewList = computed(() => {
  return fileList.value
    .filter(isImage)
    .map(f => {
      const id = getFileId(f)
      return id ? urls[`${id}`] : (f.url || '')
    })
    .filter(Boolean)
})

const fileList = ref([])

function syncFromProps() {
  const existing = (props.existingAttachments || []).map(att => ({
    ...att,
    name: att.original_name || att.name,
    attachmentId: att.id,
    fileType: att.file_type,
    status: 'success'
  }))
  const uploaded = (props.modelValue || []).map(id => {
    const found = existing.find(a => a.id === id)
    return found || { attachmentId: id, name: '附件', status: 'success' }
  })
  // 合并去重
  const map = new Map()
  ;[...existing, ...uploaded].forEach(item => {
    const key = item.attachmentId || item.id
    if (key && !map.has(key)) map.set(key, item)
  })
  fileList.value = Array.from(map.values())
}

watch(() => [props.modelValue, props.existingAttachments], syncFromProps, { immediate: true, deep: true })

// 图片附件以 Blob 对象 URL 展示/预览；文件移除时释放对应 URL
watch(fileList, (list) => {
  const aliveIds = new Set()
  list.forEach(f => {
    if (!isImage(f)) return
    const id = getFileId(f)
    if (!id) return
    aliveIds.add(id)
    ensure(id, true).catch(() => {})   // 缩略图
    ensure(id, false).catch(() => {})  // 预览原图（弹窗内最多 3 个，量小）
  })
  Object.keys(urls).forEach(k => {
    const isThumb = k.endsWith('_t')
    const id = Number(isThumb ? k.slice(0, -2) : k)
    if (!aliveIds.has(id)) revoke(id, isThumb)
  })
}, { deep: true })

function emitIds() {
  const ids = fileList.value
    .map(getFileId)
    .filter(Boolean)
  emit('update:modelValue', ids)
}

function beforeUpload(rawFile) {
  const ext = getExtension(rawFile.name)
  if (!allowedExtensions.includes(ext)) {
    ElMessage.error(`不支持的文件格式：${ext}`)
    return false
  }
  if (rawFile.size > MAX_FILE_SIZE) {
    ElMessage.error('单个附件大小不能超过 10MB')
    return false
  }
  return true
}

function handleExceed() {
  ElMessage.warning('每个记录最多上传 3 个附件')
}

async function handleUpload(options) {
  const { file, onProgress, onSuccess, onError } = options
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('files', file)
    // httpClient 响应拦截器已解包：res = { success, data: [...] }
    const res = await uploadAttachments(formData)
    const uploadedList = res?.data || []
    if (uploadedList.length) {
      const uploaded = uploadedList[0]
      onSuccess && onSuccess(uploaded)
      // 等 el-upload 添加文件后再更新 attachmentId
      nextTick(() => {
        const target = fileList.value.find(f => f.uid === file.uid || f.name === file.name)
        if (target) {
          target.attachmentId = uploaded.id
          target.fileType = uploaded.file_type
        }
        emitIds()
      })
    } else {
      throw new Error('上传返回数据异常')
    }
  } catch (err) {
    ElMessage.error(err?.response?.data?.detail || '附件上传失败')
    onError && onError(err)
  } finally {
    uploading.value = false
  }
}

function removeFile(file) {
  const idx = fileList.value.indexOf(file)
  if (idx > -1) {
    fileList.value.splice(idx, 1)
    handleRemove(file, fileList.value)
  }
}

async function handleRemove(file, files) {
  const id = getFileId(file)
  if (id) {
    try {
      await deleteAttachment(id)
    } catch (err) {
      // 静默忽略，服务端会在记录更新时再次清理
    }
  }
  fileList.value = files
  emitIds()
}

function previewImage(file) {
  // el-image 预览通过 preview-src-list 自动处理
}

function downloadFile(file) {
  const id = getFileId(file)
  if (!id) return
  downloadAttachmentFile({ id, original_name: fileName(file) }).catch(() => {})
}
</script>

<style scoped>
.attachment-upload {
  width: 100%;
}
.upload-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 6px;
  line-height: 1.4;
}
.attachment-file-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}
.attachment-file-item:last-child {
  border-bottom: none;
}
.attachment-thumb {
  width: 80px;
  height: 80px;
  border-radius: 4px;
  object-fit: cover;
  border: 1px solid #ebeef5;
  flex-shrink: 0;
}
.file-icon {
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 4px;
  color: #606266;
  flex-shrink: 0;
}
.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.file-name {
  font-size: 14px;
  color: #303133;
  word-break: break-all;
  line-height: 1.4;
}
.file-actions {
  display: flex;
  gap: 8px;
}
</style>
