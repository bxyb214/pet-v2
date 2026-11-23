# 口语计划选日与入口重排 — 设计

## 1. 页面顺序

```text
口语
每天 5 + 10 + 15 …
┌ 今日开口：跟读 … · 造句 … · 对话 …    预估 … ┐   ← 原在日历下方
├ 今天 · 第 N 天   点下方日历可切换练习日  [回到今天] ┤
│ [跟读 5 分钟] [造句 10 分钟] [自由对话 15 分钟]        │   ← 作用于选中日
├ 口语计划  已完成 x/y 天                              │
│ 1 2 3 … 30  （点数字选择练习日）                      │
│ 第 N 天 · 范围 · Part 标题                             │
│ 阶段图例 / 第 N 天的场景 / 删除计划                    │
└────────────────────────────────────────────────────┘
```

「今日开口」仍只统计今天；三个入口与场景跟随选中的计划日。

## 2. 选中日

```ts
pickedDay: number | null          // null = 跟随 todayDay
activeDay = pickedDay 合法 ? pickedDay : (todayDay || 1)
```

- `todayDay` 仍是第一个未完成的计划日；不显式选日时入口跟随它。
- 点击日历：`pickDay(day)` → 只更新 `pickedDay`，不跳页。
- 三个入口：`goShadow(activeDay)` / `goMake(activeDay)` / `goTalk(activeDay)`。
- 场景：`activePlanDay = planDays[activeDay]`，`activeScenes` 由其 `sceneIds` 得出。
- 「回到今天」：`setPickedDay(null)`，header 立即回到今天对应的计划日。

### 2.1 跨页面保持

选中日按用户存 `sessionStorage`：

```text
key:   pet_speak_day::<username>
value: "5"
```

- `onMounted` 在 `auth.restore()` 之后读取；多个账号同标签页不会串号。
- 从跟读/造句/对话返回、刷新页面仍保留；`logout` 不管它，key 带用户名自然隔离。
- 删除计划、重建计划、`day > planLength` 时清空。
- 隐私模式 `sessionStorage` 抛错时静默降级为仅内存。

## 3. 日历交互与可访问性

- 格子由 `div` 改为 `<button type="button">`：原生可点击、可聚焦、可回车/空格触发。
- `:aria-pressed="d.day === activeDay"` 暴露选中状态。
- 状态叠加：
  - `done`：已完成绿块；
  - `today`：今天浅绿底 + 主色边框；
  - `sel`：选中日外圈 2.5px 深绿描边（与今天、已完成均可区分）。
- `:focus-visible` 用暖橙外框；`:active` 轻微缩放，解决“看起来不能点”的反馈缺失。
- title 追加「点击切换练习日」。

## 4. 反馈文案

- 入口上方：「今天 · 第 N 天」或「已选 · 第 N 天」+「点下方日历可切换练习日」。
- 有显式选择时出现「回到今天」。
- 日历下方增加一行「第 N 天 · 日期范围 · Part 标题」，点哪天亮哪行。
- 场景标题：「今天（第 N 天）的场景」或「第 N 天的场景」。

## 5. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 日期点击仍直接跳跟读 | ❌ 无法选择当天再做造句/对话，且没有选中反馈 |
| 只用 CSS 加 hover，不改成按钮 | ❌ 键盘不可用，触屏按下反馈弱 |
| 选中日放路由 query | ❌ 返回计划页时 BackButton 不带 query，仍会丢 |
| 选中日放 localStorage | ❌ 与“当前会话”语义不符，久置后可能指向旧计划 |
| **按钮选日 + sessionStorage（选定）** | ✅ 反馈明确、键盘可用、跨练习返回保留、失败可降级 |

## 6. 测试

- `vue-tsc`、`vitest`（104 项）回归。
- 浏览器：页面顺序、点第 5 天、入口进入 `shadow?day=5`、返回后仍第 5 天、
  回到今天、键盘 Enter、390px 手机顺序与无溢出。
