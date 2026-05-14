# 统一权限配置优化方案

## 目标

将接口权限、数据范围、目标范围统一收口到数据库配置：

- API 是否可调用，由 `api_permission_config` 实时决定。
- 记录可查看范围，由 `data_scope_rules` 实时决定。
- 新增/操作对象范围，由 `target_scope_rules` 实时决定。
- 代码不再把“缺配置”当作隐式放行，默认拒绝应成为迁移完成后的标准。

## 统一策略模型

现有字段已经足够表达统一模型，不再新增平行表。

| 策略 | 字段表达 | 适用场景 |
| --- | --- | --- |
| 公开接口 | `is_public = 1` | 无需登录的公开资源 |
| 登录即可 | `is_public = 0`、`allowed_roles = []`、`min_level = 0`、`enforce_backend = 1` | 需要身份，但不区分角色 |
| 受控接口 | `allowed_roles` + `min_level` + `policy_mode`、`enforce_backend = 1` | 后台业务接口、管理接口 |
| 显式旁路 | `enforce_backend = 0` | 迁移期暂不纳入统一鉴权的旧接口 |

说明：

- “默认放行”不应再靠 `allow_missing=True` 实现，而应落成明确的数据库策略。
- 对于需要登录但任意登录角色都能访问的接口，使用“登录即可”策略，而不是公开接口。
- 对于明确暂缓迁移的模块，可先保留 `enforce_backend = 0` 或旧入口，后续逐批纳入。

## 运行时规则

### API 入口鉴权

迁移完成后的标准依赖应是：

```python
require_configured_api_permission(API_KEY, "GET", allow_missing=False)
```

含义：

- 查到数据库配置：按数据库策略执行。
- 查不到数据库配置：直接拒绝。

### 数据范围

优先读取 `data_scope_rules`。

推荐保留的范围键：

- `own_created`
- `teaching_classes`
- `managed_classes`
- `managed_grades`
- `all`

### 目标范围

优先读取 `target_scope_rules`。

推荐保留的范围键：

- `teaching_classes`
- `managed_classes`
- `managed_grades`
- `all_students`

## 当前默认策略建议

### 受控接口

以下已迁移或本轮收紧的接口应全部使用数据库强控制：

- dashboard 全部接口
- 日常表现主流程
- 点滴记录主流程
- 校级事件及事件类型
- 处分记录、撤销、复核
- 集体事件及分配调整
- 德育任务主流程

### 登录即可

若某些接口当前业务上允许“登录用户普遍访问”，应在数据库中显式配置为：

```json
{
  "allowed_roles": [],
  "min_level": 0,
  "policy_mode": "role_and_level",
  "is_public": 0,
  "enforce_backend": 1
}
```

这比代码中的“无配置默认放行”更可审计。

### 公开接口

只有真正无需登录的接口，才使用：

```json
{
  "is_public": 1
}
```

### 暂缓迁移

当前约定暂不迁移：

- 教师管理
- 文件收集
- 旧版作业 / 请假 / 课表
- 监考安排
- 部分 moral 辅助接口

这些接口应保留迁移标记，避免误以为已完成统一化。

## 收口步骤

1. 先把所有已迁移接口改成 `allow_missing=False`。
2. 把缺失的默认配置补入 `DEFAULT_API_PERMISSIONS`。
3. 将“登录即可”的接口改为数据库显式策略。
4. 逐步淘汰 YAML fallback。
5. 逐步淘汰 `require_permission()` 与 `MORAL_PERMISSIONS` 对业务接口的实际控制作用。
6. 将“查看他人”“代操作”等对象级能力补成独立可配置策略。

## 截至 2026-05-13 的已完成事项

- dashboard 趋势接口支持 pattern 路由配置。
- dashboard 主接口补充函数内数据库权限断言，HTTP 请求和直接函数调用保持一致。
- 年级趋势接口按“先授权、后存在性”处理越权访问，返回语义稳定为 `403`。
- 校级事件类型管理、处分复核、集体事件相关接口改为数据库缺配置即拒绝。
- 日常表现、点滴记录、生日提醒、评价查询、画像、学期末评价、诊疗、一生一册等主流程均已纳入统一配置。
- 任务结转、累进规则学生视图、菜单权限、数据库管理、基础配置接口已纳入统一配置。
- 数据范围、目标范围、动作范围均由数据库优先执行。
- 当前权限审计结果为 `174` 条 API、`0` 条风险。
- 后端全量测试结果为 `608 passed`。
