# AGENTS.md — Agent 工作规范（入口）

本仓库由 AI Agent 参与开发。开工前先读本文件与 [docs/README](docs/README.md)，
再按需读 `docs/01`、`02`、`03`；站点已基本完成，文档以当前有效信息为准。

## 必读文档

| 文档 | 用途 |
|---|---|
| [docs/01-需求清单.md](docs/01-需求清单.md) | 需求基线（**v1.0 已冻结**；决议不重开） |
| [docs/02-技术架构.md](docs/02-技术架构.md) | 选型、仓库结构、API、数据模型、同步 |
| [docs/03-开发规范.md](docs/03-开发规范.md) | 改动流程、分层与代码约束、测试、红线 |
| [docs/04-功能清单.md](docs/04-功能清单.md) | 功能编号与当前能力 |
| [docs/05-前端设计规范.md](docs/05-前端设计规范.md) | 「绿野成长」Token 与组件模式（UI 硬约束） |
| [docs/06-部署与运维.md](docs/06-部署与运维.md) | 本地 / NAS 部署、备份、迁移 |
| [docs/07-口语实时对话方案.md](docs/07-口语实时对话方案.md) | 口语 AI 设计 |
| [docs/08-AI额度与计费.md](docs/08-AI额度与计费.md) | 付费闸门、预算、告警、管理页 |

## 已冻结决议（不得重开讨论）

- 前端 Vue 3 + Vite + TypeScript；数据库 SQLite(WAL)；JWT 认证；邀请码注册。
- 迁移旧 MySQL 数据与媒体；旧站 `ai.wizoom.net/PET` 暂不下线；Qwen Key 经管理页配置，不进 git。
- 多学科预留，英语已实现 PET / KET；数学已接入「李永乐一课通关」。

## 红线（违反即不得交付）

- 同步合并语义不得擅改：mastery/mistakes 并集、progress seen 并集 + idx 取大、plan 并集、409 冲突合并重试。
- 错题本维度记账规则不得擅改：答错全维度重欠、答对划单维、dims 空自动移出、不可手动删除。
- 密钥只从环境变量/管理页读取，禁止入库、入 git、入文档。
- 新依赖必须说明用途与取舍后再引入。
- 不提交 `frontend/dist/`、`data/`、`*.db`、`.env`、音频/媒体文件。

## 工作流

```text
小改动：直接改 → 跑相关测试/构建 → 实测
跨模块/接口/数据/依赖：先说明方案与影响面 → 用户确认 → 实施
触碰红线：必须先说明并获确认
```

- 不再创建 `docs/dev/` 过程文档；历史决策查 git history。
- 能力变化同步到 `docs/04`；新的稳定设计结论写进对应核心文档。
- 完成前跑测试（后端 pytest、前端 vitest）与 `npm run build`；未验证不得宣称完成。

## 环境约定

- 生产：飞牛 NAS Docker（nginx + api），发布 `python tools/deploy_nas.py deploy --host <IP>`；
  备份/回滚见 [docs/06 §4](docs/06-部署与运维.md)。
- 开发：Docker（macOS / Windows 统一），`python tools/dev.py init` 首次、`up` 启动；
  Vite 5173 + uvicorn 8000 热更新，开发库 `data/dev/pet.db` 与生产隔离。
- 演示数据：`python tools/dev.py seed --reset`；账号/邀请码见 `backend/app/seed_dev.py`。
- 无 Docker 时用 `tools/dev_local.py --build`（Windows，8088），仅做发布前验证。
- 版本：Node 22（`.nvmrc`）、Python 3.12（`.python-version`）。
- Monorepo：`frontend/`、`backend/`、`data-src/`、`tools/`、`deploy/`。
- 媒体文件用 ASCII slug 命名；音频/图片/视频与数据库不进 git。
- 旧站参考代码在上级目录 `../PET/`，只读。
