# 函数级全量审计与重构升级方案

## 版本信息

- 生成日期：2026-05-02
- 适用项目：红皇后 / 数字天龙校园综合管理系统
- 审计依据：`docs/function-inventory.md`、现有后端路由、前端页面、测试结果和项目文档
- 审计目标：防止项目继续变成“缝合式系统”，在保留现有功能的前提下明确函数职责、迁移边界和升级路线

## 一、审计结论

本次已建立函数级全量清单：

| 范围 | 审计单元数 | 说明 |
|------|------------|------|
| 后端 Python | 1545 | 类、函数、异步函数、方法、路由处理函数、脚本函数、测试函数 |
| 前端 JS/Vue | 694 | 页面方法、组合函数、store 方法、API 方法、组件方法、测试辅助函数 |
| 合计 | 2239 | 详见 `function-inventory.md` |

整体判断：

- 项目功能不是少，而是多条历史演进线交织在一起。
- 最大风险不是某个单点 bug，而是“业务功能、API、数据库、微信指令、前端页面、脚本”之间边界不清。
- 重构不能以删功能为目标，必须先把所有函数映射到功能域，再按功能域迁移。
- `datas_api_legacy.py`、`dashboard.py`、`invigilation.py`、`moral/*` 大模块和多个大 Vue 页面，是防止系统继续缝合化的第一批治理对象。

## 二、功能域地图

### 2.1 后端入口与运行时

| 文件/模块 | 函数职责 | 保留要求 | 重构方向 |
|------|----------|----------|----------|
| `lesson/main.py` | FastAPI 应用创建、CORS、HTTPS 重定向、异常处理、WebSocket 注册、健康检查、微信消息入口、队列消费生命周期 | 必须保留应用入口、`/api/health`、`/ws`、微信消息入口 `/` | 拆成 `app/main.py`、`core/middleware.py`、`workers/queue_worker.py`、`integrations/wechat/message_entry.py` |
| `lesson/websocket.py` | 连接管理、用户/房间连接、广播、心跳、作业/课表更新通知 | 保留 `/ws` 协议和消息类型 | 抽成 `integrations/websocket/manager.py`，前端统一从配置生成 ws URL |
| `lesson/sendqueue.py` | 微信发送队列、消息生产、消费、过期清理、失败重试、文本/图片/文件/应用消息发送 | 保留队列表和发送 API 兼容 | 拆成 `workers/send_queue.py`、`integrations/wechat/client.py`、`repositories/queue_repo.py` |
| `lesson/wxmsg.py` | 微信消息解析、不同消息类型处理、入库、字符串化、@ 判断 | 保留消息解析结果字段和 `MessageDB` 兼容 | 将消息模型、解析器、数据库仓储分离 |

### 2.2 认证、教师与身份

| 文件/模块 | 函数职责 | 保留要求 | 重构方向 |
|------|----------|----------|----------|
| `datas_api/auth.py` | 密码哈希/校验、兼容明文验证、JWT 创建和解析、登录接口、当前用户依赖 | `/api/token` 不变，JWT payload 兼容 | 抽 `auth_service.py`、`security.py`；废弃明文密码兼容和 `raw_pwd` 新写入 |
| `datas_api/admin.py` | 管理员用户列表、随机重置密码、设置密码、重置密码状态 | 管理员功能保留 | 用 `secrets` 生成强随机临时密码；停止持久化明文 |
| `datas_api/teachers.py` | 教师 CRUD、任教班级关系、初始化任教班级、教师改密 | 保留教师管理和任教班级维护 | 拆 `teacher_router.py`、`teacher_service.py`、`teacher_repo.py`；课表扫描迁移为后台任务 |
| `utils/teacher_db.py` | `moral.db.teacher` 统一主表 schema、迁移、查询、增删改 | 保留主表策略 | 收敛到 repository，所有身份读写只走一个出口 |

### 2.3 legacy 业务接口

`lesson/models/datas_api_legacy.py` 是当前最明显的缝合风险。它承载多个业务域，且导入期存在课表读取副作用。

| 功能组 | 当前函数类型 | 必须保留的功能 | 目标模块 |
|------|--------------|----------------|----------|
| 班级代码和课表 | `get_class_codes`、`get_class_schedule`、`get_todays_schedule`、`get_schedules`、`get_current_classes`、教师课表相关函数 | 班级选择、课表展示、实时课程、教师课表、本周/下周课表 | `api/routers/schedule.py` + `services/schedule_service.py` |
| 作业公告 | 作业查询、发布、批量删除、更新、公告发布/更新/删除 | 班级作业、公告完整可用 | `api/routers/homework.py`、`api/routers/announcement.py` |
| 班级基础信息 | 教师消息、班级信息、学生列表、学生导入导出 | 班级页面功能不丢 | `api/routers/classes.py` |
| 请假/延时/日常旧记录 | 延时申请、请假记录提交/查询/核销、旧 daily 查询和导出 | 保留现有前端页面和历史数据查询 | `api/routers/leave.py`、`api/routers/legacy_daily.py` |
| 会员与微信权限 | member CRUD、permission CRUD | 保留微信指令管理能力 | `api/routers/wechat_admin.py` |
| 定时任务管理 | 任务函数列表、任务 CRUD | 保留任务后台管理 | `api/routers/task_admin.py` |

迁移策略：旧路径先不变。先把函数体搬入 service，旧 router 调 service。确认前端无回归后，再考虑新路径和文档更新。

### 2.4 德育评价系统

德育模块功能完整，是系统核心业务之一。重构重点不是重写规则，而是拆清楚“路由、权限、计算、数据访问、审计”。

| 模块 | 函数职责 | 不能遗漏的功能 | 重构方向 |
|------|----------|----------------|----------|
| `moral/base.py` | 静态权限、动态 API 权限辅助、数据范围、班级/任教范围、学期、评价等级、操作日志 | 数据范围判断、班主任范围、任教班级范围、操作日志 | 拆为 `moral/policies.py`、`moral/scopes.py`、`moral/semester_service.py`、`moral/audit_service.py` |
| `moral/admin.py` | 级号、班级、学年学期、学生、批量导入、状态变更、日志、系统配置 | 基础数据管理和学生状态流转 | 拆基础配置 service，批量导入独立 import service |
| `daily_record.py` | 日常事件类型、日常记录 CRUD、批量创建、学生统计、事件类型导入 | 日常记录和事件类型管理 | 事件类型 service 与记录 service 分离 |
| `school_event.py` | 校级事件类型、校级事件记录、批量导入 | 校级加扣分数据 | 与 daily 共享 event type 模型或基类 |
| `task.py`、`carryover.py` | 德育任务 CRUD、完成记录、批量导入、任务结转预览/执行/日志 | 任务分值与结转规则 | 拆 task_service 和 carryover_service |
| `punishment.py`、`escalation*.py` | 处分记录、撤销、复核、累进规则和学生违纪计数 | 处分生命周期和累进处罚建议 | 处分 service、累进规则 service、审计日志必须保留 |
| `evaluation.py` | 学生/班级/级号评价查询、批量计算 | 德育总分和等级计算 | 建立 evaluation_engine，配置读取不能硬编码 |
| `profile.py` | 学生画像生成、异步生成、状态查询、批量生成、配置 | 画像生成和历史 | 将生成任务、AI 调用、画像存储分离 |
| `consultation.py` | AI 诊疗会话、消息、关闭 | 会话和消息记录 | 抽 consultation_service，后续可接不同 AI provider |
| `birthday.py` | 今日生日、近期生日 | 生日提醒展示 | 补提醒记录和发送状态闭环 |
| `moment_api.py`、`timeline_api.py` | 点滴记录、一生一册时光轴 | 学生成长记录展示 | 点滴记录与德育画像/评价松耦合 |
| `collective.py` | 集体事件、分配记录、学生集体得分汇总 | 班级集体事件向学生分配 | 分配快照逻辑独立，避免调班影响历史 |
| `api_permission.py` | API 权限配置、模块、同步旧 YAML、权限检查、数据范围规则 | 动态权限核心 | 拆 config repo、permission evaluator、admin router |

### 2.5 监考安排

`datas_api/invigilation.py` 功能已较完整，但单文件承载项目、安排、交换、变更、通知、模板、导入、导出、报表。应按子能力拆分。

| 功能组 | 当前职责 | 目标拆分 |
|------|----------|----------|
| 项目管理 | 考试项目 CRUD、状态维护 | `invigilation/project_service.py` |
| 安排管理 | slots 查询、批量保存、交换教师 | `invigilation/slot_service.py` |
| 变更预览 | 比较版本和当前安排 | `invigilation/change_service.py` |
| 通知 | 生成通知消息、发送、日志 | `invigilation/notification_service.py` |
| 导入导出 | 模板、Excel 导入、导出安排 | `invigilation/import_export_service.py` |
| 报表 | 教师工作量统计 | `invigilation/report_service.py` |

### 2.6 驾驶舱

`dashboard.py` 聚合了多个业务域统计。它应成为“指标编排层”，不应该直接承载每个业务域的细节查询。

| 当前指标组 | 目标服务 |
|------|----------|
| 总览 | `dashboard/overview_service.py` |
| 德育摘要 | 调用 `moral/statistics_service.py` |
| 教务摘要 | 调用 `schedule/statistics_service.py`、`filegather/statistics_service.py` |
| 班级摘要 | 调用 `class/statistics_service.py` |
| 教师工作台 | 调用 teacher、schedule、homework、invigilation 服务 |
| 监考摘要 | 调用 `invigilation/report_service.py` |
| 系统摘要 | 调用 `monitor_service.py`、数据库统计服务 |

### 2.7 文件、课表、教学、微信指令

| 模块 | 函数职责 | 重构方向 |
|------|----------|----------|
| `filegather.py`、`filegather_db.py` | 上传、列表、删除、管理员处理、下载、统计 | router/service/repo 分离，文件路径和权限检查独立 |
| `models/lesson/lesson.py` | 课表更新、图片生成、班级/教师课表、今日课表、群发、模板、教师维护 | 继续拆到 repository、service、notifier、renderer |
| `schedule_repository.py`、`schedule_service.py`、`schedule_notifier.py`、`image_renderer.py` | 已有分层雏形 | 优先复用，legacy 课表接口迁入这些服务 |
| `homework.py` | 作业、公告数据库与微信触发函数 | Web API 和微信指令入口分离 |
| `notes.py`、`zhaosheng.py`、`generate_qr.py`、`lound.py` | 课时记录、招生二维码、大声 PK | 作为独立小功能保留，统一到 integrations 或 features |

### 2.8 网络设备与招生应用

| 模块 | 函数职责 | 风险 | 建议 |
|------|----------|------|------|
| `models/network/uac.py`、`ess.py`、`ruijie.py` | 网络账号、WiFi、核心设备查询和管理 | 外部设备依赖强，凭据敏感，失败难测 | 独立为 `integrations/network`，所有凭据从配置读取，增加 dry-run 和错误分类 |
| `models/application/application.py` | 招生数据、院校/专业、投档、梯度策略、图片报表 | 文件大、算法和渲染混合 | 拆数据读取、计算策略、图表渲染、微信入口 |
| `application_V1.0.py` | 旧版本应用逻辑 | 可能是历史备份 | 标注 deprecated，确认无引用后移入 archive |

### 2.9 前端函数域

| 领域 | 函数职责 | 重构方向 |
|------|----------|----------|
| `App.vue` | 登录、导航、班级选择、菜单权限、401 拦截 | 拆成布局组件和权限 composable |
| `router/index.js` | 路由表、协议切换、登录守卫 | 路由按 feature 拆分，守卫独立 |
| `stores/auth.js` | token、JWT 解析、角色判断、登录、登出 | token 解析工具化，角色判断统一复用 |
| `stores/apiPermission.js` | API 权限缓存和同步判断 | 作为菜单和按钮权限唯一来源 |
| `api/modules/moral.js` | 德育前端 API 方法 | 按 daily、school、task、punishment、profile、config 拆文件 |
| `views/*.vue` | 页面数据加载、筛选、弹窗、提交、导入导出 | 大页面拆 components + composables |
| `components/*` | 骨架屏、移动卡片、图表、课程详情 | 保留为 shared components，统一 props 和事件 |
| `utils/*`、`composables/*` | 时间、错误处理、加载态、筛选持久化、WebSocket、权限判断 | 合并重复权限逻辑，WebSocket URL 从配置生成 |

## 三、不能遗漏的功能清单

重构前必须把以下功能纳入冒烟测试或接口测试：

1. 登录、登出、token 解析、管理员/教务/学发/班主任/教师菜单显示。
2. 班级选择、班级代码列表、班级信息、学生列表。
3. 课程表、总课表、实时课程、教师课表、课表上传更新。
4. 作业查询、发布、更新、删除、批量删除。
5. 公告查询、发布、更新、删除。
6. 文件上传、我的文件、管理员待处理、已处理、标记完成、下载、统计。
7. 请假记录提交、查询、核销，延时申请提交和查询。
8. 德育基础配置：级号、班级、学生、学年学期、当前学期、系统配置、日志。
9. 德育日常表现：事件类型、记录 CRUD、批量创建、统计、批量导入。
10. 校级事件：事件类型、记录 CRUD、批量导入。
11. 德育任务：任务 CRUD、完成记录、批量导入、结转预览/执行/日志。
12. 处分：创建、更新、撤销、复核、累进规则、学生累计进度。
13. 德育评价：学生、班级、级号评价查询和计算。
14. 学生画像：查询、同步生成、异步生成、批量生成、状态查询、配置。
15. AI 诊疗：会话列表、创建、详情、更新、添加消息、关闭。
16. 生日：今日生日、近期生日。
17. 点滴记录：列表、创建、更新、删除、导出。
18. 一生一册：学生搜索、时光轴查询。
19. 集体事件：事件 CRUD、分配查询/更新、学生汇总。
20. API 权限：配置、模块、初始化、同步旧 YAML、检查、我的权限、分组。
21. 监考安排：教师列表、项目 CRUD、安排 CRUD、交换教师、变更预览、通知、日志、模板、导入、导出、工作量报表。
22. 驾驶舱：总览、德育、教务、班级、教师工作台、监考、系统运维。
23. 系统管理：会员、微信权限、任务管理、系统监控、教师管理、任教班级。
24. 微信消息：消息入库、规则触发、AI 指令翻译、发送队列、文本/图片/文件/应用消息发送。
25. WebSocket：连接、身份注册、房间、心跳、作业和课表通知。
26. 网络设备集成：UAC、ESS、锐捷核心状态和相关微信触发函数。
27. 招生/应用：二维码、院校/专业查询、投档、梯度策略、报表图片。

## 四、详细升级方案

### 4.1 第一阶段：审计固化与测试护栏

目标：让所有现有功能有清单、有入口、有保护。

任务：

1. 保留 `function-inventory.md`，作为重构防遗漏清单。
2. 为“不能遗漏的功能清单”建立冒烟测试表。
3. 修复后端随机密码测试失败。
4. 消除 `datas_api_legacy.py` 导入期课表读取副作用。
5. 给后端测试配置可写临时目录和 Matplotlib 缓存目录。
6. 前端执行 `npm run test:run`，后端执行 `python -m pytest -q`。

验收：

- 测试全部通过。
- 所有业务域至少有一个验证入口。
- 后续迁移 PR 必须说明影响哪些清单项。

### 4.2 第二阶段：公共基础设施统一

目标：先拆掉系统缝合处最明显的公共重复。

任务：

1. 统一前端 HTTP 客户端，删除硬编码 `localhost:8000` 的旧 axios 实例。
2. 统一 token 注入、401 处理、错误提示、响应解析和重试策略。
3. 后端统一响应模型和错误格式。
4. 后端统一数据库路径、连接上下文、WAL 参数、备份入口。
5. 后端统一权限依赖和审计日志调用。

验收：

- 旧 API 模块全部复用同一个 HTTP client。
- 后端不再新增裸路径拼接和散落连接逻辑。
- 登录过期行为一致。

### 4.3 第三阶段：后端 legacy 解耦

目标：把 `datas_api_legacy.py` 从“多业务缝合文件”改为兼容入口。

任务：

1. 按功能组建立新 router 文件。
2. 从 legacy 文件迁出 service 函数。
3. 旧路由路径保持不变，只调用 service。
4. 给每组 service 增加接口测试。
5. 删除导入期全局缓存副作用，改懒加载或启动期显式初始化。

验收：

- `datas_api_legacy.py` 行数显著下降。
- 新业务不再进入 legacy。
- 课表、作业、公告、请假、会员、任务管理功能全部通过冒烟。

### 4.4 第四阶段：核心业务服务化

目标：让德育、监考、驾驶舱不再由超大路由文件承载全部逻辑。

任务：

1. 德育拆 `policy/scope/audit/evaluation/import/profile/task/punishment` 服务。
2. 监考拆项目、安排、变更、通知、导入导出、报表服务。
3. 驾驶舱拆指标服务，业务统计回到对应业务域。
4. 数据库操作沉到 repository。
5. 大型 SQL 统计补充索引和缓存策略。

验收：

- 路由函数只做鉴权、参数解析、调用 service、返回响应。
- 每个 service 有独立测试或明确冒烟路径。
- 指标口径有文档说明。

### 4.5 第五阶段：前端页面瘦身

目标：让前端不再靠大页面承载全部交互。

任务：

1. 拆 `App.vue` 为布局、导航、登录、班级选择、权限 composable。
2. 拆 `InvigilationArrange.vue` 为多个业务组件。
3. 拆 `TeacherManage.vue` 为教师表格、表单、任教班级、密码操作。
4. 拆德育配置和记录页面中的导入导出、表单弹窗、筛选表格。
5. 前端 API 模块按业务域拆分，`moral.js` 不再继续膨胀。

验收：

- 大页面行数下降，复杂逻辑进入 composable 或 feature module。
- 页面只保留展示、交互编排和事件连接。
- Vitest 全部通过。

### 4.6 第六阶段：目录迁移与长期演进

目标：从“能维护”升级到“新人能接手、功能能扩展”。

任务：

1. 后端逐步迁移到 `app/api/services/repositories/core/integrations/workers` 结构。
2. 前端逐步迁移到 `shared/features/pages` 结构。
3. 文档从方案稿升级为实现说明和运行手册。
4. 建立数据库备份、恢复、迁移、校验流程。
5. 建立 release checklist：测试、冒烟、备份、文档、回滚。

验收：

- 目录名称能反映职责。
- 新增功能有明确落点。
- 不需要阅读超大 legacy 文件就能理解主流程。

## 五、优先级排序

| 优先级 | 项目 | 原因 |
|------|------|------|
| P0 | 修复密码测试、消除导入副作用、统一前端 API 客户端 | 当前已影响测试、安全和部署一致性 |
| P1 | legacy 拆分、App.vue 拆分、raw_pwd 退场 | 缝合风险最高，收益明确 |
| P1 | 德育权限与数据范围测试 | 防止重构造成越权或数据遗漏 |
| P2 | 监考和驾驶舱服务化 | 大文件明显，业务边界清晰，适合拆分 |
| P2 | 前端大页面批量瘦身 | 改善维护体验和后续升级速度 |
| P3 | 目录物理迁移 | 等 service/repository 稳定后再做，减少震荡 |

## 六、函数清单使用方法

1. 每次重构前，在 `function-inventory.md` 找到对应文件和函数。
2. 标记函数属于：保留、迁移、合并、废弃候选。
3. 迁移函数时保留旧入口测试，确认行为一致。
4. 删除函数前必须确认：无路由引用、无微信规则引用、无前端调用、无脚本调用、无测试依赖。
5. 每完成一个模块迁移，重新生成函数清单并比较数量变化。

## 七、结论

这个项目可以重构，但不能粗暴重写。正确路线是先把 2239 个函数级单元纳入清单管理，再用测试和冒烟保护现有功能，最后按功能域逐步拆开。这样既能避免遗漏功能，也能防止系统继续变成难以维护的缝合体。
