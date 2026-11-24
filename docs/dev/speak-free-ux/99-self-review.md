# 口语免费功能提示与按钮体验 — 自省报告

> 日期：2026-11-24；分支：`feat/ai-budget`；对应需求：[01-requirements](01-requirements.md) / [02-design](02-design.md)

## 逐项自查

| 类别 | 检查项 | 结果 |
|---|---|---|
| 需求 | F-01 ~ F-05 均有实现；AC 已逐条核对 | ✅ |
| 设计 | 与 02 一致：共享 `PaidAiNotice` / `PaidActionButton`；无接口与数据变更 | ✅ |
| 代码 | `<script setup lang="ts">`；HTTP 仍走 `core/api.ts`；未新增裸 `fetch`；单文件均 ≤400 行 | ✅ |
| 测试 | 后端 129 passed；前端 209 passed（新增 2）；`vue-tsc` + `vite build` 通过 | ✅ |
| 依赖 | 无新增依赖 | ✅ |
| 数据 | 无 schema 变更、无 Alembic 迁移 | ✅ |
| 同步 | 未触碰合并语义、错题本 dims、计划逻辑 | ✅ |
| 部署 | 已部署生产 NAS 8088（2026-11-24）；healthz、静态资源、Alembic、备份校验通过 | ✅ |
| 文档 | 01/02/99 齐全；`docs/04` S16 与变更记录、`docs/AI优化与额度方案` 已更新 | ✅ |

## 实测记录

| 项 | 结果 |
|---|---|
| 后端测试 | `pytest tests/ -q` → 129 passed |
| 前端测试 | `npm test` → 27 个测试文件、209 passed（`aiStatus.test.ts` 新增 2 个用例） |
| 类型与构建 | `npm run build`（`vue-tsc --noEmit && vite build`）通过；仅有既有的 `stores/auth.ts` 动态/静态导入警告 |
| 口语首页（未开通） | 暖橙提示卡展示「付费 AI 未启用」、费用说明、免费功能清单，左侧强调边 + 投影 |
| 造句页（未开通） | 提示卡与首页一致；「开始说」灰色可点击；点击后顶部 toast 展示完整提示；「听标准答案（浏览器朗读）」可见 |
| 跟读页（未开通） | 提示卡；「听示范（浏览器朗读）」；无「自己读一遍」；“跟读评分”灰色可点击，点击出 toast |
| 对话页（未开通） | 提示卡；选择场景后「开始对话」灰色可点击，点击出 toast |
| 浏览器朗读 | Playwright 点击跟读页「听示范（浏览器朗读）」后，`/api/v1/speak/tts` 请求数为 0 |
| 移动/桌面宽度 | 1440×1000 实测四页无横向溢出；提示卡与按钮在卡片内换行 |
| 临时数据 | 本地临时用户、Playwright 脚本与截图已删除；本地 8088 服务已停止 |
| 生产备份 | 部署前停 api 完成 SQLite `.backup`，`PRAGMA integrity_check=ok` |
| 生产健康检查 | `healthz` 返回 `dev_mode=false`；api 容器 `healthy`，nginx 正常监听 8088 |
| 生产路由 | `/english/speak`、`/english/speak/make` 均 200 |
| 生产静态资源 | 入口 `index-CZJWzyhJ.js` 与本地一致；`PaidAiNotice`、`PaidActionButton` 及四个口语页 chunk 均 200 |
| 生产内容校验 | 入口 chunk 含完整费用与免费功能文案；造句 chunk 含「听标准答案（浏览器朗读）」；跟读 chunk 无「自己读一遍」 |
| 生产数据库 | `alembic current` = `e1a2b3c4d5e6 (head)`；无 schema 变更 |

## 变更文件

- 新增：`frontend/src/components/PaidAiNotice.vue`、`frontend/src/components/PaidActionButton.vue`
- 修改：`frontend/src/views/SpeakHome.vue`、`frontend/src/views/SentencePage.vue`、`frontend/src/views/SpeakShadow.vue`、`frontend/src/views/SpeakTalk.vue`
- 修改：`frontend/src/core/aiStatus.ts`、`frontend/src/core/aiStatus.test.ts`
- 文档：`docs/dev/speak-free-ux/`（01/02/99）、`docs/04-功能清单.md`、`docs/AI优化与额度方案.md`

## 遗留与注意

- 已部署到生产 NAS（2026-11-24）；本次无 schema 变更，回滚需重新部署上一版本前端 `dist`，数据库无需降级。
- 本功能只改变前端呈现；未开通用户的 SOE / Realtime / LLM 闸门仍由后端 `require_paid_ai` 控制，前端置灰按钮只负责提示，不作为安全边界。
- `PaidAiNotice` 仅在 `ai_enabled=false` 时展示；额度 80% / 100% 继续由既有 `budgetBanner` 横幅提示，避免同一页面重复两套额度文案。
- `PaidActionButton` 用 `aria-disabled` + 灰色 CSS 代替原生 `disabled`，因为原生禁用按钮不派发 click；键盘 Enter / 空格仍会触发提示，真正动作被组件拦截。
- 浏览器朗读依赖 `speechSynthesis`；不支持的环境保持静默失败，不发起付费 TTS，也不阻塞练习。
- 测试环境当前默认 Node 26 的 experimental `localStorage` 会让既有 vitest/jsdom 用例失败，Node 20 又缺少已安装 undici 需要的 `zlib.createZstdDecompress`；本次使用 Node 22.23.5 运行前端测试与构建。该问题与本功能无关，未修改仓库的 Node 版本约束。
- 变更尚未提交（用户未要求提交）。

## 结论

**PASS-with-notes**（功能、测试、本地页面实测与生产部署完成；Node 版本环境差异见上）
