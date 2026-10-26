<template>
  <div class="mentor-system-page">
    <!-- 数据范围选项卡（谈话记录） -->
    <MoralScopeTabs
      module="mentor_talks"
      @change="handleScopeChange"
      @ready="handleScopeReady"
    />

    <el-tabs v-model="activeTab" class="mentor-tabs">
      <!-- ============ 谈话记录 ============ -->
      <el-tab-pane label="谈话记录" name="talks">
        <el-card class="filter-card">
          <el-form :inline="true" :model="talkFilter">
            <el-form-item label="风险等级">
              <el-select v-model="talkFilter.risk_level" placeholder="全部" clearable style="width: 110px">
                <el-option label="绿" value="green" />
                <el-option label="黄" value="yellow" />
                <el-option label="红" value="red" />
              </el-select>
            </el-form-item>
            <el-form-item label="谈话类别">
              <el-select v-model="talkFilter.talk_category" placeholder="全部" clearable style="width: 130px">
                <el-option v-for="c in talkCategoryOptions" :key="c" :label="c" :value="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="日期范围">
              <el-date-picker
                v-model="talkFilter.date_range"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                style="width: 240px"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="fetchTalks">查询</el-button>
              <el-button @click="resetTalkFilter">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>导师谈话记录</span>
              <div>
                <el-button @click="handleDownloadTalkTemplate" v-if="canCreateTalk">下载导入模板</el-button>
                <el-button @click="talkImportDialogVisible = true" v-if="canCreateTalk">批量导入</el-button>
                <el-button @click="categoryDialogVisible = true" v-if="canManageCategories">类别配置</el-button>
                <el-button type="primary" @click="handleAddTalk" v-if="canCreateTalk">新增记录</el-button>
              </div>
            </div>
          </template>
          <el-table :data="talkList" stripe v-loading="talkLoading">
            <el-table-column prop="talk_date" label="日期" width="110" />
            <el-table-column label="学生" width="130">
              <template #default="{ row }">{{ row.student_name }}（{{ row.student_id }}）</template>
            </el-table-column>
            <el-table-column prop="talk_category" label="类别" width="100" />
            <el-table-column prop="subject" label="主题" min-width="140" show-overflow-tooltip />
            <el-table-column label="风险" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="riskTagType(row.risk_level)" effect="dark" size="small">
                  {{ riskLabel(row.risk_level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="跟进" width="80" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.need_follow_up" type="info" size="small">需跟进</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="next_talk_date" label="下次谈话" width="110" />
            <el-table-column label="升级" width="90" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.escalated" type="danger" size="small">{{ escalateLabel(row.escalate_path) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="mentor_name" label="导师" width="90" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click="handleViewTalk(row)">详情</el-button>
                <el-button link type="primary" v-if="canUpdateTalk && row.can_edit" @click="handleEditTalk(row)">编辑</el-button>
                <el-button link type="danger" v-if="canDeleteTalk && row.can_delete" @click="handleDeleteTalk(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="talkPagination.page"
            v-model:page-size="talkPagination.pageSize"
            :total="talkPagination.total"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="fetchTalks"
            @size-change="fetchTalks"
            style="margin-top: 16px; justify-content: flex-end"
          />
        </el-card>
      </el-tab-pane>

      <!-- ============ 导师名单（仅管理员/年级主任） ============ -->
      <el-tab-pane label="导师名单" name="roster" v-if="canManageRoster">
        <el-card class="filter-card">
          <el-form :inline="true" :model="rosterFilter">
            <el-form-item label="学期">
              <el-select v-model="rosterFilter.semester_id" style="width: 180px" @change="fetchRoster">
                <el-option v-for="s in semesterList" :key="s.semester_id" :label="s.semester_name" :value="s.semester_id" />
              </el-select>
            </el-form-item>
            <el-form-item label="搜索">
              <el-input v-model="rosterFilter.keyword" placeholder="学生/导师姓名" clearable @keyup.enter="fetchRoster" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="fetchRoster">查询</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="table-card">
          <template #header>
            <div class="card-header">
              <span>导师 - 学生名单</span>
              <div v-if="canManageRoster">
                <el-button @click="handleDownloadTemplate">下载模板</el-button>
                <el-button @click="importDialogVisible = true">批量导入</el-button>
                <el-button type="primary" @click="assignDialogVisible = true">分配导师</el-button>
              </div>
            </div>
          </template>
          <el-table :data="rosterList" stripe v-loading="rosterLoading">
            <el-table-column prop="teacher_name" label="导师" width="110" />
            <el-table-column prop="student_id" label="学号" width="120" />
            <el-table-column prop="student_name" label="学生" width="110" />
            <el-table-column prop="class_name" label="班级" width="110" />
            <el-table-column prop="grade_name" label="年级" width="100" />
            <el-table-column prop="assigned_at" label="分配时间" width="170" />
            <el-table-column label="操作" width="100" v-if="canManageRoster">
              <template #default="{ row }">
                <el-popconfirm title="确认删除该分配？" @confirm="handleDeleteRoster(row)">
                  <template #reference>
                    <el-button link type="danger">删除</el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-model:current-page="rosterPagination.page"
            v-model:page-size="rosterPagination.pageSize"
            :total="rosterPagination.total"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @current-change="fetchRoster"
            @size-change="fetchRoster"
            style="margin-top: 16px; justify-content: flex-end"
          />
        </el-card>
      </el-tab-pane>

      <!-- ============ 工作量统计 ============ -->
      <el-tab-pane label="工作量统计" name="stats" v-if="canViewStats">
        <el-card class="filter-card">
          <el-form :inline="true">
            <el-form-item label="学期">
              <el-select v-model="statsSemesterId" style="width: 180px" @change="fetchStats">
                <el-option v-for="s in semesterList" :key="s.semester_id" :label="s.semester_name" :value="s.semester_id" />
              </el-select>
            </el-form-item>
            <el-form-item label="月份">
              <el-date-picker
                v-model="statsMonth"
                type="month"
                placeholder="全部月份"
                value-format="YYYY-MM"
                clearable
                @change="fetchStats"
              />
            </el-form-item>
            <el-form-item>
              <span class="form-hint">不选月份：按整学期累计覆盖率；选择月份：只统计当月谈话。未谈话名单始终按月</span>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card class="table-card">
          <template #header><span>导师谈话覆盖率</span></template>
          <el-table :data="statsList" stripe v-loading="statsLoading">
            <el-table-column prop="teacher_name" label="导师" width="120" />
            <el-table-column prop="assigned_count" label="应谈学生" width="110" align="center" sortable />
            <el-table-column prop="talked_count" label="已谈学生" width="110" align="center" sortable />
            <el-table-column prop="coverage_pct" label="覆盖率" width="200" sortable>
              <template #default="{ row }">
                <el-progress :percentage="row.coverage_pct" :stroke-width="14"
                  :color="row.coverage_pct >= 100 ? '#67c23a' : row.coverage_pct >= 60 ? '#e6a23c' : '#f56c6c'" />
              </template>
            </el-table-column>
            <el-table-column prop="red_count" label="红色风险" width="100" align="center" sortable>
              <template #default="{ row }">
                <el-tag v-if="row.red_count" type="danger" effect="dark" size="small">{{ row.red_count }}</el-tag>
                <span v-else>0</span>
              </template>
            </el-table-column>
            <el-table-column prop="yellow_count" label="黄色风险" width="100" align="center" sortable>
              <template #default="{ row }">
                <el-tag v-if="row.yellow_count" type="warning" effect="dark" size="small">{{ row.yellow_count }}</el-tag>
                <span v-else>0</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card class="table-card" style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>我的导生名单（{{ studentStatusMonth || '当月' }}）</span>
              <el-radio-group v-model="studentStatusFilter" size="small">
                <el-radio-button value="all">全部</el-radio-button>
                <el-radio-button value="talked">已谈</el-radio-button>
                <el-radio-button value="not_talked">未谈</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <el-table :data="filteredStudentStatus" stripe v-loading="studentStatusLoading" max-height="420">
            <el-table-column prop="teacher_name" label="导师" width="110" />
            <el-table-column prop="student_name" label="学生" width="110" />
            <el-table-column prop="student_id" label="学号" width="120" />
            <el-table-column prop="class_name" label="班级" width="110" />
            <el-table-column label="本月状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.talked ? 'success' : 'danger'" size="small">
                  {{ row.talked ? '已谈' : '未谈' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="talked_count" label="本月次数" width="90" align="center" />
            <el-table-column prop="last_talk_date" label="最近谈话" />
          </el-table>
        </el-card>

        <el-card class="table-card" style="margin-top: 16px">
          <template #header>
            <div class="card-header">
              <span>本月未谈话学生（{{ notTalkedMonth || '当月' }}）</span>
              <el-button @click="copyNotTalkedReminder">复制提醒名单</el-button>
            </div>
          </template>
          <el-table :data="notTalkedList" stripe v-loading="notTalkedLoading">
            <el-table-column prop="teacher_name" label="导师" width="110" />
            <el-table-column prop="student_id" label="学号" width="120" />
            <el-table-column prop="student_name" label="学生" width="110" />
            <el-table-column prop="class_name" label="班级" width="110" />
            <el-table-column prop="grade_name" label="年级" />
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- ============ 新增/编辑谈话记录弹窗 ============ -->
    <el-dialog v-model="talkDialogVisible" :title="talkIsEdit ? '编辑谈话记录' : '新增谈话记录'" width="640px">
      <el-form :model="talkForm" :rules="talkRules" ref="talkFormRef" label-width="100px">
        <el-form-item label="学生" prop="student_id">
          <el-select v-model="talkForm.student_id" filterable :disabled="talkIsEdit" style="width: 100%">
            <el-option-group v-for="cls in talkStudentGroups" :key="cls.class_id || cls.label" :label="cls.class_name || cls.label">
              <el-option
                v-for="stu in cls.students"
                :key="stu.student_id"
                :label="`${stu.name} (${stu.student_id})`"
                :value="stu.student_id"
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item label="谈话日期" prop="talk_date">
          <el-date-picker v-model="talkForm.talk_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="谈话类别" prop="talk_category">
          <el-select v-model="talkForm.talk_category" style="width: 100%">
            <el-option v-for="c in talkCategoryOptions" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="主题">
          <el-input v-model="talkForm.subject" placeholder="本次谈话主题" />
        </el-form-item>
        <el-form-item label="地点">
          <el-input v-model="talkForm.location" />
        </el-form-item>
        <el-form-item label="事由">
          <el-input v-model="talkForm.reason" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="学生自述">
          <el-input v-model="talkForm.student_statement" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="谈话纪要" prop="summary">
          <el-input v-model="talkForm.summary" type="textarea" :rows="3" placeholder="必填：记录本次谈话要点" />
        </el-form-item>
        <el-form-item label="导师诊断">
          <el-input v-model="talkForm.diagnosis" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="风险等级" prop="risk_level">
          <el-radio-group v-model="talkForm.risk_level">
            <el-radio-button value="green">绿</el-radio-button>
            <el-radio-button value="yellow">黄</el-radio-button>
            <el-radio-button value="red">红</el-radio-button>
          </el-radio-group>
          <div class="form-hint">红色直接触发德育预警（严重），黄色触发一般预警</div>
        </el-form-item>
        <el-form-item label="继续跟进">
          <el-switch v-model="talkForm.need_follow_up" :active-value="1" :inactive-value="0" />
          <span v-if="talkForm.need_follow_up" class="form-hint" style="margin-left: 8px">已开启：请选择下次谈话时间，将自动创建待办提醒</span>
        </el-form-item>
        <el-form-item v-if="talkForm.need_follow_up" label="下次谈话" prop="next_talk_date">
          <el-date-picker
            ref="nextTalkPickerRef"
            v-model="talkForm.next_talk_date"
            type="date"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            placeholder="选择下次谈话时间"
          />
        </el-form-item>
        <el-form-item label="是否升级">
          <el-switch v-model="talkForm.escalated" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item v-if="talkForm.escalated" label="升级路径" prop="escalate_path">
          <el-select v-model="talkForm.escalate_path" style="width: 100%">
            <el-option label="年级" value="grade" />
            <el-option label="学发" value="xuefa" />
            <el-option label="心理" value="psychology" />
            <el-option label="校领导" value="principal" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="talkDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitTalk" :loading="talkSubmitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- ============ 谈话详情抽屉 ============ -->
    <el-drawer v-model="detailVisible" title="谈话记录详情" size="420px">
      <el-descriptions :column="1" border v-if="detailTalk">
        <el-descriptions-item label="学生">{{ detailTalk.student_name }}（{{ detailTalk.student_id }}）</el-descriptions-item>
        <el-descriptions-item label="日期">{{ detailTalk.talk_date }}</el-descriptions-item>
        <el-descriptions-item label="类别">{{ detailTalk.talk_category }}</el-descriptions-item>
        <el-descriptions-item label="主题">{{ detailTalk.subject || '-' }}</el-descriptions-item>
        <el-descriptions-item label="地点">{{ detailTalk.location || '-' }}</el-descriptions-item>
        <el-descriptions-item label="事由">{{ detailTalk.reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="学生自述">{{ detailTalk.student_statement || '-' }}</el-descriptions-item>
        <el-descriptions-item label="谈话纪要">{{ detailTalk.summary || '-' }}</el-descriptions-item>
        <el-descriptions-item label="导师诊断">{{ detailTalk.diagnosis || '-' }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <el-tag :type="riskTagType(detailTalk.risk_level)" effect="dark" size="small">{{ riskLabel(detailTalk.risk_level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="下次谈话">{{ detailTalk.next_talk_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="升级">
          <template v-if="detailTalk.escalated">{{ escalateLabel(detailTalk.escalate_path) }}</template>
          <template v-else>未升级</template>
        </el-descriptions-item>
        <el-descriptions-item label="导师">{{ detailTalk.mentor_name }}</el-descriptions-item>
      </el-descriptions>
    </el-drawer>

    <!-- ============ 分配导师弹窗 ============ -->
    <el-dialog v-model="assignDialogVisible" title="分配导师" width="520px">
      <el-form :model="assignForm" :rules="assignRules" ref="assignFormRef" label-width="90px">
        <el-form-item label="导师" prop="teacher_id">
          <el-select v-model="assignForm.teacher_id" filterable style="width: 100%">
            <el-option v-for="t in teacherList" :key="t.teacher_id" :label="t.username" :value="t.teacher_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学期">
          <el-select v-model="assignForm.semester_id" style="width: 100%">
            <el-option v-for="s in semesterList" :key="s.semester_id" :label="s.semester_name" :value="s.semester_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生" prop="student_ids">
          <el-select v-model="assignForm.student_ids" filterable multiple style="width: 100%" placeholder="选择学生（可多选）">
            <el-option-group v-for="cls in assignStudentGroups" :key="cls.class_id || cls.label" :label="cls.class_name || cls.label">
              <el-option
                v-for="stu in cls.students"
                :key="stu.student_id"
                :label="`${stu.name} (${stu.student_id})`"
                :value="stu.student_id"
              />
            </el-option-group>
          </el-select>
          <div class="form-hint">学生本学期已有导师时，分配即更换导师</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitAssign" :loading="assignLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- ============ 批量导入弹窗 ============ -->
    <el-dialog v-model="importDialogVisible" title="批量导入导师名单" width="500px">
      <el-alert type="info" :closable="false" style="margin-bottom: 20px">
        <template #title>
          请上传Excel文件，格式要求：教师ID、教师姓名（教师ID选填，填姓名亦可）、学号、学生姓名（选填）。
          学生本学期已有导师时自动更换。
        </template>
      </el-alert>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleImportFileChange"
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

    <!-- ============ 谈话类别配置弹窗 ============ -->
    <el-dialog v-model="categoryDialogVisible" title="谈话类别配置" width="440px">
      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        <template #title>类别用于谈话记录的选项，修改后立即对所有导师生效</template>
      </el-alert>
      <div class="category-tags">
        <el-tag
          v-for="c in talkCategoryOptions"
          :key="c"
          closable
          style="margin: 0 8px 8px 0"
          @close="removeCategory(c)"
        >{{ c }}</el-tag>
      </div>
      <el-input
        v-model="newCategoryInput"
        placeholder="输入新类别名称后回车"
        style="margin-top: 8px"
        @keyup.enter="addCategory"
      >
        <template #append>
          <el-button @click="addCategory">添加</el-button>
        </template>
      </el-input>
      <template #footer>
        <el-button @click="categoryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveCategories" :loading="categorySaveLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- ============ 谈话记录批量导入弹窗 ============ -->
    <el-dialog v-model="talkImportDialogVisible" title="批量导入谈话记录" width="560px">
      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        <template #title>
          只能导入自己导生的谈话记录，非导生该行失败。纪要必填；红/黄风险会触发预警，填写下次谈话时间会自动创建待办。建议先下载模板按格式填写。
        </template>
      </el-alert>
      <el-upload
        ref="talkUploadRef"
        :auto-upload="false"
        :limit="1"
        accept=".xlsx,.xls"
        :on-change="handleTalkImportFileChange"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">拖拽文件至此处或 <em>点击上传</em></div>
      </el-upload>
      <template #footer>
        <el-button @click="talkImportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleTalkImportSubmit" :loading="talkImportLoading">导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import ExcelJS from 'exceljs'
import {
  getMentorTalks, createMentorTalk, updateMentorTalk, deleteMentorTalk,
  getMentorRoster, assignMentor, batchImportMentorRoster, removeMentorAssignment,
  getMentorRosterTemplate, getMentorMyStudents, getMentorTalkStatistics, getMentorNotTalked,
  getClasses, getStudents, getSemesters, getTeachers,
  getMentorTalkCategories, updateMentorTalkCategories, getMentorStudentStatus,
  batchImportMentorTalks, getMentorTalkTemplate,
} from '@/api/modules/moral'
import { getGMT8DateString } from '@/utils/time'
import { useApiPermission } from '@/composables/useApiPermission'
import MoralScopeTabs from '@/components/MoralScopeTabs.vue'

// 谈话类别：后端可人工配置（moral_config），默认五类
const talkCategoryOptions = ref([])
const categoryDialogVisible = ref(false)
const categorySaveLoading = ref(false)
const newCategoryInput = ref('')

const { hasApiPermissionSync, loadMyPermissions } = useApiPermission()
const canCreateTalk = ref(false)
const canUpdateTalk = ref(false)
const canDeleteTalk = ref(false)
const canManageRoster = ref(false)
const canManageCategories = ref(false)
const canViewStats = ref(false)

const activeTab = ref('talks')
const currentScope = ref(null)

// ============ 谈话记录 ============
const talkLoading = ref(false)
const talkList = ref([])
const talkFilter = reactive({
  risk_level: null,
  talk_category: null,
  date_range: null,
})
const talkPagination = reactive({ page: 1, pageSize: 20, total: 0 })

const talkDialogVisible = ref(false)
const talkIsEdit = ref(false)
const talkFormRef = ref(null)
const talkSubmitLoading = ref(false)
const detailVisible = ref(false)
const detailTalk = ref(null)

const talkForm = reactive({
  record_id: null,
  student_id: '',
  talk_date: getGMT8DateString(),
  talk_category: '',
  subject: '',
  location: '',
  reason: '',
  student_statement: '',
  summary: '',
  diagnosis: '',
  risk_level: 'green',
  need_follow_up: 0,
  next_talk_date: null,
  escalated: 0,
  escalate_path: null,
})

const talkRules = {
  student_id: [{ required: true, message: '请选择学生', trigger: 'change' }],
  talk_date: [{ required: true, message: '请选择谈话日期', trigger: 'change' }],
  talk_category: [{ required: true, message: '请选择谈话类别', trigger: 'change' }],
  summary: [{ required: true, message: '请填写谈话纪要', trigger: 'blur' }],
  risk_level: [{ required: true, message: '请选择风险等级', trigger: 'change' }],
}

// 继续跟进开关：开启时自动弹出下次谈话选择，关闭时清空（待办随之停用）
const nextTalkPickerRef = ref(null)
watch(() => talkForm.need_follow_up, (val) => {
  if (val === 1) {
    nextTick(() => {
      nextTalkPickerRef.value?.handleOpen?.()
    })
  } else {
    talkForm.next_talk_date = null
  }
})

const riskLabel = (level) => ({ green: '绿', yellow: '黄', red: '红' }[level] || level)
const riskTagType = (level) => ({ green: 'success', yellow: 'warning', red: 'danger' }[level] || 'info')
const escalateLabel = (path) => ({ grade: '年级', xuefa: '学发', psychology: '心理', principal: '校领导' }[path] || path)

// ============ 谈话记录批量导入 ============
const talkImportDialogVisible = ref(false)
const talkImportLoading = ref(false)
const talkImportFile = ref(null)
const talkUploadRef = ref(null)

const RISK_MAP = { '绿': 'green', '黄': 'yellow', '红': 'red', green: 'green', yellow: 'yellow', red: 'red' }
const ESCALATE_MAP = { '年级': 'grade', '学发': 'xuefa', '心理': 'psychology', '校领导': 'principal',
  grade: 'grade', xuefa: 'xuefa', psychology: 'psychology', principal: 'principal' }

const handleDownloadTalkTemplate = async () => {
  try {
    const res = await getMentorTalkTemplate()
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '导师谈话记录导入模板.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载模板失败')
  }
}

const handleTalkImportFileChange = (file) => {
  talkImportFile.value = file.raw
}

const fmtDate = (v) => {
  if (!v) return ''
  if (v instanceof Date) {
    const y = v.getFullYear(), m = String(v.getMonth() + 1).padStart(2, '0'), d = String(v.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }
  return String(v).trim()
}

const parseTalkRows = async (file) => {
  const buffer = await file.arrayBuffer()
  const workbook = new ExcelJS.Workbook()
  await workbook.xlsx.load(buffer)
  const worksheet = workbook.worksheets[0]
  if (!worksheet) return []

  const headerMap = {}
  worksheet.getRow(1).eachCell((cell, colNumber) => {
    const header = String(cell.value ?? '').trim()
    if (header) headerMap[header] = colNumber
  })
  const valueOf = (row, names) => {
    for (const name of names) {
      const col = headerMap[name]
      if (col) {
        const v = row.getCell(col).value
        if (v && typeof v === 'object' && v.text !== undefined) return String(v.text).trim()
        return v
      }
    }
    return ''
  }

  const yesNo = (v) => (['是', 'y', 'yes', '1', 1, true].includes(String(v).trim().toLowerCase()) ? 1 : 0)

  const rows = []
  worksheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) return
    const studentId = String(valueOf(row, ['学号', 'student_id']) ?? '').replace(/\.0$/, '').trim()
    if (!studentId) return
    rows.push({
      student_id: studentId,
      talk_date: fmtDate(valueOf(row, ['谈话日期', 'talk_date'])),
      talk_category: String(valueOf(row, ['谈话类别', 'talk_category']) ?? '').trim(),
      summary: String(valueOf(row, ['谈话纪要', 'summary']) ?? '').trim(),
      subject: String(valueOf(row, ['主题', 'subject']) ?? '').trim() || undefined,
      location: String(valueOf(row, ['地点', 'location']) ?? '').trim() || undefined,
      reason: String(valueOf(row, ['事由', 'reason']) ?? '').trim() || undefined,
      student_statement: String(valueOf(row, ['学生自述', 'student_statement']) ?? '').trim() || undefined,
      diagnosis: String(valueOf(row, ['导师诊断', 'diagnosis']) ?? '').trim() || undefined,
      risk_level: RISK_MAP[String(valueOf(row, ['风险等级', 'risk_level']) ?? '').trim()] || 'green',
      need_follow_up: yesNo(valueOf(row, ['继续跟进', 'need_follow_up'])),
      next_talk_date: fmtDate(valueOf(row, ['下次谈话时间', 'next_talk_date'])) || undefined,
      escalated: yesNo(valueOf(row, ['是否升级', 'escalated'])),
      escalate_path: ESCALATE_MAP[String(valueOf(row, ['升级路径', 'escalate_path']) ?? '').trim()] || undefined,
    })
  })
  return rows
}

const handleTalkImportSubmit = async () => {
  if (!talkImportFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  talkImportLoading.value = true
  try {
    const items = await parseTalkRows(talkImportFile.value)
    if (items.length === 0) {
      ElMessage.warning('文件中没有数据')
      return
    }
    const res = await batchImportMentorTalks({ items })
    if (res.success) {
      const { success_count, failed_count, errors } = res.data
      if (failed_count > 0 && errors?.length) {
        const detail = errors.map(e => `第${e.row}行（${e.student_id}）：${e.reason}`).join('\n')
        await ElMessageBox.alert(detail, `导入完成：成功 ${success_count} 条，失败 ${failed_count} 条`, {
          type: 'warning',
          confirmButtonText: '知道了',
        })
      } else {
        ElMessage.success(`导入完成：成功 ${success_count} 条`)
      }
      talkImportDialogVisible.value = false
      talkImportFile.value = null
      talkUploadRef.value?.clearFiles()
      fetchTalks()
    }
  } finally {
    talkImportLoading.value = false
  }
}

// ============ 谈话类别配置 ============
const loadTalkCategories = async () => {
  try {
    const res = await getMentorTalkCategories()
    if (res.success) talkCategoryOptions.value = res.data.categories
  } catch (e) {
    console.error('加载谈话类别失败', e)
  }
}

const addCategory = () => {
  const value = newCategoryInput.value.trim()
  if (!value) return
  if (talkCategoryOptions.value.includes(value)) {
    ElMessage.warning('类别已存在')
    return
  }
  talkCategoryOptions.value.push(value)
  newCategoryInput.value = ''
}

const removeCategory = (c) => {
  if (talkCategoryOptions.value.length <= 1) {
    ElMessage.warning('至少保留一个类别')
    return
  }
  talkCategoryOptions.value = talkCategoryOptions.value.filter(item => item !== c)
}

const handleSaveCategories = async () => {
  categorySaveLoading.value = true
  try {
    const res = await updateMentorTalkCategories(talkCategoryOptions.value)
    if (res.success) {
      ElMessage.success('谈话类别已更新')
      categoryDialogVisible.value = false
    }
  } finally {
    categorySaveLoading.value = false
  }
}

// ============ 导生名单（本月已谈/未谈） ============
const studentStatusLoading = ref(false)
const studentStatusList = ref([])
const studentStatusFilter = ref('all')

const studentStatusMonth = computed(() => statsMonth.value)

const filteredStudentStatus = computed(() => {
  if (studentStatusFilter.value === 'talked') {
    return studentStatusList.value.filter(row => row.talked)
  }
  if (studentStatusFilter.value === 'not_talked') {
    return studentStatusList.value.filter(row => !row.talked)
  }
  return studentStatusList.value
})

const fetchStudentStatus = async () => {
  studentStatusLoading.value = true
  try {
    const params = {}
    if (statsSemesterId.value) params.semester_id = statsSemesterId.value
    if (statsMonth.value) params.month = statsMonth.value
    const res = await getMentorStudentStatus(params)
    if (res.success) studentStatusList.value = res.data.items
  } catch (e) {
    console.error('获取导生名单失败', e)
  } finally {
    studentStatusLoading.value = false
  }
}

// ============ 学生选择器 ============
// 谈话表单：严格只显示自己的导生（按教师身份从名单解析，多角色用户天然正确）
const talkStudentGroups = ref([])
// 分配弹窗：需要全校学生可选
const assignStudentGroups = ref([])

const loadTalkStudentOptions = async () => {
  try {
    const res = await getMentorMyStudents()
    const items = res.data?.items || []
    const byClass = {}
    for (const row of items) {
      const key = row.class_id || 0
      if (!byClass[key]) byClass[key] = { class_id: key, class_name: row.class_name || '未分班', students: [] }
      byClass[key].students.push({ student_id: row.student_id, name: row.student_name })
    }
    talkStudentGroups.value = Object.values(byClass)
  } catch (e) {
    console.error('加载导生列表失败', e)
  }
}

const loadAssignStudentOptions = async () => {
  try {
    const [classRes, studentRes] = await Promise.all([
      getClasses({ for_record_input: 1 }),
      getStudents({ page: 1, page_size: 10000, for_record_input: 1 }),
    ])
    const byClass = {}
    for (const stu of studentRes.data?.items || []) {
      if (!byClass[stu.class_id]) byClass[stu.class_id] = []
      byClass[stu.class_id].push(stu)
    }
    assignStudentGroups.value = (classRes.data || []).map(cls => ({
      class_id: cls.class_id,
      class_name: cls.class_name,
      students: byClass[cls.class_id] || [],
    }))
  } catch (e) {
    console.error('加载学生选项失败', e)
  }
}

// ============ 导师名单 ============
const rosterLoading = ref(false)
const rosterList = ref([])
const rosterFilter = reactive({ semester_id: null, keyword: '' })
const rosterPagination = reactive({ page: 1, pageSize: 20, total: 0 })
const semesterList = ref([])
const teacherList = ref([])
const assignDialogVisible = ref(false)
const assignFormRef = ref(null)
const assignLoading = ref(false)
const assignForm = reactive({ teacher_id: '', semester_id: null, student_ids: [] })
const assignRules = {
  teacher_id: [{ required: true, message: '请选择导师', trigger: 'change' }],
  student_ids: [{ required: true, message: '请选择学生', trigger: 'change' }],
}
const importDialogVisible = ref(false)
const importLoading = ref(false)
const importFile = ref(null)
const uploadRef = ref(null)

// ============ 工作量统计 ============
const statsLoading = ref(false)
const statsList = ref([])
const statsSemesterId = ref(null)
const statsMonth = ref(null)
const notTalkedLoading = ref(false)
const notTalkedList = ref([])

const notTalkedMonth = computed(() => statsMonth.value)

const handleScopeChange = (scope) => {
  currentScope.value = scope
  fetchTalks()
}
const handleScopeReady = ({ defaultTab }) => {
  currentScope.value = defaultTab
}

const fetchTalks = async () => {
  talkLoading.value = true
  try {
    const params = {
      page: talkPagination.page,
      page_size: talkPagination.pageSize,
    }
    if (currentScope.value) params.scope = currentScope.value
    if (talkFilter.risk_level) params.risk_level = talkFilter.risk_level
    if (talkFilter.talk_category) params.talk_category = talkFilter.talk_category
    if (talkFilter.date_range?.length === 2) {
      params.start_date = talkFilter.date_range[0]
      params.end_date = talkFilter.date_range[1]
    }
    const res = await getMentorTalks(params)
    if (res.success) {
      talkList.value = res.data.items
      talkPagination.total = res.data.total
    }
  } catch (e) {
    ElMessage.error('获取谈话记录失败')
  } finally {
    talkLoading.value = false
  }
}

const resetTalkFilter = () => {
  talkFilter.risk_level = null
  talkFilter.talk_category = null
  talkFilter.date_range = null
  talkPagination.page = 1
  fetchTalks()
}

const handleAddTalk = () => {
  talkIsEdit.value = false
  resetTalkForm()
  talkDialogVisible.value = true
}

const handleEditTalk = (row) => {
  talkIsEdit.value = true
  Object.assign(talkForm, {
    record_id: row.record_id,
    student_id: row.student_id,
    talk_date: row.talk_date,
    talk_category: row.talk_category,
    subject: row.subject || '',
    location: row.location || '',
    reason: row.reason || '',
    student_statement: row.student_statement || '',
    summary: row.summary || '',
    diagnosis: row.diagnosis || '',
    risk_level: row.risk_level,
    need_follow_up: row.need_follow_up || 0,
    next_talk_date: row.next_talk_date || null,
    escalated: row.escalated || 0,
    escalate_path: row.escalate_path || null,
  })
  talkDialogVisible.value = true
}

const resetTalkForm = () => {
  Object.assign(talkForm, {
    record_id: null,
    student_id: '',
    talk_date: getGMT8DateString(),
    talk_category: '',
    subject: '',
    location: '',
    reason: '',
    student_statement: '',
    summary: '',
    diagnosis: '',
    risk_level: 'green',
    need_follow_up: 0,
    next_talk_date: null,
    escalated: 0,
    escalate_path: null,
  })
}

const handleSubmitTalk = async () => {
  try {
    await talkFormRef.value.validate()
  } catch {
    // 校验失败（如谈话纪要为空）：弹窗提示首个未通过项
    const firstField = Object.keys(talkFormRef.value.fields || {}).length
      ? Object.values(talkFormRef.value.fields).find(f => f.validateState === 'error')
      : null
    ElMessageBox.alert(
      firstField ? `请填写${firstField.label}` : '请检查表单填写',
      '表单未填写完整',
      { type: 'warning', confirmButtonText: '知道了' }
    )
    return
  }
  if (talkForm.escalated && !talkForm.escalate_path) {
    ElMessage.warning('升级时必须选择升级路径')
    return
  }
  talkSubmitLoading.value = true
  try {
    const payload = { ...talkForm }
    delete payload.record_id
    // 可选字段空串归一为 null（后端日期校验不接受 ""）
    for (const k of ['subject', 'location', 'reason', 'student_statement', 'diagnosis', 'escalate_path', 'next_talk_date']) {
      if (payload[k] === '') payload[k] = null
    }
    const res = talkIsEdit.value
      ? await updateMentorTalk(talkForm.record_id, payload)
      : await createMentorTalk(payload)
    if (res.success) {
      ElMessage.success(talkIsEdit.value ? '谈话记录已更新' : '谈话记录已创建')
      talkDialogVisible.value = false
      fetchTalks()
    }
  } finally {
    talkSubmitLoading.value = false
  }
}

const handleDeleteTalk = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该谈话记录？', '提示', { type: 'warning' })
  } catch {
    return
  }
  const res = await deleteMentorTalk(row.record_id)
  if (res.success) {
    ElMessage.success('已删除')
    fetchTalks()
  }
}

const handleViewTalk = (row) => {
  detailTalk.value = row
  detailVisible.value = true
}

// ============ 名单 ============
const fetchRoster = async () => {
  rosterLoading.value = true
  try {
    const params = {
      page: rosterPagination.page,
      page_size: rosterPagination.pageSize,
    }
    if (rosterFilter.semester_id) params.semester_id = rosterFilter.semester_id
    if (rosterFilter.keyword) params.keyword = rosterFilter.keyword
    const res = await getMentorRoster(params)
    if (res.success) {
      rosterList.value = res.data.items
      rosterPagination.total = res.data.total
      if (!rosterFilter.semester_id) rosterFilter.semester_id = res.data.semester_id
    }
  } catch (e) {
    ElMessage.error('获取导师名单失败')
  } finally {
    rosterLoading.value = false
  }
}

const loadSemesters = async () => {
  try {
    const res = await getSemesters({ page: 1, page_size: 100 })
    semesterList.value = res.data?.items || res.data || []
  } catch (e) {
    console.error('加载学期失败', e)
  }
}

const handleSubmitAssign = async () => {
  await assignFormRef.value.validate()
  assignLoading.value = true
  try {
    const res = await assignMentor({
      teacher_id: assignForm.teacher_id,
      student_ids: assignForm.student_ids,
      semester_id: assignForm.semester_id,
    })
    if (res.success) {
      ElMessage.success(res.message || '分配完成')
      assignDialogVisible.value = false
      assignForm.student_ids = []
      fetchRoster()
    }
  } finally {
    assignLoading.value = false
  }
}

const handleDeleteRoster = async (row) => {
  const res = await removeMentorAssignment(row.id)
  if (res.success) {
    ElMessage.success('已删除')
    fetchRoster()
  }
}

const handleDownloadTemplate = async () => {
  try {
    const res = await getMentorRosterTemplate()
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '导师名单导入模板.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载模板失败')
  }
}

const handleImportFileChange = (file) => {
  importFile.value = file.raw
}

const handleImportSubmit = async () => {
  if (!importFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  importLoading.value = true
  try {
    const items = await parseRosterRows(importFile.value)
    if (items.length === 0) {
      ElMessage.warning('文件中没有数据')
      return
    }
    const res = await batchImportMentorRoster({
      semester_id: rosterFilter.semester_id || undefined,
      items,
    })
    if (res.success) {
      const { success_count, update_count, errors } = res.data
      if (errors?.length) {
        const detail = errors.map(e => `第${e.row}行：${e.reason}`).join('\n')
        await ElMessageBox.alert(detail, `导入完成：新增 ${success_count} 行，更换 ${update_count} 行，失败 ${errors.length} 行`, {
          type: 'warning',
          confirmButtonText: '知道了',
        })
      } else {
        ElMessage.success(`导入完成：新增 ${success_count} 行，更换导师 ${update_count} 行`)
      }
      importDialogVisible.value = false
      importFile.value = null
      uploadRef.value?.clearFiles()
      fetchRoster()
    }
  } finally {
    importLoading.value = false
  }
}

const parseRosterRows = async (file) => {
  const buffer = await file.arrayBuffer()
  const workbook = new ExcelJS.Workbook()
  await workbook.xlsx.load(buffer)
  const worksheet = workbook.worksheets[0]
  if (!worksheet) return []

  const headerMap = {}
  worksheet.getRow(1).eachCell((cell, colNumber) => {
    const header = String(cell.value ?? '').trim()
    if (header) headerMap[header] = colNumber
  })
  const valueOf = (row, names) => {
    for (const name of names) {
      const col = headerMap[name]
      if (col) return String(row.getCell(col).value ?? '').trim()
    }
    return ''
  }

  const rows = []
  worksheet.eachRow((row, rowNumber) => {
    if (rowNumber === 1) return
    const teacherId = valueOf(row, ['教师ID', 'teacher_id'])
    const teacherName = valueOf(row, ['教师姓名', 'teacher_name'])
    const studentId = valueOf(row, ['学号', 'student_id'])
    if (!studentId) return
    rows.push({
      teacher_id: teacherId || undefined,
      teacher_name: teacherName || undefined,
      student_id: studentId,
      student_name: valueOf(row, ['学生姓名', 'student_name']) || undefined,
    })
  })
  return rows
}

// ============ 统计 ============
const fetchStats = async () => {
  statsLoading.value = true
  notTalkedLoading.value = true
  try {
    const params = {}
    if (statsSemesterId.value) params.semester_id = statsSemesterId.value
    if (statsMonth.value) params.month = statsMonth.value
    const [statsRes, notTalkedRes] = await Promise.all([
      getMentorTalkStatistics(params),
      getMentorNotTalked({ ...params, page: 1, page_size: 10000 }),
    ])
    fetchStudentStatus()
    if (statsRes.success) {
      statsList.value = statsRes.data.items
      if (!statsSemesterId.value) statsSemesterId.value = statsRes.data.semester_id
    }
    if (notTalkedRes.success) {
      notTalkedList.value = notTalkedRes.data.items
    }
  } catch (e) {
    ElMessage.error('获取统计失败')
  } finally {
    statsLoading.value = false
    notTalkedLoading.value = false
  }
}

const copyNotTalkedReminder = async () => {
  const byTeacher = {}
  for (const row of notTalkedList.value) {
    if (!byTeacher[row.teacher_name]) byTeacher[row.teacher_name] = []
    byTeacher[row.teacher_name].push(row.student_name)
  }
  const lines = Object.entries(byTeacher).map(
    ([teacher, students]) => `${teacher}：${students.join('、')}`
  )
  const text = `本月尚未谈话学生名单（共 ${notTalkedList.value.length} 人）：\n${lines.join('\n')}`
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('提醒名单已复制到剪贴板')
  } catch {
    ElMessageBox.alert(text, '本月未谈话学生', { confirmButtonText: '关闭' })
  }
}

// ============ 初始化 ============
const loadTeachers = async () => {
  try {
    const res = await getTeachers()
    // 旧版接口返回 {teachers: [...], total}，无 success/data 包装
    teacherList.value = res?.teachers || res?.data?.teachers || res?.data?.items || res?.data || []
  } catch (e) {
    console.error('加载教师列表失败', e)
  }
}

const switchToAvailableTab = () => {
  if (activeTab.value === 'talks' && !canCreateTalk.value && !canUpdateTalk.value) {
    // 教师默认可见谈话记录；无谈话权限的角色切到名单或统计
    if (canManageRoster.value) activeTab.value = 'roster'
    else if (canViewStats.value) activeTab.value = 'stats'
  }
}

onMounted(async () => {
  await loadMyPermissions()
  canCreateTalk.value = hasApiPermissionSync('/api/moral/mentor-talks/create')
  canUpdateTalk.value = hasApiPermissionSync('/api/moral/mentor-talks/update')
  canDeleteTalk.value = hasApiPermissionSync('/api/moral/mentor-talks/delete')
  canManageRoster.value = hasApiPermissionSync('/api/moral/mentor-roster/assign')
  canManageCategories.value = hasApiPermissionSync('/api/moral/mentor-talks/categories/update')
  canViewStats.value = hasApiPermissionSync('/api/moral/mentor-talks/statistics')

  switchToAvailableTab()
  loadTalkStudentOptions()
  loadTalkCategories()
  fetchTalks()
  if (canManageRoster.value) {
    loadSemesters()
    fetchRoster()
    loadTeachers()
    loadAssignStudentOptions()
  }
  if (canViewStats.value) {
    loadSemesters()
    fetchStats()
  }
})

watch(activeTab, (tab) => {
  if (tab === 'roster' && rosterList.value.length === 0) fetchRoster()
  if (tab === 'stats' && statsList.value.length === 0) fetchStats()
})
</script>

<style scoped>
.mentor-system-page {
  padding: 0;
}
.mentor-tabs {
  margin-top: 12px;
}
.filter-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.form-hint {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
  margin-top: 4px;
}
.category-tags {
  min-height: 40px;
}
.table-card {
  margin-bottom: 16px;
}
</style>
