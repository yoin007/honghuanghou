<template>
  <div class="life-book-page">
    <!-- 筛选区 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="班级">
          <el-select v-model="filterForm.class_id" placeholder="选择班级" clearable filterable style="width: 150px" @change="handleClassChange">
            <el-option v-for="cls in classList" :key="cls.class_id" :label="cls.class_name" :value="cls.class_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生姓名">
          <el-input v-model="filterForm.student_name" placeholder="输入姓名搜索" clearable style="width: 150px" />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filterForm.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="事件类型">
          <el-select v-model="filterForm.event_types" multiple placeholder="全部类型" collapse-tags style="width: 180px">
            <el-option label="点滴记录" value="moment" />
            <el-option label="日常表现" value="daily" />
            <el-option label="校级事件" value="school" />
            <el-option label="处分记录" value="punishment" />
            <el-option label="德育任务" value="task" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-btn">
          <el-button type="primary" @click="handleSearch">搜索学生</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 学生选择 -->
    <el-card v-if="showStudentList" class="student-list-card">
      <el-table :data="studentList" v-loading="studentLoading" stripe>
        <el-table-column prop="student_id" label="学号" min-width="120" />
        <el-table-column prop="name" label="姓名" min-width="100" />
        <el-table-column prop="class_name" label="班级" min-width="120" />
        <el-table-column prop="grade_name" label="级号" min-width="100" />
        <el-table-column label="操作" min-width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="handleSelectStudent(row)">查看档案</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="studentPagination.page"
        v-model:page-size="studentPagination.pageSize"
        :total="studentPagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchStudents"
        @current-change="fetchStudents"
        class="pagination"
      />
    </el-card>

    <!-- 时光轴展示 -->
    <el-card v-if="selectedStudent" class="timeline-card">
      <template #header>
        <div class="card-header">
          <div class="student-info">
            <span class="student-name">{{ selectedStudent.name }}</span>
            <span class="student-meta">{{ selectedStudent.class_name }} | {{ selectedStudent.grade_name }}</span>
          </div>
          <div class="stats-info">
            <el-tag type="primary">点滴 {{ stats.moment_count }}</el-tag>
            <el-tag type="success">日常 {{ stats.daily_count }}</el-tag>
            <el-tag type="warning">校级 {{ stats.school_count }}</el-tag>
            <el-tag type="danger">处分 {{ stats.punishment_count }}</el-tag>
            <el-tag type="info">任务 {{ stats.task_count }}</el-tag>
          </div>
        </div>
      </template>

      <!-- 时光轴 -->
      <div class="timeline-container" v-loading="timelineLoading">
        <div v-if="timeline.length === 0" class="empty-timeline">
          <el-empty description="暂无记录" />
        </div>
        <div v-else class="timeline">
          <div v-for="(item, index) in timeline" :key="index" class="timeline-item">
            <div class="timeline-date">{{ item.date }}</div>
            <div class="timeline-marker" :class="`marker-${item.type}`"></div>
            <div class="timeline-content">
              <div class="content-header">
                <el-tag :type="getTagType(item.type)" size="small">{{ item.source }}</el-tag>
                <span class="content-title">{{ item.title }}</span>
                <span v-if="item.score" :class="item.score > 0 ? 'score-positive' : 'score-negative'" class="score-badge">
                  {{ item.score > 0 ? '+' : '' }}{{ item.score }}
                </span>
              </div>
              <div class="content-body">{{ item.content }}</div>
              <div v-if="item.tags && item.tags.length" class="content-tags">
                <el-tag v-for="tag in item.tags" :key="tag" size="small" effect="plain">{{ tag }}</el-tag>
              </div>
              <div v-if="item.recorder" class="content-meta">记录人: {{ item.recorder }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="back-btn">
        <el-button @click="handleBack">返回学生列表</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const classList = ref([])
const studentList = ref([])
const selectedStudent = ref(null)
const timeline = ref([])
const stats = ref({})
const showStudentList = ref(true)

const studentLoading = ref(false)
const timelineLoading = ref(false)

const filterForm = reactive({
  class_id: null,
  student_name: '',
  date_range: null,
  event_types: []
})

const studentPagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const getTagType = (type) => {
  const map = {
    moment: 'primary',
    daily: 'success',
    school: 'warning',
    punishment: 'danger',
    task: 'info'
  }
  return map[type] || ''
}

const fetchClasses = async () => {
  try {
    const res = await api.get('/api/moral/admin/classes')
    if (res.success) {
      classList.value = res.data
    }
  } catch (error) {
    console.error('获取班级列表失败:', error)
  }
}

const fetchStudents = async () => {
  studentLoading.value = true
  try {
    const params = {
      page: studentPagination.page,
      page_size: studentPagination.pageSize
    }
    if (filterForm.class_id) {
      params.class_id = filterForm.class_id
    }
    if (filterForm.student_name) {
      params.student_name = filterForm.student_name
    }

    const res = await api.get('/api/moral/timeline/search', { params })
    if (res.success) {
      studentList.value = res.data.items
      studentPagination.total = res.data.total
    }
  } catch (error) {
    console.error('获取学生列表失败:', error)
    if (error.response?.status === 403) {
      ElMessage.warning('只能查看本班学生的档案')
    }
  } finally {
    studentLoading.value = false
  }
}

const handleClassChange = () => {
  studentPagination.page = 1
  fetchStudents()
}

const handleSearch = () => {
  studentPagination.page = 1
  fetchStudents()
}

const handleSelectStudent = async (student) => {
  selectedStudent.value = student
  showStudentList.value = false
  timelineLoading.value = true

  try {
    const params = {}
    if (filterForm.date_range) {
      params.start_date = filterForm.date_range[0]
      params.end_date = filterForm.date_range[1]
    }
    if (filterForm.event_types.length) {
      params.event_types = filterForm.event_types.join(',')
    }

    const res = await api.get(`/api/moral/timeline/${student.student_id}`, { params })
    if (res.success) {
      timeline.value = res.data.timeline
      stats.value = res.data.stats
    }
  } catch (error) {
    console.error('获取时光轴失败:', error)
    ElMessage.error('获取学生档案失败')
  } finally {
    timelineLoading.value = false
  }
}

const handleBack = () => {
  selectedStudent.value = null
  showStudentList.value = true
  timeline.value = []
  stats.value = {}
}

onMounted(() => {
  fetchClasses()
  fetchStudents()
})
</script>

<style scoped>
.life-book-page {
  padding: 20px;
  min-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 20px;
  align-items: center;
}

.filter-form .el-form-item {
  margin-right: 0;
  margin-bottom: 0;
}

.search-btn {
  margin-left: auto;
}

.student-list-card {
  margin-bottom: 20px;
  flex: 1;
}

.student-list-card :deep(.el-card__body) {
  display: flex;
  min-height: 0;
  flex-direction: column;
}

.student-list-card .pagination {
  margin-top: 15px;
  justify-content: flex-end;
}

.timeline-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.student-info .student-name {
  font-size: 18px;
  font-weight: bold;
  margin-right: 10px;
}

.student-info .student-meta {
  color: #909399;
  font-size: 14px;
}

.stats-info {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.timeline-container {
  padding: 20px 0;
}

.empty-timeline {
  padding: 40px;
}

.timeline {
  position: relative;
  padding-left: 150px;
}

.timeline-item {
  position: relative;
  padding-bottom: 30px;
  display: flex;
}

.timeline-date {
  position: absolute;
  left: 0;
  width: 120px;
  text-align: right;
  color: #909399;
  font-size: 14px;
  padding-right: 20px;
}

.timeline-marker {
  position: absolute;
  left: 130px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #409eff;
  border: 2px solid #fff;
  box-shadow: 0 0 0 2px #409eff;
}

.marker-moment { background-color: #409eff; box-shadow: 0 0 0 2px #409eff; }
.marker-daily { background-color: #67c23a; box-shadow: 0 0 0 2px #67c23a; }
.marker-school { background-color: #e6a23c; box-shadow: 0 0 0 2px #e6a23c; }
.marker-punishment { background-color: #f56c6c; box-shadow: 0 0 0 2px #f56c6c; }
.marker-task { background-color: #909399; box-shadow: 0 0 0 2px #909399; }

.timeline-content {
  margin-left: 30px;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 8px;
  flex: 1;
  min-width: 0;
}

.content-header {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.content-title {
  font-weight: 500;
}

.score-badge {
  font-size: 14px;
  font-weight: bold;
}

.score-positive { color: #67c23a; }
.score-negative { color: #f56c6c; }

.content-body {
  margin-top: 10px;
  color: #606266;
  line-height: 1.5;
}

.content-tags {
  margin-top: 10px;
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.content-meta {
  margin-top: 8px;
  color: #909399;
  font-size: 12px;
}

.back-btn {
  margin-top: 20px;
  text-align: center;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .life-book-page {
    padding: 10px;
  }

  .filter-card {
    margin-bottom: 15px;
  }

  .filter-form {
    flex-direction: column;
    gap: 10px;
  }

  .filter-form .el-form-item {
    width: 100%;
  }

  .filter-form .el-form-item .el-select,
  .filter-form .el-form-item .el-input,
  .filter-form .el-form-item .el-date-editor {
    width: 100% !important;
  }

  .search-btn {
    margin-left: 0;
    width: 100%;
  }

  .search-btn .el-button {
    width: 100%;
  }

  .student-list-card {
    margin-bottom: 15px;
  }

  .timeline-card .card-header {
    flex-direction: column;
    gap: 10px;
  }

  .stats-info {
    justify-content: center;
  }

  /* 时光轴改为垂直布局 */
  .timeline {
    padding-left: 0;
  }

  .timeline-item {
    flex-direction: column;
    padding-bottom: 20px;
  }

  .timeline-date {
    position: relative;
    left: 0;
    width: 100%;
    text-align: left;
    padding-right: 0;
    padding-bottom: 5px;
    font-size: 13px;
    font-weight: 500;
  }

  .timeline-marker {
    position: relative;
    left: 0;
    margin-bottom: 10px;
  }

  .timeline-content {
    margin-left: 0;
    padding: 12px;
  }

  .content-header {
    flex-wrap: wrap;
  }

  .content-title {
    font-size: 14px;
  }

  .back-btn .el-button {
    width: 100%;
  }
}
</style>
