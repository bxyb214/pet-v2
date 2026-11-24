# 单词学习发音修复（iPad 无声）

> 日期：2026-11-24；分支：`feat/ai-budget`；线上入口：生产 8088 `/plan` 单词学习卡

## 1. 用户问题

iPad 上进入单词学习，点卡片右下角 🔊「听发音」没有声音；同一账号在 Win11 浏览器上正常。
测验反馈区的「听发音」同样受影响。

## 2. 复现与定位

| 环境 | 现象 |
|---|---|
| Win11 Chrome/Edge | 有声音（实际是语音回退） |
| iPad Safari | 无声 |

根因链：

1. 词库 `word.audio` 值来自旧站，是**整组音频**文件名（`bimo-01.mp3`），1395 个词只对应 91 个文件；这些 mp3 只存在于只读旧站 `../PET/audio/`，新站从未部署。
2. `playWordAudio` 请求 `/media/audio/<audio>`：nginx 没有这个 location，`try_files` 回退到 `index.html`，返回 `200 text/html`。
3. `new Audio(...).play()` 因格式不符异步 reject，`.catch` 里再调 `say(word)`。
4. iOS Safari 只允许在用户手势的同步调用栈里调用 `speechSynthesis.speak()`；此时已经脱离点击事件，语音被静默丢弃。Chrome 没有这个限制，所以 Win11 听得到。

## 3. 需求 / 验收

| 编号 | 要求 |
|---|---|
| F-01 | 单词学习卡点 🔊 时，iPad Safari 与桌面浏览器都能朗读该单词 |
| F-02 | 朗读必须在点击事件内同步发起，不依赖网络请求 |
| F-03 | 所有词库（含 `audio` 为空的 KET/同义词库）都有发音按钮 |
| F-04 | 不新增依赖、不请求缺失的 `/media/audio` 资源 |
| AC-01 | `playWordAudio()` 返回前已调用 `speechSynthesis.speak()` |
| AC-02 | 单元测试断言不构造 `Audio` 对象 |
| AC-03 | 前端类型检查、构建、全量测试通过 |

## 4. 不做

- 不迁移旧站 149 MB 整组 mp3（粒度不对：一个文件是一组词，不是单词发音）。
- 不为单词引入服务端 TTS（有费用，违背“发音零成本”约定）。
- 不改 `reading.ts` 的 en-US 朗读策略。
