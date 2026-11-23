# 词汇计划：学习 / 测试分库 + 按库测试 — 设计

## 1. 总览

```text
计划页 /english/words/plan
  ├─ 学习第 N 天 → /english/words/study/day?day=N
  │    └─ PlanStudyPage：四库切换 + 翻卡（发音/释义/例句）
  └─ 测试第 N 天 → /english/words/study?day=N
       └─ QuizPage（计划模式）：四库导航，每库独立题组/进度/续做
            └─ 四库全部完成 → markPlanDayDone(N)
```

自由测验（`?bank=` 且无 `?day=`）保持原逻辑；`?day=` 存在时即使带 `?bank=` 也进入计划测试，
用于学习页「去测试本库」。**2026-11-23 迭代：无 `?day=` 的 `/study` 改为随机学习，
侧栏「学习」不再自动进入计划测试，详见 [vocab-random-learning](../vocab-random-learning/02-design.md)。**

## 2. 测试题型与题量

| 词库 | 每个词的题型 | 每词题数 |
|---|---|---|
| PET 必默 `bimo` | 拼写、看词选义、看义选词 | 3 |
| PET 高频 `gaopin` | 看词选义、看义选词 | 2 |
| PET 固定搭配 `guding` | 看词选义、看义选词 | 2 |
| PET 同义替换 `tongyi` | 看词选义、看义选词 | 2 |
| KET 各库 | 沿用 `bankMeta.dims`（看词选义、看义选词） | 2 |

实现为 `core/quiz.ts` 的纯函数：

```ts
testDimsForBank(key: string, metaDims?: string[]): QuizDim[]
// bimo → ["spell","w2m","m2w"]
// gaopin/guding/tongyi → ["w2m","m2w"]
// 其他（KET）→ metaDims ?? 全三型
```

题量：`day.banks[key].length × dims.length`。30 天 PET 计划约 136 题/天，
180 天计划约 23 题/天。页面按词库拆分，避免一次性面对全部题。

## 3. 确定性出题

`makeTestRound(bank, words, dims, seed)`：

1. 按 `splitPlan` 的词顺序遍历；每个词按 `dims` 顺序生成 `dims.length` 道题（逐词交错）；
2. 选择题干扰项从**同一词库**取，用 `mulberry32(seed)` 洗牌；
3. 种子：`seedFrom(plan_updated_at, day, bankKey)`；
4. 同一计划（`plan_updated_at` 不变）、同一天、同一库 → 题目顺序与选项完全一致；
5. 计划重建（时间戳变化）→ 新种子、新题组。

不落库、不同步题目，避免题目快照与词库升级冲突；本质是「创建计划时确定」的确定性函数。

## 4. 计划测试页（`QuizPage.vue`）

### 4.1 状态

```ts
interface BankTestState {
  round: QuizQuestion[];
  results: Array<boolean | null>;
  correct_count: number;
  wrong_words: PlanWord[];
  finished: boolean;
}
const planStates: Record<bank, BankTestState>
const activeBank: string
```

进入计划测试时（词库加载完成后）：

1. 计算当天 `planDay`；对每个有词的词库：
   - 先按作用域读取本地会话；校验通过则恢复题组/结果；
   - 否则 `makeTestRound` 生成并 `results = new Array(n).fill(null)`；
2. 默认选中 URL `?bank=` 指定的库，否则第一个未完成的库；
3. 若所有库已恢复为完成 → 标记当天打勾并显示总结果。

页面仍用现有 `round / results / correctCount / wrongWords / qIndex / finished` 作为
**当前词库**的视图；切换词库时先 `saveActiveBankState()` 再载入目标库状态。

### 4.2 词库导航

- 顶部横向胶囊：`必默 12/72`、`高频 30/28`…，完成的库显示 ✓；
- 点击切换；已答完的库进入结果视图，未答完的定位到第一道未答题；
- 导航始终可见，满足「测试过程中可选择 4 个部分」。

### 4.3 完成与打勾

- 单库最后一题点「看结果」→ 该库 `finished = true`；
- `allDone = 当天所有有词的库 finished`；
- `allDone` 时：`markPlanDayDone(day)`（幂等）、清除当天所有库会话、显示总结果；
- 单库完成但未全完成：显示本库结果 + 「下一个词库」/「重做本库」。

### 4.4 错题记账

计划测试答错时使用**该库测试维度**作为 `recordWrong` 的 dims（必默 3 维、其他 2 维），
答对仍逐维 `recordRight`。理由：非必默库不考拼写，若仍记 `spell` 欠账，该维度在计划测试里
永远无法划掉，错题会永久滞留。合并语义不变（仍是 dims 并集、答错重欠/答对划单维）。
旧数据中非必默词若已欠 `spell`，可通过自由测验（仍考三型）划掉；本次不做数据清洗。

## 5. 会话键（`core/quizSession.ts`）

按作用域分键，支持同一天多个词库各自续做：

```text
计划：pet_quiz_session::plan:<用户名>:<plan_updated_at>:<day>:<bank>
自由：pet_quiz_session::free:<用户名>
```

- `save/load/clear` 接受 `scope` 字符串；版本升到 2，旧单轮计划会话不再读取（未上线）。
- 会话体沿用单轮结构：题组、results、正确数、错词、mode、plan 天数/时间戳、bank。
- 校验仍为：版本、7 天 TTL、数据完整性、计划结构、指定日、词库。
- 计划删除/改天数/重建 → 作用域或时间戳变化，旧会话自然不命中。

## 6. 学习页（新增 `PlanStudyPage.vue`）

- 路由：`/english/words/study/day?day=N`，meta 与单词板块一致（子路径会高亮「学习」页签）。
- 词库导航：当前级别（PET 四库 / KET 五库），显示当天每库词数；默认 `?bank=` 或第一个有词的库。
- 翻卡：正面英文 + 音标 + 发音；点击翻面显示词性、中文、例句；上一张/下一张；
  `prefers-reduced-motion` 下不做翻转动画。
- 「去测试本库」→ `/english/words/study?day=N&bank=key`。
- 不写掌握/错题，不参与打勾。

## 7. 计划页（`PlanPage.vue`）

- 操作区两个按钮：`学习第 N 天`（次要）、`测试第 N 天`（主要）。
- 文案改为「学习 X 个词 · 测试 Y 道题」；Y 按各库 `词数 × 题型数` 计算。
- 预览列表仍显示每天词数；不改变切分与创建流程。

## 8. 备选方案

| 方案 | 结论 |
|---|---|
| 四库仍合并成一整轮，只加题型 | ❌ 无法按库切换、单库完成/续做 |
| 把题目持久化到计划并同步 | ❌ 改同步 schema/合并红线，题目快照易过期 |
| 每次进入随机出题 | ❌ 不满足「创建计划时生成」 |
| 非必默库也考拼写 | ❌ 与用户确认的 v1 规则不符 |
| **种子确定性 + 每库独立会话（选定）** | ✅ 零后端改动、稳定、可续做 |

## 9. 风险

| 风险 | 缓解 |
|---|---|
| 题量变大（必默 3 题/词） | 按库拆分，导航显示每库进度；计划天数越短单日越多，属预期 |
| 单库超过 80 题时分段进度过密 | 超过 80 题不再渲染逐题分段，保留数字进度（`1 / 2136`） |
| 旧错题含非必默 spell 欠账 | 自由测验仍考三型，可划掉；本次不清洗同步数据（避免触碰合并语义） |
| 计划时间戳为 0（老数据） | 种子稳定为 0，仍确定性；重建计划后改变 |
| 多标签同时测同一库 | 后保存覆盖，学习成果（掌握/错题）仍按题记账 |
| 词库升级导致某库当天词变化 | 题组按当前词库重新生成；会话校验不过则重开该库 |

## 10. 附带修复

- 自由测验「错题优先」此前把整库都排进本轮（`makeRound` 对 `picked` 未截断），
  现在仍按 10/20 题上限截取，只是错题排前面。
- 计划测试的错题记账使用该库测试维度（必默 3 维、其他 2 维），
  避免非必默库永久欠一个不会考的「拼写」维度；合并语义（并集/取欠得多）不变。

## 11. 测试

- `quiz.test.ts`：`testDimsForBank`；`makeTestRound` 每词题数、必默 3/其他 2、
  同种子完全一致、不同种子选项变化、干扰项来自同库；`makeRound` 错题优先仍受题量上限。
- `quizSession.test.ts`：作用域键隔离（不同 day/bank 互不覆盖）、TTL/损坏/版本校验、计划字段匹配、
  `pruneQuizSessions` 清理过期与旧计划代际。
- Playwright 打桩冒烟（本地 Chrome）：
  - 计划页两入口与题型文案；
  - 学习页四库导航 + 翻卡；
  - 测试页四库导航、必默 9 题/高频 6 题等；
  - 清会话后重新进入题目一致（确定性种子）；
  - 答 2 题刷新后续做；
  - 单库结果按钮、四库全完后「今日测试完成」且 push `days_done` 含 1；
  - 非必默错题 dims 为 2 维、必默为 3 维；
  - 自由测验仍为 10 题并可刷新续做。
- `vue-tsc --noEmit`、`vite build`。
