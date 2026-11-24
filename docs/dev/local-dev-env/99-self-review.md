# 本地开发环境 — 自省报告

> 日期：2026-11-24；分支：`feat/ai-budget`；对应需求：[01-requirements](01-requirements.md) / [02-design](02-design.md)

## 逐项自查

| 类别 | 检查项 | 结果 |
|---|---|---|
| 需求 | F-01 ~ F-06 均有实现；AC-01 ~ AC-06 已逐条验证 | ✅ |
| 设计 | 实现与 [02-design](02-design.md) 一致：NAS dev 代码删除；本地 8088 单进程直出；媒体令牌可选 | ✅ |
| 代码 | `py_compile` 通过；新文件 ruff 全绿；无硬编码密钥/绝对个人路径 | ✅ |
| 测试 | 后端 `pytest` 128 passed（含新增 5 个静态挂载测试）；前端 `vitest` 203 passed | ✅ |
| 构建 | `npm run build`（Node 22.20.0）通过，`vue-tsc --noEmit` 无错误 | ✅ |
| 依赖 | 无新增运行时/开发依赖 | ✅ |
| 数据 | 无 schema 变化；本地库 `backend/data/pet.db`（gitignore），与 NAS 数据隔离 | ✅ |
| 同步 | 未触碰合并语义、错题本维度、计划语义 | ✅ |
| 部署 | NAS 生产脚本保留 prod 打包/上传/chmod/构建/健康检查；本地 8088 实测通过 | ✅ |
| 文档 | `docs/06`、README、AGENTS、CLAUDE、02 已更新；`nas-dev-env` 已归档并注明替代关系 | ✅ |

## 实测记录

| 项 | 结果 |
|---|---|
| 本地启动 | `backend/.venv/Scripts/python.exe tools/dev_local.py` → `http://localhost:8088` |
| healthz | `{"status":"ok","version":"0.2.0","app":"PET v2 API","dev_mode":true}` |
| 页面/静态 | `/` 200、`/admin` 200（SPA 回退）、`/data/banks.json` 200、`/audio/listen/t1-p1.mp3` 200、`/assets/index-*.js` 200 |
| 404 边界 | `/api/nope` 404、`/missing.js` 404、未配置媒体目录时 `/media/math/none.mp4` 404 |
| prod-mode | `--port 8089 --prod-mode` → `dev_mode:false` |
| 媒体令牌 | 单测覆盖：无令牌 401；有效媒体令牌 200；`Range` 返回 206；路径穿越拒绝 |
| NAS 脚本 | `deploy_nas.py --help` 只剩 `check/deploy/ps/restart/logs`，无 `--profile`/`seed-db`；源码中无 8089/pet-v2-dev/compose.dev 引用 |

## 过程说明

1. `tools/dev_local.py --build` 依赖 PATH 中的 `npm`；本次验证用仓库内 portable Node 22.20.0
   （`_work/node/node-v22.20.0-win-x64`），未改系统环境。用户安装 Node 后重开终端即可直接用。
2. 本机 Docker Desktop 未安装成功（缺 `VirtualMachinePlatform`），因此采用用户确认的 Windows 原生进程方案。
3. 验证时重新构建了 `frontend/dist`（gitignore），并首次执行 `alembic upgrade head` 生成 `backend/data/pet.db`。
4. 未对 NAS 发起实际部署；`deploy_nas.py` 的 prod 分支仅做静态检查与 `--help` 验证。

## 遗留与注意

- `deploy_nas.py` 中 sudo 密码写入失败时仍静默 `pass`（原有行为，现已在 `noqa` 注释中说明为有意为之），
  `ruff check` 对本次改动的 Python 文件全部通过。
- 本地开发不提供前端热更新；需要 HMR 时用 `npm run dev`（5173）+ 后端 8000。
- 原 `seed-db` 能力随 NAS dev 环境一并删除；本地如需生产数据，手工复制 SQLite 一致快照到
  `backend/data/pet.db`（不要只拷 `-wal`/`-shm`）。
- 本地默认使用内置的开发 JWT secret，仅限本机；不要暴露到局域网/公网。
- 变更尚未提交（用户未要求提交）。

## 结论

**PASS-with-notes**
