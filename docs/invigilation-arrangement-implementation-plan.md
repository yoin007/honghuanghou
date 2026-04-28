# 监考安排功能实现方案

## 目标

在顶部导航栏“教务”菜单下新增“监考安排”子栏目，用于创建、导入、编辑、导出和通知考试监考安排。系统需要支持一次考试覆盖一个或多个年级，并按年级维护该次考试下的日期、时间、学科、考场、监考老师等安排。所有历史考试项目保留记录。

本方案只设计实现路径，不直接包含代码实现。

## 现有项目接入点

前端入口：

- 顶部导航：`frontend/src/App.vue`
- 路由：`frontend/src/router/index.js`
- API 封装习惯：`frontend/src/api/modules/*.js`
- 现有教务页面：`frontend/src/views/AdminFiles.vue`、`frontend/src/views/UploadSchedule.vue`

后端入口：

- API 聚合：`lesson/models/datas_api/__init__.py`
- 认证用户：`lesson/models/datas_api/auth.py`
- SQLite 路径配置：`lesson/utils/db_config.py`
- 教师数据：`lesson/utils/teacher_db.py`、`lesson/databases/auth.db`、`lesson/databases/moral.db`
- 通知函数：`lesson/sendqueue.py` 中的 `send_text`

建议新增模块：

- 后端：`lesson/models/datas_api/invigilation.py`
- 数据库初始化/迁移：可扩展 `lesson/scripts/init_databases.py` 或新增 `lesson/scripts/create_invigilation_tables.py`
- 前端页面：`frontend/src/views/InvigilationArrange.vue`
- 前端 API：`frontend/src/api/modules/invigilation.js`

## 权限与导航

### 访问权限

建议仅允许以下角色访问：

- `admin`
- `jiaowu`

若后续需要让年级负责人查看，可再扩展 `teacher/cleader` 的只读权限。

### 前端导航

在 `frontend/src/App.vue` 的“教务”菜单中新增：

```vue
<el-menu-item index="/invigilation">监考安排</el-menu-item>
```

该菜单沿用现有 `isJiaowu` 控制即可。

### 路由

在 `frontend/src/router/index.js` 新增：

```js
{
  path: '/invigilation',
  name: 'InvigilationArrange',
  component: () => import('../views/InvigilationArrange.vue'),
  meta: {
    requiresAuth: true,
    requiresJiaowu: true,
    title: '监考安排'
  }
}
```

## 数据模型设计

建议使用独立 SQLite 数据库 `lesson/databases/invigilation.db`，避免与德育业务耦合。

### 1. 考试项目表 `exam_project`

用于保存一次考试项目。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 项目 ID |
| name | TEXT NOT NULL | 考试名称，如“2026 春季期中考试” |
| school_year | TEXT | 学年，如 `2025-2026` |
| semester | TEXT | 学期，如 `下学期` |
| start_date | TEXT | 考试开始日期 |
| end_date | TEXT | 考试结束日期 |
| grade_ids | TEXT | JSON 数组，如 `[1,2,3]` |
| status | TEXT | `draft/saved/notified/archived` |
| first_saved_at | TEXT | 第一次保存时间 |
| notified_at | TEXT | 最近一次通知时间 |
| created_by | TEXT | 创建人 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 2. 项目年级表 `exam_project_grade`

用于明确一次考试包含哪些年级，便于按年级展示。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | ID |
| project_id | INTEGER | 考试项目 ID |
| grade_id | INTEGER | 年级 ID |
| grade_name | TEXT | 年级名称快照 |
| sort_order | INTEGER | 展示排序 |

### 3. 监考安排表 `invigilation_slot`

一行代表一个考场的一场考试安排。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 安排 ID |
| project_id | INTEGER | 考试项目 ID |
| grade_id | INTEGER | 年级 ID |
| exam_date | TEXT NOT NULL | 日期，格式 `YYYY-MM-DD` |
| start_time | TEXT NOT NULL | 开始时间，格式 `HH:mm` |
| end_time | TEXT NOT NULL | 结束时间，格式 `HH:mm` |
| subject | TEXT NOT NULL | 学科 |
| room_name | TEXT NOT NULL | 考场名称 |
| room_order | INTEGER | 考场排序 |
| teacher_id | INTEGER | 教师 ID，可为空 |
| teacher_name | TEXT | 教师姓名快照 |
| teacher_contact | TEXT | 通知接收人 wxid 或可发送标识 |
| source | TEXT | `manual/import` |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

建议对 `(project_id, grade_id, exam_date, start_time, room_name)` 建唯一索引，避免同一考试场次重复导入。

### 4. 安排版本表 `invigilation_version`

用于保存每次保存的版本，支持计算“本次变更了哪些老师”。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 版本 ID |
| project_id | INTEGER | 考试项目 ID |
| version_no | INTEGER | 版本号 |
| action | TEXT | `first_save/import/edit/swap` |
| snapshot_json | TEXT | 当前安排快照 JSON |
| change_summary | TEXT | 变更摘要 JSON |
| saved_by | TEXT | 保存人 |
| saved_at | TEXT | 保存时间 |
| notification_sent | INTEGER | 是否已通知 |

### 5. 通知日志表 `invigilation_notification_log`

用于审计每次发送。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | ID |
| project_id | INTEGER | 考试项目 ID |
| version_id | INTEGER | 版本 ID |
| teacher_name | TEXT | 教师姓名 |
| receiver | TEXT | 接收人 |
| message | TEXT | 通知内容 |
| change_type | TEXT | `initial/changed/cancelled` |
| sent_status | TEXT | `success/failed/skipped` |
| error_message | TEXT | 错误信息 |
| sent_at | TEXT | 发送时间 |

## Excel 模板设计

建议提供固定模板下载，导入时严格校验表头。

### 模板字段

| 字段 | 必填 | 示例 | 说明 |
|------|------|------|------|
| 年级 | 是 | 高一 | 可匹配 `grade_name` |
| 日期 | 是 | 2026-05-10 | 支持 Excel 日期和文本日期 |
| 开始时间 | 是 | 08:00 | 支持 Excel 时间和文本时间 |
| 结束时间 | 是 | 10:00 | 支持 Excel 时间和文本时间 |
| 学科 | 是 | 语文 | 文本 |
| 考场 | 是 | 第1考场 | 文本 |
| 监考老师 | 是 | 张三 | 匹配教师姓名 |

可选扩展字段：

| 字段 | 说明 |
|------|------|
| 考场序号 | 用于排序 |
| 备注 | 导入后可保留但不参与通知 |

### 导入规则

1. 前端上传 `.xlsx/.xls`。
2. 后端使用 `pandas` 或 `openpyxl` 读取。
3. 校验考试项目是否已存在，导入必须关联到一个 `project_id`。
4. 校验年级必须属于考试项目选中的年级。
5. 校验教师姓名必须能在教师库匹配到唯一教师。
6. 同一项目、年级、日期、开始时间、考场重复时，应按导入策略处理：
   - 默认：覆盖原安排。
   - 可选：导入预览页面允许选择“覆盖/跳过重复项”。
7. 导入成功后只写入草稿数据，不立即通知；由用户点击“保存并通知”触发通知。

### 导出规则

导出当前考试项目全部年级的监考安排，建议按年级拆分多个 sheet：

- `高一`
- `高二`
- `高三`

每个 sheet 保持与导入模板一致的字段，便于导出后再修改导入。

## 后端 API 设计

统一前缀建议：`/api/invigilation`

### 考试项目

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/projects` | 获取考试项目列表 |
| POST | `/projects` | 新建考试项目 |
| GET | `/projects/{project_id}` | 获取项目详情 |
| PUT | `/projects/{project_id}` | 更新项目基础信息 |
| DELETE | `/projects/{project_id}` | 删除或归档项目 |

### 监考安排

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/projects/{project_id}/slots` | 获取项目全部安排，可按 `grade_id/date/teacher_name` 过滤 |
| PUT | `/projects/{project_id}/slots` | 批量保存当前页面编辑后的安排 |
| POST | `/projects/{project_id}/slots/swap-teachers` | 拖拽交换两条安排的监考老师 |
| POST | `/projects/{project_id}/save` | 保存版本，可选择是否发送通知 |

### Excel

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/template` | 下载导入模板 |
| POST | `/projects/{project_id}/import` | 导入 Excel |
| GET | `/projects/{project_id}/export` | 导出 Excel |

### 通知

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/projects/{project_id}/changes` | 查看相对上一版本的变更 |
| POST | `/projects/{project_id}/notify` | 手动发送本版本通知 |
| GET | `/projects/{project_id}/notification-logs` | 查看通知日志 |

## 通知机制设计

### 第一次保存

当考试项目第一次正式保存时：

1. 生成版本 `version_no = 1`。
2. 按教师聚合该教师所有监考场次。
3. 调用 `send_text(content, receiver, producer='invigilation')`。
4. 将每位老师的发送结果写入 `invigilation_notification_log`。
5. 更新项目状态为 `notified`。

通知内容示例：

```text
【监考安排通知】
考试：2026 春季期中考试
张三老师，您的监考安排如下：
1. 2026-05-10 08:00-10:00 语文 高一 第1考场
2. 2026-05-11 14:00-16:00 数学 高二 第3考场
请准时到岗。
```

### 后续编辑保存

后续每次保存时：

1. 读取上一正式版本 `snapshot_json`。
2. 与当前安排生成差异。
3. 只找出有变化的老师，包括：
   - 新增监考场次的老师
   - 被取消监考场次的老师
   - 时间、学科、考场发生变化的老师
   - 拖拽交换导致场次变动的两位老师
4. 仅向这些老师发送变更通知。

变更通知示例：

```text
【监考安排变更通知】
考试：2026 春季期中考试
张三老师，您的监考安排有调整：

新增：
- 2026-05-10 10:20-12:00 英语 高一 第2考场

取消：
- 2026-05-10 08:00-10:00 语文 高一 第1考场

请以本通知为准。
```

### 教师接收人解析

当前 `auth.db.teacher` 表没有明确 `wxid` 字段，`moral.db.teacher` 中存在 `wxid` 字段但可能为空。实现时建议按以下优先级解析：

1. `moral.teacher.wxid`
2. 后续如需扩展，在 `auth.teacher` 新增 `wxid` 或 `contact` 字段
3. 若找不到接收人，通知日志记为 `skipped`，前端展示“未配置接收人”

不要因为单个老师发送失败阻断整个保存流程，应返回发送成功、失败、跳过的统计。

## 变更差异算法

为方便判断变更，建议将每条安排归一化为稳定 key：

```text
grade_id + exam_date + start_time + end_time + subject + room_name
```

然后比较 key 对应的 `teacher_name/teacher_id`。

差异类型：

- `added`：当前版本有，上一版本没有。
- `removed`：上一版本有，当前版本没有。
- `teacher_changed`：同一场次教师变化。
- `slot_changed`：场次时间、学科或考场变化，通常可表现为 removed + added。

拖拽交换两名老师时，本质上也是两条 `teacher_changed`。

## 前端页面设计

页面建议为工作台式布局，不做营销式页面。

### 顶部区域

功能：

- 考试项目选择器
- 新建考试项目按钮
- 导入 Excel
- 导出 Excel
- 保存
- 保存并通知
- 查看通知日志

项目选择器显示：

- 考试名称
- 覆盖年级
- 最近更新时间
- 通知状态

### 新建考试项目弹窗

字段：

- 考试名称
- 学年
- 学期
- 考试日期范围
- 参与年级，多选：高一、高二、高三

创建后生成项目，但安排为空。

### 主体区域

建议使用 tabs 按年级展示：

- 高一
- 高二
- 高三

每个年级内用表格展示：

| 日期 | 时间 | 学科 | 考场 | 监考老师 | 操作 |
|------|------|------|------|----------|------|

支持：

- 行内编辑日期、时间、学科、考场、监考老师
- 新增行
- 删除行
- 复制同一时间段多个考场
- 筛选日期、学科、教师

### 拖拽交换监考老师

推荐方案：

1. 每个“监考老师”单元格作为可拖拽元素。
2. 拖拽老师 A 到老师 B 的单元格时，交换两条安排的教师字段。
3. 前端立即更新本地表格，并标记为 dirty。
4. 点击保存时提交完整 slots 或提交 swap 操作。

为了减少状态不一致，建议前端拖拽只做本地交换，最终统一通过 `PUT /projects/{project_id}/slots` 保存。

前端库选择：

- 可使用 `SortableJS` 或 `vuedraggable`。
- 若不想引入新依赖，可先实现“选择两行后点击交换老师”作为保底功能，后续再加拖拽。

## 数据校验规则

后端必须校验：

1. 考试项目存在。
2. 年级属于该考试项目。
3. 日期在项目日期范围内，若项目设置了日期范围。
4. 开始时间早于结束时间。
5. 同一老师同一时间不能出现在多个考场。
6. 同一考场同一时间不能有重复安排。
7. 教师姓名应匹配到唯一教师；重名时需要前端选择具体教师。

前端应提示：

- 未保存修改
- 导入错误行号
- 冲突安排
- 未配置接收人的老师
- 通知发送失败的老师

## 实施步骤建议

### 第一阶段：基础闭环

1. 新建数据库表和初始化脚本。
2. 新建后端 `invigilation.py` 路由。
3. 实现项目 CRUD。
4. 实现安排列表读取和批量保存。
5. 前端新增菜单、路由、页面。
6. 前端支持手动新增、编辑、删除安排。

验收标准：

- 教务用户能新建一个覆盖多年级的考试项目。
- 每个年级能维护独立的监考安排。
- 多次考试项目能保留并切换查看。

### 第二阶段：Excel 导入导出

1. 实现模板下载。
2. 实现 Excel 导入和校验错误返回。
3. 实现按年级 sheet 导出。
4. 前端展示导入结果和错误行。

验收标准：

- 按模板导入成功。
- 错误模板能返回明确行号和原因。
- 导出的 Excel 可再次导入。

### 第三阶段：通知与版本

1. 实现保存版本表。
2. 第一次保存发送全量通知。
3. 后续保存计算差异，只通知有变化的老师。
4. 实现通知日志页面或弹窗。

验收标准：

- 首次保存时所有有监考任务的老师收到通知。
- 调整两名老师后，只给相关老师发送变更通知。
- 未配置接收人的老师不会阻断保存，日志可见。

### 第四阶段：拖拽交换与体验优化

1. 实现老师单元格拖拽交换。
2. 增加冲突检测即时提示。
3. 增加未保存修改离开提醒。
4. 优化移动端或窄屏表格展示。

验收标准：

- 拖拽交换后表格立即更新。
- 保存后后端数据一致。
- 再次保存只通知发生变化的老师。

## 测试清单

后端测试：

- 项目 CRUD。
- 多年级项目创建。
- 批量保存安排。
- 同一老师同一时间冲突检测。
- 同一考场同一时间冲突检测。
- Excel 导入成功。
- Excel 导入错误行返回。
- Excel 导出文件可读。
- 首次通知全量发送。
- 二次保存只通知差异老师。

前端测试：

- 教务菜单出现“监考安排”。
- 非教务用户不可访问。
- 新建考试项目弹窗字段校验。
- tabs 按年级展示。
- 行内编辑与保存。
- 导入、导出按钮状态。
- 拖拽交换老师。
- 未保存修改提示。

集成验证：

- 使用真实教师数据创建考试项目。
- 导入覆盖高一、高二、高三的模板。
- 保存并通知，检查 `invigilation_notification_log`。
- 修改两条安排后再次保存，确认只生成对应老师的变更通知。

## 风险与注意事项

1. 教师通知接收人数据可能不完整，必须有跳过和日志机制。
2. 教师重名会影响 Excel 导入，需要支持重名提示或增加教师 ID 列。
3. 拖拽交换只是 UI 操作，最终以后端保存和冲突校验为准。
4. 不建议导入后自动发通知，避免误导入造成误通知。
5. 版本快照必须在通知前生成，保证通知内容和保存内容一致。
6. 删除考试项目建议默认软删除或归档，避免误删历史记录。

## 建议文件清单

后端：

- `lesson/models/datas_api/invigilation.py`
- `lesson/utils/invigilation_db.py`
- `lesson/scripts/create_invigilation_tables.py`
- `lesson/tests/test_invigilation_api.py`

前端：

- `frontend/src/views/InvigilationArrange.vue`
- `frontend/src/api/modules/invigilation.js`
- `frontend/src/__tests__/invigilation.test.js`

文档：

- `docs/invigilation-arrangement-implementation-plan.md`
