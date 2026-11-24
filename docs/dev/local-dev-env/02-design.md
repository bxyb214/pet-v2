# 本地开发环境 — 设计

> 对应需求：[01-requirements](01-requirements.md)；部署入口：[06 部署与运维](../../06-部署与运维.md)

## 1. 方案概览

本机 Windows 原生进程，一个 uvicorn 同时在 `127.0.0.1:8088` 提供 API 与构建后的前端：

```text
浏览器 ──▶ http://localhost:8088（tools/dev_local.py → uvicorn）
             ├─ /api/*            → FastAPI 路由（api_router）
             ├─ /media/math/*     → FileResponse（仅设置 PET_MATH_MEDIA 时；校验 ?mt= 媒体令牌）
             ├─ /assets /data /audio /img /fonts …
             │                    → frontend/dist 静态文件
             └─ 其他无扩展名路径  → frontend/dist/index.html（Vue history 回退）
```

- 生产仍是 NAS 上的 nginx + api 容器；本方案只在开发机替代原 NAS `8089`。
- 前端产物仍需 `npm run build`；本脚本的 `--build` 会先构建。
- `PET_DEV_MODE` 默认 `1`（模拟 AI、顶栏 DEV）；`--prod-mode` 设为 `0`。

## 2. 变更点

### 2.1 删除 NAS 开发环境

| 文件 | 处理 |
|---|---|
| `deploy/docker-compose.dev.yml` | 删除 |
| `tools/deploy_nas.py` | 去掉 `--profile {prod,dev}`、`seed-db`、`DEFAULT_REMOTE_DEV`、`DEFAULT_PORT_DEV`、dev `.env` 分支；只保留生产 `8088` / `docker-compose.yml` |
| `docs/06` §3.4 | 删除；改为本地原生开发环境说明 |
| `docs/dev/nas-dev-env/` | 移入 `docs/archive/2026-11-24-nas-dev-env/` 并注明被 `local-dev-env` 替代 |

### 2.2 `backend/app/dev_static.py`（新增，仅开发使用）

`mount_static(app, dist, media_root=None)` 在既有 API 路由之后追加：

1. 可选 `GET /media/math/{file_path:path}`：`mt` 或 `X-Media-Token` → `decode_token(..., "media")`，
   再查 `users` 表确认用户仍存在；路径必须落在 `PET_MATH_MEDIA` 内（防穿越）。
   `FileResponse` 在 Starlette 1.10 原生支持 `Range`，拖动进度条可用。
2. `GET /{full_path:path}`：
   - `api/*`、`media/*` → 404；
   - 命中 `dist` 内文件 → `FileResponse`；`index.html` 与 `/data/*.json` 带 `Cache-Control: no-cache`，
     其余静态资源 `public, max-age=2592000`；
   - 带扩展名但文件不存在 → 404（避免把缺失 JS 回成 HTML）；
   - 无扩展名 → 返回 `index.html`（SPA 回退）。

路由顺序是硬约束：FastAPI 按注册顺序匹配，API 路由先注册，`media` 次之，通配回退最后。
生产不会导入本模块，因此不改变容器行为。

### 2.3 `tools/dev_local.py`（新增）

```bash
backend/.venv/Scripts/python.exe tools/dev_local.py            # 8088，dev_mode=1
backend/.venv/Scripts/python.exe tools/dev_local.py --build    # 先 npm run build
backend/.venv/Scripts/python.exe tools/dev_local.py --prod-mode # dev_mode=0
```

启动顺序：

1. 解析 `--host`（默认 `127.0.0.1`）、`--port`（默认 `8088`）、`--build`、`--prod-mode`。
2. 检查 `frontend/dist/index.html`；`--build` 时用 PATH 里的 `npm run build`。
3. `cwd=backend/` 执行 `python -m alembic upgrade head`。
4. 在导入 `app.main` **之前**设置 `PET_DEV_MODE`（配置在导入时读取并缓存）；
   `--prod-mode` 强制写 `0`，否则默认 `1`（外部已设置时保留）。
5. `sys.path` 加入 `backend/`，`mount_static(app, DIST, PET_MATH_MEDIA?)`，`uvicorn.run(app)`。

默认值：`PET_DATABASE_URL=sqlite:///./data/pet.db`（相对 `backend/`，即 `backend/data/pet.db`）；
JWT secret 沿用 `app.core.config` 的开发默认值。已显式设置的环境变量优先。

### 2.4 `backend/tests/test_dev_static.py`（新增）

用临时 `dist` 与独立 `FastAPI()`（注册一条 `/api/ping` 模拟 API 路由）验证：
SPA 回退、静态文件与缓存头、缺失资源 404、`/api/*` 不被回退、媒体令牌 401/200、路径穿越拒绝。

## 3. API / 数据模型 / 前端

- 无 API 契约变化、无 schema 变化、无前端代码变化。
- 媒体令牌复用现有 `make_media_token` / `decode_token`；不新增表。
- 本地数据库与 NAS 完全隔离；如需生产数据，手工复制一致快照到 `backend/data/pet.db`。

## 4. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 保留 NAS 8089 开发环境 | 否决：两套 NAS 目录/镜像/端口维护成本高，用户明确要求删除 |
| 本地 Docker Compose | 否决：本机 Docker Desktop 因缺 `VirtualMachinePlatform` 未能安装；且用户选择原生进程 |
| Vite preview（8088）+ uvicorn（8000） | 否决：需要两个进程与额外代理配置，`/media/math` 无法直出 |
| FastAPI 同进程直出 `dist` | **采用**：单进程、单端口、无新依赖，路由行为可单测 |
| 前端 HMR 作为默认 | 否决：HMR 用 `npm run dev`（5173）即可；8088 用于验证构建产物 |

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| FastAPI 静态性能低于 nginx | 仅本机单人开发，可接受；生产仍走 nginx |
| 忘记重新构建前端 | 文档标注；`--build` 一条命令构建后启动 |
| 端口 8088 被占用 | uvicorn 启动报错；`--port` 可改 |
| 路径穿越读取任意文件 | `Path.resolve()` 后校验父目录 |
| 本地误用生产 Key | 默认 `PET_DEV_MODE=1` 不发起外部调用；需要真实 AI 时显式 `--prod-mode` 并在 `/admin` 配置独立 Key |
| 误删 NAS 生产部署 | `deploy_nas.py` 只收敛 dev 分支，prod 打包/上传/构建/健康检查逻辑不变 |
