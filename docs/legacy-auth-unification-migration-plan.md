# 旧模块统一鉴权迁移计划

## 1. 目标

将以下暂缓迁移模块逐步纳入统一鉴权体系：

- 教师管理
- 文件收集
- 旧版作业 / 请假 / 课表
- 监考安排
- 部分 moral 辅助接口

迁移目标不是简单地“所有接口都强制登录”，而是让每个接口都有清晰、可审计、可配置的数据库策略：

1. 公开接口显式配置为公开。
2. 登录接口显式配置为登录即可或指定角色。
3. 管理接口显式配置角色和最低等级。
4. 涉及具体记录的接口显式配置数据范围或动作范围。
5. 前端菜单、按钮、后端 API 权限保持一致。
6. 微信鉴权 `member.py/check_permission` 保留，不纳入本轮统一 JWT 鉴权替换。

## 2. 迁移原则

### 2.1 先配置，后切入口

每迁移一个接口，必须先补齐 `api_permission_config` 默认配置，再将后端依赖改为统一鉴权。

推荐依赖：

```python
require_configured_api_permission(API_PATH, "GET", allow_missing=False)
```

### 2.2 公开接口也必须登记

公开接口不应依赖“无配置放行”。

应显式配置：

```json
{
  "is_public": 1,
  "allowed_roles": [],
  "min_level": 0,
  "enforce_backend": 1
}
```

### 2.3 旧判断先保留

迁移初期不要立刻删除原业务判断。

推荐顺序：

1. 补数据库配置
2. 接入统一 API 入口鉴权
3. 保留原对象级业务判断
4. 补测试确认新旧判断一致
5. 再考虑将对象级判断改造成统一范围工具

### 2.4 涉及记录必须做对象级校验

只检查“API 能否调用”不够。

涉及具体记录时，还要回答：

- 能看哪些记录
- 能创建给哪些对象
- 能编辑/删除哪些已有记录

## 3. 模块必要性与优先级

| 模块 | 必要性 | 迁移优先级 | 主要原因 |
| --- | --- | --- | --- |
| 教师管理 | 高 | P0 | 账号、角色、等级、任教班级影响整个权限系统 |
| 文件收集 | 高 | P0 | 有明确的“自己文件/全量文件”边界 |
| 旧版请假 | 高 | P1 | 学生出勤数据敏感，班级/年级范围明确 |
| 监考安排 | 中高 | P1 | 涉及监考安排、通知、导入导出，角色边界简单 |
| 旧版作业 | 中 | P2 | 公开查看与教师发布编辑混杂 |
| 旧版课表 | 中低 | P2 | 多数接口公开，维护接口需要强控 |
| moral 辅助接口 | 分情况 | 持续治理 | 部分接口可能成为绕过主权限的入口 |

## 4. Phase 0：盘点与冻结基线

### 4.1 任务

只读盘点，不改变业务行为。

1. 列出以下模块全部路由：
   - 教师管理
   - 文件收集
   - 旧版作业
   - 旧版请假
   - 旧版课表
   - 监考安排
   - moral 辅助接口
2. 标记当前鉴权来源：
   - 无鉴权
   - `get_current_user`
   - `check_legacy_api_permission`
   - 手写角色判断
   - `require_configured_api_permission`
3. 标记业务策略：
   - 公开
   - 登录即可
   - 指定角色
   - 本人数据
   - 班级范围
   - 年级范围
   - 全校范围
4. 对照前端页面，列出每个页面启动依赖接口。
5. 将现有 YAML/代码策略同步进 `api_permission_config`，但暂不改变运行时行为。

### 4.2 交付物

- 接口清单表
- 当前鉴权来源表
- 公开接口清单
- 数据范围接口清单
- 风险列表

### 4.3 验收

- 现有页面行为不变。
- 所有接口都有明确迁移分类。
- 权限审计可以区分：
  - 已迁移接口
  - 公开接口
  - 暂缓接口
  - 旧鉴权保留接口

## 5. Phase 1：教师管理、文件收集、监考安排

这一阶段迁移低风险、规则清晰的模块。

## 5.1 教师管理

### 5.1.1 范围

涉及后端：

- `lesson/models/datas_api/teachers.py`

主要接口：

- 获取教师列表
- 创建教师
- 更新教师
- 删除教师
- 获取教师任教班级
- 更新教师任教班级
- 初始化教师任教班级
- 教师修改自己的密码

### 5.1.2 默认策略

管理类接口：

```json
{
  "allowed_roles": ["admin"],
  "min_level": 100,
  "operation_scope_rules": {
    "admin": ["all"]
  }
}
```

教师改密：

```json
{
  "allowed_roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu"],
  "min_level": 10,
  "operation_scope_rules": {
    "teacher": ["self"],
    "cleader": ["self"],
    "g_leader": ["self"],
    "xuefa": ["self"],
    "jiaowu": ["self"]
  }
}
```

### 5.1.3 实施要求

1. 管理类接口接入 `require_configured_api_permission(..., allow_missing=False)`。
2. `change-password` 保持“本人操作”校验。
3. 不要把教师改密误配为 admin-only。

### 5.1.4 验收

- 管理员能继续管理教师。
- 普通教师不能创建、更新、删除教师。
- 普通教师只能修改自己的密码。
- 后端测试覆盖 admin 与非 admin 场景。

## 5.2 文件收集

### 5.2.1 范围

涉及后端：

- `lesson/models/datas_api/filegather.py`

主要接口：

- 上传文件
- 查看我的文件
- 删除我的文件
- 管理端待处理文件
- 管理端已完成文件
- 标记完成
- 下载文件
- 文件统计
- 月份列表

### 5.2.2 默认策略

教师端：

```json
{
  "allowed_roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"],
  "min_level": 10,
  "data_scope_rules": {
    "teacher": ["own_created"],
    "cleader": ["own_created"],
    "g_leader": ["own_created"],
    "xuefa": ["own_created"],
    "jiaowu": ["own_created"],
    "admin": ["all"]
  },
  "operation_scope_rules": {
    "teacher": ["own_created"],
    "cleader": ["own_created"],
    "g_leader": ["own_created"],
    "xuefa": ["own_created"],
    "jiaowu": ["own_created"],
    "admin": ["all"]
  }
}
```

管理端：

```json
{
  "allowed_roles": ["jiaowu", "admin"],
  "min_level": 10,
  "data_scope_rules": {
    "jiaowu": ["all"],
    "admin": ["all"]
  },
  "operation_scope_rules": {
    "jiaowu": ["all"],
    "admin": ["all"]
  }
}
```

### 5.2.3 实施要求

1. 教师端接口保留“只能操作自己文件”的业务判断。
2. 管理端接口统一为 `jiaowu/admin`。
3. 上传文件属于教师端创建行为，不需要目标学生范围。

### 5.2.4 验收

- 教师只能看到自己上传的文件。
- 教师只能删除自己上传的文件。
- 教务/管理员能查看、下载、标记全部文件。
- 非教务不能访问管理端文件接口。

## 5.3 监考安排

### 5.3.1 范围

涉及后端：

- `lesson/models/datas_api/invigilation.py`

主要接口：

- 教师列表
- 考试项目 CRUD
- 监考安排 CRUD
- 交换教师
- 变更预览
- 发送通知
- 通知日志
- 下载模板
- 导入
- 导出
- 工作量报表

### 5.3.2 默认策略

```json
{
  "allowed_roles": ["jiaowu", "admin"],
  "min_level": 10,
  "data_scope_rules": {
    "jiaowu": ["all"],
    "admin": ["all"]
  },
  "operation_scope_rules": {
    "jiaowu": ["all"],
    "admin": ["all"]
  }
}
```

### 5.3.3 实施要求

1. 将 `require_jiaowu` 替换或包装为统一数据库权限依赖。
2. 不需要复杂班级/年级范围。
3. 导入、通知、删除等高影响操作必须有测试。

### 5.3.4 验收

- 教务/管理员可以操作全部监考安排。
- 非教务不能进入监考安排管理接口。
- 监考驾驶舱权限不被误改。

## 6. Phase 2：旧版请假

### 6.1 范围

涉及后端：

- `lesson/models/datas_api/legacy_attendance.py`

主要接口：

- 公开延时/请假提交或查询接口
- 班主任班级列表
- 请假记录创建
- 请假记录列表
- 请假记录核销
- 请假记录删除

### 6.2 默认策略

公开提交/查询类接口：

```json
{
  "is_public": 1,
  "allowed_roles": [],
  "min_level": 0
}
```

后台列表：

```json
{
  "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"],
  "min_level": 0,
  "data_scope_rules": {
    "admin": ["all"],
    "xuefa": ["all"],
    "g_leader": ["managed_grades"],
    "cleader": ["managed_classes"]
  }
}
```

后台操作：

```json
{
  "allowed_roles": ["admin", "xuefa", "g_leader", "cleader"],
  "min_level": 0,
  "operation_scope_rules": {
    "admin": ["all"],
    "xuefa": ["all"],
    "g_leader": ["managed_grades"],
    "cleader": ["managed_classes"]
  }
}
```

### 6.3 实施要求

1. 先确认哪些接口必须保持公开。
2. 公开接口显式写入数据库公开配置。
3. 列表与操作接口接入统一 API 鉴权。
4. 原班主任/年级主任范围判断先保留。
5. 新旧范围判断一致后，再考虑抽统一范围工具。

### 6.4 验收

- 班主任只能看和操作自己班级记录。
- 年级主任只能看和操作自己年级记录。
- 学发/管理员可看和操作全校记录。
- 公开提交入口行为不变。
- 无权限用户不能直接调用后台接口绕过前端。

## 7. Phase 3：旧版作业

### 7.1 范围

涉及后端：

- `lesson/models/datas_api/legacy_homework.py`

主要接口：

- 班级作业公开查看
- 班级公告公开查看
- 班级消息公开查看
- 发布作业
- 批量发布作业
- 修改作业
- 删除作业
- 发布公告
- 修改公告
- 删除公告

### 7.2 默认策略

公开查看：

```json
{
  "is_public": 1,
  "allowed_roles": [],
  "min_level": 0
}
```

发布：

```json
{
  "allowed_roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"],
  "min_level": 10
}
```

编辑/删除：

```json
{
  "allowed_roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"],
  "min_level": 10,
  "operation_scope_rules": {
    "teacher": ["own_created"],
    "cleader": ["own_created"],
    "g_leader": ["own_created"],
    "xuefa": ["own_created"],
    "jiaowu": ["own_created"],
    "admin": ["all"]
  }
}
```

### 7.3 实施要求

1. 先修正 update/delete 中用户依赖不统一的问题。
2. 写接口必须能拿到当前用户。
3. 作者字段映射为 `own_created`。
4. 不要把公开查看接口误改成登录接口。

### 7.4 验收

- 班级作业和公告公开查看不受影响。
- 未登录不能发布、修改、删除。
- 教师只能改/删自己发布的作业和公告。
- 管理员可改/删全部。

## 8. Phase 4：旧版课表

### 8.1 范围

涉及后端：

- `lesson/models/datas_api/legacy_schedule.py`

主要接口：

- 班级代码
- 班级课表
- 今日课表
- 总课表
- 节次
- 当前班级
- 教师个人课表
- 教师下周课表
- 上传课表

### 8.2 默认策略

公开查询：

```json
{
  "is_public": 1,
  "allowed_roles": [],
  "min_level": 0
}
```

上传课表：

```json
{
  "allowed_roles": ["jiaowu", "admin"],
  "min_level": 10,
  "operation_scope_rules": {
    "jiaowu": ["all"],
    "admin": ["all"]
  }
}
```

教师个人课表：

```json
{
  "allowed_roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"],
  "min_level": 10,
  "data_scope_rules": {
    "teacher": ["self"],
    "cleader": ["self"],
    "g_leader": ["self"],
    "xuefa": ["all"],
    "jiaowu": ["all"],
    "admin": ["all"]
  }
}
```

### 8.3 实施要求

1. 公开查询接口显式配置公开。
2. 上传接口强制 `jiaowu/admin`。
3. 教师个人课表保留“普通教师只能看本人”的对象级判断。
4. 教务/管理员可查看任意教师课表。

### 8.4 验收

- 原公开课表页面不被登录拦住。
- 非教务无法上传课表。
- 普通教师不能查看其他教师个人课表。
- 教务/管理员可查看所有教师课表。

## 9. Phase 5：moral 辅助接口巡检

### 9.1 分类

moral 辅助接口按以下类型处理：

| 类型 | 策略 |
| --- | --- |
| 权限配置页辅助接口 | admin-only |
| 菜单配置页辅助接口 | admin-only，当前用户菜单接口按登录用户放行 |
| 页面启动下拉 | 按页面允许角色配置 |
| 静态枚举 | 登录即可或公开 |
| 返回学生/班级/记录数据 | 必须跟主业务接口同数据范围 |
| 统计/详情辅助接口 | 必须跟主业务接口同数据范围 |

### 9.2 实施要求

1. 从前端页面实际请求链路出发。
2. 每个页面列出启动接口与操作接口。
3. 主接口允许某角色访问时，页面启动依赖接口不能遗漏该角色。
4. 辅助接口不能比主接口泄露更多数据。

### 9.3 重点页面

- 日常表现
- 点滴记录
- 一生一册
- 学生画像
- 评价查询
- API 权限配置
- 菜单权限配置
- 基础配置

### 9.4 验收

- 页面不会因为辅助接口 403 误报整页无权限。
- 辅助接口不能绕过主接口范围。
- 权限审计风险为 0，或仅剩明确豁免项。

## 10. Phase 6：收口

### 10.1 任务

1. 已迁移接口全部使用 `allow_missing=False`。
2. 未迁移接口必须明确标记：
   - `is_public=1`
   - 或 `enforce_backend=0`
   - 或旧鉴权保留
3. 更新权限配置文档。
4. 更新前端权限配置页面说明。
5. 权限审计中区分：
   - 预期公开
   - 预期旁路
   - 真实风险

### 10.2 验收

- 没有隐式放行业务接口。
- 没有未登记业务接口。
- 权限配置页能解释每个接口为什么放行或拒绝。
- 后端测试全量通过。
- 前端核心页面手工测试通过。

## 11. 推荐实施顺序

建议按 7 天节奏实施：

1. 第 1 天：Phase 0，完成接口盘点文档。
2. 第 2 天：Phase 1，迁教师管理、文件收集、监考安排。
3. 第 3 天：Phase 2，迁旧版请假。
4. 第 4 天：Phase 3，迁旧版作业。
5. 第 5 天：Phase 4，迁旧版课表。
6. 第 6 天：Phase 5，巡检 moral 辅助接口。
7. 第 7 天：Phase 6，全量测试、文档、权限审计收口。

如果风险较高，可以把 Phase 2 到 Phase 4 拆成多轮小 PR。

## 12. 测试要求

每个模块至少覆盖：

1. 允许角色能访问。
2. 非允许角色被拒绝。
3. 等级不足被拒绝。
4. 公开接口不需要登录。
5. 登录接口未登录返回 401。
6. 数据范围外记录不能查看。
7. 动作范围外记录不能编辑/删除。
8. 前端按钮显隐与后端一致。

## 13. 给实现 AI 的执行说明

请严格遵守：

1. 不要一次性迁移所有模块。
2. 每迁一个模块，先补默认权限配置，再改运行时依赖。
3. 公开接口必须显式公开。
4. 涉及记录的接口必须保留或补齐对象级校验。
5. 微信鉴权 `member.py/check_permission` 保留，不纳入本轮替换。
6. 每个阶段完成后运行对应测试和权限审计。
7. 不要删除旧业务判断，除非已有测试证明统一范围逻辑完全等价。

