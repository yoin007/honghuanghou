# 鉴权系统总图

## 1. 为什么当前会显得混乱

系统里其实同时存在 4 类问题：

1. 谁在访问系统
2. 他能不能调用这个 API
3. 这个 API 返回或操作哪些数据记录
4. 在这些记录里，他能查看、创建、修改、删除哪些

如果把这 4 件事混在同一个“权限”概念里，就会出现：

- API 允许访问，但数据不该看
- 列表能看到，编辑按钮却不该出现
- 创建接口能调，但不能给某些学生创建
- 一段代码按数据库判断，另一段代码按角色硬编码判断

## 2. 统一分层模型

建议把鉴权拆成 4 层。

### L1 身份认证

回答：你是谁。

| 场景 | 当前方式 | 是否保留 |
| --- | --- | --- |
| 前端 / Web API | JWT | 保留 |
| 微信消息命令 | `member.py` 的 `check_permission` | 保留 |
| HTTP API 的微信 token 通道 | `wechat_auth.py` | 保留，但只用于 HTTP API |

说明：

- `member.py` 的 `check_permission` 是微信消息命令体系，不应被 Web API 鉴权替代。
- `wechat_auth.py` 是 HTTP API 的第二认证通道，不等于 `member.py`。

### L2 API 调用授权

回答：你能不能调用这个接口。

统一由 `api_permission_config` 决定：

- `allowed_roles`
- `min_level`
- `policy_mode`
- `is_public`
- `enforce_backend`
- `auth_mode`

推荐策略：

| 策略 | 配置方式 |
| --- | --- |
| 公开接口 | `is_public = 1` |
| 登录即可 | `allowed_roles=[]`、`min_level=0`、`enforce_backend=1` |
| 受控接口 | 角色 + 等级 + 策略 |
| 暂缓纳管 | `enforce_backend=0` |

迁移完成后的业务 API，应统一：

```python
require_configured_api_permission(API_PATH, METHOD, allow_missing=False)
```

对存在“函数直调测试”或“服务内部复用”的接口，还应在函数体内保留同口径的数据库权限断言，避免 FastAPI 依赖只在 HTTP 请求路径生效、而内部调用绕开鉴权。

### L3 数据记录范围授权

回答：这个 API 涉及的数据记录里，你能看哪些。

统一由 `data_scope_rules` 决定。

推荐范围：

- `own_created`
- `teaching_classes`
- `managed_classes`
- `managed_grades`
- `all`

示例：

```json
{
  "teacher": ["own_created"],
  "cleader": ["own_created", "managed_classes"],
  "g_leader": ["own_created", "managed_grades"],
  "xuefa": ["all"],
  "admin": ["all"]
}
```

### L4 目标对象 / 动作授权

回答：

- 创建时能给谁创建
- 编辑时能改哪些记录
- 删除时能删哪些记录

这里应拆成两类：

1. `target_scope_rules`
   - 创建、录入、批量导入时，能选择哪些学生或对象

2. 行级动作范围
   - 查看范围和编辑范围不一定相同
   - 例如：
     - 年级主任可以看全年级记录
     - 但只能编辑自己创建的记录

## 3. 角色基准规则

以下是当前应统一遵循的角色口径。

| 角色 | 查看范围 | 创建目标 | 编辑 / 删除 |
| --- | --- | --- | --- |
| teacher | 自己创建的记录 | 自己任教班级学生 | 自己创建的记录 |
| cleader | 自己创建 + 自己管理班级记录 | 自己任教班级 + 自己管理班级学生 | 自己创建的记录 |
| g_leader | 自己创建 + 自己管理年级记录 | 自己任教班级 + 自己管理年级学生 | 自己创建的记录 |
| xuefa | 全校 | 全校 | 全校 |
| jiaowu | 视业务而定；德育类当前多为全校 | 视业务而定 | 视业务而定 |
| admin | 全部 | 全部 | 全部 |

## 4. 核心业务矩阵

### 4.1 日常表现

| API | 数据对象 | teacher | cleader | g_leader | xuefa/admin |
| --- | --- | --- | --- | --- | --- |
| 列表 | 日常表现记录 | 仅自己创建 | 自己创建 + 管理班级 | 自己创建 + 管理年级 | 全校 |
| 创建 | 目标学生 | 任教班级 | 任教班级 + 管理班级 | 任教班级 + 管理年级 | 全校 |
| 编辑 | 记录 | 仅自己创建 | 仅自己创建 | 仅自己创建 | 全校 |
| 删除 | 记录 | 仅自己创建 | 仅自己创建 | 仅自己创建 | 全校 |

### 4.2 点滴记录

与日常表现同口径：

- 看：按角色数据范围
- 建：按目标学生范围
- 改删：只看动作范围，教师 / 班主任 / 年级主任均只改自己创建

### 4.3 校级事件

| API | 数据对象 | teacher | cleader | g_leader | xuefa/admin |
| --- | --- | --- | --- | --- | --- |
| CRUD | 校级事件记录 | 无 | 无 | 无 | 全校 |
| 事件类型管理 | 校级事件类型 | 无 | 无 | 无 | 可管理 |
| 一生一册中查看 | 学生关联事件 | 不涉及 | 可看管理班级学生 | 可看管理年级学生 | 全校 |

说明：

- 班主任 / 年级主任不直接访问校级事件管理页。
- 但一生一册聚合展示时，需要在学生档案里看到相应记录。

### 4.4 处分管理

| API | 数据对象 | teacher | cleader | g_leader | xuefa/admin |
| --- | --- | --- | --- | --- | --- |
| CRUD | 处分记录 | 无 | 无 | 无 | 全校 |
| 复核 | 处分记录 | 无 | 无 | 无 | 全校 |
| 一生一册中查看 | 学生处分记录 | 不涉及 | 可看管理班级学生 | 可看管理年级学生 | 全校 |

### 4.5 德育任务

| API | 数据对象 | teacher | cleader | g_leader | xuefa/admin |
| --- | --- | --- | --- | --- | --- |
| 任务定义 CRUD | 德育任务 | 无 | 无 | 无 | 可管理 |
| 完成记录 | 学生任务完成记录 | 无 | 无 | 无 | 全校 |
| 一生一册中查看 | 学生任务记录 | 不涉及 | 可看管理班级学生 | 可看管理年级学生 | 全校 |

### 4.6 集体事件

| API | 数据对象 | teacher | cleader | g_leader | xuefa/admin |
| --- | --- | --- | --- | --- | --- |
| CRUD | 集体事件 | 无 | 无 | 无 | 全校 |
| 分配调整 | 集体事件学生分配记录 | 无 | 无 | 无 | 全校 |
| 一生一册中查看 | 学生关联集体事件 | 不涉及 | 可看管理班级学生 | 可看管理年级学生 | 全校 |

### 4.7 一生一册 / 学生画像 / 趋势图

| 功能 | 数据对象 | cleader | g_leader | xuefa/jiaowu/admin |
| --- | --- | --- | --- | --- |
| 一生一册 | 学生综合档案 | 管理班级学生 | 管理年级学生 | 全校 |
| 学生个人得分趋势 | 某学生趋势 | 管理班级学生 | 管理年级学生 | 全校 |
| 班级趋势 | 某班级趋势 | 管理班级 | 视业务配置 | 全校 |
| 年级趋势 | 某年级趋势 | 无 | 管理年级 | 全校 |

## 5. 一个 API 应如何建模

以后每个 API 都按下面 5 个问题建模：

1. 这是什么 API
2. 谁可以调用它
3. 它读写什么数据对象
4. 查看数据范围是什么
5. 创建目标与编辑 / 删除动作范围是什么

例如：日常表现创建

| 维度 | 配置 |
| --- | --- |
| API | `/api/moral/daily-records/create` |
| 可调用角色 | teacher / cleader / g_leader / xuefa / jiaowu / admin |
| 数据对象 | `student_daily_record` |
| 查看范围 | 不适用 |
| 目标范围 | `teacher=teaching_classes` 等 |

例如：日常表现更新

| 维度 | 配置 |
| --- | --- |
| API | `/api/moral/daily-records/update` |
| 可调用角色 | teacher / cleader / g_leader / xuefa / jiaowu / admin |
| 数据对象 | `student_daily_record` |
| 查看范围 | 不适用 |
| 动作范围 | teacher / cleader / g_leader 仅 `own_created` |

## 6. 当前系统中应继续清理的混乱点

1. API 鉴权
   - 日常表现、点滴记录、AI 诊疗、一生一册、AI 配置及一批系统管理接口，已统一切到 `allow_missing=False`
   - `日常表现学生统计`、`一生一册导出` 已补成独立可配置 API
   - 后续继续迁移的接口，也应坚持“默认放行必须改成数据库显式策略”

2. 数据范围 fallback
   - `get_record_data_scope()` 仍存在静态权限 fallback
   - 迁移完成后应逐步取消

3. 目标范围 fallback
   - 已调整为：
     - API 完全未纳管时，保留旧兼容行为
     - API 已纳管但未配置 `target_scope_rules` 时，拒绝目标对象选择
   - 后续可继续把“未纳管兼容放行”压缩到更小范围

4. 旧静态权限名
   - `MORAL_PERMISSIONS`
   - `check_moral_permission`
   - `require_permission`
   - 这些应从业务主链路逐步退出

5. 微信鉴权
   - `member.py` 的命令鉴权保留
   - HTTP API 的微信 token 支持走 `auth_mode=wechat_token/both`
   - 不应拿 `enforce_backend=0` 代替微信鉴权

## 6.1 截至 2026-05-13 的实现状态

已完成：

- 统一 API 权限配置已落库，并由前端页面维护
- 数据范围、目标范围、动作范围已拆分建模
- 预览校验已支持按角色与多角色合并展示
- 风险巡检、模块风险统计、审计报告导出已具备
- 日常表现、点滴记录、生日提醒、评价查询、学生画像、学期末评价、校级事件、处分、任务、集体事件、诊疗、一生一册、任务结转、累进规则学生视图、菜单权限、数据库管理、基础配置与部分驾驶舱接口已纳入统一配置
- `日常表现学生统计` 已按记录范围聚合，不再绕过数据权限
- 学生画像、评价查询等动态路由已改成真实路由模板配置，不再停留在“逻辑别名路径”
- dashboard 关键接口已补函数内数据库权限断言，HTTP 调用与直接函数调用保持同一权限语义
- 年级趋势接口已改为先校验授权范围、再校验数据存在性，越权访问返回 `403`
- 截至 2026-05-13，当前库权限巡检结果为 `174` 条 API、`0` 条风险
- 截至 2026-05-13，后端全量测试 `608 passed`

仍保留兼容层：

- `get_record_data_scope()` 的静态权限 fallback
- 明确暂缓迁移的老模块与部分辅助接口
- 微信命令鉴权链路

## 7. 推荐的最终配置模型

最终每条 API 配置至少应包含：

- `api_path`
- `http_method`
- `match_type`
- `allowed_roles`
- `min_level`
- `policy_mode`
- `auth_mode`
- `is_public`
- `enforce_backend`
- `data_scope_rules`
- `target_scope_rules`

进一步建议补充：

- `resource_type`
  - 例如 `student_daily_record`
- `action_type`
  - 例如 `list/create/update/delete/review/export`
- `operation_scope_rules`
  - 专门描述编辑、删除、导出等动作范围

这样前端配置页面才能真正做到：

> 看到 API，就能同时看懂它操作什么数据、谁能调用、能看哪些记录、能改哪些记录。
