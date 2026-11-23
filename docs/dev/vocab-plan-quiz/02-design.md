# 词汇计划：删除不复活 + 创建即生成题目 — 设计

## 1. 删除不复活（同步语义的最小扩展）

### 1.1 根因

前端与后端 `mergePlan` 原文：

```text
length = cli.length || srv.length || 0
days_done = srv.days_done ∪ cli.days_done
```

删除把客户端 length 写成 0，`0 || 30` 仍然取 30；刷新 pull 合并后又变回 30。

### 1.2 方案：计划结构时间戳

新增两个字段（词汇/阅读各自独立）：

```text
plan_updated_at      epoch ms，创建/删除/改天数时写入
reading_updated_at   epoch ms，创建/删除阅读计划时写入
```

合并规则：

| 时间戳 | length / days_done |
|---|---|
| 客户端更新 | 以客户端为准（删除 = 0 + 空打卡） |
| 服务端更新 | 以服务端为准 |
| 相同（含老数据均为 0） | **保持原红线**：length 取非 0，days_done 并集 |

> 红线说明：同一份计划的完成状态仍然并集；只有「计划被重建/删除」这种结构性变更才按时间戳
> 切换代际。这样既保住多端进度不丢，又让删除真正生效。
> 阅读计划的 `reading_books` 也按时间戳取较新一侧；同代际仍沿用「客户端非空优先」。

### 1.3 落盘

- `learning.setPlan(length)`：写入 length、清空 `days_done`、`plan_updated_at = Date.now()`。
- `learning.deletePlan()`：只清词汇字段 + 时间戳（**修复原实现误清阅读计划**）。
- `setReadingPlan` / `deleteReadingPlan`：清阅读打卡并写 `reading_updated_at`。
- `markPlanDayDone` / `markReadingDayDone`：只并集打卡，不动时间戳。

### 1.4 数据库

Alembic `c9d1e2f3a4b5`：

```sql
ALTER TABLE plans ADD COLUMN plan_updated_at BIGINT NOT NULL DEFAULT 0;
ALTER TABLE plans ADD COLUMN reading_updated_at BIGINT NOT NULL DEFAULT 0;
```

`sync.py` pull/push 读写这两个字段；`PlanData` Pydantic 增加 `int` 默认 0。
老数据时间戳为 0，继续按原并集语义合并；用户下一次创建/删除即写入当前时间。

## 2. 创建计划即生成题目

### 2.1 生成规则（确定性，不落库）

对第 N 天：

```text
planDays = splitPlan(banks, plan.length, 当前级别词库)
day = planDays[N-1]
for 每个词库 key:
  for 每个词 word:
    dim = bankMeta[key].dims[i % dims.length]   # PET 三题型 / KET 两题型
    题目 = makeQuestion(key 全库, word, dim)
```

- 题目内容、题型、顺序只由「词库 + 天数 + 第几天」决定，跨设备一致；
- 不新增题目表/同步字段，避免 1680 条 ID 冗余；
- 选择题干扰项来自同一词库，保证选项稳定有意义。

### 2.2 计划页（`PlanPage.vue`）

- 计算 `planDays / totalQuestions / nextPlanDay`（第一个未完成天，全完成回最后一天）。
- 计划进行中显示：已生成 M 道题（四库 + 三题型），按钮「学习第 N 天」。
- 跳转 `/english/words/study?day=N`。

### 2.3 学习页（`QuizPage.vue`）

- `planMode = 计划长度 > 0 && 没有 ?bank=`（从词库页进入仍走自由测验）。
- 词库加载完成后自动 `startPlanDay()`；登录/同步晚到则 watch 后补启动。
- 顶部计划条：第 N 天 + 各库题数 + 总题数。
- 整轮答完（最后一题点「看结果」）→ `markPlanDayDone(N)`。
- 「再来一轮」在同一天重建同一题组；不做随机换题。
- 自由模式（`?bank=`）完全保留原设置卡片与 10/20 题逻辑。

### 2.4 同义替换词库清洗

旧数据 300 条「同义替换」全部 `cn = null`，`en` 形如 `a DVD you can keep 你可以拥有的 DVD`。
在 `loadBanks()` 加载时：

```ts
splitTermMeaning("a DVD you can keep 你可以拥有的 DVD")
→ { en: "a DVD you can keep", cn: "你可以拥有的 DVD" }
```

- 按首个 CJK 字符切分；纯英文则 cn 为空、空值回退原文；
- 只影响内存数据，不改 `frontend/public/data/banks.json`（该文件由构建链生成）。

### 2.5 首次同步 rev=0

新用户/首次连接若 `rev=0` 就 push，服务端 `SyncPushIn.rev` 要求 ≥1，会 422。
同步引擎在 `doPush` 开头：`rev < 1` 时先 `pullAndMerge()`，拿到服务端 rev 再 push。

## 3. 取舍

| 方案 | 结论 |
|---|---|
| 删除时直接以客户端 length 覆盖 | ❌ 会覆盖另一台设备刚建的新计划 |
| 把「删除」编码成特殊 length（-1） | ❌ 侵入所有消费方，schema/兼容成本高 |
| 把每天题库存进 plans 表 | ❌ 数据冗余大，词库升级后快照过期 |
| 创建时只存题目数量 | ❌ 无法保证题型/内容一致 |
| **时间戳代际 + 确定性按天生成（选定）** | ✅ 删除可靠、题目零存储、跨设备一致 |

## 4. 风险

| 风险 | 缓解 |
|---|---|
| 设备时钟偏差导致较新的删除被判旧 | 时间戳来自客户端；偏差通常秒级，删除/创建很少并发；同代际仍并集 |
| 词库更新后旧计划题目内容变化 | 题目按当前词库确定性生成，属于内容升级；计划天数/打卡不受影响 |
| 一次 56 题较长 | 计划页明确当天题数；可中途退出，不打卡，下次重新开始 |
| 同义替换拆分误伤英文中的中文标点 | 仅在 cn 为空时规范化；单测覆盖典型格式 |
| 首次同步 pull 失败 | 不再 422，状态 offline，等待下次 markDirty/pull 重试 |

## 5. 测试

- 前端：merge/sync/plan/quiz/banks/store 单测；`vue-tsc`；构建。
- 后端：merge/sync pytest。
- 浏览器（临时用户）：
  - 创建 30 天 → 显示 1680 题 → 学习第 1 天 = 56 题自动开始；
  - 删除 → 等同步 → 刷新仍为空；
  - 创建 180 天 → 第 1 天 10 题 → 全部答完 → `days_done=["1"]`；
  - 再删除 → 刷新为空；控制台无错误。
