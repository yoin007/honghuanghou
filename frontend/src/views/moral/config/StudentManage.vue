<template>
  <div class="student-manage-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>学生管理</span>
          <div>
            <el-button @click="handleExport">导出</el-button>
            <el-button @click="downloadTemplate" v-if="canBatchImport">下载模板</el-button>
            <el-button type="success" @click="handleImport" v-if="canBatchImport">批量导入</el-button>
            <el-button type="warning" plain @click="downloadAdmissionTemplate" v-if="canImportAdmission">下载录取模板</el-button>
            <el-button type="warning" @click="handleAdmissionImport" v-if="canImportAdmission">导入录取</el-button>
            <el-button type="primary" @click="handleAdd" v-if="canCreateStudent">新增学生</el-button>
          </div>
        </div>
      </template>

      <div class="filter-section">
        <el-cascader
          v-model="filterGradeClass"
          :options="gradeClassOptions"
          placeholder="选择级号/班级"
          clearable
          @change="handleGradeClassChange"
          style="width: 250px"
        />
        <el-select v-model="filterStatus" placeholder="学生状态" clearable @change="fetchStudents" style="width: 120px; margin-left: 10px">
          <el-option label="在校" value="在校" />
          <el-option label="休学" value="休学" />
          <el-option label="转出" value="转出" />
          <el-option label="毕业" value="毕业" />
        </el-select>
        <el-checkbox v-model="showArchivedGrades" @change="handleShowArchivedChange" style="margin-left: 16px">显示毕业年级</el-checkbox>
      </div>

      <el-table :data="studentList" v-loading="loading" stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="gender" label="性别" width="60">
          <template #default="{ row }">
            <el-tag :type="row.gender === '男' ? 'primary' : 'danger'" size="small">{{ row.gender }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="birthday" label="生日" width="120" />
        <el-table-column prop="roomid" label="宿舍" width="80" />
        <el-table-column prop="rpid" label="床号" width="60" />
        <el-table-column prop="class_name" label="班级" width="120" />
        <el-table-column prop="grade_name" label="级号" width="100" />
        <el-table-column prop="middle_school" label="初中毕业学校" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.middle_school || '-' }}
          </template>
        </el-table-column>
        <el-table-column v-if="showAdmissionColumn" prop="entrance_score" label="中考成绩" width="110">
          <template #default="{ row }">
            {{ row.status === '毕业' ? (row.entrance_score || '-') : '-' }}
          </template>
        </el-table-column>
        <el-table-column v-if="showAdmissionColumn" prop="gaokao_score" label="高考成绩" width="110">
          <template #default="{ row }">
            {{ row.status === '毕业' ? (row.gaokao_score || '-') : '-' }}
          </template>
        </el-table-column>
        <el-table-column v-if="showAdmissionColumn" prop="university_name" label="录取院校" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.university_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="入学时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)" v-if="canUpdateStudent && row.can_edit">编辑</el-button>
            <el-button link type="info" @click="handleViewDetail(row)">详情</el-button>
            <el-button link type="warning" @click="handleUpdateStatus(row)" v-if="canUpdateStudent && row.can_update_status">状态</el-button>
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
        <el-form-item label="班级" prop="classSelection">
          <el-cascader
            v-model="form.classSelection"
            :options="gradeClassOptions"
            placeholder="选择班级"
            style="width: 100%"
            :disabled="isEdit && !canChangeClass"
          />
          <span v-if="isEdit && !canChangeClass" class="field-hint">班主任只能编辑本班学生信息，不能修改班级</span>
        </el-form-item>
        <el-form-item label="宿舍">
          <el-input v-model="form.roomid" placeholder="宿舍号（如A101）" maxlength="20" />
        </el-form-item>
        <el-form-item label="床号">
          <el-input v-model="form.rpid" placeholder="床位号（如1）" maxlength="10" />
        </el-form-item>
        <el-form-item label="初中毕业学校">
          <el-input v-model="form.middle_school" placeholder="如：金华四中" maxlength="50" />
        </el-form-item>
        <el-form-item label="中考成绩">
          <el-input v-model="form.entrance_score" placeholder="如：632" maxlength="20" />
        </el-form-item>
        <el-form-item label="高考成绩">
          <el-input v-model="form.gaokao_score" placeholder="如：658" maxlength="20" />
        </el-form-item>
        <template v-if="form.status === '毕业'">
          <el-form-item label="录取院校">
            <el-select
              v-model="form.university_name"
              filterable
              remote
              clearable
              allow-create
              default-first-option
              :remote-method="searchCollegeOptions"
              :loading="collegeSearching"
              placeholder="输入关键词搜索院校，无结果可直接回车填写"
              no-data-text="无匹配院校，可直接输入后回车"
              style="width: 100%"
            >
              <el-option v-for="c in collegeOptions" :key="c.value" :value="c.value" :label="c.label" />
            </el-select>
          </el-form-item>
          <el-form-item label="录取专业">
            <el-select
              v-model="form.university_major"
              filterable
              remote
              clearable
              allow-create
              default-first-option
              :remote-method="searchMajorOptions"
              :loading="majorSearching"
              placeholder="输入关键词搜索专业，无结果可直接回车填写"
              no-data-text="无匹配专业，可直接输入后回车"
              style="width: 100%"
            >
              <el-option v-for="m in majorOptions" :key="m.value" :value="m.value" :label="m.label" />
            </el-select>
          </el-form-item>
        </template>
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
        <el-descriptions-item label="初中毕业学校">{{ currentStudent?.middle_school || '-' }}</el-descriptions-item>
        <template v-if="currentStudent?.status === '毕业'">
          <el-descriptions-item label="中考成绩">{{ currentStudent?.entrance_score || '-' }}</el-descriptions-item>
          <el-descriptions-item label="高考成绩">{{ currentStudent?.gaokao_score || '-' }}</el-descriptions-item>
          <el-descriptions-item label="录取院校">{{ currentStudent?.university_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="录取专业">{{ currentStudent?.university_major || '-' }}</el-descriptions-item>
        </template>
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
            <el-option label="休学" value="休学" />
            <el-option label="转出" value="转出" />
            <el-option label="毕业" value="毕业" />
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
          请上传Excel文件，格式要求：学号、姓名、性别、生日、班级名称、初中毕业学校（选填）、中考成绩（选填）
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

    <!-- 导入录取信息对话框 -->
    <el-dialog v-model="admissionDialogVisible" title="批量导入录取信息" width="500px">
      <el-alert type="info" :closable="false" style="margin-bottom: 20px">
        <template #title>
          请上传Excel文件，格式要求：学号、姓名、录取院校、录取专业（专业可选）。仅支持毕业状态的学生，姓名仅用于核对。
        </template>
      </el-alert>
      <el-upload
        ref="admissionUploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleAdmissionFileChange"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽文件至此处或 <em>点击上传</em></div>
      </el-upload>
      <template #footer>
        <el-button @click="admissionDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdmissionImportSubmit" :loading="admissionLoading">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { getGrades, getClasses, getStudents, createStudent, updateStudent, updateStudentStatus, batchCreateStudents, searchColleges, searchCollegeMajors, batchImportAdmissions } from '@/api/modules/moral'
import ExcelJS from 'exceljs'
import { downloadRowsAsExcel } from '@/utils/filegather'
import { useApiPermission } from '@/composables/useApiPermission'

// API权限检查
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canCreateStudent = ref(false)
const canBatchImport = ref(false)
const canChangeClass = ref(false)  // 是否可以修改学生班级
const canUpdateStudent = ref(false)  // 是否可以编辑学生信息
const canImportAdmission = ref(false)  // 是否可以批量导入录取信息

const loading = ref(false)
const studentList = ref([])
const gradeList = ref([])
const allGradeList = ref([])
const classList = ref([])
const allClassList = ref([])
const showArchivedGrades = ref(false)
const filterGradeClass = ref([])
const filterStatus = ref('在校')

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
  classSelection: [],
  status: '在校',
  middle_school: '',
  entrance_score: '',
  gaokao_score: '',
  university_name: '',
  university_major: ''
})

// 录取院校/专业远程搜索下拉
const collegeOptions = ref([])
const collegeSearching = ref(false)
const majorOptions = ref([])
const majorSearching = ref(false)

const searchCollegeOptions = async (query) => {
  collegeSearching.value = true
  try {
    const res = await searchColleges({ keyword: query || '', limit: 20 })
    if (res.success) {
      collegeOptions.value = (res.data || []).map(c => ({ value: c.school_name, label: c.school_name }))
    }
  } catch (error) {
    console.error('搜索院校失败:', error)
  } finally {
    collegeSearching.value = false
  }
}

const searchMajorOptions = async (query) => {
  majorSearching.value = true
  try {
    const res = await searchCollegeMajors({ keyword: query || '', limit: 20 })
    if (res.success) {
      majorOptions.value = (res.data || []).map(m => ({ value: m.zymc, label: m.zymc }))
    }
  } catch (error) {
    console.error('搜索专业失败:', error)
  } finally {
    majorSearching.value = false
  }
}
const rules = {
  student_id: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  gender: [{ required: true, message: '请选择性别', trigger: 'change' }],
  birthday: [{ required: true, message: '请选择生日', trigger: 'change' }],
  classSelection: [{ required: true, message: '请选择班级', trigger: 'change', type: 'array', min: 2 }]
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
    case '休学': return 'warning'
    case '转出': return 'warning'
    case '毕业': return 'info'
    default: return ''
  }
}

// 当前列表可能包含毕业学生时才显示录取院校列
const showAdmissionColumn = computed(() => {
  if (filterStatus.value === '毕业') return true
  // "显示毕业年级" + 状态筛选为全部时，结果中含毕业学生
  const noStatusFilter = !filterStatus.value || filterStatus.value === ''
  return showArchivedGrades.value && noStatusFilter
})

const applyGradeFilter = () => {
  gradeList.value = allGradeList.value.filter(g => showArchivedGrades.value || !g.is_archived)
}

const fetchGrades = async () => {
  try {
    const res = await getGrades({ include_archived: 1 })
    if (res.success) {
      allGradeList.value = res.data || []
      applyGradeFilter()
    }
  } catch (error) {
    console.error('获取级号列表失败:', error)
  }
}

const applyClassFilter = () => {
  const activeGradeIds = new Set(allGradeList.value.filter(g => !g.is_archived).map(g => g.grade_id))
  classList.value = allClassList.value.filter(c => showArchivedGrades.value || activeGradeIds.has(c.grade_id))
}

const handleShowArchivedChange = () => {
  applyGradeFilter()
  applyClassFilter()
  const visibleGradeIds = new Set(gradeList.value.map(g => g.grade_id))
  if (filterGradeClass.value.length && !visibleGradeIds.has(filterGradeClass.value[0])) {
    filterGradeClass.value = []
  }
  handleGradeClassChange()
}

const fetchAllClasses = async () => {
  try {
    const res = await getClasses({ include_archived: 1 })
    if (res.success) {
      allClassList.value = res.data || []
      applyClassFilter()
    }
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

// 切换级联节点时自动对齐状态筛选：毕业级默认查「毕业」，现役级恢复「在校」
const handleGradeClassChange = () => {
  const grade = allGradeList.value.find(g => g.grade_id === filterGradeClass.value[0])
  if (grade && grade.is_archived) {
    if (filterStatus.value !== '毕业') filterStatus.value = '毕业'
  } else if (filterStatus.value === '毕业') {
    filterStatus.value = '在校'
  }
  handleFilterChange()
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
    classSelection: filterGradeClass.value.length === 2 ? [...filterGradeClass.value] : [],
    status: '在校',
    middle_school: '',
    entrance_score: '',
    gaokao_score: '',
    university_name: '',
    university_major: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  // row 已包含 class_id 和 grade_id（后端返回 s.*）
  Object.assign(form, {
    student_id: row.student_id,
    name: row.name,
    gender: row.gender,
    birthday: row.birthday,
    roomid: row.roomid || '',
    rpid: row.rpid || '',
    classSelection: row.grade_id && row.class_id ? [row.grade_id, row.class_id] : [],
    status: row.status || '在校',
    middle_school: row.middle_school || '',
    // 成绩列是 NUMERIC，后端可能返回数字；转字符串避免提交时类型不符
    entrance_score: row.entrance_score == null ? '' : String(row.entrance_score),
    gaokao_score: row.gaokao_score == null ? '' : String(row.gaokao_score),
    university_name: row.university_name || '',
    university_major: row.university_major || ''
  })
  // 回显已填值，否则远程下拉选中项显示为原始值
  if (form.status === '毕业') {
    if (form.university_name) collegeOptions.value = [{ value: form.university_name, label: form.university_name }]
    if (form.university_major) majorOptions.value = [{ value: form.university_major, label: form.university_major }]
  }
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
      // 档案字段与录取字段一样始终携带（空传 ''），否则后端 is not None 判断会跳过，清空操作失效
      data.middle_school = form.middle_school || ''
      data.entrance_score = form.entrance_score || ''
      data.gaokao_score = form.gaokao_score || ''
      // 录取字段始终携带（空传 ''），否则后端 is not None 判断会跳过，清空操作失效
      if (form.status === '毕业') {
        data.university_name = form.university_name || ''
        data.university_major = form.university_major || ''
      }
      res = await updateStudent(form.student_id, data)
    } else {
      // 新增时也始终携带，后端对空串跳过写入
      res = await createStudent({
        ...data,
        middle_school: form.middle_school || '',
        entrance_score: form.entrance_score || '',
        gaokao_score: form.gaokao_score || '',
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

const getCellValue = (cell) => {
  const value = cell?.value
  if (value == null) return ''
  if (value instanceof Date) return value.toISOString().slice(0, 10)
  if (typeof value === 'object') {
    if (value.text) return value.text
    if (value.result != null) return value.result
    if (Array.isArray(value.richText)) return value.richText.map(part => part.text || '').join('')
    if (value.hyperlink && value.text) return value.text
  }
  return value
}

const normalizeHeader = (value) => String(value || '').trim()

const parseStudentRows = async (file) => {
  const workbook = new ExcelJS.Workbook()
  const data = await file.arrayBuffer()
  await workbook.xlsx.load(data)
  const worksheet = workbook.worksheets[0]
  if (!worksheet) return []

  const headerMap = {}
  worksheet.getRow(1).eachCell((cell, colNumber) => {
    const header = normalizeHeader(getCellValue(cell))
    if (header) headerMap[header] = colNumber
  })

  const valueOf = (row, names) => {
    for (const name of names) {
      const col = headerMap[name]
      if (col) return getCellValue(row.getCell(col))
    }
    return ''
  }

  const rows = []
  worksheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) return
    rows.push({
      student_id: String(valueOf(row, ['学号', 'student_id']) || '').trim(),
      name: String(valueOf(row, ['姓名', 'name']) || '').trim(),
      gender: String(valueOf(row, ['性别', 'gender']) || '男').trim(),
      class_name: String(valueOf(row, ['班级', '班级名称', 'class_name']) || '').trim(),
      birthday: valueOf(row, ['生日', 'birthday']) || null,
      roomid: String(valueOf(row, ['宿舍', 'roomid']) || '').trim(),
      rpid: String(valueOf(row, ['床号', '床位号', 'rpid']) || '').trim(),
      middle_school: String(valueOf(row, ['初中毕业学校', '初中学校', 'middle_school']) || '').trim(),
      entrance_score: valueOf(row, ['中考成绩', 'entrance_score'])
    })
  })

  return rows
}

const handleImportSubmit = async () => {
  if (!importFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  importLoading.value = true
  try {
    const jsonData = await parseStudentRows(importFile.value)

    if (jsonData.length === 0) {
      ElMessage.warning('文件中没有数据')
      importLoading.value = false
      return
    }

    // 转换数据格式
    const students = jsonData.map(row => ({
      student_id: row.student_id,
      name: row.name,
      gender: row.gender || '男',
      class_name: row.class_name,
      birthday: row.birthday,
      roomid: row.roomid || null,
      rpid: row.rpid || null,
      middle_school: row.middle_school || null,
      entrance_score: row.entrance_score === '' || row.entrance_score == null ? null : String(row.entrance_score).trim()
    })).filter(s => s.student_id && s.name && s.class_name)

    if (students.length === 0) {
      ElMessage.warning('没有有效的学生数据，请检查文件格式')
      importLoading.value = false
      return
    }

    // 调用批量导入 API
    const res = await batchCreateStudents({ students })
    if (res.success) {
      const { success_count, update_count, skip_count, error_count, errors } = res.data
      const updatedCount = update_count || skip_count || 0
      let msg = `导入完成：新增 ${success_count} 条，更新 ${updatedCount} 条`
      if (error_count > 0) {
        msg += `，失败 ${error_count} 条`
      }
      ElMessage.success(msg)
      if (errors && errors.length > 0) {
        console.warn('导入错误:', errors)
      }
      importDialogVisible.value = false
      fetchStudents()
    }
  } catch (error) {
    console.error('导入失败:', error)
    ElMessage.error('导入失败，请检查文件格式')
  } finally {
    importLoading.value = false
  }
}

onMounted(async () => {
  await loadMyPermissions()
  canCreateStudent.value = hasApiPermissionSync('/api/moral/admin/students/create')
  canBatchImport.value = hasApiPermissionSync('/api/moral/admin/students/batch')
  canUpdateStudent.value = hasApiPermissionSync('/api/moral/admin/students/update')
  canImportAdmission.value = hasApiPermissionSync('/api/moral/admin/students/admission-batch')
  // 班主任(student_manage_own_class)不能修改班级，只有 student_manage 全权限可以
  canChangeClass.value = hasApiPermissionSync('/api/moral/admin/classes/update')
  // 先加载级号，再按活跃级号过滤班级
  await fetchGrades()
  await fetchAllClasses()
  fetchStudents()
})

// 导出学生数据（支持筛选条件，导出全部数据）
const handleExport = async () => {
  // 构建筛选参数
  const params = { page_size: 10000 }
  if (filterGradeClass.value && filterGradeClass.value.length > 0) {
    if (filterGradeClass.value.length === 1) {
      params.grade_id = filterGradeClass.value[0]
    } else if (filterGradeClass.value.length === 2) {
      params.class_id = filterGradeClass.value[1]
    }
  }
  if (filterStatus.value) {
    params.status = filterStatus.value
  }

  try {
    ElMessage.info('正在导出数据...')
    const res = await getStudents(params)
    if (!res.success || !res.data?.items || res.data.items.length === 0) {
      ElMessage.warning('暂无数据可导出')
      return
    }

    const exportData = res.data.items
    await downloadRowsAsExcel({
      filename: `学生数据_${new Date().toISOString().slice(0, 10)}`,
      sheetName: '学生数据',
      columns: [
        { header: '学号', key: 'student_id', width: 16 },
        { header: '姓名', key: 'name', width: 12 },
        { header: '性别', key: 'gender', width: 8 },
        { header: '生日', key: 'birthday', width: 14 },
        { header: '宿舍', key: 'roomid', width: 14 },
        { header: '床号', key: 'rpid', width: 14 },
        { header: '班级', key: 'class_name', width: 16 },
        { header: '级号', key: 'grade_name', width: 14 },
        { header: '状态', key: 'status', width: 10 },
        { header: '入学时间', key: 'created_at', width: 20 },
        { header: '初中毕业学校', key: 'middle_school', width: 20 },
        { header: '中考成绩', key: 'entrance_score', width: 12 },
        { header: '高考成绩', key: 'gaokao_score', width: 12 },
        { header: '录取院校', key: 'university_name', width: 24 },
        { header: '录取专业', key: 'university_major', width: 20 }
      ],
      rows: exportData.map(row => ({
        ...row,
        gender: row.gender || '',
        birthday: row.birthday || '',
        roomid: row.roomid || '',
        rpid: row.rpid || '',
        class_name: row.class_name || '',
        grade_name: row.grade_name || '',
        status: row.status || '',
        created_at: row.created_at || '',
        middle_school: row.middle_school || '',
        entrance_score: row.entrance_score == null ? '' : String(row.entrance_score),
        gaokao_score: row.gaokao_score == null ? '' : String(row.gaokao_score),
        university_name: row.university_name || '',
        university_major: row.university_major || ''
      }))
    })
    ElMessage.success(`导出成功，共 ${exportData.length} 条记录`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// ==================== 批量导入录取信息 ====================
const admissionDialogVisible = ref(false)
const admissionUploadRef = ref(null)
const admissionFile = ref(null)
const admissionLoading = ref(false)

const handleAdmissionImport = () => {
  admissionFile.value = null
  admissionDialogVisible.value = true
}

const handleAdmissionFileChange = (file) => {
  admissionFile.value = file.raw
}

const parseAdmissionRows = async (file) => {
  const workbook = new ExcelJS.Workbook()
  const data = await file.arrayBuffer()
  await workbook.xlsx.load(data)
  const worksheet = workbook.worksheets[0]
  if (!worksheet) return []

  const headerMap = {}
  worksheet.getRow(1).eachCell((cell, colNumber) => {
    const header = normalizeHeader(getCellValue(cell))
    if (header) headerMap[header] = colNumber
  })

  const valueOf = (row, names) => {
    for (const name of names) {
      const col = headerMap[name]
      if (col) return getCellValue(row.getCell(col))
    }
    return ''
  }

  const rows = []
  worksheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) return
    rows.push({
      student_id: String(valueOf(row, ['学号', 'student_id']) || '').trim(),
      name: String(valueOf(row, ['姓名', 'name']) || '').trim(),
      university_name: String(valueOf(row, ['录取院校', '院校', 'university_name']) || '').trim(),
      university_major: String(valueOf(row, ['录取专业', '专业', 'university_major']) || '').trim()
    })
  })

  return rows
}

const handleAdmissionImportSubmit = async () => {
  if (!admissionFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  admissionLoading.value = true
  try {
    const jsonData = await parseAdmissionRows(admissionFile.value)
    if (jsonData.length === 0) {
      ElMessage.warning('文件中没有数据')
      return
    }

    const students = jsonData
      .filter(s => s.student_id && s.university_name)
      .map(s => ({
        student_id: s.student_id,
        name: s.name || null,
        university_name: s.university_name,
        university_major: s.university_major || null
      }))

    if (students.length === 0) {
      ElMessage.warning('没有有效数据：学号和录取院校为必填项')
      return
    }

    const res = await batchImportAdmissions({ students })
    if (res.success) {
      const { success_count, error_count, errors, not_in_library } = res.data
      // 结果明细（失败原因 / 库外名称核对提示）用弹窗展示，引导人工处理
      const sections = []
      if (error_count > 0 && errors?.length) {
        sections.push(`失败 ${error_count} 条：\n${errors.join('\n')}`)
      }
      const outside = [
        ...(not_in_library?.schools || []).map(n => `院校「${n}」`),
        ...(not_in_library?.majors || []).map(n => `专业「${n}」`)
      ]
      if (outside.length) {
        sections.push(`以下名称不在标准院校库，请核对是否有笔误（确属库外院校可忽略）：\n${outside.join('、')}`)
      }
      if (sections.length) {
        await ElMessageBox.alert(sections.join('\n\n'), `导入完成：成功 ${success_count} 条`, {
          type: error_count > 0 ? 'warning' : 'info',
          confirmButtonText: '知道了'
        })
      } else {
        ElMessage.success(`导入完成：成功 ${success_count} 条`)
      }
      admissionDialogVisible.value = false
      fetchStudents()
    }
  } catch (error) {
    console.error('导入录取信息失败:', error)
    ElMessage.error('导入失败，请检查文件格式')
  } finally {
    admissionLoading.value = false
  }
}

// 下载录取信息导入模板
const downloadAdmissionTemplate = async () => {
  await downloadRowsAsExcel({
    filename: '录取信息导入模板',
    sheetName: '录取信息导入模板',
    columns: [
      { header: '学号', key: 'student_id', width: 16 },
      { header: '姓名', key: 'name', width: 12 },
      { header: '录取院校', key: 'university_name', width: 24 },
      { header: '录取专业', key: 'university_major', width: 20 }
    ],
    rows: [
      { student_id: '20220101', name: '张三', university_name: '浙江大学', university_major: '计算机科学与技术' },
      { student_id: '20220102', name: '李四', university_name: '武汉大学', university_major: '法学' }
    ]
  })
  ElMessage.success('模板下载成功')
}

// 下载导入模板
const downloadTemplate = async () => {
  await downloadRowsAsExcel({
    filename: '学生导入模板',
    sheetName: '学生导入模板',
    columns: [
      { header: '学号', key: 'student_id', width: 16 },
      { header: '姓名', key: 'name', width: 12 },
      { header: '性别', key: 'gender', width: 8 },
      { header: '生日', key: 'birthday', width: 14 },
      { header: '宿舍', key: 'roomid', width: 10 },
      { header: '床号', key: 'rpid', width: 8 },
      { header: '班级', key: 'class_name', width: 16 },
      { header: '初中毕业学校', key: 'middle_school', width: 20 },
      { header: '中考成绩', key: 'entrance_score', width: 10 }
    ],
    rows: [
      { student_id: '20250101', name: '张三', gender: '男', birthday: '2008-05-15', roomid: 'A101', rpid: '1', class_name: '高一1班', middle_school: '育才初级中学', entrance_score: '586.5' },
      { student_id: '20250102', name: '李四', gender: '女', birthday: '2008-03-20', roomid: 'A101', rpid: '2', class_name: '高一1班', middle_school: '实验中学', entrance_score: '602' },
      { student_id: '20250103', name: '王五', gender: '男', birthday: '2008-07-10', roomid: 'B102', rpid: '3', class_name: '高一2班', middle_school: '', entrance_score: '' }
    ]
  })
  ElMessage.success('模板下载成功')
}
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

.field-hint {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}
</style>
