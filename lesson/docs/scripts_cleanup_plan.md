# scripts 目录 sqlite3.connect 清理方案

## 现状分析

### 路径定义方式不一致
- **DB_PATH 常量**（3个脚本）：
  - `generate_moral_test_data.py` - SCRIPT_DIR
  - `verify_invigilation_system.py` - SCRIPT_DIR
  - `create_invigilation_tables.py` - __file__

- **LESSON_DIR/DB_DIR inline**（5个脚本）：
  - `audit_raw_pwd.py` - LESSON_DIR
  - `cleanup_raw_pwd.py` - LESSON_DIR
  - `clear_moral_tables.py` - DB_DIR
  - `init_databases.py` - DB_DIR
  - `verify_moral_system.py` - LESSON_DIR

- **统一导入**（1个脚本，但有错误）：
  - `remove_daily_record_unique_constraint.py` - `from utils.sqlite_moral_db import DB_PATH`（错误：DB_PATH 不存在）

- **一次性迁移脚本**（3个，可能保留 inline）：
  - `create_moral_tables.py` - 可能 inline
  - `migrate_mysql_to_sqlite.py` - 可能 inline
  - `migrate_to_mysql.py` - 可能 inline

### utils 目录配置文件
- `utils/db_config.py` - 定义所有 DB 常量（AUTH_DB, TASK_DB, MORAL_DB, etc.)
- `utils/sqlite_moral_db.py` - 导入 db_config.MORAL_DB，提供 MoralDatabase 类

### 风险点
1. **环境差异**：SCRIPT_DIR/__file__/LESSON_DIR 计算结果在不同运行环境下可能不一致
2. **维护成本**：新增 DB 需修改多处硬编码，违反 DRY 原则
3. **导入错误**：`remove_daily_record_unique_constraint.py` 导入不存在 DB_PATH（需修复为 MORAL_DB）

## 迁移方案

### Batch80：修复导入错误 + 迁移常用脚本
**目标**：修复 remove_daily_record_unique_constraint.py 导入错误，迁移 5 个常用脚本到统一导入

**迁移脚本列表**：
1. `remove_daily_record_unique_constraint.py` - 修复导入（DB_PATH → MORAL_DB）
2. `generate_moral_test_data.py` - 迁移到 `from utils.db_config import MORAL_DB`
3. `verify_invigilation_system.py` - 迁移到 `from utils.db_config import INVIGILATION_DB`
4. `create_invigilation_tables.py` - 迁移到 `from utils.db_config import INVIGILATION_DB`
5. `audit_raw_pwd.py` - 迁移到 `from utils.db_config import MORAL_DB`
6. `cleanup_raw_pwd.py` - 迁移到 `from utils.db_config import MORAL_DB`

**保留 inline 的脚本**：
- `init_databases.py` - 初始化所有 DB，需要动态配置，保留 DB_DIR
- `clear_moral_tables.py` - 清空表，保留 DB_DIR
- `verify_moral_system.py` - 验证系统，保留 LESSON_DIR
- 一次性迁移脚本（create_moral_tables.py, migrate_*.py）

### Batch81：清理 scripts 目录遗留 DB_PATH 定义
**目标**：删除迁移后脚本的 DB_PATH 常量定义，验证脚本正常运行

**步骤**：
1. 删除已迁移脚本的 DB_PATH/LESSON_DIR/MORAL_DB 常量定义
2. 验证脚本导入正确
3. 运行关键脚本测试（不修改数据库）

### 验证标准
- 所有迁移脚本导入成功（无 ImportError）
- scripts 目录硬编码路径减少 50%+
- 关键脚本运行测试通过（dry-run 模式）

## 执行计划

### Batch80（1批次）
- 修复 remove_daily_record_unique_constraint.py 导入错误
- 迁移 5 个常用脚本到 utils.db_config 导入
- 测试导入正确性

### Batch81（1批次）
- 清理迁移脚本的常量定义
- 全量验证（pytest + 关键脚本 dry-run）

## 颗粒度说明
每个批次包含：
1. 代码修改（Edit 工具）
2. 导入测试（Bash python -c）
3. 扫描验证（Grep 统计）
4. 契约测试（确保无破坏）

总共 2 批次，符合用户预估的 1-2 batches。