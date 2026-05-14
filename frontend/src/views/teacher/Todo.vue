<template>
  <div class="todo-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="视图">
          <el-radio-group v-model="filterForm.view" @change="fetchTodos">
            <el-radio-button label="week">本周</el-radio-button>
            <el-radio-button label="month">本月</el-radio-button>
            <el-radio-button label="year">本年</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="周期">
          <el-button-group>
            <el-button @click="shiftPeriod(-1)">上一{{ viewUnitLabel }}</el-button>
            <el-button @click="goToday">{{ periodLabel }}</el-button>
            <el-button @click="shiftPeriod(1)">下一{{ viewUnitLabel }}</el-button>
          </el-button-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" @change="fetchTodos" style="width: 120px">
            <el-option label="全部" value="all" />
            <el-option label="待完成" value="pending" />
            <el-option label="已完成" value="completed" />
          </el-select>
        </el-form-item>
        <el-form-item label="范围">
          <el-select v-model="filterForm.scope" @change="fetchTodos" style="width: 140px">
            <el-option label="全部可见" value="all_visible" />
            <el-option label="我创建的" value="created" />
            <el-option label="分配给我" value="assigned" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleAdd">新增待办</el-button>
          <el-button @click="goGroups">协作群组</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card" v-loading="loading">
      <template #header>
        <div class="card-header">
          <span>我的待办</span>
          <span class="summary-text">共 {{ totalCount }} 条，已完成 {{ completedCount }} 条</span>
        </div>
      </template>

      <el-empty v-if="todoList.length === 0" description="当前没有待办事项" />
      <div v-else class="todo-list">
        <div v-for="group in groupedTodos" :key="group.date" class="todo-group">
          <div class="group-header">
            <span class="group-date">{{ formatDateLabel(group.date) }}</span>
            <span class="group-count">{{ group.items.length }} 条</span>
          </div>
          <div v-for="todo in group.items" :key="todo.occurrence_id" class="todo-item" :class="{ completed: todo.is_completed }">
            <div class="todo-check">
              <el-checkbox
                :model-value="todo.is_completed"
                @change="handleToggleComplete(todo)"
                :disabled="todo.occurrence_id === null"
              />
            </div>
            <div class="todo-content">
              <div class="todo-title">
                <span>{{ todo.title }}</span>
                <el-tag v-if="todo.todo_type !== 'one_off'" size="small" type="info">
                  {{ todoTypeLabel(todo.todo_type) }}
                </el-tag>
              </div>
              <div class="todo-meta">
                <span v-if="todo.description" class="todo-desc">{{ todo.description }}</span>
                <span class="todo-creator">创建者: {{ todo.creator_name || todo.creator_teacher_id }}</span>
                <span v-if="todo.assignee_names?.length" class="todo-assignees">
                  协作人: {{ todo.assignee_names.join(', ') }}
                </span>
              </div>
            </div>
            <div class="todo-actions">
              <el-button link type="primary" @click="handleEdit(todo)" v-if="canEdit(todo)">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(todo)" v-if="canDelete(todo)">删除</el-button>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="550px">
      <el-form :model="todoForm" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="todoForm.title" placeholder="待办标题" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="todoForm.description" type="textarea" :rows="3" placeholder="详细说明" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="类型" prop="todo_type">
          <el-select v-model="todoForm.todo_type" style="width: 100%">
            <el-option label="一次性" value="one_off" />
            <el-option label="每周" value="weekly" />
            <el-option label="每月" value="monthly" />
            <el-option label="每年" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始日期" prop="start_date">
          <el-date-picker v-model="todoForm.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="提醒时间">
          <el-time-picker v-model="todoForm.time_of_day" format="HH:mm" value-format="HH:mm" placeholder="选择时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束日期" v-if="todoForm.todo_type !== 'one_off'">
          <el-date-picker v-model="todoForm.end_date" type="date" placeholder="可选，留空则长期有效" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>

        <!-- 微信通知设置 -->
        <el-divider content-position="left">通知设置</el-divider>
        <el-form-item label="微信提醒">
          <el-switch v-model="todoForm.wechat_notify_enabled" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="提前提醒" v-if="todoForm.wechat_notify_enabled">
          <el-input-number v-model="todoForm.remind_before_minutes" :min="0" :max="120" :step="5" style="width: 100%" />
          <span style="margin-left: 8px; color: #909399">分钟</span>
        </el-form-item>
        <el-form-item label="通知对象" v-if="todoForm.wechat_notify_enabled">
          <el-checkbox v-model="todoForm.notify_creator" :true-label="1" :false-label="0">通知创建者</el-checkbox>
          <el-checkbox v-model="todoForm.notify_assignees" :true-label="1" :false-label="0">通知协作教师</el-checkbox>
        </el-form-item>

        <!-- 周期规则 -->
        <template v-if="todoForm.todo_type === 'weekly'">
          <el-form-item label="每周重复">
            <el-select v-model="todoForm.recurrence_rule.weekday" placeholder="选择星期" style="width: 100%">
              <el-option label="周一" :value="0" />
              <el-option label="周二" :value="1" />
              <el-option label="周三" :value="2" />
              <el-option label="周四" :value="3" />
              <el-option label="周五" :value="4" />
              <el-option label="周六" :value="5" />
              <el-option label="周日" :value="6" />
            </el-select>
          </el-form-item>
        </template>
        <template v-if="todoForm.todo_type === 'monthly'">
          <el-form-item label="每月重复">
            <el-select v-model="todoForm.recurrence_rule.day_of_month" placeholder="选择日期" style="width: 100%">
              <el-option v-for="d in 31" :key="d" :label="`${d}号`" :value="d" />
            </el-select>
          </el-form-item>
        </template>
        <template v-if="todoForm.todo_type === 'yearly'">
          <el-form-item label="每年重复">
            <el-col :span="11">
              <el-select v-model="todoForm.recurrence_rule.month" placeholder="选择月份">
                <el-option v-for="m in 12" :key="m" :label="`${m}月`" :value="m" />
              </el-select>
            </el-col>
            <el-col :span="2" style="text-align: center">-</el-col>
            <el-col :span="11">
              <el-select v-model="todoForm.recurrence_rule.day" placeholder="选择日期">
                <el-option v-for="d in 31" :key="d" :label="`${d}日`" :value="d" />
              </el-select>
            </el-col>
          </el-form-item>
        </template>

        <el-form-item label="协作群组">
          <el-select v-model="todoForm.assignee_group_ids" multiple filterable placeholder="选择协作群组" style="width: 100%">
            <el-option v-for="g in groupList" :key="g.group_id" :label="`${g.group_name} (${g.members?.length || 0}人)`" :value="g.group_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="协作教师">
          <el-select v-model="todoForm.assignee_teacher_ids" multiple filterable placeholder="选择协作教师" style="width: 100%">
            <el-option v-for="t in teacherList" :key="t.teacher_id || t.username" :label="teacherLabel(t)" :value="t.teacher_id || t.username" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTodos, createTodo, updateTodo, deleteTodo, completeOccurrence, reopenOccurrence, getGroups } from '@/api/modules/teacherTodo'
import { teacherApi } from '@/api/modules/teacher'

const loading = ref(false)
const router = useRouter()
const todoList = ref([])
const totalCount = ref(0)
const completedCount = ref(0)
const teacherList = ref([])
const groupList = ref([])

const filterForm = reactive({
  view: 'week',
  anchor_date: new Date().toISOString().slice(0, 10),
  status: 'all',
  scope: 'all_visible'
})

const dialogVisible = ref(false)
const dialogTitle = ref('新增待办')
const formRef = ref(null)
const editingSeriesId = ref(null)

const todoForm = reactive({
  title: '',
  description: '',
  todo_type: 'one_off',
  start_date: '',
  end_date: '',
  time_of_day: '08:00',
  recurrence_rule: { unit: 'weekly', weekday: null, day_of_month: null, month: null, day: null },
  wechat_notify_enabled: 1,
  remind_before_minutes: 30,
  notify_creator: 1,
  notify_assignees: 1,
  assignee_group_ids: [],
  assignee_teacher_ids: []
})

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  todo_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  start_date: [{ required: true, message: '请选择开始日期', trigger: 'change' }]
}

const viewUnitLabel = computed(() => {
  const labels = { week: '周', month: '月', year: '年' }
  return labels[filterForm.view] || '天'
})

const periodLabel = computed(() => {
  const d = new Date(`${filterForm.anchor_date}T00:00:00`)
  if (filterForm.view === 'year') return `${d.getFullYear()}年`
  if (filterForm.view === 'month') return `${d.getFullYear()}年${d.getMonth() + 1}月`
  const start = new Date(d)
  start.setDate(d.getDate() - d.getDay() + (d.getDay() === 0 ? -6 : 1))
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return `${start.getMonth() + 1}/${start.getDate()}-${end.getMonth() + 1}/${end.getDate()}`
})

// 按日期分组
const groupedTodos = computed(() => {
  const groups = {}
  todoList.value.forEach(todo => {
    // 字段映射：后端返回字段名与前端期望不同
    const mappedTodo = {
      ...todo,
      occurrence_id: todo.id,
      series_id: todo.todo_series_id,
      is_completed: todo.status === 'completed',
      recurrence_rule: todo.recurrence_rule_json ? JSON.parse(todo.recurrence_rule_json) : null,
      assignee_names: todo.assignees?.map(a => a.teacher_name) || [],
      assignee_teacher_ids: todo.assignees?.map(a => a.teacher_id) || []
    }
    const date = todo.occurrence_date || todo.start_date
    if (!groups[date]) groups[date] = []
    groups[date].push(mappedTodo)
  })
  return Object.keys(groups).sort().map(date => ({ date, items: groups[date] }))
})

const todoTypeLabel = (type) => {
  const labels = { one_off: '一次性', weekly: '每周', monthly: '每月', yearly: '每年' }
  return labels[type] || type
}

const formatDateLabel = (date) => {
  const d = new Date(date)
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)
  if (d.toDateString() === today.toDateString()) return '今天'
  if (d.toDateString() === tomorrow.toDateString()) return '明天'
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

const teacherLabel = (teacher) => {
  const name = teacher.username || teacher.name || teacher.teacher_name || teacher.teacher_id
  const subject = teacher.subject ? ` - ${teacher.subject}` : ''
  return `${name}${subject}`
}

const formatDate = (date) => date.toISOString().slice(0, 10)

const shiftPeriod = (step) => {
  const d = new Date(`${filterForm.anchor_date}T00:00:00`)
  if (filterForm.view === 'week') d.setDate(d.getDate() + step * 7)
  if (filterForm.view === 'month') d.setMonth(d.getMonth() + step)
  if (filterForm.view === 'year') d.setFullYear(d.getFullYear() + step)
  filterForm.anchor_date = formatDate(d)
  fetchTodos()
}

const goToday = () => {
  filterForm.anchor_date = formatDate(new Date())
  fetchTodos()
}

const goGroups = () => {
  router.push('/teacher/todo-group')
}

const canEdit = (todo) => todo.is_creator === true || todo.is_creator === 1
const canDelete = (todo) => todo.is_creator === true || todo.is_creator === 1

const fetchTodos = async () => {
  loading.value = true
  try {
    const res = await getTodos(filterForm)
    if (res.success) {
      todoList.value = res.data.items || []
      totalCount.value = res.data.summary?.total || 0
      completedCount.value = res.data.summary?.completed || 0
    }
  } catch (e) {
    ElMessage.error('获取待办列表失败')
  } finally {
    loading.value = false
  }
}

const fetchTeachers = async () => {
  try {
    const res = await teacherApi.getTeachers()
    // httpClient 返回完整 axios response（因后端无 success/code 字段）
    const data = res.data || res
    teacherList.value = data.teachers || []
  } catch (e) {
    console.error('获取教师列表失败:', e)
  }
}

const fetchGroups = async () => {
  try {
    const res = await getGroups()
    if (res.success) {
      groupList.value = res.data.groups || []
    }
  } catch (e) {
    console.error('获取群组列表失败:', e)
  }
}

const handleAdd = () => {
  dialogTitle.value = '新增待办'
  editingSeriesId.value = null
  todoForm.title = ''
  todoForm.description = ''
  todoForm.todo_type = 'one_off'
  todoForm.start_date = new Date().toISOString().slice(0, 10)
  todoForm.end_date = ''
  todoForm.time_of_day = '08:00'
  todoForm.recurrence_rule = { unit: 'weekly', weekday: null, day_of_month: null, month: null, day: null }
  todoForm.wechat_notify_enabled = 1
  todoForm.remind_before_minutes = 30
  todoForm.notify_creator = 1
  todoForm.notify_assignees = 1
  todoForm.assignee_group_ids = []
  todoForm.assignee_teacher_ids = []
  dialogVisible.value = true
}

const handleEdit = (todo) => {
  dialogTitle.value = '编辑待办'
  editingSeriesId.value = todo.series_id
  todoForm.title = todo.title
  todoForm.description = todo.description || ''
  todoForm.todo_type = todo.todo_type
  todoForm.start_date = todo.start_date
  todoForm.end_date = todo.end_date || ''
  todoForm.time_of_day = todo.time_of_day || (todo.scheduled_at ? todo.scheduled_at.slice(11, 16) : '08:00')
  todoForm.wechat_notify_enabled = todo.wechat_notify_enabled ?? 1
  todoForm.remind_before_minutes = todo.remind_before_minutes ?? 30
  todoForm.notify_creator = todo.notify_creator ?? 1
  todoForm.notify_assignees = todo.notify_assignees ?? 1
  todoForm.recurrence_rule = {
    unit: todo.todo_type,
    weekday: null,
    day_of_month: null,
    month: null,
    day: null,
    ...(todo.recurrence_rule || {})
  }
  todoForm.assignee_teacher_ids = todo.assignee_teacher_ids || []
  todoForm.assignee_group_ids = []
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  if (!validateRecurrenceRule()) return

  const data = {
    title: todoForm.title,
    description: todoForm.description,
    todo_type: todoForm.todo_type,
    start_date: todoForm.start_date,
    end_date: todoForm.end_date || null,
    time_of_day: todoForm.time_of_day,
    wechat_notify_enabled: todoForm.wechat_notify_enabled,
    remind_before_minutes: todoForm.remind_before_minutes,
    notify_creator: todoForm.notify_creator,
    notify_assignees: todoForm.notify_assignees,
    assignee_group_ids: todoForm.assignee_group_ids || null,
    assignee_teacher_ids: todoForm.assignee_teacher_ids
  }

  if (todoForm.todo_type !== 'one_off') {
    data.recurrence_rule = { unit: todoForm.todo_type }
    if (todoForm.todo_type === 'weekly') data.recurrence_rule.weekday = todoForm.recurrence_rule.weekday
    if (todoForm.todo_type === 'monthly') data.recurrence_rule.day_of_month = todoForm.recurrence_rule.day_of_month
    if (todoForm.todo_type === 'yearly') {
      data.recurrence_rule.month = todoForm.recurrence_rule.month
      data.recurrence_rule.day = todoForm.recurrence_rule.day
    }
  }

  try {
    if (editingSeriesId.value) {
      await updateTodo(editingSeriesId.value, data)
      ElMessage.success('更新成功')
    } else {
      await createTodo(data)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchTodos()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const validateRecurrenceRule = () => {
  if (todoForm.todo_type === 'weekly' && todoForm.recurrence_rule.weekday === null) {
    ElMessage.warning('请选择每周重复的星期')
    return false
  }
  if (todoForm.todo_type === 'monthly' && !todoForm.recurrence_rule.day_of_month) {
    ElMessage.warning('请选择每月重复的日期')
    return false
  }
  if (todoForm.todo_type === 'yearly' && (!todoForm.recurrence_rule.month || !todoForm.recurrence_rule.day)) {
    ElMessage.warning('请选择每年重复的月份和日期')
    return false
  }
  return true
}

const handleDelete = async (todo) => {
  try {
    await ElMessageBox.confirm('确定删除该待办？删除后所有相关实例都将清除。', '确认删除', { type: 'warning' })
    await deleteTodo(todo.series_id)
    ElMessage.success('删除成功')
    fetchTodos()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const handleToggleComplete = async (todo) => {
  if (!todo.occurrence_id) return
  try {
    if (todo.is_completed) {
      await reopenOccurrence(todo.occurrence_id)
      ElMessage.success('已重开')
    } else {
      await completeOccurrence(todo.occurrence_id, new Date().toISOString().slice(0, 10))
      ElMessage.success('已完成')
    }
    fetchTodos()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  fetchTodos()
  fetchTeachers()
  fetchGroups()
})
</script>

<style scoped>
.todo-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 16px;
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

.todo-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.todo-group {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  overflow: hidden;
}

.group-header {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f5f7fa;
  border-bottom: 1px solid #ebeef5;
}

.group-date {
  font-weight: 500;
  color: #303133;
}

.group-count {
  font-size: 13px;
  color: #909399;
}

.todo-item {
  display: flex;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #ebeef5;
  transition: background 0.2s;
}

.todo-item:last-child {
  border-bottom: none;
}

.todo-item:hover {
  background: #f5f7fa;
}

.todo-item.completed {
  opacity: 0.6;
}

.todo-check {
  margin-right: 16px;
}

.todo-content {
  flex: 1;
}

.todo-title {
  font-size: 15px;
  color: #303133;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.todo-item.completed .todo-title span:first-child {
  color: #909399;
  text-decoration: line-through;
}

.todo-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: #909399;
}

.todo-desc {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.todo-actions {
  display: flex;
  gap: 8px;
}
</style>
