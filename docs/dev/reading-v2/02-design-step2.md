# reading-v2 第二步 — 设计（02-design）

## 数据模型

```
plans 表新增列：reading_length INT DEFAULT 0、reading_days_done TEXT（逗号分隔 day）
新表 custom_sentences：
  id INTEGER PK / user_id FK / sid TEXT UNIQUE(业务键) / book TEXT / test_no INT / part INT
  en TEXT / cn TEXT / key TEXT / note TEXT / created_at
```

**业务键 sid** = `<book>:<testNo>:<part>:<en 小写去空格>`（同 Part 内同句去重）。

## 同步协议扩展

```
SyncData.plan: { length, days_done, reading_length, reading_days_done }
SyncData.custom_sentences: [{ sid, book, test_no, part, en, cn, key, note }]
```

合并语义：
- plan 阅读字段与词汇字段同规则（length/days_done 并集；reading 同）。
- custom_sentences 按 sid 去重并集，**冲突时服务端优先**（与 custom_words 一致）。

## 阅读计划切分（纯函数 `buildReadingPlan`）

- 单位 = **Part**（不是句子）：按 reading.json tests 顺序展开 `[book:testNo:part, ...]`，每天 `ceil(parts/N)` 个，末天吸收余量。
- `reading_day_of(partKey)` 反查所属天（打勾用）。
- 存储只存 `reading_length + reading_days_done`（切分确定性重算，与词汇计划同模式）。

## 错题维度设计

| item.type | dim 键 | 答错 | 答对 |
|---|---|---|---|
| meaning | `meaning` | recordWrong(sentId, [该 dim]) | recordRight(sentId, dim) |
| blank | `blank` | 同上 | 同上 |
| grammar | `grammar:g<该 gq 在 s.gq 数组中的下标>` | 同上 | 同上 |

- word_id 直接用句子 id（`t2p1s1` 等，与 custom 句 sid 不冲突——custom 句 sid 含 book 前缀）。
- 复习出题：取 scope 内 `mistakes[word_id].dims 非空` 的句子，**只为欠的维度重建题目**（meaning/blank 单独重建；grammar 按 gq 下标过滤），排在最前。

## 前端改动点

1. `core/merge.ts`：类型 + `mergePlan` 扩展 + `mergeCustomSentences`。
2. `core/plan.ts`：`buildReadingPlan(parts, days)` / `validatePlan` 复用。
3. `stores/learning.ts`：`setReadingPlan/deleteReadingPlan/markReadingDayDone/addCustomSentence/removeCustomSentence`。
4. `ReadingStudy.vue`：进入时按 progress idx 续学；逐句 next 时更新 idx；学完记完成日期。
5. `ReadingQuiz.vue`：错题优先组装 + submit 时维度记账；完卷打勾（按 part 反查阅读计划天）。
6. `ReadingHome.vue`：到期错题条（数量 + 进入复习）。
7. `PlanPage.vue`：新增「阅读计划」区（生成/删除/进度）。
8. 新页 `AddSentencePage.vue`：选教材/test/part + en/cn/key/note 表单。

## 后端改动点

- `models/extra.py` 加 CustomSentence；`models/learning.py` Plan 加两列。
- `schemas/sync.py` PlanData/custom_sentences；`services/merge.py` 扩展；`api/v1/sync.py` 读写。
- Alembic 迁移（autogenerate + 演练 upgrade/downgrade）。
