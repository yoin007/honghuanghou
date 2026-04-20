<template>
  <div class="student-manage-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>学生管理</span>
          <div>
            <el-button type="success" @click="handleImport">批量导入</el-button>
            <el-button type="primary" @click="handleAdd">新增学生</el-button>
          </div>
        </div>
      </template>

      <div class="filter-section">
        <el-cascader
          v-model="filterGradeClass"
          :options="gradeClassOptions"
          placeholder="选择级号/班级"
          clearable
          @change="handleFilterChange"
          style="width: 250px"
        />
        <el-select v-model="filterStatus" placeholder="学生状态" clearable @change="fetchStudents" style="width: 120px; margin-left: 10px">
          <el-option label="在校" value="在校" />
          <el-option label="毕业" value="毕业" />
          <el-option label="离校" value="离校" />
        </el-select>
      </div>

      <el-table :data="studentList" v-loading="loading" stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="gender" label="性别" width="60">
          <template #default="{ row }">
            <el-tag :type="row.gender === '男' ? 'primary' : 'danger'" size="small">{{ row.gender }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="birthday" label="生日" width="100" />
        <el-table-column prop="roomid" label="宿舍" width="80" />
        <el-table-column prop="rpid" label="床号" width="60" />
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column prop="grade_name" label="级号" width="100" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="入学时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="info" @click="handleViewDetail(row)">详情</el-button>
            <el-button link type="warning" @click="handleUpdateStatus(row)">状态</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchStudents"
        @current-change="fetchStudents"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑学生信息' : '新增学生'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="学号" prop="student_id">
          <el-input v-model="form.student_id" placeholder="输入学号" maxlength="20" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="form.name" placeholder="输入姓名" maxlength="50" />
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-radio-group v-model="form.gender">
            <el-radio label="男">男</el-radio>
            <el-radio label="女">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="生日" prop="birthday">
          <el-date-picker
            v-model="form.birthday"
            type="date"
            placeholder="选择生日"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="班级" prop="class_id">
          <el-cascader
            v-model="form.classSelection"
            :options="gradeClassOptions"
            placeholder="选择班级"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="宿舍">
          <el-input v-model="form.roomid" placeholder="宿舍号（如A101）" maxlength="20" />
        </el-form-item>
        <el-form-item label="床号">
          <el-input v-model="form.rpid" placeholder="床位号（如1）" maxlength="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialogVisible" :title="`${currentStudent?.name} - 学生详情`" width="500px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="学号">{{ currentStudent?.student_id }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ currentStudent?.name }}</el-descriptions-item>
        <el-descriptions-item label="性别">{{ currentStudent?.gender }}</el-descriptions-item>
        <el-descriptions-item label="生日">{{ currentStudent?.birthday }}</el-descriptions-item>
        <el-descriptions-item label="宿舍">{{ currentStudent?.roomid || '-' }}</el-descriptions-item>
        <el-descriptions-item label="床号">{{ currentStudent?.rpid || '-' }}</el-descriptions-item>
        <el-descriptions-item label="班级">{{ currentStudent?.class_name }}</el-descriptions-item>
        <el-descriptions-item label="级号">{{ currentStudent?.grade_name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentStudent?.status)">{{ currentStudent?.status }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="入学时间">{{ currentStudent?.created_at }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 状态变更对话框 -->
    <el-dialog v-model="statusDialogVisible" :title="`变更状态 - ${currentStudent?.name}`" width="400px">
      <el-form :model="statusForm" ref="statusFormRef" label-width="100px">
        <el-form-item label="当前状态">
          <el-tag :type="getStatusType(currentStudent?.status)">{{ currentStudent?.status }}</el-tag>
        </el-form-item>
        <el-form-item label="新状态" prop="new_status">
          <el-select v-model="statusForm.new_status" placeholder="选择新状态" style="width: 100%">
            <el-option label="在校" value="在校" />
            <el-option label="毕业" value="毕业" />
            <el-option label="离校" value="离校" />
          </el-select>
        </el-form-item>
        <el-form-item label="原因">
          <el-input v-model="statusForm.reason" type="textarea" :rows="2" placeholder="状态变更原因（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleStatusSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="批量导入学生" width="500px">
      <el-alert type="info" :closable="false" style="margin-bottom: 20px">
        <template #title>
          请上传Excel文件，格式要求：学号、姓名、性别、生日、班级名称
        </template>
      </el-alert>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleFileChange"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽文件至此处或 <em>点击上传</em></div>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImportSubmit" :loading="importLoading">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { getGrades, getClasses, getStudents, createStudent, updateStudent, updateStudentStatus } from '@/api/modules/moral'

const loading = ref(false)
const studentList = ref([])
const gradeList = ref([])
const classList = ref([])
const filterGradeClass = ref([])
const filterStatus = ref(null)

const isEdit = ref(false)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const dialogVisible = ref(false)
const formRef = ref(null)
const form = reactive({
  student_id: '',
  name: '',
  gender: '男',
  birthday: '',
  roomid: '',
  rpid: '',
  classSelection: []
})
const rules = {
  student_id: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  birthday: [{ required: true, message: '请选择生日', trigger: 'change' }],
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }]
}

const detailDialogVisible = ref(false)
const currentStudent = ref(null)

const statusDialogVisible = ref(false)
const statusFormRef = ref(null)
const statusForm = reactive({
  new_status: '在校',
  reason: ''
})

const importDialogVisible = ref(false)
const uploadRef = ref(null)
const importFile = ref(null)
const importLoading = ref(false)

const gradeClassOptions = computed(() => {
  return gradeList.value.map(grade => ({
    value: grade.grade_id,
    label: grade.grade_name,
    children: classList.value
      .filter(c => c.grade_id === grade.grade_id)
      .map(c => ({
        value: c.class_id,
        label: c.class_name
      }))
  }))
})

const getStatusType = (status) => {
  switch (status) {
    case '在校': return 'success'
    case '毕业': return 'info'
    case '离校': return 'warning'
    default: return ''
  }
}

const fetchGrades = async () => {
  try {
    const res = await getGrades()
    if (res.success) gradeList.value = res.data
  } catch (error) {
    console.error('获取级号列表失败:', error)
  }
}

const fetchAllClasses = async () => {
  try {
    const res = await getClasses()
    if (res.success) classList.value = res.data
  } catch (error) {
    console.error('获取班级列表失败:', error)
  }
}

const fetchStudents = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    if (filterGradeClass.value.length === 2) {
      params.class_id = filterGradeClass.value[1]
    } else if (filterGradeClass.value.length === 1) {
      params.grade_id = filterGradeClass.value[0]
    }
    if (filterStatus.value) {
      params.status = filterStatus.value
    }
    const res = await getStudents(params)
    if (res.success) {
      studentList.value = res.data.items || res.data
      pagination.total = res.data.total || studentList.value.length
    }
  } catch (error) {
    console.error('获取学生列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleFilterChange = () => {
  pagination.page = 1
  fetchStudents()
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(form, {
    student_id: '',
    name: '',
    gender: '男',
    birthday: '',
    roomid: '',
    rpid: '',
    classSelection: filterGradeClass.value.length === 2 ? [...filterGradeClass.value] : []
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  // 查找学生所在班级的级号-班级路径
  const classInfo = classList.value.find(c => c.class_id === row.class_id)
  const gradeId = classInfo?.grade_id
  Object.assign(form, {
    student_id: row.student_id,
    name: row.name,
    gender: row.gender,
    birthday: row.birthday,
    roomid: row.roomid || '',
    rpid: row.rpid || '',
    classSelection: gradeId ? [gradeId, row.class_id] : [row.class_id]
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    const classId = form.classSelection[form.classSelection.length - 1]
    const data = {
      name: form.name,
      gender: form.gender,
      birthday: form.birthday,
      roomid: form.roomid,
      rpid: form.rpid,
      class_id: classId
    }

    let res
    if (isEdit.value) {
      res = await updateStudent(form.student_id, data)
    } else {
      res = await createStudent({
        ...data,
        student_id: form.student_id
      })
    }

    if (res.success) {
      ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchStudents()
    }
  } catch (error) {
    console.error(isEdit.value ? '更新失败:' : '创建失败:', error)
  }
}

const handleViewDetail = (row) => {
  currentStudent.value = row
  detailDialogVisible.value = true
}

const handleUpdateStatus = (row) => {
  currentStudent.value = row
  statusForm.new_status = row.status
  statusForm.reason = ''
  statusDialogVisible.value = true
}

const handleStatusSubmit = async () => {
  try {
    const res = await updateStudentStatus(currentStudent.value.student_id, statusForm.new_status)
    if (res.success) {
      ElMessage.success('状态更新成功')
      statusDialogVisible.value = false
      fetchStudents()
    }
  } catch (error) {
    console.error('状态更新失败:', error)
  }
}

const handleImport = () => {
  importFile.value = null
  importDialogVisible.value = true
}

const handleFileChange = (file) => {
  importFile.value = file.raw
}

const handleImportSubmit = async () => {
  if (!importFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  importLoading.value = true
  try {
    // TODO: Implement actual import API call
    ElMessage.success('导入成功')
    importDialogVisible.value = false
    fetchStudents()
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败，请检查文件格式')
  } finally {
    importLoading.value = false
  }
}

onMounted(() => {
  fetchGrades()
  fetchAllClasses()
  fetchStudents()
})
</script>

<style scoped>
.student-manage-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-section {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}
</style>