# 教师待办功能实施方案

## 1. 背景与目标

当前系统已具备：

- 教师工作台
- 顶部动态菜单权限
- 数据库驱动的 API 权限配置
- 教师、班主任、年级主任、学发、教务、管理员多角色体系

本方案新增一个独立的“教师待办”模块，用于承载教师个人及协作型待办事项。

目标如下：

1. 顶部导航栏“教师”栏目下新增“我的待办”
2. 教师可以给自己创建待办事项
3. 待办支持一次性任务和周期性任务
4. 周期性任务支持按周、月、年
5. 创建待办时可关联其他老师，被关联老师在自己的待办列表中同步可见
6. 待办状态支持未完成、已完成
7. 待办列表支持按周、月、年查看，并支持按状态筛选
8. 教师工作台新增“近期待办”视图

## 2. 设计原则

### 2.1 独立建模，不复用旧任务模块

本功能不复用：

- 旧版 `/api/tasks`
- 德育任务 `/api/moral/tasks`
- 调度器任务 `scheduled_tasks`

原因：

- 旧任务模块偏系统管理或运维
- 德育任务面向学生评价，不是教师个人协作待办
- 教师待办需要“关联老师”“按实例完成”“近期待办”等独立语义

### 2.2 周期任务必须落实例

周期任务不能只保留规则并在查询时临时计算。

必须区分：

- `series`：待办模板或周期定义
- `occurrence`：某一周期中真实出现的一次待办实例

否则无法准确记录：

- 某一周是否完成
- 某个月是否延后
- 哪一期已完成、哪一期未完成

### 2.3 与现有权限体系保持一致

教师待办必须纳入统一数据库权限配置：

- API 是否可调用：`api_permission_config`
- 查看范围：`data_scope_rules`
- 编辑/删除范围：`operation_scope_rules`

## 3. 功能范围

### 3.1 第一阶段必须实现

- 创建一次性待办
- 创建周期性待办
- 周期单位：周、月、年
- 关联老师多选
- 查询个人可见待办
- 完成与取消完成
- 周/月/年视图
- 状态筛选
- 教师工作台近期待办
- 权限配置接入

### 3.2 第一阶段暂不实现

- 提醒通知
- 微信推送
- 任务附件
- 待办评论
- 每位关联老师独立完成状态
- 拖拽式日历
- 批量导入导出

## 4. 角色与业务规则

### 4.1 角色可见范围

默认允许访问教师待办模块的角色：

- `teacher`
- `cleader`
- `g_leader`
- `xuefa`
- `jiaowu`
- `admin`

最低等级建议统一为：

- `10`

### 4.2 查看规则

用户可以查看：

- 自己创建的待办
- 关联给自己的待办

### 4.3 编辑删除规则

只有创建者可以：

- 编辑待办定义
- 删除待办定义

### 4.4 完成规则

创建者与被关联老师均可：

- 将某次待办实例标记为已完成
- 将某次待办实例恢复为未完成

### 4.5 关联老师完成状态

第一阶段采用：

- 同一 occurrence 共享一个状态

即：

- 创建者完成后，关联老师看到已完成
- 关联老师完成后，创建者也看到已完成

后续若业务需要“每位老师分别完成”，再新增按人员拆分的 occurrence_assignee_status 表。

## 5. 导航与前端页面

### 5.1 顶部导航

在“教师”栏目下新增：

- 教师工作台
- 我的待办

建议菜单键：

- `teacher-todo`

建议路由：

- `/teacher/todo`

涉及代码：

- `lesson/models/datas_api/moral/menu_permission.py`
- `frontend/src/stores/resourcePermission.js`
- `frontend/src/router/index.js`

### 5.2 我的待办页面

建议新增：

- `frontend/src/views/teacher/Todo.vue`
- `frontend/src/api/modules/teacherTodo.js`

### 5.3 页面布局

页面建议分为 4 块。

#### 5.3.1 顶部工具栏

包含：

- 新增待办按钮
- 周 / 月 / 年视图切换
- 状态筛选：
  - 全部
  - 未完成
  - 已完成
- 周期导航：
  - 上一周期
  - 当前周期
  - 下一周期

#### 5.3.2 列表区

每条待办建议展示：

- 标题
- 描述摘要
- 周期类型
- 发生日期
- 截止时间
- 创建者
- 关联老师
- 状态
- 是否本人创建
- 操作按钮

#### 5.3.3 创建/编辑弹窗

字段建议：

- 标题
- 描述
- 类型：
  - 一次性
  - 每周
  - 每月
  - 每年
- 日期规则
- 关联老师
- 可选结束日期

联动规则：

- 一次性：显示单次日期
- 每周：显示星期几
- 每月：显示几号
- 每年：显示月日

#### 5.3.4 空状态

至少支持：

- 当前周期暂无待办
- 当前筛选条件无结果
- 请求失败

## 6. 数据模型设计

建议新增 3 张表。

### 6.1 `teacher_todo_series`

表示“待办定义”。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | INTEGER PK | 主键 |
| `title` | TEXT | 标题 |
| `description` | TEXT | 描述 |
| `creator_teacher_id` | TEXT | 创建人 teacher_id |
| `creator_name` | TEXT | 创建人显示名，便于展示 |
| `todo_type` | TEXT | `one_off/weekly/monthly/yearly` |
| `start_date` | TEXT | 生效开始日期 |
| `end_date` | TEXT | 可空，生效结束日期 |
| `recurrence_rule_json` | TEXT | 周期规则 JSON |
| `is_active` | INTEGER | 1 生效，0 删除或停用 |
| `created_at` | TEXT | 创建时间 |
| `updated_at` | TEXT | 更新时间 |

### 6.2 `teacher_todo_assignee`

表示“待办关联老师”。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | INTEGER PK | 主键 |
| `todo_series_id` | INTEGER | 待办定义 ID |
| `teacher_id` | TEXT | 关联教师 teacher_id |
| `teacher_name` | TEXT | 显示名 |
| `created_at` | TEXT | 创建时间 |

建议：

- 创建者也插入 assignee 表，统一查询
- `(todo_series_id, teacher_id)` 建唯一索引

### 6.3 `teacher_todo_occurrence`

表示“真实待办实例”。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | INTEGER PK | 主键 |
| `todo_series_id` | INTEGER | 所属 series |
| `occurrence_date` | TEXT | 实例日期 |
| `due_at` | TEXT | 可空，截止时间 |
| `status` | TEXT | `pending/completed` |
| `completed_at` | TEXT | 完成时间 |
| `completed_by` | TEXT | 完成人 teacher_id |
| `created_at` | TEXT | 创建时间 |
| `updated_at` | TEXT | 更新时间 |

建议：

- `(todo_series_id, occurrence_date)` 建唯一索引

## 7. 周期规则设计

### 7.1 推荐 JSON 结构

#### 每周

```json
{
  "unit": "weekly",
  "weekday": 1
}
```

#### 每月

```json
{
  "unit": "monthly",
  "day_of_month": 15
}
```

#### 每年

```json
{
  "unit": "yearly",
  "month": 9,
  "day": 1
}
```

### 7.2 实例生成策略

创建待办时：

- `one_off`：立即生成 1 个 occurrence
- `weekly`：默认生成未来 4 周 occurrence
- `monthly`：默认生成未来 2 个月 occurrence
- `yearly`：默认生成未来 1 年 occurrence

查询指定周期时：

- 若该周期应存在 occurrence，但尚未生成，则补齐

## 8. 后端 API 设计

建议新增模块：

- `lesson/models/datas_api/teacher_todo.py`

建议前缀：

- `/api/teacher/todos`

### 8.1 查询待办列表

`GET /api/teacher/todos`

参数：

| 参数 | 示例 | 说明 |
| --- | --- | --- |
| `view` | `week/month/year` | 当前视图 |
| `anchor_date` | `2026-05-13` | 当前周期锚点 |
| `status` | `all/pending/completed` | 状态筛选 |
| `scope` | `all_visible/created/assigned` | 可选筛选 |

返回建议：

```json
{
  "success": true,
  "data": {
    "range": {
      "view": "week",
      "start_date": "2026-05-11",
      "end_date": "2026-05-17"
    },
    "summary": {
      "total": 8,
      "pending": 5,
      "completed": 3
    },
    "items": []
  }
}
```

### 8.2 创建待办

`POST /api/teacher/todos`

请求体：

```json
{
  "title": "周五提交教研材料",
  "description": "提交高二语文组教研小结",
  "todo_type": "weekly",
  "start_date": "2026-05-15",
  "end_date": null,
  "recurrence_rule": {
    "unit": "weekly",
    "weekday": 5
  },
  "assignee_teacher_ids": ["T_张三", "T_李四"]
}
```

### 8.3 更新待办定义

`PUT /api/teacher/todos/{series_id}`

仅创建者可操作。

建议：

- 已完成 occurrence 保留
- 未来未完成 occurrence 可按新规则重建

### 8.4 删除待办

`DELETE /api/teacher/todos/{series_id}`

建议：

- 软删除 series
- 同步隐藏未来 occurrence
- 已完成历史默认保留但前端不再展示

### 8.5 完成某次实例

`POST /api/teacher/todos/occurrences/{occurrence_id}/complete`

### 8.6 恢复未完成

`POST /api/teacher/todos/occurrences/{occurrence_id}/reopen`

### 8.7 教师工作台近期待办

`GET /api/teacher/todos/upcoming`

参数建议：

- `limit=5`

## 9. API 权限配置设计

建议默认新增 API 配置：

| API | 说明 |
| --- | --- |
| `/api/teacher/todos` | 查询列表 |
| `/api/teacher/todos/create` | 创建待办 |
| `/api/teacher/todos/{series_id}` | 更新/删除 |
| `/api/teacher/todos/occurrences/{occurrence_id}/complete` | 完成 |
| `/api/teacher/todos/occurrences/{occurrence_id}/reopen` | 恢复 |
| `/api/teacher/todos/upcoming` | 近期待办 |

建议默认允许角色：

```json
["admin", "jiaowu", "xuefa", "g_leader", "cleader", "teacher"]
```

建议默认最低等级：

```json
10
```

### 9.1 数据范围建议

查询接口建议支持：

```json
{
  "teacher": ["own_created", "assigned_to_me"],
  "cleader": ["own_created", "assigned_to_me"],
  "g_leader": ["own_created", "assigned_to_me"],
  "xuefa": ["own_created", "assigned_to_me"],
  "jiaowu": ["own_created", "assigned_to_me"],
  "admin": ["all"]
}
```

### 9.2 操作范围建议

编辑 / 删除：

```json
{
  "teacher": ["own_created"],
  "cleader": ["own_created"],
  "g_leader": ["own_created"],
  "xuefa": ["own_created"],
  "jiaowu": ["own_created"],
  "admin": ["all"]
}
```

完成 / 恢复：

```json
{
  "teacher": ["own_created", "assigned_to_me"],
  "cleader": ["own_created", "assigned_to_me"],
  "g_leader": ["own_created", "assigned_to_me"],
  "xuefa": ["own_created", "assigned_to_me"],
  "jiaowu": ["own_created", "assigned_to_me"],
  "admin": ["all"]
}
```

说明：

- `assigned_to_me` 是新增逻辑范围键
- 若实现阶段暂不扩展通用范围枚举，也可以先在 teacher todo 模块内部实现该约束
- 但从长期一致性看，推荐正式纳入权限范围语义

## 10. 教师工作台集成

### 10.1 后端

相关文件：

- `lesson/models/datas_api/dashboard_workbench.py`
- `lesson/models/datas_api/dashboard.py`

建议新增：

- `get_teacher_upcoming_todos(...)`

并在教师工作台响应中增加：

```json
{
  "tables": {
    "upcoming_todos": []
  }
}
```

同时建议新增指标卡：

- `未完成待办`

点击跳转：

- `/teacher/todo`

### 10.2 前端

文件：

- `frontend/src/views/dashboard/TeacherWorkbench.vue`

新增一个 panel：

- 标题：近期待办
- 展示最近 5 条未完成待办
- 每条展示：
  - 标题
  - 日期
  - 创建者或协作标识
- 点击进入 `/teacher/todo`

## 11. 推荐代码落点

### 11.1 后端

- `lesson/models/datas_api/teacher_todo.py`
- `lesson/models/datas_api/__init__.py`
- `lesson/models/datas_api/moral/api_permission.py`
- 建表或迁移脚本

### 11.2 前端

- `frontend/src/views/teacher/Todo.vue`
- `frontend/src/api/modules/teacherTodo.js`
- `frontend/src/router/index.js`
- `frontend/src/stores/resourcePermission.js`

### 11.3 工作台

- `lesson/models/datas_api/dashboard_workbench.py`
- `lesson/models/datas_api/dashboard.py`
- `frontend/src/views/dashboard/TeacherWorkbench.vue`

## 12. 实施阶段

### Phase 1：后端模型与接口

1. 新增三张表
2. 新增 `teacher_todo.py`
3. 实现查询、创建、编辑、删除、完成、恢复
4. 完成周期实例生成逻辑
5. 补齐 API 权限默认配置

### Phase 2：我的待办页面

1. 新增前端 API 模块
2. 新增路由
3. 新增菜单项
4. 完成列表、筛选、创建/编辑弹窗
5. 接入权限按钮显隐

### Phase 3：教师工作台

1. 后端返回 `upcoming_todos`
2. 工作台新增指标卡与 panel
3. 增加跳转

### Phase 4：测试与验收

1. 后端单测
2. 前端组件与路由测试
3. 权限测试
4. 周期生成测试
5. 教师工作台契约测试

## 13. 测试清单

### 13.1 后端测试

- 教师创建一次性待办
- 教师创建每周待办
- 教师创建每月待办
- 教师创建每年待办
- 创建时关联其他教师
- 被关联教师能查询到待办
- 未关联教师查询不到
- 创建者可以编辑与删除
- 被关联教师不能编辑与删除
- 创建者与被关联教师都可以完成 occurrence
- 完成后可恢复
- 周视图正确
- 月视图正确
- 年视图正确
- 状态筛选正确
- upcoming 返回最近未完成事项

### 13.2 前端测试

- 顶部导航显示“我的待办”
- 教师页可正常加载
- 周/月/年切换正确
- 状态筛选正确
- 创建表单字段联动正确
- 编辑弹窗正确回填
- 完成与恢复按钮行为正确
- 权限按钮显隐正确
- 教师工作台出现近期待办区域

## 14. 验收标准

满足以下条件视为完成：

1. 教师导航中出现“我的待办”
2. 待办页能创建一次性和周期任务
3. 可关联教师并同步显示
4. 列表支持周/月/年和状态筛选
5. 可完成、恢复待办实例
6. 权限规则符合本方案
7. 教师工作台显示近期待办
8. 所有新增测试通过

## 15. 给实现 AI 的执行说明

请严格按以下约束实施：

1. 不复用旧任务模块
2. 使用独立的教师待办数据模型
3. 周期任务必须落实例
4. 新 API 必须纳入数据库权限配置
5. 前端菜单与按钮显隐要接入现有权限体系
6. 保持代码风格与当前项目一致
7. 优先补测试，再做联调修正

