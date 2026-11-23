# 单词测验断点续做 — 自省报告

> 结论：**PASS-with-notes**（功能与测试通过；本地 `npm test` / `npm run build` 的 `.bin` shim 损坏属环境问题，已改用底层入口验证；未做真实浏览器手测）

## 1. 需求对照

| 编号 | 实现 | 测试 / 验证 |
|---|---|---|
| F-01 每题保存 | `QuizPage.submit()` 记录对错后 `saveQuizSession()`；`next()` 推进后刷新保存 | `quizSession.test.ts` 往返保存 |
| F-02 刷新恢复 | `tryRestoreSession()` 应用题组/结果/正确数/错词，`firstUnanswered()` 定位第一道未答题 | 单测覆盖读取、`firstUnanswered`；类型检查通过 |
| F-03 计划模式校验 | `sessionMatches()` 校验模式、`plan_length`、`plan_updated_at`、URL `?day` | 单测覆盖天数/结构时间戳/指定日不一致 |
| F-04 自由模式校验 | 校验 `?bank`；词库不在当前级别时 `abandonRound()` 回开局设置 | 单测覆盖词库一致/不一致 |
| F-05 完成清理 + 7 天 TTL | 最后一题 `next()` 清除；恢复时发现全答完直接结算并清除；`loadQuizSession` TTL | TTL 边界单测 |
| F-06 按用户隔离 | 键 `pet_quiz_session::<用户名>` | 用户隔离单测 |

## 2. 设计一致性

- 采用 `02-design.md` 的「前端 localStorage，后端不动」方案；未新增 API、表、同步字段。
- 与设计偏差：为保证登录态/计划数据晚于页面挂载时也能续做，额外把恢复尝试挂在
  `ownerName` 与 `planLength/banksReady` 的 watch 上（设计已含「先恢复再自动开局」的意图）。
- 恢复时若发现最后一题已答（尚未点「看结果」），补调 `markPlanDayDone`，与「整轮答完才打勾」一致且幂等。

## 3. 代码检查

- `vue-tsc --noEmit` 通过；无硬编码密钥、绝对路径、TODO。
- 未触碰 `src/core/merge.ts` / `sync.ts` 与后端合并语义（红线）。
- 未引入新依赖。
- 已知遗留：`QuizPage.vue` 原本已 848 行（超过 400 行约定），本次增加约 120 行；建议后续把
  计划模式/结算区拆为子组件，本次不做以免扩大改动面。

## 4. 测试结果

```text
node node_modules/vitest/vitest.mjs run
Test Files  17 passed (17)
Tests       124 passed (124)   # 含新增 quizSession 10 条

node node_modules/vue-tsc/bin/vue-tsc.js --noEmit   → 通过
node node_modules/vite/bin/vite.js build            → 通过（QuizPage-*.js 14.55 kB）
```

说明：本机 `frontend/node_modules/.bin/vitest`、`.bin/vue-tsc` 是损坏的相对路径 shim，
`npm test` / `npm run build` 会报 `MODULE_NOT_FOUND`；这是 node_modules 安装环境问题，与本次代码无关，
因此直接调用包内入口完成验证。若重装依赖（`npm install`）后脚本应恢复正常。

## 5. 同步 / 数据 / 部署

| 项 | 结果 |
|---|---|
| 同步合并语义 | 未修改 |
| 掌握/错题记账 | 未修改，仍在每题作答时立即写本地并同步 |
| Schema / Alembic | 无变更 |
| 部署 | 无新增配置；前端产物可正常构建 |
| 文档 | 01/02/99 已落盘；`docs/dev/README`、`docs/02`、`docs/04` 已更新 |

## 6. 遗留与建议

1. 浏览器手测建议按 `02-design.md §7` 走一遍：计划第 1 天答一半刷新、答完最后一题不点看结果刷新、
   改计划后进入、自由模式换词库、换账号。
2. 若未来需要跨设备续做，另立设计：同步字段需带 `updated_at` 并按时间戳取新，不能在本次方案上直接扩展。
3. `QuizPage.vue` 行数超标，后续可拆分（与本功能无关）。
