# 口语 Part 2 — 设计（计划进度 / 时长 / 题库入口 / 返回按钮）

## 1. 计划进度

根因：`speak_days` 是 90 天原始天打卡，新计划直接复用旧记录；且 `dayDone` 只要求
`shadow_done && talk_done`。

修复：

- `PUT /speak/plan`：当计划天数发生变化时，删除该用户的 `speak_days` 记录，新计划从零开始。
- `PUT /speak/plan` 前端提示「创建新计划会重置之前的打卡进度（练习时长与历史记录保留）」。
- `speak_days` 新增 `make_done`；`POST /speak/log` 支持 `mode=make`。
- `GET /speak/days` 返回 `make_done`。
- 前端 `dayDone = shadow_done && make_done && talk_done`。
- 造句页提交 AI 检查时写入 `make` 日志（每页一次），按计划日的 `sourceDays` 标记。

## 2. 练习时长（服务端）

新增表 `speak_times`：

```
user_id + day(YYYY-MM-DD, 北京时间) + mode(shadow|make|talk) + seconds
```

接口：

```
GET  /api/v1/speak/time/today  → {day, totals:{shadow,make,talk}}
POST /api/v1/speak/time        {mode, seconds(1..600)}
     → {day, mode, seconds, totals}
```

前端 `core/speakTime.ts`：

- 进入页面先拉今日 totals 作为 `serverBase`。
- 每 5 秒把「本次页面真正开口秒数」的增量上报；页面隐藏/卸载时再补一次。
- 显示值 = `serverBase + 本地已开口 - 已上报`，刷新后以服务端为准。

### 开口检测

- `core/speakRTC.ts`：拿到麦克风流后接 `AnalyserNode`，每 200ms 算 RMS，
  超过阈值累计 200ms；`SpeechConn.speechSec()` 暴露累计秒数。
- `core/soe.ts`：对采集到的 PCM 块算 RMS，超过阈值按块时长累计；`SoeEval.speechSec()` 暴露。
- 跟读页在 AI / SOE 引擎切换时把上一引擎的秒数结算进 `speechBase`。
- 对话页在结束/返回/卸载时结算 `SpeechConn.speechSec()`。
- 造句页没有麦克风输入，按页面可见练习时间累计（明确标注为练习时间）。

倒计时目标不变：跟读 5:00、造句 10:00、对话 15:00（10+5），但显示的是累计开口时间，
不再随刷新归零。

## 3. 题库入口

- 删除首页第四个「场景题库」卡片；`SPEAK_TABS` 保留「题库」页签。
- 计划日历下方仍显示「今天的场景」，计划预览仍列出每天场景。

## 4. 返回按钮

新增 `components/BackButton.vue`：

- 胶囊形按钮，描边 + 阴影，最小高度 48px；`(min-width:768px) or (pointer:coarse)` 提到 54px。
- 图标 + 文案，`touch-action: manipulation`，明显的 hover/active/focus 反馈。
- 替换跟读、对话、造句、题库页的旧文字链接；跟读/对话页点击时仍先结算时长与保存记录。

## 风险

| 风险 | 缓解 |
|---|---|
| 麦克风能量阈值受环境噪声影响 | 阈值 0.02；回声消除开启；只作为练习时长统计，不影响评分 |
| 创建计划重置打卡被误以为是丢数据 | 前端明确提示；`speak_logs` 历史与 `speak_times` 时长保留 |
| 造句没有语音输入，时长语义不同 | UI 标注「今日造句」，按可见练习时间计，后续可改语音造句 |
| 旧计划用户的旧打卡仍存在 | 删除/重建计划即重置；本轮不主动清历史 |
