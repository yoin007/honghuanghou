# 文档目录

本目录保留当前仍有维护价值的系统文档。历史方案稿已经合并到统一说明中，避免同一主题在多份文档里重复维护。

| 文档 | 用途 |
|------|------|
| [project-optimization-upgrade-plan.md](project-optimization-upgrade-plan.md) | 文档整合入口，汇总当前系统架构、代码审阅发现和优化升级路线图 |
| [ai-refactor-execution-playbook.md](ai-refactor-execution-playbook.md) | 面向其他 AI 工具的重构执行手册，包含批次、验收、重复函数合并规则和 Codex 复核流程 |
| [function-level-audit-and-refactor-plan.md](function-level-audit-and-refactor-plan.md) | 函数级全量审计后的重构升级方案，按功能域说明保留要求、拆分方向和验收办法 |
| [function-inventory.md](function-inventory.md) | 函数级全量清单，覆盖后端 Python 和前端 JS/Vue 审计单元，用于重构防遗漏 |
| [system-architecture.md](system-architecture.md) | 当前系统功能、API、页面、角色权限、数据库和测试状态总览 |
| [moral-evaluation-system.md](moral-evaluation-system.md) | 德育评价系统的业务规则、SQLite 数据模型、API 和实施要点 |
| [moral-config-guide.md](moral-config-guide.md) | 德育配置后台的操作手册，面向系统管理员和业务配置人员 |
| [data-dashboard-implementation-plan.md](data-dashboard-implementation-plan.md) | 全系统数据驾驶舱建设方案，覆盖角色视图、指标、图表和分阶段落地 |
| [invigilation-arrangement-implementation-plan.md](invigilation-arrangement-implementation-plan.md) | 监考安排功能方案，覆盖数据模型、导入导出、通知和 API 设计 |
| [database-consolidation-report.md](database-consolidation-report.md) | `lesson/databases` 多库梳理与教师主表合并记录 |
| [nginx-https-config.md](nginx-https-config.md) | Nginx HTTPS 反向代理和重定向配置说明 |

## 推荐阅读顺序

1. 先读 [project-optimization-upgrade-plan.md](project-optimization-upgrade-plan.md)，了解项目现状和升级路线。
2. 需要让其他 AI 执行重构时，直接使用 [ai-refactor-execution-playbook.md](ai-refactor-execution-playbook.md)。
3. 需要做函数级核对时，读 [function-level-audit-and-refactor-plan.md](function-level-audit-and-refactor-plan.md)，并用 [function-inventory.md](function-inventory.md) 防止遗漏函数和功能。
4. 再读 [system-architecture.md](system-architecture.md)，查看当前 API、页面、角色和数据库总览。
5. 德育相关读 [moral-evaluation-system.md](moral-evaluation-system.md) 和 [moral-config-guide.md](moral-config-guide.md)。
6. 监考、驾驶舱、数据库合并和 HTTPS 部署按专题阅读对应文档。

## 整理记录

- 2026-05-02：新增 `project-optimization-upgrade-plan.md`，整合 docs 现有文档定位和本次代码审阅后的优化升级方案。
- 2026-05-02：新增 `function-inventory.md` 和 `function-level-audit-and-refactor-plan.md`，将函数级全量审计结果固化为重构防遗漏台账和详细重构方案。
- 2026-05-02：新增 `ai-refactor-execution-playbook.md`，明确其他 AI 工具的执行批次、重复函数合并规则和 Codex 复核流程。
- 已合并并删除历史草案：
  - `德育评价系统设计方案.md`
  - `德育评价系统合并方案.md`
  - `德育评价系统合并实施计划.md`
- 德育相关长期维护内容统一放入 `moral-evaluation-system.md`。
- 具体配置操作仍保留在 `moral-config-guide.md`，避免把用户手册和系统设计混在一起。
