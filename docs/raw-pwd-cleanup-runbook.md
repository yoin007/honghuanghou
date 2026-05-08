# raw_pwd 清理执行手册

## 版本信息

- 创建日期：2026-05-03
- 适用批次：Batch 8-9，Batch43 复核更新，Batch44 执行完成
- 用途：人工执行 raw_pwd 清理的标准流程

---

## 概述

本手册指导人工执行 `raw_pwd` 明文密码清理。清理是不可逆操作，需要严格按照流程执行。

**安全原则**：
- 默认 dry-run，必须双重确认才能执行
- 自动备份，提供恢复命令
- 只清理已改密账号（is_password_changed=1）
- 不清理未改密账号（is_password_changed=0）

---

## 执行历史

### Batch44 执行记录（2026-05-07）

**执行时间**：2026-05-07 08:46:07
**执行命令**：`python lesson/scripts/cleanup_raw_pwd.py --apply --yes`
**人工确认**：2026-05-07 事后补录确认；用户已确认所有清理结果、备份信息、恢复命令、备份保留和后续改密事项。

**清理结果**：
| 指标 | 清理前 | 清理后 |
|------|--------|--------|
| changed=1 且 raw_pwd 非空 | 2 | 0 ✅ |
| changed=0 且 raw_pwd 非空 | 63 | 63 ✅ |

**备份路径**：`/Users/yoin/bdsync/program/honghuanghou/lesson/databases/moral.db.raw_pwd_backup.20260507_084607`

**恢复命令**：
```bash
cp /Users/yoin/bdsync/program/honghuanghou/lesson/databases/moral.db.raw_pwd_backup.20260507_084607 /Users/yoin/bdsync/program/honghuanghou/lesson/databases/moral.db
```

**测试结果**：69 个 raw_pwd/auth 定向测试通过；全量后端测试 554 passed。

---

## 当前数据库状态

**审计时间**：2026-05-07（清理后）

| 指标 | 数量 | 说明 |
|------|------|------|
| teacher_total | 65 | 教师总数 |
| raw_pwd_non_empty | 63 | 存储明文密码的数量 |
| changed_with_raw_pwd | 0 | **已清理** ✅ |
| unchanged_with_raw_pwd | 63 | **不可清理**：未改密，依赖明文验证 |

---

## 执行流程

### Step 1: dry-run 验证

```bash
cd /Users/yoin/bdsync/program/honghuanghou
python lesson/scripts/cleanup_raw_pwd.py
```

**预期输出**：
```
============================================================
raw_pwd 清理报告
============================================================
模式: dry-run

数据库状态: 存在 ✅

----------------------------------------
统计结果:
----------------------------------------
可清理候选数量:        2
不可清理数量 (changed=0): 63

🔍 dry-run 模式：以下记录可清理（不显示明文）
   - teacher_id_1
   - teacher_id_2

⚠️  dry-run 不修改数据库
   如需执行清理，请使用: --apply --yes
============================================================
```

**检查点**：
- `可清理候选数量` 是否符合预期（当前应为 2）
- `不可清理数量` 是否有值（当前应为 63，这些不会被清理）

---

### Step 2: 确认执行时机

**确认条件**：
1. 业务方已知晓清理影响
2. 确认 2 条已改密账号不再需要明文密码
3. 确认 63 条未改密账号的明文验证能力不受影响

**不建议执行的场景**：
- 有用户报告登录问题
- 近期有大量用户需要首次登录
- 系统处于高负载时期

---

### Step 3: 执行清理（需人工确认）

```bash
python lesson/scripts/cleanup_raw_pwd.py --apply --yes
```

**必须同时传入 `--apply` 和 `--yes`**：
- 只传 `--apply` 不传 `--yes`：返回提示，不执行
- 同时传入：执行清理，创建备份

**预期输出**：
```
============================================================
raw_pwd 清理报告
============================================================
模式: apply

数据库状态: 存在 ✅

----------------------------------------
统计结果:
----------------------------------------
可清理候选数量:        2
不可清理数量 (changed=0): 63

----------------------------------------
执行结果:
----------------------------------------
备份路径:              lesson/databases/moral.db.raw_pwd_backup.20260503_XXXXXX
恢复命令:              cp lesson/databases/moral.db.raw_pwd_backup.XXXXXX lesson/databases/moral.db
实际清理数量:          2
清理后剩余可清理数量:  0
未清理数量 (changed=0): 63

✅ 清理完成
   已清理 teacher_id: 2 条

如需恢复，执行:
   cp lesson/databases/moral.db.raw_pwd_backup.XXXXXX lesson/databases/moral.db
============================================================
```

**关键信息**：
- **备份路径**：自动创建的备份文件位置
- **恢复命令**：用于回滚的完整命令（复制保存）

---

### Step 4: 验证清理结果

```bash
python lesson/scripts/audit_raw_pwd.py
```

**预期输出**：
```
============================================================
raw_pwd 存量审计报告
============================================================
...
统计结果:
----------------------------------------
教师总数:                    65
raw_pwd 非空数量:            63

按 is_password_changed 分组:
  changed=1 且 raw_pwd 非空: 0 (应清理) ← 验证已变为 0
  changed=0 且 raw_pwd 非空: 63 (保留兼容)
  changed=1 且 raw_pwd 为空: 2 (正常)
  changed=0 且 raw_pwd 为空: 0 (正常)

✅ 无 raw_pwd 明文存储（已改密账号），安全状态良好
============================================================
```

**验证点**：
- `changed=1 且 raw_pwd 非空` 从 2 变为 0 ✅
- `changed=0 且 raw_pwd 非空` 保持 63 ✅

---

### Step 5: 功能验证

**建议测试**：
1. 已改密账号登录正常（使用 hash 验证）
2. 未改密账号登录正常（使用明文验证）

---

## 恢复流程

如果清理后发现问题，使用备份恢复。

### 查找备份文件

备份文件命名格式：`moral.db.raw_pwd_backup.YYYYMMDD_HHMMSS`

```bash
ls lesson/databases/*.raw_pwd_backup.*
```

### 执行恢复

使用清理报告中的 `恢复命令`：

```bash
cp lesson/databases/moral.db.raw_pwd_backup.20260503_XXXXXX lesson/databases/moral.db
```

### 验证恢复

```bash
python lesson/scripts/audit_raw_pwd.py
# 验证 changed=1 且 raw_pwd 非空 恢复为 2
```

---

## 常见问题

### Q: 只传 --apply 没传 --yes 会怎样？

返回提示，不修改数据库：

```
⚠️  apply 模式需要确认
   可清理记录数: 2

⚠️  未添加 --yes 参数，不执行清理
   如需执行，请添加: --yes
```

### Q: 备份文件可以删除吗？

建议保留 7 天。清理后若无问题，可删除备份。

### Q: 为什么不清理 is_password_changed=0 的账号？

这些账号未改密，依赖明文密码验证。清理会导致无法登录。

### Q: 清理后用户无法登录怎么办？

执行恢复命令，然后检查密码验证逻辑。

---

## 附录：脚本参数说明

### cleanup_raw_pwd.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--db-path` | 数据库路径 | `lesson/databases/moral.db` |
| `--apply` | 执行清理（需配合 --yes） | False（dry-run） |
| `--yes` | 确认执行 | False |
| `--backup-dir` | 备份目录 | 数据库同目录 |

### audit_raw_pwd.py

当前审计脚本使用默认数据库路径。需要审计临时库时，请在测试或 Python 调用中传入 `audit_raw_pwd_status(db_path)`。

---

## 注意事项

- **不要对真实数据库运行 --apply --yes，除非经过人工确认**
- **不要删除 raw_pwd 字段**（长期任务，等所有用户改密后）
- **不要清理 is_password_changed=0 的记录**
- **不要删除备份文件**（至少保留 7 天）

---

## 后续退场路径（Batch45 规划）

### 当前状态

| 分组 | 数量 | 状态 |
|------|------|------|
| changed=1 且 raw_pwd 非空 | 0 | ✅ 已清理 |
| changed=0 且 raw_pwd 非空 | 63 | ⏸️ 保留兼容 |

### 四阶段退场计划

| 阶段 | 目标 | 操作 | 触发条件 |
|------|------|------|---------|
| 阶段1 | 推动改密 | 用户改密时设置 `is_password_changed=1`，`pwd` 存储 hash | 业务推动 |
| 阶段2 | 定期审计 | 运行 `audit_raw_pwd.py` 监控 `changed=0 且 raw_pwd 非空` 数量 | 每月执行 |
| 阶段3 | 批量清理 | `cleanup_raw_pwd.py --apply --yes` 清理剩余 raw_pwd | `changed=0 且 raw_pwd 非空` = 0 |
| 阶段4 | 字段删除 | 删除 teacher 表 raw_pwd 字段（需独立 batch） | 全部用户改密完成 |

### 阶段约束

- ⚠️ **阶段1-2 不删除 raw_pwd 字段**
- ⚠️ **阶段3 不清理 changed=0 的 raw_pwd**（等全部改密）
- ⚠️ **阶段4 需同步修改**：teacher 表结构、UPSERT 逻辑、迁移脚本、测试

### 定期审计命令

```bash
# 每月执行
cd /Users/yoin/bdsync/program/honghuanghou
python lesson/scripts/audit_raw_pwd.py

# 监控指标
# changed=0 且 raw_pwd 非空: 63 → 0（目标）
```

### 预计时间线

| 时间节点 | 预期状态 | 说明 |
|---------|---------|------|
| 2026-06 | 63 条未改密 | 开始推动改密 |
| 2026-12 | <30 条未改密 | 持续推动 |
| 2027-06 | 0 条未改密 | 可执行阶段3 |
| 2027-12 | 字段删除 | 可执行阶段4（可选） |

---
- **不要修改前端代码**（本批次不改前端）
