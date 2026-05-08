# 后端与驾驶舱重构轻量记录

> **读取规则**：本文件是精简索引，不是批次流水账。后续 AI 只有在以下场景才需要读取或修改：
> - 用户明确要求查看/更新重构批次记录；
> - 正在交接下一批 batch，需要确认当前主线、红线、验收命令；
> - 修改了后端架构、驾驶舱契约、权限边界、数据库连接、安全策略等会影响后续 batch 的内容。
>
> 日常代码修改、普通 bug 修复、单个页面样式调整，不需要主动读取或追加本文件。禁止把每次测试输出、完整 diff、长篇过程记录继续追加到这里。

## 当前状态（2026-05-07）

- 项目已完成前端 API 聚合、后端 SQLite 连接收口、驾驶舱接口拆分、权限守卫、驾驶舱视觉与状态体验等多轮重构。
- 后端全量测试基线：`python -m pytest lesson/tests -q`，当前最近记录为 `572 passed`。
- 前端测试基线：`npm run test:run`，当前最近记录为 `207 passed`。
- 前端构建基线：`npm run build` 通过；Batch54 已做 manualChunks 分包和 ECharts 按需注册。
- `raw_pwd` 真实数据库清理必须人工确认后才能执行；默认禁止执行 `lesson/scripts/cleanup_raw_pwd.py --apply --yes`。

## 项目红线

- 不修改 `.claude/settings.local.json`、`scripts/unix/start-backend.sh`，除非用户明确要求。
- 不回滚用户或其他 AI 的范围外改动。
- 不执行 destructive git 操作。
- 不执行 `raw_pwd` 真实清理。
- 教务驾驶舱不得展示学生请假名单或学生请假趋势。
- 班级驾驶舱和德育/学发驾驶舱必须保留请假学生相关数据展示。
- 新增或删除驾驶舱字段必须同步契约测试和指标字典。

## 质量门禁

- 文档轻量化只减少流水账，不减少约束、验收和测试要求。
- 每个 batch 必须明确范围、改动文件、验证命令和未覆盖风险。
- 代码改动必须优先保持现有功能、接口路径、权限边界、数据口径不回退。
- 前端改动至少运行 `npm run test:run` 和 `npm run build`。
- 后端改动必须运行 `python -m pytest lesson/tests -q`。
- 驾驶舱字段或权限改动必须同步契约测试和 `docs/data-dashboard-implementation-plan.md`。
- 只允许把批次结果压缩成摘要；详细质量标准应保留在专题文档、契约测试和代码结构中。

## 当前架构要点

### 前端

- 统一 HTTP 客户端：`frontend/src/shared/api/httpClient.js`。
- 兼容入口仅保留：`frontend/src/api/index.js`。旧 `frontend/src/utils/api.js`、`frontend/src/utils/axios.js` 已删除。
- 业务 API 模块集中在 `frontend/src/api/modules/`。
- 驾驶舱状态组件：
  - `frontend/src/components/dashboard/DashboardChart.vue`
  - `frontend/src/components/dashboard/DashboardLoadingState.vue`
  - `frontend/src/components/dashboard/ErrorState.vue`
  - `frontend/src/components/dashboard/ForbiddenState.vue`
- 驾驶舱错误归类工具：`frontend/src/utils/dashboardError.js`。
- 路由权限守卫：`frontend/src/router/guards.js`，并由 `frontend/src/router/index.js` 使用。

### 后端

- 后端代码目录：`lesson/`。
- SQLite 数据库目录：`lesson/databases/`。
- 驾驶舱主入口：`lesson/models/datas_api/dashboard.py`。
- 驾驶舱子模块：
  - `dashboard_common.py`
  - `dashboard_overview.py`
  - `dashboard_moral.py`
  - `dashboard_class.py`
  - `dashboard_teaching.py`
  - `dashboard_invigilation.py`
  - `dashboard_system.py`
  - `dashboard_workbench.py`
  - `dashboard_leave.py`
- legacy datas_api 拆分模块位于 `lesson/models/datas_api/legacy_*.py`。
- SQLite repository/helper 相关代码位于 `lesson/models/datas_api/repositories/` 及 `lesson/utils/`。

## 驾驶舱边界

| 驾驶舱 | 路由 | 角色 | 关键边界 |
|-------|------|------|----------|
| 总览 | `/dashboard` | 已登录用户 | 系统资源概览，不承担具体业务详情 |
| 德育/学发 | `/dashboard/moral` | admin/jiaowu/xuefa/cleader | 可展示请假学生、出勤风险、德育趋势 |
| 班级 | `/dashboard/class` | admin/jiaowu/xuefa/cleader | 可展示本班请假学生和班级运行态势 |
| 教务 | `/dashboard/teaching` | admin/jiaowu | 展示课表、课时、文件上传，不展示请假学生 |
| 监考 | `/dashboard/invigilation` | admin/jiaowu | 展示监考项目、通知、教师监考负载 |
| 系统 | `/dashboard/system` | admin | 展示用户、权限、数据库、操作统计 |
| 教师工作台 | `/dashboard/teacher` | teacher 及登录用户 | 展示教师个人课表、监考、文件、工作量 |

## 关键批次摘要

| 阶段 | 摘要 |
|------|------|
| Batch 4-15 | 处理导入副作用、密码函数、安全随机密码、SQLite 连接迁移基础设施。 |
| Batch 16-30 | 拆分 datas_api legacy 模块，建立契约测试，逐步迁移重复函数和连接逻辑。 |
| Batch 31-45 | 深入清理后端模块边界、权限与安全工具，整理 raw_pwd 审计/清理机制。 |
| Batch 46-48 | 完成驾驶舱整体规划与请假数据边界：班级/德育保留请假，教务禁止请假展示。 |
| Batch 49 | 增加前端驾驶舱路由权限守卫、默认入口、无权限状态页。 |
| Batch 50 | 固化驾驶舱指标字典，清理重复字段，统一 cards/charts/tables/insights。 |
| Batch 51 | 增加 DashboardChart 空状态、ErrorState、ForbiddenState、统一 dashboardError。 |
| Batch 52 | 完成驾驶舱视觉验收收口，修正教师工作台路径和 insights 可点击状态。 |
| Batch 53 | 增加 DashboardLoadingState 骨架屏和 ErrorState 重试防刷。 |
| Batch 54 | 前端 Vite manualChunks 分包；ECharts 改为按需注册，图表 chunk 约 1036KB 降至约 520KB。 |
| Batch 55 | 图表运行时回归验收通过；驾驶舱专项验收结束，后续回归模块化和代码瘦身主线。 |
| Batch 56 | 删除前端旧 HTTP 兼容入口 `utils/api.js`、`utils/axios.js`；页面层统一通过业务 API 模块访问后端。 |

## 最近验收基线

```bash
cd frontend
npm run test:run
npm run build

cd ..
python -m pytest lesson/tests -q
```

最近记录：

- `npm run test:run`：207 passed。
- `npm run build`：通过；前端 vendor 已分包，构建无大 chunk 警告。
- `python -m pytest lesson/tests -q`：572 passed。

## 相关文档

- 总体升级方案：`docs/project-optimization-upgrade-plan.md`
- 函数级审计：`docs/function-level-audit-and-refactor-plan.md`
- AI 执行手册：`docs/ai-refactor-execution-playbook.md`
- 驾驶舱规划：`docs/data-dashboard-implementation-plan.md`
- 驾驶舱重构方案：`docs/dashboard-refactor-plan.md`
- raw_pwd 操作手册：`docs/raw-pwd-cleanup-runbook.md`
- 最终交接：`docs/legacy-refactor-final-handoff.md`

## 维护规则

- 本文件只记录“当前状态、红线、主线摘要、下一步”，不记录完整过程。
- 新增 batch 只允许追加 3-8 行摘要和最新验收基线。
- 详细接口字段写入指标字典，不写在本文件。
- 详细执行步骤写入对应 runbook/playbook，不写在本文件。
- 如果本文件超过约 250 行，应再次压缩。
