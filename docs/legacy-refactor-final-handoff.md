# Legacy Refactor Final Handoff

## 版本信息

- 创建日期：2026-05-06
- 最后更新：Batch42 收尾
- 状态：✅ 架构复核完成，基线稳定

---

## 重构成果摘要

### 文件行数变化

| 文件 | 重构前 | 重构后 | 变化 |
|------|--------|--------|------|
| `datas_api_legacy.py` | ~1763 行 | 461 行 | -1302 行（降幅 74%） |

### 已拆分模块清单

| 模块 | 路由数 | 核心职责 |
|------|--------|---------|
| `legacy_tasks.py` | 4 | 任务管理（/tasks 相关） |
| `legacy_schedule.py` | 9 | 课程表、教师数据、时间表 |
| `legacy_homework.py` | 4 | 作业、公告、教师消息 |
| `legacy_students.py` | 6 | 学生信息、班级信息、导入导出 |
| `legacy_attendance.py` | 7 | 请假记录、迟到记录、审批 |
| `legacy_daily.py` | 3 | 日常记录 |
| `legacy_members.py` | 4 | 会员管理 |
| `legacy_permissions.py` | 4 | API 权限管理 |
| `legacy_parking.py` | 1 | 车辆进出记录 |

**累计拆分路由数**：42 个（不含 tasks 的 4 个）

---

## datas_api_legacy.py 当前职责

### 保留内容

1. **认证逻辑**（不得迁移）
   - `get_users_dict()` - 获取用户数据
   - `verify_password_compat()` - 密码验证兼容
   - `authenticate_user()` - 用户认证
   - `create_access_token()` - JWT 生成
   - `get_current_user()` - 获取当前用户
   - `check_api_permission()` - API 权限检查
   - `check_legacy_api_permission()` - legacy 任务权限兼容导出

2. **认证模型**（不得迁移）
   - `Token`, `TokenData`, `User`
   - `PasswordResetRequest`, `PasswordChangeRequest`
   - `TeacherCreate`, `TeacherUpdate`

3. **路由组装**
   - `router.include_router(schedule_router)`
   - `router.include_router(homework_router)`
   - `router.include_router(students_router)`
   - `router.include_router(attendance_router)`
   - `router.include_router(daily_router)`
   - `router.include_router(members_router)`
   - `router.include_router(permissions_router)`
   - `router.include_router(tasks_router)`
   - `router.include_router(parking_router)`

4. **兼容导出**（保持不变）
   - `TEACHER_MESSAGES`
   - `StudentInfoRequest`, `get_stu_dict`
   - `LeaveRecordRequest`
   - `DailyInfoRequest`
   - `MemberCreate`, `MemberUpdate`
   - `PermissionCreate`, `PermissionUpdate`
   - `check_legacy_api_permission`
   - Schedule 相关：`get_schedule_data_cached`, `get_teachers_data_cached`, `get_periods_cached`

### 不再包含

- **直接业务路由**：数量为 0
- **未使用导入**：已清理（shutil, json, numpy, math, io, sqlite3, File, UploadFile 等）
- **重复导入**：已清理

---

## 后续开发规则

### 新增 legacy 路由

**规则**：新增 legacy 路由应放入对应模块，不再塞回 `datas_api_legacy.py`。

| 路由类型 | 应放入模块 |
|---------|-----------|
| 课程表相关 | `legacy_schedule.py` |
| 作业/公告 | `legacy_homework.py` |
| 学生/班级 | `legacy_students.py` |
| 请假/迟到 | `legacy_attendance.py` |
| 日常记录 | `legacy_daily.py` |
| 会员管理 | `legacy_members.py` |
| 权限管理 | `legacy_permissions.py` |
| 任务管理 | `legacy_tasks.py` |
| 车辆进出 | `legacy_parking.py` |
| 其他新类型 | 新建 `legacy_xxx.py` 并 include |

### 模块模板

```python
# -*- coding: utf-8 -*-
"""Legacy XXX API - XXX 相关接口。

BatchNN: 从 datas_api_legacy.py 拆分 XXX 逻辑。
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


async def check_api_permission(request: Request):
    """复用 legacy YAML 权限检查，延迟导入避免循环依赖"""
    from models import datas_api_legacy
    return await datas_api_legacy.check_api_permission(request)


# ============================================================
# Routes
# ============================================================

@router.get("/xxx", dependencies=[Depends(check_api_permission)])
async def get_xxx():
    """获取 XXX"""
    ...


# ============================================================
# Models
# ============================================================

class XxxCreate(BaseModel):
    ...
```

### 挂载步骤

1. 在 `datas_api_legacy.py` 顶部添加：
   ```python
   from models.datas_api.legacy_xxx import router as xxx_router
   router.include_router(xxx_router)
   ```

2. 添加兼容导出（如果需要）：
   ```python
   from models.datas_api.legacy_xxx import XxxCreate, XxxUpdate
   ```

3. 创建 contract test：
   ```python
   # lesson/tests/test_datas_api_legacy_xxx_contract.py
   ```

---

## 验收命令清单

### 必跑命令

```bash
# 后端入口 contract test
python -m pytest lesson/tests/test_datas_api_legacy_entrypoint_contract.py -q

# 后端全量测试
python -m pytest -q

# 前端测试
npm run test:run

# 前端构建
npm run build
```

### 可选检查命令

```bash
# sqlite3.connect 集中度检查（应只有 sqlite_base.py）
rg "sqlite3\.connect" lesson/models -n

# raw_pwd 存量审计
python lesson/scripts/audit_raw_pwd.py
```

### 预期结果

| 命令 | 预期结果 | 说明 |
|------|---------|------|
| entrypoint contract | 9 passed | 入口行为锁定 |
| pytest -q | 551 passed | 后端全量测试通过 |
| npm test | 166 passed | 前端测试 |
| npm build | build success | 前端构建 |
| sqlite3.connect | 仅 sqlite_base.py | 集中度已达标 |
| raw_pwd audit | 2 changed, 63 unchanged | 2 条可清理 |

---

## raw_pwd 当前状态

### 存量统计

- 教师总数：65
- raw_pwd 非空：65
- 已改密且 raw_pwd 非空：2 条（应清理）
- 未改密且 raw_pwd 非空：63 条（保留兼容）

### 清理注意事项

**不要自动执行清理**。清理前需：
1. 确认用户已同意
2. 备份数据库
3. 执行：`python lesson/scripts/cleanup_raw_pwd.py --apply --yes`
4. 验证：登录测试（改密用户仍可登录）

---

## Contract Tests 覆盖矩阵

| Test File | 验证内容 |
|-----------|---------|
| `test_datas_api_legacy_entrypoint_contract.py` | 入口行为、导入清理、兼容导出 |
| `test_datas_api_legacy_parking_contract.py` | parking 路由、权限依赖 |
| `test_datas_api_legacy_permissions_contract.py` | permissions 路由、Member 上下文 |
| `test_datas_api_legacy_members_contract.py` | members 路由、Member 上下文 |
| `test_datas_api_legacy_daily_contract.py` | daily 路由、Daily 上下文 |
| `test_datas_api_legacy_attendance_contract.py` | attendance 路由、helper 函数 |
| `test_datas_api_legacy_students_contract.py` | students 路由、兼容导出 |
| `test_datas_api_legacy_homework_contract.py` | homework 路由、兼容导出 |
| `test_datas_api_legacy_schedule_contract.py` | schedule 路由、缓存函数 |

---

## 架构决策记录

### ADR-001: 延迟导入避免循环依赖

**背景**：legacy 模块需要 `check_api_permission`，但该函数在 `datas_api_legacy.py` 中定义。

**决策**：在 legacy 模块中创建 wrapper：
```python
async def check_api_permission(request: Request):
    from models import datas_api_legacy
    return await datas_api_legacy.check_api_permission(request)
```

**后果**：
- (+) 避免循环导入错误
- (+) 保持权限检查逻辑集中
- (-) 每次调用有额外 import（但 Python import cache 优化了这点）

### ADR-002: 保留认证逻辑在入口模块

**背景**：认证函数可拆分到独立模块。

**决策**：保留在 `datas_api_legacy.py`，不拆分。

**理由**：
- 认证是核心安全逻辑，集中管理更易审计
- 多处 legacy 模块依赖 `get_current_user`
- 拆分收益低（仅减少 ~150 行）

### ADR-003: 兼容导出保留

**背景**：旧代码可能从 `datas_api_legacy.py` 导入已迁移符号。

**决策**：保留兼容导入并 re-export。

**例子**：
```python
from models.datas_api.legacy_members import MemberCreate, MemberUpdate
```

**后果**：
- (+) 旧代码无需修改
- (+) 渐进式迁移
- (-) 入口模块仍有 re-export 噪音（但测试锁定）

---

## 附录：批次执行记录

批次主线摘要见 `docs/backend-refactor-notes.md`。该文件已精简为轻量索引，只有需要确认重构主线、红线、验收基线或下一阶段计划时才读取。

| Batch | 执行日期 | 核心内容 |
|-------|---------|---------|
| Batch32 | 2026-05-05 | tasks 模块拆分 |
| Batch33 | 2026-05-05 | schedule 模块拆分 |
| Batch34 | 2026-05-05 | homework 模块拆分 |
| Batch35 | 2026-05-06 | students 模块拆分 |
| Batch36 | 2026-05-06 | attendance 模块拆分 |
| Batch37 | 2026-05-06 | daily 模块拆分 |
| Batch38 | 2026-05-06 | members 模块拆分 |
| Batch39 | 2026-05-06 | permissions 模块拆分 |
| Batch40 | 2026-05-06 | parking 模块拆分 |
| Batch41 | 2026-05-06 | 入口瘦身（导入清理） |
| Batch42 | 2026-05-06 | 收尾复核与文档同步 |
