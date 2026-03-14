<template>
  <div class="class-students-container">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span class="header-title">班级学生名单</span>
          <el-button type="primary" @click="fetchStudents" :loading="loading" circle>
            <el-icon><Refresh /></el-icon>
          </el-button>
        </div>
      </template>
      
      <div v-if="loading && students.length === 0" class="loading-container">
        <el-skeleton :rows="5" animated />
      </div>

      <div v-else-if="students.length === 0" class="empty-container">
        <el-empty description="暂无学生数据" />
      </div>

      <div v-else>
        <el-tabs v-model="activeTab" class="student-tabs">
          <el-tab-pane 
            v-for="tab in studentTabs" 
            :key="tab.name" 
            :label="tab.label" 
            :name="tab.name"
          >
            <div class="students-grid">
              <div 
                v-for="student in tab.students" 
                :key="student.sid" 
                class="student-item"
                :class="getStatusClass(student.status)"
              >
                <div class="student-avatar" :style="{ backgroundColor: getAvatarColor(student.roomid || student.name) }">
                  {{ student.name ? student.name.charAt(0) : '?' }}
                </div>
                <div class="student-info">
                  <span class="student-name">{{ student.name }}</span>
                  <div class="student-room" v-if="student.roomid">
                    <el-icon><House /></el-icon>
                    <span>{{ student.roomid }}<span v-if="student.rpid"> - {{ student.rpid }}号床</span></span>
                  </div>
                  <el-tag :type="getStatusType(student.status)" size="small" effect="light" class="status-tag">
                    {{ student.status }}
                  </el-tag>
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, House } from '@element-plus/icons-vue'
import api from '../utils/api'

const students = ref([])
const loading = ref(false)
const activeTab = ref('all')

const studentTabs = computed(() => {
  const roomMap = {}
  students.value.forEach(s => {
    const room = s.roomid || '未分配'
    if (!roomMap[room]) roomMap[room] = []
    roomMap[room].push(s)
  })
  
  const roomTabs = Object.keys(roomMap).sort().map(room => ({
    label: room + '宿舍',
    name: room,
    students: roomMap[room]
  }))
  
  // 如果全是未分配，或者没有宿舍信息，就不用加后缀了，或者简单处理
  // 这里优化一下显示，如果是 '未分配' 就不加 '宿舍'
  const refinedTabs = roomTabs.map(tab => ({
    ...tab,
    label: tab.name === '未分配' ? '未分配' : tab.name
  }))

  return [
    { label: '全部学生', name: 'all', students: students.value },
    ...refinedTabs
  ]
})

const getStatusType = (status) => {
  const s = typeof status === 'string' ? status : String(status || '')
  if (s.includes('在校')) return 'success'
  if (s.includes('事假')) return 'warning'
  if (s.includes('病假')) return 'danger'
  if (s.includes('请假')) return 'warning'
  if (s.includes('迟到')) return 'danger'
  if (s.includes('早退')) return 'warning'
  if (s.includes('缺勤')) return 'danger'
  return 'info'
}

const getStatusClass = (status) => {
  const s = typeof status === 'string' ? status : String(status || '')
  if (s.includes('在校')) return 'status-school'
  if (s.includes('事假')) return 'status-leave'
  if (s.includes('病假')) return 'status-absent'
  if (s.includes('请假')) return 'status-leave'
  if (s.includes('迟到')) return 'status-late'
  if (s.includes('早退')) return 'status-early'
  if (s.includes('缺勤')) return 'status-absent'
  return ''
}

const getAvatarColor = (name) => {
  if (!name) return '#909399';
  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#8e44ad', '#16a085', '#2c3e50'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

const fetchStudents = async () => {
  loading.value = true
  try {
    const classCode = localStorage.getItem('selectedClassCode')
    if (!classCode) {
      ElMessage.warning('请先选择班级')
      loading.value = false
      return
    }
    // 将 class_code 添加到路径中
    const response = await api.get(`/api/students_status/${classCode}`)
    
    // 兼容不同的返回格式
    if (Array.isArray(response.data)) {
        students.value = response.data
    } else if (response.data && Array.isArray(response.data.students)) {
        students.value = response.data.students
    } else if (response.data && typeof response.data === 'object') {
        // 尝试将对象转换为数组格式（如果后端仍返回对象）
        // 假设对象格式为 { "Name": "Status" }
        students.value = Object.entries(response.data).map(([name, status], index) => ({
            sid: index,
            name,
            status
        }))
    }
  } catch (error) {
    console.error('获取学生名单失败', error)
    // 如果是 404，可能是接口未实现，我们可以展示模拟数据用于演示（如果需要的话，但这里先报错）
    // ElMessage.error('获取学生名单失败')
    
    // 为了防止页面空白，如果是开发环境且接口报错，可以填充一点模拟数据测试 UI
    if (import.meta.env.DEV) {
       console.warn('使用模拟数据用于展示 UI')
       students.value = [
           { sid: 1, name: "张三", status: "在校", roomid: "B101", rpid: 1 }, 
           { sid: 2, name: "李四", status: "请假", roomid: "B101", rpid: 2 }, 
           { sid: 3, name: "王五", status: "缺勤", roomid: "B102", rpid: 1 }, 
           { sid: 4, name: "赵六", status: "在校", roomid: "B102", rpid: 2 }, 
           { sid: 5, name: "钱七", status: "迟到", roomid: "B103", rpid: 1 }
       ]
    } else {
       ElMessage.error('获取学生名单失败')
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStudents()
})
</script>

<style scoped>
.class-students-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .class-students-container {
    padding: 10px;
  }
  
  .header-title {
    font-size: 16px;
  }
  
  .students-grid {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)) !important;
    gap: 10px !important;
  }

  .student-item {
    padding: 12px !important;
  }

  .student-avatar {
    width: 45px !important;
    height: 45px !important;
    font-size: 18px !important;
    margin-bottom: 10px !important;
  }

  .student-name {
    font-size: 14px !important;
  }
  
  .student-room {
    font-size: 12px !important;
  }

  .status-tag {
    transform: scale(0.9);
  }
}

.box-card {
  min-height: 400px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.students-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 20px;
  padding: 10px;
}

.student-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  border-radius: 12px;
  background-color: #ffffff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  border: 1px solid #ebeef5;
  position: relative;
  overflow: hidden;
}

.student-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.student-avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 15px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.student-info {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.student-name {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  transition: color 0.3s;
}

.student-room {
  font-size: 13px;
  color: #909399;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin: 2px 0;
}

.status-tag {
  align-self: center;
  padding: 0 15px;
}

/* 状态相关样式 */
.status-school .student-name { color: #67c23a; }
.status-leave .student-name { color: #e6a23c; }
.status-absent .student-name { color: #f56c6c; }
.status-late .student-name { color: #f56c6c; }
.status-early .student-name { color: #e6a23c; }

/* 添加顶部状态条 */
.student-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background-color: #909399; /* default */
}

.status-school::before { background-color: #67c23a; }
.status-leave::before { background-color: #e6a23c; }
.status-absent::before { background-color: #f56c6c; }
.status-late::before { background-color: #f56c6c; }
.status-early::before { background-color: #e6a23c; }

.loading-container, .empty-container {
  padding: 40px;
  display: flex;
  justify-content: center;
}
</style>
