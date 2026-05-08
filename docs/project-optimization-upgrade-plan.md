# 项目文档整合与优化升级方案

## 版本信息

- 整理日期：2026-05-02
- 适用项目：红皇后 / 数字天龙校园综合管理系统
- 技术栈：Python 3.10+ / FastAPI / SQLite / Vue 3 / Vite / Element Plus / Pinia
- 数据库目录：`lesson/databases`
- 本文定位：整合 `docs/` 目录现有说明文档，并沉淀本次代码审阅后的重构与优化升级路线图。
- 函数级审计：详见 `function-inventory.md` 和 `function-level-audit-and-refactor-plan.md`。
- AI 执行手册：详见 `ai-refactor-execution-playbook.md`。

## 一、现有文档体系整合

`docs/` 目录目前由系统总览、专题设计、实施方案和运维手册组成。后续维护时建议按“总览优先、专题深入、方案归档”的方式阅读和更新。

| 文档 | 当前定位 | 后续维护建议 |
|------|----------|--------------|
| `system-architecture.md` | 系统功能、API、页面、角色权限、数据库和测试状态总览 | 作为架构主索引维护，新增模块时同步更新路由、API 和页面清单 |
| `moral-evaluation-system.md` | 德育评价系统业务规则、数据模型、权限、API 和实施要点 | 作为德育业务权威文档维护，规则变化优先更新此文档 |
| `moral-config-guide.md` | 德育后台配置操作手册 | 保持面向管理员和业务配置人员，不混入代码实现细节 |
| `data-dashboard-implementation-plan.md` | 全系统数据驾驶舱建设方案 | 已有部分页面和接口落地，后续应从“方案稿”升级为“驾驶舱实现说明” |
| `invigilation-arrangement-implementation-plan.md` | 监考安排功能实现方案 | 当前代码已存在监考后端、页面和数据库，建议补充实际接口与使用手册 |
| `database-consolidation-report.md` | `lesson/databases` 多库梳理与教师主表合并记录 | 作为数据库演进记录维护，涉及身份、教师、微信会员时必须同步 |
| `nginx-https-config.md` | Nginx HTTPS 反向代理和重定向配置 | 作为部署运维手册维护，端口或域名策略变化时同步 |
| `function-inventory.md` | 后端 Python 与前端 JS/Vue 的函数级全量清单 | 作为重构防遗漏台账，迁移或删除函数前先查此文档 |
| `function-level-audit-and-refactor-plan.md` | 函数级审计后的详细重构升级方案 | 作为具体重构执行指南，按功能域推进 |
| `ai-refactor-execution-playbook.md` | 面向其他 AI 工具的重构执行手册 | 作为施工单使用，包含批次、验收、重复函数合并和 Codex 复核流程 |
| `README.md` | 文档目录索引 | 每新增或废弃文档时同步更新 |

建议新增本文作为“项目当前状态与升级路线”的入口：新人先读本文，再按模块读专题文档。

## 二、项目当前架构概览

### 2.1 目录结构

| 目录 | 说明 |
|------|------|
| `frontend` | Vue 3 前端，包含路由、页面、Pinia 状态、API 模块、组件和测试 |
| `lesson` | FastAPI 后端，包含 API 聚合、业务模型、微信消息、任务队列、数据库工具和测试 |
| `lesson/databases` | SQLite 数据库目录，包含 `moral.db`、`member.db`、`homework.db`、`filegather.db`、`invigilation.db` 等 |
| `lesson/config` | YAML 配置与日志配置 |
| `docs` | 项目文档和专题方案 |
| `scripts` | Windows / Unix 启停、安装脚本 |
| `backups` | 数据库备份和迁移备份 |

### 2.2 后端架构

后端入口为 `lesson/main.py`，主要职责：

- 初始化 FastAPI 应用、CORS、HTTPS 强制跳转和全局异常处理。
- 注册 `/api` 聚合路由、`/api/loudpk`、`/ws` WebSocket 和 `/api/health`。
- 在 lifespan 中启动数据库优化、系统监控、定时任务和发送队列消费。
- 处理微信消息入口 `/`，通过规则触发消息转发、自动回复和业务函数。

API 聚合入口为 `lesson/models/datas_api/__init__.py`，包含：

- `auth.py`：JWT 登录认证、密码校验和当前用户解析。
- `admin.py`：管理员用户列表、重置密码、设置密码。
- `teachers.py`：教师档案、任教班级、改密。
- `filegather.py`：文件上传、教务文件处理、下载和统计。
- `dashboard.py`：总览、德育、教务、班级、教师、监考、系统驾驶舱接口。
- `invigilation.py`：监考项目、安排、导入导出、通知和报表。
- `moral/*`：德育评价系统的全部业务模块。
- `datas_api_legacy.py`：尚未拆分的课表、作业、公告、请假、会员、任务等历史接口。

### 2.3 前端架构

前端入口为 `frontend/src/App.vue`，负责全局布局、顶部导航、登录弹窗、班级选择和权限菜单。

核心结构：

- `src/router/index.js`：路由表和登录/协议守卫。
- `src/stores/auth.js`：登录态、JWT 解析和角色判断。
- `src/stores/apiPermission.js`：德育 API 权限缓存。
- `src/shared/api/httpClient.js`、`src/api/index.js`、`src/api/modules/*`：API 封装。
- `src/views`：业务页面。
- `src/views/moral`：德育功能页面。
- `src/views/dashboard`：数据驾驶舱页面。

### 2.4 数据库架构

系统当前使用多 SQLite 数据库。数据库梳理结论以 `database-consolidation-report.md` 为准。

| 数据库 | 定位 |
|------|------|
| `moral.db` | 德育、学生、班级、教师统一主表、角色权限、评价和扩展能力 |
| `member.db` | 微信指令权限、联系人、群聊关系，会员身份已并入 `moral.db.teacher` |
| `homework.db` | 作业、晨读、公告 |
| `filegather.db` | 文件上传和教务处理 |
| `invigilation.db` | 监考项目、安排、版本、通知日志 |
| `inout.db` | 请假 / 出入校 |
| `messages.db` | 微信消息日志 |
| `queues.db` | 消息发送队列 |
| `task.db` | 定时任务 |
| `daily.db` | 旧日常记录，暂不自动并入德育日常表现 |
| `colleges.db` | 高考 / 院校数据 |

### 2.5 目录与代码体量判断

当前项目能运行、功能覆盖面较广，但目录结构和代码体量已经出现“历史功能持续叠加后自然变复杂”的特征。它不是无序堆砌，但已经需要一次有边界、有测试保护的结构治理。

函数级静态审计已固化在 `function-inventory.md`：后端 Python 识别到 1545 个类/函数/方法，前端 JS/Vue 识别到 694 个函数/方法，合计 2239 个审计单元。详细保留要求和拆分策略见 `function-level-audit-and-refactor-plan.md`。

主要表现：

| 现象 | 说明 | 影响 |
|------|------|------|
| 后端目录命名混杂 | `lesson/models/datas_api`、`lesson/models/lesson`、`lesson/models/manage`、`lesson/models/application` 同时承载 API、业务逻辑、数据读写和消息指令 | 新人难以判断模块边界，功能扩展容易放错位置 |
| legacy 文件过大 | `lesson/models/datas_api_legacy.py` 超过 2300 行，承担课表、作业、公告、请假、会员、任务等历史接口 | 导入副作用、测试困难、修改风险高 |
| 大模块集中 | `invigilation.py`、`dashboard.py`、`moral/admin.py`、`moral/api_permission.py`、`moral/profile.py` 等均超过 1000 行或接近 1000 行 | 单文件职责过多，局部修改容易影响多个业务路径 |
| 前端页面偏大 | `InvigilationArrange.vue`、`TeacherManage.vue`、`App.vue`、多个德育页面体量较大 | UI、状态、权限、API 调用耦合，复用和测试成本高 |
| API 封装分裂 | 已收敛到 `src/shared/api/httpClient.js` + `src/api/modules/*`，`src/api/index.js` 作为聚合入口 | 后续禁止恢复页面直连底层 HTTP |
| 方案稿和实现状态并存 | 部分 docs 仍是实现方案，代码已经部分或完全落地 | 读者可能不知道哪些是已实现、哪些是规划 |

结论：

- 当前代码“功能完整度”高于“结构清晰度”。
- 重构的目标不是改技术栈，也不是一次性推倒重写，而是在保证现有 API、页面和数据库可继续工作的前提下，把目录边界、模块职责和扩展点整理清楚。
- 重构优先级应遵循“先保护功能，再移动结构；先拆副作用，再拆大文件；先统一接口，再升级体验”。

## 三、功能现状总结

### 3.1 已形成闭环的功能域

| 功能域 | 当前状态 |
|------|----------|
| 登录认证 | JWT 登录，教师账号主表已统一到 `moral.db.teacher` |
| 班级与课表 | 班级信息、学生、课表、实时课程和课表文件仍以 legacy 模块为主 |
| 作业公告 | 班级作业、公告发布、查询、更新和删除功能可用 |
| 文件流转 | 教师上传、我的文件、教务查看、标记完成、下载和统计 |
| 德育评价 | 基础配置、日常表现、校级事件、任务、处分、评价、画像、生日、AI 诊疗、点滴记录、集体事件已模块化 |
| 监考安排 | 考试项目、安排、导入导出、变更预览、通知和报表已具备代码实现 |
| 数据驾驶舱 | 已有多类驾驶舱接口和前端页面，仍需进一步统一指标口径和权限边界 |
| 微信消息与任务 | 微信消息入库、规则触发、发送队列、定时任务已存在 |

### 3.2 测试状态

本次审阅运行结果：

- 前端：`npm run test:run`，5 个测试文件、139 个用例通过。
- 后端：`python -m pytest -q`，149 个用例中 148 个通过、1 个失败。

后端失败点：

- `tests/test_api.py::TestPasswordResetAPI::test_generate_random_password_contains_alphanumeric`
- 原因：管理员随机重置密码使用 `random.choices(string.ascii_letters + string.digits, k=8)`，不能保证一定包含数字。

## 四、本次代码审阅发现

### 4.1 高优先级问题

| 问题 | 影响 | 建议 |
|------|------|------|
| 随机重置密码不保证数字 | 后端测试失败，密码策略不稳定 | 改为强制包含字母和数字，并用 `secrets` 生成 |
| 密码兼容明文验证和 `raw_pwd` 落库 | 存在敏感信息留存风险 | 停止写入明文，迁移历史明文字段，保留一次性临时密码显示 |
| legacy 模块导入时读取课表并创建目录 | 测试收集、启动和部署容易受路径权限影响 | 改为懒加载或 lifespan 显式初始化 |
| 前端 API 客户端重复 | baseURL、token、401、重试和响应格式不一致 | 合并为唯一 `httpClient`，模块 API 全部复用 |
| `App.vue` CSS 括号异常 | 导航和移动端样式可能不可预测 | 修复样式块结构并补构建检查 |
| 任教班级空映射解释为全校 | 可能扩大教师数据可见范围 | 改为默认无权限，管理员初始化后再开放范围 |

### 4.2 中优先级问题

| 问题 | 影响 | 建议 |
|------|------|------|
| `datas_api_legacy.py` 文件过大 | 维护成本高，副作用多 | 按课表、作业、请假、会员、任务拆分 |
| 多处 SQL 和权限判断分散 | 同一权限规则可能产生实现偏差 | 抽 service / repository / policy 层 |
| 前端静态权限与后端动态 API 权限并存 | 菜单、按钮和接口权限可能不同步 | 前端以 `/api/moral/api-permissions/my-permissions` 为准 |
| 驾驶舱指标口径分散 | 不同页面统计可能不一致 | 建立指标字典和缓存策略 |
| 数据库多库并存 | 备份、迁移、事务边界复杂 | 继续保持业务分库，但统一连接、备份和迁移脚本 |

### 4.3 低优先级问题

| 问题 | 影响 | 建议 |
|------|------|------|
| 文档中部分方案稿已落后于代码 | 新人容易误判功能状态 | 将方案稿升级为实现说明或标注“历史方案” |
| 前端页面体量偏大 | 单页维护成本上升 | 对大页面拆分组件和 composable |
| 日志中存在较多宽泛异常捕获 | 故障定位不够清晰 | 给关键路径补 request id、业务上下文和异常分类 |

## 五、优化升级路线图

### 重构总体原则

本项目重构必须坚持以下原则：

1. **功能不回退**：现有页面、API 路径、数据库文件和微信消息能力默认保持兼容。
2. **小步迁移**：每次只迁移一个业务域或一个公共基础设施，迁移后立即跑测试。
3. **先加边界再搬代码**：先建立新目录、新 router、新 service、新 API 客户端，再逐步迁移旧实现。
4. **旧入口薄包装**：短期保留旧 API 路径和前端路由，让旧入口调用新服务，避免一次性改动全链路。
5. **数据库慎动**：SQLite 多库暂不强行合并，只统一路径、连接、备份、迁移和数据访问方式。
6. **测试兜底**：迁移前为核心接口补 characterization tests，确认旧行为，再重构实现。
7. **文档跟随代码**：每完成一个模块迁移，同步更新 `system-architecture.md` 和本文的任务状态。

### 目标目录结构建议

后端建议逐步从 `lesson/models/*` 的混合结构，迁移到“入口、API、业务服务、数据访问、公共基础设施”更清晰的结构。目标结构示例：

```text
lesson/
  app/
    main.py
    api/
      routers/
        auth.py
        teachers.py
        files.py
        dashboard.py
        invigilation.py
        moral/
          admin.py
          daily_records.py
          school_events.py
          tasks.py
          punishments.py
          evaluations.py
          profiles.py
          permissions.py
      deps.py
      schemas/
    services/
      auth_service.py
      teacher_service.py
      schedule_service.py
      homework_service.py
      filegather_service.py
      invigilation/
      moral/
    repositories/
      sqlite/
        teacher_repo.py
        moral_repo.py
        invigilation_repo.py
        homework_repo.py
    core/
      config.py
      logging.py
      security.py
      responses.py
      paths.py
    workers/
      queue_worker.py
      scheduled_tasks.py
    integrations/
      wechat/
      network/
      ai/
  databases/
  scripts/
  tests/
```

迁移过程中可以先不移动所有文件，而是先在现有 `lesson/models/datas_api` 内按相同分层拆出 service 和 repository，等稳定后再做物理目录搬迁。这样更稳，代价小。

前端建议目标结构：

```text
frontend/src/
  app/
    App.vue
    router/
    stores/
  shared/
    api/
      httpClient.js
      modules/
    components/
    composables/
    utils/
  features/
    auth/
    dashboard/
    moral/
      daily-records/
      school-events/
      tasks/
      punishments/
      profiles/
      config/
    invigilation/
    teachers/
    files/
    schedule/
    homework/
  pages/
```

短期不必一次性改成完整 feature-based 结构，可先完成三件事：

- 统一 `httpClient`。
- 大页面拆成局部组件和 composable。
- 新功能全部进入 `features/<domain>`，旧页面逐步迁移。

### 阶段一：重构保护层与安全收口

目标：先让重构有安全网，修复已知失败，消除高风险安全和启动副作用。

建议任务：

1. 为当前核心 API 建立重构保护清单：登录、课表、作业公告、文件、德育日常、评价、教师管理、监考项目。
2. 修复管理员随机密码生成策略。
3. 停止新写入 `raw_pwd`，制定历史明文字段清理脚本。
4. 将 `datas_api_legacy.py` 的导入期课表读取改为懒加载。
5. 修复 `frontend/src/App.vue` CSS 结构问题。
6. 合并前端 API 客户端，统一 token 注入、401 退出、重试、超时和响应解析。
7. 给后端测试配置可写临时目录，避免测试依赖真实用户目录。
8. 调整 `teaching_classes` 数据范围默认语义：未维护映射时不默认全校。

验收标准：

- 后端 `python -m pytest -q` 全部通过。
- 前端 `npm run test:run` 全部通过。
- 登录、德育菜单、日常记录、教师管理、监考安排、文件流转完成手工冒烟。
- 每个准备迁移的业务域至少有接口级测试或手工冒烟脚本。

### 阶段二：后端目录治理与 legacy 拆分

目标：降低 legacy 文件和后端大模块的维护成本，让 API、业务逻辑和数据访问边界更清晰。

建议任务：

1. 将 `datas_api_legacy.py` 拆分为：
   - `schedule.py`
   - `homework.py`
   - `announcement.py`
   - `class_info.py`
   - `leave.py`
   - `member.py`
   - `task_admin.py`
2. 旧 router 只保留路径和请求参数解析，具体业务转交 service。
3. 数据库访问统一走 repository 或连接工具，减少裸 `sqlite3.connect` 和相对路径。
4. 将德育、监考、驾驶舱中可复用的统计、权限、日志、导入导出逻辑抽到 service。
5. 统一响应格式，建议写操作返回 `{ success, message, data }`，查询接口返回 `{ success, data, total? }`。
6. 给脚本类文件增加分类：初始化、迁移、验证、维护，减少业务代码和一次性脚本混放。

验收标准：

- API 路径兼容，不破坏现有前端调用。
- 核心模块有独立测试。
- `datas_api_legacy.py` 不再承担新功能。
- 新业务只允许进入明确业务域目录，不再添加到 legacy 文件。

### 阶段三：前端目录治理与页面瘦身

目标：让页面只负责展示和交互，把 API、状态、权限、表单转换和复杂流程迁出页面文件。

建议任务：

1. 保持 `src/shared/api/httpClient.js` 为唯一 HTTP client，页面通过 `src/api/modules/*` 调用后端。
2. `src/api/modules/*` 统一依赖 `httpClient`，删除硬编码 baseURL。
3. 将 `App.vue` 拆分为：
   - `AppLayout.vue`
   - `TopNavigation.vue`
   - `LoginDialog.vue`
   - `ClassSelector.vue`
   - `useNavigationPermissions.js`
4. 将 `InvigilationArrange.vue` 拆为项目列表、安排表格、导入导出、通知日志、变更预览等组件。
5. 将 `TeacherManage.vue` 拆为教师表格、教师表单、任教班级维护、密码操作。
6. 将德育大页面按列表、筛选、弹窗、批量导入、权限动作拆分。
7. 新增 `features/<domain>` 目录承接新模块，旧页面逐步迁移。

验收标准：

- 单个 Vue 页面原则上控制在 300-500 行以内，复杂页面允许由多个小组件组成。
- API 调用不直接散落在大型页面中，优先由 domain API 模块或 composable 管理。
- 前端测试继续全部通过。

### 阶段四：权限与数据治理

目标：把角色、API 权限、数据范围、审计日志统一成可解释的安全模型。

建议任务：

1. 以 `moral/api_permission.py` 为中心整理 API 权限配置。
2. 为普通教师、班主任、教务、学发、管理员建立权限测试矩阵。
3. 统一前端菜单权限、按钮权限和后端接口权限。
4. 给高风险写操作补齐 `moral_operation_log`。
5. 建立敏感操作清单：密码、教师身份、学生状态、处分、API 权限、批量导入。
6. 补全数据库备份和恢复说明，明确多库备份顺序。

验收标准：

- 关键角色的读写范围有自动化测试。
- API 权限配置页面展示与后端判定一致。
- 敏感操作可审计、可追溯。

### 阶段五：驾驶舱产品化

目标：将现有驾驶舱方案和页面升级为稳定的业务首页。

建议任务：

1. 建立指标字典：指标名称、口径、数据源、权限范围、刷新频率。
2. 德育驾驶舱聚焦低分学生、处分、扣分趋势、任务完成率、画像覆盖率。
3. 教务驾驶舱聚焦课表状态、文件流转、作业公告和教学运行，不展示学生请假数据。
4. 监考驾驶舱聚焦项目状态、未安排、冲突、通知失败、教师工作量。
5. 教师工作台聚焦今日课表、待处理事项、个人记录和通知。
6. 对重统计接口增加轻量缓存或快照表，避免 SQLite 高频全表扫描。

验收标准：

- 不同角色登录后默认看到与自己相关的驾驶舱。
- 指标点击可钻取到业务页面。
- 指标口径在文档中可查。

### 阶段六：运维与交付体验

目标：让系统更容易部署、排障、备份和交接。

建议任务：

1. 整理 `.env` / YAML 配置示例，区分开发、内网生产、HTTPS 代理场景。
2. 补充启动脚本的健康检查和端口冲突提示。
3. 建立数据库备份、恢复、压缩归档和校验流程。
4. 为 Nginx / HTTPS / WebSocket 代理补充常见故障排查。
5. 增加前端构建检查和基础 Playwright 冒烟测试。
6. 将方案稿中已完成内容转为“实现说明”，未完成内容转为路线图。

验收标准：

- 新人可按文档完成本地启动。
- 内网部署文档覆盖前端、后端、HTTPS、WebSocket、静态文件和数据库备份。
- 常见问题有明确排查路径。

## 六、推荐近期任务清单

### 立即处理

- 建立重构保护清单和冒烟测试清单。
- 修复随机密码生成导致的后端测试失败。
- 修复 `App.vue` 样式语法问题。
- 合并前端 API 客户端。
- 消除 legacy 导入期副作用。
- 明确 `raw_pwd` 退场方案。

### 近期处理

- 拆分 `datas_api_legacy.py`。
- 为后端核心模块补 service / repository 边界。
- 拆分 `App.vue`、`InvigilationArrange.vue`、`TeacherManage.vue` 等前端大文件。
- 将监考安排文档从实现方案升级为实际使用说明。
- 将驾驶舱方案升级为指标口径说明。
- 补充权限矩阵测试。
- 补充数据库备份恢复手册。

### 中期处理

- 推进目标目录结构迁移。
- 建立统一响应格式。
- 为德育、监考、文件流转、课表建立端到端冒烟测试。
- 对统计类接口做缓存和性能审查。

## 七、重构迁移顺序建议

为了保证现有功能都能实现，建议按风险从低到高迁移：

| 顺序 | 迁移对象 | 原因 | 保护方式 |
|------|----------|------|----------|
| 1 | 前端 API 客户端 | 影响面明确，收益高 | Vitest + 登录和德育菜单冒烟 |
| 2 | `App.vue` 布局拆分 | UI 结构清晰，业务风险较低 | 页面路由和登录冒烟 |
| 3 | 管理员密码与认证安全 | 当前已有测试失败和安全风险 | 后端 auth/admin 测试 |
| 4 | legacy 导入副作用 | 解决测试和启动不稳定 | pytest 收集阶段验证 |
| 5 | 文件流转模块 | 业务边界相对独立 | 上传、列表、下载、标记完成冒烟 |
| 6 | 监考模块页面拆分 | 页面较大，但业务边界明确 | 项目、安排、导入导出、通知冒烟 |
| 7 | 课表/作业/公告 legacy 拆分 | 历史功能多，需要谨慎 | 保持 API 路径，新增 service 测试 |
| 8 | 德育大模块 service 化 | 功能复杂、权限多 | 权限矩阵 + 记录录入/评价计算测试 |
| 9 | 驾驶舱指标治理 | 依赖前面业务边界稳定 | 指标快照和角色权限测试 |

不建议一开始就做的事：

- 不建议直接改数据库大结构。
- 不建议一次性搬迁整个 `lesson/models`。
- 不建议同时改后端 API 路径和前端调用。
- 不建议在没有测试保护时重写德育评价计算。
- 不建议为了目录好看删除 legacy 兼容入口。

## 八、文档维护规范

1. 新增功能时，同步更新 `system-architecture.md`。
2. 德育规则变化时，同步更新 `moral-evaluation-system.md` 和 `moral-config-guide.md`。
3. 数据库结构或主表策略变化时，同步更新 `database-consolidation-report.md`。
4. 驾驶舱指标变化时，同步更新 `data-dashboard-implementation-plan.md` 或后续的指标说明文档。
5. 部署端口、HTTPS、WebSocket 或反向代理变化时，同步更新 `nginx-https-config.md`。
6. 新增或废弃文档时，同步更新 `docs/README.md`。
7. 文档中使用绝对日期，避免使用无法追溯的相对时间表述。

## 九、结论

当前项目已经形成了较完整的校园综合管理系统雏形：德育评价、监考安排、文件流转、课表作业、教师身份、驾驶舱和微信消息都已有实现基础。项目的主要矛盾已经从“有没有功能”转为“功能边界是否清晰、后续升级是否容易、历史兼容是否继续扩散”。

建议将“阶段一：重构保护层与安全收口”作为 2026-05-02 之后的第一个迭代目标，完成后按“后端 legacy 拆分、前端页面瘦身、权限治理、驾驶舱产品化、运维交付体验”的顺序推进。这样可以在不牺牲现有功能的前提下，把目录整理得更简洁，把代码职责拆得更明确，并为后续系统升级留下稳定扩展点。
