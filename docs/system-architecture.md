# 班级管理系统 - 系统功能架构文档

## 版本信息
- 当前版本：v3.1.1
- 更新日期：2026-03-29

---

## 一、系统概述

班级管理系统是一个综合性的学校管理平台，集成了课程管理、德育评价、用户管理、文件管理等多个功能模块。

### 技术栈
- **后端**：Python 3.10 + FastAPI + MySQL + SQLite
- **前端**：Vue 3 + Element Plus + Vite
- **认证**：JWT Token

---

## 二、后端API功能梳理

### 2.1 API模块总览

| 模块 | 端点数量 | 说明 |
|------|----------|------|
| 认证模块 | 1 | 用户登录认证 |
| 德育-基础管理 | 15 | 级号/班级/学生/学年学期/日志/配置 |
| 德育-日常表现 | 7 | 日常事件类型与记录管理 |
| 德育-校级事件 | 7 | 校级事件类型与记录管理 |
| 德育-德育任务 | 6 | 任务管理与完成记录 |
| 德育-处分管理 | 4 | 处分记录与撤销 |
| 德育-评价查询 | 4 | 德育评价计算与查询 |
| 德育-学生画像 | 4 | 学生画像生成与管理 |
| 德育-生日提醒 | 7 | 生日提醒管理 |
| 德育-AI诊疗 | 6 | 学生问题诊疗 |
| 用户管理 | 7 | 用户CRUD与密码管理 |
| 文件管理 | 9 | 文件上传下载管理 |
| **总计** | **77** | - |

### 2.2 认证模块

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/token` | 用户登录获取Token | 公开 |

### 2.3 德育评价系统API

#### 2.3.1 基础管理 `/api/moral/admin`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/grades` | 获取级号列表 | 登录用户 |
| POST | `/grades` | 创建级号 | grade_manage |
| DELETE | `/grades/{id}` | 删除级号 | grade_manage |
| GET | `/classes` | 获取班级列表 | 登录用户 |
| POST | `/classes` | 创建班级 | class_manage |
| PUT | `/classes/{id}` | 更新班级 | class_manage |
| DELETE | `/classes/{id}` | 删除班级 | class_manage |
| GET | `/school-years` | 获取学年列表 | 登录用户 |
| POST | `/school-years` | 创建学年 | semester_manage |
| GET | `/semesters` | 获取学期列表 | 登录用户 |
| POST | `/semesters` | 创建学期 | semester_manage |
| POST | `/semesters/{id}/set-current` | 设置当前学期 | semester_manage |
| GET | `/students` | 获取学生列表 | 登录用户 |
| POST | `/students` | 创建学生 | student_manage |
| PUT | `/students/{id}/status` | 更新学生状态 | student_manage |
| GET | `/logs` | 获取操作日志 | report_view_all |
| GET | `/config` | 获取系统配置 | report_view_all |
| PUT | `/config` | 更新系统配置 | semester_manage |

#### 2.3.2 日常表现 `/api/moral/daily-records`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/types` | 获取事件类型列表 | 登录用户 |
| POST | `/types` | 创建事件类型 | event_type_manage |
| PUT | `/types/{id}` | 更新事件类型 | event_type_manage |
| DELETE | `/types/{id}` | 删除事件类型 | event_type_manage |
| GET | `/` | 获取记录列表 | 登录用户 |
| POST | `/` | 创建记录 | moral_record_input |
| POST | `/batch` | 批量创建记录 | moral_record_input |
| PUT | `/{id}` | 更新记录 | 登录用户 |
| DELETE | `/{id}` | 删除记录 | 登录用户 |
| GET | `/statistics/student/{id}` | 学生统计 | 登录用户 |

#### 2.3.3 校级事件 `/api/moral/school-records`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/types` | 获取事件类型列表 | 登录用户 |
| POST | `/types` | 创建事件类型 | event_type_manage |
| PUT | `/types/{id}` | 更新事件类型 | event_type_manage |
| DELETE | `/types/{id}` | 删除事件类型 | event_type_manage |
| GET | `/` | 获取记录列表 | 登录用户 |
| POST | `/` | 创建记录 | moral_record_manage |
| PUT | `/{id}` | 更新记录 | moral_record_manage |
| DELETE | `/{id}` | 删除记录 | moral_record_manage |

#### 2.3.4 德育任务 `/api/moral/tasks`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/` | 获取任务列表 | 登录用户 |
| POST | `/` | 创建任务 | moral_record_manage |
| PUT | `/{id}` | 更新任务 | moral_record_manage |
| DELETE | `/{id}` | 删除任务 | moral_record_manage |
| GET | `/finish` | 获取完成记录 | 登录用户 |
| POST | `/finish` | 记录任务完成 | 登录用户 |

#### 2.3.5 处分管理 `/api/moral/punishments`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/` | 获取处分列表 | 登录用户 |
| POST | `/` | 创建处分 | punishment_manage |
| PUT | `/{id}` | 更新处分 | punishment_manage |
| POST | `/{id}/revoke` | 撤销处分 | punishment_manage |

#### 2.3.6 评价查询 `/api/moral/evaluations`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/student/{id}` | 学生评价 | 登录用户 |
| GET | `/class/{id}` | 班级评价汇总 | 登录用户 |
| GET | `/grade/{id}` | 年级评价汇总 | 登录用户 |
| POST | `/calculate` | 计算评价 | 登录用户 |

#### 2.3.7 学生画像 `/api/moral/profiles`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/student/{id}` | 获取学生画像 | 登录用户 |
| POST | `/student/{id}/generate` | 生成学生画像 | student_profile |
| POST | `/batch-generate` | 批量生成画像 | student_profile |
| GET | `/config` | 获取画像配置 | 登录用户 |

#### 2.3.8 生日提醒 `/api/moral/birthdays`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/upcoming` | 即将生日列表 | 登录用户 |
| GET | `/today` | 今日生日列表 | 登录用户 |
| GET | `/reminders` | 提醒记录列表 | 登录用户 |
| POST | `/reminders` | 创建提醒 | birthday_reminder |
| POST | `/reminders/{id}/send` | 发送提醒 | birthday_reminder |
| GET | `/config` | 获取配置 | 登录用户 |
| POST | `/generate` | 生成月度提醒 | birthday_reminder |

#### 2.3.9 AI诊疗 `/api/moral/consultations`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/` | 获取诊疗列表 | 登录用户 |
| POST | `/` | 创建诊疗会话 | ai_consultation |
| GET | `/{id}` | 获取会话详情 | 登录用户 |
| PUT | `/{id}` | 更新会话 | 登录用户 |
| POST | `/{id}/messages` | 添加消息 | 登录用户 |
| POST | `/{id}/close` | 关闭会话 | 登录用户 |

### 2.4 用户管理API `/api`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/users` | 获取用户列表 | admin |
| POST | `/reset-password` | 重置密码 | admin |
| POST | `/set-password` | 设置密码 | 登录用户 |
| PUT | `/{username}` | 更新用户 | admin |
| DELETE | `/{username}` | 删除用户 | admin |
| POST | `/change-password` | 修改密码 | 登录用户 |

### 2.5 文件管理API `/api`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| POST | `/upload` | 上传文件 | 登录用户 |
| GET | `/my-files` | 我的文件 | 登录用户 |
| DELETE | `/my-files/{id}` | 删除文件 | 登录用户 |
| GET | `/admin/files` | 文件列表 | jiaowu |
| GET | `/admin/done-files` | 已查阅文件 | jiaowu |
| POST | `/admin/mark-done/{id}` | 标记已阅 | jiaowu |
| GET | `/admin/download/{id}` | 下载文件 | jiaowu |
| GET | `/admin/statistics` | 统计信息 | jiaowu |
| GET | `/admin/months` | 月份列表 | jiaowu |

---

## 三、前端页面功能梳理

### 3.1 页面总览

| 分类 | 页面数 | 说明 |
|------|--------|------|
| 班级模块 | 4 | 班级作业/信息/学生/公告 |
| 课表模块 | 3 | 课程表/实时课程/课表文件 |
| 常规模块 | 4 | 延时申请/请假记录/常规记录/查询 |
| 趣味模块 | 2 | 随机点名/大声PK |
| 教师模块 | 4 | 发布作业/公告/文件上传/我的文件 |
| 教务模块 | 3 | 文件管理/已查阅/更新课表 |
| 系统管理 | 5 | 会员/权限/任务/系统监控/教师管理 |
| 德育评价 | 13 | 日常表现/校级事件/任务/处分/评价/画像/生日/配置管理 |
| **总计** | **38** | - |

### 3.2 页面清单

#### 班级模块
| 路由 | 页面 | 说明 |
|------|------|------|
| `/homework` | Homework.vue | 班级作业 |
| `/basic-info` | BasicInfo.vue | 班级信息 |
| `/class-students` | ClassStudents.vue | 班级学生 |
| `/announcement` | Announcement.vue | 班级公告 |

#### 课表模块
| 路由 | 页面 | 说明 |
|------|------|------|
| `/schedule` | Schedule.vue | 课程表 |
| `/current-classes` | CurrentClasses.vue | 实时课程 |
| `/schedules` | Schedules.vue | 课表文件 |

#### 常规模块
| 路由 | 页面 | 说明 |
|------|------|------|
| `/delay-application` | DelayApplication.vue | 延时申请 |
| `/leave-record` | LeaveRecord.vue | 请假记录 |
| `/routine-record` | RoutineRecord.vue | 常规记录 |
| `/routine-query` | RoutineQuery.vue | 常规查询 |

#### 趣味模块
| 路由 | 页面 | 说明 |
|------|------|------|
| `/random-call` | RandomCall.vue | 随机点名 |
| `/loud-pk` | LoudPK.vue | 大声PK |

#### 教师模块
| 路由 | 页面 | 说明 |
|------|------|------|
| `/publish-homework` | PublishHomework.vue | 发布作业 |
| `/publish-announcement` | PublishAnnouncement.vue | 发布公告 |
| `/file-upload` | FileUpload.vue | 文件上传 |
| `/my-files` | MyFiles.vue | 我的文件 |

#### 教务模块
| 路由 | 页面 | 说明 |
|------|------|------|
| `/admin-files` | AdminFiles.vue | 文件管理 |
| `/admin-files-done` | AdminFilesDone.vue | 已查阅文件 |
| `/upload-schedule` | UploadSchedule.vue | 更新课表 |

#### 系统管理
| 路由 | 页面 | 说明 |
|------|------|------|
| `/member-manage` | MemberManage.vue | 会员管理 |
| `/permission-manage` | PermissionManage.vue | 权限管理 |
| `/task-manage` | TaskManage.vue | 任务管理 |
| `/system-monitor` | SystemMonitor.vue | 系统监控 |
| `/teacher-manage` | TeacherManage.vue | 教师管理 |

#### 德育评价
| 路由 | 页面 | 说明 |
|------|------|------|
| `/moral/daily-record` | DailyRecord.vue | 日常表现记录 |
| `/moral/school-event` | SchoolEvent.vue | 校级事件 |
| `/moral/task` | TaskManage.vue | 德育任务 |
| `/moral/punishment` | Punishment.vue | 处分管理 |
| `/moral/evaluation` | Evaluation.vue | 评价查询 |
| `/moral/profile` | StudentProfile.vue | 学生画像 |
| `/moral/birthday` | Birthday.vue | 生日提醒 |
| `/moral/config` | config/Index.vue | 德育配置入口 |
| `/moral/config/grade` | config/GradeManage.vue | 级号管理 |
| `/moral/config/class` | config/ClassManage.vue | 班级管理 |
| `/moral/config/student` | config/StudentManage.vue | 学生管理 |
| `/moral/config/semester` | config/SemesterManage.vue | 学年学期管理 |
| `/moral/config/event-type` | config/EventTypeManage.vue | 事件类型管理 |

---

## 四、角色权限体系

### 4.1 角色定义

| 角色 | 等级 | 说明 |
|------|------|------|
| admin | 100 | 系统管理员，拥有所有权限 |
| jiaowu | 60 | 教发部，负责教学管理 |
| xuefa | 50 | 学发部，负责德育管理 |
| cleader | 30 | 班主任，管理本班事务 |
| teacher | 10 | 教师，基础教学功能 |
| student | 1 | 学生，查看个人信息 |
| parent | 1 | 家长，查看子女信息 |

### 4.2 权限清单

| 权限 | admin | jiaowu | xuefa | cleader | teacher | student | parent |
|------|-------|--------|-------|---------|---------|---------|--------|
| all | ✅ | - | - | - | - | - | - |
| moral_record_manage | ✅ | ✅ | ✅ | - | - | - | - |
| punishment_manage | ✅ | - | ✅ | - | - | - | - |
| event_type_manage | ✅ | ✅ | ✅ | - | - | - | - |
| student_manage | ✅ | ✅ | ✅ | - | - | - | - |
| class_manage | ✅ | ✅ | - | - | - | - | - |
| grade_manage | ✅ | ✅ | - | - | - | - | - |
| semester_manage | ✅ | ✅ | - | - | - | - | - |
| moral_record_own_class | ✅ | - | - | ✅ | - | - | - |
| moral_record_input | ✅ | - | - | - | ✅ | - | - |
| moral_self_view | ✅ | - | - | - | - | ✅ | - |
| moral_child_view | ✅ | - | - | - | - | - | ✅ |
| student_profile | ✅ | ✅ | ✅ | ✅ | - | - | - |
| ai_consultation | ✅ | - | ✅ | ✅ | - | - | - |
| birthday_reminder | ✅ | ✅ | ✅ | ✅ | - | - | - |
| report_view_all | ✅ | ✅ | ✅ | - | - | - | - |

---

## 五、数据库表结构

### 5.1 表清单（共35张）

| 分类 | 表名 | 说明 |
|------|------|------|
| 基础数据 | school_year | 学年表 |
| | semester | 学期表 |
| | grade | 级号表 |
| | grade_level_config | 年级等级配置 |
| | class | 班级表 |
| | student | 学生表 |
| | teacher | 教师表 |
| | role | 角色配置表 |
| | student_class_history | 班级履历表 |
| | student_status_change | 学籍变动表 |
| 德育核心 | daily_event_type | 日常事件类型 |
| | school_event_type | 校级事件类型 |
| | grade_moral_task | 德育任务 |
| | student_daily_record | 日常表现记录 |
| | student_school_record | 校级事件记录 |
| | student_task_finish | 任务完成记录 |
| | punishment_record | 处分记录 |
| | collective_event | 集体事件 |
| | collective_event_distribution | 集体事件分配 |
| | moral_evaluation | 德育评价 |
| 扩展功能 | student_profile | 学生画像 |
| | student_profile_history | 画像历史 |
| | profile_config | 画像配置 |
| | ai_consultation | AI诊疗会话 |
| | ai_consultation_message | 诊疗消息 |
| | birthday_reminder | 生日提醒 |
| | birthday_reminder_config | 生日提醒配置 |
| 配置管理 | violation_escalation_rule | 违纪累进规则 |
| | semester_carryover_config | 学期结转配置 |
| | data_visibility_config | 数据可见性配置 |
| | warning_config | 预警配置 |
| | warning_log | 预警日志 |
| | task_carryover_log | 任务结转日志 |
| | moral_operation_log | 操作日志 |
| | moral_config | 系统配置 |

### 5.2 当前数据统计

| 数据项 | 数量 |
|--------|------|
| 级号 | 4 |
| 班级 | 16 |
| 学生 | 591 |
| 教师 | 61 |
| 学期 | 6 |

---

## 六、配置管理状态

### 6.1 配置能力总览

| 配置项 | 前端页面 | 后端API | 状态 |
|--------|----------|---------|------|
| 级号管理 | ✅ GradeManage.vue | ✅ CRUD | ✅ 已完成 |
| 班级管理 | ✅ ClassManage.vue | ✅ CRUD | ✅ 已完成 |
| 学生管理 | ✅ StudentManage.vue | ✅ CRUD | ✅ 已完成 |
| 学年学期 | ✅ SemesterManage.vue | ✅ CRUD | ✅ 已完成 |
| 日常事件类型 | ✅ EventTypeManage.vue | ✅ CRUD | ✅ 已完成 |
| 校级事件类型 | ✅ EventTypeManage.vue | ✅ CRUD | ✅ 已完成 |
| 操作日志 | ✅ Index.vue | ✅ GET | ✅ 已完成 |
| 系统配置 | ✅ Index.vue | ✅ GET/PUT | ✅ 已完成 |

---

## 七、系统访问信息

### 7.1 开发环境
- **前端**：https://localhost:3333/
- **后端**：http://localhost:8000/
- **API文档**：http://localhost:8000/docs

### 7.2 数据库
- **MySQL**：172.31.25.228:3306
- **数据库**：moral_evaluation

### 7.3 测试账号
| 用户名 | 角色 |
|--------|------|
| 管理员 | admin |
| 教发部 | jiaowu |
| 学发部 | xuefa |
| 张班主任 | cleader |
| 李老师 | teacher |

---

## 八、测试状态

### 8.1 测试统计
| 类型 | 数量 | 状态 |
|------|------|------|
| 后端单元测试 | 139 | ✅ 全部通过 |
| API端点测试 | 6 | ✅ 全部通过 |
| 前端构建 | - | ✅ 成功 |

---

## 九、更新日志

### v3.1.1 (2026-03-29)
- 新增 moral_config 系统配置表（共35张表）
- 添加数据库连接测试脚本
- 添加 API 端点测试脚本
- 验证前后端联调正常

### v3.1.0 (2026-03-29)
- 完善德育评价系统配置管理功能
- 新增前端配置管理页面（级号/班级/学生/学期/事件类型）
- 新增事件类型管理 API（CRUD）
- 新增操作日志查询 API
- 新增系统配置 API
- 新增删除班级 API

### v3.0.0 (2026-03-29)
- 新增德育评价系统完整功能
- 新增10个后端API模块，45个API端点
- 新增7个前端页面组件
- 新增MySQL连接池管理
- 新增数据迁移脚本
- 139个测试用例全部通过

### v2.0.0
- 模块化API重构
- 新增文件管理功能

### v1.0.0
- 初始版本
- 基础班级管理功能