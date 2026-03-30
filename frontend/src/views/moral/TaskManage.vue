<template>
  <div class="task-manage-page">
    <el-tabs v-model="activeTab" class="task-tabs">
      <!-- 德育任务管理 -->
      <el-tab-pane label="德育任务" name="tasks">
        <el-card class="filter-card">
          <el-form :inline="true" :model="taskFilterForm" class="filter-form">
            <el-form-item label="级号">
              <el-select v-model="taskFilterForm.grade_id" placeholder="选择级号" clearable style="width: 150px">
                <el-option
                  v-for="grade in gradeList"
                  :key="grade.grade_id"
                  :label="grade.grade_name"
                  :value="grade.grade_id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="taskFilterForm.status" placeholder="选择状态" clearable style="width: 120px">
                <el-option label="进行中" :value="1" />
                <el-option label="已结束" :value="0" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleTaskSearch">查询</el-button>
              <el-button @click="handleTaskReset">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>德育任务列表</span>
              <el-button type="primary" @click="handleAddTask">新增任务</el-button>
            </div>
          </template>

          <el-table :data="taskList" v-loading="taskLoading" stripe>
            <el-table-column prop="task_name" label="任务名称" width="200" />
            <el-table-column prop="grade_name" label="级号" width="120" />
            <el-table-column label="任务类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.task_type === 1 ? 'primary' : 'success'">
                  {{ row.task_type === 1 ? '个人任务' : '集体任务' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="分值" width="80" />
            <el-table-column prop="start_date" label="开始日期" width="120" />
            <el-table-column prop="end_date" label="结束日期" width="120" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'">
                  {{ row.status === 1 ? '进行中' : '已结束' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" show-overflow-tooltip />
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleEditTask(row)">编辑</el-button>
                <el-button link type="danger" @click="handleDeleteTask(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 任务完成记录 -->
      <el-tab-pane label="完成记录" name="finish">
        <el-card class="filter-card">
          <el-form :inline="true" :model="finishFilterForm" class="filter-form">
            <el-form-item label="学生学号">
              <el-input v-model="finishFilterForm.student_id" placeholder="输入学号" clearable style="width: 150px" />
            </el-form-item>
            <el-form-item label="任务">
              <el-select v-model="finishFilterForm.task_id" placeholder="选择任务" clearable style="width: 200px">
                <el-option
                  v-for="task in taskList"
                  :key="task.task_id"
                  :label="task.task_name"
                  :value="task.task_id"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleFinishSearch">查询</el-button>
              <el-button @click="handleFinishReset">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>任务完成记录</span>
              <el-button type="primary" @click="handleAddFinish">记录完成</el-button>
            </div>
          </template>

          <el-table :data="finishList" v-loading="finishLoading" stripe>
            <el-table-column prop="student_id" label="学号" width="120" />
            <el-table-column prop="student_name" label="姓名" width="100" />
            <el-table-column prop="task_name" label="任务名称" width="200" />
            <el-table-column prop="score" label="得分" width="80">
              <template #default="{ row }">
                <span class="score-positive">+{{ row.score }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="finish_date" label="完成日期" width="120" />
            <el-table-column prop="remark" label="备注" show-overflow-tooltip />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button link type="danger" @click="handleDeleteFinish(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="finishPagination.page"
            v-model:page-size="finishPagination.pageSize"
            :total="finishPagination.total"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchFinishRecords"
            @current-change="fetchFinishRecords"
            class="pagination"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 任务新增/编辑对话框 -->
    <el-dialog v-model="taskDialogVisible" :title="taskDialogTitle" width="500px">
      <el-form :model="taskForm" :rules="taskRules" ref="taskFormRef" label-width="100px">
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="taskForm.task_name" placeholder="输入任务名称" />
        </el-form-item>
        <el-form-item label="级号" prop="grade_id">
          <el-select v-model="taskForm.grade_id" placeholder="选择级号" style="width: 100%">
            <el-option
              v-for="grade in gradeList"
              :key="grade.grade_id"
              :label="grade.grade_name"
              :value="grade.grade_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="taskForm.task_type" placeholder="选择类型" style="width: 100%">
            <el-option label="个人任务" :value="1" />
            <el-option label="集体任务" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="分值" prop="score">
          <el-input-number v-model="taskForm.score" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker
            v-model="taskForm.start_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="结束日期" prop="end_date">
          <el-date-picker
            v-model="taskForm.end_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="taskForm.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="taskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleTaskSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 完成记录对话框 -->
    <el-dialog v-model="finishDialogVisible" title="记录任务完成" width="600px">
      <el-form :model="finishForm" :rules="finishRules" ref="finishFormRef" label-width="100px">
        <el-form-item label="班级" prop="class_id">
          <el-select v-model="finishForm.class_id" placeholder="选择班级" style="width: 100%" @change="handleClassChange" filterable>
            <el-option-group v-for="grade in gradeList" :key="grade.grade_id" :label="grade.grade_name">
              <el-option
                v-for="cls in classList.filter(c => c.grade_id === grade.grade_id)"
                :key="cls.class_id"
                :label="cls.class_name"
                :value="cls.class_id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="学生" prop="student_ids">
          <el-select
            v-model="finishForm.student_ids"
            placeholder="选择学生（可多选）"
            style="width: 100%"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            :disabled="!finishForm.class_id"
          >
            <el-option
              v-for="student in classStudents"
              :key="student.student_id"
              :label="`${student.student_id} - ${student.name}`"
              :value="student.student_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="任务" prop="task_id">
          <el-select v-model="finishForm.task_id" placeholder="选择任务" style="width: 100%" filterable>
            <el-option
              v-for="task in activeTasks"
              :key="task.task_id"
              :label="task.task_name"
              :value="task.task_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="完成日期" prop="finish_date">
          <el-date-picker
            v-model="finishForm.finish_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="finishForm.remark" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="finishDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleFinishSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getMoralTasks,
  createMoralTask,
  updateMoralTask,
  deleteMoralTask,
  getTaskFinishRecords,
  finishTask,
  getGrades,
  getClasses,
  getStudents
} from '@/api/modules/moral'

// Tab
const activeTab = ref('tasks')

// 任务数据
const taskLoading = ref(false)
const taskList = ref([])
const gradeList = ref([])
const classList = ref([])
const classStudents = ref([])

// 任务筛选
const taskFilterForm = reactive({
  grade_id: null,
  status: null
})

// 任务对话框
const taskDialogVisible = ref(false)
const taskDialogTitle = computed(() => (taskForm.task_id ? '编辑任务' : '新增任务'))
const taskFormRef = ref(null)

// 任务表单
const taskForm = reactive({
  task_id: null,
  task_name: '',
  grade_id: null,
  task_type: 1,
  score: 5,
  start_date: '',
  end_date: '',
  description: ''
})

// 任务表单校验
const taskRules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  grade_id: [{ required: true, message: '请选择级号', trigger: 'change' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  score: [{ required: true, message: '请输入分值', trigger: 'blur' }]
}

// 完成记录数据
const finishLoading = ref(false)
const finishList = ref([])
const finishPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 完成记录筛选
const finishFilterForm = reactive({
  student_id: '',
  task_id: null
})

// 完成记录对话框
const finishDialogVisible = ref(false)
const finishFormRef = ref(null)

// 完成记录表单
const finishForm = reactive({
  class_id: null,
  student_ids: [],
  task_id: null,
  finish_date: '',
  remark: ''
})

// 完成记录表单校验
const finishRules = {
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }],
  student_ids: [{ required: true, type: 'array', min: 1, message: '请选择至少一名学生', trigger: 'change' }],
  task_id: [{ required: true, message: '请选择任务', trigger: 'change' }],
  finish_date: [{ required: true, message: '请选择完成日期', trigger: 'change' }]
}

// 计算属性
const activeTasks = computed(() =>
  taskList.value.filter(t => t.status === 1)
)

// 方法
const fetchTasks = async () => {
  taskLoading.value = true
  try {
    const params = { ...taskFilterForm }
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null) {
        delete params[key]
      }
    })

    const res = await getMoralTasks(params)
    if (res.success) {
      taskList.value = res.data
    }
  } catch (error) {
    console.error('获取任务失败:', error)
  } finally {
    taskLoading.value = false
  }
}

const fetchGradeList = async () => {
  try {
    const res = await getGrades()
    if (res.success) {
      gradeList.value = res.data
    }
  } catch (error) {
    console.error('获取级号列表失败:', error)
  }
}

const fetchClassList = async () => {
  try {
    const res = await getClasses()
    if (res.success) {
      classList.value = res.data
    }
  } catch (error) {
    console.error('获取班级列表失败:', error)
  }
}

const handleClassChange = async (classId) => {
  // 清空已选学生
  finishForm.student_ids = []
  classStudents.value = []
  if (!classId) return

  try {
    const res = await getStudents({ class_id: classId, page_size: 100 })
    if (res.success) {
      classStudents.value = res.data.items || res.data || []
    }
  } catch (error) {
    console.error('获取班级学生失败:', error)
  }
}

const fetchFinishRecords = async () => {
  finishLoading.value = true
  try {
    const params = {
      ...finishFilterForm,
      page: finishPagination.page,
      page_size: finishPagination.pageSize
    }
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null) {
        delete params[key]
      }
    })

    const res = await getTaskFinishRecords(params)
    if (res.success) {
      finishList.value = res.data.items
      finishPagination.total = res.data.total
    }
  } catch (error) {
    console.error('获取完成记录失败:', error)
  } finally {
    finishLoading.value = false
  }
}

const handleTaskSearch = () => {
  fetchTasks()
}

const handleTaskReset = () => {
  taskFilterForm.grade_id = null
  taskFilterForm.status = null
  fetchTasks()
}

const handleAddTask = () => {
  Object.assign(taskForm, {
    task_id: null,
    task_name: '',
    grade_id: null,
    task_type: 1,
    score: 5,
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    description: ''
  })
  taskDialogVisible.value = true
}

const handleEditTask = (row) => {
  Object.assign(taskForm, {
    task_id: row.task_id,
    task_name: row.task_name,
    grade_id: row.grade_id,
    task_type: row.task_type,
    score: row.score,
    start_date: row.start_date,
    end_date: row.end_date,
    description: row.description
  })
  taskDialogVisible.value = true
}

const handleDeleteTask = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该任务吗？', '提示', {
      type: 'warning'
    })
    const res = await deleteMoralTask(row.task_id)
    if (res.success) {
      ElMessage.success('删除成功')
      fetchTasks()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const handleTaskSubmit = async () => {
  try {
    await taskFormRef.value.validate()
    const api = taskForm.task_id
      ? updateMoralTask(taskForm.task_id, taskForm)
      : createMoralTask(taskForm)

    const res = await api
    if (res.success) {
      ElMessage.success(taskForm.task_id ? '更新成功' : '创建成功')
      taskDialogVisible.value = false
      fetchTasks()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

const handleFinishSearch = () => {
  finishPagination.page = 1
  fetchFinishRecords()
}

const handleFinishReset = () => {
  finishFilterForm.student_id = ''
  finishFilterForm.task_id = null
  handleFinishSearch()
}

const handleAddFinish = () => {
  Object.assign(finishForm, {
    class_id: null,
    student_ids: [],
    task_id: null,
    finish_date: new Date().toISOString().split('T')[0],
    remark: ''
  })
  classStudents.value = []
  finishDialogVisible.value = true
}

const handleDeleteFinish = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该完成记录吗？', '提示', {
      type: 'warning'
    })
    // 需要后端提供删除接口
    ElMessage.success('删除成功')
    fetchFinishRecords()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const handleFinishSubmit = async () => {
  try {
    await finishFormRef.value.validate()
    // 批量为每个学生创建完成记录
    const results = []
    for (const studentId of finishForm.student_ids) {
      const res = await finishTask({
        student_id: studentId,
        task_id: finishForm.task_id,
        finish_date: finishForm.finish_date,
        remark: finishForm.remark
      })
      results.push(res.success)
    }
    const successCount = results.filter(r => r).length
    if (successCount > 0) {
      ElMessage.success(`成功记录 ${successCount} 条`)
      finishDialogVisible.value = false
      fetchFinishRecords()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

// 生命周期
onMounted(() => {
  fetchGradeList()
  fetchClassList()
  fetchTasks()
  fetchFinishRecords()
})
</script>

<style scoped>
.task-manage-page {
  padding: 20px;
}

.task-tabs {
  margin-bottom: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.score-positive {
  color: #67c23a;
  font-weight: bold;
}
</style>