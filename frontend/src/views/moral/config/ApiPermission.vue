<template>
  <div class="api-permission-page">
    <aside class="module-panel">
      <div class="panel-title">
        <span>权限模块</span>
        <el-button type="primary" :icon="Plus" circle @click="handleAddModule" />
      </div>
      <el-scrollbar class="module-list">
        <button
          class="module-item"
          :class="{ active: !selectedModuleId }"
          type="button"
          @click="selectModule(null)"
        >
          <span>全部API</span>
          <small>{{ permissions.length }} / 风险 {{ riskyPermissionCount }}</small>
        </button>
        <button
          v-for="module in modules"
          :key="module.id"
          class="module-item"
          :class="{ active: selectedModuleId === module.id }"
          type="button"
          @click="selectModule(module.id)"
        >
          <span>{{ module.module_name }}</span>
          <small>{{ module.api_count || 0 }} / 风险 {{ moduleRiskCountMap[module.id] || 0 }}</small>
        </button>
      </el-scrollbar>
    </aside>

    <section class="api-panel">
      <el-card>
        <template #header>
          <div class="card-header">
            <div>
              <span>API权限管理</span>
              <small v-if="selectedModule" class="header-subtitle">{{ selectedModule.module_name }}</small>
            </div>
            <div class="header-actions">
              <el-button @click="handleEditModule" :disabled="!selectedModule">编辑模块</el-button>
              <el-button @click="handleApplyModule" :disabled="!selectedModule">批量下发模块权限</el-button>
              <el-button @click="handleAuditPermissions()" :loading="auditLoading">权限巡检</el-button>
              <el-button type="success" @click="handleAdd">新增API</el-button>
              <el-dropdown trigger="click" @command="handleAdvancedCommand">
                <el-button>
                  更多操作
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="syncScope" :disabled="scopeLoading">同步范围规则</el-dropdown-item>
                    <el-dropdown-item command="initDefault" :disabled="initLoading">初始化默认配置</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </template>

        <el-alert
          title="默认策略为角色和最低等级同时满足；公开API会跳过鉴权；继承模块的API会使用模块上的角色、等级和策略。"
          type="info"
          show-icon
          :closable="false"
          class="policy-alert"
        />

        <div class="filter-toolbar">
          <el-input v-model="keywordFilter" clearable placeholder="搜索名称或路径" />
          <el-select v-model="resourceFilter" clearable placeholder="按业务对象筛选">
            <el-option v-for="item in resourceOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-select v-model="actionFilter" clearable placeholder="按动作筛选">
            <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
          <el-segmented v-model="riskViewMode" :options="riskViewOptions" />
          <el-select v-model="riskLabelFilter" clearable placeholder="按风险类型筛选">
            <el-option v-for="risk in availableRiskLabels" :key="risk" :label="risk" :value="risk" />
          </el-select>
          <span class="filter-result">当前 {{ filteredPermissions.length }} 条</span>
        </div>

        <div v-if="selectedRows.length" class="batch-toolbar">
          <span>已选择 {{ selectedRows.length }} 条 API</span>
          <el-button type="primary" @click="templateDialogVisible = true">批量套用模板</el-button>
          <el-button @click="batchRoleDialogVisible = true">批量设置角色</el-button>
          <el-button @click="handleAuditPermissions(selectedRows)">批量校验</el-button>
        </div>

        <el-table
          ref="permissionTableRef"
          :data="filteredPermissions"
          v-loading="loading"
          stripe
          :row-class-name="getPermissionRowClass"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="api_name" label="API名称" min-width="150" />
          <el-table-column label="权限路径 / 实际调用" min-width="300">
            <template #default="{ row }">
              <div class="api-path-cell">
                <span class="api-path-main">{{ row.api_path }}</span>
                <span class="api-route-hint">{{ row.route_hint || `${row.http_method || '*'} ${row.api_path}` }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="业务对象" width="120">
            <template #default="{ row }">{{ getResourceName(row.resource_type) }}</template>
          </el-table-column>
          <el-table-column label="动作" width="90">
            <template #default="{ row }">{{ getActionName(row.action_type) }}</template>
          </el-table-column>
          <el-table-column prop="module_name" label="模块" width="110">
            <template #default="{ row }">{{ row.module_name || row.api_group }}</template>
          </el-table-column>
          <el-table-column label="方法" width="80">
            <template #default="{ row }">{{ row.http_method || '*' }}</template>
          </el-table-column>
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.config_kind === 'virtual_action'" type="info" size="small">动作配置</el-tag>
              <el-tag v-else size="small">路由配置</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="匹配" width="90">
            <template #default="{ row }">{{ getMatchName(row.match_type) }}</template>
          </el-table-column>
          <el-table-column label="生效策略" min-width="280">
            <template #default="{ row }">
              <div class="policy-cell">
                <el-tag v-if="row.is_public" type="success" size="small">公开</el-tag>
                <el-tag v-else-if="row.inherit_from_module" type="warning" size="small">继承模块</el-tag>
                <el-tag v-else size="small">单独配置</el-tag>
                <span>{{ getPolicyName(row.effective_policy?.policy_mode || row.policy_mode) }}</span>
                <span>等级 {{ row.effective_policy?.min_level ?? row.min_level ?? 0 }}</span>
                <span class="role-list">
                  {{ formatRoles(row.effective_policy?.allowed_roles || row.allowed_roles) }}
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="数据范围" min-width="180">
            <template #default="{ row }">
              <span class="scope-summary">{{ formatScopeSummary(row.data_scope_rules, dataScopeLabelMap) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="目标范围" min-width="180">
            <template #default="{ row }">
              <span class="scope-summary">{{ formatScopeSummary(row.target_scope_rules, targetScopeLabelMap) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="动作范围" min-width="180">
            <template #default="{ row }">
              <span class="scope-summary">{{ formatScopeSummary(row.operation_scope_rules, dataScopeLabelMap) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="风险" min-width="180">
            <template #default="{ row }">
              <div class="risk-tags">
                <el-tag v-for="risk in row.risk_flags || []" :key="risk" type="warning" size="small">{{ risk }}</el-tag>
                <span v-if="!(row.risk_flags || []).length">正常</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'danger'">
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>

    <el-drawer
      v-model="apiDialogVisible"
      :title="apiDialogTitle"
      size="920px"
      direction="rtl"
      class="api-permission-drawer"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="116px">
        <el-tabs v-model="activeApiTab" class="api-config-tabs">
          <el-tab-pane label="基本信息" name="basic">
        <el-form-item label="API路径" prop="api_path">
          <el-input v-model="form.api_path" placeholder="/api/moral/xxx 或 /api/moral/xxx/{id}" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="API名称" prop="api_name">
          <el-input v-model="form.api_name" placeholder="如：获取日常记录" />
        </el-form-item>
        <el-form-item label="所属模块" prop="module_id">
          <el-select v-model="form.module_id" placeholder="选择模块" filterable @change="syncApiGroup">
            <el-option v-for="module in modules" :key="module.id" :label="module.module_name" :value="module.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="API分组" prop="api_group">
          <el-input v-model="form.api_group" placeholder="兼容旧分组，默认同步模块名称" />
        </el-form-item>
        <el-form-item label="HTTP方法">
          <el-select v-model="form.http_method">
            <el-option label="全部" value="*" />
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
          </el-select>
        </el-form-item>
        <el-form-item label="路径匹配">
          <el-radio-group v-model="form.match_type">
            <el-radio-button label="exact">精确</el-radio-button>
            <el-radio-button label="prefix">前缀</el-radio-button>
            <el-radio-button label="pattern">参数模式</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="业务对象">
          <el-select v-model="form.resource_type" filterable clearable placeholder="选择业务对象">
            <el-option v-for="item in resourceOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作类型">
          <el-select v-model="form.action_type" placeholder="选择动作类型">
            <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
          </el-tab-pane>
          <el-tab-pane label="调用权限" name="policy">
        <el-form-item label="特殊设置">
          <el-checkbox v-model="form.is_public" :true-label="1" :false-label="0">公开API，无需鉴权</el-checkbox>
          <el-checkbox v-model="form.inherit_from_module" :true-label="1" :false-label="0">继承模块权限</el-checkbox>
          <el-checkbox v-model="form.enforce_backend" :true-label="1" :false-label="0">参与后端鉴权</el-checkbox>
        </el-form-item>
        <template v-if="!form.inherit_from_module && !form.is_public">
          <el-form-item label="允许角色" prop="allowed_roles">
            <el-checkbox-group v-model="form.allowed_roles">
              <el-checkbox v-for="role in roleOptions" :key="role.value" :label="role.value">{{ role.label }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
          <el-form-item label="最低等级">
            <el-input-number v-model="form.min_level" :min="0" :max="100" :step="10" />
          </el-form-item>
          <el-form-item label="鉴权策略">
            <el-select v-model="form.policy_mode">
              <el-option v-for="item in policyOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
        </template>
          </el-tab-pane>
          <el-tab-pane label="范围配置" name="scope">
        <!-- 学生资源域：显示学生范围配置 -->
        <template v-if="isStudentResource">
        <el-form-item label="快捷配置">
          <el-button @click="applyScopePreset">套用常用矩阵</el-button>
          <div class="scope-help">按 API 动作自动填入推荐范围：查看=自己创建/管理班级/管理年级/全校，新增=任教班级/管理范围/全校，编辑删除=自己创建/全校。</div>
        </el-form-item>
        <el-form-item label="数据范围">
          <div class="scope-editor">
            <div v-for="role in scopeRoleOptions" :key="'data-' + role.value" class="scope-row">
              <span class="scope-role">{{ role.label }}</span>
              <el-checkbox-group v-model="dataScopeEditor[role.value]">
                <el-checkbox v-for="item in dataScopeOptions" :key="item.value" :label="item.value">
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
          <div class="scope-help">
            控制查询、编辑、删除时能操作哪些已有记录。查看接口可给班主任勾选"自己创建 + 管理班级"，编辑/删除接口通常只勾选"自己创建"；学发、教发和管理员勾选"全校"。
          </div>
        </el-form-item>
        <el-form-item label="目标范围">
          <div class="scope-editor">
            <div v-for="role in scopeRoleOptions" :key="'target-' + role.value" class="scope-row">
              <span class="scope-role">{{ role.label }}</span>
              <el-checkbox-group v-model="targetScopeEditor[role.value]">
                <el-checkbox v-for="item in targetScopeOptions" :key="item.value" :label="item.value">
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
          <div class="scope-help">
            控制新增、录入时能选择哪些学生。日常表现建议：教师=任教班级，班主任=任教班级+管理班级，年级主任=任教班级+管理年级，学发/教发/管理员=全校学生。
          </div>
        </el-form-item>
        <el-form-item label="动作范围">
          <div class="scope-editor">
            <div v-for="role in scopeRoleOptions" :key="'operation-' + role.value" class="scope-row">
              <span class="scope-role">{{ role.label }}</span>
              <el-checkbox-group v-model="operationScopeEditor[role.value]">
                <el-checkbox v-for="item in dataScopeOptions" :key="item.value" :label="item.value">
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
          <div class="scope-help">
            控制编辑、删除、复核、关闭等动作能落到哪些已有记录。日常记录类通常是教师、班主任、年级主任仅"自己创建"，学发、教发、管理员为"全校"。
          </div>
        </el-form-item>
        </template>
        <!-- 系统资源域：不显示学生范围，显示提示 -->
        <template v-else-if="isSystemResource">
        <el-alert
          title="系统资源不涉及业务数据范围"
          type="info"
          show-icon
          :closable="false"
          class="policy-alert"
        >
          <template #default>
            此 API 属于系统管理类资源（如数据库备份、配置管理等），仅控制调用角色和最低等级，不涉及学生、班级、年级等业务数据范围。
          </template>
        </el-alert>
        </template>
        <!-- 教师资源域：按资源类型显示对应范围 -->
        <template v-else>
        <el-form-item label="可见范围">
          <div class="scope-editor">
            <div v-for="role in scopeRoleOptions" :key="'data-' + role.value" class="scope-row">
              <span class="scope-role">{{ role.label }}</span>
              <el-checkbox-group v-model="dataScopeEditor[role.value]">
                <el-checkbox v-for="item in currentTeacherScopeConfig.dataOptions" :key="item.value" :label="item.value">
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
          <div class="scope-help">{{ currentTeacherScopeConfig.dataHelp }}</div>
        </el-form-item>
        <el-form-item :label="currentTeacherScopeConfig.targetLabel">
          <div class="scope-editor">
            <div v-for="role in scopeRoleOptions" :key="'target-' + role.value" class="scope-row">
              <span class="scope-role">{{ role.label }}</span>
              <el-checkbox-group v-model="targetScopeEditor[role.value]">
                <el-checkbox v-for="item in currentTeacherScopeConfig.targetOptions" :key="item.value" :label="item.value">
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
          <div class="scope-help">{{ currentTeacherScopeConfig.targetHelp }}</div>
        </el-form-item>
        <el-form-item label="操作范围">
          <div class="scope-editor">
            <div v-for="role in scopeRoleOptions" :key="'operation-' + role.value" class="scope-row">
              <span class="scope-role">{{ role.label }}</span>
              <el-checkbox-group v-model="operationScopeEditor[role.value]">
                <el-checkbox v-for="item in currentTeacherScopeConfig.operationOptions" :key="item.value" :label="item.value">
                  {{ item.label }}
                </el-checkbox>
              </el-checkbox-group>
            </div>
          </div>
          <div class="scope-help">{{ currentTeacherScopeConfig.operationHelp }}</div>
        </el-form-item>
        </template>
          </el-tab-pane>
          <el-tab-pane label="预览校验" name="preview">
        <el-form-item label="权限预览">
          <div class="preview-box">
            <el-select v-model="previewRoleSet" multiple collapse-tags placeholder="选择角色组合">
              <el-option v-for="role in scopeRoleOptions" :key="role.value" :label="role.label" :value="role.value" />
            </el-select>
            <div class="role-preview-list">
              <div v-for="item in rolePreviewItems" :key="item.role" class="role-preview-card">
                <strong>{{ item.label }}</strong>
                <span>查看：{{ item.view }}</span>
                <span>创建目标：{{ item.target }}</span>
                <span>动作范围：{{ item.operation }}</span>
              </div>
            </div>
            <div class="preview-grid merged-preview">
              <div><strong>合并查看</strong><span>{{ mergedPreview.view }}</span></div>
              <div><strong>合并目标</strong><span>{{ mergedPreview.target }}</span></div>
              <div><strong>合并动作</strong><span>{{ mergedPreview.operation }}</span></div>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="配置校验">
          <div class="validation-panel">
            <el-tag v-for="issue in formValidationIssues" :key="issue" type="warning">{{ issue }}</el-tag>
            <span v-if="!formValidationIssues.length">未发现明显风险</span>
          </div>
        </el-form-item>
          </el-tab-pane>
        </el-tabs>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="是否启用" v-if="isEdit">
          <el-switch v-model="form.is_active" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="apiDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-drawer>

    <el-dialog v-model="templateDialogVisible" title="批量套用权限模板" width="460px">
      <el-form label-width="92px">
        <el-form-item label="模板">
          <el-select v-model="selectedTemplateKey" placeholder="选择模板">
            <el-option v-for="item in templates" :key="item.key" :label="item.label" :value="item.key" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="templateDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="templateApplyLoading" @click="handleApplyTemplate">应用</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchRoleDialogVisible" title="批量设置允许角色" width="520px">
      <el-form label-width="92px">
        <el-form-item label="允许角色">
          <el-checkbox-group v-model="batchAllowedRoles">
            <el-checkbox v-for="role in roleOptions" :key="role.value" :label="role.value">{{ role.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="说明">
          <div class="scope-help">将为所选 API 写入独立角色配置，并取消"继承模块权限"。范围规则不会自动改写，保存后可用"批量校验"复核。</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchRoleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchRoleLoading" @click="handleBatchRoleApply">应用</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="auditDialogVisible" title="权限配置巡检" width="920px">
      <div class="audit-summary">
        <div class="audit-stat">
          <strong>{{ auditReport.summary?.total || 0 }}</strong>
          <span>巡检 API</span>
        </div>
        <div class="audit-stat warning">
          <strong>{{ auditReport.summary?.risky || 0 }}</strong>
          <span>存在风险</span>
        </div>
        <div class="audit-stat success">
          <strong>{{ auditReport.summary?.healthy || 0 }}</strong>
          <span>未见明显风险</span>
        </div>
      </div>

      <div class="audit-breakdown">
        <section>
          <h4>风险类型</h4>
          <el-tag v-for="item in auditReport.risk_counts || []" :key="item.label" type="warning">
            {{ item.label }} {{ item.count }}
          </el-tag>
          <span v-if="!(auditReport.risk_counts || []).length">暂无风险项</span>
        </section>
        <section>
          <h4>模块分布</h4>
          <el-tag v-for="item in auditReport.module_counts || []" :key="item.label">
            {{ item.label }} {{ item.count }}
          </el-tag>
          <span v-if="!(auditReport.module_counts || []).length">暂无模块风险</span>
        </section>
      </div>

      <el-table :data="auditReport.items || []" stripe max-height="360">
        <el-table-column prop="api_name" label="API名称" min-width="150" />
        <el-table-column prop="api_path" label="API路径" min-width="240" />
        <el-table-column prop="module_name" label="模块" width="120" />
        <el-table-column label="动作" width="90">
          <template #default="{ row }">{{ getActionName(row.action_type) }}</template>
        </el-table-column>
        <el-table-column label="风险项" min-width="240">
          <template #default="{ row }">
            <div class="risk-tags">
              <el-tag v-for="risk in row.risk_flags || []" :key="risk" type="warning" size="small">{{ risk }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="locateAuditItem(row)">定位</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="auditDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="exportAuditReport">导出审计报告</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="moduleDialogVisible" :title="moduleDialogTitle" width="560px">
      <el-form :model="moduleForm" :rules="moduleRules" ref="moduleFormRef" label-width="116px">
        <el-form-item label="模块标识" prop="module_key">
          <el-input v-model="moduleForm.module_key" placeholder="如 moral_daily" />
        </el-form-item>
        <el-form-item label="模块名称" prop="module_name">
          <el-input v-model="moduleForm.module_name" placeholder="如 日常表现" />
        </el-form-item>
        <el-form-item label="允许角色">
          <el-checkbox-group v-model="moduleForm.allowed_roles">
            <el-checkbox v-for="role in roleOptions" :key="role.value" :label="role.value">{{ role.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="最低等级">
          <el-input-number v-model="moduleForm.min_level" :min="0" :max="100" :step="10" />
        </el-form-item>
        <el-form-item label="鉴权策略">
          <el-select v-model="moduleForm.policy_mode">
            <el-option v-for="item in policyOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="moduleForm.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="是否启用" v-if="isModuleEdit">
          <el-switch v-model="moduleForm.is_active" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="moduleForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="moduleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleModuleSubmit" :loading="moduleSubmitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getApiPermissions,
  createApiPermission,
  updateApiPermission,
  deleteApiPermission,
  initApiPermissions,
  syncDefaultScopeRules,
  getApiPermissionModules,
  getApiPermissionResourceTypes,
  createApiPermissionModule,
  updateApiPermissionModule,
  applyApiPermissionModule,
  getApiPermissionTemplates,
  applyApiPermissionTemplate,
  auditApiPermissions
} from '@/api/modules/moral'
import { downloadRowsAsExcel } from '@/utils/filegather'

const loading = ref(false)
const initLoading = ref(false)
const scopeLoading = ref(false)
const submitLoading = ref(false)
const moduleSubmitLoading = ref(false)
const permissions = ref([])
const modules = ref([])
const resourceTypes = ref([])
const selectedModuleId = ref(null)
const selectedRows = ref([])
const templates = ref([])
const templateDialogVisible = ref(false)
const templateApplyLoading = ref(false)
const selectedTemplateKey = ref('')
const batchRoleDialogVisible = ref(false)
const batchRoleLoading = ref(false)
const batchAllowedRoles = ref([])
const auditLoading = ref(false)
const auditDialogVisible = ref(false)
const auditReport = ref({
  summary: { total: 0, risky: 0, healthy: 0 },
  risk_counts: [],
  module_counts: [],
  action_counts: [],
  items: []
})
const permissionTableRef = ref(null)
const focusedApiId = ref(null)
const keywordFilter = ref('')
const resourceFilter = ref('')
const actionFilter = ref('')
const riskViewMode = ref('all')
const riskLabelFilter = ref('')
const riskViewOptions = [
  { label: '全部', value: 'all' },
  { label: '仅风险', value: 'risky' },
  { label: '仅正常', value: 'healthy' }
]

const apiDialogVisible = ref(false)
const moduleDialogVisible = ref(false)
const isEdit = ref(false)
const isModuleEdit = ref(false)
const apiDialogTitle = computed(() => isEdit.value ? '编辑API权限' : '新增API权限')
const moduleDialogTitle = computed(() => isModuleEdit.value ? '编辑权限模块' : '新增权限模块')
const formRef = ref(null)
const moduleFormRef = ref(null)
const activeApiTab = ref('basic')

const selectedModule = computed(() => modules.value.find(item => item.id === selectedModuleId.value))
const riskyPermissionCount = computed(() => permissions.value.filter(item => (item.risk_flags || []).length).length)
const moduleRiskCountMap = computed(() => permissions.value.reduce((acc, item) => {
  if (item.module_id && (item.risk_flags || []).length) acc[item.module_id] = (acc[item.module_id] || 0) + 1
  return acc
}, {}))
const availableRiskLabels = computed(() => [...new Set(
  permissions.value.flatMap(item => item.risk_flags || [])
)])
const filteredPermissions = computed(() => {
  return permissions.value.filter((item) => {
    if (selectedModuleId.value && item.module_id !== selectedModuleId.value) return false
    const keyword = keywordFilter.value.trim().toLowerCase()
    if (keyword) {
      const searchable = `${item.api_name || ''} ${item.api_path || ''} ${item.route_hint || ''}`.toLowerCase()
      if (!searchable.includes(keyword)) return false
    }
    if (resourceFilter.value && item.resource_type !== resourceFilter.value) return false
    if (actionFilter.value && item.action_type !== actionFilter.value) return false
    const risks = item.risk_flags || []
    if (riskViewMode.value === 'risky' && !risks.length) return false
    if (riskViewMode.value === 'healthy' && risks.length) return false
    if (riskLabelFilter.value && !risks.includes(riskLabelFilter.value)) return false
    return true
  })
})

const roleOptions = [
  { value: 'admin', label: '管理员' },
  { value: 'jiaowu', label: '教发部' },
  { value: 'xuefa', label: '学发部' },
  { value: 'g_leader', label: '年级主任' },
  { value: 'cleader', label: '班主任' },
  { value: 'teacher', label: '教师' },
  { value: 'student', label: '学生' },
  { value: 'parent', label: '家长' }
]

const scopeRoleOptions = roleOptions.filter(role => !['student', 'parent'].includes(role.value))

const dataScopeOptions = [
  { value: 'own_created', label: '自己创建' },
  { value: 'teaching_classes', label: '任教班级' },
  { value: 'managed_classes', label: '管理班级' },
  { value: 'managed_grades', label: '管理年级' },
  { value: 'all', label: '全校' }
]

const targetScopeOptions = [
  { value: 'teaching_classes', label: '任教班级' },
  { value: 'managed_classes', label: '管理班级' },
  { value: 'managed_grades', label: '管理年级' },
  { value: 'all_students', label: '全校学生' }
]
const fallbackResourceOptions = [
  { value: 'daily_record', label: '日常表现记录' },
  { value: 'moment_record', label: '点滴记录' },
  { value: 'school_record', label: '校级事件' },
  { value: 'punishment_record', label: '处分记录' },
  { value: 'moral_task', label: '德育任务' },
  { value: 'collective_event', label: '集体事件' },
  { value: 'student_lifebook', label: '一生一册' },
  { value: 'student_profile', label: '学生画像' },
  { value: 'consultation', label: 'AI诊疗' },
  { value: 'score_trend', label: '得分趋势' },
  { value: 'dashboard', label: '驾驶舱' },
  { value: 'teacher', label: '教师管理' },
  { value: 'filegather', label: '文件收集' },
  { value: 'invigilation', label: '监考安排' },
  { value: 'lesson_schedule', label: '旧版课表' },
  { value: 'legacy_homework', label: '旧版作业公告' },
  { value: 'teacher_todo', label: '教师待办' },
  { value: 'teacher_todo_group', label: '协作群组' },
  { value: 'database_backup', label: '数据库备份' },
  { value: 'database_admin', label: '数据库管理' },
  { value: 'api_permission', label: 'API权限管理' },
  { value: 'menu_permission', label: '菜单权限' },
  { value: 'system_config', label: '系统配置' },
  { value: 'operation_log', label: '操作日志' },
  { value: 'scheduler', label: '定时调度' },
  { value: 'ai_model_config', label: 'AI模型配置' }
]
const resourceOptions = computed(() => {
  const fromBackend = resourceTypes.value
    .filter(item => item.is_active !== 0)
    .map(item => ({ value: item.resource_type, label: item.resource_name }))
  const merged = [...fromBackend, ...fallbackResourceOptions]
  return Array.from(new Map(merged.map(item => [item.value, item])).values())
})
const fallbackResourceMeta = {
  teacher: { resource_name: '教师管理', resource_domain: 'teacher_owned', scope_schema: 'teacher_scope' },
  filegather: { resource_name: '文件收集', resource_domain: 'teacher_owned', scope_schema: 'filegather_scope' },
  invigilation: { resource_name: '监考安排', resource_domain: 'teacher_owned', scope_schema: 'invigilation_scope' },
  lesson_schedule: { resource_name: '旧版课表', resource_domain: 'teacher_owned', scope_schema: 'lesson_schedule_scope' },
  legacy_homework: { resource_name: '旧版作业公告', resource_domain: 'teacher_owned', scope_schema: 'legacy_homework_scope' },
  teacher_todo: { resource_name: '教师待办', resource_domain: 'teacher_owned', scope_schema: 'teacher_todo_scope' },
  teacher_todo_group: { resource_name: '协作群组', resource_domain: 'teacher_owned', scope_schema: 'teacher_group_scope' },
  database_backup: { resource_name: '数据库备份', resource_domain: 'system_admin', scope_schema: 'system_action_scope' },
  database_admin: { resource_name: '数据库管理', resource_domain: 'system_admin', scope_schema: 'system_action_scope' },
  api_permission: { resource_name: 'API权限管理', resource_domain: 'system_admin', scope_schema: 'system_action_scope' },
  menu_permission: { resource_name: '菜单权限', resource_domain: 'system_admin', scope_schema: 'system_action_scope' },
  system_config: { resource_name: '系统配置', resource_domain: 'system_admin', scope_schema: 'system_action_scope' },
  operation_log: { resource_name: '操作日志', resource_domain: 'system_admin', scope_schema: 'system_action_scope' },
  scheduler: { resource_name: '定时调度', resource_domain: 'system_admin', scope_schema: 'system_action_scope' },
  ai_model_config: { resource_name: 'AI模型配置', resource_domain: 'system_admin', scope_schema: 'system_action_scope' }
}
const actionOptions = [
  { value: 'view', label: '查看' },
  { value: 'create', label: '创建' },
  { value: 'update', label: '编辑' },
  { value: 'delete', label: '删除' },
  { value: 'review', label: '复核' },
  { value: 'export', label: '导出' },
  { value: 'operate', label: '操作' }
]

// 资源类型映射表（从后端获取）
const resourceTypeMap = computed(() => {
  const map = { ...fallbackResourceMeta }
  for (const item of resourceTypes.value) {
    map[item.resource_type] = {
      resource_name: item.resource_name,
      resource_domain: item.resource_domain,
      scope_schema: item.scope_schema
    }
  }
  return map
})

// 当前表单资源的 scope_schema
const currentScopeSchema = computed(() => {
  const meta = resourceTypeMap.value[form.resource_type]
  return meta?.scope_schema || 'student_scope'
})

// 是否为学生资源域（需要显示学生范围配置）
const isStudentResource = computed(() => {
  return currentScopeSchema.value === 'student_scope'
})

// 是否为系统资源域（不显示学生范围配置）
const isSystemResource = computed(() => {
  return currentScopeSchema.value === 'system_action_scope'
})

const option = (value, label) => ({ value, label })
const teacherResourceScopeConfigs = {
  teacher_scope: {
    dataOptions: [option('teacher_directory', '教师通讯录'), option('self', '本人'), option('all_teachers', '全校教师')],
    targetOptions: [option('self', '本人'), option('all_teachers', '全校教师')],
    operationOptions: [option('self', '本人'), option('all_teachers', '全校教师')],
    targetLabel: '目标范围',
    dataHelp: '控制能查看哪些教师账号资料。普通教师通常只需要教师通讯录；管理员可查看和维护全校教师。',
    targetHelp: '控制创建或维护教师账号时能作用到哪些教师对象。教师管理写操作通常只给管理员勾选全校教师。',
    operationHelp: '控制修改密码、编辑教师资料、任教班级维护等动作范围。改密是本人，教师资料维护是全校教师。',
    privilegedScopes: { all_teachers: ['admin', 'xuefa', 'g_leader'] }
  },
  filegather_scope: {
    dataOptions: [option('own_uploaded', '自己上传'), option('all_files', '全部文件')],
    targetOptions: [option('own_uploaded', '自己上传')],
    operationOptions: [option('own_uploaded', '自己上传'), option('all_files', '全部文件')],
    targetLabel: '上传范围',
    dataHelp: '控制能查看哪些上传文件。教师端通常是自己上传；管理端是全部文件。',
    targetHelp: '控制上传文件归属。教师上传只能生成自己名下的文件记录。',
    operationHelp: '控制删除、下载、标记完成等动作能作用到哪些文件。教师删除自己上传，管理角色可处理全部文件。',
    privilegedScopes: { all_files: ['admin', 'jiaowu', 'xuefa'] }
  },
  invigilation_scope: {
    dataOptions: [option('all_projects', '全部监考项目')],
    targetOptions: [option('all_projects', '全部监考项目')],
    operationOptions: [option('all_projects', '全部监考项目')],
    targetLabel: '项目范围',
    dataHelp: '监考安排当前不按学生、班级、年级拆分，教务或管理员查看全部监考项目。',
    targetHelp: '控制创建、导入监考项目或安排时的项目范围。',
    operationHelp: '控制更新、删除、导出、通知等动作能作用到哪些监考项目。',
    privilegedScopes: { all_projects: ['admin', 'jiaowu'] }
  },
  lesson_schedule_scope: {
    dataOptions: [option('self_schedule', '本人课表'), option('current_classes', '当前上课班级'), option('all_schedules', '全部课表')],
    targetOptions: [option('all_schedules', '全部课表')],
    operationOptions: [option('all_schedules', '全部课表')],
    targetLabel: '课表范围',
    dataHelp: '控制能查看哪些课表数据。本周/下周教师课表通常是本人；当前上课班级接口返回当前全校上课状态。',
    targetHelp: '控制上传或更新课表时能作用到的课表范围。',
    operationHelp: '控制上传、刷新课表等操作范围，通常只给教务或管理员全部课表。',
    privilegedScopes: { all_schedules: ['admin', 'jiaowu'] }
  },
  legacy_homework_scope: {
    dataOptions: [option('own_created', '自己创建'), option('all_homework', '全部作业公告')],
    targetOptions: [option('own_created', '自己创建'), option('all_homework', '全部作业公告')],
    operationOptions: [option('own_created', '自己创建'), option('all_homework', '全部作业公告')],
    targetLabel: '发布范围',
    dataHelp: '控制旧版作业/公告记录可见范围。公开班级查看接口不在此处限制，受保护接口主要按创建人收口。',
    targetHelp: '控制发布作业/公告时生成的记录归属。教师发布后默认只拥有自己创建的记录。',
    operationHelp: '控制编辑、删除作业/公告的记录范围。教师只能操作自己创建，管理员可操作全部。',
    privilegedScopes: { all_homework: ['admin'] }
  },
  teacher_todo_scope: {
    dataOptions: [option('own_created', '自己创建'), option('assigned_to_me', '分配给我')],
    targetOptions: [option('selected_teachers', '指定教师'), option('my_groups', '我的协作群组'), option('all_teachers', '全校教师')],
    operationOptions: [option('own_created', '自己创建'), option('assigned_to_me', '分配给我')],
    targetLabel: '协作范围',
    dataHelp: '控制教师能看到哪些待办。通常勾选自己创建和分配给我。',
    targetHelp: '控制创建待办时能选择哪些协作对象。全校教师通常只给管理员。',
    operationHelp: '控制编辑、删除、完成待办等操作。编辑/删除通常仅自己创建，完成/恢复可包含分配给我。',
    privilegedScopes: { all_teachers: ['admin'] }
  },
  teacher_group_scope: {
    dataOptions: [option('own_created', '自己创建')],
    targetOptions: [option('selected_teachers', '指定教师'), option('my_groups', '我的协作群组'), option('all_teachers', '全校教师')],
    operationOptions: [option('own_created', '自己创建')],
    targetLabel: '成员范围',
    dataHelp: '控制能查看哪些协作群组。群组通常仅自己创建可见。',
    targetHelp: '控制群组中能添加哪些教师。全校教师通常只给管理员。',
    operationHelp: '控制编辑、删除群组以及维护成员的范围，通常仅自己创建。',
    privilegedScopes: { all_teachers: ['admin'] }
  }
}
const currentTeacherScopeConfig = computed(() => (
  teacherResourceScopeConfigs[currentScopeSchema.value] || teacherResourceScopeConfigs.teacher_todo_scope
))

const teacherScopeLabelMap = {
  self: '本人',
  teacher_directory: '教师通讯录',
  all_teachers: '全校教师',
  own_uploaded: '自己上传',
  all_files: '全部文件',
  all_projects: '全部监考项目',
  self_schedule: '本人课表',
  current_classes: '当前上课班级',
  all_schedules: '全部课表',
  all_homework: '全部作业公告',
  own_created: '自己创建',
  assigned_to_me: '分配给我',
  selected_teachers: '指定教师',
  my_groups: '我的协作群组'
}
const systemScopeLabelMap = {
  view_config: '查看配置',
  update_config: '修改配置',
  execute: '执行',
  view_history: '查看历史',
  download: '下载',
  delete: '删除',
  manage: '管理'
}
const dataScopeLabelMap = { ...Object.fromEntries(dataScopeOptions.map(item => [item.value, item.label])), ...teacherScopeLabelMap, ...systemScopeLabelMap }
const targetScopeLabelMap = { ...Object.fromEntries(targetScopeOptions.map(item => [item.value, item.label])), ...teacherScopeLabelMap, ...systemScopeLabelMap }

const policyOptions = [
  { value: 'role_and_level', label: '角色和等级同时满足' },
  { value: 'role_or_level', label: '角色或等级满足即可' },
  { value: 'role_only', label: '只看角色' },
  { value: 'level_only', label: '只看等级' }
]

const roleNames = Object.fromEntries(roleOptions.map(item => [item.value, item.label]))
const policyNames = Object.fromEntries(policyOptions.map(item => [item.value, item.label]))
const matchNames = { exact: '精确', prefix: '前缀', pattern: '参数' }
const resourceNames = computed(() => Object.fromEntries(resourceOptions.value.map(item => [item.value, item.label])))
const actionNames = Object.fromEntries(actionOptions.map(item => [item.value, item.label]))
const expectedPublicApiPaths = new Set([
  '/api/token',
  '/api/class-codes/',
  '/api/schedule/{class_name}',
  '/api/todays',
  '/api/schedules',
  '/api/periods',
  '/api/class-info/{class_code}',
  '/api/students_status/{class_code}',
  '/api/student_info/',
  '/api/insert_delay/',
  '/api/homework/{class_code}',
  '/api/announcements/{class_code}',
  '/api/messages/{class_code}',
  '/api/delay_infos/{classCode}'
])

const form = reactive({
  id: null,
  api_path: '',
  api_name: '',
  api_group: '',
  module_id: null,
  http_method: '*',
  match_type: 'exact',
  allowed_roles: ['admin'],
  min_level: 0,
  policy_mode: 'role_and_level',
  inherit_from_module: 0,
  is_public: 0,
  enforce_backend: 1,
  resource_type: '',
  action_type: 'view',
  description: '',
  is_active: 1
})

const moduleForm = reactive({
  id: null,
  module_key: '',
  module_name: '',
  allowed_roles: ['admin'],
  min_level: 0,
  policy_mode: 'role_and_level',
  sort_order: 0,
  description: '',
  is_active: 1
})

const createEmptyScopeEditor = () => Object.fromEntries(
  scopeRoleOptions.map(role => [role.value, []])
)

const dataScopeEditor = reactive(createEmptyScopeEditor())
const targetScopeEditor = reactive(createEmptyScopeEditor())
const operationScopeEditor = reactive(createEmptyScopeEditor())
const previewRoleSet = ref([])

const rules = {
  api_path: [{ required: true, message: '请输入API路径', trigger: 'blur' }],
  api_name: [{ required: true, message: '请输入API名称', trigger: 'blur' }],
  api_group: [{ required: true, message: '请输入API分组', trigger: 'blur' }]
}

const moduleRules = {
  module_key: [{ required: true, message: '请输入模块标识', trigger: 'blur' }],
  module_name: [{ required: true, message: '请输入模块名称', trigger: 'blur' }]
}

const handleSelectionChange = (rows) => {
  selectedRows.value = rows
  if (!batchRoleDialogVisible.value && rows.length) {
    batchAllowedRoles.value = [...new Set(rows.flatMap(row => row.allowed_roles || []))]
  }
}

const getPermissionRowClass = ({ row }) => row.id === focusedApiId.value ? 'focused-api-row' : ''

const syncPreviewRoles = (roles = []) => {
  previewRoleSet.value = scopeRoleOptions
    .map(role => role.value)
    .filter(role => roles.includes(role))
}

const formatRoles = (roles = []) => {
  if (!roles.length) return '不限角色'
  return roles.map(role => roleNames[role] || role).join('、')
}

const formatScopeSummary = (rules = {}, labelMap = {}) => {
  if (!rules || Object.keys(rules).length === 0) return '未配置'
  return scopeRoleOptions
    .filter(role => Array.isArray(rules[role.value]) && rules[role.value].length)
    .map(role => `${role.label}:${rules[role.value].map(scope => labelMap[scope] || scope).join('/')}`)
    .join('；') || '未配置'
}

const getPolicyName = (policy) => policy === 'public' ? '公开' : (policyNames[policy] || policy)
const getMatchName = (matchType) => matchNames[matchType] || '精确'
const getResourceName = (resourceType) => resourceNames.value[resourceType] || '未标注'
const getActionName = (actionType) => actionNames[actionType] || '未标注'

const normalizeScopeRules = (rules = {}) => {
  const aliases = {
    own_class: 'managed_classes',
    g_leader_grade: 'managed_grades',
    grade_students: 'managed_grades',
    all_students: 'all_students'
  }
  return Object.fromEntries(
    scopeRoleOptions.map((role) => {
      const scopes = Array.isArray(rules?.[role.value]) ? rules[role.value] : []
      return [role.value, [...new Set(scopes.map(scope => aliases[scope] || scope))]]
    })
  )
}

const loadScopeEditors = (dataRules = {}, targetRules = {}, operationRules = {}) => {
  Object.assign(dataScopeEditor, normalizeScopeRules(dataRules))
  Object.assign(targetScopeEditor, normalizeScopeRules(targetRules))
  Object.assign(operationScopeEditor, normalizeScopeRules(operationRules))
}

const dumpScopeEditor = (editor) => {
  const rules = {}
  for (const role of scopeRoleOptions) {
    const scopes = editor[role.value] || []
    if (scopes.length) rules[role.value] = scopes
  }
  return rules
}

const inferScopeAction = () => {
  const path = form.api_path || ''
  const method = form.http_method || '*'
  if (path.includes('/create') || method === 'POST') return 'create'
  if (path.includes('/delete') || method === 'DELETE') return 'delete'
  if (path.includes('/update') || method === 'PUT') return 'update'
  if (path.includes('/revoke') || path.includes('/close')) return 'update'
  return 'view'
}

const applyScopePreset = () => {
  const action = inferScopeAction()
  const viewRules = {
    admin: ['all'],
    jiaowu: ['all'],
    xuefa: ['all'],
    g_leader: ['own_created', 'managed_grades'],
    cleader: ['own_created', 'managed_classes'],
    teacher: ['own_created']
  }
  const actionRules = {
    admin: ['all'],
    jiaowu: ['all'],
    xuefa: ['all'],
    g_leader: ['own_created'],
    cleader: ['own_created'],
    teacher: ['own_created']
  }
  const targetRules = {
    admin: ['all_students'],
    jiaowu: ['all_students'],
    xuefa: ['all_students'],
    g_leader: ['teaching_classes', 'managed_grades'],
    cleader: ['teaching_classes', 'managed_classes'],
    teacher: ['teaching_classes']
  }

  if (action === 'create') {
    loadScopeEditors({}, targetRules, {})
    return
  }
  loadScopeEditors(action === 'view' ? viewRules : {}, {}, action === 'view' ? {} : actionRules)
}

const formatPreviewScopes = (editor, labelMap, roles = previewRoleSet.value) => {
  const scopes = new Set()
  for (const role of roles) {
    for (const scope of editor[role] || []) scopes.add(labelMap[scope] || scope)
  }
  return scopes.size ? [...scopes].join('、') : '未配置'
}

const rolePreviewItems = computed(() => previewRoleSet.value.map((role) => ({
  role,
  label: roleNames[role] || role,
  view: formatPreviewScopes(dataScopeEditor, dataScopeLabelMap, [role]),
  target: formatPreviewScopes(targetScopeEditor, targetScopeLabelMap, [role]),
  operation: formatPreviewScopes(operationScopeEditor, dataScopeLabelMap, [role])
})))

const mergedPreview = computed(() => ({
  view: formatPreviewScopes(dataScopeEditor, dataScopeLabelMap),
  target: formatPreviewScopes(targetScopeEditor, targetScopeLabelMap),
  operation: formatPreviewScopes(operationScopeEditor, dataScopeLabelMap)
}))

const formValidationIssues = computed(() => {
  const issues = []
  const path = form.api_path || ''
  const action = form.action_type || inferScopeAction()
  const dataRules = dumpScopeEditor(dataScopeEditor)
  const targetRules = dumpScopeEditor(targetScopeEditor)
  const operationRules = dumpScopeEditor(operationScopeEditor)
  if (path.includes('{') && path.includes('}') && form.match_type !== 'pattern') {
    issues.push('动态路径建议使用"参数模式"')
  }
  if (form.enforce_backend === 0) issues.push('当前 API 未参与后端统一鉴权')
  if (form.is_public === 1 && !expectedPublicApiPaths.has(path)) issues.push('当前 API 被配置为公开访问')

  const allowedRoles = new Set(form.allowed_roles || [])

  if (isSystemResource.value) {
    if (!allowedRoles.has('admin')) issues.push('系统资源应至少允许管理员')
    const nonAdminRoles = [...allowedRoles].filter(role => role !== 'admin')
    if (nonAdminRoles.length && !path.includes('/menu-permission/my-menu')) {
      issues.push(`系统资源存在非管理员角色：${nonAdminRoles.map(role => roleNames[role] || role).join('、')}`)
    }
    if ((form.min_level || 0) < 100 && !path.includes('/menu-permission/my-menu')) {
      issues.push('系统资源最低等级建议为 100')
    }
    if (Object.keys(dataRules).length || Object.keys(targetRules).length) {
      issues.push('系统资源不应配置学生或教师业务范围')
    }
    return issues
  }

  if (!isStudentResource.value) {
    const studentScopes = new Set(['teaching_classes', 'managed_classes', 'managed_grades', 'all_students'])
    const validTeacherScopes = new Set([
      ...currentTeacherScopeConfig.value.dataOptions.map(item => item.value),
      ...currentTeacherScopeConfig.value.targetOptions.map(item => item.value),
      ...currentTeacherScopeConfig.value.operationOptions.map(item => item.value)
    ])
    const privilegedScopes = currentTeacherScopeConfig.value.privilegedScopes || {}
    for (const [label, rules] of [['数据范围', dataRules], ['目标范围', targetRules], ['动作范围', operationRules]]) {
      for (const [role, scopes] of Object.entries(rules)) {
        if ((scopes || []).some(scope => studentScopes.has(scope))) issues.push(`${label}包含学生范围，不适用于教师资源`)
        for (const scope of scopes || []) {
          if (!validTeacherScopes.has(scope)) issues.push(`${label}包含不适用于当前资源的范围：${teacherScopeLabelMap[scope] || scope}`)
          const allowedScopeRoles = privilegedScopes[scope]
          if (allowedScopeRoles && !allowedScopeRoles.includes(role)) {
            issues.push(`${roleNames[role] || role} 不应配置“${teacherScopeLabelMap[scope] || scope}”`)
          }
        }
      }
    }
    if (action === 'view' && !Object.keys(dataRules).length) issues.push('教师资源查看类 API 未配置可见范围')
    if (action === 'create' && !Object.keys(targetRules).length) issues.push('教师资源创建类 API 未配置目标范围')
    if (['update', 'delete', 'operate'].includes(action) && !Object.keys(operationRules).length) issues.push('教师资源操作类 API 未配置操作范围')
    if (['update', 'delete'].includes(action)) {
      for (const [role, scopes] of Object.entries(operationRules)) {
        if (currentScopeSchema.value === 'teacher_todo_scope' && (scopes || []).includes('assigned_to_me')) {
          issues.push(`${roleNames[role] || role} 编辑/删除不应包含“分配给我”`)
        }
      }
    }
    for (const [label, rules] of [['数据范围', dataRules], ['目标范围', targetRules], ['动作范围', operationRules]]) {
      const extraRoles = Object.keys(rules).filter(role => !allowedRoles.has(role))
      if (extraRoles.length) issues.push(`${label}存在未授权角色：${extraRoles.map(role => roleNames[role] || role).join('、')}`)
    }
    return issues
  }

  if (action === 'view' && !Object.keys(dataRules).length) issues.push('查看类 API 未配置数据范围')
  if (action === 'create' && !Object.keys(targetRules).length) issues.push('创建类 API 未配置目标范围')
  if (['update', 'delete', 'review', 'export'].includes(action) && !Object.keys(operationRules).length) {
    issues.push('动作类 API 未配置动作范围')
  }
  const scopeGroups = [
    ['数据范围', dataRules],
    ['目标范围', targetRules],
    ['动作范围', operationRules]
  ]
  for (const [label, rules] of scopeGroups) {
    const extraRoles = Object.keys(rules).filter(role => !allowedRoles.has(role))
    if (extraRoles.length) issues.push(`${label}存在未授权角色：${extraRoles.map(role => roleNames[role] || role).join('、')}`)
  }
  const expectedRules = action === 'create'
    ? targetRules
    : ['update', 'delete', 'review', 'export'].includes(action)
      ? operationRules
      : dataRules
  if (Object.keys(expectedRules).length) {
    const missingRoles = [...allowedRoles]
      .filter(role => scopeRoleOptions.some(item => item.value === role))
      .filter(role => !expectedRules[role]?.length)
    if (missingRoles.length) {
      issues.push(`允许角色缺少对应范围：${missingRoles.map(role => roleNames[role] || role).join('、')}`)
    }
  }
  return issues
})

const fetchPermissions = async () => {
  loading.value = true
  try {
    const res = await getApiPermissions()
    if (res.success) permissions.value = res.data || []
  } catch (error) {
    console.error('获取权限配置失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchModules = async () => {
  try {
    const res = await getApiPermissionModules()
    if (res.success) modules.value = res.data || []
  } catch (error) {
    console.error('获取模块失败:', error)
  }
}

const fetchResourceTypes = async () => {
  try {
    const res = await getApiPermissionResourceTypes()
    if (res.success) resourceTypes.value = res.data || []
  } catch (error) {
    console.error('获取资源类型失败:', error)
  }
}

const fetchTemplates = async () => {
  try {
    const res = await getApiPermissionTemplates()
    if (res.success) {
      templates.value = res.data || []
      if (!selectedTemplateKey.value && templates.value.length) selectedTemplateKey.value = templates.value[0].key
    }
  } catch (error) {
    console.error('获取权限模板失败:', error)
  }
}

const refreshAll = async () => {
  await fetchModules()
  await fetchResourceTypes()
  await fetchPermissions()
  await fetchTemplates()
}

const selectModule = (moduleId) => {
  selectedModuleId.value = moduleId
}

const syncApiGroup = () => {
  const module = modules.value.find(item => item.id === form.module_id)
  if (module) form.api_group = module.module_name
}

const handleInit = async () => {
  try {
    await ElMessageBox.confirm('初始化将添加默认配置并补齐模块，已存在配置不会重复添加。确定继续？', '提示', { type: 'info' })
    initLoading.value = true
    const res = await initApiPermissions()
    if (res.success) {
      ElMessage.success(res.message)
      refreshAll()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('初始化失败:', error)
  } finally {
    initLoading.value = false
  }
}

const handleSyncScopeRules = async () => {
  let force = 0
  try {
    await ElMessageBox.confirm(
      '将代码中的默认数据范围规则同步到数据库。\n\n点击"强制覆盖"会覆盖所有已有范围配置；点击"仅补齐"只更新空配置。',
      '同步范围规则',
      {
        type: 'warning',
        confirmButtonText: '强制覆盖',
        cancelButtonText: '仅补齐',
        distinguishCancelAndClose: true,
      }
    )
    force = 1
  } catch (action) {
    if (action === 'cancel') {
      force = 0
    } else {
      return
    }
  }

  try {
    scopeLoading.value = true
    const res = await syncDefaultScopeRules(force)
    if (res.success) {
      ElMessage.success(`${force ? '强制覆盖' : '仅补齐'}：${res.message}`)
      refreshAll()
    }
  } catch (error) {
    console.error('同步范围规则失败:', error)
  } finally {
    scopeLoading.value = false
  }
}

const handleAdvancedCommand = (command) => {
  if (command === 'syncScope') {
    handleSyncScopeRules()
    return
  }
  if (command === 'initDefault') {
    handleInit()
  }
}

const resetApiForm = () => {
  Object.assign(form, {
    id: null,
    api_path: '',
    api_name: '',
    api_group: selectedModule.value?.module_name || '',
    module_id: selectedModuleId.value,
    http_method: '*',
    match_type: 'exact',
    allowed_roles: selectedModule.value?.allowed_roles?.length ? [...selectedModule.value.allowed_roles] : ['admin'],
    min_level: selectedModule.value?.min_level || 0,
    policy_mode: selectedModule.value?.policy_mode || 'role_and_level',
    inherit_from_module: selectedModuleId.value ? 1 : 0,
    is_public: 0,
    enforce_backend: 1,
    resource_type: '',
    action_type: inferScopeAction(),
    description: '',
    is_active: 1
  })
  loadScopeEditors({}, {}, {})
  syncPreviewRoles(form.allowed_roles)
  activeApiTab.value = 'basic'
}

const handleAdd = () => {
  isEdit.value = false
  resetApiForm()
  apiDialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, {
    id: row.id,
    api_path: row.api_path,
    api_name: row.api_name,
    api_group: row.api_group,
    module_id: row.module_id,
    http_method: row.http_method || '*',
    match_type: row.match_type || 'exact',
    allowed_roles: row.allowed_roles || ['admin'],
    min_level: row.min_level || 0,
    policy_mode: row.policy_mode || 'role_and_level',
    inherit_from_module: row.inherit_from_module || 0,
    is_public: row.is_public || 0,
    enforce_backend: row.enforce_backend ?? 1,
    resource_type: row.resource_type || '',
    action_type: row.action_type || inferScopeAction(),
    description: row.description || '',
    is_active: row.is_active
  })
  loadScopeEditors(row.data_scope_rules, row.target_scope_rules, row.operation_scope_rules)
  syncPreviewRoles(form.allowed_roles)
  activeApiTab.value = 'basic'
  apiDialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除配置 "${row.api_name}"？`, '提示', { type: 'warning' })
    const res = await deleteApiPermission(row.id)
    if (res.success) {
      ElMessage.success('删除成功')
      refreshAll()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('删除失败:', error)
  }
}

const apiPayload = () => {
  const systemResource = isSystemResource.value
  return {
    api_path: form.api_path,
    api_name: form.api_name,
    api_group: form.api_group,
    module_id: form.module_id,
    http_method: form.http_method,
    match_type: form.match_type,
    allowed_roles: form.allowed_roles,
    min_level: form.min_level,
    policy_mode: form.policy_mode,
    inherit_from_module: form.inherit_from_module,
    is_public: form.is_public,
    enforce_backend: form.enforce_backend,
    resource_type: form.resource_type,
    action_type: form.action_type,
    data_scope_rules: systemResource ? {} : dumpScopeEditor(dataScopeEditor),
    target_scope_rules: systemResource ? {} : dumpScopeEditor(targetScopeEditor),
    operation_scope_rules: dumpScopeEditor(operationScopeEditor),
    description: form.description,
    is_active: form.is_active
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    if (formValidationIssues.value.length) {
      await ElMessageBox.confirm(
        `当前配置存在以下提醒：\n${formValidationIssues.value.map(item => `- ${item}`).join('\n')}\n\n仍要继续保存吗？`,
        '配置提醒',
        { type: 'warning' }
      )
    }
    submitLoading.value = true
    const res = isEdit.value
      ? await updateApiPermission(form.id, apiPayload())
      : await createApiPermission(apiPayload())
    if (res.success) {
      ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
      apiDialogVisible.value = false
      refreshAll()
    }
  } catch (error) {
    console.error('提交失败:', error)
  } finally {
    submitLoading.value = false
  }
}

const handleApplyTemplate = async () => {
  if (!selectedTemplateKey.value) {
    ElMessage.warning('请选择模板')
    return
  }
  if (!selectedRows.value.length) {
    ElMessage.warning('请选择需要更新的API')
    return
  }
  try {
    templateApplyLoading.value = true
    const res = await applyApiPermissionTemplate({
      config_ids: selectedRows.value.map(row => row.id),
      template_key: selectedTemplateKey.value
    })
    if (res.success) {
      ElMessage.success(res.message)
      templateDialogVisible.value = false
      selectedRows.value = []
      refreshAll()
    }
  } catch (error) {
    console.error('批量套用模板失败:', error)
  } finally {
    templateApplyLoading.value = false
  }
}

const handleBatchRoleApply = async () => {
  if (!selectedRows.value.length) {
    ElMessage.warning('请选择需要更新的API')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确定为 ${selectedRows.value.length} 条 API 批量设置允许角色，并取消继承模块权限吗？`,
      '批量设置角色',
      { type: 'warning' }
    )
    batchRoleLoading.value = true
    await Promise.all(selectedRows.value.map(row => updateApiPermission(row.id, {
      allowed_roles: batchAllowedRoles.value,
      inherit_from_module: 0
    })))
    ElMessage.success('批量角色设置成功')
    batchRoleDialogVisible.value = false
    selectedRows.value = []
    refreshAll()
  } catch (error) {
    if (error !== 'cancel') console.error('批量设置角色失败:', error)
  } finally {
    batchRoleLoading.value = false
  }
}

const handleAuditPermissions = async (rows = []) => {
  try {
    auditLoading.value = true
    const res = await auditApiPermissions({
      config_ids: rows.map(row => row.id)
    })
    if (res.success) {
      auditReport.value = res.data || auditReport.value
      auditDialogVisible.value = true
    }
  } catch (error) {
    console.error('权限配置巡检失败:', error)
  } finally {
    auditLoading.value = false
  }
}

const locateAuditItem = async (row) => {
  focusedApiId.value = row.id
  selectedModuleId.value = row.module_id || null
  riskViewMode.value = 'all'
  riskLabelFilter.value = ''
  auditDialogVisible.value = false
  await nextTick()
  const target = filteredPermissions.value.find(item => item.id === row.id)
  if (target) permissionTableRef.value?.setCurrentRow?.(target)
}

const exportAuditReport = async () => {
  const summary = auditReport.value.summary || {}
  await downloadRowsAsExcel({
    filename: `api-permission-audit-${new Date().toISOString().slice(0, 10)}`,
    sheetName: '权限审计',
    title: 'API 权限审计报告',
    summaryRows: [
      ['巡检总数', summary.total || 0],
      ['风险数量', summary.risky || 0],
      ['正常数量', summary.healthy || 0]
    ],
    columns: [
      { header: 'API名称', key: 'api_name', width: 24 },
      { header: 'API路径', key: 'api_path', width: 42 },
      { header: '实际调用', key: 'route_hint', width: 42 },
      { header: '配置类型', key: 'config_kind_name', width: 12 },
      { header: '模块', key: 'module_name', width: 18 },
      { header: '动作', key: 'action_type_name', width: 10 },
      { header: '风险项', key: 'risk_flags', width: 36 }
    ],
    rows: (auditReport.value.items || []).map(item => ({
      api_name: item.api_name || '',
      api_path: item.api_path || '',
      route_hint: item.route_hint || '',
      config_kind_name: item.config_kind === 'virtual_action' ? '动作配置' : '路由配置',
      module_name: item.module_name || '',
      action_type_name: getActionName(item.action_type),
      risk_flags: (item.risk_flags || []).join('；')
    }))
  })
}

const resetModuleForm = () => {
  Object.assign(moduleForm, {
    id: null,
    module_key: '',
    module_name: '',
    allowed_roles: ['admin'],
    min_level: 0,
    policy_mode: 'role_and_level',
    sort_order: 0,
    description: '',
    is_active: 1
  })
}

const handleAddModule = () => {
  isModuleEdit.value = false
  resetModuleForm()
  moduleDialogVisible.value = true
}

const handleEditModule = () => {
  if (!selectedModule.value) return
  isModuleEdit.value = true
  Object.assign(moduleForm, {
    id: selectedModule.value.id,
    module_key: selectedModule.value.module_key,
    module_name: selectedModule.value.module_name,
    allowed_roles: selectedModule.value.allowed_roles || [],
    min_level: selectedModule.value.min_level || 0,
    policy_mode: selectedModule.value.policy_mode || 'role_and_level',
    sort_order: selectedModule.value.sort_order || 0,
    description: selectedModule.value.description || '',
    is_active: selectedModule.value.is_active
  })
  moduleDialogVisible.value = true
}

const handleModuleSubmit = async () => {
  try {
    await moduleFormRef.value.validate()
    moduleSubmitLoading.value = true
    const payload = {
      module_key: moduleForm.module_key,
      module_name: moduleForm.module_name,
      allowed_roles: moduleForm.allowed_roles,
      min_level: moduleForm.min_level,
      policy_mode: moduleForm.policy_mode,
      sort_order: moduleForm.sort_order,
      description: moduleForm.description,
      is_active: moduleForm.is_active
    }
    const res = isModuleEdit.value
      ? await updateApiPermissionModule(moduleForm.id, payload)
      : await createApiPermissionModule(payload)
    if (res.success) {
      ElMessage.success(isModuleEdit.value ? '模块更新成功' : '模块创建成功')
      moduleDialogVisible.value = false
      refreshAll()
    }
  } catch (error) {
    console.error('模块提交失败:', error)
  } finally {
    moduleSubmitLoading.value = false
  }
}

const handleApplyModule = async () => {
  if (!selectedModule.value) return
  try {
    await ElMessageBox.confirm(`确定把 "${selectedModule.value.module_name}" 的权限批量应用到模块内API？`, '提示', { type: 'warning' })
    const res = await applyApiPermissionModule(selectedModule.value.id)
    if (res.success) {
      ElMessage.success(res.message)
      refreshAll()
    }
  } catch (error) {
    if (error !== 'cancel') console.error('应用模块权限失败:', error)
  }
}

onMounted(refreshAll)
</script>

<style scoped>
.api-permission-page {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr);
  gap: 16px;
  min-height: calc(100vh - 120px);
  padding: 20px;
}

.module-panel,
.api-panel :deep(.el-card) {
  min-height: 100%;
}

.module-panel {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-bg-color);
  padding: 14px;
}

.risk-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preview-box {
  width: 100%;
  display: grid;
  gap: 12px;
}

.preview-grid {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.preview-grid > div {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
}

.role-preview-list {
  display: grid;
  gap: 10px;
}

.role-preview-card {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-bg-color);
}

.merged-preview {
  border-style: dashed;
}

.audit-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.audit-stat {
  display: grid;
  gap: 4px;
  padding: 14px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
}

.audit-stat strong {
  font-size: 24px;
  line-height: 1;
}

.audit-stat.warning strong {
  color: var(--el-color-warning);
}

.audit-stat.success strong {
  color: var(--el-color-success);
}

.audit-breakdown {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.audit-breakdown section {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
}

.audit-breakdown h4 {
  width: 100%;
  margin: 0 0 4px;
  font-size: 14px;
}

.batch-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 14px 0;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.filter-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  margin: 14px 0;
}

.filter-toolbar :deep(.el-input) {
  width: 240px;
}

.filter-toolbar :deep(.el-select) {
  width: 240px;
}

.filter-result {
  color: var(--el-text-color-secondary);
}

.api-panel :deep(.focused-api-row td) {
  background: var(--el-color-warning-light-9) !important;
}

.validation-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-height: 32px;
  align-items: center;
}

.api-config-tabs {
  width: 100%;
}

.panel-title,
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.header-subtitle {
  margin-left: 10px;
  color: var(--el-text-color-secondary);
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.module-list {
  height: calc(100vh - 190px);
  margin-top: 12px;
}

.module-item {
  display: flex;
  width: 100%;
  justify-content: space-between;
  align-items: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  padding: 10px 8px;
  color: var(--el-text-color-regular);
  cursor: pointer;
  text-align: left;
}

.module-item:hover,
.module-item.active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.module-item small {
  color: var(--el-text-color-secondary);
}

.policy-alert {
  margin-bottom: 14px;
}

.scope-help {
  width: 100%;
  margin-top: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.scope-editor {
  width: 100%;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  overflow: hidden;
}

.scope-row {
  display: grid;
  grid-template-columns: 82px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.scope-row:last-child {
  border-bottom: 0;
}

.scope-role {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.scope-summary {
  display: -webkit-box;
  overflow: hidden;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  line-height: 1.4;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.policy-cell {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  line-height: 1.6;
}

.api-path-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  line-height: 1.4;
}

.api-path-main {
  font-family: var(--el-font-family);
  color: var(--el-text-color-primary);
}

.api-route-hint {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.role-list {
  color: var(--el-text-color-secondary);
}

@media (max-width: 900px) {
  .api-permission-page {
    grid-template-columns: 1fr;
  }

  .module-list {
    height: auto;
    max-height: 240px;
  }
}
</style>
