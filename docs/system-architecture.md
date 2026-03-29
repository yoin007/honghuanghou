# 班级管理系统 - 系统功能架构文档

## 版本信息
- 当前版本：v3.0.0
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
| 德育-基础管理 | 14 | 级号/班级/学生/学年学期 |
| 德育-日常表现 | 5 | 日常事件记录管理 |
| 德育-校级事件 | 3 | 校级事件记录管理 |
| 德育-德育任务 | 4 | 任务管理与完成记录 |
| 德育-处分管理 | 2 | 处分记录与撤销 |
| 德育-评价查询 | 4 | 德育评价计算与查询 |
| 德育-学生画像 | 4 | 学生画像生成与管理 |
| 德育-生日提醒 | 7 | 生日提醒管理 |
| 德育-AI诊疗 | 4 | 学生问题诊疗 |
| 用户管理 | 7 | 用户CRUD与密码管理 |
| 文件管理 | 9 | 文件上传下载管理 |
| **总计** | **64** | - |

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
| GET | `/school-years` | 获取学年列表 | 登录用户 |
| POST | `/school-years` | 创建学年 | semester_manage |
| GET | `/semesters` | 获取学期列表 | 登录用户 |
| POST | `/semesters` | 创建学期 | semester_manage |
| POST | `/semesters/{id}/set-current` | 设置当前学期 | semester_manage |
| GET | `/students` | 获取学生列表 | 登录用户 |
| POST | `/students` | 创建学生 | student_manage |
| PUT | `/students/{id}/status` | 更新学生状态 | student_manage |

#### 2.3.2 日常表现 `/api/moral/daily-records`

| 方法 | 端点 | 说明 | 权限 |
|------|------|------|------|
| GET | `/types` | 获取事件类型列表 | 登录用户 |
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
| 德育评价 | 7 | 日常表现/校级事件/任务/处分/评价/画像/生日 |
| **总计** | **32** | - |

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
| student_manage | ✅ | ✅ | ✅ | - | - | - | - |
| class_manage | ✅ | ✅ | - | - | - | - | - |
| grade_manage | ✅ | ✅ | - | - | - | - | - |
| semester_manage | ✅ | ✅ | - | - | - | - | - |
| moral_record_own_class | ✅ | - | - | ✅ | - | - | - |
| moral_record_input | ✅ | - | - | - | ✅ | - | - |
| moral_self_view | ✅ | - | - | - | - | ✅ | - |
| moral_child_view | ✅ | - | - | - | - | - | ✅ |
| student_profile | ✅ | ✅ | ✅ | - | - | - | - |
| ai_consultation | ✅ | - | ✅ | ✅ | - | - | - |
| birthday_reminder | ✅ | ✅ | ✅ | - | - | - | - |

---

## 五、数据库表结构

### 5.1 表清单

| 分类 | 表名 | 说明 |
|------|------|------|
| 基础数据 | grade | 级号表 |
| | class | 班级表 |
| | student | 学生表 |
| | teacher | 教师表 |
| | student_class_history | 班级履历表 |
| | school_year | 学年表 |
| | semester | 学期表 |
| 德育核心 | daily_event_type | 日常事件类型 |
| | school_event_type | 校级事件类型 |
| | grade_moral_task | 德育任务 |
| | student_daily_record | 日常表现记录 |
| | student_school_record | 校级事件记录 |
| | student_task_finish | 任务完成记录 |
| | punishment_record | 处分记录 |
| | moral_evaluation | 德育评价 |
| 扩展功能 | student_profile | 学生画像 |
| | ai_consultation | AI诊疗会话 |
| | consultation_message | 诊疗消息 |
| | birthday_reminder | 生日提醒 |
| | moral_operation_log | 操作日志 |
| **总计** | **20+** | - |

---

## 六、可视化配置方案

### 6.1 现有配置能力

| 配置项 | 前端页面 | 后端API | 状态 |
|--------|----------|---------|------|
| 级号管理 | ❌ | ✅ CRUD | 需前端 |
| 班级管理 | ❌ | ✅ CRUD | 需前端 |
| 学生管理 | ❌ | ✅ CRUD | 需前端 |
| 学年学期 | ❌ | ✅ CRUD | 需前端 |
| 日常事件类型 | ❌ | ✅ GET | 需完善 |
| 校级事件类型 | ❌ | ✅ GET | 需完善 |
| 德育任务 | ✅ | ✅ CRUD | 已完成 |
| 处分类型 | - | - | 需新增 |

### 6.2 缺失功能清单

#### 后端API缺失
1. **事件类型管理API**
   - POST/PUT/DELETE `/api/moral/daily-records/types`
   - POST/PUT/DELETE `/api/moral/school-records/types`

2. **系统配置API**
   - GET/POST `/api/moral/config/settings` - 系统参数
   - GET `/api/moral/config/permissions` - 权限配置

3. **操作日志API**
   - GET `/api/moral/logs` - 操作日志查询

#### 前端页面缺失
1. **系统配置模块**
   - 级号管理页面
   - 班级管理页面
   - 学生管理页面
   - 学年学期管理页面
   - 事件类型配置页面

### 6.3 实施计划

---

## 七、功能补充详细计划

### 7.1 后端API补充计划

#### 7.1.1 日常事件类型管理API

**文件**：`models/datas_api/moral/daily_record.py`

| 任务 | 方法 | 端点 | 请求体 | 说明 |
|------|------|------|--------|------|
| 新增类型 | POST | `/types` | `{event_name, event_type, score, description}` | 创建事件类型 |
| 更新类型 | PUT | `/types/{type_id}` | `{event_name, score, is_active}` | 更新事件类型 |
| 删除类型 | DELETE | `/types/{type_id}` | - | 删除事件类型 |

**Pydantic模型**：
```python
class DailyEventTypeCreate(BaseModel):
    event_name: str
    event_type: int  # 1=积极, 2=消极
    score: int
    description: Optional[str] = None

class DailyEventTypeUpdate(BaseModel):
    event_name: Optional[str]
    score: Optional[int]
    is_active: Optional[int]
```

#### 7.1.2 校级事件类型管理API

**文件**：`models/datas_api/moral/school_event.py`

| 任务 | 方法 | 端点 | 请求体 | 说明 |
|------|------|------|--------|------|
| 新增类型 | POST | `/types` | `{event_name, event_type, score, description}` | 创建事件类型 |
| 更新类型 | PUT | `/types/{type_id}` | `{event_name, score, is_active}` | 更新事件类型 |
| 删除类型 | DELETE | `/types/{type_id}` | - | 删除事件类型 |

#### 7.1.3 操作日志查询API

**文件**：`models/datas_api/moral/admin.py`（新增路由）

| 任务 | 方法 | 端点 | 参数 | 说明 |
|------|------|------|------|------|
| 查询日志 | GET | `/logs` | `operator, operation, table_name, start_date, end_date, page` | 分页查询操作日志 |

**响应格式**：
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "log_id": 1,
        "operator": "张三",
        "operator_role": "xuefa",
        "operation": "INSERT",
        "table_name": "student_daily_record",
        "record_id": 123,
        "old_data": null,
        "new_data": {"event_name": "拾金不昧"},
        "created_at": "2026-03-29 10:00:00"
      }
    ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

#### 7.1.4 系统配置API

**文件**：`models/datas_api/moral/admin.py`（新增路由）

| 任务 | 方法 | 端点 | 说明 |
|------|------|------|------|
| 获取配置 | GET | `/config` | 获取系统配置项 |
| 更新配置 | PUT | `/config` | 更新系统配置项 |

**配置项**：
```json
{
  "evaluation_base_score": 100,
  "evaluation_weights": {
    "daily": 0.3,
    "school_event": 0.3,
    "task": 0.2,
    "punishment": -0.2
  },
  "birthday_reminder_days": 7,
  "semester_start_month": 9
}
```

---

### 7.2 前端页面补充计划

#### 7.2.1 页面结构规划

```
frontend/src/views/moral/
├── config/
│   ├── Index.vue           # 配置入口页面（Tab导航）
│   ├── GradeManage.vue     # 级号管理
│   ├── ClassManage.vue     # 班级管理
│   ├── StudentManage.vue   # 学生管理
│   ├── SemesterManage.vue  # 学年学期管理
│   └── EventTypeManage.vue # 事件类型配置
```

#### 7.2.2 各页面功能设计

##### GradeManage.vue - 级号管理
| 功能 | 说明 |
|------|------|
| 列表展示 | 级号名称、入学年份、班级数、学生数 |
| 新增级号 | 级号名称、入学年份 |
| 删除级号 | 二次确认，检查关联数据 |
| 查看详情 | 查看该级号下所有班级 |

##### ClassManage.vue - 班级管理
| 功能 | 说明 |
|------|------|
| 筛选条件 | 按级号筛选 |
| 列表展示 | 班级代码、名称、班主任、学生数 |
| 新增班级 | 级号、班号、班主任信息 |
| 编辑班级 | 修改班主任、微信群等 |
| 查看学生 | 跳转到学生列表 |

##### StudentManage.vue - 学生管理
| 功能 | 说明 |
|------|------|
| 筛选条件 | 按级号/班级/状态筛选 |
| 列表展示 | 学号、姓名、班级、出生日期、状态 |
| 新增学生 | 学号、姓名、班级、出生日期 |
| 状态变更 | 在校/休学/转出/毕业 |
| 导入学生 | Excel批量导入 |
| 导出学生 | 导出Excel |

##### SemesterManage.vue - 学年学期管理
| 功能 | 说明 |
|------|------|
| 学年列表 | 学年名称、开始/结束日期、是否当前 |
| 学期列表 | 学期名称、所属学年、是否当前 |
| 新增学年 | 学年名称、日期范围 |
| 新增学期 | 学期名称、所属学年、日期范围 |
| 设为当前 | 设置当前学期 |

##### EventTypeManage.vue - 事件类型配置
| 功能 | 说明 |
|------|------|
| Tab切换 | 日常事件类型 / 校级事件类型 |
| 列表展示 | 事件名称、类型、分值、状态 |
| 新增类型 | 名称、类型（积极/消极）、分值 |
| 编辑类型 | 修改名称、分值 |
| 启用/禁用 | 切换类型状态 |

---

### 7.3 路由配置补充

**文件**：`frontend/src/router/index.js`

```javascript
// 新增路由
{
  path: '/moral/config',
  name: 'MoralConfig',
  component: () => import('../views/moral/config/Index.vue'),
  meta: { requiresAuth: true, title: '系统配置' },
  children: [
    { path: 'grades', name: 'GradeManage', component: GradeManage },
    { path: 'classes', name: 'ClassManage', component: ClassManage },
    { path: 'students', name: 'StudentManage', component: StudentManage },
    { path: 'semesters', name: 'SemesterManage', component: SemesterManage },
    { path: 'event-types', name: 'EventTypeManage', component: EventTypeManage },
  ]
}
```

---

### 7.4 前端API模块补充

**文件**：`frontend/src/api/modules/moral.js`

```javascript
// 事件类型管理
export function createDailyEventType(data) {
  return request.post('/moral/daily-records/types', data)
}
export function updateDailyEventType(typeId, data) {
  return request.put(`/moral/daily-records/types/${typeId}`, data)
}
export function deleteDailyEventType(typeId) {
  return request.delete(`/moral/daily-records/types/${typeId}`)
}

// 校级事件类型管理
export function createSchoolEventType(data) {
  return request.post('/moral/school-records/types', data)
}
export function updateSchoolEventType(typeId, data) {
  return request.put(`/moral/school-records/types/${typeId}`, data)
}
export function deleteSchoolEventType(typeId) {
  return request.delete(`/moral/school-records/types/${typeId}`)
}

// 操作日志
export function getOperationLogs(params) {
  return request.get('/moral/admin/logs', { params })
}

// 系统配置
export function getSystemConfig() {
  return request.get('/moral/admin/config')
}
export function updateSystemConfig(data) {
  return request.put('/moral/admin/config', data)
}
```

---

### 7.5 导航菜单更新

**文件**：`frontend/src/App.vue`

```html
<!-- 德育评价菜单更新 -->
<el-sub-menu v-if="isLoggedIn" index="moral">
  <template #title>德育评价</template>
  <el-menu-item index="/moral/daily-record">日常表现</el-menu-item>
  <el-menu-item index="/moral/school-event">校级事件</el-menu-item>
  <el-menu-item index="/moral/task">德育任务</el-menu-item>
  <el-menu-item index="/moral/punishment">处分管理</el-menu-item>
  <el-menu-item index="/moral/evaluation">评价查询</el-menu-item>
  <el-menu-item index="/moral/profile">学生画像</el-menu-item>
  <el-menu-item index="/moral/birthday">生日提醒</el-menu-item>
  <!-- 新增：系统配置（仅管理员/xuefa可见） -->
  <el-menu-item v-if="isAdmin || isXuefa" index="/moral/config">系统配置</el-menu-item>
</el-sub-menu>
```

---

### 7.6 实施进度表

| 阶段 | 任务 | 优先级 | 预计工时 | 依赖 |
|------|------|--------|----------|------|
| **后端** | | | | |
| 1.1 | 日常事件类型管理API | 高 | 2h | - |
| 1.2 | 校级事件类型管理API | 高 | 2h | - |
| 1.3 | 操作日志查询API | 中 | 2h | - |
| 1.4 | 系统配置API | 中 | 2h | - |
| **前端** | | | | |
| 2.1 | EventTypeManage.vue | 高 | 3h | 1.1, 1.2 |
| 2.2 | GradeManage.vue | 高 | 2h | - |
| 2.3 | ClassManage.vue | 高 | 2h | 2.2 |
| 2.4 | StudentManage.vue | 高 | 3h | 2.3 |
| 2.5 | SemesterManage.vue | 中 | 2h | - |
| 2.6 | Index.vue（配置入口） | 中 | 1h | 2.1-2.5 |
| **集成** | | | | |
| 3.1 | 路由配置 | 中 | 0.5h | 2.6 |
| 3.2 | API模块更新 | 中 | 0.5h | 1.1-1.4 |
| 3.3 | 导航菜单更新 | 中 | 0.5h | 3.1 |
| 3.4 | 测试验证 | 高 | 2h | 3.1-3.3 |
| **总计** | | | **22h** | |

---

### 7.7 验收标准

| 功能 | 验收标准 |
|------|----------|
| 事件类型管理 | 可增删改查日常/校级事件类型 |
| 级号管理 | 可创建、删除级号，显示班级/学生统计 |
| 班级管理 | 可增删改班级，关联班主任信息 |
| 学生管理 | 可增删改学生，支持状态变更 |
| 学期管理 | 可创建学年学期，设置当前学期 |
| 操作日志 | 可按条件查询操作日志 |
| 系统配置 | 可查看和修改系统参数 |

---

## 九、系统访问信息

### 7.1 开发环境
- **前端**：https://localhost:3333/
- **后端**：http://localhost:14600/
- **API文档**：http://localhost:14600/docs

### 7.2 测试账号
| 用户名 | 密码 | 角色 |
|--------|------|------|
| 陈明 | 888888 | teacher/xuefa |
| 李伟刚 | zX9cV7bN | admin |

---

## 十、更新日志

### v3.0.0 (2026-03-29)
- 新增德育评价系统完整功能
- 新增10个后端API模块，41个API端点
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