# 函数级全量审计清单

## 说明

- 生成日期：2026-05-02
- 范围：`lesson/**/*.py` 与 `frontend/src/**/*.{js,vue,html}`，排除 `__pycache__`、`.pytest_cache`、`dist`、`node_modules`。
- Python 通过 AST 识别类、函数、异步函数和方法；前端通过源码模式识别函数、箭头函数和对象方法。
- “功能说明”优先使用 docstring，其次按函数名、路由装饰器和源码上下文推断。
- 本清单用于防止重构遗漏功能；详细整改策略见 `function-level-audit-and-refactor-plan.md`。

## 汇总

- 审计单元总数：2239
- 后端 Python 单元：1545
- 前端 JS/Vue 单元：694

### 按领域统计

| 领域 | 单元数 |
|------|--------|
| 前端 API 封装 | 140 |
| 前端其他 | 11 |
| 前端工具 | 11 |
| 前端测试代码 | 16 |
| 前端状态 | 10 |
| 前端组件 | 8 |
| 前端组合函数 | 22 |
| 前端路由 | 2 |
| 前端页面 | 219 |
| 前端页面 - 德育 | 232 |
| 前端页面 - 驾驶舱 | 23 |
| 后端 API | 249 |
| 后端 API - 德育 | 297 |
| 后端会员/管理 | 64 |
| 后端其他 | 189 |
| 后端基础设施 | 169 |
| 后端招生/应用 | 69 |
| 后端网络设备集成 | 55 |
| 后端脚本 | 53 |
| 后端课表/教学/微信指令 | 172 |
| 测试代码 | 228 |

### 高密度文件

| 文件 | 单元数 |
|------|--------|
| `lesson/models/datas_api_legacy.py` | 103 |
| `frontend/src/api/modules/moral.js` | 101 |
| `lesson/models/lesson/lesson.py` | 77 |
| `lesson/tests/test_api.py` | 60 |
| `lesson/tests/test_permission.py` | 55 |
| `lesson/tests/test_auth.py` | 47 |
| `lesson/models/manage/member.py` | 44 |
| `lesson/wxmsg.py` | 42 |
| `lesson/models/datas_api/moral/api_permission.py` | 40 |
| `lesson/models/datas_api/moral/base.py` | 37 |
| `lesson/models/datas_api/dashboard.py` | 36 |
| `lesson/models/datas_api/moral/admin.py` | 35 |
| `lesson/models/application/application_V1.0.py` | 34 |
| `lesson/models/application/application.py` | 34 |
| `lesson/models/task.py` | 32 |
| `lesson/models/datas_api/moral/profile.py` | 31 |
| `lesson/models/datas_api/invigilation.py` | 29 |
| `frontend/src/views/InvigilationArrange.vue` | 29 |
| `lesson/sendqueue.py` | 26 |
| `frontend/src/views/TeacherManage.vue` | 24 |
| `lesson/tests/test_migration.py` | 23 |
| `lesson/tests/test_moral_api.py` | 23 |
| `lesson/models/datas_api/moral/daily_record.py` | 23 |
| `frontend/src/views/moral/config/ApiPermission.vue` | 23 |
| `lesson/utils/teacher_db.py` | 22 |
| `lesson/models/network/uac.py` | 22 |
| `lesson/models/lesson/schedule_service.py` | 21 |
| `lesson/utils/mysql_db.py` | 20 |
| `lesson/models/daily/inout.py` | 20 |
| `lesson/models/lesson/homework.py` | 20 |
| `lesson/utils/sqlite_moral_db.py` | 18 |
| `lesson/utils/response.py` | 18 |
| `lesson/utils/monitor.py` | 17 |
| `lesson/models/datas_api/moral/scheduler.py` | 17 |
| `frontend/src/views/Homework.vue` | 17 |
| `frontend/src/views/LoudPK.vue` | 17 |
| `frontend/src/views/moral/Punishment.vue` | 17 |
| `lesson/client.py` | 16 |
| `lesson/utils/cache.py` | 16 |
| `lesson/models/filegather_db.py` | 16 |

## 前端 API 封装

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/api/modules/auth.js` | object_method | `login` | 13 | login(username, password) { | - |
| `frontend/src/api/modules/auth.js` | object_method | `refreshToken` | 26 | refreshToken() { | - |
| `frontend/src/api/modules/auth.js` | object_method | `getCurrentUser` | 34 | getCurrentUser() { | - |
| `frontend/src/api/modules/auth.js` | object_method | `logout` | 42 | logout() { | - |
| `frontend/src/api/modules/dashboard.js` | function | `getDashboardOverview` | 3 | export function getDashboardOverview() { | - |
| `frontend/src/api/modules/dashboard.js` | function | `getMoralDashboardSummary` | 7 | export function getMoralDashboardSummary(params = {}) { | - |
| `frontend/src/api/modules/dashboard.js` | function | `getTeachingDashboardSummary` | 11 | export function getTeachingDashboardSummary(params = {}) { | - |
| `frontend/src/api/modules/dashboard.js` | function | `getClassDashboardSummary` | 15 | export function getClassDashboardSummary(params = {}) { | - |
| `frontend/src/api/modules/dashboard.js` | function | `getTeacherWorkbench` | 19 | export function getTeacherWorkbench(params = {}) { | - |
| `frontend/src/api/modules/dashboard.js` | function | `getInvigilationDashboardSummary` | 23 | export function getInvigilationDashboardSummary(params = {}) { | - |
| `frontend/src/api/modules/dashboard.js` | function | `getSystemDashboardSummary` | 27 | export function getSystemDashboardSummary() { | - |
| `frontend/src/api/modules/filegather.js` | object_method | `uploadFile` | 18 | 上传：uploadFile | - |
| `frontend/src/api/modules/filegather.js` | object_method | `getMyFiles` | 37 | getMyFiles(month = '') { | - |
| `frontend/src/api/modules/filegather.js` | object_method | `deleteFile` | 47 | 删除：deleteFile | - |
| `frontend/src/api/modules/filegather.js` | object_method | `getPendingFiles` | 57 | getPendingFiles() { | - |
| `frontend/src/api/modules/filegather.js` | object_method | `getDoneFiles` | 66 | getDoneFiles(month = '') { | - |
| `frontend/src/api/modules/filegather.js` | object_method | `markDone` | 76 | markDone(fileId) { | - |
| `frontend/src/api/modules/filegather.js` | object_method | `getDownloadUrl` | 85 | getDownloadUrl(fileId) { | - |
| `frontend/src/api/modules/filegather.js` | object_method | `downloadFile` | 97 | 下载：downloadFile | - |
| `frontend/src/api/modules/filegather.js` | object_method | `getStatistics` | 108 | getStatistics(month = '') { | - |
| `frontend/src/api/modules/filegather.js` | object_method | `getMonths` | 117 | getMonths() { | - |
| `frontend/src/api/modules/homework.js` | object_method | `getHomeworkList` | 13 | getHomeworkList(classCode) { | - |
| `frontend/src/api/modules/homework.js` | object_method | `getHomeworkDetail` | 22 | getHomeworkDetail(homeworkId) { | - |
| `frontend/src/api/modules/homework.js` | object_method | `createHomework` | 31 | 创建：createHomework | - |
| `frontend/src/api/modules/homework.js` | object_method | `updateHomework` | 41 | 更新：updateHomework | - |
| `frontend/src/api/modules/homework.js` | object_method | `deleteHomework` | 50 | 删除：deleteHomework | - |
| `frontend/src/api/modules/homework.js` | object_method | `batchDeleteHomework` | 59 | batchDeleteHomework(ids) { | - |
| `frontend/src/api/modules/moral.js` | function | `getDailyEventTypes` | 18 | export function getDailyEventTypes(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createDailyEventType` | 25 | 创建：createDailyEventType | - |
| `frontend/src/api/modules/moral.js` | function | `updateDailyEventType` | 32 | 更新：updateDailyEventType | - |
| `frontend/src/api/modules/moral.js` | function | `deleteDailyEventType` | 39 | 删除：deleteDailyEventType | - |
| `frontend/src/api/modules/moral.js` | function | `batchImportDailyEventTypes` | 47 | export function batchImportDailyEventTypes(items) { | - |
| `frontend/src/api/modules/moral.js` | function | `getDailyRecords` | 55 | export function getDailyRecords(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createDailyRecord` | 63 | 创建：createDailyRecord | - |
| `frontend/src/api/modules/moral.js` | function | `batchCreateDailyRecords` | 71 | export function batchCreateDailyRecords(records) { | - |
| `frontend/src/api/modules/moral.js` | function | `updateDailyRecord` | 80 | 更新：updateDailyRecord | - |
| `frontend/src/api/modules/moral.js` | function | `deleteDailyRecord` | 88 | 删除：deleteDailyRecord | - |
| `frontend/src/api/modules/moral.js` | function | `getStudentDailyStatistics` | 97 | export function getStudentDailyStatistics(studentId, semesterId = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `getSchoolEventTypes` | 110 | export function getSchoolEventTypes(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createSchoolEventType` | 117 | 创建：createSchoolEventType | - |
| `frontend/src/api/modules/moral.js` | function | `updateSchoolEventType` | 124 | 更新：updateSchoolEventType | - |
| `frontend/src/api/modules/moral.js` | function | `deleteSchoolEventType` | 131 | 删除：deleteSchoolEventType | - |
| `frontend/src/api/modules/moral.js` | function | `batchImportSchoolEventTypes` | 139 | export function batchImportSchoolEventTypes(items) { | - |
| `frontend/src/api/modules/moral.js` | function | `getSchoolRecords` | 146 | export function getSchoolRecords(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createSchoolRecord` | 153 | 创建：createSchoolRecord | - |
| `frontend/src/api/modules/moral.js` | function | `updateSchoolRecord` | 160 | 更新：updateSchoolRecord | - |
| `frontend/src/api/modules/moral.js` | function | `deleteSchoolRecord` | 167 | 删除：deleteSchoolRecord | - |
| `frontend/src/api/modules/moral.js` | function | `getMoralTasks` | 178 | export function getMoralTasks(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createMoralTask` | 185 | 创建：createMoralTask | - |
| `frontend/src/api/modules/moral.js` | function | `updateMoralTask` | 192 | 更新：updateMoralTask | - |
| `frontend/src/api/modules/moral.js` | function | `deleteMoralTask` | 199 | 删除：deleteMoralTask | - |
| `frontend/src/api/modules/moral.js` | function | `getTaskFinishRecords` | 206 | export function getTaskFinishRecords(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `finishTask` | 213 | export function finishTask(data) { | - |
| `frontend/src/api/modules/moral.js` | function | `batchImportMoralTasks` | 221 | export function batchImportMoralTasks(items) { | - |
| `frontend/src/api/modules/moral.js` | function | `getPunishments` | 232 | export function getPunishments(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createPunishment` | 239 | 创建：createPunishment | - |
| `frontend/src/api/modules/moral.js` | function | `updatePunishment` | 246 | 更新：updatePunishment | - |
| `frontend/src/api/modules/moral.js` | function | `revokePunishment` | 253 | export function revokePunishment(recordId, reason, revokeType = 2) { | - |
| `frontend/src/api/modules/moral.js` | function | `getPunishmentReviewInfo` | 263 | export function getPunishmentReviewInfo(recordId) { | - |
| `frontend/src/api/modules/moral.js` | function | `reviewPunishment` | 270 | export function reviewPunishment(recordId, action, reason) { | - |
| `frontend/src/api/modules/moral.js` | function | `getStudentEvaluation` | 281 | export function getStudentEvaluation(studentId, semesterId = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `getClassEvaluation` | 290 | export function getClassEvaluation(classId, semesterId = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `getGradeEvaluation` | 299 | export function getGradeEvaluation(gradeId, semesterId = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `calculateEvaluation` | 308 | 计算：calculateEvaluation | - |
| `frontend/src/api/modules/moral.js` | function | `getStudentProfile` | 319 | export function getStudentProfile(studentId) { | - |
| `frontend/src/api/modules/moral.js` | function | `generateStudentProfile` | 326 | 生成：generateStudentProfile | - |
| `frontend/src/api/modules/moral.js` | function | `startStudentProfileGeneration` | 335 | export function startStudentProfileGeneration(studentId) { | - |
| `frontend/src/api/modules/moral.js` | function | `getStudentProfileGenerationStatus` | 344 | export function getStudentProfileGenerationStatus(jobId) { | - |
| `frontend/src/api/modules/moral.js` | function | `batchGenerateProfiles` | 353 | export function batchGenerateProfiles(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `getProfileConfig` | 363 | export function getProfileConfig() { | - |
| `frontend/src/api/modules/moral.js` | function | `getUpcomingBirthdays` | 374 | export function getUpcomingBirthdays(days = 7, classId = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `getTodayBirthdays` | 383 | export function getTodayBirthdays() { | - |
| `frontend/src/api/modules/moral.js` | function | `getConsultations` | 394 | export function getConsultations(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createConsultation` | 401 | 创建：createConsultation | - |
| `frontend/src/api/modules/moral.js` | function | `getConsultation` | 408 | export function getConsultation(consultationId) { | - |
| `frontend/src/api/modules/moral.js` | function | `updateConsultation` | 415 | 更新：updateConsultation | - |
| `frontend/src/api/modules/moral.js` | function | `addConsultationMessage` | 422 | export function addConsultationMessage(consultationId, data) { | - |
| `frontend/src/api/modules/moral.js` | function | `closeConsultation` | 429 | export function closeConsultation(consultationId, outcome = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `getTeachers` | 442 | export function getTeachers() { | - |
| `frontend/src/api/modules/moral.js` | function | `getGrades` | 453 | export function getGrades() { | - |
| `frontend/src/api/modules/moral.js` | function | `getEscalationRules` | 464 | export function getEscalationRules(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createEscalationRule` | 471 | 创建：createEscalationRule | - |
| `frontend/src/api/modules/moral.js` | function | `updateEscalationRule` | 478 | 更新：updateEscalationRule | - |
| `frontend/src/api/modules/moral.js` | function | `deleteEscalationRule` | 485 | 删除：deleteEscalationRule | - |
| `frontend/src/api/modules/moral.js` | function | `getConfigurableEvents` | 492 | export function getConfigurableEvents() { | - |
| `frontend/src/api/modules/moral.js` | function | `getPunishmentTypes` | 499 | export function getPunishmentTypes() { | - |
| `frontend/src/api/modules/moral.js` | function | `getStudentEscalationHistory` | 506 | export function getStudentEscalationHistory(studentId, semesterId = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `getStudentEventCount` | 515 | export function getStudentEventCount(studentId, eventId, timeWindowDays = 90) { | - |
| `frontend/src/api/modules/moral.js` | function | `getStudentAllProgress` | 524 | export function getStudentAllProgress(studentId) { | - |
| `frontend/src/api/modules/moral.js` | function | `getApiPermissions` | 535 | export function getApiPermissions(apiGroup = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `getApiPermissionModules` | 544 | export function getApiPermissionModules() { | - |
| `frontend/src/api/modules/moral.js` | function | `createApiPermissionModule` | 551 | 创建：createApiPermissionModule | - |
| `frontend/src/api/modules/moral.js` | function | `updateApiPermissionModule` | 558 | 更新：updateApiPermissionModule | - |
| `frontend/src/api/modules/moral.js` | function | `applyApiPermissionModule` | 565 | export function applyApiPermissionModule(moduleId) { | - |
| `frontend/src/api/modules/moral.js` | function | `syncLegacyApiPermissions` | 572 | 同步：syncLegacyApiPermissions | - |
| `frontend/src/api/modules/moral.js` | function | `createApiPermission` | 579 | 创建：createApiPermission | - |
| `frontend/src/api/modules/moral.js` | function | `updateApiPermission` | 586 | 更新：updateApiPermission | - |
| `frontend/src/api/modules/moral.js` | function | `deleteApiPermission` | 593 | 删除：deleteApiPermission | - |
| `frontend/src/api/modules/moral.js` | function | `getMyApiPermissions` | 600 | export function getMyApiPermissions() { | - |
| `frontend/src/api/modules/moral.js` | function | `checkApiPermission` | 607 | 检查：checkApiPermission | - |
| `frontend/src/api/modules/moral.js` | function | `initApiPermissions` | 616 | 初始化：initApiPermissions | - |
| `frontend/src/api/modules/moral.js` | function | `getApiGroups` | 623 | export function getApiGroups() { | - |
| `frontend/src/api/modules/moral.js` | function | `getCollectiveEvents` | 634 | export function getCollectiveEvents(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createCollectiveEvent` | 641 | 创建：createCollectiveEvent | - |
| `frontend/src/api/modules/moral.js` | function | `getCollectiveEvent` | 648 | export function getCollectiveEvent(eventId) { | - |
| `frontend/src/api/modules/moral.js` | function | `updateCollectiveEvent` | 655 | 更新：updateCollectiveEvent | - |
| `frontend/src/api/modules/moral.js` | function | `deleteCollectiveEvent` | 662 | 删除：deleteCollectiveEvent | - |
| `frontend/src/api/modules/moral.js` | function | `updateDistribution` | 669 | 更新：updateDistribution | - |
| `frontend/src/api/modules/moral.js` | function | `getStudentCollectiveScore` | 676 | export function getStudentCollectiveScore(studentId, semesterId = null) { | - |
| `frontend/src/api/modules/moral.js` | function | `createGrade` | 685 | 创建：createGrade | - |
| `frontend/src/api/modules/moral.js` | function | `deleteGrade` | 692 | 删除：deleteGrade | - |
| `frontend/src/api/modules/moral.js` | function | `getClasses` | 699 | export function getClasses(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createClass` | 706 | 创建：createClass | - |
| `frontend/src/api/modules/moral.js` | function | `updateClass` | 713 | 更新：updateClass | - |
| `frontend/src/api/modules/moral.js` | function | `deleteClass` | 720 | 删除：deleteClass | - |
| `frontend/src/api/modules/moral.js` | function | `getSchoolYears` | 727 | export function getSchoolYears() { | - |
| `frontend/src/api/modules/moral.js` | function | `createSchoolYear` | 734 | 创建：createSchoolYear | - |
| `frontend/src/api/modules/moral.js` | function | `getSemesters` | 741 | export function getSemesters(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `createSemester` | 748 | 创建：createSemester | - |
| `frontend/src/api/modules/moral.js` | function | `setCurrentSemester` | 755 | export function setCurrentSemester(semesterId) { | - |
| `frontend/src/api/modules/moral.js` | function | `getStudents` | 762 | export function getStudents(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `batchCreateStudents` | 769 | export function batchCreateStudents(data) { | - |
| `frontend/src/api/modules/moral.js` | function | `createStudent` | 776 | 创建：createStudent | - |
| `frontend/src/api/modules/moral.js` | function | `updateStudent` | 783 | 更新：updateStudent | - |
| `frontend/src/api/modules/moral.js` | function | `updateStudentStatus` | 790 | 更新：updateStudentStatus | - |
| `frontend/src/api/modules/moral.js` | function | `getOperationLogs` | 799 | export function getOperationLogs(params = {}) { | - |
| `frontend/src/api/modules/moral.js` | function | `getSystemConfig` | 806 | export function getSystemConfig() { | - |
| `frontend/src/api/modules/moral.js` | function | `updateSystemConfig` | 813 | 更新：updateSystemConfig | - |
| `frontend/src/api/modules/schedule.js` | object_method | `getClassSchedule` | 14 | getClassSchedule(classCode, week) { | - |
| `frontend/src/api/modules/schedule.js` | object_method | `getAllSchedules` | 24 | getAllSchedules() { | - |
| `frontend/src/api/modules/schedule.js` | object_method | `getCurrentClass` | 33 | getCurrentClass(classCode) { | - |
| `frontend/src/api/modules/schedule.js` | object_method | `uploadSchedule` | 42 | 上传：uploadSchedule | - |
| `frontend/src/api/modules/schedule.js` | object_method | `deleteSchedule` | 53 | 删除：deleteSchedule | - |
| `frontend/src/api/modules/user.js` | object_method | `getUserList` | 13 | getUserList(params) { | - |
| `frontend/src/api/modules/user.js` | object_method | `getUserDetail` | 22 | getUserDetail(userId) { | - |
| `frontend/src/api/modules/user.js` | object_method | `createUser` | 31 | 创建：createUser | - |
| `frontend/src/api/modules/user.js` | object_method | `updateUser` | 41 | 更新：updateUser | - |
| `frontend/src/api/modules/user.js` | object_method | `deleteUser` | 50 | 删除：deleteUser | - |
| `frontend/src/api/modules/user.js` | object_method | `getClassStudents` | 59 | getClassStudents(classCode) { | - |
| `frontend/src/api/modules/user.js` | object_method | `getClassCodes` | 68 | getClassCodes(ip) { | - |

## 前端其他

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/App.vue` | const_fn | `loadMoralMenuPermissions` | 211 | 加载：loadMoralMenuPermissions | 大页面 |
| `frontend/src/App.vue` | const_fn | `handleLogin` | 255 | 处理前端交互：handleLogin | 大页面 |
| `frontend/src/App.vue` | const_fn | `handleLogout` | 276 | 处理前端交互：handleLogout | 大页面 |
| `frontend/src/App.vue` | const_fn | `handleClassChange` | 294 | 处理前端交互：handleClassChange | 大页面 |
| `frontend/src/App.vue` | const_fn | `handleSelect` | 298 | 处理前端交互：handleSelect | 大页面 |
| `frontend/src/assets/zhf.html` | function | `calculateAndUpdate` | 175 | 计算：calculateAndUpdate | - |
| `frontend/src/assets/zhf.html` | function | `getComprehensiveScore` | 201 | function getComprehensiveScore(culture, professional) { | - |
| `frontend/src/assets/zhf.html` | function | `getProfessionalScore` | 206 | function getProfessionalScore(culture, comprehensive) { | - |
| `frontend/src/assets/zhf.html` | function | `getCultureScore` | 211 | function getCultureScore(professional, comprehensive) { | - |
| `frontend/src/assets/zhf.html` | function | `getCurrentRatio` | 216 | function getCurrentRatio() { | - |
| `frontend/src/assets/zhf.html` | function | `updateNotice` | 229 | 更新：updateNotice | - |

## 前端工具

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/utils/errorHandler.js` | function | `getFriendlyErrorMessage` | 32 | export function getFriendlyErrorMessage(error) { | - |
| `frontend/src/utils/errorHandler.js` | function | `showError` | 65 | export function showError(error, defaultMessage = '操作失败') { | - |
| `frontend/src/utils/errorHandler.js` | function | `showSuccess` | 74 | export function showSuccess(message = '操作成功') { | - |
| `frontend/src/utils/errorHandler.js` | function | `showWarning` | 82 | export function showWarning(message) { | - |
| `frontend/src/utils/errorHandler.js` | function | `showConfirm` | 92 | export function showConfirm(message, title = '确认') { | - |
| `frontend/src/utils/errorHandler.js` | function | `withErrorHandler` | 106 | export function withErrorHandler(fn, options = {}) { | - |
| `frontend/src/utils/errorHandler.js` | function | `createApiWrapper` | 137 | 创建：createApiWrapper | - |
| `frontend/src/utils/time.js` | const_fn | `getGMT8TimeString` | 9 | export const getGMT8TimeString = () => { | - |
| `frontend/src/utils/time.js` | const_fn | `getGMT8DateString` | 20 | export const getGMT8DateString = () => { | - |
| `frontend/src/utils/time.js` | const_fn | `getGMT8ISOString` | 30 | export const getGMT8ISOString = () => { | - |
| `frontend/src/utils/time.js` | const_fn | `getGMT8Year` | 40 | export const getGMT8Year = () => { | - |

## 前端测试代码

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/__tests__/auth.store.test.js` | function | `parseJwtPayload` | 39 | 解析：parseJwtPayload | - |
| `frontend/src/__tests__/auth.store.test.js` | function | `createMockToken` | 51 | 创建：createMockToken | - |
| `frontend/src/__tests__/auth.store.test.js` | function | `createAuthStore` | 60 | 创建：createAuthStore | - |
| `frontend/src/__tests__/auth.store.test.js` | const_fn | `isLoggedIn` | 69 | const isLoggedIn = () => !!state.token | - |
| `frontend/src/__tests__/auth.store.test.js` | const_fn | `initAuth` | 71 | 初始化：initAuth | - |
| `frontend/src/__tests__/auth.store.test.js` | const_fn | `login` | 88 | const login = async (user, password) => { | - |
| `frontend/src/__tests__/auth.store.test.js` | const_fn | `logout` | 116 | const logout = () => { | - |
| `frontend/src/__tests__/permission.test.js` | function | `checkPermission` | 17 | 检查：checkPermission | - |
| `frontend/src/__tests__/permission.test.js` | function | `hasAnyPermission` | 67 | function hasAnyPermission(permissions) { | - |
| `frontend/src/__tests__/router.test.js` | function | `isPublicPath` | 48 | function isPublicPath(path) { | - |
| `frontend/src/__tests__/router.test.js` | function | `mockBeforeEach` | 53 | function mockBeforeEach(to) { | - |
| `frontend/src/__tests__/router.test.js` | function | `ensureProtocol` | 72 | function ensureProtocol(to) { | - |
| `frontend/src/__tests__/usePermission.test.js` | function | `usePermission` | 20 | function usePermission() { | - |
| `frontend/src/__tests__/usePermission.test.js` | const_fn | `hasRole` | 27 | const hasRole = (targetRole) => { | - |
| `frontend/src/__tests__/usePermission.test.js` | const_fn | `isOwner` | 40 | const isOwner = (ownerUsername) => { | - |
| `frontend/src/__tests__/usePermission.test.js` | const_fn | `canEdit` | 44 | const canEdit = (ownerUsername) => { | - |

## 前端状态

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/stores/apiPermission.js` | const_fn | `loadMyPermissions` | 23 | 加载：loadMyPermissions | - |
| `frontend/src/stores/apiPermission.js` | const_fn | `hasApiPermissionSync` | 47 | const hasApiPermissionSync = (apiPath) => { | - |
| `frontend/src/stores/apiPermission.js` | const_fn | `clearCache` | 63 | 清理：clearCache | - |
| `frontend/src/stores/app.js` | const_fn | `getClassCode` | 10 | const getClassCode = () => { | - |
| `frontend/src/stores/app.js` | const_fn | `fetchClassCodes` | 15 | 获取/加载：fetchClassCodes | - |
| `frontend/src/stores/app.js` | const_fn | `handleClassChange` | 52 | 处理前端交互：handleClassChange | - |
| `frontend/src/stores/app.js` | const_fn | `initClassCode` | 62 | 初始化：initClassCode | - |
| `frontend/src/stores/auth.js` | const_fn | `initAuth` | 17 | 初始化：initAuth | - |
| `frontend/src/stores/auth.js` | const_fn | `login` | 41 | const login = async (user, password) => { | - |
| `frontend/src/stores/auth.js` | const_fn | `logout` | 76 | const logout = () => { | - |

## 前端组件

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/components/CourseDetail.vue` | const_fn | `handleClose` | 18 | 处理前端交互：handleClose | - |
| `frontend/src/components/DataSkeleton.vue` | const_fn | `getRandomWidth` | 101 | const getRandomWidth = () => { | - |
| `frontend/src/components/MobileCardView.vue` | const_fn | `handleResize` | 90 | 处理前端交互：handleResize | - |
| `frontend/src/components/MobileCardView.vue` | const_fn | `handleSelect` | 106 | 处理前端交互：handleSelect | - |
| `frontend/src/components/MobileCardView.vue` | const_fn | `handleClick` | 110 | 处理前端交互：handleClick | - |
| `frontend/src/components/Skeleton.vue` | const_fn | `getRandomWidth` | 69 | const getRandomWidth = () => { | - |
| `frontend/src/components/dashboard/DashboardChart.vue` | const_fn | `renderChart` | 45 | 渲染：renderChart | - |
| `frontend/src/components/dashboard/DashboardChart.vue` | const_fn | `resizeChart` | 54 | const resizeChart = () => { | - |

## 前端组合函数

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/composables/useApiPermission.js` | function | `useApiPermission` | 11 | export function useApiPermission() { | - |
| `frontend/src/composables/useApiPermission.js` | function | `checkButtonPermission` | 38 | 检查：checkButtonPermission | - |
| `frontend/src/composables/useFilterPersistence.js` | function | `useFilterPersistence` | 6 | export function useFilterPersistence(key, defaultValue = {}) { | - |
| `frontend/src/composables/useFilterPersistence.js` | const_fn | `loadFilters` | 10 | 加载：loadFilters | - |
| `frontend/src/composables/useFilterPersistence.js` | const_fn | `saveFilters` | 23 | const saveFilters = (filters) => { | - |
| `frontend/src/composables/useFilterPersistence.js` | const_fn | `clearFilters` | 32 | 清理：clearFilters | - |
| `frontend/src/composables/useLoading.js` | function | `useLoading` | 7 | export function useLoading(initialState = false) { | - |
| `frontend/src/composables/useLoading.js` | const_fn | `startLoading` | 11 | const startLoading = () => { | - |
| `frontend/src/composables/useLoading.js` | const_fn | `stopLoading` | 16 | const stopLoading = () => { | - |
| `frontend/src/composables/useLoading.js` | const_fn | `setError` | 20 | const setError = (err) => { | - |
| `frontend/src/composables/useLoading.js` | const_fn | `wrap` | 25 | const wrap = async (fn) => { | - |
| `frontend/src/composables/usePermission.js` | function | `usePermission` | 8 | export function usePermission() { | - |
| `frontend/src/composables/usePermission.js` | const_fn | `hasRole` | 25 | const hasRole = (targetRole) => { | - |
| `frontend/src/composables/usePermission.js` | const_fn | `hasPermission` | 73 | const hasPermission = (permission) => { | - |
| `frontend/src/composables/usePermission.js` | const_fn | `isOwner` | 114 | const isOwner = (ownerUsername) => { | - |
| `frontend/src/composables/usePermission.js` | const_fn | `canEdit` | 123 | const canEdit = (ownerUsername) => { | - |
| `frontend/src/composables/useWebSocket.js` | function | `useWebSocket` | 5 | export function useWebSocket(url = 'ws://localhost:14600/ws') { | - |
| `frontend/src/composables/useWebSocket.js` | const_fn | `connect` | 12 | const connect = (userId = 'anonymous', room = null) => { | - |
| `frontend/src/composables/useWebSocket.js` | const_fn | `handleMessage` | 50 | 处理前端交互：handleMessage | - |
| `frontend/src/composables/useWebSocket.js` | const_fn | `send` | 67 | 发送：send | - |
| `frontend/src/composables/useWebSocket.js` | const_fn | `ping` | 73 | const ping = () => { | - |
| `frontend/src/composables/useWebSocket.js` | const_fn | `disconnect` | 77 | const disconnect = () => { | - |

## 前端路由

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/router/index.js` | const_fn | `ensureProtocol` | 471 | const ensureProtocol = (to) => { | - |
| `frontend/src/router/index.js` | const_fn | `isPublicPath` | 503 | const isPublicPath = (path) => { | - |

## 前端页面

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/views/AdminFiles.vue` | const_fn | `formatDateTime` | 120 | 格式化：formatDateTime | - |
| `frontend/src/views/AdminFiles.vue` | const_fn | `getStatusType` | 134 | const getStatusType = (status) => { | - |
| `frontend/src/views/AdminFiles.vue` | const_fn | `fetchFiles` | 143 | 获取/加载：fetchFiles | - |
| `frontend/src/views/AdminFiles.vue` | const_fn | `fetchStats` | 160 | 获取/加载：fetchStats | - |
| `frontend/src/views/AdminFiles.vue` | const_fn | `handleDownload` | 170 | 处理前端交互：handleDownload | - |
| `frontend/src/views/AdminFiles.vue` | const_fn | `handleMarkDone` | 187 | 处理前端交互：handleMarkDone | - |
| `frontend/src/views/AdminFilesDone.vue` | const_fn | `generateMonths` | 136 | 生成：generateMonths | - |
| `frontend/src/views/AdminFilesDone.vue` | const_fn | `formatMonth` | 147 | 格式化：formatMonth | - |
| `frontend/src/views/AdminFilesDone.vue` | const_fn | `formatDateTime` | 152 | 格式化：formatDateTime | - |
| `frontend/src/views/AdminFilesDone.vue` | const_fn | `fetchFiles` | 164 | 获取/加载：fetchFiles | - |
| `frontend/src/views/AdminFilesDone.vue` | const_fn | `handleMonthChange` | 182 | 处理前端交互：handleMonthChange | - |
| `frontend/src/views/AdminFilesDone.vue` | const_fn | `handleSearch` | 186 | 处理前端交互：handleSearch | - |
| `frontend/src/views/AdminFilesDone.vue` | const_fn | `handlePageChange` | 190 | 处理前端交互：handlePageChange | - |
| `frontend/src/views/AdminFilesDone.vue` | const_fn | `handleDownload` | 194 | 处理前端交互：handleDownload | - |
| `frontend/src/views/Announcement.vue` | const_fn | `getClassCode` | 22 | const getClassCode = () => { | - |
| `frontend/src/views/Announcement.vue` | const_fn | `canManage` | 27 | const canManage = (author) => { | - |
| `frontend/src/views/Announcement.vue` | const_fn | `fetchAnnouncements` | 31 | 获取/加载：fetchAnnouncements | - |
| `frontend/src/views/Announcement.vue` | const_fn | `openEditDialog` | 58 | const openEditDialog = (ann) => { | - |
| `frontend/src/views/Announcement.vue` | const_fn | `handleUpdate` | 67 | 处理前端交互：handleUpdate | - |
| `frontend/src/views/Announcement.vue` | const_fn | `handleDelete` | 85 | 处理前端交互：handleDelete | - |
| `frontend/src/views/BasicInfo.vue` | const_fn | `getClassCode` | 10 | const getClassCode = () => { | - |
| `frontend/src/views/BasicInfo.vue` | const_fn | `fetchClassInfo` | 15 | 获取/加载：fetchClassInfo | - |
| `frontend/src/views/ClassStudents.vue` | const_fn | `getStatusType` | 95 | const getStatusType = (status) => { | - |
| `frontend/src/views/ClassStudents.vue` | const_fn | `getStatusClass` | 107 | const getStatusClass = (status) => { | - |
| `frontend/src/views/ClassStudents.vue` | const_fn | `getAvatarColor` | 119 | const getAvatarColor = (name) => { | - |
| `frontend/src/views/ClassStudents.vue` | const_fn | `fetchStudents` | 129 | 获取/加载：fetchStudents | - |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `parseScheduleCell` | 226 | 解析：parseScheduleCell | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `filterTeachers` | 289 | const filterTeachers = (query) => { | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `handleResize` | 302 | 处理前端交互：handleResize | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `fetchPeriods` | 308 | 获取/加载：fetchPeriods | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `handleApiError` | 321 | 处理前端交互：handleApiError | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `fetchCurrentClasses` | 329 | 获取/加载：fetchCurrentClasses | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `fetchTeachers` | 345 | 获取/加载：fetchTeachers | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `fetchTeacherSchedule` | 359 | 获取/加载：fetchTeacherSchedule | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `fetchNextWeekSchedule` | 380 | 获取/加载：fetchNextWeekSchedule | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `toggleWeek` | 398 | const toggleWeek = async (nextWeek) => { | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `refreshSchedule` | 404 | const refreshSchedule = async () => { | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `handleTeacherChange` | 415 | 处理前端交互：handleTeacherChange | 大页面 |
| `frontend/src/views/CurrentClasses.vue` | const_fn | `autoRefreshSchedule` | 446 | const autoRefreshSchedule = async () => { | 大页面 |
| `frontend/src/views/DelayApplication.vue` | const_fn | `getClassCode` | 83 | const getClassCode = () => { | - |
| `frontend/src/views/DelayApplication.vue` | const_fn | `fetchStudentInfo` | 89 | 获取/加载：fetchStudentInfo | - |
| `frontend/src/views/DelayApplication.vue` | const_fn | `submitDelay` | 108 | const submitDelay = async () => { | - |
| `frontend/src/views/DelayApplication.vue` | const_fn | `fetchDelayRecords` | 128 | 获取/加载：fetchDelayRecords | - |
| `frontend/src/views/DelayApplication.vue` | const_fn | `deleteDelay` | 146 | 删除：deleteDelay | - |
| `frontend/src/views/FileUpload.vue` | const_fn | `handleFileChange` | 115 | 处理前端交互：handleFileChange | - |
| `frontend/src/views/FileUpload.vue` | const_fn | `handleExceed` | 120 | 处理前端交互：handleExceed | - |
| `frontend/src/views/FileUpload.vue` | const_fn | `submitForm` | 124 | const submitForm = async () => { | - |
| `frontend/src/views/FileUpload.vue` | const_fn | `resetForm` | 153 | 重置：resetForm | - |
| `frontend/src/views/Homework.vue` | const_fn | `canModifyHomework` | 194 | const canModifyHomework = (row) => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `handleSelectionChange` | 230 | 处理前端交互：handleSelectionChange | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `handleSelectAll` | 234 | 处理前端交互：handleSelectAll | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `handleBatchDelete` | 243 | 处理前端交互：handleBatchDelete | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `getContentLines` | 261 | const getContentLines = (content) => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `hasHomework` | 270 | const hasHomework = (type) => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `getAllHomeworkList` | 285 | const getAllHomeworkList = (type) => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `calculateDuration` | 319 | 计算：calculateDuration | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `getSubjectClass` | 347 | const getSubjectClass = (subject) => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `formatDate` | 362 | 格式化：formatDate | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `getDeadlineClass` | 372 | const getDeadlineClass = (deadline) => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `getDeadlineStatus` | 383 | const getDeadlineStatus = (deadline) => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `getClassCode` | 396 | const getClassCode = () => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `openEditDialog` | 401 | const openEditDialog = (hw) => { | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `handleUpdate` | 413 | 处理前端交互：handleUpdate | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `handleDelete` | 437 | 处理前端交互：handleDelete | 大页面 |
| `frontend/src/views/Homework.vue` | const_fn | `fetchHomework` | 448 | 获取/加载：fetchHomework | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `loadProjects` | 384 | 加载：loadProjects | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `loadTeachers` | 395 | 加载：loadTeachers | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `loadProjectSlots` | 406 | 加载：loadProjectSlots | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `convertToHorizontal` | 438 | function convertToHorizontal() { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `convertToVertical` | 481 | function convertToVertical() { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `handleDragStart` | 511 | 处理前端交互：handleDragStart | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `handleDrop` | 522 | 处理前端交互：handleDrop | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `addRow` | 552 | function addRow(gradeId) { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `deleteRow` | 570 | 删除：deleteRow | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `addRoom` | 576 | function addRoom(gradeId) { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `removeRoom` | 585 | 移除：removeRoom | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `markChanged` | 596 | function markChanged() { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `showCreateProjectDialog` | 601 | function showCreateProjectDialog() { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `createProject` | 610 | 创建：createProject | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `saveSlots` | 637 | async function saveSlots() { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `showNotifyDialog` | 657 | function showNotifyDialog() { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `loadChangesPreview` | 672 | 加载：loadChangesPreview | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `sendNotificationsV2` | 694 | 发送：sendNotificationsV2 | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `showNotificationLogs` | 722 | function showNotificationLogs() { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `loadNotificationLogs` | 727 | 加载：loadNotificationLogs | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `downloadTemplate` | 739 | 下载：downloadTemplate | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `showImportDialog` | 756 | function showImportDialog() { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `handleFileChange` | 761 | 处理前端交互：handleFileChange | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `importExcel` | 765 | 导入：importExcel | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `exportExcel` | 798 | 导出：exportExcel | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `exportReport` | 816 | 导出：exportReport | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `getStatusType` | 835 | function getStatusType(status) { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `getStatusName` | 840 | function getStatusName(status) { | 大页面 |
| `frontend/src/views/InvigilationArrange.vue` | function | `confirmDeleteProject` | 846 | async function confirmDeleteProject() { | 大页面 |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `classLabel` | 203 | const classLabel = (item) => { | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `fetchCleaderClasses` | 211 | 获取/加载：fetchCleaderClasses | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `handleClassChange` | 234 | 处理前端交互：handleClassChange | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `fetchRecords` | 253 | 获取/加载：fetchRecords | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `handleFilterChange` | 273 | 处理前端交互：handleFilterChange | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `handlePageChange` | 278 | 处理前端交互：handlePageChange | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `refreshRecords` | 283 | const refreshRecords = async () => { | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `submitForm` | 287 | const submitForm = async () => { | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `handleConsume` | 317 | 处理前端交互：handleConsume | - |
| `frontend/src/views/LeaveRecord.vue` | const_fn | `resetForm` | 335 | 重置：resetForm | - |
| `frontend/src/views/LoudPK.vue` | const_fn | `getClassCode` | 85 | const getClassCode = () => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `refreshMicDevices` | 90 | const refreshMicDevices = async () => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `isLocalhost` | 114 | const isLocalhost = () => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `checkMicAvailability` | 119 | 检查：checkMicAvailability | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `getMicErrorMessage` | 147 | const getMicErrorMessage = (error) => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `syncDecibel` | 182 | 同步：syncDecibel | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `startSync` | 194 | const startSync = () => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `getItemClassCode` | 201 | const getItemClassCode = (item) => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `getItemDecibel` | 208 | const getItemDecibel = (item) => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `hashString` | 220 | const hashString = (text) => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `updateChart` | 242 | 更新：updateChart | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `fetchStats` | 323 | 获取/加载：fetchStats | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `initChart` | 346 | 初始化：initChart | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `stopAudio` | 354 | const stopAudio = () => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `updateVolume` | 374 | 更新：updateVolume | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `startAudio` | 392 | const startAudio = async () => { | 大页面 |
| `frontend/src/views/LoudPK.vue` | const_fn | `toggleListening` | 477 | const toggleListening = () => { | 大页面 |
| `frontend/src/views/MemberManage.vue` | const_fn | `fetchData` | 164 | 获取/加载：fetchData | - |
| `frontend/src/views/MemberManage.vue` | const_fn | `handleSearch` | 184 | 处理前端交互：handleSearch | - |
| `frontend/src/views/MemberManage.vue` | const_fn | `handleSizeChange` | 189 | 处理前端交互：handleSizeChange | - |
| `frontend/src/views/MemberManage.vue` | const_fn | `handleCurrentChange` | 194 | 处理前端交互：handleCurrentChange | - |
| `frontend/src/views/MemberManage.vue` | const_fn | `handleAdd` | 199 | 处理前端交互：handleAdd | - |
| `frontend/src/views/MemberManage.vue` | const_fn | `handleEdit` | 215 | 处理前端交互：handleEdit | - |
| `frontend/src/views/MemberManage.vue` | const_fn | `handleDelete` | 221 | 处理前端交互：handleDelete | - |
| `frontend/src/views/MemberManage.vue` | const_fn | `handleSubmit` | 246 | 处理前端交互：handleSubmit | - |
| `frontend/src/views/MyFiles.vue` | const_fn | `generateMonths` | 87 | 生成：generateMonths | - |
| `frontend/src/views/MyFiles.vue` | const_fn | `formatMonth` | 98 | 格式化：formatMonth | - |
| `frontend/src/views/MyFiles.vue` | const_fn | `formatDateTime` | 103 | 格式化：formatDateTime | - |
| `frontend/src/views/MyFiles.vue` | const_fn | `getStatusType` | 108 | const getStatusType = (status) => { | - |
| `frontend/src/views/MyFiles.vue` | const_fn | `fetchFiles` | 117 | 获取/加载：fetchFiles | - |
| `frontend/src/views/MyFiles.vue` | const_fn | `handleMonthChange` | 130 | 处理前端交互：handleMonthChange | - |
| `frontend/src/views/MyFiles.vue` | const_fn | `handleDelete` | 134 | 处理前端交互：handleDelete | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `fetchData` | 243 | 获取/加载：fetchData | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `handleSearch` | 263 | 处理前端交互：handleSearch | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `handleSizeChange` | 268 | 处理前端交互：handleSizeChange | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `handleCurrentChange` | 273 | 处理前端交互：handleCurrentChange | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `handleStatusChange` | 278 | 处理前端交互：handleStatusChange | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `handleAdd` | 289 | 处理前端交互：handleAdd | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `handleEdit` | 306 | 处理前端交互：handleEdit | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `handleDelete` | 312 | 处理前端交互：handleDelete | - |
| `frontend/src/views/PermissionManage.vue` | const_fn | `handleSubmit` | 337 | 处理前端交互：handleSubmit | - |
| `frontend/src/views/PublishAnnouncement.vue` | const_fn | `submitAnnouncement` | 78 | const submitAnnouncement = async () => { | - |
| `frontend/src/views/PublishAnnouncement.vue` | const_fn | `resetForm` | 119 | 重置：resetForm | - |
| `frontend/src/views/PublishAnnouncement.vue` | const_fn | `fetchClassCodes` | 125 | 获取/加载：fetchClassCodes | - |
| `frontend/src/views/PublishHomework.vue` | const_fn | `submitHomework` | 114 | const submitHomework = async () => { | - |
| `frontend/src/views/PublishHomework.vue` | const_fn | `resetForm` | 167 | 重置：resetForm | - |
| `frontend/src/views/PublishHomework.vue` | const_fn | `fetchClassCodes` | 175 | 获取/加载：fetchClassCodes | - |
| `frontend/src/views/RandomCall.vue` | const_fn | `getClassCode` | 109 | const getClassCode = () => { | - |
| `frontend/src/views/RandomCall.vue` | const_fn | `fetchStudentList` | 116 | 获取/加载：fetchStudentList | - |
| `frontend/src/views/RandomCall.vue` | const_fn | `handleCountChange` | 142 | 处理前端交互：handleCountChange | - |
| `frontend/src/views/RandomCall.vue` | const_fn | `pickRandomStudents` | 149 | const pickRandomStudents = () => { | - |
| `frontend/src/views/RandomCall.vue` | const_fn | `clearPickedStudents` | 169 | 清理：clearPickedStudents | - |
| `frontend/src/views/Schedule.vue` | const_fn | `updateCurrentTime` | 40 | 更新：updateCurrentTime | - |
| `frontend/src/views/Schedule.vue` | const_fn | `getCurrentPeriod` | 76 | const getCurrentPeriod = () => { | - |
| `frontend/src/views/Schedule.vue` | const_fn | `getSubjectColor` | 133 | const getSubjectColor = (subject) => { | - |
| `frontend/src/views/Schedule.vue` | const_fn | `getCellStyle` | 148 | const getCellStyle = ({ row, column }) => { | - |
| `frontend/src/views/Schedule.vue` | const_fn | `fetchSchedule` | 224 | 获取/加载：fetchSchedule | - |
| `frontend/src/views/Schedule.vue` | const_fn | `fetchPeriods` | 251 | 获取/加载：fetchPeriods | - |
| `frontend/src/views/Schedule.vue` | const_fn | `getClassCode` | 263 | const getClassCode = () => { | - |
| `frontend/src/views/Schedules.vue` | const_fn | `getWeekDays` | 109 | const getWeekDays = () => { | 大页面 |
| `frontend/src/views/Schedules.vue` | const_fn | `getScheduleDownloadUrl` | 140 | const getScheduleDownloadUrl = (rawUrl) => { | 大页面 |
| `frontend/src/views/Schedules.vue` | const_fn | `fetchTodays` | 190 | 获取/加载：fetchTodays | 大页面 |
| `frontend/src/views/Schedules.vue` | const_fn | `fetchSchedules` | 216 | 获取/加载：fetchSchedules | 大页面 |
| `frontend/src/views/Schedules.vue` | const_fn | `handleDateChange` | 237 | 处理前端交互：handleDateChange | 大页面 |
| `frontend/src/views/Schedules.vue` | const_fn | `tableRowClassName` | 253 | const tableRowClassName = ({ rowIndex }) => { | 大页面 |
| `frontend/src/views/SystemMonitor.vue` | const_fn | `formatBytes` | 193 | 格式化：formatBytes | - |
| `frontend/src/views/SystemMonitor.vue` | const_fn | `formatLoadAvg` | 204 | 格式化：formatLoadAvg | - |
| `frontend/src/views/SystemMonitor.vue` | const_fn | `getProgressColor` | 209 | const getProgressColor = (percent) => { | - |
| `frontend/src/views/SystemMonitor.vue` | const_fn | `getProcessStatusType` | 215 | const getProcessStatusType = (status) => { | - |
| `frontend/src/views/SystemMonitor.vue` | const_fn | `fetchHealthInfo` | 226 | 获取/加载：fetchHealthInfo | - |
| `frontend/src/views/SystemMonitor.vue` | const_fn | `fetchWsStatus` | 269 | 获取/加载：fetchWsStatus | - |
| `frontend/src/views/SystemMonitor.vue` | const_fn | `fetchProcessList` | 279 | 获取/加载：fetchProcessList | - |
| `frontend/src/views/SystemMonitor.vue` | const_fn | `refreshData` | 303 | const refreshData = async () => { | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleTriggerTypeChange` | 201 | 处理前端交互：handleTriggerTypeChange | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `fetchFuncOptions` | 209 | 获取/加载：fetchFuncOptions | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `fetchData` | 219 | 获取/加载：fetchData | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleStatusChange` | 239 | 处理前端交互：handleStatusChange | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleSearch` | 244 | 处理前端交互：handleSearch | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleSizeChange` | 249 | 处理前端交互：handleSizeChange | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleCurrentChange` | 254 | 处理前端交互：handleCurrentChange | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleAdd` | 259 | 处理前端交互：handleAdd | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleEdit` | 275 | 处理前端交互：handleEdit | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleDelete` | 292 | 处理前端交互：handleDelete | - |
| `frontend/src/views/TaskManage.vue` | const_fn | `handleSubmit` | 315 | 处理前端交互：handleSubmit | - |
| `frontend/src/views/TeacherManage.vue` | const_fn | `getRoleType` | 457 | const getRoleType = (role) => { | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `getRoleText` | 468 | const getRoleText = (role) => { | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `getIdentityText` | 481 | const getIdentityText = (identityType) => { | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `getIdentityType` | 490 | const getIdentityType = (identityType) => { | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `formatDate` | 499 | 格式化：formatDate | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `updatePagination` | 506 | 更新：updatePagination | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `fetchTeachers` | 540 | 获取/加载：fetchTeachers | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `fetchClassOptions` | 555 | 获取/加载：fetchClassOptions | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleSizeChange` | 566 | 处理前端交互：handleSizeChange | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleCurrentChange` | 573 | 处理前端交互：handleCurrentChange | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleSearch` | 579 | 处理前端交互：handleSearch | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleReset` | 585 | 处理前端交互：handleReset | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleAdd` | 595 | 处理前端交互：handleAdd | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleAddSubmit` | 606 | 处理前端交互：handleAddSubmit | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleEdit` | 635 | 处理前端交互：handleEdit | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleEditSubmit` | 656 | 处理前端交互：handleEditSubmit | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleTeachingClasses` | 692 | 处理前端交互：handleTeachingClasses | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleTeachingSubmit` | 713 | 处理前端交互：handleTeachingSubmit | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleInitTeachingClasses` | 735 | 处理前端交互：handleInitTeachingClasses | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleDelete` | 792 | 处理前端交互：handleDelete | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleResetPassword` | 810 | 处理前端交互：handleResetPassword | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleResetSubmit` | 817 | 处理前端交互：handleResetSubmit | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleChangeMyPassword` | 840 | 处理前端交互：handleChangeMyPassword | 大页面 |
| `frontend/src/views/TeacherManage.vue` | const_fn | `handleChangePasswordSubmit` | 847 | 处理前端交互：handleChangePasswordSubmit | 大页面 |
| `frontend/src/views/TeacherMessage.vue` | const_fn | `getClassCode` | 10 | const getClassCode = () => { | - |
| `frontend/src/views/TeacherMessage.vue` | const_fn | `fetchMessages` | 15 | 获取/加载：fetchMessages | - |
| `frontend/src/views/UploadSchedule.vue` | const_fn | `handleChange` | 76 | 处理前端交互：handleChange | - |
| `frontend/src/views/UploadSchedule.vue` | const_fn | `beforeUpload` | 80 | const beforeUpload = (file) => { | - |
| `frontend/src/views/UploadSchedule.vue` | const_fn | `submitUpload` | 89 | const submitUpload = () => { | - |
| `frontend/src/views/UploadSchedule.vue` | const_fn | `handleSuccess` | 95 | 处理前端交互：handleSuccess | - |
| `frontend/src/views/UploadSchedule.vue` | const_fn | `handleError` | 100 | 处理前端交互：handleError | - |

## 前端页面 - 德育

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/views/moral/Birthday.vue` | const_fn | `fetchClassList` | 94 | 获取/加载：fetchClassList | - |
| `frontend/src/views/moral/Birthday.vue` | const_fn | `fetchTodayBirthdays` | 105 | 获取/加载：fetchTodayBirthdays | - |
| `frontend/src/views/moral/Birthday.vue` | const_fn | `fetchBirthdays` | 116 | 获取/加载：fetchBirthdays | - |
| `frontend/src/views/moral/Birthday.vue` | const_fn | `getDaysTagType` | 130 | const getDaysTagType = (days) => { | - |
| `frontend/src/views/moral/Birthday.vue` | const_fn | `formatDate` | 136 | 格式化：formatDate | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `getEventTypeTag` | 259 | const getEventTypeTag = (type) => { | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `fetchGrades` | 268 | 获取/加载：fetchGrades | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `fetchClasses` | 279 | 获取/加载：fetchClasses | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `fetchEvents` | 290 | 获取/加载：fetchEvents | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleSearch` | 312 | 处理前端交互：handleSearch | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleReset` | 317 | 处理前端交互：handleReset | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleAdd` | 324 | 处理前端交互：handleAdd | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleEdit` | 336 | 处理前端交互：handleEdit | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleSubmit` | 348 | 处理前端交互：handleSubmit | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleDelete` | 378 | 处理前端交互：handleDelete | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleView` | 393 | 处理前端交互：handleView | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleEditDistribution` | 409 | 处理前端交互：handleEditDistribution | - |
| `frontend/src/views/moral/Collective.vue` | const_fn | `handleAdjustSubmit` | 418 | 处理前端交互：handleAdjustSubmit | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `getTypeTag` | 193 | const getTypeTag = (type) => { | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `getTypeName` | 198 | const getTypeName = (type) => { | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `getStatusTag` | 203 | const getStatusTag = (status) => { | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `getStatusName` | 208 | const getStatusName = (status) => { | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `getPriorityTag` | 213 | const getPriorityTag = (priority) => { | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `getPriorityName` | 218 | const getPriorityName = (priority) => { | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `fetchConsultations` | 252 | 获取/加载：fetchConsultations | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `handleSearch` | 275 | 处理前端交互：handleSearch | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `handleReset` | 280 | 处理前端交互：handleReset | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `handleCreate` | 288 | 处理前端交互：handleCreate | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `handleCreateSubmit` | 297 | 处理前端交互：handleCreateSubmit | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `handleView` | 314 | 处理前端交互：handleView | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `handleSendMessage` | 330 | 处理前端交互：handleSendMessage | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `handleRequestAI` | 348 | 处理前端交互：handleRequestAI | - |
| `frontend/src/views/moral/Consultation.vue` | const_fn | `handleClose` | 365 | 处理前端交互：handleClose | - |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `fetchRecords` | 237 | 获取/加载：fetchRecords | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `fetchEventTypes` | 264 | 获取/加载：fetchEventTypes | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `fetchClassList` | 275 | 获取/加载：fetchClassList | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `fetchGradeList` | 286 | 获取/加载：fetchGradeList | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleClassChange` | 297 | 处理前端交互：handleClassChange | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleSearch` | 312 | 处理前端交互：handleSearch | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleReset` | 317 | 处理前端交互：handleReset | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleAdd` | 324 | 处理前端交互：handleAdd | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleBatchAdd` | 337 | 处理前端交互：handleBatchAdd | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleEdit` | 341 | 处理前端交互：handleEdit | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleDelete` | 369 | 处理前端交互：handleDelete | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleSubmit` | 386 | 处理前端交互：handleSubmit | 大页面 |
| `frontend/src/views/moral/DailyRecord.vue` | const_fn | `handleExport` | 437 | 处理前端交互：handleExport | 大页面 |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `onActionChange` | 169 | const onActionChange = (row) => { | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `fetchRules` | 174 | 获取/加载：fetchRules | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `fetchConfigurableEvents` | 186 | 获取/加载：fetchConfigurableEvents | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `fetchPunishmentTypes` | 195 | 获取/加载：fetchPunishmentTypes | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `handleAdd` | 204 | 处理前端交互：handleAdd | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `handleEdit` | 212 | 处理前端交互：handleEdit | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `handleDelete` | 227 | 处理前端交互：handleDelete | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `handleSubmit` | 240 | 处理前端交互：handleSubmit | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `createDefaultRule` | 293 | 创建：createDefaultRule | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `addRule` | 304 | const addRule = () => { | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `removeRule` | 316 | 移除：removeRule | - |
| `frontend/src/views/moral/EscalationRuleManage.vue` | const_fn | `getActionType` | 320 | const getActionType = (action) => { | - |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `fetchClassList` | 255 | 获取/加载：fetchClassList | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `fetchSemesterList` | 269 | 获取/加载：fetchSemesterList | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `fetchEvaluation` | 285 | 获取/加载：fetchEvaluation | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `handleCalculate` | 302 | 处理前端交互：handleCalculate | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `handleExport` | 326 | 处理前端交互：handleExport | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `handleSortChange` | 372 | 处理前端交互：handleSortChange | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `handleViewDetail` | 381 | 处理前端交互：handleViewDetail | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `handleViewProfile` | 409 | 处理前端交互：handleViewProfile | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `getScoreClass` | 416 | const getScoreClass = (score) => { | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `getLevelType` | 423 | const getLevelType = (level) => { | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `formatScore` | 433 | 格式化：formatScore | 大页面 |
| `frontend/src/views/moral/Evaluation.vue` | const_fn | `scoreClass` | 439 | const scoreClass = (score, signed = true) => { | 大页面 |
| `frontend/src/views/moral/LifeBook.vue` | const_fn | `getTagType` | 145 | const getTagType = (type) => { | 大页面 |
| `frontend/src/views/moral/LifeBook.vue` | const_fn | `fetchClasses` | 156 | 获取/加载：fetchClasses | 大页面 |
| `frontend/src/views/moral/LifeBook.vue` | const_fn | `fetchStudents` | 167 | 获取/加载：fetchStudents | 大页面 |
| `frontend/src/views/moral/LifeBook.vue` | const_fn | `handleClassChange` | 196 | 处理前端交互：handleClassChange | 大页面 |
| `frontend/src/views/moral/LifeBook.vue` | const_fn | `handleSearch` | 201 | 处理前端交互：handleSearch | 大页面 |
| `frontend/src/views/moral/LifeBook.vue` | const_fn | `handleSelectStudent` | 206 | 处理前端交互：handleSelectStudent | 大页面 |
| `frontend/src/views/moral/LifeBook.vue` | const_fn | `handleBack` | 234 | 处理前端交互：handleBack | 大页面 |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `getTypeName` | 183 | const getTypeName = (type) => { | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `getTypeColor` | 188 | const getTypeColor = (type) => { | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `parseTags` | 193 | 解析：parseTags | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `fetchRecords` | 202 | 获取/加载：fetchRecords | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `fetchClassesAndStudents` | 232 | 获取/加载：fetchClassesAndStudents | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `handleSearch` | 256 | 处理前端交互：handleSearch | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `handleReset` | 261 | 处理前端交互：handleReset | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `handleAdd` | 270 | 处理前端交互：handleAdd | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `handleEdit` | 283 | 处理前端交互：handleEdit | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `handleSubmit` | 296 | 处理前端交互：handleSubmit | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `handleDelete` | 328 | 处理前端交互：handleDelete | - |
| `frontend/src/views/moral/MomentRecord.vue` | const_fn | `handleExport` | 342 | 处理前端交互：handleExport | - |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `getPunishmentTagType` | 349 | const getPunishmentTagType = (level) => { | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `fetchRecords` | 359 | 获取/加载：fetchRecords | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `fetchClassList` | 385 | 获取/加载：fetchClassList | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `fetchGradeList` | 396 | 获取/加载：fetchGradeList | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleClassChange` | 407 | 处理前端交互：handleClassChange | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleSearch` | 422 | 处理前端交互：handleSearch | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleReset` | 427 | 处理前端交互：handleReset | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleAdd` | 434 | 处理前端交互：handleAdd | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleEdit` | 450 | 处理前端交互：handleEdit | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleDelete` | 481 | 处理前端交互：handleDelete | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleSubmit` | 498 | 处理前端交互：handleSubmit | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleRevoke` | 516 | 处理前端交互：handleRevoke | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleRevokeSubmit` | 529 | 处理前端交互：handleRevokeSubmit | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleReview` | 546 | 处理前端交互：handleReview | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleReviewRevoke` | 565 | 处理前端交互：handleReviewRevoke | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleReviewApprove` | 579 | 处理前端交互：handleReviewApprove | 大页面 |
| `frontend/src/views/moral/Punishment.vue` | const_fn | `handleExport` | 593 | 处理前端交互：handleExport | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `fetchRecords` | 238 | 获取/加载：fetchRecords | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `fetchEventTypes` | 264 | 获取/加载：fetchEventTypes | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `fetchClassList` | 275 | 获取/加载：fetchClassList | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `fetchGradeList` | 286 | 获取/加载：fetchGradeList | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `handleClassChange` | 297 | 处理前端交互：handleClassChange | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `handleSearch` | 312 | 处理前端交互：handleSearch | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `handleReset` | 317 | 处理前端交互：handleReset | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `handleAdd` | 324 | 处理前端交互：handleAdd | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `handleEdit` | 338 | 处理前端交互：handleEdit | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `handleDelete` | 367 | 处理前端交互：handleDelete | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `handleSubmit` | 384 | 处理前端交互：handleSubmit | 大页面 |
| `frontend/src/views/moral/SchoolEvent.vue` | const_fn | `handleExport` | 427 | 处理前端交互：handleExport | 大页面 |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `handleSearch` | 192 | 处理前端交互：handleSearch | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `handleGenerate` | 210 | 处理前端交互：handleGenerate | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `applyGeneratedProfile` | 234 | const applyGeneratedProfile = (data) => { | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `wait` | 253 | const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms)) | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `pollProfileGeneration` | 255 | const pollProfileGeneration = async (jobId) => { | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `isStrengthTag` | 274 | const isStrengthTag = (tag) => { | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `getRiskType` | 279 | const getRiskType = (level) => { | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `getProgressColor` | 288 | const getProgressColor = (score) => { | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `formatDateTime` | 294 | 格式化：formatDateTime | - |
| `frontend/src/views/moral/StudentProfile.vue` | const_fn | `formatSigned` | 299 | 格式化：formatSigned | - |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `fetchTasks` | 360 | 获取/加载：fetchTasks | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `fetchGradeList` | 381 | 获取/加载：fetchGradeList | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `fetchClassList` | 392 | 获取/加载：fetchClassList | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleClassChange` | 403 | 处理前端交互：handleClassChange | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `fetchFinishRecords` | 419 | 获取/加载：fetchFinishRecords | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleTaskSearch` | 445 | 处理前端交互：handleTaskSearch | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleTaskReset` | 449 | 处理前端交互：handleTaskReset | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleAddTask` | 455 | 处理前端交互：handleAddTask | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleEditTask` | 469 | 处理前端交互：handleEditTask | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleDeleteTask` | 483 | 处理前端交互：handleDeleteTask | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleTaskSubmit` | 500 | 处理前端交互：handleTaskSubmit | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleFinishSearch` | 518 | 处理前端交互：handleFinishSearch | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleFinishReset` | 523 | 处理前端交互：handleFinishReset | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleAddFinish` | 529 | 处理前端交互：handleAddFinish | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleDeleteFinish` | 541 | 处理前端交互：handleDeleteFinish | 大页面 |
| `frontend/src/views/moral/TaskManage.vue` | const_fn | `handleFinishSubmit` | 556 | 处理前端交互：handleFinishSubmit | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `formatRoles` | 332 | 格式化：formatRoles | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `getPolicyName` | 337 | const getPolicyName = (policy) => policy === 'public' ? '公开' : (policyNames[policy] // policy) | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `getMatchName` | 338 | const getMatchName = (matchType) => matchNames[matchType] // '精确' | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `stringifyRules` | 340 | const stringifyRules = (rules) => { | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `parseRulesText` | 345 | 解析：parseRulesText | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `fetchPermissions` | 364 | 获取/加载：fetchPermissions | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `fetchModules` | 376 | 获取/加载：fetchModules | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `refreshAll` | 385 | const refreshAll = async () => { | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `selectModule` | 390 | const selectModule = (moduleId) => { | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `syncApiGroup` | 394 | 同步：syncApiGroup | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleInit` | 399 | 处理前端交互：handleInit | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleSyncLegacy` | 415 | 处理前端交互：handleSyncLegacy | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `resetApiForm` | 431 | 重置：resetApiForm | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleAdd` | 453 | 处理前端交互：handleAdd | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleEdit` | 459 | 处理前端交互：handleEdit | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleDelete` | 483 | 处理前端交互：handleDelete | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `apiPayload` | 496 | const apiPayload = () => ({ | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleSubmit` | 515 | 处理前端交互：handleSubmit | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `resetModuleForm` | 534 | 重置：resetModuleForm | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleAddModule` | 548 | 处理前端交互：handleAddModule | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleEditModule` | 554 | 处理前端交互：handleEditModule | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleModuleSubmit` | 571 | 处理前端交互：handleModuleSubmit | 大页面 |
| `frontend/src/views/moral/config/ApiPermission.vue` | const_fn | `handleApplyModule` | 600 | 处理前端交互：handleApplyModule | 大页面 |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `fetchGrades` | 140 | 获取/加载：fetchGrades | - |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `fetchTeachers` | 149 | 获取/加载：fetchTeachers | - |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `fetchClasses` | 163 | 获取/加载：fetchClasses | - |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `handleAdd` | 177 | 处理前端交互：handleAdd | - |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `handleGradeChange` | 195 | 处理前端交互：handleGradeChange | - |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `handleEdit` | 205 | 处理前端交互：handleEdit | - |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `handleSubmit` | 220 | 处理前端交互：handleSubmit | - |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `handleDelete` | 251 | 处理前端交互：handleDelete | - |
| `frontend/src/views/moral/config/ClassManage.vue` | const_fn | `handleViewStudents` | 268 | 处理前端交互：handleViewStudents | - |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `fetchDailyTypes` | 301 | 获取/加载：fetchDailyTypes | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `fetchSchoolTypes` | 315 | 获取/加载：fetchSchoolTypes | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleTabChange` | 329 | 处理前端交互：handleTabChange | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleAddDaily` | 335 | 处理前端交互：handleAddDaily | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleEditDaily` | 347 | 处理前端交互：handleEditDaily | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleSubmitDaily` | 359 | 处理前端交互：handleSubmitDaily | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleToggleDaily` | 387 | 处理前端交互：handleToggleDaily | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleAddSchool` | 402 | 处理前端交互：handleAddSchool | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleEditSchool` | 415 | 处理前端交互：handleEditSchool | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleSubmitSchool` | 428 | 处理前端交互：handleSubmitSchool | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleToggleSchool` | 457 | 处理前端交互：handleToggleSchool | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `downloadTemplate` | 472 | 下载：downloadTemplate | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleExport` | 524 | 处理前端交互：handleExport | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleImport` | 557 | 处理前端交互：handleImport | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `parseCSV` | 564 | 解析：parseCSV | 大页面 |
| `frontend/src/views/moral/config/EventTypeManage.vue` | const_fn | `handleImportSubmit` | 593 | 处理前端交互：handleImportSubmit | 大页面 |
| `frontend/src/views/moral/config/GradeManage.vue` | const_fn | `fetchGrades` | 90 | 获取/加载：fetchGrades | - |
| `frontend/src/views/moral/config/GradeManage.vue` | const_fn | `handleAdd` | 102 | 处理前端交互：handleAdd | - |
| `frontend/src/views/moral/config/GradeManage.vue` | const_fn | `handleSubmit` | 111 | 处理前端交互：handleSubmit | - |
| `frontend/src/views/moral/config/GradeManage.vue` | const_fn | `handleDelete` | 132 | 处理前端交互：handleDelete | - |
| `frontend/src/views/moral/config/GradeManage.vue` | const_fn | `handleViewClasses` | 149 | 处理前端交互：handleViewClasses | - |
| `frontend/src/views/moral/config/Index.vue` | const_fn | `fetchStats` | 116 | 获取/加载：fetchStats | - |
| `frontend/src/views/moral/config/Index.vue` | const_fn | `navigateTo` | 145 | const navigateTo = (type) => { | - |
| `frontend/src/views/moral/config/OperationLog.vue` | const_fn | `getRoleName` | 149 | const getRoleName = (role) => roleNames[role] // role | - |
| `frontend/src/views/moral/config/OperationLog.vue` | const_fn | `getTableName` | 150 | const getTableName = (table) => tableNames[table] // table | - |
| `frontend/src/views/moral/config/OperationLog.vue` | const_fn | `getOperationName` | 151 | const getOperationName = (op) => operationNames[op] // op | - |
| `frontend/src/views/moral/config/OperationLog.vue` | const_fn | `getOperationType` | 153 | const getOperationType = (op) => { | - |
| `frontend/src/views/moral/config/OperationLog.vue` | const_fn | `formatData` | 163 | 格式化：formatData | - |
| `frontend/src/views/moral/config/OperationLog.vue` | const_fn | `fetchLogs` | 180 | 获取/加载：fetchLogs | - |
| `frontend/src/views/moral/config/OperationLog.vue` | const_fn | `handleSearch` | 207 | 处理前端交互：handleSearch | - |
| `frontend/src/views/moral/config/OperationLog.vue` | const_fn | `handleReset` | 212 | 处理前端交互：handleReset | - |
| `frontend/src/views/moral/config/SemesterManage.vue` | const_fn | `fetchSchoolYears` | 147 | 获取/加载：fetchSchoolYears | - |
| `frontend/src/views/moral/config/SemesterManage.vue` | const_fn | `fetchSemesters` | 156 | 获取/加载：fetchSemesters | - |
| `frontend/src/views/moral/config/SemesterManage.vue` | const_fn | `handleAddYear` | 168 | 处理前端交互：handleAddYear | - |
| `frontend/src/views/moral/config/SemesterManage.vue` | const_fn | `handleYearSubmit` | 177 | 处理前端交互：handleYearSubmit | - |
| `frontend/src/views/moral/config/SemesterManage.vue` | const_fn | `handleAddSemester` | 194 | 处理前端交互：handleAddSemester | - |
| `frontend/src/views/moral/config/SemesterManage.vue` | const_fn | `handleSemesterSubmit` | 222 | 处理前端交互：handleSemesterSubmit | - |
| `frontend/src/views/moral/config/SemesterManage.vue` | const_fn | `handleSetCurrent` | 242 | 处理前端交互：handleSetCurrent | - |
| `frontend/src/views/moral/config/Settings.vue` | const_fn | `fetchConfig` | 142 | 获取/加载：fetchConfig | - |
| `frontend/src/views/moral/config/Settings.vue` | const_fn | `handleSave` | 170 | 处理前端交互：handleSave | - |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `getStatusType` | 263 | const getStatusType = (status) => { | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `fetchGrades` | 272 | 获取/加载：fetchGrades | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `fetchAllClasses` | 281 | 获取/加载：fetchAllClasses | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `fetchStudents` | 290 | 获取/加载：fetchStudents | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleFilterChange` | 317 | 处理前端交互：handleFilterChange | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleAdd` | 322 | 处理前端交互：handleAdd | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleEdit` | 336 | 处理前端交互：handleEdit | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleSubmit` | 351 | 处理前端交互：handleSubmit | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleViewDetail` | 384 | 处理前端交互：handleViewDetail | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleUpdateStatus` | 389 | 处理前端交互：handleUpdateStatus | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleStatusSubmit` | 396 | 处理前端交互：handleStatusSubmit | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleImport` | 409 | 处理前端交互：handleImport | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleFileChange` | 414 | 处理前端交互：handleFileChange | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleImportSubmit` | 418 | 处理前端交互：handleImportSubmit | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `handleExport` | 489 | 处理前端交互：handleExport | 大页面 |
| `frontend/src/views/moral/config/StudentManage.vue` | const_fn | `downloadTemplate` | 532 | 下载：downloadTemplate | 大页面 |

## 前端页面 - 驾驶舱

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `frontend/src/views/dashboard/ClassDashboard.vue` | const_fn | `go` | 111 | const go = (route) => route && router.push(route) | - |
| `frontend/src/views/dashboard/ClassDashboard.vue` | const_fn | `isEmpty` | 112 | const isEmpty = (items = []) => !items?.some(item => Number(item?.value) > 0) | - |
| `frontend/src/views/dashboard/ClassDashboard.vue` | const_fn | `onClassChange` | 115 | const onClassChange = (newClassId) => { | - |
| `frontend/src/views/dashboard/ClassDashboard.vue` | const_fn | `fetchClassList` | 162 | 获取/加载：fetchClassList | - |
| `frontend/src/views/dashboard/ClassDashboard.vue` | const_fn | `fetchSummary` | 170 | 获取/加载：fetchSummary | - |
| `frontend/src/views/dashboard/InvigilationDashboard.vue` | const_fn | `go` | 127 | const go = (route) => route && router.push(route) | - |
| `frontend/src/views/dashboard/InvigilationDashboard.vue` | const_fn | `isEmpty` | 128 | const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0) | - |
| `frontend/src/views/dashboard/InvigilationDashboard.vue` | const_fn | `fetchSummary` | 194 | 获取/加载：fetchSummary | - |
| `frontend/src/views/dashboard/MoralDashboard.vue` | const_fn | `go` | 96 | const go = (route) => route && router.push(route) | - |
| `frontend/src/views/dashboard/MoralDashboard.vue` | const_fn | `isEmpty` | 98 | const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0) | - |
| `frontend/src/views/dashboard/MoralDashboard.vue` | const_fn | `fetchSummary` | 207 | 获取/加载：fetchSummary | - |
| `frontend/src/views/dashboard/Overview.vue` | const_fn | `go` | 88 | const go = (route) => { | - |
| `frontend/src/views/dashboard/Overview.vue` | const_fn | `fetchOverview` | 125 | 获取/加载：fetchOverview | - |
| `frontend/src/views/dashboard/SystemDashboard.vue` | const_fn | `go` | 112 | const go = (route) => route && router.push(route) | - |
| `frontend/src/views/dashboard/SystemDashboard.vue` | const_fn | `isEmpty` | 113 | const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0) | - |
| `frontend/src/views/dashboard/SystemDashboard.vue` | const_fn | `fetchSummary` | 191 | 获取/加载：fetchSummary | - |
| `frontend/src/views/dashboard/TeacherWorkbench.vue` | const_fn | `fmt` | 168 | const fmt = (d) => { | 大页面 |
| `frontend/src/views/dashboard/TeacherWorkbench.vue` | const_fn | `go` | 183 | const go = (route) => route && router.push(route) | 大页面 |
| `frontend/src/views/dashboard/TeacherWorkbench.vue` | const_fn | `fetchSummary` | 204 | 获取/加载：fetchSummary | 大页面 |
| `frontend/src/views/dashboard/TeachingDashboard.vue` | const_fn | `fmt` | 127 | const fmt = (d) => { | 大页面 |
| `frontend/src/views/dashboard/TeachingDashboard.vue` | const_fn | `go` | 143 | const go = (route) => route && router.push(route) | 大页面 |
| `frontend/src/views/dashboard/TeachingDashboard.vue` | const_fn | `isEmpty` | 144 | const isEmpty = (items = [], field = 'value') => !items?.some(item => Number(item?.[field]) > 0) | 大页面 |
| `frontend/src/views/dashboard/TeachingDashboard.vue` | const_fn | `fetchSummary` | 226 | 获取/加载：fetchSummary | 大页面 |

## 后端 API

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/main.py` | class | `NumpyJSONResponse` | 38 | 处理 numpy 类型的 JSON 响应 | - |
| `lesson/main.py` | method | `NumpyJSONResponse.render` | 41 | 渲染：render | 缺少docstring |
| `lesson/main.py` | method | `NumpyJSONResponse._numpy_encoder` | 52 | method：NumpyJSONResponse._numpy_encoder | 缺少docstring |
| `lesson/main.py` | function | `_consume_queue_once` | 64 | function：_consume_queue_once | 缺少docstring |
| `lesson/main.py` | async_function | `consume_queue` | 69 | async_function：consume_queue | 缺少docstring |
| `lesson/main.py` | async_function | `lifespan` | 76 | async_function：lifespan | 缺少docstring |
| `lesson/main.py` | async_function | `https_redirect` | 118 | 处理 FastAPI 路由请求 | 路由、缺少docstring |
| `lesson/main.py` | async_function | `global_exception_handler` | 138 | 全局异常处理器 | 路由 |
| `lesson/main.py` | async_function | `websocket_route` | 153 | 处理路由 /ws | 路由、缺少docstring |
| `lesson/main.py` | async_function | `ws_status` | 158 | 处理路由 /api/ws/status | 路由、缺少docstring |
| `lesson/main.py` | async_function | `health_check` | 172 | 处理路由 /api/health | 路由、缺少docstring |
| `lesson/main.py` | async_function | `root` | 186 | 处理路由 / | 路由、缺少docstring |
| `lesson/main.py` | function | `trigger` | 214 | function：trigger | 缺少docstring |
| `lesson/main.py` | function | `ai_content` | 264 | 使用 LLM 将自然语言翻译为规则格式 从数据库读取 ai_flag=1 的规则，让 LLM 智能匹配并翻译 | - |
| `lesson/models/datas_api/admin.py` | class | `PasswordResetRequest` | 28 | 定义 PasswordResetRequest 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/admin.py` | class | `AdminSetPasswordRequest` | 32 | 管理员设置用户密码 | - |
| `lesson/models/datas_api/admin.py` | class | `PasswordChangeRequest` | 38 | 定义 PasswordChangeRequest 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/admin.py` | class | `ResetPasswordChangeRequest` | 43 | 重置：ResetPasswordChangeRequest | 缺少docstring |
| `lesson/models/datas_api/admin.py` | async_function | `list_users` | 50 | 获取所有用户列表（需要管理员权限） | 路由 |
| `lesson/models/datas_api/admin.py` | async_function | `admin_reset_password` | 69 | 管理员重置用户密码（生成随机密码） | 路由 |
| `lesson/models/datas_api/admin.py` | async_function | `admin_set_password` | 103 | 管理员为用户设置密码 | 路由 |
| `lesson/models/datas_api/admin.py` | async_function | `admin_reset_password_changed` | 133 | 管理员重置用户的密码修改状态为未修改（is_password_changed=0），使用明文验证 | 路由 |
| `lesson/models/datas_api/auth.py` | class | `Token` | 39 | 定义 Token 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/auth.py` | class | `TokenData` | 44 | 定义 TokenData 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/auth.py` | class | `User` | 48 | 定义 User 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/auth.py` | function | `hash_password` | 60 | 生成密码哈希 | - |
| `lesson/models/datas_api/auth.py` | function | `verify_password` | 65 | 验证密码 | - |
| `lesson/models/datas_api/auth.py` | function | `get_users_dict` | 73 | 从数据库获取用户数据 | - |
| `lesson/models/datas_api/auth.py` | function | `verify_password_compat` | 95 | 验证密码，根据 is_password_changed 决定验证方式 - is_password_changed=1: 使用 bcrypt 验证 - is_password_changed=0: 使用明文验证 | - |
| `lesson/models/datas_api/auth.py` | function | `get_password_hash` | 116 | 生成密码哈希 | - |
| `lesson/models/datas_api/auth.py` | function | `get_user` | 121 | 动态获取用户信息 | - |
| `lesson/models/datas_api/auth.py` | function | `authenticate_user` | 131 | 验证用户登录（从数据库） | - |
| `lesson/models/datas_api/auth.py` | function | `create_access_token` | 151 | 创建访问令牌 | - |
| `lesson/models/datas_api/auth.py` | async_function | `get_current_user` | 163 | 获取当前登录用户 | - |
| `lesson/models/datas_api/auth.py` | function | `is_admin_user` | 184 | 检查用户是否为管理员 | - |
| `lesson/models/datas_api/auth.py` | function | `get_current_active_user` | 195 | 获取当前活跃用户 | - |
| `lesson/models/datas_api/auth.py` | async_function | `login` | 206 | 用户登录接口 | 路由 |
| `lesson/models/datas_api/dashboard.py` | function | `_now_text` | 25 | function：_now_text | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_is_jiaowu` | 29 | function：_is_jiaowu | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_is_moral_manager` | 33 | function：_is_moral_manager | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_date_range` | 37 | function：_date_range | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_metric` | 44 | function：_metric | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_normalize_top_n` | 48 | function：_normalize_top_n | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_current_week_range` | 56 | function：_current_week_range | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_safe_count` | 62 | function：_safe_count | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_safe_query_all` | 69 | function：_safe_query_all | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_score_distribution` | 76 | function：_score_distribution | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_daily_event_mix` | 100 | function：_daily_event_mix | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_daily_record_trend` | 118 | function：_daily_record_trend | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_class_score_rank` | 137 | function：_class_score_rank | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_base_overview_cards` | 152 | function：_base_overview_cards | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | async_function | `get_dashboard_overview` | 186 | 当前用户数据驾驶舱总览 | 路由、缺少docstring |
| `lesson/models/datas_api/dashboard.py` | async_function | `get_moral_dashboard_summary` | 210 | 德育驾驶舱总览 | 路由、缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_schedule_frames_for_range` | 280 | function：_schedule_frames_for_range | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_teacher_lesson_counts` | 293 | function：_teacher_lesson_counts | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_month_keys_for_range` | 297 | function：_month_keys_for_range | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_week_start_from_schedule_filename` | 307 | function：_week_start_from_schedule_filename | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_schedule_files_for_range` | 319 | function：_schedule_files_for_range | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_format_week_schedule_file` | 343 | function：_format_week_schedule_file | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_teacher_lesson_counts_from_files` | 352 | function：_teacher_lesson_counts_from_files | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_minutes_from_time` | 434 | function：_minutes_from_time | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_find_current_period` | 442 | function：_find_current_period | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_teacher_subject_lookup` | 466 | function：_teacher_subject_lookup | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_current_course_snapshot` | 480 | function：_current_course_snapshot | 缺少docstring |
| `lesson/models/datas_api/dashboard.py` | async_function | `get_teaching_dashboard_summary` | 554 | 教务驾驶舱总览 | 路由、缺少docstring |
| `lesson/models/datas_api/dashboard.py` | function | `_get_homework_db` | 630 | 获取作业数据库连接 | - |
| `lesson/models/datas_api/dashboard.py` | function | `_get_inout_db` | 639 | 获取请假数据库连接 | - |
| `lesson/models/datas_api/dashboard.py` | async_function | `get_class_dashboard_summary` | 649 | 班级驾驶舱：班级基础、学习活动、德育表现、出勤事务、生日关怀 | 过长、路由 |
| `lesson/models/datas_api/dashboard.py` | async_function | `get_teacher_workbench` | 834 | 教师工作台：今日事项、发布内容、德育参与、监考任务 | 过长、路由 |
| `lesson/models/datas_api/dashboard.py` | function | `_get_invigilation_db` | 980 | 获取监考数据库连接 | - |
| `lesson/models/datas_api/dashboard.py` | async_function | `get_invigilation_dashboard_summary` | 990 | 监考驾驶舱：考试项目状态、安排完整度、通知状态、教师负载、预警列表 | 过长、路由 |
| `lesson/models/datas_api/dashboard.py` | function | `_get_db_stats` | 1203 | 获取数据库统计信息 | - |
| `lesson/models/datas_api/dashboard.py` | async_function | `get_system_dashboard_summary` | 1226 | 系统运维驾驶舱：服务状态、数据库统计、用户权限、操作审计 | 过长、路由 |
| `lesson/models/datas_api/filegather.py` | function | `is_jiaowu_user` | 35 | 检查是否为教务角色 Args: user: 用户对象 Returns: 是否为教务或管理员 | - |
| `lesson/models/datas_api/filegather.py` | class | `MarkDoneRequest` | 54 | 标记完成请求 | - |
| `lesson/models/datas_api/filegather.py` | class | `DeleteRequest` | 59 | 删除请求 | - |
| `lesson/models/datas_api/filegather.py` | async_function | `upload_file` | 67 | 上传文件 - **file**: 要上传的文件 - **copies**: 打印份数 - **use_date**: 使用日期 (YYYY-MM-DD) - **note**: 备注 (可选) | 路由 |
| `lesson/models/datas_api/filegather.py` | async_function | `get_my_files` | 167 | 获取我的文件列表 - **month**: 月份筛选 (YYYYMM格式，可选) | 路由 |
| `lesson/models/datas_api/filegather.py` | async_function | `delete_my_file` | 183 | 删除文件 - **file_id**: 文件ID | 路由 |
| `lesson/models/datas_api/filegather.py` | async_function | `admin_get_pending_files` | 205 | 获取待处理文件列表（需要教务或管理员权限） | 路由 |
| `lesson/models/datas_api/filegather.py` | async_function | `admin_get_done_files` | 220 | 获取已完成文件列表（需要教务或管理员权限） - **month**: 月份筛选 (YYYYMM格式，可选) | 路由 |
| `lesson/models/datas_api/filegather.py` | async_function | `admin_mark_done` | 241 | 标记文件为已完成（需要教务或管理员权限） - **file_id**: 文件ID | 路由 |
| `lesson/models/datas_api/filegather.py` | async_function | `admin_download_file` | 296 | 下载文件（需要教务或管理员权限） - **file_id**: 文件ID | 路由 |
| `lesson/models/datas_api/filegather.py` | async_function | `admin_get_statistics` | 334 | 获取统计信息（需要教务或管理员权限） - **month**: 月份筛选 (YYYYMM格式，可选) | 路由 |
| `lesson/models/datas_api/filegather.py` | async_function | `admin_get_months` | 354 | 获取月份列表（需要教务或管理员权限） | 路由 |
| `lesson/models/datas_api/invigilation.py` | class | `ExamProjectCreate` | 37 | 创建考试项目 | - |
| `lesson/models/datas_api/invigilation.py` | class | `ExamProjectUpdate` | 47 | 更新考试项目 | - |
| `lesson/models/datas_api/invigilation.py` | class | `InvigilationSlotCreate` | 57 | 创建监考安排 | - |
| `lesson/models/datas_api/invigilation.py` | class | `InvigilationSlotsBatch` | 71 | 批量保存监考安排 | - |
| `lesson/models/datas_api/invigilation.py` | class | `NotifyRequest` | 76 | 发送通知请求 | - |
| `lesson/models/datas_api/invigilation.py` | class | `NotifyRequestV2` | 83 | 发送通知请求V2 - 支持学科筛选 | - |
| `lesson/models/datas_api/invigilation.py` | function | `get_invigilation_db` | 96 | 获取监考安排数据库连接 | - |
| `lesson/models/datas_api/invigilation.py` | function | `require_jiaowu` | 103 | 检查教务权限 | - |
| `lesson/models/datas_api/invigilation.py` | async_function | `get_teachers_for_invigilation` | 115 | 获取教师列表用于监考安排 | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `get_exam_projects` | 132 | 获取考试项目列表 | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `create_exam_project` | 162 | 创建考试项目 | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `get_exam_project` | 193 | 获取考试项目详情 | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `update_exam_project` | 232 | 更新考试项目基础信息 | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `delete_exam_project` | 286 | 删除考试项目及相关数据（真删除） | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `get_invigilation_slots` | 318 | 获取项目的监考安排列表 | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `save_invigilation_slots` | 358 | 批量保存监考安排（覆盖模式） | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `swap_teachers` | 432 | 交换两条安排的监考老师 | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `get_changes_preview` | 476 | 获取监考安排变更预览（对比上次通知版本） | 过长、路由 |
| `lesson/models/datas_api/invigilation.py` | function | `get_key` | 515 | 获取：get_key | 缺少docstring |
| `lesson/models/datas_api/invigilation.py` | async_function | `send_notifications` | 679 | 发送监考通知给老师（支持学科筛选和变更检测） | 过长、路由 |
| `lesson/models/datas_api/invigilation.py` | function | `get_key` | 722 | 获取：get_key | 缺少docstring |
| `lesson/models/datas_api/invigilation.py` | function | `format_slot` | 847 | 格式化：format_slot | 缺少docstring |
| `lesson/models/datas_api/invigilation.py` | function | `send_and_log` | 850 | 发送：send_and_log | 缺少docstring |
| `lesson/models/datas_api/invigilation.py` | async_function | `get_notification_logs` | 1001 | 获取项目的通知日志 | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `download_template` | 1025 | 下载监考安排导入模板（横向布局） | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `import_invigilation` | 1057 | 导入监考安排 Excel | 过长、路由 |
| `lesson/models/datas_api/invigilation.py` | function | `parse_session` | 1108 | 解析场次字符串，如 '第一场(08:00-10:00)' | - |
| `lesson/models/datas_api/invigilation.py` | async_function | `export_invigilation` | 1300 | 导出监考安排 Excel（横向布局，同一学科不同考场横向排列） | 路由 |
| `lesson/models/datas_api/invigilation.py` | async_function | `export_workload_report` | 1401 | 导出监考工作量报表 报表内容： - Sheet1: 教师工作量汇总（场次数、监考时长） - Sheet2: 按年级细化统计 | 过长、路由 |
| `lesson/models/datas_api/teachers.py` | class | `TeacherCreate` | 33 | 定义 TeacherCreate 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/teachers.py` | class | `TeacherUpdate` | 43 | 定义 TeacherUpdate 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/teachers.py` | class | `PasswordChangeRequest` | 61 | 定义 PasswordChangeRequest 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/teachers.py` | class | `TeachingClassItem` | 66 | 定义 TeachingClassItem 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/teachers.py` | class | `TeachingClassUpdate` | 71 | 定义 TeachingClassUpdate 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/datas_api/teachers.py` | function | `_ensure_teaching_class_table` | 75 | function：_ensure_teaching_class_table | 缺少docstring |
| `lesson/models/datas_api/teachers.py` | async_function | `get_teachers` | 96 | 获取教师列表。默认只返回可登录系统的正式教师。 | 路由 |
| `lesson/models/datas_api/teachers.py` | async_function | `create_teacher` | 143 | 创建新教师（需要管理员权限） | 路由 |
| `lesson/models/datas_api/teachers.py` | async_function | `update_teacher` | 179 | 更新教师信息 | 路由 |
| `lesson/models/datas_api/teachers.py` | async_function | `delete_teacher` | 222 | 删除教师 | 路由 |
| `lesson/models/datas_api/teachers.py` | async_function | `get_teacher_teaching_classes` | 246 | 获取教师任教班级关系（管理员维护权限）。 | 路由 |
| `lesson/models/datas_api/teachers.py` | async_function | `update_teacher_teaching_classes` | 281 | 全量更新教师任教班级关系。 | 路由 |
| `lesson/models/datas_api/teachers.py` | async_function | `init_all_teaching_classes` | 332 | 根据最近一个月的课表数据，批量更新所有教师的任教班级。 管理员权限：基于 lesson.yaml 中课表数据，提取每个教师涉及的班级作为任教班级。 已有任教班级记录的教师会被覆盖更新。 | 过长、路由 |
| `lesson/models/datas_api/teachers.py` | async_function | `teacher_change_password` | 509 | 教师修改自己的密码 | 路由 |
| `lesson/models/datas_api/utils.py` | function | `refresh_teacher_cache` | 20 | 刷新教师相关缓存 | - |
| `lesson/models/datas_api/utils.py` | function | `refresh_schedule_cache` | 31 | 细粒度刷新课程表缓存 Args: class_name: 指定班级名称，如果为 None 则刷新所有课程表缓存 | - |
| `lesson/models/datas_api/utils.py` | function | `backup_excel_file` | 49 | 备份 Excel 文件 | - |
| `lesson/models/datas_api/utils.py` | function | `get_schedule_data` | 70 | 获取课程表数据 | - |
| `lesson/models/datas_api/utils.py` | function | `get_teacher_data` | 88 | 获取教师数据 | - |
| `lesson/models/datas_api/utils.py` | function | `get_time_table` | 102 | 获取作息时间表 | - |
| `lesson/models/datas_api_legacy.py` | function | `refresh_teacher_cache` | 45 | 刷新教师相关缓存 | legacy |
| `lesson/models/datas_api_legacy.py` | function | `backup_excel_file` | 55 | 备份 Excel 文件 | legacy |
| `lesson/models/datas_api_legacy.py` | function | `get_schedule_data` | 64 | 获取：get_schedule_data | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `get_teacher_data` | 88 | 获取：get_teacher_data | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `get_time_table` | 101 | 获取：get_time_table | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `hash_password` | 152 | 生成密码哈希 | legacy |
| `lesson/models/datas_api_legacy.py` | function | `verify_password` | 156 | 验证密码 | legacy |
| `lesson/models/datas_api_legacy.py` | function | `get_users_dict` | 163 | 动态获取用户数据，支持缓存刷新 | legacy |
| `lesson/models/datas_api_legacy.py` | class | `Token` | 260 | 定义 Token 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `TokenData` | 265 | 定义 TokenData 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `User` | 269 | 定义 User 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `verify_password_compat` | 278 | 验证密码，根据 is_password_changed 决定验证方式 - is_password_changed=1: 使用 bcrypt 验证 - is_password_changed=0: 使用明文验证 | legacy |
| `lesson/models/datas_api_legacy.py` | function | `get_password_hash` | 301 | 生成密码哈希 | legacy |
| `lesson/models/datas_api_legacy.py` | function | `get_user` | 306 | 动态获取用户信息 | legacy |
| `lesson/models/datas_api_legacy.py` | function | `authenticate_user` | 317 | function：authenticate_user | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `create_access_token` | 335 | 创建：create_access_token | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_current_user` | 346 | 获取：get_current_user | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `PasswordResetRequest` | 374 | 定义 PasswordResetRequest 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `TeacherCreate` | 380 | 定义 TeacherCreate 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `TeacherUpdate` | 390 | 定义 TeacherUpdate 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `PasswordChangeRequest` | 398 | 定义 PasswordChangeRequest 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `is_admin_user` | 403 | 检查用户是否为管理员 | legacy |
| `lesson/models/datas_api_legacy.py` | function | `_match_route` | 431 | function：_match_route | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `_get_api_rule` | 444 | function：_get_api_rule | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `check_api_permission` | 460 | 检查：check_api_permission | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_class_codes` | 500 | 获取所有可用的班级代码 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_class_schedule` | 534 | 获取指定班级的课程表 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_todays_schedule` | 551 | 获取指定日期的课程，默认今日 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | function | `get_schedule_for_date` | 561 | 获取：get_schedule_for_date | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `NpEncoder` | 596 | 定义 NpEncoder 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | method | `NpEncoder.default` | 597 | method：NpEncoder.default | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_schedules` | 624 | 获取课表数据 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | function | `replace_url` | 630 | function：replace_url | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_homework` | 643 | 获取作业列表，按类型分类，按学科和老师分组 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_class_announcements` | 664 | 获取指定班级的公告 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `HomeworkForm` | 672 | 定义 HomeworkForm 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `create_homework` | 683 | 发布作业（需要登录） | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `HomeworkIds` | 731 | 定义 HomeworkIds 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `delete_homework_batch` | 737 | 批量删除作业 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `AnnouncementForm` | 770 | 定义 AnnouncementForm 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `create_announcement` | 778 | 发布公告 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `HomeworkUpdateForm` | 797 | 定义 HomeworkUpdateForm 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `update_homework` | 806 | 修改作业 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `delete_homework` | 843 | 删除作业 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `AnnouncementUpdateForm` | 871 | 定义 AnnouncementUpdateForm 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `update_announcement` | 877 | 修改公告 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `delete_announcement` | 906 | 删除公告 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_teacher_messages` | 931 | 获取指定班级的老师留言 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_class_info` | 939 | 获取指定班级的基本信息 - 数据源改为德育系统 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_students` | 981 | 获取指定班级的学生名单 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `export_students_excel` | 990 | 导出班级学生 Excel | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `import_students_excel` | 1020 | 导入学生 Excel | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_periods` | 1047 | 获取课程时间安排 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_current_classes` | 1053 | 获取当前所有班级正在上的课程 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_teacher_schedule` | 1114 | 获取指定教师的课表 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_teacher_schedule_nextweek` | 1147 | 获取指定教师的课表 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_vehicle_inout` | 1184 | 获取所有车辆进出记录 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_students_status` | 1191 | 获取所有学生状态 - 数据源改为德育系统 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `StudentInfoRequest` | 1247 | 定义 StudentInfoRequest 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `get_stu_dict` | 1251 | 获取：get_stu_dict | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `safe_int_str` | 1255 | function：safe_int_str | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_student_info` | 1278 | 获取指定学生信息 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `insert_delay` | 1290 | 插入学生延迟 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_delay_infos` | 1300 | 获取所有学生延迟 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `del_delay` | 1325 | 删除学生延时记录 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `LeaveRecordRequest` | 1354 | 定义 LeaveRecordRequest 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `_user_has_role` | 1361 | function：_user_has_role | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `_user_has_any_role` | 1366 | function：_user_has_any_role | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `_user_has_admin_role` | 1372 | 检查用户是否有管理员角色（包括 admin、管理员） | legacy |
| `lesson/models/datas_api_legacy.py` | function | `_ensure_leave_permission` | 1379 | function：_ensure_leave_permission | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `_can_manage_all_classes` | 1383 | function：_can_manage_all_classes | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `_get_cleader_class_rows` | 1386 | function：_get_cleader_class_rows | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `_resolve_class_row` | 1396 | function：_resolve_class_row | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_cleader_classes` | 1409 | 处理路由 /cleader-classes/ | 路由、legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `insert_leave_records` | 1447 | 提交请假记录 | 路由、legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_leave_records` | 1485 | 处理路由 /leave-records/ | 路由、legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `consume_leave_record` | 1561 | 处理路由 /leave-records/{record_id}/consume | 路由、legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `DailyInfoRequest` | 1596 | 定义 DailyInfoRequest 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `insert_daily` | 1609 | 插入学生日常 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `_get_dailies_data` | 1635 | async_function：_get_dailies_data | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `upload_schedule` | 1715 | 上传课表文件并触发自动更新 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_dailies` | 1758 | 获取日常记录 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `export_dailies` | 1779 | 导出日常记录 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `MemberCreate` | 1832 | 定义 MemberCreate 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `MemberUpdate` | 1845 | 定义 MemberUpdate 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `PermissionCreate` | 1855 | 定义 PermissionCreate 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `PermissionUpdate` | 1876 | 定义 PermissionUpdate 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_members` | 1901 | 获取会员列表 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `create_member` | 1942 | 创建会员 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `update_member` | 1973 | 更新会员信息 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `delete_member` | 1995 | 删除会员 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_permissions` | 2013 | 获取权限列表 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `create_permission` | 2066 | 创建权限 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `update_permission` | 2101 | 更新权限信息 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `delete_permission` | 2123 | 删除权限 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | class | `TaskCreate` | 2143 | 定义 TaskCreate 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | class | `TaskUpdate` | 2154 | 定义 TaskUpdate 类，承载相关状态和方法 | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | function | `get_tasks_connection` | 2166 | 获取：get_tasks_connection | legacy、缺少docstring |
| `lesson/models/datas_api_legacy.py` | async_function | `get_available_funcs` | 2177 | 获取可用的任务函数列表 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `get_tasks` | 2186 | 获取任务列表 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `create_task` | 2263 | 创建任务 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `update_task` | 2294 | 更新任务 | 路由、legacy |
| `lesson/models/datas_api_legacy.py` | async_function | `delete_task` | 2354 | 删除任务 | 路由、legacy |
| `lesson/websocket.py` | class | `ConnectionManager` | 13 | WebSocket 连接管理器 | - |
| `lesson/websocket.py` | method | `ConnectionManager.__init__` | 16 | ConnectionManager.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/websocket.py` | async_method | `ConnectionManager.connect` | 24 | 接受 WebSocket 连接 | - |
| `lesson/websocket.py` | method | `ConnectionManager.disconnect` | 37 | 断开 WebSocket 连接 | - |
| `lesson/websocket.py` | async_method | `ConnectionManager.send_personal_message` | 51 | 发送个人消息 | - |
| `lesson/websocket.py` | async_method | `ConnectionManager.broadcast` | 61 | 广播消息 | - |
| `lesson/websocket.py` | async_method | `ConnectionManager.send_json` | 88 | 发送 JSON 消息 | - |
| `lesson/websocket.py` | method | `ConnectionManager.get_connection_count` | 95 | 获取活跃连接数 | - |
| `lesson/websocket.py` | method | `ConnectionManager.get_user_count` | 99 | 获取用户数 | - |
| `lesson/websocket.py` | async_function | `websocket_endpoint` | 108 | WebSocket 端点 | - |
| `lesson/websocket.py` | async_function | `notify_homework_update` | 176 | 通知作业更新 | - |
| `lesson/websocket.py` | async_function | `notify_schedule_update` | 186 | 通知课表更新 | - |

## 后端 API - 德育

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/models/datas_api/moral/__init__.py` | async_function | `get_punishment_types_direct` | 69 | 获取处罚类型列表（用于前端下拉框） 无需权限验证（前端展示需要） | 路由 |
| `lesson/models/datas_api/moral/admin.py` | function | `_has_scoped_permission` | 42 | function：_has_scoped_permission | 缺少docstring |
| `lesson/models/datas_api/moral/admin.py` | function | `_has_scoped_any_permission` | 47 | function：_has_scoped_any_permission | 缺少docstring |
| `lesson/models/datas_api/moral/admin.py` | function | `_student_manage_scope` | 52 | function：_student_manage_scope | 缺少docstring |
| `lesson/models/datas_api/moral/admin.py` | class | `GradeCreate` | 67 | 创建级号 | - |
| `lesson/models/datas_api/moral/admin.py` | class | `ClassCreate` | 73 | 创建班级 | - |
| `lesson/models/datas_api/moral/admin.py` | class | `ClassUpdate` | 84 | 更新班级 | - |
| `lesson/models/datas_api/moral/admin.py` | class | `StudentCreate` | 98 | 创建学生 | - |
| `lesson/models/datas_api/moral/admin.py` | class | `StudentBatchItem` | 107 | 批量导入学生单项 | - |
| `lesson/models/datas_api/moral/admin.py` | class | `StudentBatchImport` | 116 | 批量导入学生 | - |
| `lesson/models/datas_api/moral/admin.py` | class | `StudentUpdate` | 121 | 更新学生信息 | - |
| `lesson/models/datas_api/moral/admin.py` | class | `SchoolYearCreate` | 131 | 创建学年 | - |
| `lesson/models/datas_api/moral/admin.py` | class | `SemesterCreate` | 137 | 创建学期 | - |
| `lesson/models/datas_api/moral/admin.py` | async_function | `get_grades` | 151 | 获取级号列表 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `create_grade` | 164 | 创建级号 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `delete_grade` | 196 | 删除级号 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `get_classes` | 226 | 获取班级列表 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `create_class` | 260 | 创建班级 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `update_class` | 295 | 更新班级 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `delete_class` | 354 | 删除班级 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `get_school_years` | 384 | 获取学年列表 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `create_school_year` | 398 | 创建学年 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `get_semesters` | 428 | 获取学期列表 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `create_semester` | 464 | 创建学期 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `set_current_semester` | 499 | 设置当前学期 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `get_students` | 545 | 获取学生列表 权限说明： - admin/jiaowu/xuefa: 可查看所有学生 - cleader: 只能查看自己班级的学生 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | function | `check_student_manage_permission` | 644 | 学生管理权限检查 允许有 student_manage 或 student_manage_own_class 权限的用户访问 | - |
| `lesson/models/datas_api/moral/admin.py` | async_function | `check` | 650 | 检查：check | 缺少docstring |
| `lesson/models/datas_api/moral/admin.py` | async_function | `create_student` | 665 | 创建学生 权限说明： - admin/jiaowu/xuefa (student_manage): 可创建任意班级学生 - cleader (student_manage_own_class): 只能创建自己班级的学生 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `batch_import_students` | 739 | 批量导入学生 通过班级名称匹配班级ID，支持大量学生快速导入。 权限说明： - admin/jiaowu/xuefa (student_manage): 可导入任意班级学生 - cleader (student_manage_own_cla | 过长、路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `update_student` | 849 | 更新学生基本信息 权限说明： - admin/jiaowu/xuefa (student_manage): 可编辑所有学生 - cleader (student_manage_own_class): 只能编辑自己班级的学生 - teache | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `update_student_status` | 939 | 更新学生状态 | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `get_operation_logs` | 985 | 获取操作日志列表 权限要求：admin/jiaowu/xuefa | 路由 |
| `lesson/models/datas_api/moral/admin.py` | async_function | `get_system_config` | 1079 | 获取系统配置 权限要求：admin/jiaowu/xuefa | 路由 |
| `lesson/models/datas_api/moral/admin.py` | class | `ConfigUpdate` | 1111 | 更新系统配置 | - |
| `lesson/models/datas_api/moral/admin.py` | async_function | `update_system_config` | 1121 | 更新系统配置 权限要求：admin/jiaowu | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | class | `ApiPermissionCreate` | 36 | 创建API权限配置 | - |
| `lesson/models/datas_api/moral/api_permission.py` | class | `ApiPermissionUpdate` | 55 | 更新API权限配置 | - |
| `lesson/models/datas_api/moral/api_permission.py` | class | `ApiPermissionModuleCreate` | 74 | 创建API权限模块 | - |
| `lesson/models/datas_api/moral/api_permission.py` | class | `ApiPermissionModuleUpdate` | 86 | 更新API权限模块 | - |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_json_list` | 286 | function：_json_list | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_json_dump` | 298 | function：_json_dump | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_json_dict` | 302 | function：_json_dict | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_json_dict_dump` | 324 | function：_json_dict_dump | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_normalize_policy_mode` | 328 | function：_normalize_policy_mode | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_normalize_match_type` | 332 | function：_normalize_match_type | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_table_columns` | 336 | function：_table_columns | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `ensure_api_permission_schema` | 341 | 兼容式补齐API权限模块表和扩展列。 | - |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_backfill_default_scope_rules` | 423 | 为重点业务API补齐默认数据范围规则，保留管理员已有手工配置。 | - |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_module_key_from_group` | 443 | function：_module_key_from_group | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_dedupe_permission_modules` | 451 | 按模块名称合并历史自动生成的重复模块。 | - |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_roles_for_group` | 474 | function：_roles_for_group | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_ensure_module` | 485 | function：_ensure_module | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_sync_legacy_api_level_yaml` | 508 | 将 lesson/config/api_level.yaml 同步到数据库权限配置。 | - |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_path_matches` | 575 | function：_path_matches | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_get_matching_config` | 588 | function：_get_matching_config | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_effective_policy` | 614 | function：_effective_policy | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `is_api_allowed` | 637 | 按统一语义判断API权限。默认角色和等级同时生效。 | - |
| `lesson/models/datas_api/moral/api_permission.py` | function | `check_configured_api_permission` | 670 | 使用 api_permission_config 做后端统一鉴权。 allow_missing=True 时，未配置的 API 仍回退到原有代码内权限判断； 已配置且 enforce_backend=1 的 API 必须满足配置中的角色、等 | - |
| `lesson/models/datas_api/moral/api_permission.py` | function | `require_configured_api_permission` | 707 | FastAPI 依赖：按 api_permission_config 校验当前用户能否调用 API。 | - |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `check` | 714 | 检查：check | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `_parse_config_row` | 728 | function：_parse_config_row | 缺少docstring |
| `lesson/models/datas_api/moral/api_permission.py` | function | `require_admin` | 742 | 仅admin可访问 | - |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `get_api_permissions` | 750 | 获取API权限配置列表（仅admin） | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `get_api_permission_modules` | 785 | 获取API权限模块列表（仅admin） | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `create_api_permission_module` | 803 | 创建API权限模块（仅admin） | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `update_api_permission_module` | 839 | 更新API权限模块（仅admin） | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `apply_module_permission` | 875 | 将模块权限批量写入模块下API，并取消单API覆盖。 | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `sync_legacy_yaml_permissions` | 905 | 将 lesson/config/api_level.yaml 导入统一API权限配置（仅admin）。 | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `create_api_permission` | 922 | 创建API权限配置（仅admin） | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `update_api_permission` | 983 | 更新API权限配置（仅admin） | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `delete_api_permission` | 1083 | 删除API权限配置（仅admin） | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `get_my_api_permissions` | 1111 | 获取当前用户可访问的API列表 | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `check_api_permission_endpoint` | 1145 | 检查用户对特定API的权限 | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `init_api_permissions` | 1171 | 初始化默认API权限配置（仅admin） | 路由 |
| `lesson/models/datas_api/moral/api_permission.py` | async_function | `get_api_groups` | 1253 | 获取API分组列表 | 路由 |
| `lesson/models/datas_api/moral/base.py` | function | `get_moral_db` | 140 | 获取德育数据库连接的上下文管理器（SQLite） 使用方式: with get_moral_db() as db: result = db.query_all("SELECT * FROM student") | - |
| `lesson/models/datas_api/moral/base.py` | class | `MoralDB` | 152 | 德育数据库操作便捷类（SQLite） | - |
| `lesson/models/datas_api/moral/base.py` | method | `MoralDB.__init__` | 155 | MoralDB.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/datas_api/moral/base.py` | method | `MoralDB.__enter__` | 158 | MoralDB.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/datas_api/moral/base.py` | method | `MoralDB.__exit__` | 163 | MoralDB.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/datas_api/moral/base.py` | function | `get_user_role_level` | 171 | 获取用户角色等级 优先读取 teacher 表中的实际等级字段， 如果未配置则回退到角色预设等级。 Args: user: 用户对象 Returns: int: 角色等级 | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_user_roles` | 213 | 获取用户角色列表，兼容 teacher/xuefa 这类多角色格式。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `has_user_role` | 222 | 检查用户是否包含指定角色。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `check_moral_permission` | 227 | 检查用户是否有指定权限 Args: user: 用户对象 permission: 权限名称 Returns: bool: 是否有权限 | - |
| `lesson/models/datas_api/moral/base.py` | function | `check_moral_permission_for_roles` | 263 | 按指定角色集合检查权限，用于多角色用户在某个API下的业务范围收敛。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `check_any_moral_permission_for_roles` | 273 | 按指定角色集合检查任一权限。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_api_scoped_user_roles` | 278 | 获取用户在指定API配置下实际生效的角色。 多角色用户只保留该API允许的角色，避免“API只允许教师访问， 但用户同时有教发部身份，于是业务数据范围被提升”的问题。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_scoped_role_permissions` | 314 | 返回用户在某个API配置下收敛后的角色和权限判断器。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_record_data_scope` | 324 | 计算记录类数据范围。 all: 全部记录 own_class: 当前班主任班级学生的记录 teaching_classes: 当前教师任教班级学生的记录；未维护任教班级时默认全校 own: 当前用户自己创建的记录 | - |
| `lesson/models/datas_api/moral/base.py` | function | `_get_configured_data_scope` | 379 | 读取 API 权限配置中的角色数据范围规则。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `append_record_scope_condition` | 426 | 把记录范围转换为 SQL 条件。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `record_in_scope` | 462 | 判断单条记录是否在数据范围内。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `record_action_flags` | 487 | 生成前端行级操作能力。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `target_student_in_scope` | 516 | 判断创建/录入接口是否允许选择目标学生。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `check_class_access` | 561 | 检查用户是否有班级访问权限 Args: user: 用户对象 class_id: 班级ID db: 数据库连接 Returns: bool: 是否有权限 | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_teacher_class_id` | 611 | 获取班主任管理的班级ID Args: user: 用户对象 db: 数据库连接 Returns: 班级ID，如果不是班主任或未关联班级则返回 None | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_teacher_teaching_class_ids` | 661 | 获取教师任教班级ID列表。 依赖 teacher_teaching_class 映射表。没有维护映射时返回空列表； teaching_classes 范围会把空列表解释为全校班级。 | - |
| `lesson/models/datas_api/moral/base.py` | function | `require_permission` | 702 | 权限检查装饰器工厂函数 Args: permission: 需要的权限名称 Returns: 依赖函数 | - |
| `lesson/models/datas_api/moral/base.py` | async_function | `check` | 712 | 检查：check | 缺少docstring |
| `lesson/models/datas_api/moral/base.py` | function | `require_role_level` | 740 | 角色等级检查装饰器工厂函数 Args: min_level: 最低角色等级 Returns: 依赖函数 | - |
| `lesson/models/datas_api/moral/base.py` | async_function | `check` | 750 | 检查：check | 缺少docstring |
| `lesson/models/datas_api/moral/base.py` | function | `get_current_school_year` | 765 | 获取当前学年 Args: db: 数据库连接 Returns: 当前学年信息，包含 year_id, year_name 等 | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_next_school_year` | 780 | 获取下一个学年 Args: db: 数据库连接 current_year_id: 当前学年ID Returns: 下一个学年信息，如果不存在则返回None | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_current_semester` | 797 | 获取当前学期 Args: db: 数据库连接 Returns: 当前学期信息，包含 semester_id, semester_name 等 | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_or_create_current_semester` | 812 | 获取或创建当前学期 如果不存在当前学期，自动创建 Args: db: 数据库连接 Returns: 当前学期信息 | - |
| `lesson/models/datas_api/moral/base.py` | class | `BaseResponse` | 865 | 基础响应模型 | - |
| `lesson/models/datas_api/moral/base.py` | class | `PaginationParams` | 871 | 分页参数 | - |
| `lesson/models/datas_api/moral/base.py` | method | `PaginationParams.offset` | 877 | method：PaginationParams.offset | 缺少docstring |
| `lesson/models/datas_api/moral/base.py` | class | `PaginatedResponse` | 881 | 分页响应模型 | - |
| `lesson/models/datas_api/moral/base.py` | function | `calculate_moral_level` | 894 | 根据分数计算德育等级 Args: score: 德育总分 Returns: 等级：优秀/良好/合格/不合格 | - |
| `lesson/models/datas_api/moral/base.py` | function | `get_student_class_snapshot` | 914 | 获取学生当前班级信息快照 Args: db: 数据库连接 student_id: 学号 Returns: 包含 class_id, grade_id 的字典 | - |
| `lesson/models/datas_api/moral/base.py` | function | `log_operation` | 932 | 记录操作日志 Args: db: 数据库连接 operator: 操作人 operator_role: 操作人角色 operation: 操作类型 table_name: 表名 record_id: 记录ID semester_id: 学期 | - |
| `lesson/models/datas_api/moral/birthday.py` | class | `BlessingSend` | 34 | 发送祝福请求 | - |
| `lesson/models/datas_api/moral/birthday.py` | class | `BirthdayConfigUpdate` | 40 | 更新生日提醒配置 | - |
| `lesson/models/datas_api/moral/birthday.py` | async_function | `get_upcoming_birthdays` | 58 | 获取即将到来的生日列表 权限说明： - teacher/cleader: 查看本班 - xuefa/jiaowu/admin: 查看所有，支持班级筛选 | 路由 |
| `lesson/models/datas_api/moral/birthday.py` | async_function | `get_today_birthdays` | 139 | 获取今日过生日的学生 权限说明： - teacher/cleader: 只能查看本班学生 - jiaowu/xuefa/admin: 可查看所有 | 路由 |
| `lesson/models/datas_api/moral/carryover.py` | function | `execute_task_carryover` | 31 | 执行学年末任务结转 Args: db: 数据库连接 from_year_id: 结转源学年ID（即将结束的学年） to_year_id: 结转目标学年ID（即将开始的学年） Returns: Dict: 结转结果统计 | 过长 |
| `lesson/models/datas_api/moral/carryover.py` | function | `get_next_school_year` | 159 | 获取下一个学年 Args: db: 数据库连接 current_year_id: 当前学年ID Returns: Dict: 下一个学年信息，若无则返回None | - |
| `lesson/models/datas_api/moral/carryover.py` | function | `manual_carryover_trigger` | 188 | 手动触发任务结转（用于API调用） Args: from_year_id: 源学年ID to_year_id: 目标学年ID operator: 操作者 Returns: Dict: 结转结果 | - |
| `lesson/models/datas_api/moral/carryover.py` | class | `CarryoverRequest` | 244 | 结转请求 | - |
| `lesson/models/datas_api/moral/carryover.py` | async_function | `api_execute_carryover` | 251 | 手动执行任务结转 权限要求：admin/jiaowu 流程： 1. 查询源学年所有未完成任务 2. 检查结转次数（超过2次的作废） 3. 计算新分值（×60%） 4. 更新任务所属学年 5. 记录结转日志 | 路由 |
| `lesson/models/datas_api/moral/carryover.py` | async_function | `api_preview_carryover` | 289 | 预览某学年待结转任务情况 返回： - 未完成任务列表 - 各任务的当前分值和结转后分值 - 将作废的任务列表 | 路由 |
| `lesson/models/datas_api/moral/carryover.py` | async_function | `api_get_carryover_logs` | 378 | 获取任务结转日志列表 | 路由 |
| `lesson/models/datas_api/moral/collective.py` | class | `CollectiveEventCreate` | 44 | 创建集体事件 | - |
| `lesson/models/datas_api/moral/collective.py` | class | `CollectiveEventUpdate` | 54 | 更新集体事件 | - |
| `lesson/models/datas_api/moral/collective.py` | class | `DistributionUpdate` | 63 | 更新分配记录 | - |
| `lesson/models/datas_api/moral/collective.py` | function | `ensure_collective_class_access` | 70 | 校验集体事件班级访问范围。 | - |
| `lesson/models/datas_api/moral/collective.py` | async_function | `get_collective_events` | 89 | 获取集体事件列表 权限说明： - admin/jiaowu/xuefa: 可查看所有 - cleader: 只能查看本班 | 路由 |
| `lesson/models/datas_api/moral/collective.py` | async_function | `create_collective_event` | 163 | 创建集体事件并自动分配给班级学生 流程： 1. 创建集体事件记录 2. 获取班级所有在校学生 3. 自动为每个学生分配分数 | 路由 |
| `lesson/models/datas_api/moral/collective.py` | async_function | `get_collective_event` | 254 | 获取集体事件详情，包含分配列表 | 路由 |
| `lesson/models/datas_api/moral/collective.py` | async_function | `update_collective_event` | 290 | 更新集体事件基本信息 | 路由 |
| `lesson/models/datas_api/moral/collective.py` | async_function | `delete_collective_event` | 373 | 删除集体事件及其分配记录 | 路由 |
| `lesson/models/datas_api/moral/collective.py` | async_function | `get_distributions` | 433 | 获取集体事件的学生分配列表 | 路由 |
| `lesson/models/datas_api/moral/collective.py` | async_function | `update_distribution` | 463 | 更新单个学生的分配记录 用例：学生未参与集体活动，标记不加分 | 路由 |
| `lesson/models/datas_api/moral/collective.py` | async_function | `get_student_collective_score` | 531 | 获取学生在某学期的集体事件得分汇总 | 路由 |
| `lesson/models/datas_api/moral/consultation.py` | class | `ConsultationCreate` | 34 | 创建诊疗会话 | - |
| `lesson/models/datas_api/moral/consultation.py` | class | `ConsultationUpdate` | 43 | 更新诊疗会话 | - |
| `lesson/models/datas_api/moral/consultation.py` | class | `MessageCreate` | 55 | 创建消息 | - |
| `lesson/models/datas_api/moral/consultation.py` | async_function | `get_consultations` | 66 | 获取诊疗会话列表 权限说明： - cleader: 查看本班学生 - xuefa/jiaowu/admin: 查看所有 | 路由 |
| `lesson/models/datas_api/moral/consultation.py` | async_function | `create_consultation` | 136 | 创建诊疗会话 | 路由 |
| `lesson/models/datas_api/moral/consultation.py` | async_function | `get_consultation` | 194 | 获取诊疗会话详情 | 路由 |
| `lesson/models/datas_api/moral/consultation.py` | async_function | `update_consultation` | 229 | 更新诊疗会话 | 路由 |
| `lesson/models/datas_api/moral/consultation.py` | async_function | `add_consultation_message` | 295 | 添加诊疗消息 | 路由 |
| `lesson/models/datas_api/moral/consultation.py` | async_function | `close_consultation` | 333 | 关闭诊疗会话 | 路由 |
| `lesson/models/datas_api/moral/consultation.py` | function | `generate_initial_analysis` | 365 | 生成初始AI分析 | - |
| `lesson/models/datas_api/moral/consultation.py` | function | `generate_ai_reply` | 391 | 生成AI回复 | - |
| `lesson/models/datas_api/moral/daily_record.py` | function | `_has_scoped_permission` | 53 | function：_has_scoped_permission | 缺少docstring |
| `lesson/models/datas_api/moral/daily_record.py` | function | `_has_scoped_any_permission` | 58 | function：_has_scoped_any_permission | 缺少docstring |
| `lesson/models/datas_api/moral/daily_record.py` | function | `_daily_view_scope` | 68 | function：_daily_view_scope | 缺少docstring |
| `lesson/models/datas_api/moral/daily_record.py` | function | `_daily_own_action_scope` | 79 | function：_daily_own_action_scope | 缺少docstring |
| `lesson/models/datas_api/moral/daily_record.py` | class | `DailyRecordCreate` | 94 | 创建日常表现记录 | - |
| `lesson/models/datas_api/moral/daily_record.py` | method | `DailyRecordCreate.validate_record_date` | 101 | 验证记录时间不能超过当前时间 | - |
| `lesson/models/datas_api/moral/daily_record.py` | class | `DailyRecordUpdate` | 109 | 更新日常表现记录 | - |
| `lesson/models/datas_api/moral/daily_record.py` | class | `DailyRecordResponse` | 115 | 日常表现记录响应 | - |
| `lesson/models/datas_api/moral/daily_record.py` | class | `DailyEventTypeCreate` | 130 | 创建日常事件类型 | - |
| `lesson/models/datas_api/moral/daily_record.py` | class | `DailyEventTypeUpdate` | 138 | 更新日常事件类型 | - |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `get_daily_event_types` | 152 | 获取日常事件类型列表 | 路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `get_daily_records` | 178 | 获取日常表现记录列表 权限说明： - admin/xuefa/jiaowu: 可查看所有记录 - cleader/teacher: 只能查看自己创建的记录 | 过长、路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `create_daily_record` | 298 | 创建日常表现记录 权限要求： - teacher/cleader/xuefa/jiaowu/admin 可录入 | 过长、路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `batch_create_daily_records` | 418 | 批量创建日常表现记录 权限要求：cleader/xuefa/jiaowu/admin | 过长、路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `update_daily_record` | 533 | 更新日常表现记录 | 路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `delete_daily_record` | 594 | 删除日常表现记录（软删除） 删除后会重新计算德育评价总分 | 路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `get_student_daily_statistics` | 646 | 获取学生日常表现统计 | 路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `create_daily_event_type` | 703 | 创建日常事件类型 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `update_daily_event_type` | 743 | 更新日常事件类型 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `delete_daily_event_type` | 819 | 删除日常事件类型（软删除，设为禁用状态） 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/daily_record.py` | class | `DailyEventImportItem` | 870 | 批量导入日常事件类型项 | - |
| `lesson/models/datas_api/moral/daily_record.py` | async_function | `batch_import_daily_event_types` | 879 | 批量导入日常事件类型 权限要求：xuefa/jiaowu/admin CSV格式： 事件名称,事件类型,分值,描述 拾金不昧,积极,3,主动上交拾得物品 | 路由 |
| `lesson/models/datas_api/moral/daily_record.py` | function | `check_related_punishments` | 947 | 检查记录删除后关联处分是否需要复核 Args: db: 数据库连接 record_id: 被删除的记录ID student_id: 学生ID event_id: 事件ID semester_id: 学期ID | - |
| `lesson/models/datas_api/moral/escalation.py` | class | `EscalationResult` | 24 | 累进判断结果 | - |
| `lesson/models/datas_api/moral/escalation.py` | function | `get_action_to_level_map` | 40 | 从配置获取 action → level 映射 | - |
| `lesson/models/datas_api/moral/escalation.py` | function | `check_and_trigger_escalation` | 71 | 检查并触发累进处罚 Args: db: 数据库连接 student_id: 学生ID event_id: 违纪事件类型ID record_id: 当前记录ID record_date: 记录时间（可以是date或datetime） seme | 过长 |
| `lesson/models/datas_api/moral/escalation.py` | function | `create_escalation_punishment` | 273 | 自动创建累进处分记录 Args: db: 数据库连接 student_id: 学生ID event_id: 违纪事件ID semester_id: 学期ID punishment_date: 处分日期 punishment_reason:  | - |
| `lesson/models/datas_api/moral/escalation.py` | function | `send_escalation_notification` | 352 | 发送累进处罚通知 Args: db: 数据库连接 student_id: 学生ID result: 累进判断结果 student_info: 学生信息（可选，避免重复查询） | - |
| `lesson/models/datas_api/moral/escalation.py` | function | `get_student_escalation_history` | 428 | 获取学生累进处罚历史 Args: db: 数据库连接 student_id: 学生ID semester_id: 学期ID Returns: List: 累进处罚历史记录 | - |
| `lesson/models/datas_api/moral/escalation.py` | function | `get_student_event_count_in_window` | 458 | 获取学生在时间窗口内某事件的累计次数 Args: db: 数据库连接 student_id: 学生ID event_id: 事件ID current_date: 当前日期 time_window_days: 时间窗口天数 Returns:  | - |
| `lesson/models/datas_api/moral/escalation.py` | function | `get_next_threshold_info` | 493 | 获取学生某事件的累计进度和下一阈值信息 Args: db: 数据库连接 student_id: 学生ID event_id: 事件ID current_date: 当前日期 Returns: Dict: 包含当前次数、下一阈值、距离等信息 | - |
| `lesson/models/datas_api/moral/escalation_api.py` | class | `EscalationRuleItem` | 39 | 单个处罚阶梯 | - |
| `lesson/models/datas_api/moral/escalation_api.py` | class | `EscalationRuleCreate` | 48 | 创建累进规则 | - |
| `lesson/models/datas_api/moral/escalation_api.py` | class | `EscalationRuleUpdate` | 55 | 更新累进规则 | - |
| `lesson/models/datas_api/moral/escalation_api.py` | async_function | `get_escalation_rules` | 66 | 获取累进规则列表 | 路由 |
| `lesson/models/datas_api/moral/escalation_api.py` | async_function | `create_escalation_rule` | 103 | 创建累进规则 | 路由 |
| `lesson/models/datas_api/moral/escalation_api.py` | async_function | `update_escalation_rule` | 153 | 更新累进规则 | 路由 |
| `lesson/models/datas_api/moral/escalation_api.py` | async_function | `delete_escalation_rule` | 202 | 删除累进规则 | 路由 |
| `lesson/models/datas_api/moral/escalation_api.py` | async_function | `get_escalation_history` | 231 | 获取学生累进处罚历史 | 路由 |
| `lesson/models/datas_api/moral/escalation_api.py` | async_function | `get_event_count` | 248 | 获取学生在时间窗口内某事件的累计次数 | 路由 |
| `lesson/models/datas_api/moral/escalation_api.py` | async_function | `get_student_all_progress` | 279 | 获取学生所有消极事件的累计进度 | 路由 |
| `lesson/models/datas_api/moral/escalation_api.py` | async_function | `get_configurable_events` | 315 | 获取可配置累进规则的消极事件列表 | 路由 |
| `lesson/models/datas_api/moral/evaluation.py` | function | `_has_scoped_permission` | 40 | function：_has_scoped_permission | 缺少docstring |
| `lesson/models/datas_api/moral/evaluation.py` | function | `_student_allowed_by_eval_scope` | 45 | function：_student_allowed_by_eval_scope | 缺少docstring |
| `lesson/models/datas_api/moral/evaluation.py` | async_function | `get_student_evaluation` | 64 | 获取学生德育评价 权限说明： - 学生只能查看自己的评价 - 家长只能查看子女的评价 - 班主任可查看本班学生 - xuefa/jiaowu/admin 可查看所有 | 过长、路由 |
| `lesson/models/datas_api/moral/evaluation.py` | async_function | `get_class_evaluation` | 195 | 获取班级德育评价汇总 权限要求： - cleader 可查看本班 - xuefa/jiaowu/admin 可查看所有 | 路由 |
| `lesson/models/datas_api/moral/evaluation.py` | async_function | `get_grade_evaluation` | 255 | 获取年级德育评价汇总 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/evaluation.py` | async_function | `calculate_evaluation_api` | 314 | 计算德育评价 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/evaluation.py` | function | `calculate_evaluation` | 379 | 计算学生德育评价 Args: db: 数据库连接 student_id: 学号 semester_id: 学期ID class_id: 班级ID（可选） grade_id: 级号ID（可选） Returns: 评价结果字典 | 过长 |
| `lesson/models/datas_api/moral/evaluation.py` | function | `get_daily_statistics` | 501 | 获取日常表现统计 | - |
| `lesson/models/datas_api/moral/evaluation.py` | function | `get_school_statistics` | 527 | 获取校级事件统计 | - |
| `lesson/models/datas_api/moral/evaluation.py` | function | `get_task_statistics` | 551 | 获取任务完成统计 | - |
| `lesson/models/datas_api/moral/evaluation.py` | function | `get_collective_statistics` | 568 | 获取集体事件统计 | - |
| `lesson/models/datas_api/moral/evaluation.py` | function | `get_punishment_statistics` | 581 | 获取处分统计 | - |
| `lesson/models/datas_api/moral/evaluation.py` | function | `get_recent_evaluation_records` | 593 | 获取评价详情所需的近期证据记录 | - |
| `lesson/models/datas_api/moral/moment_api.py` | function | `_has_scoped_permission` | 38 | function：_has_scoped_permission | 缺少docstring |
| `lesson/models/datas_api/moral/moment_api.py` | function | `_has_scoped_any_permission` | 43 | function：_has_scoped_any_permission | 缺少docstring |
| `lesson/models/datas_api/moral/moment_api.py` | function | `_moment_view_scope` | 53 | function：_moment_view_scope | 缺少docstring |
| `lesson/models/datas_api/moral/moment_api.py` | function | `_moment_own_action_scope` | 64 | function：_moment_own_action_scope | 缺少docstring |
| `lesson/models/datas_api/moral/moment_api.py` | class | `MomentRecordCreate` | 75 | 创建点滴记录 | - |
| `lesson/models/datas_api/moral/moment_api.py` | method | `MomentRecordCreate.validate_record_date` | 83 | 验证记录日期不能超过今天 | - |
| `lesson/models/datas_api/moral/moment_api.py` | class | `MomentRecordUpdate` | 91 | 更新点滴记录 | - |
| `lesson/models/datas_api/moral/moment_api.py` | async_function | `get_moment_records` | 100 | 获取点滴记录列表 权限说明： - teacher/cleader: 只能查看自己创建的记录 - admin/jiaowu: 可以查看所有记录 | 路由 |
| `lesson/models/datas_api/moral/moment_api.py` | async_function | `create_moment_record` | 187 | 创建点滴记录 权限要求： - teacher/cleader/xuefa/jiaowu/admin 可创建 | 路由 |
| `lesson/models/datas_api/moral/moment_api.py` | async_function | `update_moment_record` | 256 | 更新点滴记录 权限说明： - 只能更新自己创建的记录 | 路由 |
| `lesson/models/datas_api/moral/moment_api.py` | async_function | `delete_moment_record` | 323 | 删除点滴记录 权限说明： - 只能删除自己创建的记录 | 路由 |
| `lesson/models/datas_api/moral/profile.py` | function | `_scoped_roles` | 42 | function：_scoped_roles | 缺少docstring |
| `lesson/models/datas_api/moral/profile.py` | function | `_has_scoped_permission` | 46 | function：_has_scoped_permission | 缺少docstring |
| `lesson/models/datas_api/moral/profile.py` | function | `_student_allowed_by_profile_scope` | 50 | function：_student_allowed_by_profile_scope | 缺少docstring |
| `lesson/models/datas_api/moral/profile.py` | function | `_cleanup_profile_jobs` | 64 | function：_cleanup_profile_jobs | 缺少docstring |
| `lesson/models/datas_api/moral/profile.py` | function | `_generate_student_profile_payload` | 74 | 生成并保存单个学生画像，返回前端可直接展示的数据。 | 过长 |
| `lesson/models/datas_api/moral/profile.py` | function | `_run_profile_generation_job` | 180 | function：_run_profile_generation_job | 缺少docstring |
| `lesson/models/datas_api/moral/profile.py` | class | `DecimalEncoder` | 202 | 自定义JSON编码器，处理Decimal类型 | - |
| `lesson/models/datas_api/moral/profile.py` | method | `DecimalEncoder.default` | 204 | method：DecimalEncoder.default | 缺少docstring |
| `lesson/models/datas_api/moral/profile.py` | class | `ProfileUpdate` | 214 | 更新学生画像 | - |
| `lesson/models/datas_api/moral/profile.py` | async_function | `get_student_profile` | 229 | 获取学生画像 权限说明： - 学生只能查看自己的画像 - 家长只能查看子女的画像 - 班主任可查看本班学生 - xuefa/jiaowu/admin 可查看所有 | 路由 |
| `lesson/models/datas_api/moral/profile.py` | async_function | `generate_student_profile` | 295 | 生成学生画像（基于德育数据分析） 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/profile.py` | async_function | `generate_student_profile_async` | 332 | 创建画像生成任务，立即返回任务ID，由前端轮询结果。 | 路由 |
| `lesson/models/datas_api/moral/profile.py` | async_function | `get_profile_generation_status` | 376 | 查询画像生成任务状态。 | 路由 |
| `lesson/models/datas_api/moral/profile.py` | function | `generate_single_profile_internal` | 397 | 单个学生画像生成的内部函数（用于批量生成） Args: db: 数据库连接 student_id: 学生ID semester_id: 学期ID Returns: dict: 生成结果 | 过长 |
| `lesson/models/datas_api/moral/profile.py` | async_function | `batch_generate_profiles` | 511 | 批量生成学生画像 | 路由 |
| `lesson/models/datas_api/moral/profile.py` | async_function | `get_profile_config` | 599 | 获取画像配置 | 路由 |
| `lesson/models/datas_api/moral/profile.py` | function | `get_profile_config_value` | 640 | 获取画像配置参数 | - |
| `lesson/models/datas_api/moral/profile.py` | function | `get_all_profile_config` | 655 | 获取所有画像配置 | - |
| `lesson/models/datas_api/moral/profile.py` | function | `analyze_student_data` | 674 | 分析学生数据 | 过长 |
| `lesson/models/datas_api/moral/profile.py` | function | `build_profile_output` | 816 | 生成画像内容，AI 不可用时退回本地规则。 | - |
| `lesson/models/datas_api/moral/profile.py` | function | `generate_ai_profile_output` | 855 | 调用项目现有大模型配置生成更自然的画像文本。 | - |
| `lesson/models/datas_api/moral/profile.py` | function | `_num` | 948 | function：_num | 缺少docstring |
| `lesson/models/datas_api/moral/profile.py` | function | `build_evidence_summary` | 955 | 把画像证据整理成稳定摘要，供AI和本地规则复用。 | - |
| `lesson/models/datas_api/moral/profile.py` | function | `generate_profile_summary` | 991 | 生成画像摘要 | - |
| `lesson/models/datas_api/moral/profile.py` | function | `generate_profile_tags` | 1058 | 生成画像标签（支持配置化规则） | - |
| `lesson/models/datas_api/moral/profile.py` | function | `calculate_moral_subscore` | 1124 | 计算品德评分（支持配置化权重） | - |
| `lesson/models/datas_api/moral/profile.py` | function | `calculate_attitude_subscore` | 1139 | 计算态度评分（支持配置化权重） | - |
| `lesson/models/datas_api/moral/profile.py` | function | `calculate_social_subscore` | 1156 | 计算社交评分（基于集体活动参与） | - |
| `lesson/models/datas_api/moral/profile.py` | function | `calculate_growth_subscore` | 1171 | 计算成长评分（支持配置化权重） | - |
| `lesson/models/datas_api/moral/profile.py` | function | `assess_risk_level` | 1184 | 评估风险等级（支持配置化阈值） | - |
| `lesson/models/datas_api/moral/profile.py` | function | `generate_suggestions` | 1210 | 根据画像分析生成个性化建议 | - |
| `lesson/models/datas_api/moral/punishment.py` | class | `PunishmentCreate` | 34 | 创建处分记录 | - |
| `lesson/models/datas_api/moral/punishment.py` | class | `PunishmentRevoke` | 45 | 撤销处分 | - |
| `lesson/models/datas_api/moral/punishment.py` | async_function | `get_punishments` | 56 | 获取处分记录列表 权限说明： - admin/xuefa/jiaowu: 可查看所有 - cleader: 只能查看本班 | 路由 |
| `lesson/models/datas_api/moral/punishment.py` | async_function | `create_punishment` | 146 | 创建处分记录 | 路由 |
| `lesson/models/datas_api/moral/punishment.py` | async_function | `update_punishment` | 223 | 更新处分记录 | 路由 |
| `lesson/models/datas_api/moral/punishment.py` | async_function | `revoke_punishment` | 262 | 撤销处分 revoke_type 说明： - 1: 源记录错误撤销（归还分数） - 2: 期满申请撤销（不归还分数） - 3: 复核误处分撤销（归还分数） | 路由 |
| `lesson/models/datas_api/moral/punishment.py` | async_function | `get_punishment_review_info` | 332 | 获取处分复核所需信息 返回：源记录状态、累计次数、阈值等 | 过长、路由 |
| `lesson/models/datas_api/moral/punishment.py` | class | `PunishmentReview` | 449 | 复核决定 | - |
| `lesson/models/datas_api/moral/punishment.py` | async_function | `review_punishment` | 456 | 复核处分（撤销或通过） - revoke: 撤销处分，回滚扣分，重新计算评价 - approve: 标记复核通过，处分保持有效 | 路由 |
| `lesson/models/datas_api/moral/scheduler.py` | function | `get_scheduler` | 27 | 获取调度器实例 | - |
| `lesson/models/datas_api/moral/scheduler.py` | function | `birthday_reminder_task` | 39 | 每日生日提醒任务（08:00执行） 流程： 1. 查询今日生日学生 2. 发布班级公告通知全班 3. 记录日志 | - |
| `lesson/models/datas_api/moral/scheduler.py` | function | `birthday_blessing_task` | 126 | 每日生日祝福任务（08:30执行） 发布班级祝福公告 | 过长 |
| `lesson/models/datas_api/moral/scheduler.py` | function | `profile_update_check_task` | 243 | 每周一画像更新检查任务（09:00执行） 检查新记录超过阈值的学生，触发画像生成 | - |
| `lesson/models/datas_api/moral/scheduler.py` | function | `warning_check_task` | 309 | 每日预警检查任务（10:00执行） 检查德育分过低、扣分过多、违纪次数过多的学生 | 过长 |
| `lesson/models/datas_api/moral/scheduler.py` | function | `semester_evaluation_task` | 426 | 学期末德育评价计算任务 执行时机：学期末（需手动触发或配置具体日期） | - |
| `lesson/models/datas_api/moral/scheduler.py` | function | `task_carryover_year_end_task` | 454 | 学年末任务结转任务 执行时机：学年末（需手动触发或配置具体日期） | - |
| `lesson/models/datas_api/moral/scheduler.py` | function | `start_scheduler` | 496 | 启动定时任务调度器 | - |
| `lesson/models/datas_api/moral/scheduler.py` | function | `stop_scheduler` | 555 | 停止定时任务调度器 | - |
| `lesson/models/datas_api/moral/scheduler.py` | function | `get_scheduler_status` | 564 | 获取调度器状态 | - |
| `lesson/models/datas_api/moral/scheduler.py` | async_function | `api_get_scheduler_status` | 598 | 获取定时任务调度器状态 | 路由 |
| `lesson/models/datas_api/moral/scheduler.py` | async_function | `api_start_scheduler` | 607 | 启动定时任务调度器 | 路由 |
| `lesson/models/datas_api/moral/scheduler.py` | async_function | `api_stop_scheduler` | 619 | 停止定时任务调度器 | 路由 |
| `lesson/models/datas_api/moral/scheduler.py` | async_function | `api_trigger_birthday_reminder` | 631 | 手动触发生日提醒任务 | 路由 |
| `lesson/models/datas_api/moral/scheduler.py` | async_function | `api_trigger_warning_check` | 643 | 手动触发预警检查任务 | 路由 |
| `lesson/models/datas_api/moral/scheduler.py` | async_function | `api_trigger_semester_evaluation` | 655 | 手动触发学期末德育评价计算 | 路由 |
| `lesson/models/datas_api/moral/scheduler.py` | async_function | `api_trigger_task_carryover` | 667 | 手动触发学年末任务结转 | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | class | `SchoolRecordCreate` | 37 | 创建校级事件记录 | - |
| `lesson/models/datas_api/moral/school_event.py` | method | `SchoolRecordCreate.validate_event_date` | 45 | 验证事件日期不能超过今天 | - |
| `lesson/models/datas_api/moral/school_event.py` | class | `SchoolRecordUpdate` | 53 | 更新校级事件记录 | - |
| `lesson/models/datas_api/moral/school_event.py` | class | `SchoolEventTypeCreate` | 61 | 创建校级事件类型 | - |
| `lesson/models/datas_api/moral/school_event.py` | class | `SchoolEventTypeUpdate` | 70 | 更新校级事件类型 | - |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `get_school_event_types` | 85 | 获取校级事件类型列表 | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `get_school_records` | 116 | 获取校级事件记录列表 | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `create_school_record` | 199 | 创建校级事件记录 | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `update_school_record` | 278 | 更新校级事件记录 | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `delete_school_record` | 331 | 删除校级事件记录（软删除） | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `create_school_event_type` | 364 | 创建校级事件类型 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `update_school_event_type` | 404 | 更新校级事件类型 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `delete_school_event_type` | 482 | 删除校级事件类型（软删除，设为禁用状态） 权限要求：xuefa/jiaowu/admin | 路由 |
| `lesson/models/datas_api/moral/school_event.py` | class | `SchoolEventImportItem` | 530 | 批量导入校级事件类型项 | - |
| `lesson/models/datas_api/moral/school_event.py` | async_function | `batch_import_school_event_types` | 540 | 批量导入校级事件类型 权限要求：xuefa/jiaowu/admin CSV格式： 事件名称,事件类型,事件级别,分值,描述 三好学生,荣誉奖励,校级,10,校级三好学生称号 | 路由 |
| `lesson/models/datas_api/moral/task.py` | class | `MoralTaskCreate` | 36 | 创建德育任务 | - |
| `lesson/models/datas_api/moral/task.py` | class | `TaskFinishCreate` | 47 | 完成任务记录 | - |
| `lesson/models/datas_api/moral/task.py` | async_function | `get_moral_tasks` | 60 | 获取德育任务列表 | 路由 |
| `lesson/models/datas_api/moral/task.py` | async_function | `create_moral_task` | 89 | 创建德育任务 | 路由 |
| `lesson/models/datas_api/moral/task.py` | async_function | `update_moral_task` | 121 | 更新德育任务 | 路由 |
| `lesson/models/datas_api/moral/task.py` | async_function | `delete_moral_task` | 159 | 删除德育任务（软删除） | 路由 |
| `lesson/models/datas_api/moral/task.py` | async_function | `get_task_finish_records` | 184 | 获取任务完成记录列表 | 路由 |
| `lesson/models/datas_api/moral/task.py` | async_function | `finish_task` | 246 | 记录任务完成 | 路由 |
| `lesson/models/datas_api/moral/task.py` | class | `MoralTaskImportItem` | 341 | 批量导入德育任务项 | - |
| `lesson/models/datas_api/moral/task.py` | async_function | `batch_import_moral_tasks` | 352 | 批量导入德育任务 权限要求：xuefa/jiaowu/admin CSV格式： 级号名称,任务名称,任务描述,分值,截止类型,是否必修 2023级,志愿服务,参加志愿服务活动,5,学年截止,是 | 路由 |
| `lesson/models/datas_api/moral/timeline_api.py` | async_function | `search_students_for_timeline` | 25 | 搜索学生用于一生一册查看 权限说明： - 班主任只能搜索本班学生 - 教发部/管理员可搜索所有学生 | 路由 |
| `lesson/models/datas_api/moral/timeline_api.py` | async_function | `get_student_timeline` | 93 | 获取学生成长时光轴 权限说明： - 班主任(cleader): 只能查看本班学生 - 教发部/管理员: 可查看所有学生 | 过长、路由 |

## 后端会员/管理

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/models/manage/log_analyzer.py` | function | `analyze_log` | 52 | function：analyze_log | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `get_solutions_for_errors` | 118 | 获取：get_solutions_for_errors | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `analyze_group_stats` | 137 | function：analyze_group_stats | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `analyze_inactive_members` | 161 | function：analyze_inactive_members | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `filter_corpus` | 192 | function：filter_corpus | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `extract_highlights` | 218 | function：extract_highlights | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `perform_nlp_analysis` | 243 | function：perform_nlp_analysis | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `generate_report` | 251 | 生成：generate_report | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `generate_single_group_report` | 297 | 生成：generate_single_group_report | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `generate_error_report` | 340 | 生成：generate_error_report | 缺少docstring |
| `lesson/models/manage/log_analyzer.py` | function | `analyze_log_file` | 364 | function：analyze_log_file | 缺少docstring |
| `lesson/models/manage/manage.py` | async_function | `forward_msg` | 16 | async_function：forward_msg | 缺少docstring |
| `lesson/models/manage/manage.py` | async_function | `command_manul` | 34 | 命令帮助 :param record: 命令记录 :return: 命令帮助 | - |
| `lesson/models/manage/manage.py` | async_function | `welcome_msg` | 57 | 欢迎消息 | - |
| `lesson/models/manage/manage.py` | async_function | `say_hi_qun` | 70 | 新人入群欢迎，小黄人举牌 | - |
| `lesson/models/manage/manage.py` | async_function | `invite_chatroom_member` | 95 | 邀请入群 | - |
| `lesson/models/manage/manage.py` | async_function | `view_rules` | 133 | 查看规则列表和详情 - 规则：显示所有规则列表 - 规则 AI：只显示 AI 规则 - 规则 模块：显示所有模块列表 - 规则 模块名：按模块筛选 - 规则-id：显示单条规则详情 | - |
| `lesson/models/manage/manage.py` | function | `_send_rules_list` | 183 | 发送规则列表 | - |
| `lesson/models/manage/manage.py` | function | `_send_rule_detail` | 229 | 发送规则详情 | - |
| `lesson/models/manage/manage.py` | function | `_send_modules_list` | 262 | 发送模块列表 | - |
| `lesson/models/manage/member.py` | function | `_member_teacher_id` | 34 | function：_member_teacher_id | 缺少docstring |
| `lesson/models/manage/member.py` | class | `Member` | 39 | 定义 Member 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/models/manage/member.py` | method | `Member.__init__` | 40 | Member.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/manage/member.py` | method | `Member.__enter__` | 45 | Member.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/manage/member.py` | method | `Member.__exit__` | 50 | Member.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/manage/member.py` | method | `Member.__create_table__` | 54 | Member.__create_table__ 生命周期/魔术方法 | 过长、缺少docstring |
| `lesson/models/manage/member.py` | method | `Member.wx_contacts` | 180 | 获取微信联系人 | - |
| `lesson/models/manage/member.py` | method | `Member.db_contacts` | 186 | 获取数据库联系人 | - |
| `lesson/models/manage/member.py` | method | `Member.db_chatroom` | 193 | 获取数据库群聊 | - |
| `lesson/models/manage/member.py` | method | `Member.update_contacts` | 200 | 更新本地数据库联系人 | - |
| `lesson/models/manage/member.py` | method | `Member.update_chatroom` | 261 | 更新本地数据库群聊 | - |
| `lesson/models/manage/member.py` | method | `Member.update_group_members` | 301 | 更新群聊成员 | 过长 |
| `lesson/models/manage/member.py` | method | `Member.query_member_name` | 408 | 查询群聊成员名称 | - |
| `lesson/models/manage/member.py` | method | `Member.wxid_remark` | 447 | 获取微信联系人备注 | - |
| `lesson/models/manage/member.py` | method | `Member.remark_wxid` | 463 | 根据备注获取微信联系人 | - |
| `lesson/models/manage/member.py` | method | `Member.chatroom_name` | 479 | 获取群聊名称 | - |
| `lesson/models/manage/member.py` | method | `Member.insert_member` | 495 | 插入成员 | - |
| `lesson/models/manage/member.py` | method | `Member.delte_member` | 572 | 删除成员 | - |
| `lesson/models/manage/member.py` | method | `Member.member_info` | 589 | 获取成员信息 | - |
| `lesson/models/manage/member.py` | method | `Member.update_member` | 606 | 更新成员信息 | - |
| `lesson/models/manage/member.py` | method | `Member.member_columns` | 641 | 获取成员列名 | - |
| `lesson/models/manage/member.py` | method | `Member.member_wxid` | 645 | 获取成员微信ID | - |
| `lesson/models/manage/member.py` | method | `Member._member_select_sql` | 662 | method：Member._member_select_sql | 缺少docstring |
| `lesson/models/manage/member.py` | method | `Member.ensure_unified_member_schema` | 682 | 确保 moral.teacher 可以承载原 member 表字段。 | - |
| `lesson/models/manage/member.py` | method | `Member.migrate_legacy_members_to_teacher` | 763 | 把 member.db.member 的历史数据迁移到 moral.teacher，原表保留备份。 | - |
| `lesson/models/manage/member.py` | method | `Member.insert_permission` | 846 | 插入权限 | - |
| `lesson/models/manage/member.py` | method | `Member.delte_permission` | 900 | 删除权限 | - |
| `lesson/models/manage/member.py` | method | `Member.permission_info` | 907 | 获取权限信息 | - |
| `lesson/models/manage/member.py` | method | `Member.permission_func_list` | 919 | 获取权限列表 | - |
| `lesson/models/manage/member.py` | method | `Member.permission_columns` | 926 | 获取权限列名 | - |
| `lesson/models/manage/member.py` | method | `Member.update_permission` | 934 | 更新权限信息 | - |
| `lesson/models/manage/member.py` | method | `Member.get_permission_by_id` | 958 | 根据ID获取权限信息 | - |
| `lesson/models/manage/member.py` | method | `Member.activate_func` | 965 | 激活函数 | - |
| `lesson/models/manage/member.py` | method | `Member.deactivate_func` | 974 | 禁用函数 | - |
| `lesson/models/manage/member.py` | async_function | `query_permission` | 984 | 查询权限 | - |
| `lesson/models/manage/member.py` | async_function | `insert_permission` | 1035 | 插入权限 | - |
| `lesson/models/manage/member.py` | async_function | `add_member` | 1107 | 插入会员：+会员：abc-10-lesson | - |
| `lesson/models/manage/member.py` | async_function | `del_member` | 1151 | 删除会员 | - |
| `lesson/models/manage/member.py` | async_function | `query_members` | 1170 | 查询会员 | - |
| `lesson/models/manage/member.py` | async_function | `start_func` | 1184 | 启动功能 | - |
| `lesson/models/manage/member.py` | async_function | `stop_func` | 1204 | async_function：stop_func | 缺少docstring |
| `lesson/models/manage/member.py` | function | `check_permission` | 1222 | 检查：check_permission | 缺少docstring |
| `lesson/models/manage/member.py` | async_function | `wrapper` | 1223 | async_function：wrapper | 缺少docstring |
| `lesson/models/manage/member.py` | function | `has_permission` | 1236 | function：has_permission | 缺少docstring |

## 后端其他

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/client.py` | class | `Client` | 19 | 定义 Client 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/client.py` | method | `Client.__init__` | 20 | Client.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/client.py` | method | `Client._check_token` | 28 | 检查token是否过期，过期则重新获取 | - |
| `lesson/client.py` | method | `Client._make_request` | 32 | 通用HTTP请求方法 Args: endpoint: API端点 data: 请求数据 params: URL参数 Returns: str: 成功时返回响应内容 int: 失败时返回-1 | - |
| `lesson/client.py` | method | `Client.send_text` | 71 | 发送文本消息 | - |
| `lesson/client.py` | method | `Client.send_image` | 81 | 发送图片消息 | - |
| `lesson/client.py` | method | `Client.send_rich_text` | 90 | 发送富文本消息 | - |
| `lesson/client.py` | method | `Client.send_app` | 99 | 发送应用消息 Args: xml_dict (dict): xml receiver (str): 接收者wxid type (int): 消息类型，默认13为 Returns: int: 0表示成功，-1表示失败 | - |
| `lesson/client.py` | method | `Client.send_file` | 115 | 发送文件 Args: file_dict (dict or str): 文件信息字典或文件路径 receiver (str): 接收者wxid Returns: int: 0表示成功，-1表示失败 | - |
| `lesson/client.py` | method | `Client.down_file` | 142 | 下载文件 | - |
| `lesson/client.py` | function | `trigger_download_file` | 149 | 触发下载文件 | - |
| `lesson/client.py` | method | `Client.contact_info` | 172 | 获取联系人信息 Args: content_type (int): 0通讯录 1群聊 Returns: dict: 包含所有联系人信息的字典 | - |
| `lesson/client.py` | method | `Client.group_qr` | 214 | 获取群二维码 | - |
| `lesson/client.py` | method | `Client.group_manage` | 237 | 群管理 Args: roomid: 群id wxid: 要管理的wxid type: 3为踢人 2为加人 Returns: dict: 包含所有联系人信息的字典 | - |
| `lesson/client.py` | method | `Client.get_group_members` | 254 | 获取群成员信息 | - |
| `lesson/client.py` | function | `down_file` | 293 | 下载文件 | - |
| `lesson/feishu.py` | class | `FeishuClient` | 15 | 定义 FeishuClient 类，承载相关状态和方法 | 缺少docstring |
| `lesson/feishu.py` | method | `FeishuClient.__init__` | 16 | FeishuClient.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/feishu.py` | method | `FeishuClient._get_token` | 22 | method：FeishuClient._get_token | 缺少docstring |
| `lesson/feishu.py` | method | `FeishuClient.upload_file` | 40 | 上传：upload_file | 缺少docstring |
| `lesson/feishu.py` | method | `FeishuClient.send_message` | 55 | 发送：send_message | 缺少docstring |
| `lesson/feishu.py` | function | `send_file` | 76 | 发送：send_file | 缺少docstring |
| `lesson/migrate_passwords.py` | function | `migrate_passwords` | 17 | 将明文密码迁移为 bcrypt 哈希 | - |
| `lesson/models/api.py` | class | `ZPAI` | 14 | 定义 ZPAI 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/api.py` | method | `ZPAI.__init__` | 15 | ZPAI.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/api.py` | method | `ZPAI.ai_remind_text` | 19 | method：ZPAI.ai_remind_text | 缺少docstring |
| `lesson/models/api.py` | function | `one_day_English` | 43 | function：one_day_English | 缺少docstring |
| `lesson/models/api.py` | function | `countdown_day` | 55 | 日期倒计时函数 :param target_date: :return: | - |
| `lesson/models/api.py` | function | `gk_countdown` | 79 | 高考倒计时，每天一句英语 :return: | - |
| `lesson/models/api.py` | function | `ju_pai` | 105 | function：ju_pai | 缺少docstring |
| `lesson/models/api.py` | function | `bailian_req` | 131 | function：bailian_req | 缺少docstring |
| `lesson/models/api.py` | function | `ai_remind_text` | 149 | 调用 bailian 模型，返回模型的回答 :param question: :return: | - |
| `lesson/models/daily/daily.py` | class | `Daily` | 21 | 定义 Daily 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.__init__` | 22 | Daily.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.__enter__` | 25 | Daily.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.__exit__` | 30 | Daily.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.__create_table__` | 33 | Daily.__create_table__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.insert_daily` | 56 | method：Daily.insert_daily | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.get_dailies` | 64 | 获取：get_dailies | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.daily_columns` | 92 | method：Daily.daily_columns | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.del_daily` | 96 | method：Daily.del_daily | 缺少docstring |
| `lesson/models/daily/daily.py` | method | `Daily.get_recorder` | 101 | 获取：get_recorder | 缺少docstring |
| `lesson/models/daily/daily.py` | async_function | `insert_daily` | 106 | 触发条件 睡觉-(.*) 添加课时记录碎片 | - |
| `lesson/models/daily/daily.py` | async_function | `get_dailies` | 141 | 触发条件 查询常规记录碎片 常规-20260127-睡觉 | - |
| `lesson/models/daily/daily.py` | async_function | `export_dailies` | 181 | 导出：export_dailies | 缺少docstring |
| `lesson/models/daily/daily.py` | async_function | `del_daily` | 219 | 触发条件 删常规-1 删除指定记录碎片 | - |
| `lesson/models/daily/inout.py` | class | `InOut` | 19 | 定义 InOut 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.__enter__` | 20 | InOut.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.__exit__` | 25 | InOut.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.__create_table__` | 28 | InOut.__create_table__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.insert_inout` | 55 | method：InOut.insert_inout | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.get_inouts` | 63 | 获取：get_inouts | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.out_inout` | 75 | method：InOut.out_inout | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.in_inout` | 79 | method：InOut.in_inout | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.del_delay` | 83 | method：InOut.del_delay | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.consume_delay` | 87 | method：InOut.consume_delay | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.inout_columns` | 91 | method：InOut.inout_columns | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.get_recorder` | 95 | 获取：get_recorder | 缺少docstring |
| `lesson/models/daily/inout.py` | method | `InOut.get_id` | 99 | 获取：get_id | 缺少docstring |
| `lesson/models/daily/inout.py` | async_function | `insert_inout` | 104 | 触发条件 事假-高二1班-张三-2-备注(可选) 添加记录碎片 | - |
| `lesson/models/daily/inout.py` | async_function | `get_inout` | 131 | 触发条件 请假-高二1班-张三 查询记录碎片 | - |
| `lesson/models/daily/inout.py` | async_function | `out_inout` | 173 | 触发条件 出校-高二1班-张三 出校记录碎片 | - |
| `lesson/models/daily/inout.py` | async_function | `in_inout` | 199 | 触发条件 销假-高二1班-张三 销假记录碎片 | - |
| `lesson/models/daily/inout.py` | function | `get_stu_dict` | 224 | 获取：get_stu_dict | 缺少docstring |
| `lesson/models/daily/inout.py` | function | `safe_int_str` | 228 | function：safe_int_str | 缺少docstring |
| `lesson/models/daily/inout.py` | function | `check_inout_days` | 248 | 检查所有请假记录的天数是否已经到达时限 | - |
| `lesson/models/filegather_db.py` | class | `FileGatherDB` | 33 | 文件收集系统数据库操作类 | 过长 |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.__init__` | 36 | 初始化数据库连接 Args: db_path: 数据库文件路径 storage_root: 存储根目录 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB._get_connection` | 55 | 获取数据库连接的上下文管理器 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB._ensure_dirs` | 64 | 确保存储目录和数据库目录存在 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB._init_db` | 72 | 初始化数据库表 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.check_extension` | 101 | 检查文件扩展名是否允许 Args: filename: 文件名 Returns: 是否允许 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.parse_use_date` | 116 | 解析使用日期 Args: raw: 日期字符串 (YYYY-MM-DD格式) Returns: (日期ISO字符串, 月份字符串) | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.save_file` | 133 | 保存上传的文件 Args: month: 月份 (YYYYMM格式) filename: 原始文件名 file_content: 文件内容 Returns: 存储路径 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.insert_file` | 163 | 插入文件记录 Args: username: 用户名 original_name: 原始文件名 stored_path: 存储路径 content_type: 内容类型 copies: 打印份数 use_date: 使用日期 month:  | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.query_files` | 214 | 查询文件记录 Args: username: 用户名筛选 status: 状态筛选 month: 月份筛选 Returns: 文件记录列表 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.get_file_by_id` | 262 | 根据ID获取文件记录 Args: file_id: 文件ID Returns: 文件记录或None | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.mark_done` | 277 | 标记文件为已完成 Args: file_id: 文件ID Returns: 更新后的文件信息 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.update_status` | 312 | 更新文件状态 Args: file_id: 文件ID status: 新状态 Returns: 是否成功 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.delete_file` | 332 | 删除文件记录和文件 Args: file_id: 文件ID username: 操作用户名 Returns: 是否成功 | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.get_months` | 369 | 获取所有有文件的月份列表 Returns: 月份列表 (YYYYMM格式) | - |
| `lesson/models/filegather_db.py` | method | `FileGatherDB.get_statistics` | 382 | 获取统计信息 Args: month: 月份筛选 Returns: 统计信息 | - |
| `lesson/models/parking.py` | function | `get_parking_records` | 12 | 获取：get_parking_records | 缺少docstring |
| `lesson/models/parking.py` | function | `watching_parking` | 56 | function：watching_parking | 缺少docstring |
| `lesson/models/push_brach.py` | function | `login_github` | 14 | 使用个人访问令牌(Personal Access Token)登录GitHub | - |
| `lesson/models/push_brach.py` | function | `push_branch` | 39 | 将指定文件夹中的代码提交到远程分支 参数: repo_path: 本地仓库路径 branch_name: 要提交到的分支名称 commit_message: 提交信息 remote_name: 远程仓库名称 proxy: 代理地址，格式为  | - |
| `lesson/models/push_brach.py` | function | `get_qrcode` | 138 | 获取：get_qrcode | 缺少docstring |
| `lesson/models/push_brach.py` | function | `push_qrcode` | 153 | function：push_qrcode | 缺少docstring |
| `lesson/models/push_brach.py` | async_function | `change_roomid` | 190 | async_function：change_roomid | 缺少docstring |
| `lesson/models/task.py` | function | `register_task` | 58 | 任务函数装饰器，自动注册到任务系统 | - |
| `lesson/models/task.py` | function | `decorator` | 60 | function：decorator | 缺少docstring |
| `lesson/models/task.py` | function | `init_task_registry` | 69 | 初始化任务注册表，手动注册所有任务函数 | - |
| `lesson/models/task.py` | function | `parse_datetime` | 86 | 解析：parse_datetime | 缺少docstring |
| `lesson/models/task.py` | class | `Task` | 108 | 定义 Task 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/models/task.py` | method | `Task.__init__` | 109 | Task.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/task.py` | method | `Task.__enter__` | 116 | Task.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/task.py` | method | `Task.__exit__` | 121 | Task.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/task.py` | method | `Task.__create_table__` | 125 | Task.__create_table__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/task.py` | method | `Task.add_job` | 152 | method：Task.add_job | 缺少docstring |
| `lesson/models/task.py` | method | `Task.add_job_cron` | 165 | method：Task.add_job_cron | 缺少docstring |
| `lesson/models/task.py` | method | `Task.add_job_interval` | 176 | method：Task.add_job_interval | 缺少docstring |
| `lesson/models/task.py` | method | `Task.random_daily_task` | 181 | method：Task.random_daily_task | 缺少docstring |
| `lesson/models/task.py` | method | `Task.show_tasks` | 221 | method：Task.show_tasks | 缺少docstring |
| `lesson/models/task.py` | method | `Task.remove_task` | 238 | 移除：remove_task | 缺少docstring |
| `lesson/models/task.py` | async_method | `Task.start` | 246 | async_method：Task.start | 缺少docstring |
| `lesson/models/task.py` | async_method | `Task.stop` | 249 | async_method：Task.stop | 缺少docstring |
| `lesson/models/task.py` | async_method | `Task.run` | 252 | async_method：Task.run | 缺少docstring |
| `lesson/models/task.py` | method | `Task.add_task_to_db` | 257 | 将任务添加到数据库 :param func_name: 函数名称 :param trigger_type: 触发器类型 (cron, interval) :param trigger_args: 触发器参数 (JSON格式) :param  | - |
| `lesson/models/task.py` | method | `Task.get_tasks_from_db` | 302 | 从数据库获取所有启用的任务 :return: 任务列表 | - |
| `lesson/models/task.py` | method | `Task.get_available_funcs` | 315 | 获取可用的任务函数列表 :return: 函数名和描述的列表 | - |
| `lesson/models/task.py` | method | `Task.update_task_consumed` | 323 | 更新任务的consumed状态 :param task_id: 任务ID :param consumed: 是否已消费 :return: 是否更新成功 | - |
| `lesson/models/task.py` | async_function | `get_task_list` | 350 | 获取：get_task_list | 缺少docstring |
| `lesson/models/task.py` | async_function | `stop_task` | 355 | async_function：stop_task | 缺少docstring |
| `lesson/models/task.py` | async_function | `add_cron_remind` | 367 | async_function：add_cron_remind | 缺少docstring |
| `lesson/models/task.py` | function | `push_qrcode` | 430 | function：push_qrcode | 缺少docstring |
| `lesson/models/task.py` | async_function | `task_start` | 433 | async_function：task_start | 缺少docstring |
| `lesson/models/task.py` | function | `init_default_tasks` | 450 | 初始化默认任务到数据库（如果不存在） | - |
| `lesson/models/task.py` | function | `task_wrapper` | 524 | 任务包装器，在任务执行后更新consumed状态 :param func: 原始任务函数 :param task_id: 任务ID :return: 包装后的函数 | - |
| `lesson/models/task.py` | function | `wrapper` | 532 | function：wrapper | 缺少docstring |
| `lesson/models/task.py` | function | `load_tasks_from_db` | 547 | 从数据库加载任务到调度器 | - |
| `lesson/models/task.py` | function | `incert_task_from_excel` | 634 | 从Excel文件导入任务 | - |
| `lesson/sendqueue.py` | class | `QueueDB` | 35 | 定义 QueueDB 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/sendqueue.py` | method | `QueueDB.__new__` | 39 | QueueDB.__new__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/sendqueue.py` | method | `QueueDB.__init__` | 46 | QueueDB.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/sendqueue.py` | method | `QueueDB.__enter__` | 58 | QueueDB.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/sendqueue.py` | method | `QueueDB.__exit__` | 65 | QueueDB.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/sendqueue.py` | method | `QueueDB.__create_table__` | 71 | 创建队列表 producer: 消息生产者 consumer: 消息消费者 p_time: 消息生产时间 c_time: 消息消费时间 | - |
| `lesson/sendqueue.py` | method | `QueueDB.__produce__` | 97 | 生产消息队列 :param msg_id: 对应微信消息的msg_id :param data: 消息内容 :param producer: 消息生产者 :param consumer: 消息消费者,api :return: | - |
| `lesson/sendqueue.py` | method | `QueueDB.__is_message_expired__` | 131 | 检查消息是否过期 :param record: 消息记录 :return: bool | - |
| `lesson/sendqueue.py` | method | `QueueDB.__clean_expired_messages__` | 151 | 清理过期消息 :return: 清理的消息数量 | - |
| `lesson/sendqueue.py` | method | `QueueDB.__retry_failed_messages__` | 174 | 重试失败的消息 :return: 重试的消息数量 | - |
| `lesson/sendqueue.py` | method | `QueueDB.get_queue_status` | 196 | 获取队列状态 :return: dict | - |
| `lesson/sendqueue.py` | method | `QueueDB.__update_message_status__` | 236 | 更新消息状态 :param msg_id: 消息ID :param status: 状态 :param error_message: 错误信息 | - |
| `lesson/sendqueue.py` | method | `QueueDB.__increment_retry_count__` | 255 | 增加重试计数 :param msg_id: 消息ID | - |
| `lesson/sendqueue.py` | method | `QueueDB.__consume__` | 271 | 消费消息队列（带重试机制） :return: | 过长 |
| `lesson/sendqueue.py` | function | `_debug_send` | 381 | 调试模式下的打印函数 | - |
| `lesson/sendqueue.py` | function | `send_text` | 388 | 发送：send_text | 缺少docstring |
| `lesson/sendqueue.py` | function | `send_image` | 391 | 发送：send_image | 缺少docstring |
| `lesson/sendqueue.py` | function | `send_file` | 394 | 发送：send_file | 缺少docstring |
| `lesson/sendqueue.py` | function | `send_app_msg` | 397 | 发送：send_app_msg | 缺少docstring |
| `lesson/sendqueue.py` | function | `send_text` | 402 | 发送文本消息 | - |
| `lesson/sendqueue.py` | function | `send_image` | 413 | 发送图片消息 | - |
| `lesson/sendqueue.py` | function | `send_file` | 421 | 发送文件消息 | - |
| `lesson/sendqueue.py` | function | `send_app_msg` | 440 | 发送应用消息 | - |
| `lesson/sendqueue.py` | async_function | `get_queue_info` | 451 | 获取队列状态信息 | - |
| `lesson/sendqueue.py` | function | `clean_expired_messages` | 459 | 清理过期消息 | - |
| `lesson/sendqueue.py` | function | `retry_failed_messages` | 465 | 重试失败的消息 | - |
| `lesson/wxmsg.py` | function | `process_nested_dict` | 15 | 处理嵌套的字典，尝试解析可能是JSON的字符串 | - |
| `lesson/wxmsg.py` | function | `filter_msg` | 40 | function：filter_msg | 缺少docstring |
| `lesson/wxmsg.py` | class | `WxMsg` | 52 | 微信消息 Attributes: id (str): primary key type (int): 消息类型 sender (str): 消息发送人 roomid (str): （仅群消息有）群 id content (str): 消息内 | 过长 |
| `lesson/wxmsg.py` | method | `WxMsg.__init__` | 67 | WxMsg.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg.formate_msg` | 77 | 格式化：formate_msg | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg.event_callback` | 92 | 事件回调 | - |
| `lesson/wxmsg.py` | method | `WxMsg.parse_content` | 108 | 解析消息内容 | - |
| `lesson/wxmsg.py` | method | `WxMsg._process_by_type` | 142 | 根据消息类型处理内容 | - |
| `lesson/wxmsg.py` | method | `WxMsg._handle_other_types` | 225 | 处理其他类型的消息 | - |
| `lesson/wxmsg.py` | method | `WxMsg._handle_file` | 258 | method：WxMsg._handle_file | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_card` | 269 | method：WxMsg._handle_card | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_location` | 280 | method：WxMsg._handle_location | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_redpacket` | 291 | method：WxMsg._handle_redpacket | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_transfer` | 302 | method：WxMsg._handle_transfer | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_miniprogram` | 317 | method：WxMsg._handle_miniprogram | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_emotion` | 333 | method：WxMsg._handle_emotion | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_group_management` | 337 | method：WxMsg._handle_group_management | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_redpacket_received` | 341 | method：WxMsg._handle_redpacket_received | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_group_system` | 352 | method：WxMsg._handle_group_system | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_article` | 366 | method：WxMsg._handle_article | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_voice_call` | 377 | method：WxMsg._handle_voice_call | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_video_call` | 381 | method：WxMsg._handle_video_call | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_service_notification` | 385 | method：WxMsg._handle_service_notification | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_quote` | 396 | method：WxMsg._handle_quote | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_group_chain` | 411 | method：WxMsg._handle_group_chain | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_video_channel` | 415 | method：WxMsg._handle_video_channel | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_group_live` | 426 | method：WxMsg._handle_group_live | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_pat` | 437 | method：WxMsg._handle_pat | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_share_music` | 440 | method：WxMsg._handle_share_music | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_video_live` | 444 | method：WxMsg._handle_video_live | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_customer_card` | 448 | method：WxMsg._handle_customer_card | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_enterprise_card` | 459 | method：WxMsg._handle_enterprise_card | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._handle_unsupported` | 470 | method：WxMsg._handle_unsupported | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg.__to_dict__` | 474 | WxMsg.__to_dict__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg.__str__` | 490 | WxMsg.__str__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/wxmsg.py` | method | `WxMsg._is_at` | 531 | 是否被 @：群消息，在 @ 名单里，并且不是 @ 所有人 | - |
| `lesson/wxmsg.py` | class | `MessageDB` | 545 | 消息数据库 | - |
| `lesson/wxmsg.py` | method | `MessageDB.__enter__` | 548 | MessageDB.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/wxmsg.py` | method | `MessageDB.__exit__` | 553 | MessageDB.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/wxmsg.py` | method | `MessageDB.__create_table__` | 557 | MessageDB.__create_table__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/wxmsg.py` | method | `MessageDB.insert` | 577 | method：MessageDB.insert | 缺少docstring |
| `lesson/wxmsg.py` | method | `MessageDB.select` | 586 | method：MessageDB.select | 缺少docstring |

## 后端基础设施

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/config/config.py` | class | `Config` | 10 | 定义 Config 类，承载相关状态和方法 | 缺少docstring |
| `lesson/config/config.py` | method | `Config.__init__` | 11 | Config.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/config/config.py` | method | `Config.get_config` | 15 | 获取：get_config | 缺少docstring |
| `lesson/config/config.py` | method | `Config.get_cross_platform_path` | 24 | 获取跨平台路径配置 配置格式示例 (YAML): lesson_dir: Darwin: /Users/yoin/bdsync/temp/lesson # macOS Windows: D:/lesson # Windows Linux:  | - |
| `lesson/config/config.py` | method | `Config.get_config_all` | 67 | 获取：get_config_all | 缺少docstring |
| `lesson/config/config.py` | method | `Config.modify_config` | 76 | method：Config.modify_config | 缺少docstring |
| `lesson/config/log.py` | function | `get_request_id` | 18 | 获取当前请求的追踪 ID | - |
| `lesson/config/log.py` | function | `set_request_id` | 23 | 设置当前请求的追踪 ID | - |
| `lesson/config/log.py` | class | `RequestIdFormatter` | 31 | 带请求追踪 ID 的 formatter | - |
| `lesson/config/log.py` | method | `RequestIdFormatter.__init__` | 34 | RequestIdFormatter.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/config/log.py` | method | `RequestIdFormatter.format` | 38 | 格式化：format | 缺少docstring |
| `lesson/config/log.py` | method | `RequestIdFormatter._format_json` | 48 | method：RequestIdFormatter._format_json | 缺少docstring |
| `lesson/config/log.py` | method | `RequestIdFormatter._format_text` | 70 | method：RequestIdFormatter._format_text | 缺少docstring |
| `lesson/config/log.py` | class | `JsonFormatter` | 77 | JSON 格式日志 formatter | - |
| `lesson/config/log.py` | method | `JsonFormatter.format` | 80 | 格式化：format | 缺少docstring |
| `lesson/config/log.py` | class | `LogConfig` | 106 | 定义 LogConfig 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/config/log.py` | method | `LogConfig.__init__` | 107 | LogConfig.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/config/log.py` | method | `LogConfig.__config_logging` | 113 | 配置日志 | 过长 |
| `lesson/config/log.py` | method | `LogConfig.get_logger` | 221 | 获取：get_logger | 缺少docstring |
| `lesson/utils/cache.py` | class | `NumpyEncoder` | 15 | 处理 numpy 类型的 JSON 编码器 | - |
| `lesson/utils/cache.py` | method | `NumpyEncoder.default` | 18 | method：NumpyEncoder.default | 缺少docstring |
| `lesson/utils/cache.py` | class | `RedisCache` | 28 | Redis 缓存管理器 | 过长 |
| `lesson/utils/cache.py` | method | `RedisCache.__new__` | 34 | RedisCache.__new__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/cache.py` | method | `RedisCache.__init__` | 39 | RedisCache.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/cache.py` | method | `RedisCache._connect` | 43 | 连接 Redis | - |
| `lesson/utils/cache.py` | method | `RedisCache.get` | 67 | 获取缓存 | - |
| `lesson/utils/cache.py` | method | `RedisCache.set` | 80 | 设置缓存 | - |
| `lesson/utils/cache.py` | method | `RedisCache.delete` | 92 | 删除缓存 | - |
| `lesson/utils/cache.py` | method | `RedisCache.clear_pattern` | 104 | 清除匹配的所有缓存 | - |
| `lesson/utils/cache.py` | method | `RedisCache.refresh` | 117 | 细粒度刷新：刷新指定 key 的缓存 Args: key: 缓存键 value: 新值，如果为 None 则删除该缓存（下次访问时重新生成） expire: 过期时间（秒） Returns: bool: 操作是否成功 | - |
| `lesson/utils/cache.py` | method | `RedisCache.refresh_keys` | 145 | 批量刷新指定 keys 的缓存 Args: keys: 缓存键列表 values: 新值字典，key -> value，如果为 None 则删除这些缓存 Returns: int: 成功刷新的数量 | - |
| `lesson/utils/cache.py` | method | `RedisCache.get_or_set` | 177 | 获取缓存，如果不存在则调用 factory 生成并缓存 Args: key: 缓存键 factory: 当缓存不存在时调用的函数 expire: 过期时间（秒） Returns: Any: 缓存值或 factory 的返回值 | - |
| `lesson/utils/cache.py` | function | `cached` | 208 | 缓存装饰器 用法: @cached("user:", expire=1800) def get_user(user_id): return database.query(user_id) | - |
| `lesson/utils/cache.py` | function | `decorator` | 217 | function：decorator | 缺少docstring |
| `lesson/utils/cache.py` | function | `wrapper` | 219 | function：wrapper | 缺少docstring |
| `lesson/utils/database.py` | class | `DatabaseOptimized` | 15 | SQLite 数据库优化类 | - |
| `lesson/utils/database.py` | method | `DatabaseOptimized.__new__` | 20 | DatabaseOptimized.__new__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/database.py` | method | `DatabaseOptimized.__init__` | 25 | DatabaseOptimized.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/database.py` | method | `DatabaseOptimized.initialize` | 28 | 初始化数据库优化设置 | - |
| `lesson/utils/database.py` | method | `DatabaseOptimized._set_pragmas` | 37 | 设置数据库优化参数 | - |
| `lesson/utils/database.py` | function | `init_db_optimization` | 70 | 初始化数据库优化（应在应用启动时调用） | - |
| `lesson/utils/database.py` | function | `get_db_connection` | 76 | 获取优化后的数据库连接 用法: with get_db_connection("databases/homework.db") as conn: conn.execute("SELECT * FROM homework") | - |
| `lesson/utils/db_config.py` | function | `get_db_path` | 31 | 获取数据库路径 | - |
| `lesson/utils/fonts.py` | function | `get_system` | 35 | 获取操作系统类型 | - |
| `lesson/utils/fonts.py` | function | `get_chinese_font_family` | 40 | 获取适合当前操作系统的中文字体名称 Returns: str: 字体名称 | - |
| `lesson/utils/fonts.py` | function | `get_chinese_fonts_list` | 52 | 获取适合当前操作系统的中文字体列表（按优先级排序） Returns: List[str]: 字体列表 | - |
| `lesson/utils/fonts.py` | function | `get_font_file` | 64 | 获取适合当前操作系统的字体文件名 Returns: str: 字体文件名 | - |
| `lesson/utils/fonts.py` | function | `setup_matplotlib_chinese_font` | 76 | 配置 matplotlib 支持中文显示 用法: import matplotlib.pyplot as plt from utils.fonts import setup_matplotlib_chinese_font setup_mat | - |
| `lesson/utils/fonts.py` | function | `get_available_chinese_font` | 102 | 检测系统中可用的中文字体 Returns: Optional[str]: 第一个可用的中文字体名称，如果没有则返回 None | - |
| `lesson/utils/fonts.py` | function | `get_cached_chinese_font` | 140 | 获取缓存的中文字体（首次调用时检测，后续使用缓存） Returns: str: 可用的中文字体名称 | - |
| `lesson/utils/monitor.py` | function | `_get_disk_path` | 23 | 根据操作系统获取磁盘路径 | - |
| `lesson/utils/monitor.py` | class | `SystemMonitor` | 37 | 系统监控器 | 过长 |
| `lesson/utils/monitor.py` | method | `SystemMonitor.__new__` | 43 | SystemMonitor.__new__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/monitor.py` | method | `SystemMonitor.__init__` | 50 | SystemMonitor.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/monitor.py` | method | `SystemMonitor.initialize` | 56 | 初始化监控器 | - |
| `lesson/utils/monitor.py` | method | `SystemMonitor.get_system_metrics` | 63 | 获取系统指标 | - |
| `lesson/utils/monitor.py` | method | `SystemMonitor._format_uptime` | 130 | 格式化运行时间 | - |
| `lesson/utils/monitor.py` | method | `SystemMonitor._get_basic_metrics` | 142 | 获取基础指标（无 psutil 时） | - |
| `lesson/utils/monitor.py` | method | `SystemMonitor.check_alerts` | 153 | 检查是否需要告警 | - |
| `lesson/utils/monitor.py` | method | `SystemMonitor.get_status` | 178 | 获取系统状态 | - |
| `lesson/utils/monitor.py` | function | `init_monitor` | 201 | 初始化监控器 | - |
| `lesson/utils/monitor.py` | function | `get_system_status` | 206 | 获取系统状态 | - |
| `lesson/utils/monitor.py` | function | `get_metrics` | 211 | 获取系统指标 | - |
| `lesson/utils/monitor.py` | function | `monitor_performance` | 217 | 监控函数执行时间 用法: @monitor_performance(threshold_ms=500) async def slow_function(): ... | - |
| `lesson/utils/monitor.py` | function | `decorator` | 226 | function：decorator | 缺少docstring |
| `lesson/utils/monitor.py` | async_function | `async_wrapper` | 228 | async_function：async_wrapper | 缺少docstring |
| `lesson/utils/monitor.py` | function | `sync_wrapper` | 242 | 同步：sync_wrapper | 缺少docstring |
| `lesson/utils/mysql_db.py` | function | `get_connection_pool` | 26 | 获取或创建MySQL连接池 Args: pool_name: 连接池名称 config_file: 配置文件名 Returns: MySQLConnectionPool: 连接池对象 | - |
| `lesson/utils/mysql_db.py` | function | `get_db_connection` | 71 | 获取数据库连接的上下文管理器 使用方式: with get_db_connection() as conn: cursor = conn.cursor() cursor.execute("SELECT * FROM student") re | - |
| `lesson/utils/mysql_db.py` | class | `MySQLDatabase` | 104 | MySQL数据库操作类 提供便捷的数据库操作方法 | 过长 |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.__init__` | 110 | MySQLDatabase.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.__enter__` | 116 | 进入上下文管理器 | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.__exit__` | 123 | 退出上下文管理器 | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.execute` | 141 | 执行SQL语句（INSERT/UPDATE/DELETE） Args: query: SQL语句 params: 参数 Returns: int: 影响的行数 | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.executemany` | 155 | 批量执行SQL语句 Args: query: SQL语句 params_list: 参数列表 Returns: int: 影响的行数 | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.query_one` | 169 | 查询单条记录 Args: query: SQL语句 params: 参数 Returns: Optional[Dict]: 查询结果（字典形式）或 None | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.query_all` | 183 | 查询多条记录 Args: query: SQL语句 params: 参数 Returns: List[Dict]: 查询结果列表 | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.query_value` | 197 | 查询单个值 Args: query: SQL语句 params: 参数 Returns: Optional[Any]: 查询值或 None | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.lastrowid` | 214 | 获取最后插入的ID Returns: Optional[int]: 最后插入的ID | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.commit` | 223 | 手动提交事务 | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.rollback` | 228 | 手动回滚事务 | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.cursor` | 234 | 获取游标对象（用于高级操作） | - |
| `lesson/utils/mysql_db.py` | method | `MySQLDatabase.connection` | 239 | 获取连接对象（用于高级操作） | - |
| `lesson/utils/mysql_db.py` | function | `execute_query` | 244 | 快捷查询函数（自动管理连接） Args: query: SQL语句 params: 参数 pool_name: 连接池名称 config_file: 配置文件名 fetch_all: 是否获取所有结果 Returns: 查询结果 | - |
| `lesson/utils/mysql_db.py` | function | `execute_insert` | 270 | 快捷插入函数（自动管理连接和事务） Args: query: SQL语句 params: 参数 pool_name: 连接池名称 config_file: 配置文件名 Returns: Optional[int]: 插入的记录ID | - |
| `lesson/utils/mysql_db.py` | function | `execute_update` | 293 | 快捷更新函数（自动管理连接和事务） Args: query: SQL语句 params: 参数 pool_name: 连接池名称 config_file: 配置文件名 Returns: int: 影响的行数 | - |
| `lesson/utils/mysql_db.py` | function | `execute_batch` | 315 | 快捷批量执行函数（自动管理连接和事务） Args: query: SQL语句 params_list: 参数列表 pool_name: 连接池名称 config_file: 配置文件名 Returns: int: 影响的行数 | - |
| `lesson/utils/operation_log.py` | class | `OperationLogger` | 13 | 操作日志记录器 | - |
| `lesson/utils/operation_log.py` | method | `OperationLogger.__init__` | 16 | OperationLogger.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/operation_log.py` | method | `OperationLogger.log` | 25 | 记录操作日志 | - |
| `lesson/utils/operation_log.py` | method | `OperationLogger.info` | 45 | 记录信息日志 | - |
| `lesson/utils/operation_log.py` | method | `OperationLogger.warning` | 49 | 记录警告日志 | - |
| `lesson/utils/operation_log.py` | method | `OperationLogger.error` | 53 | 记录错误日志 | - |
| `lesson/utils/operation_log.py` | function | `log_operation` | 62 | 操作日志装饰器 用法: @log_operation("删除作业") async def delete_homework(hw_id): ... | - |
| `lesson/utils/operation_log.py` | function | `decorator` | 71 | function：decorator | 缺少docstring |
| `lesson/utils/operation_log.py` | async_function | `async_wrapper` | 73 | async_function：async_wrapper | 缺少docstring |
| `lesson/utils/operation_log.py` | function | `sync_wrapper` | 106 | 同步：sync_wrapper | 缺少docstring |
| `lesson/utils/operation_log.py` | function | `log_user_action` | 147 | 记录用户行为 | - |
| `lesson/utils/operation_log.py` | function | `log_system_event` | 152 | 记录系统事件 | - |
| `lesson/utils/paths.py` | function | `get_system` | 13 | 获取操作系统类型 | - |
| `lesson/utils/paths.py` | function | `get_cross_platform_path` | 18 | 从配置字典中获取跨平台路径 配置格式示例: 方式1 - 按系统分类: lesson_dir: Darwin: /Users/yoin/bdsync/temp/lesson Windows: D:/lesson Linux: /home/us | - |
| `lesson/utils/paths.py` | function | `normalize_path` | 78 | 规范化路径，处理不同操作系统的路径分隔符 Args: path: 原始路径 Returns: str: 规范化后的路径 | - |
| `lesson/utils/paths.py` | function | `get_lesson_dir` | 95 | 获取课程数据目录（便捷函数） Args: config: 配置字典 Returns: str: 课程数据目录路径 | - |
| `lesson/utils/rate_limit.py` | class | `RateLimiter` | 13 | 简单的内存限流器 | - |
| `lesson/utils/rate_limit.py` | method | `RateLimiter.__new__` | 18 | RateLimiter.__new__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/rate_limit.py` | method | `RateLimiter._init` | 24 | method：RateLimiter._init | 缺少docstring |
| `lesson/utils/rate_limit.py` | method | `RateLimiter._cleanup` | 30 | 清理过期的请求记录 | - |
| `lesson/utils/rate_limit.py` | method | `RateLimiter.is_allowed` | 38 | 检查请求是否允许 返回: (是否允许, 剩余次数) | - |
| `lesson/utils/rate_limit.py` | method | `RateLimiter.get_remaining` | 67 | 获取剩余请求次数 | - |
| `lesson/utils/rate_limit.py` | method | `RateLimiter.reset` | 75 | 重置限流记录 | - |
| `lesson/utils/rate_limit.py` | function | `check_rate_limit` | 87 | 限流装饰器/检查函数 用法: # 方式1: 手动检查 allowed, remaining = check_rate_limit("user:123", limit=10) # 方式2: 装饰器（需要在异常处理中使用） @check_rat | - |
| `lesson/utils/response.py` | class | `ResponseCode` | 10 | 响应状态码 | - |
| `lesson/utils/response.py` | class | `ResponseModel` | 21 | 统一响应模型 | - |
| `lesson/utils/response.py` | method | `ResponseModel.success` | 25 | 成功响应 Args: data: 响应数据 message: 响应消息 code: 状态码 Returns: JSONResponse | - |
| `lesson/utils/response.py` | method | `ResponseModel.error` | 45 | 错误响应 Args: message: 错误消息 code: 错误状态码 details: 详细错误信息 Returns: JSONResponse | - |
| `lesson/utils/response.py` | method | `ResponseModel.paginate` | 67 | 分页响应 Args: data: 数据列表 page: 当前页码 page_size: 每页数量 total: 总数 message: 响应消息 Returns: JSONResponse | - |
| `lesson/utils/response.py` | function | `success_response` | 96 | 成功响应便捷函数 | - |
| `lesson/utils/response.py` | function | `error_response` | 101 | 错误响应便捷函数 | - |
| `lesson/utils/response.py` | function | `paginate_response` | 106 | 分页响应便捷函数 | - |
| `lesson/utils/response.py` | class | `APIException` | 111 | 自定义 API 异常 | - |
| `lesson/utils/response.py` | method | `APIException.__init__` | 114 | APIException.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/response.py` | class | `NotFoundException` | 121 | 资源不存在异常 | - |
| `lesson/utils/response.py` | method | `NotFoundException.__init__` | 124 | NotFoundException.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/response.py` | class | `UnauthorizedException` | 128 | 未授权异常 | - |
| `lesson/utils/response.py` | method | `UnauthorizedException.__init__` | 131 | UnauthorizedException.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/response.py` | class | `ForbiddenException` | 135 | 禁止访问异常 | - |
| `lesson/utils/response.py` | method | `ForbiddenException.__init__` | 138 | ForbiddenException.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/response.py` | class | `BadRequestException` | 142 | 请求参数错误异常 | - |
| `lesson/utils/response.py` | method | `BadRequestException.__init__` | 145 | BadRequestException.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/sqlite_moral_db.py` | class | `MoralDatabase` | 25 | 德育系统 SQLite 数据库操作类 兼容 MySQLDatabase 接口，API 代码无需修改即可切换 | 过长 |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.__init__` | 32 | 初始化数据库连接 Args: db_path: 数据库文件路径，默认为 databases/moral.db | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.__enter__` | 46 | 进入上下文管理器 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.__exit__` | 60 | 退出上下文管理器 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase._convert_sql` | 79 | 将 MySQL SQL 语句转换为 SQLite SQL 主要转换： - %s 占位符 → ? 占位符 - NOW() → datetime('now') | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase._convert_params` | 95 | 转换参数值，处理 Decimal 类型 Args: params: 原始参数 Returns: 转换后的参数 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.execute` | 119 | 执行 SQL 语句（INSERT/UPDATE/DELETE） Args: query: SQL 语句（支持 %s 占位符） params: 参数 Returns: int: 影响的行数 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.executemany` | 135 | 批量执行 SQL 语句 Args: query: SQL 语句 params_list: 参数列表 Returns: int: 影响的行数 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.query_one` | 151 | 查询单条记录 Args: query: SQL 语句 params: 参数 Returns: Optional[Dict]: 查询结果（字典形式）或 None | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.query_all` | 168 | 查询多条记录 Args: query: SQL 语句 params: 参数 Returns: List[Dict]: 查询结果列表 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.query_value` | 185 | 查询单个值 Args: query: SQL 语句 params: 参数 Returns: Optional[Any]: 查询值或 None | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.lastrowid` | 202 | 获取最后插入的 ID Returns: Optional[int]: 最后插入的 ID | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.commit` | 211 | 手动提交事务 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.rollback` | 216 | 手动回滚事务 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.cursor` | 222 | 获取游标对象 | - |
| `lesson/utils/sqlite_moral_db.py` | method | `MoralDatabase.connection` | 227 | 获取连接对象 | - |
| `lesson/utils/sqlite_moral_db.py` | function | `get_moral_db_path` | 232 | 获取德育数据库路径 | - |
| `lesson/utils/sqlite_moral_db.py` | function | `init_moral_db` | 237 | 初始化德育数据库（应在应用启动时调用） 确保 WAL 模式已启用 | - |
| `lesson/utils/teacher_db.py` | function | `_teacher_id_from_name` | 22 | function：_teacher_id_from_name | 缺少docstring |
| `lesson/utils/teacher_db.py` | class | `TeacherDB` | 27 | 教师数据库操作类，默认连接 moral.db。 | - |
| `lesson/utils/teacher_db.py` | method | `TeacherDB.__init__` | 30 | TeacherDB.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/teacher_db.py` | method | `TeacherDB.__enter__` | 34 | TeacherDB.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/teacher_db.py` | method | `TeacherDB.__exit__` | 42 | TeacherDB.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/utils/teacher_db.py` | method | `TeacherDB.query_one` | 50 | 查询：query_one | 缺少docstring |
| `lesson/utils/teacher_db.py` | method | `TeacherDB.query_all` | 56 | 查询：query_all | 缺少docstring |
| `lesson/utils/teacher_db.py` | method | `TeacherDB.query_value` | 61 | 查询：query_value | 缺少docstring |
| `lesson/utils/teacher_db.py` | method | `TeacherDB.execute` | 67 | method：TeacherDB.execute | 缺少docstring |
| `lesson/utils/teacher_db.py` | method | `TeacherDB.lastrowid` | 72 | method：TeacherDB.lastrowid | 缺少docstring |
| `lesson/utils/teacher_db.py` | function | `get_teacher_db` | 77 | 获取教师数据库连接 | - |
| `lesson/utils/teacher_db.py` | function | `ensure_teacher_schema` | 83 | 确保 moral.teacher 具备登录、教师档案和会员身份字段。 | - |
| `lesson/utils/teacher_db.py` | function | `migrate_auth_teachers_to_moral` | 170 | 把 auth.db.teacher 缺失的教师档案补齐到 moral.db.teacher。 | - |
| `lesson/utils/teacher_db.py` | function | `_teacher_select_sql` | 248 | function：_teacher_select_sql | 缺少docstring |
| `lesson/utils/teacher_db.py` | function | `get_all_teachers` | 280 | 获取所有教师列表 | - |
| `lesson/utils/teacher_db.py` | function | `get_all_teacher_records` | 286 | 获取 teacher 表全部身份记录。仅供管理员维护统一身份表。 | - |
| `lesson/utils/teacher_db.py` | function | `get_teacher_by_name` | 297 | 根据姓名获取教师 | - |
| `lesson/utils/teacher_db.py` | function | `get_teachers_by_role` | 303 | 根据角色获取教师列表（支持多角色匹配） | - |
| `lesson/utils/teacher_db.py` | function | `create_teacher_record` | 312 | 创建教师账号。 | - |
| `lesson/utils/teacher_db.py` | function | `update_teacher_record` | 356 | 按教师姓名更新教师字段。 | - |
| `lesson/utils/teacher_db.py` | function | `delete_teacher_record` | 404 | 删除教师账号。为保留历史引用，实际改为非教师身份并禁用登录。 | - |
| `lesson/utils/teacher_db.py` | function | `get_teachers_dataframe` | 421 | 获取教师数据（返回 DataFrame 格式，兼容旧课表代码） | - |

## 后端招生/应用

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/models/application/application.py` | class | `Application` | 31 | 定义 Application 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/models/application/application.py` | method | `Application.__init__` | 32 | Application.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/application/application.py` | method | `Application.__enter__` | 42 | Application.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/application/application.py` | method | `Application.__exit__` | 47 | Application.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/application/application.py` | method | `Application.query_zy` | 51 | 查询专业 :param zy: 专业 :return: 专业 | - |
| `lesson/models/application/application.py` | method | `Application.query_yx` | 92 | 查询：query_yx | 缺少docstring |
| `lesson/models/application/application.py` | method | `Application.rank_to_score` | 121 | 专业排名转分数 (带缓存) :param rank: 专业排名 :param category: 专业类别 :param year: 年份 :param fangxiang: 方向 :param type: 类型 :return: 分数 | - |
| `lesson/models/application/application.py` | method | `Application.score_to_rank` | 167 | 专业分数转排名 (带缓存) :param score: 专业分数 :param category: 专业类别 :param year: 年份 :param fangxiang: 方向 :param type: 类型 :return: 排名 | - |
| `lesson/models/application/application.py` | method | `Application.toudang` | 213 | 查询投档情况 Args: category: 类别 zy: 专业名称 year: 年份 yx: 院校名称 rank: 位次 fenshu: 分数 fangxiang: 方向 counts: 返回结果数量，-1表示返回全部 Returns:  | 过长 |
| `lesson/models/application/application.py` | method | `Application._get_jihua_info` | 369 | 获取计划信息的通用方法 | - |
| `lesson/models/application/application.py` | method | `Application.get_jh` | 389 | 获取：get_jh | 缺少docstring |
| `lesson/models/application/application.py` | method | `Application.get_xk` | 393 | 获取：get_xk | 缺少docstring |
| `lesson/models/application/application.py` | method | `Application.get_xf` | 397 | 获取：get_xf | 缺少docstring |
| `lesson/models/application/application.py` | method | `Application.batch_get_info` | 401 | 批量获取信息 | - |
| `lesson/models/application/application.py` | method | `Application.toudang_range` | 448 | 根据类别、年份和位次范围查询投档情况 Args: category: 类别，如"普通"、"美术"等 year: 年份 min_rank: 最小位次 max_rank: 最大位次 Returns: pandas.DataFrame: 投档结果 | 过长 |
| `lesson/models/application/application.py` | function | `df_to_png` | 600 | 将DataFrame转换为PNG图片 :param df: DataFrame :param png_name: 图片文件名 :param title: 图片标题 :return: PNG图片路径 | - |
| `lesson/models/application/application.py` | async_function | `zy_jieshao` | 618 | async_function：zy_jieshao | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `yx_jieshao` | 631 | async_function：yx_jieshao | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `zy_template` | 640 | async_function：zy_template | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `yx_template` | 645 | async_function：yx_template | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `rank_template` | 650 | async_function：rank_template | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `zy_toudang` | 655 | async_function：zy_toudang | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `yx_toudang` | 706 | async_function：yx_toudang | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `rank_toudang` | 755 | async_function：rank_toudang | 缺少docstring |
| `lesson/models/application/application.py` | function | `add_watermark` | 795 | 给图片添加水印 Args: image_path: 原图片路径 output_path: 输出图片路径 watermark_text: 水印文字 font_path: 字体路径 font_size: 字体大小 opacity: 透明度 st | - |
| `lesson/models/application/application.py` | function | `calculate_gradient_intervals` | 851 | 计算五级梯度位次区间，根据考生总数动态划分高中低分段 参数: rank -- 考生位次(整数) total_candidates -- 考生总数(整数) category -- 考生类型: '普通' 或 '艺术类' risk_prefere | 过长 |
| `lesson/models/application/application.py` | function | `dynamic_range` | 909 | 动态梯度范围计算函数 base_factor: 基础范围系数 min_span_factor: 最小跨度系数 max_span_factor: 最大跨度系数 rank_span_factor: 位次跨度影响因子 | - |
| `lesson/models/application/application.py` | function | `plot_gradient_strategy` | 1108 | 可视化梯度策略 - 优化X轴刻度和区间标签 | 过长 |
| `lesson/models/application/application.py` | function | `add_segment_marker` | 1165 | function：add_segment_marker | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `gradient_intervals` | 1244 | async_function：gradient_intervals | 缺少docstring |
| `lesson/models/application/application.py` | function | `get_gradient_level` | 1259 | 根据位次、类别、风险偏好和总考生数，返回梯度等级 | - |
| `lesson/models/application/application.py` | function | `check_xk` | 1270 | 检查选科要求是否符合 Args: xk: 考生选科 xkyq: 专业选科要求 Returns: bool: 是否符合选科要求 | - |
| `lesson/models/application/application.py` | async_function | `range_template` | 1295 | async_function：range_template | 缺少docstring |
| `lesson/models/application/application.py` | async_function | `get_gradient_file` | 1303 | 获取：get_gradient_file | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | class | `Application` | 30 | 定义 Application 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/models/application/application_V1.0.py` | method | `Application.__init__` | 31 | Application.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | method | `Application.__enter__` | 38 | Application.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | method | `Application.__exit__` | 43 | Application.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | method | `Application.query_zy` | 47 | 查询专业 :param zy: 专业 :return: 专业 | - |
| `lesson/models/application/application_V1.0.py` | method | `Application.query_yx` | 88 | 查询：query_yx | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | method | `Application.rank_to_score` | 117 | 专业排名转分数 (带缓存) :param rank: 专业排名 :param category: 专业类别 :param year: 年份 :return: 分数 | - |
| `lesson/models/application/application_V1.0.py` | method | `Application.score_to_rank` | 168 | 专业分数转排名 (带缓存) :param score: 专业分数 :param category: 专业类别 :param year: 年份 :return: 排名 | - |
| `lesson/models/application/application_V1.0.py` | method | `Application.toudang` | 218 | 查询投档情况 Args: category: 类别，如"普通类"、"美术类"等 zy: 专业名称 year: 年份 yx: 院校名称 rank: 位次 level: 层次，如"本科"、"专科"等 counts: 返回结果数量，-1表示返回全 | 过长 |
| `lesson/models/application/application_V1.0.py` | method | `Application._get_jihua_info` | 369 | 获取计划信息的通用方法 | - |
| `lesson/models/application/application_V1.0.py` | method | `Application.get_jh` | 389 | 获取：get_jh | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | method | `Application.get_xk` | 393 | 获取：get_xk | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | method | `Application.get_xf` | 397 | 获取：get_xf | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | method | `Application.batch_get_info` | 401 | 批量获取信息 | - |
| `lesson/models/application/application_V1.0.py` | method | `Application.toudang_range` | 448 | 根据类别、年份和位次范围查询投档情况 Args: category: 类别，如"普通类"、"美术类"等 year: 年份 min_rank: 最小位次 max_rank: 最大位次 Returns: pandas.DataFrame: 投档 | 过长 |
| `lesson/models/application/application_V1.0.py` | function | `df_to_png` | 609 | 将DataFrame转换为PNG图片 :param df: DataFrame :param png_name: 图片文件名 :param title: 图片标题 :return: PNG图片路径 | - |
| `lesson/models/application/application_V1.0.py` | async_function | `zy_jieshao` | 627 | async_function：zy_jieshao | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `yx_jieshao` | 640 | async_function：yx_jieshao | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `zy_template` | 649 | async_function：zy_template | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `yx_template` | 654 | async_function：yx_template | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `rank_template` | 659 | async_function：rank_template | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `zy_toudang` | 664 | async_function：zy_toudang | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `yx_toudang` | 715 | async_function：yx_toudang | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `rank_toudang` | 764 | async_function：rank_toudang | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | function | `add_watermark` | 804 | 给图片添加水印 Args: image_path: 原图片路径 output_path: 输出图片路径 watermark_text: 水印文字 font_path: 字体路径 font_size: 字体大小 opacity: 透明度 st | - |
| `lesson/models/application/application_V1.0.py` | function | `calculate_gradient_intervals` | 860 | 计算五级梯度位次区间，根据考生总数动态划分高中低分段 参数: rank -- 考生位次(整数) total_candidates -- 考生总数(整数) category -- 考生类型: '普通类' 或 '艺术类' risk_prefer | 过长 |
| `lesson/models/application/application_V1.0.py` | function | `dynamic_range` | 918 | 动态梯度范围计算函数 base_factor: 基础范围系数 min_span_factor: 最小跨度系数 max_span_factor: 最大跨度系数 rank_span_factor: 位次跨度影响因子 | - |
| `lesson/models/application/application_V1.0.py` | function | `plot_gradient_strategy` | 1117 | 可视化梯度策略 - 优化X轴刻度和区间标签 | 过长 |
| `lesson/models/application/application_V1.0.py` | function | `add_segment_marker` | 1174 | function：add_segment_marker | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `gradient_intervals` | 1253 | async_function：gradient_intervals | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | function | `get_gradient_level` | 1268 | 根据位次、类别、风险偏好和总考生数，返回梯度等级 | - |
| `lesson/models/application/application_V1.0.py` | function | `check_xk` | 1279 | 检查选科要求是否符合 Args: xk: 考生选科 xkyq: 专业选科要求 Returns: bool: 是否符合选科要求 | - |
| `lesson/models/application/application_V1.0.py` | async_function | `range_template` | 1304 | async_function：range_template | 缺少docstring |
| `lesson/models/application/application_V1.0.py` | async_function | `get_gradient_file` | 1312 | 获取：get_gradient_file | 缺少docstring |
| `lesson/models/application/share.py` | async_function | `bd_share` | 8 | 百度分享 :param record: 记录 :return: 分享链接 | - |

## 后端网络设备集成

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/models/network/ess.py` | function | `encrypt` | 28 | function：encrypt | 缺少docstring |
| `lesson/models/network/ess.py` | function | `session` | 36 | function：session | 缺少docstring |
| `lesson/models/network/ess.py` | function | `add_user` | 62 | function：add_user | 缺少docstring |
| `lesson/models/network/ess.py` | function | `del_user` | 77 | function：del_user | 缺少docstring |
| `lesson/models/network/ess.py` | function | `ess_online_user` | 89 | function：ess_online_user | 缺少docstring |
| `lesson/models/network/ess.py` | function | `ess_mac` | 113 | function：ess_mac | 缺少docstring |
| `lesson/models/network/ess.py` | function | `query_user` | 136 | 查询：query_user | 缺少docstring |
| `lesson/models/network/ess.py` | async_function | `add_wifi_user` | 160 | async_function：add_wifi_user | 缺少docstring |
| `lesson/models/network/ess.py` | async_function | `del_wifi_user` | 175 | async_function：del_wifi_user | 缺少docstring |
| `lesson/models/network/ess.py` | async_function | `ess_online` | 184 | async_function：ess_online | 缺少docstring |
| `lesson/models/network/ess.py` | async_function | `ess_mac_async` | 203 | async_function：ess_mac_async | 缺少docstring |
| `lesson/models/network/ess.py` | async_function | `ess_user` | 219 | async_function：ess_user | 缺少docstring |
| `lesson/models/network/ess.py` | function | `black_user` | 235 | function：black_user | 缺少docstring |
| `lesson/models/network/ess.py` | function | `del_black_user` | 250 | function：del_black_user | 缺少docstring |
| `lesson/models/network/ess.py` | async_function | `black_user_async` | 287 | async_function：black_user_async | 缺少docstring |
| `lesson/models/network/ess.py` | async_function | `del_black_user_async` | 295 | async_function：del_black_user_async | 缺少docstring |
| `lesson/models/network/ruijie.py` | function | `run_cmd` | 37 | 返回 strip 后的回显；Invalid 返回空串 | - |
| `lesson/models/network/ruijie.py` | function | `check_core` | 44 | 检查：check_core | 缺少docstring |
| `lesson/models/network/ruijie.py` | async_function | `core_status` | 70 | async_function：core_status | 缺少docstring |
| `lesson/models/network/ruijie.py` | async_function | `core_cmd` | 74 | async_function：core_cmd | 缺少docstring |
| `lesson/models/network/uac-bak.py` | function | `init_driver` | 33 | 初始化：init_driver | 缺少docstring |
| `lesson/models/network/uac-bak.py` | function | `login_uac` | 74 | function：login_uac | 缺少docstring |
| `lesson/models/network/uac-bak.py` | function | `query_user` | 111 | 适用于开发/测试环境，禁用SSL验证 | - |
| `lesson/models/network/uac-bak.py` | function | `query_online_user` | 168 | 适用于开发/测试环境，禁用SSL验证 | - |
| `lesson/models/network/uac-bak.py` | async_function | `query_uac_async` | 224 | 查询：query_uac_async | 缺少docstring |
| `lesson/models/network/uac-bak.py` | function | `get_token` | 250 | 获取：get_token | 缺少docstring |
| `lesson/models/network/uac-bak.py` | function | `del_pc_user` | 286 | 适用于开发/测试环境，禁用SSL验证 | - |
| `lesson/models/network/uac-bak.py` | function | `add_pc_user` | 331 | 适用于开发/测试环境，禁用SSL验证 | - |
| `lesson/models/network/uac-bak.py` | async_function | `del_pc_user_async` | 393 | async_function：del_pc_user_async | 缺少docstring |
| `lesson/models/network/uac-bak.py` | async_function | `add_pc_user_async` | 402 | async_function：add_pc_user_async | 缺少docstring |
| `lesson/models/network/uac-bak.py` | function | `export_pc_user` | 422 | 导出：export_pc_user | 缺少docstring |
| `lesson/models/network/uac-bak.py` | function | `get_one_ip` | 478 | 获取：get_one_ip | 缺少docstring |
| `lesson/models/network/uac-bak.py` | async_function | `get_one_ip_async` | 496 | 获取：get_one_ip_async | 缺少docstring |
| `lesson/models/network/uac.py` | function | `get_token` | 22 | 获取：get_token | 缺少docstring |
| `lesson/models/network/uac.py` | function | `jmy_decrypt` | 32 | function：jmy_decrypt | 缺少docstring |
| `lesson/models/network/uac.py` | function | `crypto_encrypt` | 45 | function：crypto_encrypt | 缺少docstring |
| `lesson/models/network/uac.py` | function | `login_uac` | 73 | function：login_uac | 缺少docstring |
| `lesson/models/network/uac.py` | function | `get_tokenid` | 91 | 获取：get_tokenid | 缺少docstring |
| `lesson/models/network/uac.py` | function | `query_user` | 101 | 适用于开发/测试环境，禁用SSL验证 | - |
| `lesson/models/network/uac.py` | function | `query_online_user` | 154 | 适用于开发/测试环境，禁用SSL验证 | - |
| `lesson/models/network/uac.py` | async_function | `query_uac_async` | 205 | 查询：query_uac_async | 缺少docstring |
| `lesson/models/network/uac.py` | function | `del_pc_user` | 231 | 适用于开发/测试环境，禁用SSL验证 | - |
| `lesson/models/network/uac.py` | function | `add_pc_user` | 273 | 适用于开发/测试环境，禁用SSL验证 | - |
| `lesson/models/network/uac.py` | async_function | `del_pc_user_async` | 337 | async_function：del_pc_user_async | 缺少docstring |
| `lesson/models/network/uac.py` | async_function | `add_pc_user_async` | 346 | async_function：add_pc_user_async | 缺少docstring |
| `lesson/models/network/uac.py` | function | `export_pc_user` | 366 | 导出：export_pc_user | 缺少docstring |
| `lesson/models/network/uac.py` | function | `get_one_ip` | 426 | 获取：get_one_ip | 缺少docstring |
| `lesson/models/network/uac.py` | async_function | `get_one_ip_async` | 444 | 获取：get_one_ip_async | 缺少docstring |
| `lesson/models/network/uac.py` | function | `init_white` | 453 | 初始化：init_white | 缺少docstring |
| `lesson/models/network/uac.py` | function | `black_ip` | 458 | function：black_ip | 缺少docstring |
| `lesson/models/network/uac.py` | async_function | `black_ip_async` | 495 | async_function：black_ip_async | 缺少docstring |
| `lesson/models/network/uac.py` | function | `del_black_ip` | 506 | function：del_black_ip | 缺少docstring |
| `lesson/models/network/uac.py` | async_function | `del_black_ip_async` | 545 | async_function：del_black_ip_async | 缺少docstring |
| `lesson/models/network/uac.py` | function | `high_risk_data` | 556 | function：high_risk_data | 缺少docstring |
| `lesson/models/network/uac.py` | function | `high_risk` | 594 | function：high_risk | 缺少docstring |

## 后端脚本

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/scripts/clear_moral_tables.py` | function | `get_table_count` | 34 | 获取表记录数 | - |
| `lesson/scripts/clear_moral_tables.py` | function | `clear_table` | 44 | 清空表记录，返回删除数量 | - |
| `lesson/scripts/clear_moral_tables.py` | function | `show_status` | 56 | 显示各表当前状态 | - |
| `lesson/scripts/clear_moral_tables.py` | function | `clear_all` | 71 | 清空所有表 | - |
| `lesson/scripts/clear_moral_tables.py` | function | `clear_selected` | 87 | 清空选定的表 | - |
| `lesson/scripts/clear_moral_tables.py` | function | `interactive_mode` | 103 | 交互式选择清空 | - |
| `lesson/scripts/create_invigilation_tables.py` | function | `create_tables` | 19 | 创建监考安排数据库表 | 过长 |
| `lesson/scripts/create_invigilation_tables.py` | function | `init_test_data` | 127 | 初始化测试数据 | - |
| `lesson/scripts/create_moral_tables.py` | function | `create_database_if_not_exists` | 1435 | 创建数据库（如果不存在） | - |
| `lesson/scripts/create_moral_tables.py` | function | `create_tables` | 1457 | 创建所有表 Args: drop_existing: 是否先删除现有表 | - |
| `lesson/scripts/create_moral_tables.py` | function | `verify_tables` | 1509 | 验证MySQL表创建结果 | - |
| `lesson/scripts/create_moral_tables.py` | function | `ensure_sqlite_schema` | 1585 | 补齐已有 SQLite 数据库的增量字段。 | 过长 |
| `lesson/scripts/create_moral_tables.py` | function | `create_sqlite_tables` | 1948 | 创建SQLite表 Args: db_path: 数据库文件路径，默认为 databases/moral.db drop_existing: 是否先删除现有表 | - |
| `lesson/scripts/create_moral_tables.py` | function | `verify_sqlite_tables` | 2010 | 验证SQLite表创建结果 | - |
| `lesson/scripts/create_moral_tables.py` | function | `main` | 2032 | 主函数 | - |
| `lesson/scripts/generate_moral_test_data.py` | function | `generate_test_data` | 17 | 生成测试数据 | 过长 |
| `lesson/scripts/generate_moral_test_data.py` | function | `verify_data_flow` | 165 | 验证数据流转 | - |
| `lesson/scripts/init_databases.py` | function | `clear_tables` | 160 | 清空数据库中的所有表数据（不删除数据库文件） Args: db_name: 数据库文件名 db_config: 数据库配置 Returns: bool: 是否成功 | - |
| `lesson/scripts/init_databases.py` | function | `init_database` | 208 | 初始化单个数据库 Args: db_name: 数据库文件名 db_config: 数据库配置 reset: 是否重置数据库 Returns: bool: 是否成功 | - |
| `lesson/scripts/init_databases.py` | function | `init_all_databases` | 269 | 初始化所有数据库 Args: reset: 是否重置数据库 Returns: dict: 初始化结果 | - |
| `lesson/scripts/init_databases.py` | function | `main` | 305 | function：main | 缺少docstring |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | class | `MySQLConnection` | 43 | MySQL 连接类（迁移专用，不依赖配置文件） | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | method | `MySQLConnection.__init__` | 46 | MySQLConnection.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | method | `MySQLConnection.__enter__` | 51 | MySQLConnection.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | method | `MySQLConnection.__exit__` | 56 | MySQLConnection.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | method | `MySQLConnection.query_one` | 67 | 查询：query_one | 缺少docstring |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | method | `MySQLConnection.query_all` | 71 | 查询：query_all | 缺少docstring |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | method | `MySQLConnection.query_value` | 75 | 查询：query_value | 缺少docstring |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `convert_value` | 120 | 转换 MySQL 值到 SQLite 兼容格式 Args: value: MySQL 值 Returns: SQLite 兼容值 | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `convert_row` | 142 | 转换 MySQL 行数据到 SQLite 兼容格式 Args: row: MySQL 行数据字典 Returns: SQLite 兼容的元组 | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `get_table_columns` | 155 | 获取 MySQL 表的列名列表 Args: mysql_db: MySQL 数据库连接 table_name: 表名 Returns: 列名列表 | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `migrate_table` | 175 | 迁移单个表的数据 Args: mysql_db: MySQL 数据库连接 sqlite_db: SQLite 数据库连接 table_name: 表名 batch_size: 批量插入大小 Returns: 迁移的记录数 | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `verify_migration` | 226 | 验证迁移结果 Args: mysql_db: MySQL 数据库连接 sqlite_db: SQLite 数据库连接 table_name: 表名 Returns: 是否验证通过 | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `run_migration` | 250 | 执行完整迁移 Args: batch_size: 批量插入大小 verify: 是否验证迁移结果 | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `migrate_table_mysql_sqlite_direct` | 313 | 直接迁移单个表（使用已建立的连接） Args: mysql_db: MySQL 数据库连接 sqlite_conn: SQLite 连接 sqlite_cursor: SQLite 游标 table_name: 表名 batch_size: | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `verify_migration_direct` | 360 | 直接验证迁移结果 Args: mysql_db: MySQL 数据库连接 sqlite_conn: SQLite 连接 table_name: 表名 Returns: 是否验证通过 | - |
| `lesson/scripts/migrate_mysql_to_sqlite.py` | function | `main` | 389 | 主函数 | - |
| `lesson/scripts/migrate_to_mysql.py` | class | `DataMigrator` | 35 | 数据迁移器 | 过长 |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.__init__` | 38 | 初始化迁移器 Args: dry_run: 是否只进行模拟运行（不实际写入数据库） | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.load_template_data` | 61 | 加载 Excel 模板数据 Returns: dict: 包含 teachers, class, students 的数据 | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.parse_class_code` | 101 | 解析班级代码，提取级号和班号 Args: class_code: 班级代码，如 "202301" 或 "高一1班" Returns: tuple: (enrollment_year, class_number) | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.parse_class_name` | 152 | 从班级名称解析级号和班号 Args: class_name: 班级名称，如 "2023级1班" 或 "高一1班" Returns: tuple: (enrollment_year, class_number) | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.migrate_grades` | 190 | 迁移级号数据 Args: data: 模板数据 Returns: int: 迁移的级号数量 | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.migrate_classes` | 252 | 迁移班级数据 Args: data: 模板数据 Returns: int: 迁移的班级数量 | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.migrate_students` | 339 | 迁移学生数据 Args: data: 模板数据 Returns: int: 迁移的学生数量 | 过长 |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.migrate_teachers` | 474 | 迁移教师数据 Args: data: 模板数据 Returns: int: 迁移的教师数量 | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.create_initial_semester` | 541 | 创建初始学年学期配置 Returns: int: 创建的记录数 | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.migrate_all` | 607 | 执行完整迁移 Returns: dict: 迁移统计信息 | - |
| `lesson/scripts/migrate_to_mysql.py` | method | `DataMigrator.verify_migration` | 633 | 验证迁移结果 | - |
| `lesson/scripts/migrate_to_mysql.py` | function | `main` | 685 | 主函数 | - |
| `lesson/scripts/remove_daily_record_unique_constraint.py` | function | `migrate` | 20 | 执行迁移 | 过长 |
| `lesson/scripts/verify_invigilation_system.py` | function | `verify_invigilation_system` | 15 | 验证监考安排系统 | - |
| `lesson/scripts/verify_moral_system.py` | function | `verify_data_flow` | 18 | 验证数据流转 | 过长 |

## 后端课表/教学/微信指令

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/models/lesson/generate_qr.py` | function | `get_font` | 31 | 获取跨平台中文字体 | - |
| `lesson/models/lesson/generate_qr.py` | function | `create_qr_code` | 66 | 生成美化二维码 Args: url: 二维码链接 title: 主标题 subtitle: 副标题 logo_path: Logo路径 output_path: 输出路径 theme: 主题 (gradient/elegant/warm)  | 过长 |
| `lesson/models/lesson/generate_qr.py` | function | `add_logo` | 243 | 在二维码中心添加 Logo | - |
| `lesson/models/lesson/generate_qr.py` | function | `main` | 279 | function：main | 缺少docstring |
| `lesson/models/lesson/homework.py` | class | `Homework` | 18 | 定义 Homework 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.__init__` | 19 | Homework.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.__enter__` | 35 | Homework.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.__exit__` | 41 | Homework.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.__create_table__` | 44 | Homework.__create_table__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.add_homework` | 141 | method：Homework.add_homework | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.get_homework` | 159 | 获取：get_homework | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.get_class_homeworks` | 199 | 获取班级指定类型的全部未过期作业，按学科和教师组织。 | - |
| `lesson/models/lesson/homework.py` | method | `Homework.add_announcement` | 208 | method：Homework.add_announcement | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.get_announcement` | 222 | 获取：get_announcement | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.delete_homework` | 250 | 删除：delete_homework | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.delete_announcement` | 262 | 删除：delete_announcement | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.update_homework` | 274 | 更新：update_homework | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.update_announcement` | 307 | 更新：update_announcement | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.get_homework_by_id` | 331 | 获取：get_homework_by_id | 缺少docstring |
| `lesson/models/lesson/homework.py` | method | `Homework.get_announcement_by_id` | 356 | 获取：get_announcement_by_id | 缺少docstring |
| `lesson/models/lesson/homework.py` | async_function | `hw_template` | 378 | async_function：hw_template | 缺少docstring |
| `lesson/models/lesson/homework.py` | async_function | `incert_homework` | 384 | record.content='作业布置 $班级：202401/202402 $学科：地理 $教师：李老师 $内容： 1.完成学案 2.预习新课 3.练习 $上交日期：2024-12-12 $预计用时：20 $ 作业类型：日常' | - |
| `lesson/models/lesson/homework.py` | async_function | `get_class_homework` | 439 | record.content='202401日常作业' | - |
| `lesson/models/lesson/homework.py` | async_function | `incert_announcement` | 463 | async_function：incert_announcement | 缺少docstring |
| `lesson/models/lesson/image_renderer.py` | class | `ImageRenderer` | 17 | DataFrame 图片渲染器。 | - |
| `lesson/models/lesson/image_renderer.py` | method | `ImageRenderer.__init__` | 20 | ImageRenderer.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/image_renderer.py` | method | `ImageRenderer.dataframe_to_png` | 23 | 将 DataFrame 转换为 PNG 图片。 Returns: 包含保存路径的列表，兼容旧的 Lesson.df_to_png 返回格式。 | - |
| `lesson/models/lesson/lesson.py` | function | `error_handler` | 39 | function：error_handler | 缺少docstring |
| `lesson/models/lesson/lesson.py` | function | `wrapper` | 41 | function：wrapper | 缺少docstring |
| `lesson/models/lesson/lesson.py` | class | `Lesson` | 56 | 定义 Lesson 类，承载相关状态和方法 | 过长、缺少docstring |
| `lesson/models/lesson/lesson.py` | method | `Lesson.__new__` | 59 | Lesson.__new__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/lesson.py` | method | `Lesson.__init__` | 65 | Lesson.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/lesson.py` | method | `Lesson.create_c_month_dir` | 94 | 创建当前月份目录 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.notify_admins` | 102 | 通知管理员 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.load_excel_file` | 113 | 加载Excel文件 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.now` | 118 | 获取当前时间 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.c_month` | 123 | 获取当前月份 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.week_info` | 128 | 获取周次信息 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.teacher_template` | 145 | 获取教师模板（从数据库） | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.class_template` | 150 | 获取班级模板 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.students` | 155 | 获取学生列表 | - |
| `lesson/models/lesson/lesson.py` | function | `safe_int_str` | 162 | function：safe_int_str | 缺少docstring |
| `lesson/models/lesson/lesson.py` | method | `Lesson.time_table` | 179 | 获取时间表 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.members` | 184 | 加载会员 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.sync_members` | 188 | 显式同步通讯录，避免普通 Lesson 初始化或缓存刷新触发网络请求。 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.schedule_file` | 195 | 获取课程表文件 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.replace_dict` | 204 | 获取替换字典 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.ignore_subjects` | 210 | 获取忽略列表 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.format_schedule` | 215 | 格式化课程表（优化版） | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.schedule_data` | 219 | 获取当前周课程表文件 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.current_schedule` | 224 | 获取当前周课程表 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.next_schedule` | 230 | 获取下一周课程表 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.today_schedule` | 236 | 获取今日课程表 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.get_weekday_schedule` | 240 | 获取指定日期的课程表（支持传入日期或周几 1-7） | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.refresh_cache` | 244 | 刷新缓存 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.get_cache_data` | 266 | 获取缓存数据 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.member_wxid` | 303 | 加载会员 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.get_wxids` | 309 | 获取：get_wxids | 缺少docstring |
| `lesson/models/lesson/lesson.py` | method | `Lesson._split_subjects` | 322 | 统一处理课表和教师表中的学科字段，兼容空值和非字符串。 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.get_sid` | 326 | 获取学生ID | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.get_alias` | 331 | 获取wxid对应的姓名 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.move_file` | 339 | 移动文件 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.get_subject_teacher` | 349 | 获取学科对应的老师 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.replace_subject_teacher` | 353 | 将课表中的学科替换为对应的老师或学科简称。 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson._title_to_week` | 357 | 将课表标题转换为周历日期 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson._check_schedule_date` | 361 | 检查课表日期是否符合要求 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson._check_schedule_class` | 365 | 检查课表班级是否符合要求 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson._check_repeated_subjects` | 369 | 检查课表中是否有重复学科 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.check_schedule` | 374 | 检查课表是否符合要求, 请先将df_schedule格式化 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.update_schedule_file` | 379 | 课表检查无误后, 更新课表文件 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.schedule_diff` | 383 | 比较课表差异 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.get_class_schedule` | 388 | 获取班级课表 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.get_teacher_schedule` | 392 | 获取教师课表 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.df_to_png` | 396 | 兼容旧入口：将 DataFrame 转换为 PNG 图片。 | - |
| `lesson/models/lesson/lesson.py` | method | `Lesson.current_teaching` | 401 | 获取当前正在上的课程 | - |
| `lesson/models/lesson/lesson.py` | function | `clear_temp_file` | 405 | 清理：clear_temp_file | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `create_month_dir` | 420 | 创建当前月份的文件夹, 并将上课月的课表复制到 新的月份 目录下 | - |
| `lesson/models/lesson/lesson.py` | async_function | `process_and_send_image` | 457 | 异步处理并发送图片 | - |
| `lesson/models/lesson/lesson.py` | async_function | `process_class_schedule` | 461 | 异步处理并发送班级课表图片 | - |
| `lesson/models/lesson/lesson.py` | async_function | `_update_schedule` | 465 | async_function：_update_schedule | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `update_schedule` | 543 | 更新：update_schedule | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `update_schedule_all` | 563 | 更新所有班级和老师的课表 | - |
| `lesson/models/lesson/lesson.py` | async_function | `teacher_schedule` | 571 | 获取指定老师或班级的课表 | - |
| `lesson/models/lesson/lesson.py` | async_function | `get_current_schedule` | 607 | 获取当前本周或下周的课表文件 | - |
| `lesson/models/lesson/lesson.py` | function | `send_today_schedule` | 624 | 发送今日课表（支持传入日期参数） | - |
| `lesson/models/lesson/lesson.py` | function | `take_first_four` | 658 | function：take_first_four | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `get_today_schedule` | 669 | 获取今日课表或指定周几的课表 | - |
| `lesson/models/lesson/lesson.py` | function | `refresh_cache_data` | 685 | 刷新cache数据 | - |
| `lesson/models/lesson/lesson.py` | async_function | `refresh_schedule` | 696 | 刷新cache数据 | - |
| `lesson/models/lesson/lesson.py` | async_function | `get_current_teacher` | 706 | 获取当前正在上课教师 | - |
| `lesson/models/lesson/lesson.py` | function | `today_teachers` | 721 | function：today_teachers | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `current_week_info` | 726 | async_function：current_week_info | 缺少docstring |
| `lesson/models/lesson/lesson.py` | function | `group_send` | 730 | function：group_send | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `mass_message` | 778 | 群发消息 | - |
| `lesson/models/lesson/lesson.py` | async_function | `file_template` | 796 | 获取文件， 根据 file_template 文件配置 文件字典 | - |
| `lesson/models/lesson/lesson.py` | async_function | `pan_share` | 806 | async_function：pan_share | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `sunday_record` | 815 | async_function：sunday_record | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `schedule_tips` | 835 | async_function：schedule_tips | 缺少docstring |
| `lesson/models/lesson/lesson.py` | function | `add_teacher` | 842 | 添加教师 | - |
| `lesson/models/lesson/lesson.py` | function | `delete_teacher` | 854 | 删除教师 | - |
| `lesson/models/lesson/lesson.py` | async_function | `add_teacher_async` | 866 | 异步添加教师 | - |
| `lesson/models/lesson/lesson.py` | async_function | `delete_teacher_async` | 893 | 异步删除教师 | - |
| `lesson/models/lesson/lesson.py` | function | `lesson_pwd` | 902 | function：lesson_pwd | 缺少docstring |
| `lesson/models/lesson/lesson.py` | async_function | `manual_update_schedule` | 925 | 手动更新课程表 | - |
| `lesson/models/lesson/lound.py` | class | `LoudPKUpsertIn` | 11 | 定义 LoudPKUpsertIn 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/lesson/lound.py` | class | `LoudPKItem` | 16 | 定义 LoudPKItem 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/lesson/lound.py` | class | `LoudPKStatsOut` | 23 | 定义 LoudPKStatsOut 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/lesson/lound.py` | class | `LoudPKStore` | 27 | 定义 LoudPKStore 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/lesson/lound.py` | method | `LoudPKStore.__init__` | 28 | LoudPKStore.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/lound.py` | async_method | `LoudPKStore.upsert` | 32 | async_method：LoudPKStore.upsert | 缺少docstring |
| `lesson/models/lesson/lound.py` | async_method | `LoudPKStore.list` | 51 | 列出：list | 缺少docstring |
| `lesson/models/lesson/lound.py` | async_function | `loudpk_upsert` | 68 | 处理路由 /loudpk | 路由、缺少docstring |
| `lesson/models/lesson/lound.py` | async_function | `loudpk_stats` | 73 | 处理路由 /loudpk | 路由、缺少docstring |
| `lesson/models/lesson/notes.py` | class | `Notes` | 18 | 定义 Notes 类，承载相关状态和方法 | 缺少docstring |
| `lesson/models/lesson/notes.py` | method | `Notes.__enter__` | 19 | Notes.__enter__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/notes.py` | method | `Notes.__exit__` | 24 | Notes.__exit__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/notes.py` | method | `Notes.__create_table__` | 27 | Notes.__create_table__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/notes.py` | method | `Notes.insert_note` | 47 | method：Notes.insert_note | 缺少docstring |
| `lesson/models/lesson/notes.py` | method | `Notes.get_notes` | 53 | 获取：get_notes | 缺少docstring |
| `lesson/models/lesson/notes.py` | async_function | `insert_note` | 68 | 触发条件 记录=(.*) 添加课时记录碎片 | - |
| `lesson/models/lesson/notes.py` | async_function | `get_notes` | 88 | 触发条件 ^课时记录查询@9 查询课时记录碎片 | - |
| `lesson/models/lesson/schedule_notifier.py` | class | `ScheduleNotifier` | 14 | 课表通知服务。 | 过长 |
| `lesson/models/lesson/schedule_notifier.py` | method | `ScheduleNotifier.__init__` | 17 | ScheduleNotifier.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/schedule_notifier.py` | async_method | `ScheduleNotifier.process_and_send_image` | 20 | async_method：ScheduleNotifier.process_and_send_image | 缺少docstring |
| `lesson/models/lesson/schedule_notifier.py` | async_method | `ScheduleNotifier.process_class_schedule` | 39 | async_method：ScheduleNotifier.process_class_schedule | 缺少docstring |
| `lesson/models/lesson/schedule_notifier.py` | async_method | `ScheduleNotifier.send_all_schedules` | 59 | 发送：send_all_schedules | 缺少docstring |
| `lesson/models/lesson/schedule_notifier.py` | method | `ScheduleNotifier.today_teachers` | 107 | method：ScheduleNotifier.today_teachers | 缺少docstring |
| `lesson/models/lesson/schedule_repository.py` | class | `ScheduleRepository` | 15 | 课表文件仓储。 | - |
| `lesson/models/lesson/schedule_repository.py` | method | `ScheduleRepository.__init__` | 18 | ScheduleRepository.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/schedule_repository.py` | method | `ScheduleRepository.create_month_dir` | 22 | 创建：create_month_dir | 缺少docstring |
| `lesson/models/lesson/schedule_repository.py` | method | `ScheduleRepository.load_excel_file` | 34 | 加载：load_excel_file | 缺少docstring |
| `lesson/models/lesson/schedule_repository.py` | method | `ScheduleRepository.load_template` | 42 | 加载：load_template | 缺少docstring |
| `lesson/models/lesson/schedule_repository.py` | method | `ScheduleRepository.get_schedule_files` | 49 | 获取：get_schedule_files | 缺少docstring |
| `lesson/models/lesson/schedule_repository.py` | method | `ScheduleRepository.archive_and_replace_schedule` | 62 | method：ScheduleRepository.archive_and_replace_schedule | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | class | `ScheduleService` | 15 | 课表业务服务。 | 过长 |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.__init__` | 18 | ScheduleService.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.format_schedule` | 34 | 格式化：format_schedule | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | function | `process` | 39 | function：process | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.schedule_data` | 57 | method：ScheduleService.schedule_data | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.today_schedule` | 66 | method：ScheduleService.today_schedule | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.get_weekday_schedule` | 79 | 获取：get_weekday_schedule | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.split_subjects` | 123 | method：ScheduleService.split_subjects | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.get_subject_teacher` | 137 | 获取：get_subject_teacher | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.replace_subject_teacher` | 147 | method：ScheduleService.replace_subject_teacher | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | function | `replace_with_teacher` | 156 | function：replace_with_teacher | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.title_to_week` | 163 | method：ScheduleService.title_to_week | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.check_schedule_date` | 173 | 检查：check_schedule_date | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.check_schedule_class` | 188 | 检查：check_schedule_class | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.check_repeated_subjects` | 198 | 检查：check_repeated_subjects | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.check_schedule` | 216 | 检查：check_schedule | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.update_schedule_file` | 230 | 更新：update_schedule_file | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.schedule_diff` | 252 | method：ScheduleService.schedule_diff | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.get_class_schedule` | 285 | 获取：get_class_schedule | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.get_teacher_schedule` | 301 | 获取：get_teacher_schedule | 缺少docstring |
| `lesson/models/lesson/schedule_service.py` | method | `ScheduleService.current_teaching` | 330 | method：ScheduleService.current_teaching | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | function | `hash_teacher_password` | 20 | function：hash_teacher_password | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | class | `TeacherDirectory` | 24 | 教师与通讯录目录。 | 过长 |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.__init__` | 27 | TeacherDirectory.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.get_teacher_template` | 31 | 获取：get_teacher_template | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.get_members` | 34 | 获取：get_members | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.sync_members` | 42 | 同步：sync_members | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.member_wxid` | 47 | method：TeacherDirectory.member_wxid | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.get_wxids` | 57 | 获取：get_wxids | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.get_sid` | 96 | 获取：get_sid | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.get_alias` | 103 | 获取：get_alias | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.add_teacher` | 110 | method：TeacherDirectory.add_teacher | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory.delete_teacher` | 131 | 删除：delete_teacher | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory._get_class_template` | 138 | method：TeacherDirectory._get_class_template | 缺少docstring |
| `lesson/models/lesson/teacher_directory.py` | method | `TeacherDirectory._get_students` | 143 | method：TeacherDirectory._get_students | 缺少docstring |
| `lesson/models/lesson/zhaosheng.py` | async_function | `zhaosheng_dengji` | 11 | async_function：zhaosheng_dengji | 缺少docstring |
| `lesson/models/lesson/zhaosheng.py` | function | `gen_qrcode` | 18 | 生成招生二维码 Args: url: 二维码链接 title: 主标题 subtitle: 副标题（可选） Returns: 生成的二维码图片绝对路径 | - |
| `lesson/models/lesson/zhaosheng.py` | async_function | `async_gen_qrcode` | 51 | 微信消息触发生成二维码 支持 ai_flag=1，AI 智能解析参数 消息格式： 生成二维码 $url: https://example.com $title: 招生报名 $subtitle: 诚邀参与 | - |

## 测试代码

| 文件 | 类型 | 名称 | 行 | 功能说明 | 风险标记 |
|------|------|------|----|----------|----------|
| `lesson/conftest.py` | function | `pytest_configure` | 20 | pytest 配置钩子，在测试收集之前执行 | - |
| `lesson/test_moral_endpoints.py` | function | `create_mock_user` | 17 | 创建：create_mock_user | 缺少docstring |
| `lesson/test_moral_endpoints.py` | function | `test_api_endpoint` | 23 | 通用 API 测试函数 | - |
| `lesson/test_moral_endpoints.py` | function | `main` | 43 | function：main | 过长、缺少docstring |
| `lesson/test_real_db_api.py` | function | `create_mock_user` | 16 | 创建：create_mock_user | 缺少docstring |
| `lesson/test_real_db_api.py` | function | `test_real_db_api` | 22 | 测试真实数据库 API 连接 | - |
| `lesson/tests/test_api.py` | class | `MockUser` | 12 | 模拟用户对象 | - |
| `lesson/tests/test_api.py` | method | `MockUser.__init__` | 14 | MockUser.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/tests/test_api.py` | class | `MockUsersDict` | 19 | 模拟用户数据 | - |
| `lesson/tests/test_api.py` | method | `MockUsersDict.__init__` | 21 | MockUsersDict.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/tests/test_api.py` | method | `MockUsersDict.get` | 69 | method：MockUsersDict.get | 缺少docstring |
| `lesson/tests/test_api.py` | function | `is_admin_user` | 75 | 检查用户是否为管理员 | - |
| `lesson/tests/test_api.py` | function | `check_admin_permission` | 83 | 检查管理员权限，无权限则抛出异常 | - |
| `lesson/tests/test_api.py` | function | `generate_random_password` | 89 | 生成随机密码 | - |
| `lesson/tests/test_api.py` | function | `filter_users_by_role` | 96 | 按角色过滤用户 | - |
| `lesson/tests/test_api.py` | class | `TestAdminPermissionCheck` | 105 | 管理员权限检查测试 | - |
| `lesson/tests/test_api.py` | method | `TestAdminPermissionCheck.test_admin_user_has_permission` | 108 | 管理员应该有权限 | - |
| `lesson/tests/test_api.py` | method | `TestAdminPermissionCheck.test_non_admin_user_no_permission` | 113 | 非管理员应该没有权限 | - |
| `lesson/tests/test_api.py` | method | `TestAdminPermissionCheck.test_combined_role_with_admin` | 118 | 包含admin的组合角色应该有权限 | - |
| `lesson/tests/test_api.py` | method | `TestAdminPermissionCheck.test_jiaowu_user_no_admin_permission` | 123 | 教发部用户没有管理员权限 | - |
| `lesson/tests/test_api.py` | method | `TestAdminPermissionCheck.test_none_user_no_permission` | 128 | None用户没有权限 | - |
| `lesson/tests/test_api.py` | method | `TestAdminPermissionCheck.test_check_admin_permission_raises_for_non_admin` | 132 | 非管理员调用check_admin_permission应该抛出403 | - |
| `lesson/tests/test_api.py` | method | `TestAdminPermissionCheck.test_check_admin_permission_passes_for_admin` | 139 | 管理员调用check_admin_permission不应该抛出异常 | - |
| `lesson/tests/test_api.py` | class | `TestUserListAPI` | 146 | 用户列表API测试 | - |
| `lesson/tests/test_api.py` | method | `TestUserListAPI.test_list_users_returns_all_users` | 149 | 获取用户列表应该返回所有用户 | - |
| `lesson/tests/test_api.py` | method | `TestUserListAPI.test_list_users_includes_required_fields` | 155 | 用户列表应该包含必要字段 | - |
| `lesson/tests/test_api.py` | method | `TestUserListAPI.test_filter_users_by_teacher_role` | 164 | 按teacher角色过滤用户 | - |
| `lesson/tests/test_api.py` | method | `TestUserListAPI.test_filter_users_by_admin_role` | 172 | 按admin角色过滤用户 | - |
| `lesson/tests/test_api.py` | method | `TestUserListAPI.test_filter_users_no_match` | 179 | 过滤不存在的角色返回空列表 | - |
| `lesson/tests/test_api.py` | class | `TestPasswordResetAPI` | 186 | 密码重置API测试 | - |
| `lesson/tests/test_api.py` | method | `TestPasswordResetAPI.test_generate_random_password_length` | 189 | 随机密码长度应该正确 | - |
| `lesson/tests/test_api.py` | method | `TestPasswordResetAPI.test_generate_random_password_contains_alphanumeric` | 194 | 随机密码应该包含字母和数字 | - |
| `lesson/tests/test_api.py` | method | `TestPasswordResetAPI.test_generate_random_password_uniqueness` | 200 | 多次生成的随机密码应该不同 | - |
| `lesson/tests/test_api.py` | method | `TestPasswordResetAPI.test_generate_random_password_custom_length` | 205 | 自定义长度的随机密码 | - |
| `lesson/tests/test_api.py` | class | `TestTeacherCreateAPI` | 211 | 教师创建API测试 | - |
| `lesson/tests/test_api.py` | method | `TestTeacherCreateAPI.test_create_teacher_requires_admin` | 214 | 创建教师需要管理员权限 | - |
| `lesson/tests/test_api.py` | method | `TestTeacherCreateAPI.test_create_teacher_duplicate_check` | 221 | 创建重复教师应该失败 | - |
| `lesson/tests/test_api.py` | method | `TestTeacherCreateAPI.test_create_teacher_new_username` | 227 | 新教师用户名应该不存在 | - |
| `lesson/tests/test_api.py` | class | `TestTeacherUpdateAPI` | 234 | 教师更新API测试 | - |
| `lesson/tests/test_api.py` | method | `TestTeacherUpdateAPI.test_update_teacher_requires_admin` | 237 | 更新教师需要管理员权限 | - |
| `lesson/tests/test_api.py` | method | `TestTeacherUpdateAPI.test_update_teacher_not_found` | 244 | 更新不存在的教师应该失败 | - |
| `lesson/tests/test_api.py` | method | `TestTeacherUpdateAPI.test_update_teacher_fields` | 250 | 教师字段更新模拟 | - |
| `lesson/tests/test_api.py` | class | `TestTeacherDeleteAPI` | 261 | 教师删除API测试 | - |
| `lesson/tests/test_api.py` | method | `TestTeacherDeleteAPI.test_delete_teacher_requires_admin` | 264 | 删除教师需要管理员权限 | - |
| `lesson/tests/test_api.py` | method | `TestTeacherDeleteAPI.test_delete_teacher_not_found` | 271 | 删除不存在的教师应该失败 | - |
| `lesson/tests/test_api.py` | class | `TestPasswordChangeAPI` | 278 | 密码修改API测试 | - |
| `lesson/tests/test_api.py` | method | `TestPasswordChangeAPI.test_admin_cannot_use_teacher_endpoint` | 281 | 管理员不能使用教师密码修改接口 | - |
| `lesson/tests/test_api.py` | method | `TestPasswordChangeAPI.test_teacher_can_use_change_password` | 288 | 教师可以使用密码修改接口 | - |
| `lesson/tests/test_api.py` | method | `TestPasswordChangeAPI.test_password_verification_old_password_correct` | 293 | 旧密码验证正确 | - |
| `lesson/tests/test_api.py` | method | `TestPasswordChangeAPI.test_password_verification_old_password_wrong` | 300 | 旧密码验证错误 | - |
| `lesson/tests/test_api.py` | class | `TestResponseFormat` | 309 | 响应格式测试 | - |
| `lesson/tests/test_api.py` | method | `TestResponseFormat.test_user_list_response_format` | 312 | 用户列表响应格式 | - |
| `lesson/tests/test_api.py` | method | `TestResponseFormat.test_success_response_format` | 328 | 成功响应格式 | - |
| `lesson/tests/test_api.py` | method | `TestResponseFormat.test_error_response_format` | 334 | 错误响应格式 | - |
| `lesson/tests/test_api.py` | class | `TestEdgeCases` | 340 | 边界情况测试 | - |
| `lesson/tests/test_api.py` | method | `TestEdgeCases.test_empty_username` | 343 | 空用户名处理 | - |
| `lesson/tests/test_api.py` | method | `TestEdgeCases.test_special_characters_in_username` | 348 | 用户名特殊字符 | - |
| `lesson/tests/test_api.py` | method | `TestEdgeCases.test_concurrent_user_operations` | 357 | 并发用户操作模拟 | - |
| `lesson/tests/test_api.py` | method | `TestEdgeCases.test_user_with_empty_fields` | 365 | 空字段用户处理 | - |
| `lesson/tests/test_api.py` | method | `TestEdgeCases.test_user_with_missing_fields` | 378 | 缺失字段用户处理 | - |
| `lesson/tests/test_api.py` | class | `TestRoleBasedAccess` | 386 | 基于角色的访问控制测试 | - |
| `lesson/tests/test_api.py` | method | `TestRoleBasedAccess.test_admin_can_access_all_endpoints` | 389 | 管理员可以访问所有端点 | - |
| `lesson/tests/test_api.py` | method | `TestRoleBasedAccess.test_jiaowu_can_list_users` | 395 | 教发部可以查看用户列表（无权限限制） | - |
| `lesson/tests/test_api.py` | method | `TestRoleBasedAccess.test_teacher_cannot_create_teacher` | 401 | 普通教师不能创建教师 | - |
| `lesson/tests/test_api.py` | method | `TestRoleBasedAccess.test_teacher_cannot_delete_teacher` | 407 | 普通教师不能删除教师 | - |
| `lesson/tests/test_api.py` | method | `TestRoleBasedAccess.test_teacher_cannot_update_teacher` | 413 | 普通教师不能更新其他教师 | - |
| `lesson/tests/test_auth.py` | function | `hash_password` | 18 | 生成密码哈希 | - |
| `lesson/tests/test_auth.py` | function | `verify_password` | 23 | 验证密码 | - |
| `lesson/tests/test_auth.py` | function | `verify_password_compat` | 31 | 验证密码，兼容明文和bcrypt | - |
| `lesson/tests/test_auth.py` | function | `create_access_token` | 40 | 创建访问令牌 | - |
| `lesson/tests/test_auth.py` | function | `decode_access_token` | 51 | 解码访问令牌 | - |
| `lesson/tests/test_auth.py` | function | `is_admin_user` | 62 | 检查用户是否为管理员 | - |
| `lesson/tests/test_auth.py` | class | `MockUser` | 73 | 模拟用户对象 | - |
| `lesson/tests/test_auth.py` | method | `MockUser.__init__` | 75 | MockUser.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/tests/test_auth.py` | class | `TestPasswordHashing` | 80 | 密码哈希测试 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordHashing.test_hash_password_creates_bcrypt_hash` | 83 | hash_password应该生成bcrypt格式哈希 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordHashing.test_hash_password_is_different_each_time` | 89 | 每次hash应该生成不同的哈希值（因为有salt） | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordHashing.test_verify_password_with_correct_password` | 96 | 正确密码应该验证成功 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordHashing.test_verify_password_with_wrong_password` | 102 | 错误密码应该验证失败 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordHashing.test_verify_password_with_invalid_hash` | 108 | 无效哈希应该返回False | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordHashing.test_verify_password_with_empty_password` | 112 | 空密码应该验证失败 | - |
| `lesson/tests/test_auth.py` | class | `TestPasswordCompat` | 118 | 密码兼容验证测试 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordCompat.test_verify_compat_with_bcrypt_changed_password` | 121 | 已修改密码应该用bcrypt验证 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordCompat.test_verify_compat_with_bcrypt_wrong_password` | 127 | bcrypt模式下错误密码应该失败 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordCompat.test_verify_compat_with_plaintext_password` | 133 | 未修改密码应该用明文验证 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordCompat.test_verify_compat_with_plaintext_wrong_password` | 138 | 明文模式下错误密码应该失败 | - |
| `lesson/tests/test_auth.py` | method | `TestPasswordCompat.test_verify_compat_invalid_bcrypt_format` | 142 | 非bcrypt格式在bcrypt模式应该失败 | - |
| `lesson/tests/test_auth.py` | class | `TestJWTToken` | 147 | JWT Token测试 | - |
| `lesson/tests/test_auth.py` | method | `TestJWTToken.test_create_access_token_contains_username` | 150 | Token应该包含用户名 | - |
| `lesson/tests/test_auth.py` | method | `TestJWTToken.test_create_access_token_contains_role` | 157 | Token应该包含角色 | - |
| `lesson/tests/test_auth.py` | method | `TestJWTToken.test_create_access_token_has_expiration` | 163 | Token应该有过期时间 | - |
| `lesson/tests/test_auth.py` | method | `TestJWTToken.test_create_access_token_custom_expiry` | 169 | 自定义过期时间应该生效 | - |
| `lesson/tests/test_auth.py` | method | `TestJWTToken.test_decode_expired_token` | 183 | 过期Token解码应该返回None | - |
| `lesson/tests/test_auth.py` | method | `TestJWTToken.test_decode_invalid_token` | 191 | 无效Token解码应该返回None | - |
| `lesson/tests/test_auth.py` | method | `TestJWTToken.test_decode_token_wrong_secret` | 196 | 使用错误密钥解码应该失败 | - |
| `lesson/tests/test_auth.py` | class | `TestAdminCheck` | 206 | 管理员检查测试 | - |
| `lesson/tests/test_auth.py` | method | `TestAdminCheck.test_is_admin_with_admin_role` | 209 | admin角色应该返回True | - |
| `lesson/tests/test_auth.py` | method | `TestAdminCheck.test_is_admin_with_teacher_role` | 214 | teacher角色应该返回False | - |
| `lesson/tests/test_auth.py` | method | `TestAdminCheck.test_is_admin_with_jiaowu_role` | 219 | jiaowu角色应该返回False | - |
| `lesson/tests/test_auth.py` | method | `TestAdminCheck.test_is_admin_with_combined_role` | 224 | 包含admin的组合角色应该返回True | - |
| `lesson/tests/test_auth.py` | method | `TestAdminCheck.test_is_admin_with_dict_user` | 229 | 字典格式用户应该正确判断 | - |
| `lesson/tests/test_auth.py` | method | `TestAdminCheck.test_is_admin_with_none_user` | 234 | None用户应该返回False | - |
| `lesson/tests/test_auth.py` | method | `TestAdminCheck.test_is_admin_with_empty_role` | 238 | 空角色应该返回False | - |
| `lesson/tests/test_auth.py` | class | `TestAuthenticateFlow` | 244 | 认证流程测试 | - |
| `lesson/tests/test_auth.py` | method | `TestAuthenticateFlow.test_authenticate_success_flow` | 247 | 成功认证流程模拟 | - |
| `lesson/tests/test_auth.py` | method | `TestAuthenticateFlow.test_authenticate_failure_wrong_password` | 271 | 密码错误认证失败 | - |
| `lesson/tests/test_auth.py` | method | `TestAuthenticateFlow.test_plaintext_to_bcrypt_migration` | 280 | 明文密码迁移到bcrypt流程 | - |
| `lesson/tests/test_auth.py` | class | `TestSecurityEdgeCases` | 299 | 安全边界测试 | - |
| `lesson/tests/test_auth.py` | method | `TestSecurityEdgeCases.test_empty_password_not_accepted` | 302 | 空密码不应被接受 | - |
| `lesson/tests/test_auth.py` | method | `TestSecurityEdgeCases.test_very_long_password` | 310 | 超长密码bcrypt有72字节限制 | - |
| `lesson/tests/test_auth.py` | method | `TestSecurityEdgeCases.test_special_characters_in_password` | 321 | 特殊字符密码应该能处理 | - |
| `lesson/tests/test_auth.py` | method | `TestSecurityEdgeCases.test_unicode_password` | 327 | Unicode密码应该能处理 | - |
| `lesson/tests/test_auth.py` | method | `TestSecurityEdgeCases.test_token_with_special_username` | 333 | 特殊字符用户名Token应该能处理 | - |
| `lesson/tests/test_migration.py` | class | `MockDatabase` | 8 | 模拟数据库 | - |
| `lesson/tests/test_migration.py` | method | `MockDatabase.__init__` | 10 | MockDatabase.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/tests/test_migration.py` | method | `MockDatabase.execute` | 20 | 执行SQL（简化版） | - |
| `lesson/tests/test_migration.py` | method | `MockDatabase.query` | 62 | 查询（简化版） | - |
| `lesson/tests/test_migration.py` | class | `Result` | 64 | 定义 Result 类，承载相关状态和方法 | 缺少docstring |
| `lesson/tests/test_migration.py` | method | `Result.__init__` | 65 | Result.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/tests/test_migration.py` | method | `Result.first` | 68 | method：Result.first | 缺少docstring |
| `lesson/tests/test_migration.py` | function | `validate_migration` | 89 | 验证迁移结果 | - |
| `lesson/tests/test_migration.py` | class | `TestDataMigration` | 110 | 数据迁移测试 | - |
| `lesson/tests/test_migration.py` | method | `TestDataMigration.test_grade_migration` | 113 | 测试级号迁移 | - |
| `lesson/tests/test_migration.py` | method | `TestDataMigration.test_class_migration` | 122 | 测试班级迁移 | - |
| `lesson/tests/test_migration.py` | method | `TestDataMigration.test_student_migration` | 137 | 测试学生迁移 | - |
| `lesson/tests/test_migration.py` | method | `TestDataMigration.test_teacher_migration` | 152 | 测试教师迁移 | - |
| `lesson/tests/test_migration.py` | method | `TestDataMigration.test_student_class_history_creation` | 164 | 测试班级履历创建 | - |
| `lesson/tests/test_migration.py` | class | `TestMigrationValidation` | 177 | 迁移验证测试 | - |
| `lesson/tests/test_migration.py` | method | `TestMigrationValidation.test_validation_with_data` | 180 | 有数据时验证应该通过 | - |
| `lesson/tests/test_migration.py` | method | `TestMigrationValidation.test_validation_without_data` | 191 | 无数据时验证应该失败 | - |
| `lesson/tests/test_migration.py` | class | `TestSQLParameterCount` | 202 | SQL参数数量测试（验证设计文档中的参数匹配） | - |
| `lesson/tests/test_migration.py` | method | `TestSQLParameterCount.test_grade_insert_parameters` | 205 | grade表INSERT应该有2个参数 | - |
| `lesson/tests/test_migration.py` | method | `TestSQLParameterCount.test_class_insert_parameters` | 211 | class表INSERT应该有6个参数 | - |
| `lesson/tests/test_migration.py` | method | `TestSQLParameterCount.test_student_insert_parameters` | 217 | student表INSERT应该有6个参数+2固定值 | - |
| `lesson/tests/test_migration.py` | method | `TestSQLParameterCount.test_student_class_history_insert_parameters` | 223 | student_class_history表INSERT应该有4个参数+1固定值 | - |
| `lesson/tests/test_migration.py` | method | `TestSQLParameterCount.test_teacher_insert_parameters` | 229 | teacher表INSERT应该有8个参数 | - |
| `lesson/tests/test_moral_api.py` | function | `mock_task_init` | 17 | Mock Task 类的初始化，避免在测试中连接真实数据库 | - |
| `lesson/tests/test_moral_api.py` | function | `create_mock_user` | 24 | 创建模拟用户 | - |
| `lesson/tests/test_moral_api.py` | class | `TestDailyRecordAPI` | 30 | 日常表现记录 API 测试 | - |
| `lesson/tests/test_moral_api.py` | method | `TestDailyRecordAPI.client` | 34 | 创建测试客户端 | - |
| `lesson/tests/test_moral_api.py` | method | `TestDailyRecordAPI.test_get_daily_event_types` | 51 | 测试获取日常事件类型列表 | - |
| `lesson/tests/test_moral_api.py` | method | `TestDailyRecordAPI.test_get_daily_records` | 66 | 测试获取日常表现记录列表 | - |
| `lesson/tests/test_moral_api.py` | method | `TestDailyRecordAPI.test_create_daily_record_unauthorized` | 78 | 测试未授权创建记录 | - |
| `lesson/tests/test_moral_api.py` | class | `TestEvaluationAPI` | 92 | 评价查询 API 测试 | - |
| `lesson/tests/test_moral_api.py` | method | `TestEvaluationAPI.client` | 96 | 创建测试客户端 | - |
| `lesson/tests/test_moral_api.py` | method | `TestEvaluationAPI.test_get_student_evaluation_not_found` | 101 | 测试获取不存在学生的评价 | - |
| `lesson/tests/test_moral_api.py` | class | `TestBirthdayAPI` | 112 | 生日提醒 API 测试 | - |
| `lesson/tests/test_moral_api.py` | method | `TestBirthdayAPI.client` | 116 | 创建测试客户端 | - |
| `lesson/tests/test_moral_api.py` | method | `TestBirthdayAPI.test_get_today_birthdays` | 133 | 测试获取今日生日 | - |
| `lesson/tests/test_moral_api.py` | class | `TestMySQLDatabase` | 145 | MySQL 数据库操作测试 | - |
| `lesson/tests/test_moral_api.py` | method | `TestMySQLDatabase.test_moral_db_context_manager` | 148 | 测试数据库上下文管理器 | - |
| `lesson/tests/test_moral_api.py` | method | `TestMySQLDatabase.test_execute_query_function` | 163 | 测试快捷查询函数 | - |
| `lesson/tests/test_moral_api.py` | class | `TestMoralPermissions` | 175 | 德育系统权限测试 | - |
| `lesson/tests/test_moral_api.py` | method | `TestMoralPermissions.test_moral_permissions_structure` | 178 | 测试权限配置结构 | - |
| `lesson/tests/test_moral_api.py` | method | `TestMoralPermissions.test_check_moral_permission_admin` | 190 | 测试管理员权限检查 | - |
| `lesson/tests/test_moral_api.py` | method | `TestMoralPermissions.test_check_moral_permission_teacher` | 200 | 测试教师权限检查 | - |
| `lesson/tests/test_moral_api.py` | class | `TestMoralUtilities` | 213 | 德育系统工具函数测试 | - |
| `lesson/tests/test_moral_api.py` | method | `TestMoralUtilities.test_calculate_moral_level` | 216 | 测试德育等级计算 | - |
| `lesson/tests/test_moral_api.py` | method | `TestMoralUtilities.test_get_user_role_level` | 228 | 测试用户角色等级获取 | - |
| `lesson/tests/test_moral_data_scope.py` | function | `test_teacher_xuefa_is_not_admin_role` | 22 | function：test_teacher_xuefa_is_not_admin_role | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_api_policy_rejects_multi_role_when_level_is_too_low` | 28 | function：test_api_policy_rejects_multi_role_when_level_is_too_low | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | class | `FakeScopeDB` | 45 | 定义 FakeScopeDB 类，承载相关状态和方法 | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | method | `FakeScopeDB.__init__` | 46 | FakeScopeDB.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | method | `FakeScopeDB.query_one` | 60 | 查询：query_one | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | method | `FakeScopeDB.query_all` | 84 | 查询：query_all | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_teacher_multi_role_is_narrowed_to_api_allowed_role` | 90 | function：test_teacher_multi_role_is_narrowed_to_api_allowed_role | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_class_teacher_can_view_own_class_records_but_edit_only_own_records` | 110 | function：test_class_teacher_can_view_own_class_records_but_edit_only_own_records | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_record_scope_sql_and_row_action_flags_are_consistent` | 143 | function：test_record_scope_sql_and_row_action_flags_are_consistent | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_configured_scope_rules_override_permission_defaults` | 176 | function：test_configured_scope_rules_override_permission_defaults | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_target_scope_rules_can_limit_record_input_to_own_class` | 199 | function：test_target_scope_rules_can_limit_record_input_to_own_class | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_target_scope_rules_can_limit_record_input_to_teaching_classes` | 212 | function：test_target_scope_rules_can_limit_record_input_to_teaching_classes | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_teaching_classes_defaults_to_all_when_no_mapping_exists` | 225 | function：test_teaching_classes_defaults_to_all_when_no_mapping_exists | 缺少docstring |
| `lesson/tests/test_moral_data_scope.py` | function | `test_record_teaching_classes_defaults_to_all_when_no_mapping_exists` | 238 | function：test_record_teaching_classes_defaults_to_all_when_no_mapping_exists | 缺少docstring |
| `lesson/tests/test_permission.py` | function | `check_permission` | 92 | 检查用户是否有某权限 | - |
| `lesson/tests/test_permission.py` | function | `check_class_access` | 107 | 检查用户是否有班级访问权限 | - |
| `lesson/tests/test_permission.py` | class | `MockUser` | 121 | 模拟用户对象 | - |
| `lesson/tests/test_permission.py` | method | `MockUser.__init__` | 123 | MockUser.__init__ 生命周期/魔术方法 | 缺少docstring |
| `lesson/tests/test_permission.py` | class | `TestAdminRole` | 128 | 管理员角色测试 | - |
| `lesson/tests/test_permission.py` | method | `TestAdminRole.test_admin_has_all_permissions` | 131 | 管理员应该拥有所有权限 | - |
| `lesson/tests/test_permission.py` | method | `TestAdminRole.test_admin_level` | 139 | 管理员级别应该是100 | - |
| `lesson/tests/test_permission.py` | class | `TestJiaowuRole` | 144 | 教发部角色测试 | - |
| `lesson/tests/test_permission.py` | method | `TestJiaowuRole.test_has_teacher_manage_permission` | 147 | 应该拥有教师管理权限 | - |
| `lesson/tests/test_permission.py` | method | `TestJiaowuRole.test_has_class_manage_permission` | 152 | 应该拥有班级管理权限 | - |
| `lesson/tests/test_permission.py` | method | `TestJiaowuRole.test_has_schedule_manage_permission` | 157 | 应该拥有课表管理权限 | - |
| `lesson/tests/test_permission.py` | method | `TestJiaowuRole.test_no_admin_permission` | 162 | 不应该拥有admin权限 | - |
| `lesson/tests/test_permission.py` | method | `TestJiaowuRole.test_no_moral_record_own_class` | 167 | 不应该拥有本班德育记录权限 | - |
| `lesson/tests/test_permission.py` | method | `TestJiaowuRole.test_level` | 172 | 级别应该是50 | - |
| `lesson/tests/test_permission.py` | class | `TestXuefaRole` | 177 | 学发部角色测试 | - |
| `lesson/tests/test_permission.py` | method | `TestXuefaRole.test_has_moral_record_manage_permission` | 180 | 应该拥有德育记录管理权限 | - |
| `lesson/tests/test_permission.py` | method | `TestXuefaRole.test_has_punishment_manage_permission` | 185 | 应该拥有处分管理权限 | - |
| `lesson/tests/test_permission.py` | method | `TestXuefaRole.test_has_class_change_approve_permission` | 190 | 应该拥有班级变更审批权限 | - |
| `lesson/tests/test_permission.py` | method | `TestXuefaRole.test_no_teacher_manage_permission` | 195 | 不应该拥有教师管理权限 | - |
| `lesson/tests/test_permission.py` | method | `TestXuefaRole.test_level` | 200 | 级别应该是50 | - |
| `lesson/tests/test_permission.py` | class | `TestCleaderRole` | 205 | 班主任角色测试 | - |
| `lesson/tests/test_permission.py` | method | `TestCleaderRole.test_has_moral_record_own_class_permission` | 208 | 应该拥有本班德育记录权限 | - |
| `lesson/tests/test_permission.py` | method | `TestCleaderRole.test_has_homework_publish_permission` | 213 | 应该拥有作业发布权限 | - |
| `lesson/tests/test_permission.py` | method | `TestCleaderRole.test_has_ai_consultation_own_class_permission` | 218 | 应该拥有本班AI诊疗权限 | - |
| `lesson/tests/test_permission.py` | method | `TestCleaderRole.test_no_moral_record_manage_permission` | 223 | 不应该拥有全局德育记录管理权限 | - |
| `lesson/tests/test_permission.py` | method | `TestCleaderRole.test_no_punishment_manage_permission` | 228 | 不应该拥有处分管理权限 | - |
| `lesson/tests/test_permission.py` | method | `TestCleaderRole.test_level` | 233 | 级别应该是30 | - |
| `lesson/tests/test_permission.py` | class | `TestTeacherRole` | 238 | 教师角色测试 | - |
| `lesson/tests/test_permission.py` | method | `TestTeacherRole.test_has_homework_publish_permission` | 241 | 应该拥有作业发布权限 | - |
| `lesson/tests/test_permission.py` | method | `TestTeacherRole.test_has_schedule_view_permission` | 246 | 应该拥有课表查看权限 | - |
| `lesson/tests/test_permission.py` | method | `TestTeacherRole.test_has_moral_record_input_permission` | 251 | 应该拥有德育记录录入权限 | - |
| `lesson/tests/test_permission.py` | method | `TestTeacherRole.test_no_moral_record_own_class_permission` | 256 | 不应该拥有本班德育记录权限 | - |
| `lesson/tests/test_permission.py` | method | `TestTeacherRole.test_no_announcement_publish_permission` | 261 | 不应该拥有公告发布权限 | - |
| `lesson/tests/test_permission.py` | method | `TestTeacherRole.test_level` | 266 | 级别应该是10 | - |
| `lesson/tests/test_permission.py` | class | `TestStudentRole` | 271 | 学生角色测试 | - |
| `lesson/tests/test_permission.py` | method | `TestStudentRole.test_has_moral_self_view_permission` | 274 | 应该拥有自己德育查看权限 | - |
| `lesson/tests/test_permission.py` | method | `TestStudentRole.test_has_homework_view_permission` | 279 | 应该拥有作业查看权限 | - |
| `lesson/tests/test_permission.py` | method | `TestStudentRole.test_has_birthday_blessing_receive_permission` | 284 | 应该拥有生日祝福接收权限 | - |
| `lesson/tests/test_permission.py` | method | `TestStudentRole.test_no_moral_record_input_permission` | 289 | 不应该拥有德育记录录入权限 | - |
| `lesson/tests/test_permission.py` | method | `TestStudentRole.test_level` | 294 | 级别应该是1 | - |
| `lesson/tests/test_permission.py` | class | `TestParentRole` | 299 | 家长角色测试 | - |
| `lesson/tests/test_permission.py` | method | `TestParentRole.test_has_moral_child_view_permission` | 302 | 应该拥有子女德育查看权限 | - |
| `lesson/tests/test_permission.py` | method | `TestParentRole.test_has_profile_child_view_permission` | 307 | 应该拥有子女画像查看权限 | - |
| `lesson/tests/test_permission.py` | method | `TestParentRole.test_has_birthday_reminder_child_permission` | 312 | 应该拥有子女生日提醒权限 | - |
| `lesson/tests/test_permission.py` | method | `TestParentRole.test_no_homework_view_permission` | 317 | 不应该拥有作业查看权限 | - |
| `lesson/tests/test_permission.py` | method | `TestParentRole.test_level` | 322 | 级别应该是1 | - |
| `lesson/tests/test_permission.py` | class | `TestUnknownRole` | 327 | 未知角色测试 | - |
| `lesson/tests/test_permission.py` | method | `TestUnknownRole.test_no_permissions` | 330 | 未知角色不应该有任何权限 | - |
| `lesson/tests/test_permission.py` | class | `TestCheckClassAccess` | 337 | 班级访问权限测试 | - |
| `lesson/tests/test_permission.py` | method | `TestCheckClassAccess.test_admin_has_access` | 340 | 管理员应该有班级访问权限 | - |
| `lesson/tests/test_permission.py` | method | `TestCheckClassAccess.test_jiaowu_has_access` | 345 | 教发部应该有班级访问权限 | - |
| `lesson/tests/test_permission.py` | method | `TestCheckClassAccess.test_cleader_has_own_class_access` | 350 | 班主任应该有本班访问权限 | - |
| `lesson/tests/test_permission.py` | class | `TestRoleLevelHierarchy` | 356 | 角色级别层级测试 | - |
| `lesson/tests/test_permission.py` | method | `TestRoleLevelHierarchy.test_admin_is_highest` | 359 | 管理员级别最高 | - |
| `lesson/tests/test_permission.py` | method | `TestRoleLevelHierarchy.test_level_order` | 364 | 级别顺序应该正确 | - |

