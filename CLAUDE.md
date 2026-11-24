# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 必读与完成标准

- 开工前读 `AGENTS.md`、`docs/README.md` 和 `docs/01~05`；七阶段工作流见 `docs/03-Agent技术规范.md`（强制）。
- 完成前必须写 `docs/dev/{feature}/99-self-review.md`，结论为 PASS / PASS-with-notes / FAIL；FAIL 不得宣称完成。

## 常用命令

前端（`cd frontend`，Node 20+）
- `npm run dev` — :5173，`/api` 代理到 :8000
- `npm test` — vitest run；单文件：`npx vitest run src/core/merge.test.ts`
- `npm run build` — `vue-tsc --noEmit && vite build`（没有独立 lint 脚本）
- `vite.config.ts` 设了 `emptyOutDir: false`（dist 含 85MB 音频），不要手动清 `dist`

后端（`cd backend`，Python ≥3.12；macOS/Linux 用 `.venv/bin`）
- `.venv/bin/python -m alembic upgrade head`
- `.venv/bin/python -m uvicorn app.main:app --port 8000 --reload`
- `.venv/bin/python -m pytest tests/ -q`；单文件：`... -m pytest tests/test_merge.py -q`
- ruff 配置在 `pyproject.toml`（line-length=100, py312）

Docker（`cd deploy`）
- 先 `cd frontend && npm run build`：nginx 直接挂载 `../frontend/dist`，compose 不构建前端。
- `cp .env.example .env` 填 `PET_JWT_SECRET` → `docker compose up -d --build`
- api 容器启动时自动执行 `alembic upgrade head`；SQLite 在 `../data/pet.db`
- 空库首次部署：用邀请码 `claim` 注册的第一个账号自动成为管理员；完整流程见 `docs/06-部署与运维.md`

工具（仓库根 `package.json` 只为 playwright）
- `node tools/check_overflow.js <BASE>`（先起 vite）；`python tools/check_tokens.py`
- 本地开发/预发布（无 Docker，localhost:8088）：`backend/.venv/Scripts/python.exe tools/dev_local.py --build`

## 不要改

- `../PET/` 旧站参考代码，只读。
- `frontend/public/data/*.json` 是 `tools/build_*` 的产物；改数据请改 `data-src/` 后重新生成。
- `docs/01-需求清单.md` v1.0 已冻结；需求决议不得重开。
- 红线：同步合并语义（并集/取大）、错题本 dims 记账规则、密钥只从环境变量或管理页读取。
- 新增依赖须先在设计方案中说明（白名单见 `docs/03` §5）。

## 架构要点

- 后端分层：`api/v1/` 路由薄 → `services/`（merge、AI、Qwen、SOE、用量）→ `models/`；schema 只由 Alembic 管理，勿用 `create_all`。
- 前端 `src/core/` 是纯逻辑核心（sync 合并、plan、quiz、soe、review），均有 vitest 覆盖；合并/同步不得写进组件。
- 所有 HTTP 调用走 `src/core/api.ts`，组件内禁止裸 `fetch`。
- 数据默认存 localStorage，联网后增量同步；冲突返回 409，客户端合并后重试。
- 路由 meta（subject/module/crumbs/tabs/width）驱动布局与导航，新增页面必须补 meta。
- AI Key 存 `app_cfg` 表，在 `/admin` 配置，服务端只回显尾 4 位；不入 env 文件、不入 git。
- 组件用 `<script setup lang="ts">`；后端模块 snake_case、类 PascalCase；单文件 ≤400 行。
