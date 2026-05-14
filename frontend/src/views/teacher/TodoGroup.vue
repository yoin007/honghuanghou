<template>
  <div class="group-page">
    <el-card class="header-card">
      <div class="header-actions">
        <el-button type="primary" @click="handleAdd">新建群组</el-button>
      </div>
    </el-card>

    <el-card class="table-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>我的协作群组</span>
          <span class="summary-text">共 {{ groupList.length }} 个群组</span>
        </div>
      </template>

      <el-empty v-if="groupList.length === 0" description="暂无协作群组" />
      <div v-else class="group-list">
        <div v-for="group in groupList" :key="group.group_id" class="group-item">
          <div class="group-header">
            <span class="group-name">{{ group.group_name }}</span>
            <span class="group-meta">{{ group.members?.length || 0 }} 人</span>
          </div>
          <div class="group-members">
            <el-tag v-for="m in group.members" :key="m.teacher_id" size="small" closable @close="handleRemoveMember(group.group_id, m.teacher_id)">
              {{ m.teacher_name }}
            </el-tag>
            <el-button link type="primary" size="small" @click="handleAddMember(group.group_id)">添加成员</el-button>
          </div>
          <div class="group-actions">
            <el-button link type="primary" @click="handleEdit(group)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(group.group_id)">删除</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 新建/编辑群组对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="400px">
      <el-form :model="groupForm" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="群组名称" prop="group_name">
          <el-input v-model="groupForm.group_name" placeholder="输入群组名称" maxlength="50" show-word-limit />
        </el-form-item>
        <el-form-item label="初始成员" v-if="!editingGroupId">
          <el-select v-model="groupForm.member_teacher_ids" multiple filterable placeholder="选择初始成员" style="width: 100%">
            <el-option v-for="t in teacherList" :key="t.teacher_id || t.username" :label="teacherLabel(t)" :value="t.teacher_id || t.username" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加成员对话框 -->
    <el-dialog v-model="memberDialogVisible" title="添加群组成员" width="400px">
      <el-select v-model="newMemberIds" multiple filterable placeholder="选择要添加的教师" style="width: 100%">
        <el-option v-for="t in teacherList" :key="t.teacher_id || t.username" :label="teacherLabel(t)" :value="t.teacher_id || t.username" />
      </el-select>
      <template #footer>
        <el-button @click="memberDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAddMemberSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getGroups, createGroup, updateGroup, deleteGroup, addGroupMembers, removeGroupMember } from '@/api/modules/teacherTodo'
import { teacherApi } from '@/api/modules/teacher'

const loading = ref(false)
const groupList = ref([])
const teacherList = ref([])

const dialogVisible = ref(false)
const dialogTitle = ref('新建群组')
const formRef = ref(null)
const editingGroupId = ref(null)

const groupForm = reactive({
  group_name: '',
  member_teacher_ids: []
})

const rules = {
  group_name: [{ required: true, message: '请输入群组名称', trigger: 'blur' }]
}

const memberDialogVisible = ref(false)
const memberGroupId = ref(null)
const newMemberIds = ref([])

const teacherLabel = (teacher) => {
  const name = teacher.username || teacher.name || teacher.teacher_name || teacher.teacher_id
  const subject = teacher.subject ? ` - ${teacher.subject}` : ''
  return `${name}${subject}`
}

const fetchGroups = async () => {
  loading.value = true
  try {
    const res = await getGroups()
    if (res.success) {
      groupList.value = res.data.groups || []
    }
  } catch (e) {
    ElMessage.error('获取群组列表失败')
  } finally {
    loading.value = false
  }
}

const fetchTeachers = async () => {
  try {
    const res = await teacherApi.getTeachers()
    const data = res.data || res
    teacherList.value = data.teachers || []
  } catch (e) {
    console.error('获取教师列表失败:', e)
  }
}

const handleAdd = () => {
  dialogTitle.value = '新建群组'
  editingGroupId.value = null
  groupForm.group_name = ''
  groupForm.member_teacher_ids = []
  dialogVisible.value = true
}

const handleEdit = (group) => {
  dialogTitle.value = '编辑群组'
  editingGroupId.value = group.group_id
  groupForm.group_name = group.group_name
  groupForm.member_teacher_ids = []
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  try {
    if (editingGroupId.value) {
      await updateGroup(editingGroupId.value, { group_name: groupForm.group_name })
      ElMessage.success('更新成功')
    } else {
      await createGroup({ group_name: groupForm.group_name, member_teacher_ids: groupForm.member_teacher_ids })
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchGroups()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (groupId) => {
  try {
    await ElMessageBox.confirm('确定删除该群组？', '确认删除', { type: 'warning' })
    await deleteGroup(groupId)
    ElMessage.success('删除成功')
    fetchGroups()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const handleAddMember = (groupId) => {
  memberGroupId.value = groupId
  newMemberIds.value = []
  memberDialogVisible.value = true
}

const handleAddMemberSubmit = async () => {
  if (newMemberIds.value.length === 0) {
    ElMessage.warning('请选择要添加的教师')
    return
  }
  try {
    await addGroupMembers(memberGroupId.value, newMemberIds.value)
    ElMessage.success('成员添加成功')
    memberDialogVisible.value = false
    fetchGroups()
  } catch (e) {
    ElMessage.error('添加失败')
  }
}

const handleRemoveMember = async (groupId, teacherId) => {
  try {
    await removeGroupMember(groupId, teacherId)
    ElMessage.success('成员已移除')
    fetchGroups()
  } catch (e) {
    ElMessage.error('移除失败')
  }
}

onMounted(() => {
  fetchGroups()
  fetchTeachers()
})
</script>

<style scoped>
.group-page {
  padding: 20px;
}

.header-card {
  margin-bottom: 16px;
}

.header-actions {
  display: flex;
  justify-content: flex-end;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.summary-text {
  font-size: 14px;
  color: #909399;
}

.group-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.group-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px;
}

.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.group-name {
  font-weight: 500;
  font-size: 16px;
}

.group-meta {
  color: #909399;
  font-size: 14px;
}

.group-members {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.group-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>