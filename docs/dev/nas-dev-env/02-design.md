# NAS 开发环境 — 设计

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

## 3. API / 数据模型 / 前端

- 无 API 契约变化、无 schema 变化、无前端代码变化。
- 数据库迁移仍由 api 容器启动时 `alembic upgrade head` 执行；两套环境各自迁移各自数据库。

## 4. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 只用同一个 compose 加 override 文件、共享目录 | 否决：共享 `data/` 会污染生产库，且 `pet-api:latest` 会被重建覆盖 |
| 在 NAS 上跑 Vite dev server 做开发环境 | 否决：需要 Node 与源码热更新，NAS 定位是部署验证而非编码环境 |
| 用独立目录 + 独立 compose + 独立镜像 tag | **采用**：隔离彻底，脚本改动小，复用镜像层缓存 |

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| dev 重建覆盖生产镜像 | 独立 tag `pet-api:dev` |
| Windows tar 权限 0 导致 403 | 部署脚本解包后 `chmod -R a+rX` |
| 端口/容器名冲突 | 独立 compose 项目名 `pet-v2-dev`，端口 8089 |
| dev 误连生产库 | 独立目录与 `data/` 卷；文档注明不复制生产库 |
| JWT 互相串用 | 两套 `.env` 各自生成 secret |
