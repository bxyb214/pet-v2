# 无计划自由练习 — 设计

## 1. 总开关：`hasPlan`

三个入口页都以服务端 `/speak/plan` 的 `length` 为准：

```ts
const hasPlan = computed(() => planLength.value > 0);
const planDays = computed(() => hasPlan.value ? splitSpeakPlan(data, planLength.value) : []);
const planDay  = computed(() => hasPlan.value ? planDays[...] : null);
```

此前页面写的是 `splitSpeakPlan(data, planLength || 90)`，没有计划也会按 90 天切分，
既显示今日内容，也会记时/打卡。本次统一去掉该兜底。

## 2. 计划页（`SpeakHome.vue`）

- 今日开口、5/10/15 入口：`v-if="loaded && hasPlan"`。
- 无计划：只显示「还没有口语计划」+ 创建按钮，并说明可去三个子页自由练习。
- `refresh()` 无计划时直接跳过 `/speak/days`、`/speak/usage_today`、`/speak/time/today`，
  避免隐藏区域仍发起时长请求。
- 有计划时保持选日、场景、打卡与删除计划逻辑不变。

## 3. 时长开关（`core/speakTime.ts`）

`useSpeakTime` 增加第三个参数：

```ts
useSpeakTime(mode, getSeconds, () => hasPlan.value)
```

- `load()` / `flush()` / `tick()` 在 `enabled()` 为 false 时直接返回；
- 挂载时无计划不读取 `/speak/time/today`，之后若计划加载出来，tick 会补一次 load；
- 页面卸载不会上报。

## 4. 跟读页（`SpeakShadow.vue`）

无计划：

- 隐藏 5 分钟目标条与计划日 chip；副标题提示“自由练习，不计时、不打卡”。
- 新增 `freePacks`：按 `packs.order` 排序、统计每个 pack 的句子数，只列有内容的库。
- 选择 pack → `freeItems = shadow.filter(s => s.pack === id)`，库内顺序不变；
  「换一句」在库内循环。
- 开始跟读/腾讯 SOE 的流程不变；麦克风数字人照常出现。
- `finish()` 因 `planDay === null` 不写 `/speak/log`。
- 「结束练习」在自由模式留在本页并提示可换一组，不跳回计划页。

## 5. 造句页（`SentencePage.vue`）

- 题库句型选择（`patterns`）本来就有，保留。
- 隐藏 10 分钟目标条，副标题改为自由练习说明。
- 页面秒表只在 `hasPlan` 时累加；时长 composable 关闭。
- `planDay` 为 null，`logMake()` 不写打卡。

## 6. 对话页（`SpeakTalk.vue`）

无计划且未选场景、`phase === "idle"` 时：

- 显示「选择题库场景开始」：Part 1–4 筛选 + 搜索 + 场景卡片列表（161 个，区内部滚动）。
- 点击场景 → `scene = s` 并立即 `start()`；也可先从 `?scene=` 带入（题库页跳转）。
- 计时：`v-if="hasPlan"` 隐藏 10 分钟/5 分钟计时；`startTimer()` 只在有计划时启动。
- 无计划时 `planDay = null`：boot 的 `day=0`，无 patterns，`/speak/log` 循环为空。
- 结束对话仍调用 `session_end` 记真实用量/费用（不写入练习时长）。
- 「完成今天练习」在自由模式回到场景选择（不跳计划页）。

## 7. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 无计划继续按 90 天默认计划发内容 | ❌ 用户明确要求“必须创建计划才有这些内容” |
| 无计划时三个 tab 直接重定向到题库页 | ❌ 多一次跳转，且跟读/造句并非场景驱动 |
| 自由练习也计时但不上报 | ❌ 界面仍会显示 5/10/15 目标，与需求冲突 |
| 无计划也调用时间接口只是不展示 | ❌ 仍会产生服务端数据，违背“不计时” |
| **hasPlan 分流 + 各页题库选择 + 时长开关（选定）** | ✅ 计划与自由练习边界清晰，接口零写入 |

## 8. 测试

- 类型检查、104 项单测、构建。
- 浏览器（无计划）：计划页无入口/今日开口；跟读 19 个句子库、无计时条；
  造句无计时条；对话 161 场景、点选即开始、无计时；全程无 `/speak/time*`、无 `/speak/log`。
- 浏览器（30 天临时计划）：入口/今日开口/日历恢复，跟读 5 分钟条、造句 10 分钟条、
  对话 10:00 计时恢复，无不一致。
