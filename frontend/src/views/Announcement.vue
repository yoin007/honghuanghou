<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElTimeline, ElTimelineItem, ElCard, ElEmpty, ElButton, ElDialog, ElForm, ElFormItem, ElInput } from 'element-plus'
import { getAnnouncements, updateAnnouncement, deleteAnnouncement } from '@/api/modules/announcement'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const username = computed(() => authStore.username)
const isAdmin = computed(() => authStore.isAdmin)

const announcements = ref([])
const loading = ref(false)
const classCode = ref('')
const editDialogVisible = ref(false)
const editForm = ref({
  id: null,
  title: '',
  content: ''
})
const updating = ref(false)

const getClassCode = () => {
  const code = document.cookie.split('; ').find(row => row.startsWith('classCode='))
  return code ? code.split('=')[1] : null
}

const canManage = (author) => {
  return isAdmin.value || username.value === author
}

const fetchAnnouncements = async () => {
  const classCode = getClassCode()
  if (!classCode) {
    ElMessage.error('请先选择班级')
    return
  }

  loading.value = true
  try {
    const response = await getAnnouncements(classCode)
    if (response.data && Array.isArray(response.data.announcements)) {
      announcements.value = response.data.announcements.sort((a, b) => 
        new Date(b.date) - new Date(a.date)
      )
    } else {
      announcements.value = []
      ElMessage.warning('暂无公告')
    }
  } catch (error) {
    console.error('Error fetching announcements:', error)
    ElMessage.error('获取公告失败')
    announcements.value = []
  } finally {
    loading.value = false
  }
}

const openEditDialog = (ann) => {
  editForm.value = {
    id: ann.id,
    title: ann.title,
    content: ann.content
  }
  editDialogVisible.value = true
}

const handleUpdate = async () => {
  updating.value = true
  try {
    await updateAnnouncement(editForm.value.id, {
      title: editForm.value.title,
      content: editForm.value.content
    })
    ElMessage.success('公告更新成功')
    editDialogVisible.value = false
    fetchAnnouncements()
  } catch (error) {
    console.error('Update announcement error:', error)
    ElMessage.error('更新失败：' + (error.response?.data?.detail || '未知错误'))
  } finally {
    updating.value = false
  }
}

const handleDelete = async (annId) => {
  try {
    await deleteAnnouncement(annId)
    ElMessage.success('公告删除成功')
    fetchAnnouncements()
  } catch (error) {
    console.error('Delete announcement error:', error)
    ElMessage.error('删除失败：' + (error.response?.data?.detail || '未知错误'))
  }
}

onMounted(() => {
  fetchAnnouncements()
  classCode.value = getClassCode()
})
</script>

<template>
  <div class="announcement-container">
    <h2>{{ classCode ? `${classCode}公告` : '公告' }}</h2>
    <el-empty v-if="!loading && announcements.length === 0" description="暂无公告" />
    <el-timeline v-else>
      <el-timeline-item
        v-for="announcement in announcements"
        :key="announcement.id"
        :timestamp="announcement.date"
        type="primary"
        size="large"
        placement="top"
      >
        <el-card class="announcement-card">
          <template #header>
            <div class="card-header">
              <h4>{{ announcement.title }}  ({{ announcement.author }})</h4>
              <div v-if="canManage(announcement.author)" class="card-actions">
                <el-button size="small" type="primary" @click="openEditDialog(announcement)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDelete(announcement.id)">删除</el-button>
              </div>
            </div>
          </template>
          <p class="announcement-content">{{ announcement.content }}</p>
        </el-card>
      </el-timeline-item>
    </el-timeline>

    <el-dialog v-model="editDialogVisible" title="编辑公告" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="editForm.content" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate" :loading="updating">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.announcement-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h2 {
  margin-bottom: 20px;
  color: #409EFF;
  text-align: center;
}

.announcement-card {
  margin-bottom: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.announcement-content {
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
}
</style>
