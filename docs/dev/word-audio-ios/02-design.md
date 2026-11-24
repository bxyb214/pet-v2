# 单词学习发音修复 — 设计

## 1. 方案取舍

| 方案 | 结论 | 原因 |
|---|---|---|
| A. 部署旧站 `/media/audio/*.mp3` 并修 nginx | 否 | 文件是整组音频，单词点播会放出整组录音，语义错误；且多 149 MB |
| B. 单词改用服务端 Qwen TTS | 否 | 产生字符费用，与“单词发音零成本”约定冲突 |
| C. 单词一律走浏览器 `speechSynthesis`，点击内同步调用 | **采用** | 零依赖零费用；同步调用满足 iOS 手势限制 |

## 2. 代码改动

| 文件 | 改动 |
|---|---|
| `frontend/src/core/say.ts` | `playWordAudio(word)` 直接同步 `say(word)`；删除 `/media/audio` 请求与异步回退。`say()` 仅在 `speaking/pending` 时先 `cancel()`，规避 iOS「cancel 后立即 speak 被吞」 |
| `frontend/src/components/WordStudyCard.vue` | 发音按钮显示条件从 `audio` 字段改为 `word.en`；删除只服务于静态音频的 `audio` computed |
| `frontend/src/views/QuizPage.vue` | 反馈区「听发音」改为 `playWordAudio(word.en)`（w2m 答题前自动朗读同一入口） |
| `frontend/src/core/say.test.ts` | 新增 9 个用例：同步发声、不构造 `Audio`、中文截断、空词、cancel 策略、无 API 降级、splitExample |

## 3. 行为变化

- 桌面端：原本「先请求不存在的 mp3 → 回退朗读」变为直接朗读，听感不变，少一次 404/HTML 请求。
- iPad：点击 🔊 由静默变为正常朗读；`听整句` 原本就是同步 `say()`，不受影响。
- KET / 同义词库（`audio` 为空）此前不显示发音按钮，现在统一显示。
- 测验 w2m 答题前的自动朗读在 iOS 上仍受浏览器策略限制（非用户手势），属预期；答后手动「听发音」正常。

## 4. 验证

- `npx vitest run`：194 passed（新增 9）。
- `npm run build`：`vue-tsc --noEmit` + vite 通过，入口 `assets/index-BLuW05fu.js`。
- 生产包内 `say-*.js` 不再包含 `media/audio`，`playWordAudio` 编译为同步 `say` 调用。
- iPad 真机验收：需部署后人工点按确认（见 99-self-review）。
