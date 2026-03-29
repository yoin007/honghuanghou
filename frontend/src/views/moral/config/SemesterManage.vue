<template>
  <div class="semester-manage-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>学年学期管理</span>
          <div>
            <el-button type="success" @click="handleAddYear">新增学年</el-button>
            <el-button type="primary" @click="handleAddSemester">新增学期</el-button>
          </div>
        </div>
      </template>

      <el-table :data="semesterList" v-loading="loading" stripe>
        <el-table-column prop="school_year_name" label="学年" width="150" />
        <el-table-column prop="semester_name" label="学期" width="100" />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.semester_type === 1 ? '上学期' : '下学期' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_date" label="开始日期" width="120" />
        <el-table-column prop="end_date" label="结束日期" width="120" />
        <el-table-column label="当前学期" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.is_current" type="success" effect="dark">当前</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_current"
              link
              type="success"
              @click="handleSetCurrent(row)"
            >
              设为当前
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增学年对话框 -->
    <el-dialog v-model="yearDialogVisible" title="新增学年" width="400px">
      <el-form :model="yearForm" :rules="yearRules" ref="yearFormRef" label-width="100px">
        <el-form-item label="学年名称" prop="school_year_name">
          <el-input v-model="yearForm.school_year_name" placeholder="如：2025-2026学年" maxlength="30" />
        </el-form-item>
        <el-form-item label="起始年份" prop="start_year">
          <el-date-picker
            v-model="yearForm.start_year"
            type="year"
            placeholder="选择年份"
            value-format="YYYY"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="yearDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleYearSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新增学期对话框 -->
    <el-dialog v-model="semesterDialogVisible" title="新增学期" width="450px">
      <el-form :model="semesterForm" :rules="semesterRules" ref="semesterFormRef" label-width="100px">
        <el-form-item label="所属学年" prop="school_year_id">
          <el-select v-model="semesterForm.school_year_id" placeholder="选择学年" style="width: 100%">
            <el-option v-for="year in schoolYearList" :key="year.school_year_id" :label="year.school_year_name" :value="year.school_year_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学期类型" prop="semester_type">
          <el-radio-group v-model="semesterForm.semester_type">
            <el-radio :label="1">上学期</el-radio>
            <el-radio :label="2">下学期</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="学期名称" prop="semester_name">
          <el-input v-model="semesterForm.semester_name" placeholder="自动生成，可修改" maxlength="20" />
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker
            v-model="semesterForm.start_date"
            type="date"
            placeholder="选择开始日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker
            v-model="semesterForm.end_date"
            type="date"
            placeholder="选择结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="semesterDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSemesterSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSchoolYears, createSchoolYear, getSemesters, createSemester, setCurrentSemester } from '@/api/modules/moral'

const loading = ref(false)
const semesterList = ref([])
const schoolYearList = ref([])

const yearDialogVisible = ref(false)
const yearFormRef = ref(null)
const yearForm = reactive({
  school_year_name: '',
  start_year: ''
})
const yearRules = {
  school_year_name: [{ required: true, message: '请输入学年名称', trigger: 'blur' }],
  start_year: [{ required: true, message: '请选择起始年份', trigger: 'change' }]
}

const semesterDialogVisible = ref(false)
const semesterFormRef = ref(null)
const semesterForm = reactive({
  school_year_id: null,
  semester_type: 1,
  semester_name: '',
  start_date: '',
  end_date: ''
})
const semesterRules = {
  school_year_id: [{ required: true, message: '请选择所属学年', trigger: 'change' }],
  semester_type: [{ required: true, message: '请选择学期类型', trigger: 'change' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  end_date: [{ required: true, message: '请选择结束日期', trigger: 'change' }]
}

const fetchSchoolYears = async () => {
  try {
    const res = await getSchoolYears()
    if (res.success) schoolYearList.value = res.data
  } catch (error) {
    console.error('获取学年列表失败:', error)
  }
}

const fetchSemesters = async () => {
  loading.value = true
  try {
    const res = await getSemesters()
    if (res.success) semesterList.value = res.data
  } catch (error) {
    console.error('获取学期列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleAddYear = () => {
  const currentYear = new Date().getFullYear()
  Object.assign(yearForm, {
    school_year_name: `${currentYear}-${currentYear + 1}学年`,
    start_year: String(currentYear)
  })
  yearDialogVisible.value = true
}

const handleYearSubmit = async () => {
  try {
    await yearFormRef.value.validate()
    const res = await createSchoolYear({
      school_year_name: yearForm.school_year_name,
      start_year: parseInt(yearForm.start_year)
    })
    if (res.success) {
      ElMessage.success('学年创建成功')
      yearDialogVisible.value = false
      fetchSchoolYears()
    }
  } catch (error) {
    console.error('创建失败:', error)
  }
}

const handleAddSemester = () => {
  const now = new Date()
  const month = now.getMonth() + 1
  const isSecondSemester = month >= 2 && month <= 7

  Object.assign(semesterForm, {
    school_year_id: schoolYearList.value[0]?.school_year_id || null,
    semester_type: isSecondSemester ? 2 : 1,
    semester_name: '',
    start_date: '',
    end_date: ''
  })
  semesterDialogVisible.value = true
}

watch(
  () => [semesterForm.school_year_id, semesterForm.semester_type],
  ([yearId, type]) => {
    if (yearId && type) {
      const year = schoolYearList.value.find(y => y.school_year_id === yearId)
      if (year) {
        const typeName = type === 1 ? '上学期' : '下学期'
        semesterForm.semester_name = `${year.school_year_name}${typeName}`
      }
    }
  }
)

const handleSemesterSubmit = async () => {
  try {
    await semesterFormRef.value.validate()
    const res = await createSemester({
      school_year_id: semesterForm.school_year_id,
      semester_type: semesterForm.semester_type,
      semester_name: semesterForm.semester_name,
      start_date: semesterForm.start_date,
      end_date: semesterForm.end_date
    })
    if (res.success) {
      ElMessage.success('学期创建成功')
      semesterDialogVisible.value = false
      fetchSemesters()
    }
  } catch (error) {
    console.error('创建失败:', error)
  }
}

const handleSetCurrent = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要将"${row.semester_name}"设为当前学期吗？`, '提示', { type: 'warning' })
    const res = await setCurrentSemester(row.semester_id)
    if (res.success) {
      ElMessage.success('已设为当前学期')
      fetchSemesters()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('设置失败:', error)
  }
}

onMounted(() => {
  fetchSchoolYears()
  fetchSemesters()
})
</script>

<style scoped>
.semester-manage-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>