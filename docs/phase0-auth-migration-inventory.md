# Phase 0 盘点：教师管理、文件收集、监考安排鉴权状态

> 生成时间：2026-05-17
> 更新时间：2026-05-17
> 目标：记录 Phase 1 迁移前盘点与迁移后状态

## 0. 当前结论

教师管理、文件收集、监考安排已经完成 Phase 1 入口统一鉴权迁移：

1. 后端接口已使用 `require_configured_api_permission(..., allow_missing=False)`。
2. 默认权限配置已写入 `lesson/models/datas_api/moral/api_permission.py` 的 `DEFAULT_API_PERMISSIONS`。
3. 前端权限配置页已补齐 `teacher`、`filegather`、`invigilation` 三类资源的展示元数据。
4. 对象级业务判断仍按计划保留，例如教师管理写操作的 admin 判断、文件收集的本人文件判断。

下方“当前鉴权来源”保留迁移前盘点口径，供回溯使用；以本节结论为准。

## 1. 接口清单表

### 1.1 教师管理 (`/teachers`)

| 接口 | 路径 | 方法 | 当前鉴权来源 | 业务策略 |
|-----|------|------|-------------|---------|
| 获取教师列表 | `/teachers` | GET | `get_current_user` + 手写 admin 判断（`include_all` 参数） | 登录即可（默认）；admin 可看全部身份记录 |
| 创建教师 | `/teachers` | POST | `get_current_user` + `is_admin_user` | admin-only |
| 更新教师 | `/teachers/{username}` | PUT | `get_current_user` + `is_admin_user` | admin-only |
| 删除教师 | `/teachers/{username}` | DELETE | `get_current_user` + `is_admin_user` | admin-only |
| 获取任教班级 | `/teachers/{teacher_id}/teaching-classes` | GET | `get_current_user` + `is_admin_user` | admin-only |
| 更新任教班级 | `/teachers/{teacher_id}/teaching-classes` | PUT | `get_current_user` + `is_admin_user` | admin-only |
| 初始化任教班级 | `/teachers/init-teaching-classes` | POST | `get_current_user` + `is_admin_user` | admin-only |
| 修改密码 | `/teachers/change-password` | POST | `get_current_user` + 本人校验 | 仅本人操作（非 admin） |

**鉴权来源分类**：手写角色判断（`is_admin_user`）

**迁移后状态**：
- 已接入统一鉴权依赖 `require_configured_api_permission`。
- `/teachers` 因 GET/POST 同路径，数据库默认配置使用 `http_method='*'`。
- `include_all=1` 和写操作仍保留 admin 业务判断。

---

### 1.2 文件收集 (`/filegather`)

| 接口 | 路径 | 方法 | 当前鉴权来源 | 业务策略 |
|-----|------|------|-------------|---------|
| 上传文件 | `/filegather/upload` | POST | `get_current_user` | 登录即可，记录归属当前用户 |
| 获取我的文件 | `/filegather/my-files` | GET | `get_current_user` + 数据库查询限定 `username` | 仅本人数据 |
| 删除我的文件 | `/filegather/my-files/{file_id}` | DELETE | `get_current_user` + `db.delete_file` 内校验 | 仅本人数据（`delete_file` 内有校验） |
| 待处理文件列表 | `/filegather/admin/files` | GET | `get_current_user` + `is_jiaowu_user` | jiaowu/admin-only |
| 已完成文件列表 | `/filegather/admin/done-files` | GET | `get_current_user` + `is_jiaowu_user` | jiaowu/admin-only |
| 标记完成 | `/filegather/admin/mark-done/{file_id}` | POST | `get_current_user` + `is_jiaowu_user` | jiaowu/admin-only |
| 下载文件 | `/filegather/admin/download/{file_id}` | GET | `get_current_user` + `is_jiaowu_user` | jiaowu/admin-only |
| 统计信息 | `/filegather/admin/statistics` | GET | `get_current_user` + `is_jiaowu_user` | jiaowu/admin-only |
| 月份列表 | `/filegather/admin/months` | GET | `get_current_user` + `is_jiaowu_user` | jiaowu/admin-only |

**鉴权来源分类**：
- 教师端：`get_current_user` + 数据库限定
- 管理端：`is_jiaowu_user` 手写判断

**数据范围逻辑**：
- 教师端：`own_created`（数据库查询限定 `username=current_user.username`）
- 管理端：`all`（无数据范围限制）

**迁移后状态**：
- 已接入统一鉴权依赖 `require_configured_api_permission`。
- 教师端本人文件范围仍由查询和删除逻辑保护。
- 管理端 `jiaowu/admin` 由数据库配置控制。

---

### 1.3 监考安排 (`/invigilation`)

| 接口 | 路径 | 方法 | 当前鉴权来源 | 业务策略 |
|-----|------|------|-------------|---------|
| 教师列表 | `/invigilation/teachers` | GET | `require_jiaowu` | jiaowu/admin-only |
| 考试项目列表 | `/invigilation/projects` | GET | `require_jiaowu` | jiaowu/admin-only |
| 创建考试项目 | `/invigilation/projects` | POST | `require_jiaowu` | jiaowu/admin-only |
| 获取考试项目详情 | `/invigilation/projects/{project_id}` | GET | `require_jiaowu` | jiaowu/admin-only |
| 更新考试项目 | `/invigilation/projects/{project_id}` | PUT | `require_jiaowu` | jiaowu/admin-only |
| 删除考试项目 | `/invigilation/projects/{project_id}` | DELETE | `require_jiaowu` | jiaowu/admin-only |
| 获取监考安排列表 | `/invigilation/projects/{project_id}/slots` | GET | `require_jiaowu` | jiaowu/admin-only |
| 批量保存监考安排 | `/invigilation/projects/{project_id}/slots` | PUT | `require_jiaowu` | jiaowu/admin-only |
| 交换监考老师 | `/invigilation/projects/{project_id}/slots/swap-teachers` | POST | `require_jiaowu` | jiaowu/admin-only |
| 变更预览 | `/invigilation/projects/{project_id}/changes` | GET | `require_jiaowu` | jiaowu/admin-only |
| 发送监考通知 | `/invigilation/projects/{project_id}/notify` | POST | `require_jiaowu` | jiaowu/admin-only |
| 通知日志 | `/invigilation/projects/{project_id}/notification-logs` | GET | `require_jiaowu` | jiaowu/admin-only |
| 下载模板 | `/invigilation/template` | GET | `require_jiaowu` | jiaowu/admin-only |
| 导入监考安排 | `/invigilation/projects/{project_id}/import` | POST | `require_jiaowu` | jiaowu/admin-only |
| 导出监考安排 | `/invigilation/projects/{project_id}/export` | GET | `require_jiaowu` | jiaowu/admin-only |
| 工作量报表 | `/invigilation/projects/{project_id}/report` | GET | `require_jiaowu` | jiaowu/admin-only |

**鉴权来源分类**：`require_jiaowu`（模块内包装依赖）

**迁移后状态**：
- 已接入统一鉴权依赖 `require_configured_api_permission`。
- 所有接口都是 `jiaowu/admin`，无学生数据范围区分。
- 旧 `require_jiaowu` 函数暂留，但当前路由已不再依赖它。

---

## 2. 当前鉴权来源统计

| 鉴权来源 | 教师管理 | 文件收集 | 监考安排 | 说明 |
|---------|:-------:|:-------:|:-------:|-----|
| `require_configured_api_permission` | 8 | 9 | 16 | **统一鉴权依赖（当前）** |
| `get_current_user` + 手写判断 | 0 | 0 | 0 | 迁移前主要方式，已替换入口依赖 |
| `require_jiaowu`（模块内） | 0 | 0 | 0 | 函数暂留，当前路由未使用 |
| `is_jiaowu_user`（模块内） | 0 | 0 | 0 | 函数暂留，当前管理端路由未使用 |
| 无鉴权 | 0 | 0 | 0 | 无 |

---

## 3. 公开接口清单

| 模块 | 公开接口 | 当前状态 | 迁移后状态 |
|-----|---------|---------|-----------|
| 教师管理 | 无 | 无公开接口 | 无公开接口 |
| 文件收集 | 无 | 无公开接口 | 无公开接口 |
| 监考安排 | 无 | 无公开接口 | 无公开接口 |

**结论**：三个模块均无公开接口，迁移后无需配置 `is_public=1`。

---

## 4. 数据范围接口清单

| 模块 | 接口 | 数据范围类型 | 当前实现方式 |
|-----|------|-------------|-------------|
| 教师管理 | `/teachers` GET | `teacher_directory` | 返回教师通讯录；`include_all=1` 仍由 admin 代码判断 |
| 教师管理 | `/teachers` POST、`/teachers/{username}`、任教班级维护 | `all_teachers` | 数据库配置表达全校教师对象，代码仍要求 admin |
| 教师管理 | `/teachers/change-password` | `self` | 代码内校验本人改密 |
| 文件收集 | `/filegather/upload` | `own_uploaded` | 插入记录时写入 `current_user.username` |
| 文件收集 | `/filegather/my-files` | `own_uploaded` | 数据库查询限定 `username` |
| 文件收集 | `/filegather/my-files/{file_id}` | `own_uploaded` | `delete_file` 内校验上传者 |
| 文件收集 | `/filegather/admin/*` | `all_files` | 管理端处理全部上传文件 |
| 监考安排 | 全部接口 | `all_projects` | 当前监考项目不按学生/班级/年级拆分 |

**结论**：
- 教师管理：改密接口需保留"本人操作"校验
- 文件收集：教师端需保留 `own_uploaded` 业务判断；管理端为 `all_files`
- 监考安排：全部为 `all_projects`，无学生数据范围

---

## 5. 风险列表

| # | 模块 | 接口 | 风险描述 | 严重程度 | 迁移建议 |
|---|-----|------|---------|:-------:|---------|
| 1 | 教师管理 | `/teachers` GET/POST | 同路径多方法受 `api_path` 唯一约束影响，只能配置 `http_method='*'` | 中 | 后续可升级唯一键为 `(api_path, http_method)` |
| 2 | 教师管理 | `/teachers/change-password` | 本人校验仍依赖代码 | 低 | 保留对象级判断，后续可抽统一 self helper |
| 3 | 文件收集 | `/filegather/my-files` | 数据范围校验在数据库查询内，不统一 | 低 | 保留业务判断，后续可抽统一 own_created helper |
| 4 | 文件收集 | `/filegather/admin/*` | 已由数据库配置控制 | 已处理 | 持续通过权限风险扫描验证 |
| 5 | 监考安排 | 全部 | 已由数据库配置控制 | 已处理 | 持续通过权限风险扫描验证 |
| 6 | 全部 | - | 默认配置已补齐 | 已处理 | 新增接口仍需同步 `DEFAULT_API_PERMISSIONS` |

---

## 6. 迁移策略

### 6.1 教师管理

```json
// 管理类接口默认配置
{
  "api_path": "/teachers",
  "http_method": "POST|PUT|DELETE",
  "allowed_roles": ["admin"],
  "min_level": 100,
  "resource_type": "teacher",
  "operation_scope_rules": {
    "admin": ["all"]
  },
  "enforce_backend": 1
}

// 改密接口配置
{
  "api_path": "/teachers/change-password",
  "http_method": "POST",
  "allowed_roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu"],
  "min_level": 10,
  "resource_type": "teacher",
  "operation_scope_rules": {
    "teacher": ["self"],
    "cleader": ["self"],
    "g_leader": ["self"],
    "xuefa": ["self"],
    "jiaowu": ["self"]
  },
  "enforce_backend": 1
}
```

### 6.2 文件收集

```json
// 教师端接口
{
  "api_path": "/filegather/upload|my-files",
  "http_method": "*",
  "allowed_roles": ["teacher", "cleader", "g_leader", "xuefa", "jiaowu", "admin"],
  "min_level": 10,
  "resource_type": "filegather",
  "data_scope_rules": {
    "teacher": ["own_uploaded"],
    "cleader": ["own_uploaded"],
    "g_leader": ["own_uploaded"],
    "xuefa": ["own_uploaded"],
    "jiaowu": ["own_uploaded"],
    "admin": ["own_uploaded"]
  },
  "operation_scope_rules": {
    "teacher": ["own_uploaded"],
    "cleader": ["own_uploaded"],
    "g_leader": ["own_uploaded"],
    "xuefa": ["own_uploaded"],
    "jiaowu": ["own_uploaded"],
    "admin": ["own_uploaded"]
  },
  "enforce_backend": 1
}

// 管理端接口
{
  "api_path": "/filegather/admin/*",
  "http_method": "*",
  "allowed_roles": ["jiaowu", "admin"],
  "min_level": 10,
  "resource_type": "filegather",
  "data_scope_rules": {
    "jiaowu": ["all_files"],
    "admin": ["all_files"]
  },
  "operation_scope_rules": {
    "jiaowu": ["all_files"],
    "admin": ["all_files"]
  },
  "enforce_backend": 1
}
```

### 6.3 监考安排

```json
// 全部接口
{
  "api_path": "/invigilation/*",
  "http_method": "*",
  "allowed_roles": ["jiaowu", "admin"],
  "min_level": 10,
  "resource_type": "invigilation",
  "data_scope_rules": {
    "jiaowu": ["all_projects"],
    "admin": ["all_projects"]
  },
  "operation_scope_rules": {
    "jiaowu": ["all_projects"],
    "admin": ["all_projects"]
  },
  "enforce_backend": 1
}
```

---

## 7. 数据库当前状态

```sql
-- 当前状态：三个模块的默认配置已写入 DEFAULT_API_PERMISSIONS。
-- ensure_api_permission_schema(db) 会同步到 api_permission_config。
-- 已迁移路由使用 allow_missing=False，缺失配置会直接拒绝。
```

---

## 8. 验收标准

- [x] 所有接口都有明确的迁移分类
- [x] 公开接口、登录接口、管理接口分类清晰
- [x] 数据范围接口清单完整
- [x] 风险列表标注严重程度
- [x] 迁移策略 JSON 配置已进入默认配置
- [x] 现有页面行为保持兼容
