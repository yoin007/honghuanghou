<template>
  <div class="requirement-center">
    <el-tabs v-model="activeTab">
      <!-- 功能大厅 -->
      <el-tab-pane label="功能大厅" name="catalog">
        <div class="catalog-header">
          <span class="catalog-tip">系统已有 {{ totalFeatures }} 个功能，看看你要的是不是已经有了？</span>
          <el-button type="primary" @click="openSubmitDialog">我要提需求</el-button>
        </div>
        <el-collapse v-model="openGroups">
          <el-collapse-item v-for="group in featureGroups" :key="group.key" :name="group.key">
            <template #title>
              <span class="group-title">{{ group.name }}</span>
              <span class="group-count">（{{ group.features.length }} 个）</span>
            </template>
            <div class="feature-grid">
              <div v-for="f in group.features" :key="f.name" class="feature-card">
                <div class="feature-name">{{ f.name }}</div>
                <div class="feature-desc">{{ f.desc }}</div>
                <el-tag size="small" type="info" class="feature-audience">{{ f.audience }}</el-tag>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
        <div class="catalog-footer">清单更新日期：{{ catalogUpdated }}。没有找到想要的？点右上角「我要提需求」。</div>
      </el-tab-pane>

      <!-- 需求列表 -->
      <el-tab-pane :label="isManager ? '全部需求' : '我的需求'" name="list">
        <div class="list-header">
          <el-button type="primary" @click="openSubmitDialog">我要提需求</el-button>
        </div>
        <el-table :data="requirements" v-loading="listLoading" @row-click="openDetail" class="req-table">
          <el-table-column prop="requirement_no" label="编号" width="140" />
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small">{{ row.status_label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column v-if="isManager" prop="submitter_name" label="提交人" width="120" />
          <el-table-column prop="updated_at" label="最近更新" width="170" />
        </el-table>
        <el-empty v-if="!listLoading && requirements.length === 0"
                  :description="isManager ? '还没有收到需求' : '你还没有提交过需求，点上方按钮提一个吧'" />
      </el-tab-pane>
    </el-tabs>

    <!-- 提需求弹窗 -->
    <el-dialog v-model="submitVisible" title="我要提需求" width="560px">
      <el-alert type="info" :closable="false" style="margin-bottom: 14px">
        <template #title>用大白话写就行：说清遇到什么问题、希望什么效果，不用想怎么实现。</template>
      </el-alert>
      <el-form ref="submitFormRef" :model="submitForm" :rules="submitRules" label-width="130px">
        <el-form-item label="一句话概括" prop="title">
          <el-input v-model="submitForm.title" maxlength="60" show-word-limit placeholder="例：希望监考安排能按学科筛选通知" />
        </el-form-item>
        <el-form-item label="遇到什么问题" prop="problem">
          <el-input v-model="submitForm.problem" type="textarea" :rows="3" maxlength="2000" show-word-limit
                    placeholder="描述现在遇到的麻烦，最好举个真实例子" />
        </el-form-item>
        <el-form-item label="谁在什么场景遇到" prop="scenario">
          <el-input v-model="submitForm.scenario" type="textarea" :rows="2" maxlength="1000" show-word-limit
                    placeholder="选填。例：每次考试后，教务要逐个通知监考老师" />
        </el-form-item>
        <el-form-item label="希望达到什么效果" prop="expectation">
          <el-input v-model="submitForm.expectation" type="textarea" :rows="3" maxlength="2000" show-word-limit
                    placeholder="描述「用完之后」的样子" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="submitVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">提交</el-button>
      </template>
    </el-dialog>

    <!-- 需求详情抽屉 -->
    <el-drawer v-model="detailVisible" :title="detail?.requirement_no || '需求详情'" size="480px">
      <template v-if="detail">
        <div class="detail-title">{{ detail.title }}</div>
        <el-tag :type="statusTagType(detail.status)" size="small">{{ detail.status_label }}</el-tag>
        <el-descriptions :column="1" border class="detail-desc">
          <el-descriptions-item label="遇到什么问题">{{ detail.problem }}</el-descriptions-item>
          <el-descriptions-item v-if="detail.scenario" label="使用场景">{{ detail.scenario }}</el-descriptions-item>
          <el-descriptions-item label="期望效果">{{ detail.expectation }}</el-descriptions-item>
          <el-descriptions-item label="提交人">{{ detail.submitter_name }}</el-descriptions-item>
          <el-descriptions-item label="提交时间">{{ detail.created_at }}</el-descriptions-item>
        </el-descriptions>

        <!-- 教务/管理员：推进状态 -->
        <div v-if="isManager" class="manage-block">
          <div class="block-title">推进状态</div>
          <el-select v-model="statusForm.status" placeholder="选择新状态" style="width: 180px">
            <el-option v-for="(label, key) in statusOptions" :key="key" :label="label" :value="key" />
          </el-select>
          <el-input v-model="statusForm.note" type="textarea" :rows="2" maxlength="2000"
                    placeholder="处理说明（会记录在时间线里），例：已确认，进入设计" class="manage-note" />
          <el-button type="primary" size="small" @click="handleStatusUpdate" :loading="statusUpdating">更新状态</el-button>
        </div>

        <!-- 补充说明 -->
        <div class="manage-block">
          <div class="block-title">补充说明</div>
          <el-input v-model="commentText" type="textarea" :rows="2" maxlength="2000"
                    placeholder="补充信息或沟通记录" />
          <el-button size="small" @click="handleComment" :loading="commenting" class="manage-note">提交说明</el-button>
        </div>

        <!-- 进展时间线 -->
        <div class="block-title">进展时间线</div>
        <el-timeline v-if="detail.logs && detail.logs.length">
          <el-timeline-item v-for="log in detail.logs" :key="log.created_at + log.action"
                            :timestamp="log.created_at" placement="top">
            <b>{{ log.actor_name }}</b>
            <span class="log-action">{{ actionLabel(log.action) }}</span>
            <div v-if="log.note" class="log-note">{{ log.note }}</div>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无进展记录" :image-size="60" />
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { FEATURE_GROUPS, FEATURE_CATALOG_UPDATED } from '@/data/featureCatalog'
import {
  submitRequirement, listRequirements, getRequirementDetail,
  updateRequirementStatus, addRequirementComment
} from '@/api/modules/requirements'

const authStore = useAuthStore()
const isManager = computed(() => authStore.isAdmin || authStore.isJiaowu)

const activeTab = ref('catalog')
const featureGroups = FEATURE_GROUPS
const catalogUpdated = FEATURE_CATALOG_UPDATED
const totalFeatures = featureGroups.reduce((n, g) => n + g.features.length, 0)
const openGroups = ref(featureGroups.map(g => g.key))

// 需求列表
const requirements = ref([])
const listLoading = ref(false)

const STATUS_OPTIONS = {
  pending: '待澄清', designing: '设计中', reviewing: '待审核',
  developing: '开发中', accepting: '待验收', done: '已上线', deferred: '已搁置'
}
const statusOptions = STATUS_OPTIONS

function statusTagType(status) {
  const map = {
    pending: 'info', designing: 'primary', reviewing: 'warning',
    developing: 'primary', accepting: 'warning', done: 'success', deferred: 'info'
  }
  return map[status] || 'info'
}

function actionLabel(action) {
  const map = { submit: ' 提交了需求', status: ' 更新了状态', comment: ' 留言' }
  return map[action] || ''
}

async function loadList() {
  listLoading.value = true
  try {
    const res = await listRequirements(isManager.value ? 'all' : 'mine')
    requirements.value = res.data || []
  } catch (e) {
    console.error('加载需求列表失败:', e)
  } finally {
    listLoading.value = false
  }
}

// 提需求
const submitVisible = ref(false)
const submitting = ref(false)
const submitFormRef = ref(null)
const submitForm = reactive({ title: '', problem: '', scenario: '', expectation: '' })
const submitRules = {
  title: [{ required: true, message: '请用一句话概括', trigger: 'blur' }],
  problem: [{ required: true, message: '请描述遇到的问题', trigger: 'blur' }],
  expectation: [{ required: true, message: '请描述期望效果', trigger: 'blur' }]
}

function openSubmitDialog() {
  submitForm.title = ''
  submitForm.problem = ''
  submitForm.scenario = ''
  submitForm.expectation = ''
  submitVisible.value = true
}

async function handleSubmit() {
  await submitFormRef.value.validate()
  submitting.value = true
  try {
    const res = await submitRequirement({
      title: submitForm.title,
      problem: submitForm.problem,
      scenario: submitForm.scenario || undefined,
      expectation: submitForm.expectation
    })
    ElMessage.success(`已收到！编号 ${res.data.requirement_no}，可在「${isManager.value ? '全部' : '我的'}需求」查看进度`)
    submitVisible.value = false
    loadList()
  } catch (e) {
    console.error('提交需求失败:', e)
  } finally {
    submitting.value = false
  }
}

// 详情抽屉
const detailVisible = ref(false)
const detail = ref(null)
const statusForm = reactive({ status: '', note: '' })
const statusUpdating = ref(false)
const commentText = ref('')
const commenting = ref(false)

async function openDetail(row) {
  try {
    const res = await getRequirementDetail(row.id)
    detail.value = res.data
    statusForm.status = ''
    statusForm.note = ''
    commentText.value = ''
    detailVisible.value = true
  } catch (e) {
    console.error('加载需求详情失败:', e)
  }
}

async function handleStatusUpdate() {
  if (!statusForm.status) {
    ElMessage.warning('请选择新状态')
    return
  }
  statusUpdating.value = true
  try {
    await updateRequirementStatus(detail.value.id, {
      status: statusForm.status,
      note: statusForm.note || undefined
    })
    ElMessage.success('状态已更新')
    detailVisible.value = false
    loadList()
  } catch (e) {
    console.error('更新状态失败:', e)
  } finally {
    statusUpdating.value = false
  }
}

async function handleComment() {
  if (!commentText.value.trim()) {
    ElMessage.warning('请填写说明内容')
    return
  }
  commenting.value = true
  try {
    await addRequirementComment(detail.value.id, commentText.value)
    ElMessage.success('已提交说明')
    openDetail(detail.value)  // 刷新时间线
  } catch (e) {
    console.error('提交说明失败:', e)
  } finally {
    commenting.value = false
  }
}

onMounted(loadList)
</script>

<style scoped>
.requirement-center {
  padding: 16px;
}
.catalog-header,
.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.catalog-tip {
  color: #64748b;
  font-size: 14px;
}
.group-title {
  font-weight: 600;
}
.group-count {
  color: #94a3b8;
  font-size: 12px;
  margin-left: 6px;
}
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}
.feature-card {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px 12px;
  background: #f8fafc;
}
.feature-name {
  font-weight: 600;
  margin-bottom: 4px;
}
.feature-desc {
  font-size: 13px;
  color: #475569;
  margin-bottom: 8px;
  min-height: 36px;
}
.catalog-footer {
  margin-top: 12px;
  color: #94a3b8;
  font-size: 12px;
  text-align: center;
}
.req-table {
  cursor: pointer;
}
.detail-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 10px;
}
.detail-desc {
  margin: 14px 0;
}
.block-title {
  font-weight: 600;
  margin: 16px 0 8px;
}
.manage-note {
  margin: 8px 0;
}
.log-action {
  color: #64748b;
}
.log-note {
  color: #475569;
  font-size: 13px;
  margin-top: 2px;
  white-space: pre-wrap;
}
</style>
