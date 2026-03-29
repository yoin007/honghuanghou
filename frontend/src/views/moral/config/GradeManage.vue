<template>
  <div class="grade-manage-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>级号管理</span>
          <el-button type="primary" @click="handleAdd">新增级号</el-button>
        </div>
      </template>

      <el-table :data="gradeList" v-loading="loading" stripe>
        <el-table-column prop="grade_name" label="级号名称" width="150" />
        <el-table-column prop="enrollment_year" label="入学年份" width="120" />
        <el-table-column prop="class_count" label="班级数" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.class_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="student_count" label="学生数" width="100">
          <template #default="{ row }">
            <el-tag type="success">{{ row.student_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleViewClasses(row)">查看班级</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增对话框 -->
    <el-dialog v-model="dialogVisible" title="新增级号" width="400px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="级号名称" prop="grade_name">
          <el-input v-model="form.grade_name" placeholder="如：2026级" />
        </el-form-item>
        <el-form-item label="入学年份" prop="enrollment_year">
          <el-date-picker
            v-model="form.enrollment_year"
            type="year"
            placeholder="选择年份"
            value-format="YYYY"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 班级列表对话框 -->
    <el-dialog v-model="classDialogVisible" :title="`${currentGrade?.grade_name} - 班级列表`" width="600px">
      <el-table :data="classByGrade" v-loading="classLoading" stripe max-height="400">
        <el-table-column prop="class_name" label="班级名称" />
        <el-table-column prop="leader_name" label="班主任" width="100" />
        <el-table-column prop="student_count" label="学生数" width="80" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getGrades, createGrade, deleteGrade, getClasses } from '@/api/modules/moral'

const loading = ref(false)
const gradeList = ref([])
const dialogVisible = ref(false)
const formRef = ref(null)
const form = reactive({
  grade_name: '',
  enrollment_year: ''
})
const rules = {
  grade_name: [{ required: true, message: '请输入级号名称', trigger: 'blur' }],
  enrollment_year: [{ required: true, message: '请选择入学年份', trigger: 'change' }]
}

const classDialogVisible = ref(false)
const classLoading = ref(false)
const classByGrade = ref([])
const currentGrade = ref(null)

const fetchGrades = async () => {
  loading.value = true
  try {
    const res = await getGrades()
    if (res.success) gradeList.value = res.data
  } catch (error) {
    console.error('获取级号列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  const currentYear = new Date().getFullYear()
  Object.assign(form, {
    grade_name: `${currentYear}级`,
    enrollment_year: String(currentYear)
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    const res = await createGrade({
      grade_name: form.grade_name,
      enrollment_year: parseInt(form.enrollment_year)
    })
    if (res.success) {
      ElMessage.success('创建成功')
      dialogVisible.value = false
      fetchGrades()
    } else {
      ElMessage.error(res.message || '创建失败')
    }
  } catch (error) {
    const msg = error.response?.data?.detail || error.response?.data?.message || error.message || '创建失败'
    ElMessage.error(msg)
    console.error('创建失败:', error)
  }
}

const handleDelete = async (row) => {
  if (row.class_count > 0) {
    ElMessage.warning('该级号下存在班级，无法删除')
    return
  }
  try {
    await ElMessageBox.confirm('确定要删除该级号吗？', '提示', { type: 'warning' })
    const res = await deleteGrade(row.grade_id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchGrades()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('删除失败:', error)
  }
}

const handleViewClasses = async (row) => {
  currentGrade.value = row
  classDialogVisible.value = true
  classLoading.value = true
  try {
    const res = await getClasses({ grade_id: row.grade_id })
    if (res.success) classByGrade.value = res.data
  } catch (error) {
    console.error('获取班级列表失败:', error)
  } finally {
    classLoading.value = false
  }
}

onMounted(() => {
  fetchGrades()
})
</script>

<style scoped>
.grade-manage-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>