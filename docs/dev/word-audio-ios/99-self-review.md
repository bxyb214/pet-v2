# 单词学习发音修复 — 自省报告

> 日期：2026-11-24；分支：`feat/ai-budget`（未提交）；关联：[01 需求](01-requirements.md)、[02 设计](02-design.md)

## 1. 逐项自查

| 类别 | 检查项 | 结果 |
|---|---|---|
| 需求 | F-01 ~ F-04、AC-01 ~ AC-03 全部落地 | ✅ |
| 设计 | 实现与 02-design 一致，未偏离 | ✅ |
| 代码 | 改动仅 `core/say.ts`、`WordStudyCard.vue`、`QuizPage.vue`；无新增依赖；HTTP 调用约定未受影响 | ✅ |
| iOS 约束 | 朗读在点击事件内同步发起；`say()` 空闲时不 `cancel()`；不再依赖网络音频成功 | ✅ |
| 测试 | `npx vitest run`：24 文件 / **194 passed**（新增 `say.test.ts` 9 例） | ✅ |
| 构建 | `npm run build`（vue-tsc + vite）通过；入口 `assets/index-BLuW05fu.js` | ✅ |
| 产物 | 新 `say-*.js` 无 `media/audio`，`playWordAudio` 编译为同步 `say` 调用 | ✅ |
| 数据 | 未改 `frontend/public/data/*.json`；未触碰同步合并、错题 dims、密钥规则 | ✅ |
| 文档 | 01/02/99 齐全；`docs/AI优化与额度方案.md` §1.1 与 P0-5 已按新方案修订 | ✅ |
| 真机 | iPad Safari 点按验收 | ✅ 2026-11-24 用户在生产 8088 实测通过 |
| 部署 | 生产 8088 | ✅ 2026-11-24 20:35 部署，`/` 入口 `index-BLuW05fu.js` 与本机构建一致，`say-Ck94qr8J.js` 200 且无 `media/audio`，healthz 200 |

## 2. 根因与修复摘要

词库 `audio` 字段是旧站整组音频（`bimo-01.mp3`，1395 词仅 91 个文件），本站从未托管；
`/media/audio/*` 被 nginx `try_files` 回退成 `index.html`，`new Audio(...).play()` 异步失败后
才回退 `say()`。桌面浏览器允许异步朗读，iOS Safari 只认用户手势内同步调用 → iPad 静默。

修复：单词一律同步 `say(word)`；发音按钮改按 `word.en` 显示；`say()` 空闲时跳过 `cancel()`。

## 3. 风险与取舍

- **音色由系统语音决定**：iOS 与 Windows 音色不同，属浏览器能力差异，非缺陷。
- **w2m 答题前自动朗读在 iOS 上可能无声**：该调用不在用户手势内，浏览器会拦截；答后手动按钮正常，符合“答前仅 w2m 自动发音”的既有规则。
- **`playAudioUrl` 仍是异步 `play()`**：服务端 TTS（口语示范/造句）在 iOS 首次点击时可能被拦截，属另一链路，本次未改；如后续出现同类问题再单独处理。
- 旧站 `../PET/audio` 保持只读，未复制任何文件进仓库。

## 4. 结论

**PASS**：代码、测试、构建、部署与 iPad 真机验收全部完成（2026-11-24 生产 8088 实测有声音）。
