# NAS 开发环境 — 设计

> **已归档（2026-11-24）**：NAS `8089` 开发环境已删除，改由
> [本地开发环境](../../dev/local-dev-env/02-design.md)（`localhost:8088`，Windows 原生进程）替代。
>
> 对应需求：[01-requirements](01-requirements.md)；部署入口：[06 部署与运维](../../06-部署与运维.md)

## 1. 方案概览

同一台 NAS、两套 compose 项目并行：

```text
浏览器 ──▶ 前置 TLS ──┬─▶ nginx(prod)  :8088 ──▶ api pet-api:latest ──▶ data/pet.db
                      └─▶ nginx(dev)   :8089 ──▶ api pet-api:dev    ──▶ data/pet.db
```

- 生产目录 `/vol1/1000/docker/pet-v2`，开发目录 `/vol1/1000/docker/pet-v2-dev`。
- 两套目录各自带 `deploy/`、`frontend/dist/`、`data/`，互不共享。
- 开发环境通过 `PET_DEV_MODE=1` 返回模拟 AI 结果，不发起外部调用。

## 2. 变更点

### 2.1 `deploy/docker-compose.dev.yml`（新增）

- 顶层 `name: pet-v2-dev`，容器名与生产不冲突。
- nginx：`${PET_DEV_PORT:-8089}:80`，挂载 `../frontend/dist`。
- api：镜像 `pet-api:dev`（**必须**与 `pet-api:latest` 区分，避免重建 dev 覆盖生产镜像）；
  `PET_DEV_MODE=${PET_DEV_MODE:-1}`；挂载 `../data:/app/data`（相对 dev 根目录，天然隔离）。
- 其余配置（PIP 镜像、时区、healthcheck）与生产一致。

### 2.2 `tools/deploy_nas.py`

| 变更 | 说明 |
|---|---|
| `--profile {prod,dev}` | prod：8088 + `docker-compose.yml` + `pet-v2`；dev：8089 + `docker-compose.dev.yml` + `pet-v2-dev` |
| `--http-port` | 可覆盖宿主端口（保持 `--port` 仍为 SSH 端口） |
| `Runner.compose_file` | compose 命令统一带 `-f <file>` |
| `.env` 生成 | dev 写入 `PET_DEV_MODE=1`、`PET_DEV_PORT`；secret 备份为 `_work/nas-dev-jwt-secret.txt` |
| 打包排除 `.env` | 防止本地 secret 被带进 tar |
| 解包后 `chmod -R a+rX frontend/dist` | 修复 Windows tar 条目 mode 000 导致的 nginx 403 |

### 2.3 `seed-db`（新增 action，仅 dev）

用生产库的一致快照覆盖开发库，流程：

1. 在生产 api 容器内用 `sqlite3.Connection.backup` 生成快照
   `.../pet-v2/data/backup/pet-seed-<时间戳>.db`（WAL 安全，不停生产）。
2. `docker compose -f docker-compose.dev.yml stop api`（只停 dev api）。
3. `install -m 600` 快照到 dev `data/pet.db`，同时删除 `pet.db-wal` / `pet.db-shm`。
4. `docker compose -f docker-compose.dev.yml start api`，轮询 8089 `/api/v1/healthz`。

约束：`--profile prod` 调用直接拒绝，避免误覆盖生产。快照保留在备份目录便于回溯；
其中包含生产账号哈希与 `app_cfg`（AI Key），仅存于 NAS 本机备份目录。

## 3. API / 数据模型 / 前端

- 无 API 契约变化、无 schema 变化、无前端代码变化。
- 数据库迁移仍由 api 容器启动时 `alembic upgrade head` 执行；两套环境各自迁移各自数据库。

## 4. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 只用同一个 compose 加 override 文件、共享目录 | 否决：共享 `data/` 会污染生产库，且 `pet-api:latest` 会被重建覆盖 |
| 在 NAS 上跑 Vite dev server 做开发环境 | 否决：需要 Node 与源码热更新，NAS 定位是部署验证而非编码环境 |
| 用独立目录 + 独立 compose + 独立镜像 tag | **采用**：隔离彻底，脚本改动小，复用镜像层缓存 |
| dev 使用空库、手工注册测试账号 | 否决：无法复现真实账号/学习数据，验收价值低 |
| 直接复制生产 `pet.db` 文件（含 WAL） | 否决：WAL 未合并会丢数据，改用容器内 `sqlite.backup` 一致快照 |

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| dev 重建覆盖生产镜像 | 独立 tag `pet-api:dev` |
| Windows tar 权限 0 导致 403 | 部署脚本解包后 `chmod -R a+rX` |
| 端口/容器名冲突 | 独立 compose 项目名 `pet-v2-dev`，端口 8089 |
| dev 误连生产库 | 独立目录与 `data/` 卷；`seed-db` 只复制快照，不挂载生产库 |
| JWT 互相串用 | 两套 `.env` 各自生成 secret |
| 生产 Key 被 dev 调用 | dev 默认 `PET_DEV_MODE=1` 不发起外部调用；切真实 AI 前在 dev `/admin` 换独立 Key |
