# 本地开发环境 — 需求

> 功能编号：`local-dev-env`；日期：2026-11-24；关联文档：[06 部署与运维](../../06-部署与运维.md)
> 替代：[nas-dev-env](../../archive/2026-11-24-nas-dev-env/01-requirements.md)（已归档到 `docs/archive/2026-11-24-nas-dev-env/`）

## 1. 背景与目标

原开发/预发布环境是飞牛 NAS 上的第二套 Compose（`8089`、`pet-v2-dev`、`pet-api:dev`、
`seed-db` 快照播种）。它需要额外维护一套 NAS 目录、镜像与端口，验证价值与成本不匹配。
目标：删除 NAS 开发环境部署代码，改为在本机 Windows 原生进程运行 `http://localhost:8088`，
发布前先在本机验证；NAS 上的生产部署（`8088`）保持不变。

## 2. 用户故事

- **US-01**：作为维护者，我希望在本机用一条命令启动与生产同构的站点（8088），以便发布前验证。
- **US-02**：作为维护者，我希望本地环境不依赖 Docker/nginx，以便在没有 Docker Desktop 的 Windows 上直接运行。
- **US-03**：作为维护者，我希望 NAS 只保留一套生产部署，以便减少目录、镜像与端口维护。

## 3. 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| F-01 | 删除 `deploy/docker-compose.dev.yml`，移除 `tools/deploy_nas.py` 的 `--profile dev`、`seed-db`、`8089`/`pet-v2-dev` 分支 | P0 |
| F-02 | 新增 `tools/dev_local.py`：`127.0.0.1:8088` 单进程同时提供 FastAPI 与 `frontend/dist`，含 SPA 回退 | P0 |
| F-03 | 本地默认 `PET_DEV_MODE=1`；`--prod-mode` 可关闭；`PET_MATH_MEDIA` 设置时才挂载 `/media/math` 并校验 `mt` 媒体令牌 | P0 |
| F-04 | 启动前自动 `alembic upgrade head`；`--build` 先构建前端；数据库默认 `backend/data/pet.db`，与 NAS 数据隔离 | P0 |
| F-05 | 文档更新：`docs/06`、README、AGENTS；`nas-dev-env` 归档并注明被替代 | P1 |
| F-06 | 保留 NAS 生产部署能力：`tools/deploy_nas.py deploy --host <IP>` 行为不变 | P0 |

## 4. 边界与非目标

- 不提供前端热更新；需要 HMR 时仍用 `npm run dev`（5173）+ 后端 8000。
- 不引入 Docker、nginx、CI/CD、新运行时依赖。
- 不改同步合并语义、错题本维度、计划语义、API 契约与数据库 schema。
- 不再在 NAS 上保留第二套开发/预发布环境。

## 5. 验收标准

- **AC-01**（F-02）：`python tools/dev_local.py` 启动后，
  `GET /api/v1/healthz` 返回 `status=ok` 且 `dev_mode=true`；`/`、`/data/banks.json`、
  `/audio/listen/*.mp3`、`/admin` 均返回 200。
- **AC-02**（F-02）：`/api/unknown` 与 `/missing.js` 返回 404，不返回 `index.html`。
- **AC-03**（F-03）：设置 `PET_MATH_MEDIA` 后，不带 `mt` 请求 `/media/math/<文件>` 返回 401；
  用登录用户的媒体令牌请求返回 200，`Range: bytes=0-99` 返回 206。
- **AC-04**（F-03）：`--prod-mode` 启动时 healthz 的 `dev_mode=false`。
- **AC-05**（F-01/F-06）：`deploy_nas.py --help` 不再出现 `--profile`/`seed-db`；
  `deploy_nas.py deploy --host <IP>` 仍是生产 8088 的完整发布流程。
- **AC-06**（F-05）：`docs/06` 不再包含 8089/`--profile dev`/`seed-db` 操作说明；
  归档目录含「已被本地 8088 替代」说明。

## 6. 影响面

| 类别 | 内容 |
|---|---|
| 部署 | 删除 `deploy/docker-compose.dev.yml`；新增 `tools/dev_local.py`、`backend/app/dev_static.py` |
| 脚本 | `tools/deploy_nas.py` 收敛为生产单环境 |
| 测试 | 新增 `backend/tests/test_dev_static.py`；现有后端/前端测试保持通过 |
| 数据 | 无 schema 变化；本地库在 `backend/data/pet.db`（gitignore） |
| 业务代码 | 无同步/合并/错题/计划改动 |
| 依赖 | 无新增 |
