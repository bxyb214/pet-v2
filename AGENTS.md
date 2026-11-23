# AGENTS.md — Agent 工作规范（入口）

本仓库由 AI Agent 参与开发。开工前先读本文件与 [docs/README](docs/README.md)，再读 `docs/01~05`。

## 必读文档

| 文档 | 用途 |
|---|---|
| [docs/01-需求清单.md](docs/01-需求清单.md) | 需求基线（**v1.0 已冻结，2026-11-22**；决议不重开） |
| [docs/02-技术架构.md](docs/02-技术架构.md) | 选型、仓库结构、API、数据模型、同步 |
| [docs/03-Agent技术规范.md](docs/03-Agent技术规范.md) | 七阶段工作流与 DoD（**强制**） |
| [docs/04-功能清单.md](docs/04-功能清单.md) | 功能编号与验收口径 |
| [docs/05-前端设计规范.md](docs/05-前端设计规范.md) | 「绿野成长」Token 与组件模式（UI 硬约束） |
| [docs/06-部署与运维.md](docs/06-部署与运维.md) | 本地 / NAS 部署、备份、迁移 |
| [docs/07-口语实时对话方案.md](docs/07-口语实时对话方案.md) | 口语 AI 设计 |

## 已冻结决议（不得重开讨论）

- 前端 Vue 3 + Vite + TypeScript；数据库 SQLite(WAL)；JWT 认证；邀请码注册。
- 迁移旧 MySQL 数据与媒体；旧站 `ai.wizoom.net/PET` 暂不下线；Qwen Key 经管理页配置，不进 git。
- 多学科预留，首版只实现英语（PET / KET）。

## 红线（违反即 FAIL）

- 同步合并语义不得擅改：mastery/mistakes 并集、progress seen 并集+idx 取大、plan 并集、409 冲突合并重试。
- 错题本维度记账规则不得擅改：答错全维度重欠、答对划单维、dims 空自动移出、不可手动删除。
- 密钥只从环境变量/外部配置读取，禁止入库入 git。
- 新依赖必须经设计文档说明后引入。
- 完成前必须产出 `99-self-review.md` 且结论非 FAIL。

## 工作流（详见 docs/03）

```text
01 需求 → 02 设计 → 实现 → 测试 → 依赖 → 部署 → 99 自省
产物：docs/dev/{feature}/{01-requirements,02-design,99-self-review}.md
多步迭代用 -step2 后缀；功能文档完成后保留，不删除。
```

## 环境约定

- 目标部署：飞牛 NAS Docker（nginx + FastAPI + SQLite），见 [docs/06](docs/06-部署与运维.md)。
- Monorepo：`frontend/`（Vue 3）、`backend/`（FastAPI）、`data-src/`（学习数据源）、`tools/`（构建/迁移）。
- 媒体文件沿用 ASCII slug 命名；音频/图片与数据库不进 git。
- 旧站参考代码在上级目录 `../PET/`，只读。
