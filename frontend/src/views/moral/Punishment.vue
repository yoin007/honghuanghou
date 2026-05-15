<template>
  <div class="punishment-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" class="filter-form">
        <el-form-item label="学生学号">
          <el-input v-model="filterForm.student_id" placeholder="输入学号" clearable />
        </el-form-item>
        <el-form-item label="班级">
          <el-select v-model="filterForm.class_id" placeholder="选择班级" clearable>
            <el-option
              v-for="cls in classList"
              :key="cls.class_id"
              :label="cls.class_name"
              :value="cls.class_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="处分状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable>
            <el-option label="生效中" :value="1" />
            <el-option label="已撤销" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>处分记录管理</span>
          <div class="header-actions">
            <el-button @click="showExpiringDialog" type="warning" plain>到期提醒</el-button>
            <el-button @click="showPeriodConfig" v-if="canConfigPeriod">期限配置</el-button>
            <el-button @click="handleExport">导出</el-button>
            <el-button type="primary" @click="handleAdd" v-if="canCreatePunishment">新增处分</el-button>
          </div>
        </div>
      </template>

      <el-table :data="recordList" v-loading="loading" stripe>
        <el-table-column prop="student_id" label="学号" width="120" />
        <el-table-column prop="student_name" label="姓名" width="100" />
        <el-table-column prop="class_name" label="班级" width="150" />
        <el-table-column prop="punishment_type" label="处分类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getPunishmentTagType(row.punishment_level)">
              {{ row.punishment_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="punishment_reason" label="处分原因" show-overflow-tooltip />
        <el-table-column prop="score_deduct" label="德育扣分" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="danger" size="small">{{ row.score_deduct }}分</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="punishment_date" label="处分日期" width="120" />
        <el-table-column label="记录人" width="100">
          <template #default="{ row }">
            {{ row.recorder || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="expire_date" label="到期日期" width="120">
          <template #default="{ row }">
            <span v-if="row.expire_date">{{ row.expire_date }}</span>
            <span v-else class="text-muted">未配置</span>
          </template>
        </el-table-column>
        <el-table-column label="到期状态" width="100">
          <template #default="{ row }">
            <template v-if="row.is_revoked === 0 && row.expire_date">
              <el-tag v-if="isExpired(row.expire_date)" type="danger" size="small">已到期</el-tag>
              <el-tag v-else-if="isExpiringSoon(row.expire_date)" type="warning" size="small">即将到期</el-tag>
              <el-tag v-else type="success" size="small">生效中</el-tag>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150">
          <template #default="{ row }">
            <div>
              <el-tag :type="row.review_status === 1 ? 'warning' : (row.is_revoked === 0 ? 'danger' : 'info')">
                {{ row.review_status === 1 ? '待复核' : (row.is_revoked === 0 ? '生效中' : '已撤销') }}
              </el-tag>
              <el-tag v-if="row.is_revoked === 1 && row.revoke_category" type="success" size="small" style="margin-left: 4px">
                {{ row.revoke_type === 1 || row.revoke_type === 3 ? '已归还' : '扣分保留' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="revoke_date" label="撤销日期" width="120" />
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleApplyRevoke(row)" v-if="canApplyRevoke && row.is_revoked === 0 && row.expire_date && isExpired(row.expire_date)">代申请撤销</el-button>
            <el-button link type="warning" @click="handleRevoke(row)" v-if="row.is_revoked === 0 && canRevokePunishment">撤销</el-button>
            <el-button link type="primary" @click="handleReview(row)" v-if="row.review_status === 1 && canRevokePunishment">复核</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchRecords"
        @current-change="fetchRecords"
        class="pagination"
      />
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="recordForm" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="班级" prop="class_id">
          <el-select v-model="recordForm.class_id" placeholder="选择班级" style="width: 100%" @change="handleClassChange" filterable>
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
        <el-form-item label="学生" prop="student_id">
          <el-select
            v-model="recordForm.student_id"
            placeholder="选择学生"
            style="width: 100%"
            filterable
            :disabled="!recordForm.class_id"
          >
            <el-option
              v-for="student in classStudents"
              :key="student.student_id"
              :label="`${student.student_id} - ${student.name}`"
              :value="student.student_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="处分类型" prop="punishment_type">
          <el-select v-model="recordForm.punishment_type" placeholder="选择处分类型" style="width: 100%" filterable>
            <el-option label="警告" value="警告" />
            <el-option label="严重警告" value="严重警告" />
            <el-option label="记过" value="记过" />
            <el-option label="记大过" value="记大过" />
            <el-option label="留校察看" value="留校察看" />
          </el-select>
        </el-form-item>
        <el-form-item label="处分等级" prop="punishment_level">
          <el-select v-model="recordForm.punishment_level" placeholder="选择等级" style="width: 100%">
            <el-option label="一级（轻微）" :value="1" />
            <el-option label="二级（一般）" :value="2" />
            <el-option label="三级（严重）" :value="3" />
            <el-option label="四级（重大）" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="处分日期" prop="punishment_date">
          <el-date-picker
            v-model="recordForm.punishment_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="处分原因" prop="punishment_reason">
          <el-input v-model="recordForm.punishment_reason" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="证明材料">
          <el-input v-model="recordForm.evidence" placeholder="相关证明材料链接" />
        </el-form-item>
        <el-form-item label="德育扣分">
          <el-input-number v-model="recordForm.score_deduct" :min="-100" :max="-1" />
          <span class="score-hint">处分将扣除德育分</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 撤销对话框 -->
    <el-dialog v-model="revokeDialogVisible" title="撤销处分" width="500px">
      <el-form :model="revokeForm" ref="revokeFormRef" label-width="100px">
        <el-form-item label="处分信息">
          <div class="punishment-info">
            <p><strong>学生：</strong>{{ revokeForm.student_name }}</p>
            <p><strong>处分类型：</strong>{{ revokeForm.punishment_type }}</p>
            <p><strong>处分日期：</strong>{{ revokeForm.punishment_date }}</p>
          </div>
        </el-form-item>
        <el-form-item label="撤销类型" prop="revoke_type">
          <el-radio-group v-model="revokeForm.revoke_type">
            <el-radio :value="2">期满申请撤销（扣分保留）</el-radio>
            <el-radio :value="1">误处分撤销（扣分归还）</el-radio>
          </el-radio-group>
          <div class="hint" style="margin-top: 8px">
            {{ revokeForm.revoke_type === 2 ? '处分有效，因表现良好申请撤销，扣分保留' : '处分本身有误（如记录错误），扣分归还' }}
          </div>
        </el-form-item>
        <el-form-item label="撤销日期" prop="revoke_date">
          <el-date-picker
            v-model="revokeForm.revoke_date"
            type="date"
            placeholder="选择撤销日期"
            style="width: 100%"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="撤销原因" prop="revoke_reason">
          <el-input v-model="revokeForm.revoke_reason" type="textarea" :rows="3" placeholder="请填写撤销原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="revokeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRevokeSubmit">确定撤销</el-button>
      </template>
    </el-dialog>

    <!-- 复核对话框 -->
    <el-dialog v-model="reviewDialogVisible" title="处分复核" width="600px">
      <el-descriptions :column="1" border v-loading="reviewLoading">
        <el-descriptions-item label="学生">{{ reviewInfo.student_name }}（{{ reviewInfo.student_id }}）</el-descriptions-item>
        <el-descriptions-item label="事件">{{ reviewInfo.event_name }}</el-descriptions-item>
        <el-descriptions-item label="扣分">{{ reviewInfo.score_deduct }}分</el-descriptions-item>
        <el-descriptions-item label="处分等级">{{ reviewInfo.level || '无' }}</el-descriptions-item>
        <el-descriptions-item label="触发条件">累计 {{ reviewInfo.threshold }} 次（时间窗口 {{ reviewInfo.time_window_days }} 天）</el-descriptions-item>
        <el-descriptions-item label="当前有效次数">{{ reviewInfo.valid_count }} 次</el-descriptions-item>
      </el-descriptions>

      <el-divider content-position="left">源记录状态</el-divider>
      <el-table :data="reviewInfo.source_records" size="small" border v-if="reviewInfo.source_records?.length">
        <el-table-column prop="record_id" label="记录ID" width="100" />
        <el-table-column prop="record_date" label="记录日期" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_deleted === 0 ? 'success' : 'danger'" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="无源记录信息" :image-size="60" />

      <el-divider />
      <el-alert :title="`推荐操作：${reviewInfo.recommendation}`" type="warning" :closable="false" show-icon style="margin-bottom: 15px" />
      <el-alert title="撤销处分将归还扣分，复核通过则扣分保留" type="info" :closable="false" show-icon style="margin-bottom: 15px" />

      <el-form-item label="复核说明">
        <el-input v-model="reviewReason" type="textarea" :rows="2" placeholder="可选填写复核说明" />
      </el-form-item>

      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="handleReviewRevoke">撤销处分（归还扣分）</el-button>
        <el-button type="success" @click="handleReviewApprove">复核通过（扣分保留）</el-button>
      </template>
    </el-dialog>

    <!-- 代申请撤销对话框 -->
    <el-dialog v-model="applyRevokeDialogVisible" title="代学生申请撤销处分" width="500px">
      <el-form :model="applyRevokeForm" ref="applyRevokeFormRef" label-width="100px">
        <el-form-item label="处分信息">
          <div class="punishment-info">
            <p><strong>学生：</strong>{{ applyRevokeForm.student_name }}</p>
            <p><strong>处分类型：</strong>{{ applyRevokeForm.punishment_type }}</p>
            <p><strong>处分日期：</strong>{{ applyRevokeForm.punishment_date }}</p>
            <p><strong>到期日期：</strong>{{ applyRevokeForm.expire_date }}</p>
          </div>
        </el-form-item>
        <el-form-item label="申请理由" prop="apply_reason">
          <el-input v-model="applyRevokeForm.apply_reason" type="textarea" :rows="3" placeholder="请填写申请理由，如观察期表现良好等" />
        </el-form-item>
        <el-form-item label="观察期表现">
          <el-input v-model="applyRevokeForm.observation_proof" type="textarea" :rows="2" placeholder="描述观察期内的良好表现" />
        </el-form-item>
        <el-form-item label="良好记录数">
          <el-input-number v-model="applyRevokeForm.good_record_count" :min="0" :max="100" />
          <span class="hint" style="margin-left: 10px; color: #909399">观察期内良好表现记录数</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="applyRevokeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleApplyRevokeSubmit">提交申请</el-button>
      </template>
    </el-dialog>

    <!-- 到期提醒对话框 -->
    <el-dialog v-model="expiringDialogVisible" title="处分到期提醒" width="700px">
      <el-tabs v-model="expiringTab">
        <el-tab-pane label="已到期" name="expired">
          <el-table :data="expiredPunishments" v-loading="expiringLoading" size="small">
            <el-table-column prop="student_name" label="学生" width="100" />
            <el-table-column prop="class_name" label="班级" width="150" />
            <el-table-column prop="punishment_type" label="处分类型" width="100" />
            <el-table-column prop="expire_date" label="到期日期" width="120" />
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="handleQuickApply(row)">代申请</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!expiredPunishments.length && !expiringLoading" description="暂无已到期处分" :image-size="60" />
        </el-tab-pane>
        <el-tab-pane label="即将到期（7天内）" name="expiring">
          <el-table :data="expiringSoonPunishments" v-loading="expiringLoading" size="small">
            <el-table-column prop="student_name" label="学生" width="100" />
            <el-table-column prop="class_name" label="班级" width="150" />
            <el-table-column prop="punishment_type" label="处分类型" width="100" />
            <el-table-column prop="expire_date" label="到期日期" width="120" />
            <el-table-column label="剩余天数" width="80">
              <template #default="{ row }">
                <el-tag :type="getDaysTagType(row.days_until_expire)" size="small">{{ row.days_until_expire }}天</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!expiringSoonPunishments.length && !expiringLoading" description="暂无即将到期处分" :image-size="60" />
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getPunishments,
  createPunishment,
  updatePunishment,
  revokePunishment,
  getPunishmentReviewInfo,
  reviewPunishment,
  getClasses,
  getGrades,
  getStudents,
  getExpiringPunishments,
  createRevokeApplication,
  getPunishmentPeriods
} from '@/api/modules/moral'
import { getGMT8DateString } from '@/utils/time'
import { useApiPermission } from '@/composables/useApiPermission'
import { useRouter } from 'vue-router'

const router = useRouter()

// API权限
const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canCreatePunishment = ref(false)
const canRevokePunishment = ref(false)
const canApplyRevoke = ref(false)
const canConfigPeriod = ref(false)

// 数据
const loading = ref(false)
const recordList = ref([])
const classList = ref([])
const gradeList = ref([])
const classStudents = ref([])

// 筛选表单
const filterForm = reactive({
  student_id: '',
  class_id: null,
  status: null
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = computed(() => (recordForm.record_id ? '编辑处分' : '新增处分'))
const formRef = ref(null)

// 记录表单
const recordForm = reactive({
  record_id: null,
  class_id: null,
  student_id: '',
  punishment_type: '',
  punishment_level: 2,
  punishment_date: '',
  punishment_reason: '',
  evidence: '',
  score_deduct: -10
})

// 表单校验规则
const rules = {
  class_id: [{ required: true, message: '请选择班级', trigger: 'change' }],
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  punishment_type: [{ required: true, message: '请选择处分类型', trigger: 'change' }],
  punishment_level: [{ required: true, message: '请选择处分等级', trigger: 'change' }],
  punishment_date: [{ required: true, message: '请选择处分日期', trigger: 'change' }],
  punishment_reason: [{ required: true, message: '请输入处分原因', trigger: 'blur' }]
}

// 撤销对话框
const revokeDialogVisible = ref(false)
const revokeFormRef = ref(null)
const revokeForm = reactive({
  record_id: null,
  student_name: '',
  punishment_type: '',
  punishment_date: '',
  revoke_date: '',
  revoke_reason: '',
  revoke_type: 2  // 默认期满申请撤销
})

// 复核对话框
const reviewDialogVisible = ref(false)
const reviewLoading = ref(false)
const reviewReason = ref('')
const reviewInfo = reactive({
  punishment_id: null,
  student_id: '',
  student_name: '',
  event_name: '',
  score_deduct: 0,
  level: '',
  reason: '',
  threshold: 0,
  time_window_days: 90,
  valid_count: 0,
  source_records: [],
  recommendation: ''
})

// 代申请撤销对话框
const applyRevokeDialogVisible = ref(false)
const applyRevokeFormRef = ref(null)
const applyRevokeForm = reactive({
  punishment_id: null,
  student_id: '',
  student_name: '',
  punishment_type: '',
  punishment_date: '',
  expire_date: '',
  apply_reason: '',
  observation_proof: '',
  good_record_count: 0
})

// 到期提醒对话框
const expiringDialogVisible = ref(false)
const expiringTab = ref('expired')
const expiringLoading = ref(false)
const expiredPunishments = ref([])
const expiringSoonPunishments = ref([])

// 辅助函数：判断是否已到期
const isExpired = (expireDate) => {
  if (!expireDate) return false
  const today = new Date().toISOString().slice(0, 10)
  return expireDate <= today
}

// 辅助函数：判断是否即将到期（7天内）
const isExpiringSoon = (expireDate) => {
  if (!expireDate) return false
  const today = new Date()
  const expire = new Date(expireDate)
  const diffDays = Math.ceil((expire - today) / (1000 * 60 * 60 * 24))
  return diffDays > 0 && diffDays <= 7
}

// 辅助函数：获取剩余天数标签类型
const getDaysTagType = (days) => {
  if (days <= 1) return 'danger'
  if (days <= 3) return 'warning'
  return 'info'
}

// 方法
const getPunishmentTagType = (level) => {
  const types = {
    1: 'info',
    2: 'warning',
    3: 'danger',
    4: 'danger'
  }
  return types[level] || 'warning'
}

const fetchRecords = async () => {
  loading.value = true
  try {
    const params = {
      ...filterForm,
      page: pagination.page,
      page_size: pagination.pageSize
    }
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null) {
        delete params[key]
      }
    })

    const res = await getPunishments(params)
    if (res.success) {
      recordList.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error('获取记录失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchClassList = async () => {
  try {
    const res = await getClasses({ for_record_input: 1 })
    if (res.success) {
      classList.value = res.data
    }
  } catch (error) {
    console.error('获取班级列表失败:', error)
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

const handleClassChange = async (classId) => {
  recordForm.student_id = ''
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

const handleSearch = () => {
  pagination.page = 1
  fetchRecords()
}

const handleReset = () => {
  filterForm.student_id = ''
  filterForm.class_id = null
  filterForm.status = null
  handleSearch()
}

const handleAdd = () => {
  Object.assign(recordForm, {
    record_id: null,
    class_id: null,
    student_id: '',
    punishment_type: '',
    punishment_level: 2,
    punishment_date: getGMT8DateString(), // 东八区当前日期
    punishment_reason: '',
    evidence: '',
    score_deduct: -10
  })
  classStudents.value = []
  dialogVisible.value = true
}

const handleEdit = async (row) => {
  // 获取学生所属班级
  const studentClass = classList.value.find(c => c.class_name === row.class_name)
  const classId = studentClass?.class_id

  // 加载该班级的学生列表
  if (classId) {
    try {
      const res = await getStudents({ class_id: classId, page_size: 100 })
      if (res.success) {
        classStudents.value = res.data.items || res.data || []
      }
    } catch (error) {
      console.error('获取班级学生失败:', error)
    }
  }

  Object.assign(recordForm, {
    record_id: row.record_id,
    class_id: classId,
    student_id: row.student_id,
    punishment_type: row.punishment_type,
    punishment_level: row.punishment_level,
    punishment_date: row.punishment_date,
    punishment_reason: row.punishment_reason,
    evidence: row.evidence,
    score_deduct: row.score_deduct
  })
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该处分记录吗？', '提示', {
      type: 'warning'
    })
    const res = await updatePunishment(row.record_id, { status: 0 })
    if (res.success) {
      ElMessage.success('删除成功')
      fetchRecords()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    const api = recordForm.record_id
      ? updatePunishment(recordForm.record_id, recordForm)
      : createPunishment(recordForm)

    const res = await api
    if (res.success) {
      ElMessage.success(recordForm.record_id ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    console.error('提交失败:', error)
  }
}

const handleRevoke = (row) => {
  Object.assign(revokeForm, {
    record_id: row.record_id,
    student_name: row.student_name,
    punishment_type: row.punishment_type,
    punishment_date: row.punishment_date,
    revoke_date: getGMT8DateString(),
    revoke_reason: '',
    revoke_type: 2  // 默认期满申请撤销
  })
  revokeDialogVisible.value = true
}

const handleRevokeSubmit = async () => {
  try {
    const res = await revokePunishment(revokeForm.record_id, revokeForm.revoke_reason, revokeForm.revoke_type)
    if (res.success) {
      const msg = res.score_returned
        ? `撤销成功（扣分已归还 +${Math.abs(res.score_deduct || 0)}分）`
        : '撤销成功（扣分保留）'
      ElMessage.success(msg)
      revokeDialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    console.error('撤销失败:', error)
  }
}

// 复核处分
const handleReview = async (row) => {
  reviewLoading.value = true
  reviewDialogVisible.value = true
  reviewReason.value = ''

  try {
    const res = await getPunishmentReviewInfo(row.record_id)
    if (res.success) {
      Object.assign(reviewInfo, res.data)
    }
  } catch (error) {
    ElMessage.error('获取复核信息失败')
    reviewDialogVisible.value = false
  } finally {
    reviewLoading.value = false
  }
}

// 复核撤销
const handleReviewRevoke = async () => {
  try {
    const res = await reviewPunishment(reviewInfo.punishment_id, 'revoke', reviewReason.value)
    if (res.success) {
      ElMessage.success('处分已撤销，扣分已回滚')
      reviewDialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    ElMessage.error('撤销失败')
  }
}

// 复核通过
const handleReviewApprove = async () => {
  try {
    const res = await reviewPunishment(reviewInfo.punishment_id, 'approve', reviewReason.value)
    if (res.success) {
      ElMessage.success('复核通过，处分保持有效')
      reviewDialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 代申请撤销
const handleApplyRevoke = (row) => {
  Object.assign(applyRevokeForm, {
    punishment_id: row.record_id,
    student_id: row.student_id,
    student_name: row.student_name,
    punishment_type: row.punishment_type,
    punishment_date: row.punishment_date,
    expire_date: row.expire_date,
    apply_reason: '',
    observation_proof: '',
    good_record_count: 0
  })
  applyRevokeDialogVisible.value = true
}

// 提交代申请撤销
const handleApplyRevokeSubmit = async () => {
  try {
    const res = await createRevokeApplication({
      punishment_id: applyRevokeForm.punishment_id,
      student_id: applyRevokeForm.student_id,
      apply_reason: applyRevokeForm.apply_reason,
      observation_proof: applyRevokeForm.observation_proof,
      good_record_count: applyRevokeForm.good_record_count
    })
    if (res.success) {
      ElMessage.success('申请已提交，等待管理员审批')
      applyRevokeDialogVisible.value = false
      fetchRecords()
    }
  } catch (error) {
    ElMessage.error('提交申请失败')
  }
}

// 显示到期提醒对话框
const showExpiringDialog = async () => {
  expiringDialogVisible.value = true
  expiringLoading.value = true
  try {
    const res = await getExpiringPunishments({ days: 7 })
    if (res.success) {
      expiredPunishments.value = res.data.already_expired || []
      expiringSoonPunishments.value = res.data.expiring_soon || []
    }
  } catch (error) {
    ElMessage.error('获取到期提醒失败')
  } finally {
    expiringLoading.value = false
  }
}

// 快速代申请（从到期提醒对话框）
const handleQuickApply = (row) => {
  expiringDialogVisible.value = false
  handleApplyRevoke(row)
}

// 显示期限配置页面
const showPeriodConfig = () => {
  router.push('/moral/config/punishment-period')
}

// 导出处分记录（支持筛选条件，导出全部数据）
const handleExport = async () => {
  const params = { ...filterForm, page_size: 10000 }
  Object.keys(params).forEach(key => {
    if (params[key] === '' || params[key] === null) {
      delete params[key]
    }
  })

  try {
    ElMessage.info('正在导出数据...')
    const res = await getPunishments(params)
    if (!res.success || !res.data.items || res.data.items.length === 0) {
      ElMessage.warning('暂无数据可导出')
      return
    }

    const exportData = res.data.items
    let csvContent = '学号,姓名,班级,处分类型,处分原因,处分日期,状态,撤销日期,德育扣分\n'
    exportData.forEach(row => {
      csvContent += `${row.student_id},${row.student_name},${row.class_name},${row.punishment_type},${row.punishment_reason},${row.punishment_date},${row.status === 1 ? '生效中' : '已撤销'},${row.revoke_date || ''},${row.score_deduct || ''}\n`
    })

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `处分记录_${new Date().toISOString().slice(0,10)}.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success(`导出成功，共 ${exportData.length} 条记录`)
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 生命周期
onMounted(async () => {
  await loadMyPermissions()
  canCreatePunishment.value = hasApiPermissionSync('/api/moral/punishments/create')
  canRevokePunishment.value = hasApiPermissionSync('/api/moral/punishments/revoke')
  canApplyRevoke.value = hasApiPermissionSync('/api/moral/punishment-revoke-applications/create')
  canConfigPeriod.value = hasApiPermissionSync('/api/moral/punishment-periods')
  fetchGradeList()
  fetchClassList()
  fetchRecords()
})
</script>

<style scoped>
.punishment-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.punishment-info {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.punishment-info p {
  margin: 5px 0;
}

.score-hint {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.text-muted {
  color: #909399;
}

.hint {
  color: #909399;
  font-size: 12px;
}
</style>