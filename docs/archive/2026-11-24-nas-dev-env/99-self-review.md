# NAS 开发环境 — 自省报告

> **已归档（2026-11-24）**：NAS `8089` 开发环境已删除，改由
> [本地开发环境](../../dev/local-dev-env/02-design.md)（`localhost:8088`，Windows 原生进程）替代。
>
> 日期：2026-11-23；提交：`chore/nas-dev-env` → `main`（含 `seed-db` 追加）

## 逐项自查

| 类别 | 检查项 | 结果 |
|---|---|---|
| 需求 | F-01 ~ F-06 均有实现；AC-01 ~ AC-08 已验证 | ✅ |
| 设计 | 实现与 [02-design](02-design.md) 一致；未偏离 | ✅ |
| 代码 | `py_compile` 通过；无硬编码密钥/绝对个人路径；`.env` 被打包排除 | ✅ |
| 测试 | 后端 `pytest` 88 passed；前端 `vitest` 139 passed | ✅ |
| 依赖 | 无新增运行时依赖；仅本机临时使用 portable Node 20/22 构建与测试（未入库） | ✅ |
| 数据 | 无 schema 改动；生产迁移 `b7c1f2a90d34 → c9d1e2f3a4b5` 先在快照上演练，含 downgrade/upgrade 往返 | ✅ |
| 同步 | 未触碰合并/错题维度/计划语义 | ✅ |
| 部署 | 生产已备份 `data/backup/pet-2026-11-23.db`；8088/8089 healthz 均通过 | ✅ |
| 文档 | 01/02/99 齐全；`docs/06` 已补 §3.4 与发布顺序 | ✅ |

## 实测记录

| 项 | 结果 |
|---|---|
| 开发环境 | `http://<NAS-IP>:8089`，`dev_mode: true`，容器 `pet-v2-dev-api-1` / `pet-v2-dev-nginx-1` |
| 生产环境 | `http://<NAS-IP>:8088`，`dev_mode: false`，容器 `deploy-api-1` / `deploy-nginx-1` |
| 静态资源 | 两端 `/`、`/data/banks.json`、`/audio/listen/t1-p1.mp3`、`/admin` 均 200 |
| 新构建生效 | 生产 `/` 引用的 `assets/index-eWKvUqTw.js` 与本机 `frontend/dist/index.html` 一致 |
| 数据隔离 | dev 与 prod 各自 `data/pet.db`；生产迁移后 `rev=c9d1e2f3a4b5`、`users=4`、`mastery=1289` 不变 |
| 开发库播种 | `seed-db --profile dev` 后 dev `rev=c9d1e2f3a4b5`、`users=4`、`mastery=1289`、`plans=1`，与生产快照一致；生产 healthz 仍正常 |
| 迁移演练 | 对生产快照执行 upgrade → downgrade → upgrade，`integrity_check=ok` |

## 过程问题（已修复）

1. **静态资源 403**：Windows 打的 tar 条目 mode 为 `000`，nginx worker 无读权限。
   已在 `deploy_nas.py` 解包步骤加入 `chmod -R a+rX frontend/dist`，并对运行中的 dev 目录手工修复。
2. **本机无 Node**：下载 portable Node 20/22 到 `_work/`（gitignore），未改系统环境。
   Node 20 无法跑 vitest（`undici@8` 要求 Node ≥22.19），测试改用 Node 22。

## 遗留说明

- dev 环境默认 `PET_DEV_MODE=1`（AI/SOE 模拟，不产生外部调用）。需要真实 AI 时把 dev `.env` 改为 `PET_DEV_MODE=0`；
  注意开发库由生产快照复制，`app_cfg` 中带着生产 Key，建议先在 dev `/admin` 换成独立 Key。
- 开发库如需再次与生产对齐，执行 `seed-db --profile dev`（会覆盖 dev 数据，不影响生产）。
- 尚未配置 `8089` 的外网 HTTPS 反代；局域网可用，外网发布前需在路由器/NAS 反代补一条规则。
- 本次提交仅在本机 `main`，未推送到 GitHub。

## 结论

**PASS**
