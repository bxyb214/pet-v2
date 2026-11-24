# 用户端 AI 计费统计 — 自省报告

> 日期：2026-11-24；分支：`feat/ai-budget`；对应需求：[01-requirements](01-requirements.md) / [02-design](02-design.md)

## 逐项自查

| 类别 | 检查项 | 结果 |
|---|---|---|
| 需求 | F-01 ~ F-06 均有实现；AC 已逐条核对 | ✅ |
| 设计 | 与 02 一致：`GET /usage/me` + `/settings/usage`；未引入额外依赖 | ✅ |
| 代码 | 后端分层（api → service → model）；前端请求走 `core/api.ts`；无裸 `fetch` | ✅ |
| 测试 | 后端 129 passed（新增 4）；前端 207 passed（新增 4）；`vue-tsc` + `vite build` 通过 | ✅ |
| 依赖 | 无新增 | ✅ |
| 数据 | 无 schema 变更、无 Alembic 迁移；只读 `usages` | ✅ |
| 同步 | 未触碰合并语义、错题本 dims、计划逻辑 | ✅ |
| 部署 | 本地 `localhost:8088` 实测通过；已部署生产 NAS，healthz / 路由 / 静态资源 / Alembic 校验通过 | ✅ |
| 文档 | 01/02/99、02 API 表、04 M4 与变更记录、AI 方案已更新 | ✅ |

## 实测记录

| 项 | 结果 |
|---|---|
| `GET /usage/me` 未登录 | 401 |
| 新用户 | `days=[]`，四区间全 0，`ai_enabled=false` |
| 双用户隔离 | A 的金额/明细不含 B 的 999；B 只看到自己的 999 |
| 区间汇总 | 今日 12、所选月 19、今年 19（去年 500 未混入）；本周按周一至今天计算 |
| 月份过滤 | `?month=2020-01` → 空明细、0 元；`2026-13` / `abc` → 422 |
| 响应隐私 | 根对象与 `days` 均无 `user_id` |
| 本地真实接口 | 临时用户写入 185 秒对话、4 次 SOE、1350 TTS 字符、730 LLM token，`/usage/me` 返回 0.11 元；四区间与逐日行一致 |
| 设置入口（非管理员） | 桌面/移动截图均显示「AI 计费」卡（今日/本月 + 查看明细），可跳转 `/settings/usage` |
| 统计页（未开通） | 显示未开通提示与历史用量；隐藏无意义的预算进度，显示「未开通期间不会产生新的 AI 费用」 |
| 统计页（已开通） | 显示日/月额度进度、剩余 0.39 元、单次对话上限约 30 分钟 |
| 统计页（移动端） | 汇总卡 2 列；明细表在容器内横向滚动，页面无整体横向溢出 |
| 管理员设置页 | 「AI 计费」卡数量 0，且未发起 `/usage/me` 请求 |
| 生产 healthz | `{"status":"ok","version":"0.2.0","dev_mode":false}`，api 容器 healthy |
| 生产路由 | `/settings/usage` 200；`/api/v1/usage/me` 未登录 401（路由已生效） |
| 生产静态资源 | 入口 `index-COPaTtXf.js` 与本地一致；`UsagePage-DDciJFhE.js`、`SettingsPage-l0OThphj.js` SHA256 与本地一致 |
| 生产数据库 | Alembic `e1a2b3c4d5e6 (head)`，无迁移变更 |
| 清理 | 临时用户、用量/告警/会话、邀请码与截图/token 均已删除 |

## 变更文件

- 后端：`api/v1/usage.py`（新）、`api/v1/__init__.py`、`schemas/usage.py`（新）、`services/usage.py`
- 后端测试：`tests/test_usage_me.py`（新，4 个用例）
- 前端：`views/UsagePage.vue`（新）、`views/SettingsPage.vue`、`router/index.ts`、`core/usage.ts`（新）
- 前端测试：`core/usage.test.ts`（新，4 个用例）
- 文档：`docs/02-技术架构.md`、`docs/04-功能清单.md`、`docs/AI优化与额度方案.md`

## 遗留与注意

- 已部署到生产 NAS（2026-11-24）；生产库无 schema 变更，回滚只需切回上一镜像。
- `totals.year` 固定为**当前自然年**，不随所选月份变化；页面标签为「今年」。选择历史月份时，「所选月」看历史，「今年」看当前年度，已在 UI 中区分。
- `budget.status()` 保留原有「80%/100% 告警去重写入」副作用；打开统计页可能补记一次告警，但同一周期同一档只写一次。
- 管理员入口不展示；管理员手动访问 `/settings/usage` 仍只会看到自己的数据，不影响管理页。
- 额度提示按 `daily/monthly.stage` 判断，`hard_stop=false` 时额度用尽仍显示「已用尽」文案，不会误报「额度可用」；
  与 `core/aiStatus.ts` 的横幅口径一致。
- 新文件 `api/v1/usage.py` 仍会命中项目既有的 ruff `B008`（FastAPI `Depends` 默认参数）规则；与现有 `speak.py` 等一致，未新增其他规则问题。
- `rm -rf` 未使用；临时用户与文件已逐项删除，未触碰真实账号/数据。
- 变更尚未提交（用户未要求提交）。

## 结论

**PASS-with-notes**（功能、测试与生产部署完成；遗留项见上）
