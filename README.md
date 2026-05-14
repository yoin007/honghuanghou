# 鸿荒侯班级管理系统

本仓库包含一个以 FastAPI + Vue 3 为核心的校园管理系统，主要覆盖：

- 德育记录、处分、任务、画像、AI 诊疗、一生一册
- 数据驾驶舱、班级/年级趋势分析
- 教师、班级、学生、学年学期等基础配置
- 基于数据库动态配置的 API 权限、数据范围、目标范围与动作范围

## 目录

- `lesson/`：后端服务与测试
- `frontend/`：前端应用
- `docs/`：系统方案、架构、运维和交接文档
- `lesson/databases/`：SQLite 数据库文件

## 当前鉴权结论

截至 2026-05-13：

- 统一权限配置已落库，可通过前端 `moral/config/api-permission` 修改。
- 当前权限巡检结果为 `174` 条 API、`0` 条风险。
- 后端全量测试 `608 passed`。

权限体系说明优先阅读：

- `docs/auth-system-blueprint.md`
- `docs/auth-frontend-adaptation-plan.md`
- `docs/unified-permission-optimization-plan.md`

## 文档入口

完整文档索引见：

- `docs/README.md`

## 维护约定

- 数据库：SQLite
- 分支：`feature/* -> develop -> main`
- 提交：`feat:`、`fix:`、`refactor:`、`docs:`、`chore:`
- Python 遵循 PEP 8，前端遵循 ESLint 约定
