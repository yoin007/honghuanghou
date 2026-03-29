<template>
  <div class="class-manage-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>班级管理</span>
          <el-button type="primary" @click="handleAdd">新增班级</el-button>
        </div>
      </template>

      <div class="filter-section">
        <el-select v-model="filterGradeId" placeholder="选择级号" clearable @change="fetchClasses" style="width: 200px">
          <el-option v-for="grade in gradeList" :key="grade.grade_id" :label="grade.grade_name" :value="grade.grade_id" />
        </el-select>
      </div>

      <el-table :data="classList" v-loading="loading" stripe>
        <el-table-column prop="class_name" label="班级名称" width="150" />
        <el-table-column prop="grade_name" label="所属级号" width="120" />
        <el-table-column prop="leader_name" label="班主任" width="100">
          <template #default="{ row }">
            <span>{{ row.leader_name || '未指定' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="student_count" label="学生数" width="80">
          <template #default="{ row }">
            <el-tag type="success">{{ row.student_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="primary" @click="handleViewStudents(row)">查看学生</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="所属级号" prop="grade_id">
          <el-select v-model="form.grade_id" placeholder="选择级号" style="width: 100%" @change="handleGradeChange">
            <el-option v-for="grade in gradeList" :key="grade.grade_id" :label="grade.grade_name" :value="grade.grade_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="班级代码" prop="class_code">
          <el-input v-model="form.class_code" placeholder="如：2026-1" maxlength="20" />
        </el-form-item>
        <el-form-item label="班号" prop="class_number">
          <el-input-number v-model="form.class_number" :min="1" :max="30" style="width: 100%" />
        </el-form-item>
        <el-form-item label="班级名称" prop="class_name">
          <el-input v-model="form.class_name" placeholder="如：1班、2班" maxlength="20" />
        </el-form-item>
        <el-form-item label="班主任">
          <el-select v-model="form.leader_name" placeholder="选择班主任" clearable filterable style="width: 100%">
            <el-option v-for="teacher in teacherList" :key="teacher.teacher_id" :label="teacher.name" :value="teacher.name" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 学生列表对话框 -->
    <el-dialog v-model="studentDialogVisible" :title="`${currentClass?.class_name} - 学生列表`" width="700px">
      <el-table :data="studentsByClass" v-loading="studentLoading" stripe max-height="400">
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="gender" label="性别" width="60">
          <template #default="{ row }">
            <el-tag :type="row.gender === '男' ? 'primary' : 'danger'" size="small">{{ row.gender }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="birthday" label="生日" width="100" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === '在校' ? 'success' : 'warning'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getGrades, getClasses, createClass, updateClass, deleteClass, getStudents, getTeachers } from '@/api/modules/moral'

const loading = ref(false)
const classList = ref([])
const gradeList = ref([])
const teacherList = ref([])
const filterGradeId = ref(null)

const dialogVisible = ref(false)
const formRef = ref(null)
const form = reactive({
  class_id: null,
  grade_id: null,
  class_code: '',
  class_number: 1,
  class_name: '',
  leader_name: ''
})
const rules = {
  grade_id: [{ required: true, message: '请选择级号', trigger: 'change' }],
  class_code: [{ required: true, message: '请输入班级代码', trigger: 'blur' }],
  class_number: [{ required: true, message: '请输入班号', trigger: 'blur' }],
  class_name: [{ required: true, message: '请输入班级名称', trigger: 'blur' }]
}
const dialogTitle = computed(() => form.class_id ? '编辑班级' : '新增班级')

const studentDialogVisible = ref(false)
const studentLoading = ref(false)
const studentsByClass = ref([])
const currentClass = ref(null)

const fetchGrades = async () => {
  try {
    const res = await getGrades()
    if (res.success) gradeList.value = res.data
  } catch (error) {
    console.error('获取级号列表失败:', error)
  }
}

const fetchTeachers = async () => {
  try {
    const res = await getTeachers()
    if (res.teachers) {
      // Transform teachers data for use in select
      teacherList.value = res.teachers.map(t => ({
        teacher_id: t.username,
        name: t.username
      }))
    }
  } catch (error) {
    console.error('获取教师列表失败:', error)
  }
}

const fetchClasses = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterGradeId.value) params.grade_id = filterGradeId.value
    const res = await getClasses(params)
    if (res.success) classList.value = res.data
  } catch (error) {
    console.error('获取班级列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  const selectedGrade = gradeList.value.find(g => g.grade_id === filterGradeId.value)
  const year = selectedGrade?.enrollment_year || new Date().getFullYear()
  const classCount = classList.value.filter(c => c.grade_id === filterGradeId.value).length + 1
  Object.assign(form, {
    class_id: null,
    grade_id: filterGradeId.value || null,
    class_code: `${year}-${classCount}`,
    class_number: classCount,
    class_name: `${classCount}班`,
    leader_name: ''
  })
  dialogVisible.value = true
}

const handleGradeChange = (gradeId) => {
  const selectedGrade = gradeList.value.find(g => g.grade_id === gradeId)
  if (selectedGrade) {
    const classCount = classList.value.filter(c => c.grade_id === gradeId).length + 1
    form.class_code = `${selectedGrade.enrollment_year}-${classCount}`
    form.class_number = classCount
    form.class_name = `${classCount}班`
  }
}

const handleEdit = (row) => {
  Object.assign(form, {
    class_id: row.class_id,
    grade_id: row.grade_id,
    class_code: row.class_code,
    class_number: row.class_number,
    class_name: row.class_name,
    leader_name: row.leader_name || ''
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    const data = {
      class_code: form.class_code,
      grade_id: form.grade_id,
      class_number: form.class_number,
      class_name: form.class_name,
      leader_name: form.leader_name || null
    }

    let res
    if (form.class_id) {
      res = await updateClass(form.class_id, data)
    } else {
      res = await createClass(data)
    }

    if (res.success) {
      ElMessage.success(form.class_id ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchClasses()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

const handleDelete = async (row) => {
  if (row.student_count > 0) {
    ElMessage.warning('该班级下存在学生，无法删除')
    return
  }
  try {
    await ElMessageBox.confirm('确定要删除该班级吗？', '提示', { type: 'warning' })
    const res = await deleteClass(row.class_id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchClasses()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('删除失败:', error)
  }
}

const handleViewStudents = async (row) => {
  currentClass.value = row
  studentDialogVisible.value = true
  studentLoading.value = true
  try {
    const res = await getStudents({ class_id: row.class_id })
    if (res.success) studentsByClass.value = res.data
  } catch (error) {
    console.error('获取学生列表失败:', error)
  } finally {
    studentLoading.value = false
  }
}

onMounted(() => {
  fetchGrades()
  fetchTeachers()
  fetchClasses()
})
</script>

<style scoped>
.class-manage-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filter-section {
  margin-bottom: 20px;
}
</style>