# 全系统数据驾驶舱实现方案

## 目标

为当前班级数据展示系统建设一组可落地的数据驾驶舱，覆盖班级、课表、教务、监考、德育、教师、文件、系统运维等核心功能，让不同角色能在登录后快速看到“当前状态、风险预警、待办事项、趋势变化和可追溯明细”。

本方案仅用于分析和设计，暂不直接实现代码。

## 当前系统功能范围

根据现有路由、后端 API 与文档，系统主要包含以下功能域：

| 功能域 | 代表页面/模块 | 主要数据 |
|------|---------------|----------|
| 班级管理 | 班级作业、班级信息、班级学生、公告、延时申请、请假记录 | 班级、学生、作业、公告、请假/延时 |
| 课表管理 | 课程表、实时课程、总课表、更新课表 | 课程、教师、班级、时间段 |
| 教师工作 | 发布作业、发布公告、文件上传、我的文件 | 教师发布内容、文件 |
| 教务管理 | 文件管理、已查阅文件、更新课表、监考安排 | 文件流转、课表更新、监考项目 |
| 监考安排 | 考试项目、监考安排、导入导出、通知日志 | 考试项目、考场、教师、通知 |
| 德育评价 | 日常表现、校级事件、德育任务、处分、评价查询、集体事件、点滴记录 | 德育分、事件、任务、处分、画像 |
| 德育配置 | 级号、班级、学生、学期、事件类型、累进规则、API 权限、操作日志 | 基础数据、配置、日志 |
| 系统管理 | 会员、权限、任务、系统监控、教师管理 | 用户、权限、任务、服务状态 |
| 趣味互动 | 随机点名、大声 PK | 活动记录、参与情况 |

## 建设原则

1. **按角色授权展示**：驾驶舱里的数据权限必须与现有 API 权限、角色权限一致，不能因为统计聚合绕过数据权限。
2. **先总览后钻取**：首页展示关键指标和异常，点击后进入对应业务页面或明细弹窗。
3. **以业务闭环为中心**：不仅显示数量，还要显示待处理、异常、趋势、完成率。
4. **保留原业务页面**：驾驶舱不替代现有功能页，只做汇总、预警和入口。
5. **SQLite 优先**：当前系统数据库仍使用 SQLite，统计接口应避免复杂长事务和高频全表扫描。
6. **分阶段落地**：先做能复用现有表的统计，再做趋势、快照、缓存和更复杂的分析。

## 2026-05-07 角色价值重规划

本次重规划把驾驶舱定位为“真实工作态势屏 + 可行动工作台”，而不是普通统计报表。每个驾驶舱必须回答三个问题：

1. **现在发生了什么**：用实时或近实时数据展示当前状态。
2. **哪里需要处理**：用预警、待办、异常名单指出工作重点。
3. **下一步怎么做**：每个指标都能跳转到现有业务页面或明细接口。

### 当前已存在的 Dashboard API

| API | 当前用途 | 适用角色 | 说明 |
|-----|----------|----------|------|
| `GET /api/dashboard/overview` | 当前用户可见总览 | 登录用户 | 返回角色可见模块、全局卡片、预警 |
| `GET /api/dashboard/moral/summary` | 德育驾驶舱 | `admin/jiaowu/xuefa/cleader` | 已按角色裁剪全校或本班范围 |
| `GET /api/dashboard/teaching/summary` | 教务驾驶舱 | `admin/jiaowu` | 已含课表、教师课时、班级规模、文件上传统计 |
| `GET /api/dashboard/class/summary` | 班级驾驶舱 | `admin/jiaowu/xuefa/cleader` | 已含班级学生、德育、作业公告、请假数量、生日 |
| `GET /api/dashboard/teacher/workbench` | 教师工作台 | `teacher/cleader/admin` | 已含今日课程、发布、德育参与、监考任务 |
| `GET /api/dashboard/invigilation/summary` | 监考驾驶舱 | `admin/jiaowu` | 已含项目、安排、通知、负载、冲突 |
| `GET /api/dashboard/system/summary` | 系统驾驶舱 | `admin` | 已含数据库、任务、权限、运行状态 |

### 可复用业务 API 和数据源

| 业务域 | 可复用接口/API | 数据源 | 驾驶舱价值 |
|--------|----------------|--------|------------|
| 文件上传 | `GET /api/filegather/admin/statistics`、`GET /api/filegather/admin/files`、`GET /api/filegather/admin/done-files` | `filegather.db.files` | 教务掌握待处理文件、完成率、教师上传排行、逾期文件 |
| 请假名单 | `GET /api/leave-records/`、`POST /api/leave-records/{record_id}/consume` | `inout.db.inout` + `Lesson().get_cache_data("students")` | 班主任/学发看到当前请假学生名单、未销假、请假类型和时长；不进入教务驾驶舱 |
| 延时申请 | `GET /api/delay_infos/{classCode}`、`POST /api/insert_delay/` | `inout.db.inout` | 班主任掌握当天延时学生，避免漏管 |
| 德育表现 | `GET /api/dashboard/moral/summary` 及德育评价接口 | `moral.db` | 学发/班主任定位低分学生、消极事件、班级差异 |
| 班级学生 | `GET /api/dashboard/class/summary`、`GET /api/moral/admin/students` | `moral.db.student/class` + lesson cache | 班主任掌握班级人数、生日、信息缺失、风险学生 |
| 课表课时 | `GET /api/dashboard/teaching/summary` | `lesson.yaml` 指向的课表文件和缓存 | 教务了解课表覆盖、当前课节、教师课时负载 |
| 监考安排 | `GET /api/dashboard/invigilation/summary` | `invigilation.db` | 教务看到未安排、冲突、通知失败、教师负载 |
| 教师工作 | `GET /api/dashboard/teacher/workbench` | 课表、作业公告、德育记录、监考库 | 教师明确今日课程、待办、自己贡献和风险提醒 |

### 数据价值分层

| 层级 | 展示内容 | 对工作的价值 |
|------|----------|--------------|
| 态势层 | 核心指标卡、完成率、当前课节、班级请假、低分人数 | 让角色快速知道“现在是否正常” |
| 预警层 | 低分学生、班级未销假、文件逾期、监考冲突、通知失败 | 让角色知道“今天必须处理什么” |
| 趋势层 | 德育趋势、文件流转趋势、课时负载、请假变化 | 让角色看到工作走势和管理压力 |
| 明细层 | 学生名单、文件列表、低分排行、待处理任务 | 让角色能直接行动和追踪 |
| 启示层 | 高风险班级、反复请假学生、文件处理瓶颈、教师负载不均 | 帮助后续调整班级管理、教务安排和学生关怀 |

### 教务驾驶舱重规划

教务驾驶舱不应只展示课表和文件数量，而要成为“教学运行调度屏”。

| 模块 | 真实数据 | API/数据源 | 展示形态 | 行动价值 |
|------|----------|------------|----------|----------|
| 教学运行态势 | 班级数、在校学生数、教师账号数、当前课节、正在上课班级 | `/api/dashboard/teaching/summary`、课表缓存、`moral.db` | 发光指标卡 + 当前课节横幅 | 判断当前教学运行是否正常 |
| 课时负载 | 区间课时、教师课时排行、覆盖日期、源课表文件 | `/api/dashboard/teaching/summary` | 横向排行条 + 课表覆盖提示 | 发现教师负载不均和课表统计缺口 |
| 文件上传流转 | 本月文件、待处理文件、已完成文件、完成率、上传教师 TopN、最近待处理文件 | `filegather.db.files`、`/api/filegather/admin/*` | 霓虹环图 + 待处理列表 | 教务及时处理打印/资料文件，避免积压 |
| 班级规模与档案 | 班级人数排行、学生档案缺失项 | `moral.db.class/student` | 柱状图 + 异常列表 | 发现班级容量和基础数据维护问题 |

Batch46 优先落地教务驾驶舱中的“文件上传深度指标 + 课表/教学运行态势”。文件上传已有基础统计，需要进一步补齐完成率、最近待处理、逾期未处理。请假学生相关数据不进入教务驾驶舱，应在班级驾驶舱和德育驾驶舱中展示。

### 德育驾驶舱重规划

德育驾驶舱面向学发、班主任和管理者，核心不是“分数好看”，而是发现学生成长风险。

| 模块 | 真实数据 | API/数据源 | 展示形态 | 行动价值 |
|------|----------|------------|----------|----------|
| 德育态势 | 可见学生数、平均分、低分人数、日常记录数 | `/api/dashboard/moral/summary`、`moral.db` | 仪表盘 + 核心卡 | 判断德育总体健康度 |
| 风险学生 | 低分学生、严重低分、近期消极事件频繁学生 | `moral_evaluation`、`student_daily_record` | 风险名单 + 标签 | 学发和班主任优先谈话、跟进 |
| 请假与出勤风险 | 当前未销假学生、近期反复请假学生、按班级请假分布 | `inout.db.inout` + students cache | 请假名单 + 班级分布图 | 学发识别学生流动和班级管理风险 |
| 班级对比 | 班级平均分、低分率、扣分次数、任务完成率 | `moral.db` | 排行条 + 热力图 | 找出需要支持的班级 |
| 事件结构 | 正向/负向事件占比、事件 TopN、近 14/30 天趋势 | `student_daily_record`、事件类型表 | 折线图 + 玫瑰图 | 识别管理问题是纪律、学习态度还是生活习惯 |
| 学生画像 | 画像覆盖率、过期画像、风险标签分布 | profile 相关表 | 标签云 + 覆盖率 | 让德育工作从记录走向诊断 |

### 班级驾驶舱重规划

班级驾驶舱面向班主任，必须把“今天要管谁、为什么管、怎么跟进”放在首屏。

| 模块 | 真实数据 | API/数据源 | 展示形态 | 行动价值 |
|------|----------|------------|----------|----------|
| 班级状态 | 班级人数、男女比例、平均德育分、低分人数 | `/api/dashboard/class/summary` | 班级态势卡 + 环图 | 快速掌握班级基本盘 |
| 当前请假名单 | 当前未销假学生、请假类型、天数、备注、记录人 | `inout.db.inout` + students cache | 首屏名单表 | 班主任知道谁不在、何时跟进销假 |
| 风险学生 | 低分、频繁扣分、未生成画像、近期异常学生 | `moral.db` | 风险卡片列表 | 优先安排谈话、家校沟通 |
| 关怀事项 | 本周/本月生日、近期请假较多学生 | `student.birthday`、`inout.db` | 时间轴 | 形成正向关怀和班级温度 |
| 学习活动 | 作业数、公告数、当前课程 | `homework.db`、课表缓存 | 小趋势 + 快捷入口 | 检查班级学习活动节奏 |

### 教师工作驾驶舱重规划

教师工作台不是管理驾驶舱，而是个人行动清单。

| 模块 | 真实数据 | API/数据源 | 展示形态 | 行动价值 |
|------|----------|------------|----------|----------|
| 今日课程 | 今天课程、班级、节次、时间 | `/api/dashboard/teacher/workbench` | 时间轴 | 提醒当天教学安排 |
| 我的发布 | 本周作业、公告、上传文件、待处理文件 | `homework.db`、`filegather.db` | 工作量卡片 | 回顾自己发布和资料流转 |
| 我的德育参与 | 自己创建的日常记录、点滴记录、涉及学生 | `moral.db` | 贡献卡 + 学生列表 | 让任课教师看到育人参与 |
| 我的监考 | 近期监考安排、变更通知 | `invigilation.db` | 任务列表 | 减少漏看监考安排 |

### 总览驾驶舱重规划

总览页应根据角色裁剪，不同角色看到不同“默认入口”：

| 角色 | 首屏重点 | 默认推荐入口 |
|------|----------|--------------|
| `admin` | 全校运行、系统健康、权限风险、业务预警 | 系统、德育、教务、监考 |
| `jiaowu` | 教学运行、文件流转、课表覆盖、监考安排 | 教务、监考、班级 |
| `xuefa` | 德育风险、请假未销假、低分学生、处分画像 | 德育、班级 |
| `cleader` | 本班请假名单、低分学生、生日关怀、作业公告 | 班级、教师工作台 |
| `teacher` | 今日课程、我的上传、我的记录、监考任务 | 教师工作台 |

### 炫酷但真实的视觉方向

驾驶舱视觉要有“大屏感”，但不能牺牲可读性。

1. **整体风格**：深色科技背景 + 半透明玻璃面板 + 微弱发光边框 + 清晰状态色。
2. **首屏结构**：顶部角色标题和时间范围，中部 4-8 个核心指标卡，底部两列图表和待办名单。
3. **数据强调**：风险数字用红/橙，完成率用绿/青，趋势用蓝/紫，但避免全页面单一紫蓝。
4. **动效克制**：卡片 hover、数字轻微滚动、图表渐入即可，不做影响阅读的动画。
5. **名单必须真实可用**：请假学生、低分学生、待处理文件都要显示姓名/班级/状态/时间/处理入口。
6. **空状态要专业**：无数据时显示“当前无待处理文件/当前无请假学生”，而不是空白或假数据。

### 新增数据结构建议

在保持现有 `cards/charts/tables` 结构的基础上，建议 dashboard API 增加约定字段：

```json
{
  "data": {
    "cards": [],
    "charts": {},
    "tables": {
      "leave_students": [],
      "pending_files": [],
      "risk_students": []
    },
    "alerts": [],
    "insights": [],
    "updated_at": "2026-05-07 10:00:00"
  }
}
```

| 字段 | 用途 | 示例 |
|------|------|------|
| `tables.leave_students` | 班级/德育驾驶舱中的当前可见请假/未销假学生名单，教务驾驶舱不返回该字段 | `{name, class_name, style, days, status, recorder, create_at}` |
| `tables.pending_files` | 待处理文件明细 | `{id, username, original_name, status, use_date, uploaded_at, overdue_days}` |
| `tables.risk_students` | 低分/频繁异常学生 | `{student_id, name, class_name, reason, score}` |
| `alerts` | 可点击预警 | `{level, title, message, route}` |
| `insights` | 系统给出的工作启示 | `{type, title, message, action_route}` |

## 整体信息架构

建议采用“三层驾驶舱”：

1. **系统总览驾驶舱**：面向 admin/jiaowu/xuefa，展示全校运行态势。
2. **业务专题驾驶舱**：围绕德育、教务、监考、班级、系统运维分别展示。
3. **角色首页驾驶舱**：教师、班主任、教务、学发、管理员登录后看到与自己相关的待办和指标。

建议新增前端路由：

| 路由 | 页面 | 面向角色 |
|------|------|----------|
| `/dashboard` | DashboardOverview.vue | 登录用户，按角色展示 |
| `/dashboard/teaching` | TeachingDashboard.vue | admin/jiaowu |
| `/dashboard/moral` | MoralDashboard.vue | admin/jiaowu/xuefa/cleader |
| `/dashboard/class` | ClassDashboard.vue | cleader/teacher/admin |
| `/dashboard/invigilation` | InvigilationDashboard.vue | admin/jiaowu |
| `/dashboard/system` | SystemDashboard.vue | admin |

顶部导航建议新增一级菜单“驾驶舱”，或在首页 `/` 默认跳转到 `/dashboard`。

## 角色视图设计

### admin 管理员

重点关注：

- 系统总量：学生、班级、教师、活跃用户、文件、德育记录。
- 系统健康：服务状态、任务运行、数据库状态、异常日志。
- 权限风险：API 权限配置、近期 403/异常访问、敏感操作日志。
- 业务风险：低德育分学生、处分未撤销、通知失败、文件未处理。

### jiaowu 教务

重点关注：

- 班级/学生基础数据完整度。
- 课表更新状态、文件流转状态。
- 监考项目状态、未安排监考、通知失败。

### xuefa 学发

重点关注：

- 德育分布、扣分趋势、处分、预警。
- 日常表现、校级事件、集体事件、任务完成率。
- 学生画像生成覆盖率、AI 诊疗待处理。
- 班级/年级横向对比。
- 德育评价中与班级/年级管理相关的趋势。

### cleader 班主任

重点关注：

- 本班学生德育分分布。
- 本班低分/高风险学生。
- 本班请假、生日、任务完成、日常表现。
- 自己创建或待处理的记录。

### teacher 教师

重点关注：

- 今日课程/近期课表。
- 自己发布的作业、公告、文件。
- 自己创建的日常表现、点滴记录。
- 与自己相关的监考通知和任务提醒。

### student/parent

若后续开放，可展示：

- 个人德育分趋势。
- 作业、公告、课表。
- 个人画像摘要、生日祝福、请假记录。

## 总览驾驶舱指标

### 1. 核心指标卡

| 指标 | 说明 | 数据来源 |
|------|------|----------|
| 在校学生数 | 当前在校学生总数 | `moral.student` |
| 班级数 | 当前启用班级数 | `moral.class` |
| 教师数 | 当前启用教师数 | `auth.teacher` 或 `moral.teacher` |
| 今日课程数 | 当天排课数量 | 课表数据源 |
| 本周作业数 | 本周发布作业数量 | `homework.db` |
| 本月文件上传数 | 文件上传数量 | `filegather.db` |
| 德育记录数 | 本学期日常/校级/集体/处分记录 | `moral.*record` |
| 待处理预警数 | 未处理 warning | `moral.warning_log` |
| 监考项目数 | 近期考试项目 | `invigilation.exam_project` |
| 通知失败数 | 监考/生日/文件等通知失败 | 通知日志表 |

### 2. 趋势图

| 图表 | 维度 | 说明 |
|------|------|------|
| 德育记录趋势 | 日/周/月 | 展示积极、消极、处分、任务完成变化 |
| 作业发布趋势 | 日期、教师、班级 | 观察教学活动频率 |
| 文件流转趋势 | 上传、已阅、未阅 | 教务文件处理效率 |
| 监考通知趋势 | 成功、失败、跳过 | 发现通知链路问题 |
| 学生人数变化 | 年级、班级、状态 | 观察学籍变化 |

### 3. 风险列表

| 风险 | 规则 |
|------|------|
| 德育低分学生 | 当前学期总分低于阈值 |
| 扣分频繁学生 | 最近 30 天消极事件次数超过阈值 |
| 处分未撤销 | `punishment_record.status` 未撤销 |
| 任务完成率低班级 | 任务完成率低于阈值 |
| 文件未处理 | 教务文件超过 N 天未标记已阅 |
| 监考未安排 | 考试项目存在空教师或冲突 |
| 监考通知失败 | `sent_status=failed/skipped` |
| API 权限异常 | 敏感 API 允许角色过宽或近期频繁 403 |

## 业务专题驾驶舱

## 一、德育驾驶舱

### 指标模块

| 模块 | 指标 |
|------|------|
| 德育总览 | 学生平均分、最高分、最低分、低分人数、优秀人数 |
| 分数结构 | 日常表现分、校级事件分、集体事件分、任务分、处分扣分 |
| 事件分析 | 积极事件 Top10、消极事件 Top10、事件趋势 |
| 班级对比 | 班级平均分、低分率、扣分次数、任务完成率 |
| 年级对比 | 年级平均分、处分数、预警数 |
| 处分预警 | 未撤销处分、累进处罚触发、待复核处分 |
| 学生画像 | 已生成画像数、覆盖率、最近生成时间、标签分布 |
| AI 诊疗 | 会话数、未关闭会话、问题类型分布 |
| 生日提醒 | 今日生日、近期生日、提醒发送状态 |

### 推荐图表

- 年级/班级平均分柱状图。
- 德育总分分布直方图。
- 积极/消极事件趋势折线图。
- 低分学生列表。
- 处分状态漏斗。
- 学生画像标签词云或标签排行。

### 重点钻取

- 点击班级进入 `/moral/evaluation?class_id=...`。
- 点击学生进入 `/moral/profile?student_id=...`。
- 点击事件进入日常表现/校级事件明细。
- 点击处分进入处分管理。

### 权限边界

- `admin/jiaowu/xuefa` 可看全校。
- `cleader` 只能看自己班级。
- `teacher` 默认不展示全校德育驾驶舱，只展示自己创建的日常/点滴记录统计。

## 二、教务驾驶舱

### 指标模块

| 模块 | 指标 |
|------|------|
| 基础数据 | 年级数、班级数、学生数、教师数、异常学生档案 |
| 课表状态 | 当前课表版本、最近更新时间、今日课程数、空课/冲突数 |
| 文件流转 | 上传文件数、待查阅文件数、已阅率、逾期未阅 |
| 作业公告 | 本周作业数、公告数、发布教师排行 |
| 教学运行 | 班级/学生基础规模、课表状态、作业公告与文件流转状态 |

### 推荐图表

- 班级人数柱状图。
- 文件已阅率环图。
- 本周作业/公告趋势。
- 今日课程热力表。

### 重点钻取

- 文件指标跳转 `/admin-files` 或 `/admin-files-done`。
- 课表指标跳转 `/schedules`、`/upload-schedule`。
- 班级指标跳转 `/class-students` 或德育学生管理。

## 三、监考驾驶舱

当前项目已经存在 `lesson/models/datas_api/invigilation.py`、`frontend/src/views/InvigilationArrange.vue`、`invigilation.db`，驾驶舱应复用其数据。

### 指标模块

| 模块 | 指标 |
|------|------|
| 考试项目 | 项目总数、草稿数、已通知数、近期考试数 |
| 安排完整度 | 总场次、已安排场次、未安排教师场次、冲突场次 |
| 教师负载 | 教师监考次数排行、平均监考次数、最大/最小负载 |
| 年级分布 | 各年级考试场次、考场数、学科数 |
| 通知状态 | 成功、失败、跳过、最近通知时间 |
| 变更追踪 | 最近变更项目、变更老师、变更次数 |

### 推荐图表

- 考试项目状态卡片。
- 教师监考负载柱状图。
- 按日期/时间的监考场次热力表。
- 通知结果堆叠条形图。
- 未安排/冲突场次列表。

### 重点钻取

- 点击考试项目进入 `/invigilation?project_id=...`。
- 点击通知失败进入通知日志。
- 点击教师进入该教师监考明细。

## 四、班级驾驶舱

### 指标模块

| 模块 | 指标 |
|------|------|
| 班级基础 | 班级人数、男女比例、住宿/床位信息完整度 |
| 学习活动 | 作业数、公告数、课程数 |
| 德育表现 | 班级平均分、低分学生、近期扣分/加分 |
| 出勤事务 | 请假人数、未销假、延时申请 |
| 生日关怀 | 本月生日、本周生日 |

### 角色化展示

- 班主任默认进入自己班级驾驶舱。
- 教务/管理员可切换年级和班级。
- 普通教师只展示与自己教学或创建记录相关的部分。

## 五、教师工作驾驶舱

### 指标模块

| 模块 | 指标 |
|------|------|
| 今日事项 | 今日课程、今日监考、待处理文件、生日提醒 |
| 发布内容 | 本周作业数、公告数、文件数 |
| 德育参与 | 自己创建的日常表现、点滴记录、涉及学生 |
| 监考任务 | 近期监考安排、变更通知 |
| 系统消息 | 任务提醒、通知失败提示 |

## 六、系统运维驾驶舱

### 指标模块

| 模块 | 指标 |
|------|------|
| 服务状态 | API 存活、响应时间、错误数 |
| 数据库状态 | 各 SQLite 文件大小、表记录数、最近更新时间 |
| 后台任务 | 任务数量、运行中、失败、最近执行 |
| 权限安全 | 用户数、角色分布、API 权限配置风险 |
| 操作审计 | 最近敏感操作、删除/更新操作排行 |

### 重点接入

- 复用现有 `/system-monitor` 页面数据。
- 复用 `moral_operation_log` 和系统任务表。
- 后续可增加 `dashboard_metric_snapshot` 做每日快照。

## 数据来源设计

### 现有 SQLite 数据库

| 数据库 | 主要用途 | 驾驶舱用途 |
|------|----------|------------|
| `moral.db` | 德育、学生、班级、学期、教师快照 | 德育、班级、基础数据 |
| `auth.db` | 用户/教师登录信息 | 用户、教师、角色 |
| `homework.db` | 作业、公告 | 教学活动 |
| `filegather.db` | 文件上传与查阅 | 文件流转 |
| `inout.db` | 请假/出入校 | 出勤事务 |
| `task.db` | 定时任务/提醒 | 运维和待办 |
| `invigilation.db` | 监考项目与通知 | 监考驾驶舱 |

### 建议新增汇总表

为减少页面打开时多库扫描，建议新增一个轻量汇总库：`lesson/databases/dashboard.db`。

#### `dashboard_metric_snapshot`

每日或每小时保存核心指标快照。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | ID |
| metric_key | TEXT | 指标键 |
| metric_name | TEXT | 指标名 |
| metric_value | REAL | 数值 |
| dimension_json | TEXT | 维度，如年级/班级/角色 |
| snapshot_date | TEXT | 快照日期 |
| created_at | TEXT | 创建时间 |

#### `dashboard_alert`

统一保存驾驶舱风险提示。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | ID |
| alert_type | TEXT | 风险类型 |
| severity | TEXT | `info/warning/danger` |
| title | TEXT | 标题 |
| content | TEXT | 内容 |
| source_module | TEXT | 来源模块 |
| target_path | TEXT | 点击跳转路径 |
| status | TEXT | `open/resolved/ignored` |
| owner_role | TEXT | 负责角色 |
| created_at | TEXT | 创建时间 |
| resolved_at | TEXT | 解决时间 |

## 后端 API 方案

建议新增模块：`lesson/models/datas_api/dashboard.py`，在 `lesson/models/datas_api/__init__.py` 注册。

统一前缀：`/api/dashboard`

### API 清单

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/overview` | 当前用户可见的总览指标 |
| GET | `/alerts` | 当前用户可见预警列表 |
| GET | `/moral/summary` | 德育总览 |
| GET | `/moral/trends` | 德育趋势 |
| GET | `/moral/rankings` | 德育排行/低分列表 |
| GET | `/teaching/summary` | 教务/教学总览 |
| GET | `/class/summary` | 班级总览 |
| GET | `/teacher/workbench` | 教师个人工作台 |
| GET | `/invigilation/summary` | 监考总览 |
| GET | `/system/summary` | 系统运维总览 |
| GET | `/meta/filters` | 年级、班级、学期、日期范围等筛选项 |

### 通用查询参数

| 参数 | 说明 |
|------|------|
| `semester_id` | 学期 |
| `grade_id` | 年级 |
| `class_id` | 班级 |
| `start_date` | 开始日期 |
| `end_date` | 结束日期 |
| `scope` | `school/grade/class/self` |

### 响应结构建议

```json
{
  "success": true,
  "data": {
    "cards": [],
    "charts": {},
    "tables": {},
    "alerts": [],
    "updated_at": "2026-04-28 10:00:00"
  }
}
```

## 权限方案

### 数据权限规则

| 角色 | 数据范围 |
|------|----------|
| admin | 全校、全部模块 |
| jiaowu | 教务、课表、基础数据、监考、全校汇总 |
| xuefa | 德育全校汇总、学生风险、处分、画像 |
| cleader | 自己班级汇总、自己可处理事项 |
| teacher | 自己创建/负责/相关的数据 |
| student | 自己数据 |
| parent | 子女数据 |

### 技术要求

1. 所有 dashboard API 都必须通过 `get_current_user`。
2. 后端根据用户角色裁剪查询条件，前端不承担数据权限。
3. 不允许返回用户无权查看的学生明细；汇总数据也要注意班级范围。
4. 对普通教师，德育相关只展示自己创建的日常表现、点滴记录，不展示全量学生。
5. 对班主任，默认限制到自己班级；如某业务已明确放开录入范围，驾驶舱仍应按查看权限而非录入权限展示。

## 前端页面方案

### 组件拆分

建议新增：

- `frontend/src/views/dashboard/Overview.vue`
- `frontend/src/views/dashboard/MoralDashboard.vue`
- `frontend/src/views/dashboard/TeachingDashboard.vue`
- `frontend/src/views/dashboard/ClassDashboard.vue`
- `frontend/src/views/dashboard/TeacherWorkbench.vue`
- `frontend/src/views/dashboard/InvigilationDashboard.vue`
- `frontend/src/views/dashboard/SystemDashboard.vue`
- `frontend/src/api/modules/dashboard.js`

通用组件：

- `MetricCard.vue`
- `TrendChart.vue`
- `RankTable.vue`
- `AlertList.vue`
- `DashboardFilterBar.vue`
- `ModuleShortcutGrid.vue`

### UI 结构

顶部：

- 时间范围
- 学期
- 年级/班级
- 刷新按钮
- 数据更新时间

主体：

- 第一行：核心指标卡。
- 第二行：趋势图和分布图。
- 第三行：预警列表、待办列表、排行榜。
- 底部：业务快捷入口。

### 视觉化驾驶舱修正方案

驾驶舱不是普通管理页的表格搬运，应按“大屏态势 + 可钻取工作台”来实现。第一屏必须同时回答：系统现在怎么样、哪里异常、谁需要关注、下一步去哪里处理。

#### 视觉原则

1. **首屏态势化**：使用深色渐变背景、发光指标卡、趋势图、环形图、排行条形图，形成“驾驶舱”而不是“列表页”。
2. **信息密度可控**：核心指标 3-6 个，图表 2-4 个，表格只保留 TopN 和异常清单。
3. **真实数据驱动**：所有图表均从后端统计接口返回，不在前端编造演示数据。
4. **可钻取**：指标卡、预警、排行项保留跳转入口，回到现有业务页面处理。
5. **权限一致**：视觉化不改变数据边界，图表统计范围必须复用后端 API 权限与数据范围。
6. **移动端降级**：桌面使用双列/三列图表，移动端变为单列卡片，不出现横向挤压。

#### 第一阶段视觉交付

本阶段先把已上线的三个页面重构为可视化驾驶舱：

- `/dashboard`：系统总览，展示角色可见模块、全局指标、预警雷达、模块快捷入口。
- `/dashboard/moral`：德育驾驶舱，展示德育均分仪表、分数段分布、正负事件占比、近 14 天记录趋势、低分学生 Top5。
- `/dashboard/teaching`：教务驾驶舱，展示指定时间段课时统计、教师课时 Top5 柱状图、班级规模 Top5、统计覆盖日期说明。

#### 前端组件补充

在原有组件规划基础上，优先新增：

- `DashboardChart.vue`：统一封装 ECharts 初始化、resize、空状态。
- 视觉化指标卡样式：发光边框、状态色、渐变背景、单位弱化。
- 排行条样式：用于 Top5，不再只依赖表格展示。

#### 后端图表数据补充

`/api/dashboard/moral/summary` 增加：

- `charts.score_distribution`：德育分数段分布。
- `charts.daily_event_mix`：日常表现正向/负向记录占比。
- `charts.daily_record_trend`：近 14 天日常记录趋势。
- `charts.class_score_rank`：班级平均分排行，数量由 `top_n` 控制。

`/api/dashboard/teaching/summary` 增加：

- `charts.teacher_workload_rank`：指定时间段教师课时排行，数量由 `top_n` 控制。
- `charts.class_size_rank`：班级学生人数排行，数量由 `top_n` 控制。
- `charts.resource_mix`：班级、学生、教师资源结构。

验收标准：

- 页面打开后首屏可见至少 2 个图表。
- 无数据时显示空状态，而不是空白区域。
- `npm run build` 通过。
- 已有后端 API 测试不回归。

### 图表库建议

当前项目主要使用 Vue 3 + Element Plus。建议引入：

- `echarts`
- `vue-echarts`

当前 `frontend/package.json` 已包含 `echarts`，第一阶段直接使用 ECharts，不再停留在干巴巴的数据罗列。

## 指标口径设计

### 德育总分

应与当前评价计算逻辑完全一致：

```text
总分 = 基础分 + 日常表现分 + 校级事件分 + 集体事件分 + 任务分 - 处分扣分
```

扣分项必须按扣分处理，不得再次加正数。

### 任务完成率

```text
任务完成率 = 已完成学生任务记录数 / 应完成学生任务记录数
```

需要明确按任务、班级、年级、学期分别计算。

### 文件已阅率

```text
已阅率 = 已标记已阅文件数 / 教务需处理文件总数
```

若文件有多个接收/处理对象，应按处理记录计算，而不是简单按文件数。

### 监考安排完整率

```text
完整率 = 已分配监考老师的场次数 / 总场次数
```

冲突场次不应计入“正常完成”。

### 通知成功率

```text
通知成功率 = success 数 / (success + failed + skipped)
```

`skipped` 表示缺少接收人，也应作为待处理问题展示。

## 预警规则建议

### 德育预警

| 预警 | 默认规则 |
|------|----------|
| 低分学生 | 当前总分 < 60 |
| 严重低分 | 当前总分 < 50 |
| 消极事件频繁 | 30 天内消极事件 >= 5 |
| 处分待处理 | 处分状态未撤销 |
| 画像过期 | 画像更新时间超过 30 天 |

### 教务预警

| 预警 | 默认规则 |
|------|----------|
| 文件逾期未阅 | 上传后超过 3 天未处理 |
| 课表未更新 | 当前周课表缺失或更新时间超过阈值 |
| 学生档案不完整 | 生日、班级、状态等关键字段缺失 |

### 监考预警

| 预警 | 默认规则 |
|------|----------|
| 未安排教师 | `teacher_id` 为空 |
| 教师时间冲突 | 同一教师同一时间多场 |
| 考场冲突 | 同一考场同一时间多场 |
| 通知失败 | `sent_status=failed/skipped` |
| 监考负载过高 | 单个教师监考次数超过平均值 2 倍 |

### 系统预警

| 预警 | 默认规则 |
|------|----------|
| 任务失败 | 定时任务最近执行失败 |
| 数据库过大 | SQLite 文件超过阈值 |
| 高频错误 | 单位时间内 API 错误数超过阈值 |
| 权限配置风险 | 敏感 API 允许 teacher/student/parent |

## 数据刷新策略

### 实时查询

适合：

- 当前用户待办
- 今日课程
- 今日生日
- 监考通知失败
- 系统健康状态

### 定时快照

适合：

- 德育趋势
- 文件流转趋势
- 班级/年级平均分
- 教师工作量排行

建议：

- 每天凌晨生成一次全量快照。
- 工作时间每 1 小时生成关键指标快照。
- 用户手动刷新时可实时重新查询当前页指标。

## 实施阶段

### 第一阶段：总览与德育驾驶舱

目标：

- 新增 `/dashboard`。
- 展示角色化核心指标卡。
- 展示德育总览、低分学生、预警列表。
- 提供跳转到现有业务页面。

交付：

- `dashboard.py`
- `dashboard.js`
- `Overview.vue`
- `MoralDashboard.vue`

验收：

- admin 可看全校。
- xuefa 可看德育全校。
- cleader 只看本班。
- teacher 不出现全校学生明细。

### 第二阶段：教务、班级、教师工作台

目标：

- 增加教务文件、课表、作业公告统计；教务驾驶舱不展示学生请假数据。
- 增加班主任班级驾驶舱，并在班级驾驶舱展示当前请假学生名单。
- 增加德育驾驶舱的请假与出勤风险模块，供学发/班主任识别学生流动风险。
- 增加教师个人工作台。

验收：

- 教务可看文件流转和课表状态。
- 班主任默认进入本班视角。
- 教师只看到自己的发布、记录和监考。

### 第三阶段：监考与通知驾驶舱

目标：

- 增加监考项目状态、安排完整度、通知状态。
- 增加教师监考负载分析。
- 增加冲突和未安排预警。

验收：

- 监考项目可按状态筛选。
- 通知失败可跳转日志。
- 负载过高教师可识别。

### 第四阶段：系统运维与快照

目标：

- 增加 `dashboard.db`。
- 增加指标快照和预警表。
- 增加系统运行态势和权限风险分析。

验收：

- 支持按日期查看历史趋势。
- 支持预警状态处理。
- 系统管理员能看到数据库、任务、权限风险。

## 后端实现注意事项

1. 多 SQLite 数据库查询时，避免一个请求同时持有多个写连接。
2. 统计查询优先只读连接。
3. 对常用字段增加索引，如日期、班级、年级、教师、状态。
4. 查询返回前统一做权限裁剪。
5. 明细列表分页，驾驶舱只返回 TopN。
6. 所有统计口径应写入注释或文档，避免前后端口径不一致。
7. 对无法获取的数据返回空数组和说明，不让驾驶舱整体失败。

## 前端实现注意事项

1. 驾驶舱首页不要做成大段说明文字，应直接呈现数据。
2. 卡片数量控制在 6-10 个，避免信息过载。
3. 所有图表都应提供空状态。
4. 所有预警都应可点击跳转。
5. 移动端采用纵向卡片布局。
6. 图表颜色不要只使用单一色系，风险色应明确。
7. 数据更新时间必须可见。

## 与当前 Review Findings 的关系

用户提供的 review findings 涉及德育核心数据流。驾驶舱依赖这些业务数据，落地前需要确认以下问题已修正并通过验证：

1. 集体事件表结构与接口一致，`class_id` 可正常写入和查询。
2. 普通教师不能读取全量学生和任意学生评价。
3. 德育任务完成接口权限可用。
4. 班主任可正常查看本班评价。
5. 集体事件分数进入德育总分计算。
6. 集体事件页面按钮和权限函数正常。
7. 启动任务不再因为 SQLite 跨线程连接报错。

否则驾驶舱中的德育总分、集体事件、任务完成率、权限可见范围会不准确。

## 测试清单

### 权限测试

- admin 查看全校总览。
- jiaowu 查看教务和全校基础数据。
- xuefa 查看德育全校数据。
- cleader 只能查看自己班级明细。
- teacher 不能通过 dashboard API 获取全校学生明细。

### 数据口径测试

- 德育总分与 `/moral/evaluation` 页面一致。
- 班级人数与学生管理一致。
- 监考完整率与监考安排页面一致。
- 文件已阅率与教务文件页面一致。
- 通知成功率与通知日志一致。

### 前端测试

- `/dashboard` 可按角色显示不同模块。
- 图表空状态正常。
- 时间、年级、班级筛选生效。
- 点击指标能跳转对应页面。
- 移动端无明显溢出。

### 性能测试

- 总览接口在当前数据量下响应小于 1 秒。
- 德育趋势接口响应小于 2 秒。
- 多用户并发访问不锁死 SQLite。
- 快照任务不会影响正常业务写入。

## 建议文件清单

后端：

- `lesson/models/datas_api/dashboard.py`
- `lesson/utils/dashboard_db.py`
- `lesson/scripts/create_dashboard_tables.py`
- `lesson/scripts/generate_dashboard_snapshot.py`
- `lesson/tests/test_dashboard_api.py`

前端：

- `frontend/src/api/modules/dashboard.js`
- `frontend/src/views/dashboard/Overview.vue`
- `frontend/src/views/dashboard/MoralDashboard.vue`
- `frontend/src/views/dashboard/TeachingDashboard.vue`
- `frontend/src/views/dashboard/ClassDashboard.vue`
- `frontend/src/views/dashboard/TeacherWorkbench.vue`
- `frontend/src/views/dashboard/InvigilationDashboard.vue`
- `frontend/src/views/dashboard/SystemDashboard.vue`
- `frontend/src/components/dashboard/MetricCard.vue`
- `frontend/src/components/dashboard/AlertList.vue`
- `frontend/src/components/dashboard/DashboardFilterBar.vue`

文档：

- `docs/data-dashboard-implementation-plan.md`

---

## 数据驾驶舱指标字典（Batch50 固化）

本指标字典定义所有驾驶舱 API 返回字段的标准，确保前后端一致，避免误删或误改。

### 字段命名规范

1. **cards**: 顶层指标卡数组，每个元素包含 `label`、`value`、`unit`、`route`
2. **charts**: 图表数据对象，键名表示图表类型，值为适配前端图表组件的数据格式
3. **tables**: 表格/列表数据对象，键名表示表名，值为数组
4. **insights**: 态势面板，包含风险预警和行动建议
5. **updated_at**: 数据更新时间文本

---

### 总览驾驶舱（Overview）

**API**: `GET /api/dashboard/overview`

**权限**: 登录用户

| 字段路径 | 类型 | 数据来源 | 统计口径 | 权限范围 | 空状态 | 备注 |
|---------|------|---------|---------|---------|--------|------|
| `cards[]` | Array | moral.db + dashboard_overview | 按角色动态生成 | 登录用户 | 空数组 | 每个元素 {label, value, unit, route} |
| `cards[].label` | String | 硬编码 | - | 登录用户 | - | "在校学生"、"德育评价" 等 |
| `cards[].value` | Number | moral.db SQL COUNT | 实时 | 登录用户 | 0 | - |
| `cards[].unit` | String | 硬编码 | - | 登录用户 | - | "人"、"条"、"分" |
| `cards[].route` | String | 硬编码 | - | 登录用户 | - | 跳转路由 |
| `modules[]` | Array | 硬编码 + 角色判断 | 按角色裁剪 visible | 登录用户 | 空数组 | 驾驶舱入口卡片 |
| `modules[].title` | String | 硬编码 | - | 登录用户 | - | "德育驾驶舱"、"教务驾驶舱" |
| `modules[].route` | String | 硬编码 | - | 登录用户 | - | "/dashboard/moral"、"dashboard/teaching" |
| `modules[].visible` | Boolean | 角色判断 | admin/jiaowu/xuefa/cleader | 登录用户 | - | 前端只显示 visible=true 的项 |
| `alerts[]` | Array | moral.db + 角色判断 | 低分学生预警 | admin/jiaowu/xuefa | 空数组 | 预警消息 |
| `alerts[].level` | String | 硬编码 | - | admin/jiaowu/xuefa | - | "warning" |
| `alerts[].title` | String | 硬编码 | - | admin/jiaowu/xuefa | - | "低分学生关注" |
| `alerts[].message` | String | 低分人数拼接 | - | admin/jiaowu/xuefa | - | f-string 拼接 |
| `updated_at` | String | datetime.now() | 实时 | 登录用户 | - | "YYYY-MM-DD HH:MM:SS" |

---

### 德育驾驶舱（Moral）

**API**: `GET /api/dashboard/moral/summary`

**权限**: admin/jiaowu/xuefa/cleader（班主任只看本班）

| 字段路径 | 类型 | 数据来源 | 统计口径 | 权限范围 | 空状态 | 备注 |
|---------|------|---------|---------|---------|--------|------|
| `cards[]` | Array | moral.db + inout.db | 实时 | admin/jiaowu/xuefa/cleader | 空数组 | 4个固定卡 |
| `cards[0].label` | String | 硬编码 | - | - | - | "可见学生" |
| `cards[0].value` | Number | moral.db student COUNT(status='在校') | 实时 | cleader 只看本班 | 0 | - |
| `cards[1].label` | String | 硬编码 | - | - | - | "日常记录" |
| `cards[1].value` | Number | student_daily_record COUNT | 实时 | admin/jiaowu/xuefa | 0 | - |
| `cards[2].label` | String | 硬编码 | - | - | - | "平均德育分" |
| `cards[2].value` | Number | moral_evaluation AVG(total_score) | 实时 | admin/jiaowu/xuefa/cleader | 0 | round(1位) |
| `cards[3].label` | String | 硬编码 | - | - | - | "当前请假" |
| `cards[3].value` | Number | inout.db active_leave COUNT | 实时 | admin/jiaowu/xuefa/cleader | 0 | 未销假 |
| `charts.score_distribution` | Array | moral_evaluation GROUP BY score_band | 实时 | admin/jiaowu/xuefa/cleader | [] | 玫瑰图数据 |
| `charts.daily_event_mix` | Array | student_daily_record GROUP BY is_positive | 实时 | admin/jiaowu/xuefa | [] | 正负事件占比 |
| `charts.daily_record_trend` | Array | student_daily_record GROUP BY date(近14天) | 近14天 | admin/jiaowu/xuefa | [] | 折线图 |
| `charts.class_score_rank` | Array | moral_evaluation GROUP BY class_id | 实时 | admin/jiaowu/xuefa | [] | 班级平均分排行 |
| `charts.leave_by_class` | Array | inout.db GROUP BY class_name | 实时 | admin/jiaowu/xuefa | [] | 请假班级分布 |
| `tables.low_students` | Array | moral_evaluation WHERE total_score < 60 | 实时 | admin/jiaowu/xuefa/cleader | [] | 低分学生名单 |
| `tables.low_students[].name` | String | student.name | - | - | - | 学生姓名 |
| `tables.low_students[].class_name` | String | class.class_name | - | - | - | 班级名称 |
| `tables.low_students[].total_score` | Number | moral_evaluation.total_score | - | - | - | 德育总分 |
| `tables.leave_students` | Array | inout.db WHERE active=1 AND style!='延时' | 实时 | admin/jiaowu/xuefa/cleader | [] | 当前请假名单 Top20 |
| `tables.leave_students[].name` | String | inout + students cache | - | - | - | 请假学生姓名 |
| `tables.leave_students[].class_name` | String | inout + students cache | - | - | - | 班级名称 |
| `tables.leave_students[].style` | String | inout.style | - | - | - | 请假类型 |
| `tables.leave_students[].days` | Number | inout.days | - | - | - | 请假天数 |
| `tables.leave_students[].status` | String | inout.status | - | - | - | 已请假/已出校等状态 |
| `insights` | Array | 算法计算 | 出勤风险预警 | admin/jiaowu/xuefa/cleader | [] | 态势面板 |
| `insights[].type` | String | 硬编码 | - | - | - | "warning"/"info" |
| `insights[].message` | String | 算法拼接 | - | - | - | 风险描述 |
| `top_n` | Number | Query参数 | 默认5 | - | 5 | 排行数量限制 |
| `updated_at` | String | datetime.now() | 实时 | - | - | 时间戳 |

**已清理重复字段**：
- `leave.students` 已合并到 `tables.leave_students`。
- `leave.count` 已删除，请使用 `cards[3].value`。
- `leave.by_class` 已合并到 `charts.leave_by_class`。
- `file_upload` 块不属于德育驾驶舱，已删除。

---

### 教务驾驶舱（Teaching）

**API**: `GET /api/dashboard/teaching/summary`

**权限**: admin/jiaowu

**⚠️ 禁止字段**: `tables.leave_students`、`leave.students`、`leave.count` —— 教务驾驶舱不展示请假学生

| 字段路径 | 类型 | 数据来源 | 统计口径 | 权限范围 | 空状态 | 备注 |
|---------|------|---------|---------|---------|--------|------|
| `cards[]` | Array | moral.db + filegather.db + Lesson | 实时 + 周范围 | admin/jiaowu | 空数组 | 11个固定卡 |
| `cards[0].label` | String | 硬编码 | - | - | - | "班级" |
| `cards[0].value` | Number | moral.db class COUNT(is_active=1) | 实时 | - | 0 | - |
| `cards[1].label` | String | 硬编码 | - | - | - | "在校学生" |
| `cards[1].value` | Number | moral.db student COUNT(status='在校') | 实时 | - | 0 | - |
| `cards[2].label` | String | 硬编码 | - | - | - | "教师账号" |
| `cards[2].value` | Number | moral.db teacher COUNT(identity_type='teacher') | 实时 | - | 0 | - |
| `cards[3].label` | String | 硬编码 | - | - | - | "区间课时" |
| `cards[3].value` | Number | workload.rows SUM(lesson_count) | 周范围 | - | 0 | - |
| `cards[4].label` | String | 硬编码 | - | - | - | "当前课节" |
| `cards[4].value` | String | current_course.current_period | 实时 | - | "非上课" | - |
| `cards[5].label` | String | 硬编码 | - | - | - | "正在上课" |
| `cards[5].value` | Number | current_course.active_class_count | 实时 | - | 0 | - |
| `cards[6].label` | String | 硬编码 | - | - | - | "待处理文件" |
| `cards[6].value` | Number | filegather.db pending_files COUNT | 实时 | - | 0 | - |
| `cards[7].label` | String | 硬编码 | - | - | - | "本月文件" |
| `cards[7].value` | Number | filegather.db total_files COUNT(本月) | 本月 | - | 0 | - |
| `cards[8].label` | String | 硬编码 | - | - | - | "已完成文件" |
| `cards[8].value` | Number | filegather.db done_files COUNT | 实时 | - | 0 | - |
| `cards[9].label` | String | 硬编码 | - | - | - | "完成率" |
| `cards[9].value` | Number | filegather.db completion_rate | 实时 | - | 0 | percent |
| `cards[10].label` | String | 硬编码 | - | - | - | "逾期文件" |
| `cards[10].value` | Number | filegather.db overdue_pending_count | 实时 | - | 0 | - |
| `charts.teacher_workload_rank` | Array | workload.rows | 周范围 | admin/jiaowu | [] | 教师课时排行条 |
| `charts.class_size_rank` | Array | moral.db class + student COUNT | 实时 | admin/jiaowu | [] | 班级规模排行 |
| `charts.resource_mix` | Array | 硬编码 + moral.db COUNT | 实时 | admin/jiaowu | [] | 班级/学生/教师占比 |
| `charts.file_upload_status` | Array | filegather.db GROUP BY status | 实时 | admin/jiaowu | [] | 文件状态占比 |
| `tables.teacher_workload_rank` | Array | workload.rows | 周范围 | admin/jiaowu | [] | 教师课时排行明细 |
| `tables.file_upload_top_users` | Array | filegather.db by_user | 本月 | admin/jiaowu | [] | 上传排行 |
| `tables.pending_file_list` | Array | filegather.db pending_file_list | 实时 | admin/jiaowu | [] | 待处理文件列表 |
| `tables.recent_file_list` | Array | filegather.db recent_file_list | 实时 | admin/jiaowu | [] | 最近文件列表 |
| `insights` | Array | 算法计算 | 教学运行态势 | admin/jiaowu | [] | 态势面板 |
| `updated_at` | String | datetime.now() | 实时 | - | - | 时间戳 |

**已清理重复字段**：
- `tables.teacher_workload` 已合并到 `tables.teacher_workload_rank`。
- `file_upload` 块已删除，数据已在 cards/charts/tables 中表达。

---

### 班级驾驶舱（Class）

**API**: `GET /api/dashboard/class/summary`

**权限**: admin/jiaowu/xuefa/cleader（班主任只看本班）

| 字段路径 | 类型 | 数据来源 | 统计口径 | 权限范围 | 空状态 | 备注 |
|---------|------|---------|---------|---------|--------|------|
| `cards[]` | Array | moral.db + homework.db + inout.db | 实时 | admin/jiaowu/xuefa/cleader | 空数组 | 10个固定卡 |
| `cards[0].label` | String | 硬编码 | - | - | - | "班级人数" |
| `cards[0].value` | Number | moral.db student COUNT(class_id) | 实时 | cleader 只看本班 | 0 | - |
| `cards[1].label` | String | 硬编码 | - | - | - | "男生" |
| `cards[1].value` | Number | moral.db student COUNT(gender='男') | 实时 | cleader 只看本班 | 0 | - |
| `cards[2].label` | String | 硬编码 | - | - | - | "女生" |
| `cards[2].value` | Number | moral.db student COUNT(gender='女') | 实时 | cleader 只看本班 | 0 | - |
| `cards[3].label` | String | 硬编码 | - | - | - | "性别未维护" |
| `cards[3].value` | Number | moral.db student COUNT(gender IS NULL) | 实时 | cleader 只看本班 | 0 | - |
| `cards[4].label` | String | 硬编码 | - | - | - | "平均德育分" |
| `cards[4].value` | Number | moral_evaluation AVG(total_score) | 实时 | cleader 只看本班 | 0 | round(1位) |
| `cards[5].label` | String | 硬编码 | - | - | - | "低分学生" |
| `cards[5].value` | Number | moral_evaluation COUNT(score<60) | 实时 | cleader 只看本班 | 0 | - |
| `cards[6].label` | String | 硬编码 | - | - | - | "本月作业" |
| `cards[6].value` | Number | homework.db COUNT(本月) | 本月 | cleader 只看本班 | 0 | - |
| `cards[7].label` | String | 硬编码 | - | - | - | "本月公告" |
| `cards[7].value` | Number | homework.db announcement COUNT(本月) | 本月 | cleader 只看本班 | 0 | - |
| `cards[8].label` | String | 硬编码 | - | - | - | "请假人数" |
| `cards[8].value` | Number | inout.db active_leave COUNT | 实时 | cleader 只看本班 | 0 | - |
| `charts.gender_mix` | Array | student GROUP BY gender | 实时 | cleader 只看本班 | [] | 性别占比环图 |
| `charts.score_band` | Array | moral_evaluation GROUP BY score_band | 实时 | cleader 只看本班 | [] | 分数段分布 |
| `tables.low_students` | Array | moral_evaluation WHERE score<60 | 实时 | cleader 只看本班 | [] | 低分学生名单 |
| `tables.birthday_this_month` | Array | student WHERE birthday LIKE 'XX%' | 本月 | cleader 只看本班 | [] | 本月生日学生 |
| `tables.birthday_this_week` | Array | student WHERE birthday 近7天 | 本周 | cleader 只看本班 | [] | 本周生日学生 |
| `tables.leave_students` | Array | inout.db WHERE active=1 AND style!='延时' | 实时 | cleader 只看本班 | [] | 本班当前请假名单 |
| `insights` | Array | 算法计算 | 班级管理风险 | cleader 只看本班 | [] | 态势面板 |
| `class_info.class_id` | Number | Query参数或get_teacher_class_id | 实时 | cleader 默认本班 | - | 班级ID |
| `class_info.class_name` | String | moral.db class.class_name | 实时 | - | - | 班级名称 |
| `updated_at` | String | datetime.now() | 实时 | - | - | 时间戳 |

**已清理重复字段**：
- `leave.students` 已合并到 `tables.leave_students`。
- `leave.count` 已删除，请使用 `cards[8].value`。

---

### 教师工作台（Teacher Workbench）

**API**: `GET /api/dashboard/teacher/workbench`

**权限**: teacher/cleader/admin（个人数据）

| 字段路径 | 类型 | 数据来源 | 统计口径 | 权限范围 | 空状态 | 备注 |
|---------|------|---------|---------|---------|--------|------|
| `cards[]` | Array | Lesson + homework.db + moral.db + invigilation.db | 实时 + 周范围 | teacher本人 | 空数组 | 个人指标卡 |
| `cards[0].label` | String | 硬编码 | - | - | - | "今日课程" |
| `cards[0].value` | Number | Lesson today_lessons COUNT | 实时 | teacher本人 | 0 | - |
| `cards[1].label` | String | 硬编码 | - | - | - | "本周作业" |
| `cards[1].value` | Number | homework.db homework COUNT(本周) | 本周 | teacher本人 | 0 | - |
| `cards[2].label` | String | 硬编码 | - | - | - | "本周公告" |
| `cards[2].value` | Number | homework.db announcement COUNT(本周) | 本周 | teacher本人 | 0 | - |
| `cards[3].label` | String | 硬编码 | - | - | - | "德育记录" |
| `cards[3].value` | Number | moral.db daily_record COUNT(teacher) | 实时 | teacher本人 | 0 | - |
| `cards[4].label` | String | 硬编码 | - | - | - | "点滴记录" |
| `cards[4].value` | Number | moral.db moment_record COUNT(teacher) | 实时 | teacher本人 | 0 | - |
| `cards[5].label` | String | 硬编码 | - | - | - | "监考任务" |
| `cards[5].value` | Number | invigilation.db invigilation_tasks COUNT | 实时 | teacher本人 | 0 | - |
| `cards[6].label` | String | 硬编码 | - | - | - | "区间课时" |
| `cards[6].value` | Number | Lesson workload COUNT | 周范围 | teacher本人 | 0 | - |
| `tables.today_lessons` | Array | Lesson today_lessons | 实时 | teacher本人 | [] | 今日课程列表 |
| `tables.today_lessons[].class_name` | String | Lesson schedule | - | - | - | 班级名称 |
| `tables.today_lessons[].subject` | String | Lesson schedule | - | - | - | 科目 |
| `tables.today_lessons[].period` | String | Lesson time_table | - | - | - | 节次 |
| `tables.today_lessons[].time_range` | String | Lesson time_table | - | - | - | 时间范围 |
| `tables.invigilation_tasks` | Array | invigilation.db invigilation_tasks | 实时 | teacher本人 | [] | 监考任务列表 |
| `tables.invigilation_tasks[].project_name` | String | invigilation.project_name | - | - | - | 考试项目名称 |
| `tables.invigilation_tasks[].date` | String | invigilation.date | - | - | - | 监考日期 |
| `tables.invigilation_tasks[].slot` | String | invigilation.slot | - | - | - | 监考场次 |
| `tables.workload_lessons` | Array | Lesson workload | 周范围 | teacher本人 | [] | 区间课时明细 |
| `updated_at` | String | datetime.now() | 实时 | - | - | 时间戳 |

**已清理重复字段**：
- `workload.lessons` 已合并到 `tables.workload_lessons`。

---

### 监考驾驶舱（Invigilation）

**API**: `GET /api/dashboard/invigilation/summary`

**权限**: admin/jiaowu

| 字段路径 | 类型 | 数据来源 | 统计口径 | 权限范围 | 空状态 | 备注 |
|---------|------|---------|---------|---------|--------|------|
| `cards[]` | Array | invigilation.db | 实时 | admin/jiaowu | 空数组 | 6个固定卡 |
| `cards[0].label` | String | 硬编码 | - | - | - | "考试项目" |
| `cards[0].value` | Number | invigilation.db project COUNT | 实时 | admin/jiaowu | 0 | - |
| `cards[1].label` | String | 硬编码 | - | - | - | "待安排场次" |
| `cards[1].value` | Number | invigilation.db slot WHERE unarranged | 实时 | admin/jiaowu | 0 | - |
| `cards[2].label` | String | 硬编码 | - | - | - | "冲突场次" |
| `cards[2].value` | Number | invigilation.db conflict COUNT | 实时 | admin/jiaowu | 0 | - |
| `cards[3].label` | String | 硬编码 | - | - | - | "安排完整率" |
| `cards[3].value` | Number | invigilation.db arranged/total*100 | 实时 | admin/jiaowu | 0 | percent |
| `cards[4].label` | String | 硬编码 | - | - | - | "通知成功率" |
| `cards[4].value` | Number | invigilation.db success/total*100 | 实时 | admin/jiaowu | 0 | percent |
| `cards[5].label` | String | 硬编码 | - | - | - | "通知失败" |
| `cards[5].value` | Number | invigilation.db failed+skipped COUNT | 实时 | admin/jiaowu | 0 | - |
| `charts.project_status` | Array | invigilation.db project GROUP BY status | 实时 | admin/jiaowu | [] | 考试项目状态占比 |
| `charts.notification_status` | Array | invigilation.db notification GROUP BY status | 实时 | admin/jiaowu | [] | 通知状态占比 |
| `charts.teacher_workload_rank` | Array | invigilation.db teacher_workload GROUP BY teacher | 实时 | admin/jiaowu | [] | 教师监考负载排行 |
| `tables.unarranged_slots` | Array | invigilation.db slot WHERE unarranged | 实时 | admin/jiaowu | [] | 未安排场次列表 |
| `tables.conflict_slots` | Array | invigilation.db conflict_slots | 实时 | admin/jiaowu | [] | 冲突场次详情 |
| `tables.notification_failed` | Array | invigilation.db notification WHERE failed | 实时 | admin/jiaowu | [] | 通知失败记录 |
| `tables.recent_projects` | Array | invigilation.db project ORDER BY created_at DESC | 实时 | admin/jiaowu | [] | 近期考试项目 |
| `tables.teacher_workload_rank` | Array | invigilation.db teacher_workload | 实时 | admin/jiaowu | [] | 教师监考负载排行明细 |
| `top_n` | Number | Query参数 | 默认5 | - | 5 | 排行数量限制 |
| `updated_at` | String | datetime.now() | 实时 | - | - | 时间戳 |

**已清理重复字段**：
- `charts.teacher_workload_top5` 已删除，用 `charts.teacher_workload_rank`。
- `tables.teacher_workload_top5` 已删除，用 `tables.teacher_workload_rank`。

---

### 系统运维驾驶舱（System）

**API**: `GET /api/dashboard/system/summary`

**权限**: admin

| 字段路径 | 类型 | 数据来源 | 统计口径 | 权限范围 | 空状态 | 备注 |
|---------|------|---------|---------|---------|--------|------|
| `cards[]` | Array | databases/*.db + moral.db + task.db | 实时 | admin | 空数组 | 7个固定卡 |
| `cards[0].label` | String | 硬编码 | - | - | - | "数据库文件" |
| `cards[0].value` | Number | databases/*.db EXISTS COUNT | 实时 | admin | 0 | - |
| `cards[1].label` | String | 硬编码 | - | - | - | "总大小" |
| `cards[1].value` | Number | databases/*.db SIZE SUM | 实时 | admin | 0 | MB |
| `cards[2].label` | String | 硬编码 | - | - | - | "总记录数" |
| `cards[2].value` | Number | databases/*.db ROWS SUM | 实时 | admin | 0 | - |
| `cards[3].label` | String | 硬编码 | - | - | - | "活跃用户" |
| `cards[3].value` | Number | member.db user COUNT | 实时 | admin | 0 | - |
| `cards[4].label` | String | 硬编码 | - | - | - | "教师账号" |
| `cards[4].value` | Number | moral.db teacher COUNT(identity='teacher') | 实时 | admin | 0 | - |
| `cards[5].label` | String | 硬编码 | - | - | - | "权限风险" |
| `cards[5].value` | Number | moral.db api_permission WHERE risk | 实时 | admin | 0 | - |
| `charts.role_distribution` | Array | member.db user GROUP BY role | 实时 | admin | [] | 角色分布 |
| `charts.teacher_identity` | Array | moral.db teacher GROUP BY identity_type | 实时 | admin | [] | 教师身份占比 |
| `charts.operation_stats` | Array | operation_log.db GROUP BY date(近7天) | 近7天 | admin | [] | 操作统计趋势 |
| `tables.db_files` | Array | databases/*.db FILE INFO | 实时 | admin | [] | 数据库文件列表 |
| `tables.db_files[].name` | String | 硬编码 | - | - | - | 文件名 |
| `tables.db_files[].exists` | Boolean | os.path.exists | 实时 | - | false | 是否存在 |
| `tables.db_files[].size_kb` | Number | os.path.getsize | 实时 | - | 0 | 文件大小 |
| `tables.db_files[].tables` | Array | SQLite table list | 实时 | - | [] | 表列表 |
| `tables.api_permission_risks` | Array | moral.db api_permission WHERE risk | 实时 | admin | [] | 权限风险列表 |
| `tables.recent_operations` | Array | operation_log.db ORDER BY timestamp DESC | 近50条 | admin | [] | 最近操作日志 |
| `task_stats` | Object | task.db task COUNT GROUP BY status | 实时 | admin | {} | 任务状态统计 |
| `task_stats.total` | Number | task.db task COUNT | 实时 | admin | 0 | - |
| `task_stats.active` | Number | task.db task WHERE status='active' | 实时 | admin | 0 | - |
| `task_stats.paused` | Number | task.db task WHERE status='paused' | 实时 | admin | 0 | - |
| `updated_at` | String | datetime.now() | 实时 | - | - | 时间戳 |

---

## 刷新频率建议

| 驾驶舱 | 建议刷新频率 | 原因 |
|-------|------------|------|
| Overview | 5分钟 | 总览数据变化较慢 |
| Moral | 3分钟 | 德育记录和请假实时变化 |
| Teaching | 3分钟 | 当前课节实时变化，文件流转频繁 |
| Class | 5分钟 | 班级数据变化较慢 |
| Teacher Workbench | 3分钟 | 今日课程实时变化 |
| Invigilation | 5分钟 | 监考安排变化较慢 |
| System | 10分钟 | 系统状态变化很慢 |

---

## 前端字段使用契约

前端 Vue 文件使用的字段路径必须全部在指标字典中有定义，否则视为违规。

| Vue 文件 | 使用的字段路径 | 契约状态 |
|---------|---------------|---------|
| Overview.vue | `cards`, `modules`, `alerts` | ✅ 全部定义 |
| MoralDashboard.vue | `cards`, `charts.score_distribution`, `charts.daily_event_mix`, `charts.daily_record_trend`, `charts.class_score_rank`, `tables.low_students`, `tables.leave_students` | ⚠️ `tables.leave_students` 重复，待清理 |
| TeachingDashboard.vue | `cards`, `charts.resource_mix`, `charts.file_upload_status`, `charts.teacher_workload_rank`, `charts.class_size_rank`, `tables.file_upload_top_users`, `tables.pending_file_list` | ✅ 全部定义 |
| ClassDashboard.vue | `cards`, `charts.gender_mix`, `charts.score_band`, `tables.low_students`, `tables.birthday_this_month`, `tables.birthday_this_week`, `tables.leave_students` | ⚠️ `tables.leave_students` 重复，待清理 |
| TeacherWorkbench.vue | `cards`, `tables.today_lessons`, `tables.invigilation_tasks`, `tables.workload_lessons` | ✅ 全部定义 |
| InvigilationDashboard.vue | `cards`, `charts.project_status`, `charts.notification_status`, `charts.teacher_workload_rank`, `tables.unarranged_slots`, `tables.conflict_slots`, `tables.notification_failed` | ✅ 全部定义 |
| SystemDashboard.vue | `cards`, `charts.role_distribution`, `charts.teacher_identity`, `charts.operation_stats`, `tables.db_files`, `tables.api_permission_risks`, `tables.recent_operations` | ✅ 全部定义 |

---

## Batch50 执行记录

### 发现的重复字段

| 驾驶舱 | 重复字段 | 处理建议 |
|-------|---------|---------|
| Moral | `tables.leave_students` 与 `leave.students` | 已合并到 `tables.leave_students` |
| Moral | `leave.count` 与 `cards[3].value` | 已删除 `leave.count` |
| Moral | `leave.by_class` 与 `charts.leave_by_class` | 已合并到 `charts.leave_by_class` |
| Moral | `file_upload` 块 | 不属于德育驾驶舱，已删除 |
| Teaching | `tables.teacher_workload` 与 `tables.teacher_workload_rank` | 已合并到 `tables.teacher_workload_rank` |
| Teaching | `file_upload` 块 | 数据已在 charts/tables 中表达，已删除 |
| Class | `tables.leave_students` 与 `leave.students` | 已合并到 `tables.leave_students` |
| Class | `leave.count` 与 `cards[8].value` | 已删除 `leave.count` |
| TeacherWorkbench | `tables.workload_lessons` 与 `workload.lessons` | 已合并到 `tables.workload_lessons` |
| Invigilation | `charts.teacher_workload_top5` 与 `charts.teacher_workload_rank` | 已删除 `teacher_workload_top5` |
| Invigilation | `tables.teacher_workload_top5` 与 `tables.teacher_workload_rank` | 已删除 `teacher_workload_top5` |

### 契约测试覆盖

所有驾驶舱的关键字段必须有契约测试覆盖，确保不会被误删或误改。

---
