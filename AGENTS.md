# AGENTS.md — PET v2 仓库 Agent 工作规范（入口）

本仓库由 AI Agent 参与开发。开始任何工作前，先读完本文件与 `docs/` 三份文档。

## 必读文档

1. `docs/01-需求清单.md` — 需求基线（**v1.0 已确认冻结，2026-11-22**）
2. `docs/02-技术架构.md` — 选型、API 设计、数据模型、部署
3. `docs/03-Agent技术规范.md` — 七阶段工作流与各阶段 DoD（**强制执行**）
4. `docs/04-功能清单.md` — 功能编号清单（v0.1 待用户标注修正，修正后冻结）
5. `docs/05-前端设计规范.md` — 「绿野成长」设计 token 与组件模式（AI 生成 UI 的硬约束）

## 已冻结决议（不得重开讨论）

- 前端 Vue 3 + Vite + TypeScript；数据库 SQLite(WAL)；JWT 认证；邀请码注册。
- 需迁移旧 MySQL 数据与媒体文件；旧站 ai.wizoom.net/PET 暂不下线；Qwen Key 走 NAS 环境变量。

## 红线（违反即 FAIL）

- 同步合并语义不得擅改：mastery/mistakes 并集、progress seen 并集+idx 取大、plan 并集、409 冲突合并重试。
- 错题本维度记账规则不得擅改：答错全维度重欠、答对划单维、dims 空自动移出、不可手动删除。
- 密钥只从环境变量/外部配置读取，禁止入库入 git。
- 新依赖必须经设计文档说明后引入。
- 完成前必须产出 `99-self-review.md` 且结论非 FAIL。

## 环境约定

- 目标部署：飞牛 NAS Docker（nginx + fastapi + sqlite），详见架构文档 §6。
- 仓库 monorepo：`frontend/`（Vue3+Vite+TS）、`backend/`（FastAPI）、`data-src/`（学习数据源）、`tools/`（构建/迁移脚本）。
- 媒体文件（音频/图片）沿用 ASCII slug 命名。
- 旧站参考代码在上级目录 `../PET/`（只读参考，勿直接改动）。
