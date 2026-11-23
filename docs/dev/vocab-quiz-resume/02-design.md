# 单词测验断点续做 — 设计

## 1. 结论：前端本地保存，后端不动

本轮进度是**界面/会话状态**，不是学习成果：

| 数据 | 现状 | 刷新后 |
|---|---|---|
| 每题掌握维度 `mastery` | 答题即写 localStorage 并防抖同步后端 | 保留（pull 合并，mastery 取并集） |
| 每题错题 `mistakes` | 答题即写 localStorage 并防抖同步后端 | 保留（合并取「欠得多」） |
| 本轮题组、当前第几题、已答对错、错词列表 | 只在组件内存 | **丢失（本次要修）** |

因此正确做法是：**学习成果继续走现有同步；本轮会话由前端 localStorage 持久化**。

### 1.1 备选方案

| 方案 | 结论 |
|---|---|
| 后端同步字段（`SyncData.quiz_session`） | ❌ 要改 Pydantic、同步 schema、合并语义（红线），且两端同时做一半会互相覆盖；会话不是成就，不应跨设备合并 |
| 后端独立表 + 新 API | ❌ 新增迁移、鉴权、TTL 清理；为一份临时的 UI 状态引入完整服务端生命周期，过度设计 |
| Pinia 内存 / sessionStorage | ❌ 刷新即丢；sessionStorage 也随标签页关闭而丢 |
| **localStorage 按用户隔离（选定）** | ✅ 零后端改动、离线可用、与「数据默认存 localStorage」架构一致；刷新/关页后可续做 |

若将来确实需要跨设备续做，应单独立项：在同步数据中增加带 `updated_at` 的会话字段并按时间戳取新，
不能混进本次修复。

## 2. 数据流

```text
submit(ans)
  ├─ learning.recordRight/recordWrong  → 学习快照落盘 + 防抖 push（原有）
  ├─ results[qIndex] = 对/错
  └─ saveQuizSession(scope, snapshot)  → localStorage pet_quiz_session::<作用域>（新增）

next()
  ├─ 非最后一题：qIndex++ → saveQuizSession()
  └─ 最后一题：markPlanDayDone → clearQuizSession()

刷新
  router.beforeEach → auth.restore() → learning.hydrate()（owner/计划同步恢复）
  QuizPage setup → restoreSession()
      ├─ 校验版本 / TTL / 模式 / 计划天数 / 指定日 / 词库
      ├─ 命中：应用 round/results/correct/wrongWords，定位第一道未答题
      └─ 未命中：清除并按原逻辑开局（计划日 / 开局设置）
```

> 2026-11-23 迭代：计划测试改为按「天 + 词库」分作用域存储；自由测验仍用 `free:<用户>`。
> 新的键与页面设计见 [vocab-plan-learn-test §5](../vocab-plan-learn-test/02-design.md)。

## 3. 存储契约（`src/core/quizSession.ts`）

localStorage 键：`pet_quiz_session::<作用域>`（自由 `free:<用户名>`；计划
`plan:<用户名>:<plan_updated_at>:<day>:<bank>`）；值：

```ts
interface QuizSession {
  version: 1;
  saved_at: number;          // epoch ms，7 天 TTL
  mode: "plan" | "free";
  plan_day: number;          // 计划模式第几天；自由模式 0
  plan_length: number;       // 开轮时的计划总天数，用于识别计划变更
  plan_updated_at: number;   // 开轮时的计划结构时间戳，识别「删了又建、天数相同」
  bank: string;              // 自由模式词库 key
  count: number;             // 自由模式题量
  mistake_first: boolean;    // 自由模式「错题优先」
  round: QuizQuestion[];     // 题组（含选项与答案，恢复后不再随机）
  results: Array<boolean | null>;
  correct_count: number;
  wrong_words: PlanWord[];
}
```

校验（不通过即静默清除，回退到正常开局）：

- `version === 1`、`mode` 合法、`round.length > 0`；
- `results.length === round.length`；
- `now - saved_at <= 7 天`；
- 计划模式：`plan_day >= 1` 且 `plan_length >= 1`；`plan_length` 与 `plan_updated_at` 都必须等于当前计划；URL 带 `?day=` 时必须等于 `plan_day`；
- 自由模式：URL 带 `?bank=` 时必须等于 `bank`。

写入/读取/清除与业务判断均为纯函数，便于 vitest 覆盖；`localStorage` 异常（私密模式、配额）一律静默降级，
绝不影响答题主流程。

## 4. 恢复算法

```text
restoreSession():
  s = loadQuizSession(owner)
  if !s || !sessionMatches(s, 当前上下文) → 清除候选并返回 false
  应用 s.round / s.results / s.correct_count / s.wrong_words / s.bank / s.count
  计划模式：activePlanDay = s.plan_day
  idx = firstUnanswered(s.results)
  if idx >= 0:
      qIndex = idx; finished = false; 答题态复位; 若当前题为 w2m 自动发音
  else:
      qIndex = 最后一题; finished = true
      计划模式 → markPlanDayDone(plan_day)（幂等）
      clearQuizSession()
```

- 刷新发生在「已提交、未点下一题」之间：`results` 已落盘，恢复时直接从下一道未答题开始。
- 刷新发生在「最后一题已提交、未点看结果」之间：恢复即进入结算，并补打当天计划勾（`markPlanDayDone` 幂等）。
- 恢复后 `answers`/`picked`/`typed` 清零，因此不会把上一题的反馈错配到新题。

## 5. 接入点（`QuizPage.vue`）

| 时机 | 行为 |
|---|---|
| setup 末尾 | `restoreSession()`；命中则不再自动开局 |
| `loadBanks().then` | 自动 `startPlanDay()` 前增加 `!round.length` 守卫；自由模式恢复的词库若已不在当前级别，丢弃轮次回开局设置 |
| `submit()` | 记录对错后立即 `saveQuizSession()`（每题保存） |
| `next()` | 推进后保存；最后一题打勾并清除 |
| `start()` / `restart()` | 先清除旧轮次，再按原有逻辑开局 |
| 计划/登录晚到 watch | 保留原有 `!round.length && !finished` 守卫，不覆盖已恢复轮次 |

开局时把轮次模式固定为 `roundMode`（plan/free），保存与「打勾」都按它判断：
即使用户答题中途同步拉回了另一台设备新建的计划，也不会把自由轮次误存成计划轮次。

## 6. 风险

| 风险 | 缓解 |
|---|---|
| 计划被删除/改天数后恢复旧题组 | 校验 `plan_length`；清计划后自动开局不命中 |
| 从词库页指定另一词库仍恢复旧轮次 | 自由模式校验 `?bank=`；词库不可用时丢弃 |
| 同一浏览器多标签同时续做 | 后保存者覆盖，最坏回到较新的位置；不影响已记账的掌握/错题 |
| localStorage 满/禁用 | 写入失败静默降级，答题与同步不受影响 |
| 轮次长期堆积 | 7 天 TTL；完成即清除；按用户键隔离，不串号 |
| 题组体积 | 一轮最多约 56 题，序列化约十几 KB，远低于 localStorage 限额 |

## 7. 测试

- 新增 `src/core/quizSession.test.ts`：往返保存、用户隔离、TTL 过期、损坏/版本不符/长度不符丢弃、
  `sessionMatches` 的计划天数/指定日/词库判断、`firstUnanswered` / `resumePosition`（含「全部答完后刷新」落点）。
- 既有 `npm test`（sync/merge/plan/quiz/store）回归。
- `npm run build`（`vue-tsc --noEmit` + vite）。
- 浏览器手测：计划第 1 天答一半 → 刷新 → 从下一题继续；答完最后一题不点看结果直接刷新 → 结算且打勾；
  删/改计划后不恢复；自由模式按词库续做；换账号不串轮次。
