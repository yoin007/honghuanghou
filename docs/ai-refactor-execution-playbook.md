# AI 重构执行手册

## 版本信息

- 生成日期：2026-05-02
- 适用项目：红皇后 / 数字天龙校园综合管理系统
- 面向对象：后续执行重构的 AI 工具、接手开发者、代码复核者
- 目标：让其他 AI 可以按明确批次执行升级优化，完成后由 Codex 按统一标准复核

## 一、当前方案复核结论

### 1.1 是否实现模块化

当前升级方案已经明确模块化目标，但代码尚未实现该目标。执行时必须把“目标模块化”落实为以下结构：

| 层级 | 后端职责 | 前端职责 |
|------|----------|----------|
| Router / Page | 接收请求、参数校验、调用服务、返回响应 | 页面展示、用户交互、组件编排 |
| Service / Composable | 业务规则、流程编排、权限后置校验、跨表事务 | 页面状态、业务动作、表单流程、权限动作 |
| Repository / API Module | SQLite 查询、文件读写、外部 API 封装 | HTTP 请求、WebSocket 请求、下载上传封装 |
| Core / Shared | 配置、日志、安全、响应格式、路径、错误处理 | HTTP client、通用组件、工具函数、错误处理 |
| Integration / Workers | 微信、网络设备、AI、定时任务、发送队列 | 浏览器能力、导入导出、图表适配 |

判定标准：

- 路由函数不再直接拼复杂 SQL，不直接实现长业务流程。
- 页面不再直接散落大量 API 调用和导入导出逻辑。
- 同一数据表只通过一个 repository 或兼容仓储访问。
- 同一业务规则只在一个 service / policy 中实现。

### 1.2 目录结构是否清晰

目标目录清晰，但迁移必须分阶段，不允许一次性搬迁全项目。

后端第一阶段允许在现有结构内新增：

```text
lesson/models/datas_api/services/
lesson/models/datas_api/repositories/
lesson/models/datas_api/schemas/
lesson/models/datas_api/policies/
```

后端稳定后再迁移到：

```text
lesson/app/api/routers/
lesson/app/services/
lesson/app/repositories/
lesson/app/core/
lesson/app/integrations/
lesson/app/workers/
```

前端第一阶段允许新增：

```text
frontend/src/shared/api/
frontend/src/shared/components/
frontend/src/shared/composables/
frontend/src/features/
```

长期目标：

```text
frontend/src/app/
frontend/src/shared/
frontend/src/features/
frontend/src/pages/
```

### 1.3 功能相同但名称不同的函数是否合并

当前方案提出了合并方向，但执行时还需要严格合并规则。不能仅凭名称相同或相近合并。

必须合并的典型类型：

| 重复类型 | 示例 | 合并目标 |
|------|------|----------|
| 前端 HTTP client 重复 | 旧 `src/utils/api.js`、`src/utils/axios.js` 已删除，`src/api/index.js` 为聚合入口 | `src/shared/api/httpClient.js` |
| 前端角色/权限判断重复 | `stores/auth.js`、`usePermission.js`、菜单权限判断 | `stores/auth.js` + `stores/apiPermission.js` + `useNavigationPermissions.js` |
| 前端 CRUD 事件函数重复 | 多页面 `handleAdd`、`handleEdit`、`handleDelete`、`handleSubmit` | 可抽 `useCrudDialog`，但保留页面语义包装 |
| 后端认证函数重复 | `datas_api/auth.py` 与 `datas_api_legacy.py` 中的密码/JWT函数 | 只保留 `datas_api/auth.py` 或 `core/security.py` |
| 数据库访问类重复 | `mysql_db.py`、`sqlite_moral_db.py`、`teacher_db.py` 中相似 query 方法 | 统一接口协议，按数据库类型保留实现 |
| 德育 scoped permission helper 重复 | `_has_scoped_permission`、`_has_scoped_any_permission` 多文件重复 | `moral/policies.py` |
| 课表查询重复 | legacy、`Lesson`、`ScheduleService` 中班级/教师课表函数 | `schedule_service.py` |
| 日期/状态格式化重复 | 多个 Vue 页面 `formatDate`、`getStatusType` | `shared/utils` 或 domain constants |

不能盲目合并的类型：

| 类型 | 原因 | 处理方式 |
|------|------|----------|
| 同名但业务域不同 | 如多个 `handleSubmit` 提交不同表单 | 可抽通用 hook，但页面保留语义函数 |
| 快照字段与主表字段 | 如监考 `teacher_name` 快照与 `teacher` 主表 | 不能合并为实时关联 |
| 旧 daily 与德育 daily | 字段语义和评分规则不同 | 建历史导入服务，不能直接并表 |
| 微信触发函数和 Web API 函数 | 入口、权限、响应方式不同 | 共享 service，入口分离 |
| 测试 mock 函数 | 服务于测试隔离 | 可统一测试工厂，但不影响业务代码 |

### 1.4 代码级实现目标

本手册不是只描述“理想结构”，执行 AI 必须在代码层面逐步实现以下目标：

| 目标 | 代码级完成标志 |
|------|----------------|
| 模块化 | 新增或迁移的业务逻辑进入 `services` / `repositories` / `policies` / `features`，旧 router/page 只做薄入口 |
| 目录清晰 | 新增文件名能表达业务域和层级，例如 `schedule_service.py`、`teacher_repo.py`、`useNavigationPermissions.js` |
| 重复函数合并 | 重复实现减少，旧函数保留 wrapper 或 alias，内部调用统一实现 |
| 功能兼容 | 旧 API 路径、前端路由、微信触发函数名和数据库文件保持可用 |
| 可复核 | 每批改动能通过函数清单、测试和冒烟步骤验证 |

### 1.5 首批必须创建的基础文件

其他 AI 在开始大规模迁移前，先创建这些“承接点”，避免继续把代码塞回旧文件：

后端：

```text
lesson/models/datas_api/services/__init__.py
lesson/models/datas_api/repositories/__init__.py
lesson/models/datas_api/policies/__init__.py
lesson/models/datas_api/schemas/__init__.py
lesson/models/datas_api/services/auth_service.py
lesson/models/datas_api/services/schedule_service.py
lesson/models/datas_api/services/homework_service.py
lesson/models/datas_api/services/filegather_service.py
lesson/models/datas_api/repositories/teacher_repo.py
lesson/models/datas_api/policies/moral_policy.py
```

前端：

```text
frontend/src/shared/api/httpClient.js
frontend/src/shared/api/modules/
frontend/src/shared/composables/useCrudDialog.js
frontend/src/shared/composables/useConfirmAction.js
frontend/src/shared/utils/date.js
frontend/src/shared/utils/status.js
frontend/src/features/navigation/useNavigationPermissions.js
```

注意：创建承接点不等于立刻搬空旧文件。每个旧函数迁移后，旧位置先保留兼容 wrapper。

### 1.6 wrapper 模式规范

后端旧函数迁移示例：

```python
# old router / legacy file
@router.get("/schedule/{class_name}")
async def get_class_schedule(class_name: str):
    return schedule_service.get_class_schedule(class_name)
```

前端旧 API 迁移示例：

```js
// old module keeps public name
import { httpClient } from '@/shared/api/httpClient'

export function getDailyRecords(params = {}) {
  return httpClient.get('/api/moral/daily-records', { params })
}
```

wrapper 要求：

- wrapper 不再包含复杂 SQL、复杂业务判断或重复数据转换。
- wrapper 保留旧函数名和旧路径，便于调用方无感迁移。
- wrapper 内部只做参数适配、调用新 service、返回结果。
- 删除 wrapper 前必须完成全仓引用搜索和版本迁移说明。

## 二、其他 AI 执行规则

### 2.1 总规则

1. 不允许删除功能，除非在文档中列为废弃候选并通过引用搜索确认无调用。
2. 不允许一次性重写大模块。
3. 不允许同时改后端 API 路径和前端调用路径。
4. 不允许直接改数据库大结构，除非先提供迁移脚本、备份方案和回滚方案。
5. 每个批次只处理一个明确主题。
6. 每个批次完成后必须更新相关文档和函数清单。
7. 每个批次必须运行测试或说明不能运行的原因。
8. 保留旧入口兼容，新入口稳定后再考虑迁移前端调用。

### 2.2 每个批次必须交付

每个 AI 执行批次必须提交以下内容：

```text
1. 改动范围
2. 涉及功能清单项
3. 新增/迁移/合并/保留/废弃候选函数列表
4. 兼容性说明
5. 测试命令和结果
6. 手工冒烟步骤
7. 回滚建议
8. 未完成事项
```

### 2.3 禁止行为

- 禁止为了目录好看移动所有文件。
- 禁止把多个业务域混进一个新 service。
- 禁止把前端所有 API 再合成一个巨大的 `api.js`。
- 禁止删除 `datas_api_legacy.py` 路由兼容入口。
- 禁止把 `raw_pwd` 清理和认证逻辑重构与大型目录迁移混在同一个批次。
- 禁止在未确认微信规则引用时删除 `models.*` 中的异步触发函数。

## 三、执行批次

### Batch 0：建立执行基线

目标：确认当前状态，建立后续对比基线。

执行步骤：

1. 运行：`git status --short`。
2. 运行：`npm run test:run`，工作目录 `frontend`。
3. 运行：`python -m pytest -q`，工作目录 `lesson`。
4. 如后端测试因已知随机密码失败失败，记录失败用例。
5. 保存当前 API 路由清单：`rg "@router\.|@app\." lesson/main.py lesson/models`。
6. 保存当前函数清单或复用 `docs/function-inventory.md`。

交付物：

- 测试基线记录。
- 当前失败项列表。
- 不修改业务代码。

### Batch 1：统一前端 HTTP 客户端

目标：消除前端 API 封装缝合点。

范围：

- `frontend/src/shared/api/httpClient.js`
- `frontend/src/api/index.js`
- `frontend/src/api/modules/*`
- `frontend/src/stores/auth.js`

执行要求：

1. 新建 `frontend/src/shared/api/httpClient.js`。
2. 统一 baseURL 逻辑、timeout、Content-Type、Authorization、401 处理、错误提示、重试策略。
3. 让所有 API module 依赖同一个 httpClient。
4. 禁止恢复 `src/utils/api.js`、`src/utils/axios.js` 这类旧兼容入口。
5. 不改变 API 路径。

代码级步骤：

1. 搜索引用：`rg "utils/axios|utils/api|api/index|axios.create|localhost:8000" frontend/src`。
2. 确认重试、错误处理逻辑只在 `shared/api/httpClient.js` 维护。
3. 在 `shared/api/httpClient.js` 导出命名导出和默认导出，减少迁移摩擦。
4. 将 `stores/auth.js` 的登录请求改为使用同一 httpClient，并统一设置 Authorization。
5. 将 `api/modules/*` 中的 `api` import 改为 `httpClient`。
6. 页面/组件/store 不直接导入 `shared/api/httpClient.js`，应通过 `api/modules/*` 业务模块。
7. 若新增业务 API，先放入 `api/modules/*`，再由页面调用。

代码级完成标志：

- `rg "axios.create" frontend/src` 只剩 `shared/api/httpClient.js` 一个结果。
- `rg "localhost:8000" frontend/src` 无结果。
- `src/api/index.js` 不再创建 axios 实例，只负责聚合导出。

验收命令：

```bash
cd frontend
npm run test:run
npm run build
```

冒烟：

- 登录成功。
- 登录后菜单权限正常。
- 德育任一列表可加载。
- 文件列表可加载。

### Batch 2：修复认证安全与密码策略

目标：修复测试失败，停止新增明文密码风险。

范围：

- `lesson/models/datas_api/auth.py`
- `lesson/models/datas_api/admin.py`
- `lesson/models/datas_api/teachers.py`
- `lesson/utils/teacher_db.py`
- 相关测试

执行要求：

1. 随机密码使用 `secrets`，确保至少包含字母和数字。
2. 新重置/设置密码不再写入明文 `raw_pwd`。
3. 历史 `raw_pwd` 保留只读兼容，但新增路径不写。
4. 保留旧用户登录兼容策略，另建迁移计划逐步关闭明文验证。
5. 修复测试中对随机密码的断言。

代码级步骤：

1. 在 `auth.py` 或新 `services/auth_service.py` 中新增 `generate_temporary_password(length=10)`。
2. 使用 `secrets.choice`，保证至少 1 个字母、1 个数字；如允许符号，需确认前端和用户输入兼容。
3. `admin_reset_password` 返回临时密码，但数据库只保存 bcrypt hash。
4. `admin_set_password` 和 `teacher_change_password` 不再传 `raw_pwd`。
5. `teacher_db.update_teacher_record` 对 `raw_pwd=None` 不更新该字段，避免误清历史数据。
6. 单独新增历史 `raw_pwd` 清理脚本文档，不在本批次批量清库。

代码级完成标志：

- `rg "raw_pwd=.*new_password|raw_pwd=new_password|raw_pwd=str\\(request.new_password\\)" lesson/models lesson/utils` 无新增写入路径。
- `admin.py` 不再使用 `random.choices` 生成密码。
- 明文兼容只存在于历史登录验证路径，且文档标注退场计划。

验收命令：

```bash
cd lesson
python -m pytest tests/test_auth.py tests/test_api.py -q
python -m pytest -q
```

冒烟：

- 管理员登录。
- 管理员重置普通教师密码。
- 普通教师用新密码登录。
- 普通教师修改密码。

### Batch 3：消除 legacy 导入副作用

目标：让导入 API 模块不再读课表、创建外部目录或触发缓存初始化。

范围：

- `lesson/models/datas_api_legacy.py`
- `lesson/models/datas_api/__init__.py`
- 课表相关 service / utils

执行要求：

1. 删除或替换模块级 `SCHEDULE_DATA = get_schedule_data()`。
2. 改为函数内懒加载或 FastAPI lifespan 显式初始化。
3. 测试环境不得写入用户真实 `lesson_dir`。
4. 保持 `/api/schedule/*`、`/api/todays`、`/api/current-classes` 等旧路由可用。

代码级步骤：

1. 搜索模块级执行：`rg "^[A-Z_]+\\s*=\\s*get_|Lesson\\(\\)|create_.*dir" lesson/models/datas_api_legacy.py lesson/models/datas_api`。
2. 将 `SCHEDULE_DATA` 改为函数内缓存，例如 `get_schedule_data_cached()`。
3. 缓存函数不得在 import 阶段创建目录。
4. 测试环境通过环境变量或 monkeypatch 使用临时 lesson 目录。
5. 如需启动预热，放入 `lifespan`，并捕获失败为 warning，不阻塞测试收集。

代码级完成标志：

- `python - <<'PY'\nimport models.datas_api\nprint('ok')\nPY` 在 `lesson` 目录下不会创建用户真实课表目录。
- `rg "SCHEDULE_DATA = get_schedule_data" lesson/models/datas_api_legacy.py` 无结果。

验收命令：

```bash
cd lesson
python -m pytest tests/test_moral_data_scope.py -q
python -m pytest -q
```

冒烟：

- 打开总课表。
- 打开班级课表。
- 打开实时课程。

### Batch 4：拆分 App.vue 与导航权限

目标：前端入口不再同时承载布局、登录、权限、导航、班级选择。

范围：

- `frontend/src/App.vue`
- 新增 layout/components/composables
- `stores/auth.js`
- `stores/apiPermission.js`

执行要求：

1. 拆出 `AppLayout.vue`、`TopNavigation.vue`、`LoginDialog.vue`、`ClassSelector.vue`。
2. 拆出 `useNavigationPermissions.js`。
3. 保持现有视觉和路由行为。
4. 修复 CSS 括号异常。
5. 不改业务页面。

代码级步骤：

1. 将登录弹窗 template 和 `handleLogin` 迁到 `features/auth/LoginDialog.vue` 或 `shared/components/LoginDialog.vue`。
2. 将菜单 template 和 `handleSelect` 迁到 `features/navigation/TopNavigation.vue`。
3. 将 `loadMoralMenuPermissions` 迁到 `features/navigation/useNavigationPermissions.js`。
4. 将班级选择迁到 `features/classes/ClassSelector.vue`。
5. `App.vue` 只保留布局、store 初始化和 router-view。
6. 修复 scoped CSS 中错位的 `font-weight: 500` 和多余 `}`。

代码级完成标志：

- `App.vue` 中不再直接包含完整德育菜单权限细节。
- `App.vue` 行数明显下降。
- `rg "loadMoralMenuPermissions" frontend/src` 指向 navigation composable。

验收命令：

```bash
cd frontend
npm run test:run
npm run build
```

冒烟：

- 未登录可看到登录入口。
- 登录后用户名、班级选择、菜单可见性正常。
- 点击每个一级菜单能跳转。
- `/loud-pk` HTTPS 协议逻辑不回退。

### Batch 5：建立后端 service/repository 基础目录

目标：先加边界，不大规模搬代码。

范围：

```text
lesson/models/datas_api/services/
lesson/models/datas_api/repositories/
lesson/models/datas_api/policies/
lesson/models/datas_api/schemas/
```

执行要求：

1. 新目录只承接新迁移逻辑。
2. 先迁移无争议公共逻辑：响应、权限 helper、数据库连接 helper。
3. 旧 router 调用新 service。
4. 不移动 `main.py`。
5. 不改 API 路径。

验收：

- 现有测试全部通过。
- 新目录中每个文件职责单一。
- 无循环导入。

代码级完成标志：

- `lesson/models/datas_api/services` 中不出现 FastAPI `@router` 装饰器。
- `lesson/models/datas_api/repositories` 中不依赖 FastAPI `Request` 或 `Depends`。
- router 文件可以 import service，service 不 import router。
- repository 只处理数据访问，不拼接 HTTP 响应。

### Batch 6：按功能组拆分 datas_api_legacy.py

目标：把 legacy 文件从业务实现文件降级为兼容聚合入口。

执行顺序：

1. schedule：班级代码、班级课表、今日课表、实时课程、教师课表。
2. homework：作业查询、发布、更新、删除。
3. announcement：公告查询、发布、更新、删除。
4. classes：班级信息、学生列表、导入导出。
5. leave：延时申请、请假记录、核销。
6. wechat_admin：会员和微信权限。
7. task_admin：任务管理。

每个子批次要求：

- 先复制到 service，旧函数调用 service。
- 增加或调整测试。
- 运行相关冒烟。
- 一次只迁一个功能组。

验收：

- `datas_api_legacy.py` 行数逐步下降。
- 旧路由路径全部保留。
- 功能清单对应项全部通过。

代码级步骤：

1. 为每个功能组建立 service 文件，不先移动路由。
2. 将纯业务函数迁出，保留 route handler。
3. route handler 保留原函数名，但内部调用 service。
4. 每迁完一个功能组，运行相关前端页面冒烟。
5. 迁移后在 `datas_api_legacy.py` 顶部写明“兼容入口，不再新增业务实现”。

代码级完成标志：

- legacy 文件中新增业务逻辑行数不再增长。
- 旧路由装饰器仍能被 `rg "@router\\." lesson/models/datas_api_legacy.py` 找到。
- 已迁移函数体不再包含复杂 SQL 或 Excel 解析。

### Batch 7：德育 service 化和重复权限函数合并

目标：保留德育功能，统一权限、范围、审计、计算。

执行顺序：

1. 合并 `_has_scoped_permission`、`_has_scoped_any_permission` 到统一 policy。
2. 拆 `base.py`：roles、permissions、scope、semester、audit。
3. 拆 daily/school event 的事件类型公共逻辑。
4. 拆 evaluation engine。
5. 拆 import service。
6. 拆 profile generation service。

验收：

```bash
cd lesson
python -m pytest tests/test_moral_api.py tests/test_moral_data_scope.py tests/test_permission.py -q
```

冒烟：

- 日常记录 CRUD。
- 校级事件 CRUD。
- 学生管理。
- 班主任只看本班。
- 教师只看授权范围。
- 德育评价计算。

代码级步骤：

1. 先迁 policy helper，不动业务路由。
2. 将多文件 `_has_scoped_permission` 改为 import 统一实现。
3. 提取 `get_record_data_scope` 相关逻辑时保持原函数名 re-export，避免大范围修改。
4. 评价计算先加 `evaluation_engine.py`，旧 `evaluation.py` 路由调用 engine。
5. 批量导入逻辑单独放 import service，不和 CRUD 混在一个函数里。

代码级完成标志：

- `rg "def _has_scoped_permission" lesson/models/datas_api/moral` 只剩一个定义或全改为统一 import。
- `evaluation.py` 中计算逻辑明显减少，核心算法进入 engine/service。
- 德育路由函数不直接实现大段权限矩阵判断。

### Batch 8：监考模块拆分

目标：把 `invigilation.py` 从单文件大模块拆成服务。

服务划分：

- `project_service.py`
- `slot_service.py`
- `change_service.py`
- `notification_service.py`
- `import_export_service.py`
- `report_service.py`
- `invigilation_repo.py`

验收：

- 项目 CRUD。
- 批量保存安排。
- 交换教师。
- 变更预览。
- 通知日志。
- 模板下载。
- Excel 导入。
- 导出安排。
- 工作量报表。

代码级步骤：

1. 先建立 `repositories/invigilation_repo.py`，集中 `exam_project`、`slot`、`version`、`notification_log` 查询。
2. 将 Excel 导入导出函数迁入 `import_export_service.py`。
3. 将通知消息生成和发送迁入 `notification_service.py`。
4. 将变更比较迁入 `change_service.py`。
5. 路由函数保留原路径和 response 类型。

代码级完成标志：

- `invigilation.py` 不再直接包含大段 Excel 解析、通知消息构造和报表统计。
- 查询 SQL 集中在 repository。
- 通知发送失败处理和日志写入集中在 notification service。

### Batch 9：驾驶舱指标服务化

目标：把统计口径放回业务域，dashboard 只做编排。

要求：

1. 建立指标字典文档。
2. 每个 dashboard endpoint 调用对应业务 statistics service。
3. 避免重复 SQL 和重复权限判断。
4. 对慢查询增加缓存或快照策略。

验收：

- `/api/dashboard/overview`
- `/api/dashboard/moral/summary`
- `/api/dashboard/teaching/summary`
- `/api/dashboard/class/summary`
- `/api/dashboard/teacher/workbench`
- `/api/dashboard/invigilation/summary`
- `/api/dashboard/system/summary`

代码级完成标志：

- `dashboard.py` 中 endpoint 函数只做参数解析、权限判断和调用统计 service。
- 每个指标 service 文件有明确业务域名称。
- 指标口径文档能对应到 service 函数。

### Batch 10：前端大页面瘦身

执行顺序：

1. `TeacherManage.vue`
2. `InvigilationArrange.vue`
3. `moral/config/ApiPermission.vue`
4. `moral/config/EventTypeManage.vue`
5. `moral/config/StudentManage.vue`
6. `moral/DailyRecord.vue`、`SchoolEvent.vue`、`Punishment.vue`、`TaskManage.vue`

要求：

- 页面保留路由入口。
- 子组件放在 feature 目录。
- API 调用进 composable 或 API module。
- 通用导入导出逻辑抽 shared utility。

验收：

```bash
cd frontend
npm run test:run
npm run build
```

代码级完成标志：

- 页面文件中不再出现大段 API URL 字符串。
- 页面文件中导入业务 composable，例如 `useTeacherManage`、`useInvigilationProject`。
- 每个拆出的组件 props/events 明确，不直接访问 unrelated store。

## 四、同义/重复函数合并规则

### 4.1 合并前检查清单

合并任意两个函数前，必须确认：

1. 输入参数语义一致或可通过 adapter 统一。
2. 返回结构一致或调用方可兼容。
3. 权限要求一致。
4. 数据范围一致。
5. 数据库副作用一致。
6. 错误处理一致。
7. 日志和审计要求一致。
8. 前端展示需求一致。
9. 测试覆盖合并前后行为。

### 4.2 合并方式

| 情况 | 处理方式 |
|------|----------|
| 完全重复 | 删除一个，保留统一实现，旧名字作为别名或 wrapper |
| 业务相同但参数不同 | 建统一 service，旧函数做参数适配 |
| 名字相同但业务不同 | 不合并，只重命名为更明确名称 |
| 公共 UI 操作相似 | 抽 composable，页面保留业务命名函数 |
| 数据访问模式相同 | 抽 repository 基类或协议，不强行合并不同数据库类 |

### 4.3 优先合并清单

| 优先级 | 合并对象 | 目标 |
|------|----------|------|
| P0 | 前端三个 axios/http client | `shared/api/httpClient.js` |
| P0 | auth 与 legacy 中重复密码/JWT函数 | `auth.py` 或 `core/security.py` |
| P1 | 多个 `_has_scoped_permission` helper | `moral/policies.py` |
| P1 | `ScheduleService`、`Lesson`、legacy 中课表查询重复 | `services/schedule_service.py` |
| P1 | 多页面 class/student/grade list 加载逻辑 | `features/moral/shared/useMoralLookups.js` |
| P2 | 多页面导入/导出 CSV/XLSX | `shared/utils/importExport.js` |
| P2 | 多页面 CRUD dialog 状态 | `shared/composables/useCrudDialog.js` |
| P2 | dashboard 页面 `fetchSummary`、`go`、`isEmpty` | `features/dashboard/useDashboardPage.js` |

## 五、其他 AI 完成后的 Codex 复核流程

### 5.1 复核输入要求

执行 AI 完成后，必须提供：

1. 改动摘要。
2. 改动文件列表。
3. 影响功能清单项。
4. 测试命令与输出。
5. 未完成事项。
6. 是否改动数据库 schema。
7. 是否改动 API 路径。
8. 是否删除函数或文件。

### 5.2 Codex 复核步骤

Codex 复核时按以下顺序执行：

1. `git status --short` 查看变更范围。
2. `git diff --stat` 看体量。
3. 对照 `function-inventory.md` 检查删除/迁移函数是否有说明。
4. 对照“不能遗漏的功能清单”确认影响面。
5. 搜索旧入口是否保留：路由路径、前端路由、微信函数名。
6. 搜索重复实现是否真的减少，而不是换地方复制。
7. 运行前端测试：`npm run test:run`。
8. 运行前端构建：`npm run build`。
9. 运行后端测试：`python -m pytest -q`。
10. 对安全点做专项检查：密码、raw_pwd、JWT、权限范围、文件下载路径。
11. 对数据点做专项检查：SQLite 路径、迁移脚本、备份、WAL 设置。
12. 对 UI 做抽样检查：登录、导航、德育、监考、文件。
13. 输出 review findings，按严重程度排序。

### 5.3 Codex 复核判定标准

| 结果 | 条件 |
|------|------|
| 通过 | 测试通过，旧功能保留，结构更清晰，无新增高风险 |
| 有条件通过 | 存在轻微文档或测试缺口，但主功能可用 |
| 退回修改 | API 路径破坏、权限回退、数据风险、测试大面积失败、功能遗漏 |
| 禁止合并 | 删除未确认功能、数据库不可逆改动、明文密码扩大、越权访问 |

## 六、文档更新要求

每个执行批次完成后必须更新对应的专题文档；`docs/backend-refactor-notes.md` 只作为轻量索引，只有变更主线、红线、验收基线或下一阶段计划时才更新，不写入完整过程日志。

| 情况 | 必改文档 |
|------|----------|
| 迁移函数或拆模块 | `function-inventory.md`、本手册对应批次状态 |
| 改 API 路由 | `system-architecture.md` |
| 改德育规则 | `moral-evaluation-system.md`、`moral-config-guide.md` |
| 改数据库 | `database-consolidation-report.md` |
| 改部署/端口/HTTPS | `nginx-https-config.md` |
| 改驾驶舱指标 | `data-dashboard-implementation-plan.md` 或新增指标字典 |

## 七、最终完成定义

整个重构优化项目完成时，必须满足：

1. 前端和后端测试全部通过。
2. 旧 API 路径和前端路由兼容。
3. `datas_api_legacy.py` 不再承载多业务实现，只作为兼容入口或被明确归档。
4. 前端只有一个 HTTP client。
5. 德育权限和数据范围有测试覆盖。
6. 监考、驾驶舱、文件流转、课表有独立 service 或 composable 边界。
7. 大页面明显瘦身。
8. 重复函数按规则合并或保留 wrapper。
9. 文档和函数清单更新。
10. 新人可以按 README 阅读顺序理解系统。
