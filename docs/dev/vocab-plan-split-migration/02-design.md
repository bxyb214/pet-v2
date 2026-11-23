# 词汇计划切分对齐 v1 + felix 计划迁移核对 — 设计

## 1. 切分算法（v1 语义）

对每个词库 `bank`（长度 L）和计划天数 N，第 d 天（0-based）取：

```text
start = floor(d * L / N)
end   = floor((d + 1) * L / N)
words = bank[start:end]
```

- 每库每天条数只可能是 `floor(L/N)` 或 `ceil(L/N)`，差 ≤1；
- 余量均匀散布到各天，不会出现「前几天 24 个、最后一天 0 个」；
- 只要 `L >= N`，每天都有该库的词；
- 库内顺序不变，拼接回来等于原库（不重不漏）。

### 1.1 第 24 天验算（PET 30 天）

| 词库 | 长度 | 第 24 天区间 | 词数 |
|---|---|---|---|
| 必默 | 712 | [545, 569) | 24 |
| 高频 | 414 | [317, 331) | 14 |
| 固定搭配 | 254 | [194, 203) | 9 |
| 同义替换 | 300 | [230, 240) | 10 |
| **合计** | 1680 | | **57** |

与 v1 的「学习单词 57 个词条」一致。

### 1.2 为什么不是全局平分

旧的全局算法先算 `total/N`，再四库轮流取词；前 30 天平均 56 词，但
高频/固搭/同义库较早耗尽，后段天数会偏向必默，且第 24 天只有 49 词。
这正是 v2 与 v1 不一致的根因。

## 2. 计划存储与迁移

- v2 计划只存 `length`、`days_done`、`plan_updated_at`；每天词表由 `splitPlan` 实时计算。
- 因此**修正切分代码即可**让 felix 的计划第 24 天恢复为 57 词，不需要改库里的每日词表。

### 2.1 迁移脚本的根因（`tools/migrate_legacy.py`）

旧脚本：

```python
length = max(max(days), plan_days) if plan_days else max(days)
```

v1 的 `PLAN_DAYS` 固定 30，但旧库若存在脏数据 `day=34`，会把 v2 计划拉成 **34 天**。
按旧的全局平分：`1680 / 34 ≈ 49.4`，第 24 天正好 **49 词、49 题**，与用户看到的现象完全吻合。

修复：

```python
length = plan_days                      # 传了固定天数就以它为准
valid  = {d: r for d, r in days if 1 <= d <= plan_days}
done   = [d for d in valid if state == "done"]
```

超出 30 天的行忽略并输出 warning；新增单测 `test_map_plan_caps_at_fixed_plan_days`。

### 2.2 线上 felix 需要的修正（待授权执行）

1. 先备份 SQLite；
2. 查 felix 的 `plans` 行，确认 `length`（预期 34）与 `days_done`；
3. 仅修正该行：`length=30`、`days_done` 过滤 1..30、`plan_updated_at=<当前 epoch ms>`；
4. 客户端刷新后确认第 24 天 57 词、必默测试 72 题。

> 必须把 `plan_updated_at` 设为较新时间：同代际合取 `cli.length || srv.length`，
> 客户端本地旧的 34 会反覆盖服务端的 30。

## 3. 题量 72 vs 49（已用公开 v1 代码确认）

v1 公开站 `js/app.js`：

- `planWords(source, day)`：
  `a = floor((day-1)*L/PLAN_DAYS)`, `b = floor(day*L/PLAN_DAYS)`，`PLAN_DAYS=30`；
- `Q_TYPES.bimo = [w2m, m2w, spell]`；`gaopin/guding/tongyi` 各两型；
- `startPlanQuiz` 对计划测验设置 `forceAll: true`，即**每个词把该库全部题型各做一遍**。

因此第 24 天：

| 词库 | 词数 | 题型数 | 题数 |
|---|---|---|---|
| 必默 | 24 | 3 | **72**（用户看到的 v1 72 题） |
| 高频 | 14 | 2 | 28 |
| 固定搭配 | 9 | 2 | 18 |
| 同义替换 | 10 | 2 | 20 |
| 合计 | 57 | | 138 |

v2 的 49 = 旧切分 34 天 × 每词 1 题。修正切分 + 每词按题型出题后，v2 必默库同样 72 题。
切分、题型规则与 v1 完全一致，不需要为凑 72 额外改题目生成逻辑。

## 4. 验收与诊断命令（远程只读）

```bash
# 跳板机 → 代码服务器（连接方式由运维脚本提供）
# v1 代码（只读）
cd <v1 代码目录>
ls js/
grep -rn "PLAN_DAYS\|plan\|day\|quiz\|bimo\|spell" js/*.js | head -80

# v2 数据库（只读）
sqlite3 /path/to/pet.db \
  "select id,username from users where username='felix';
   select * from plans where user_id=(select id from users where username='felix');"

# v2 切分验算（本地即可）
# 用 frontend/public/data/banks.json + 新 splitPlan 计算第 24 天
```

> 所有命令只读；任何写库操作（修正 plans 字段）需先备份 SQLite 并再次确认。

## 5. 备选方案

| 方案 | 结论 |
|---|---|
| 保持全局平分，只把 v2 计划长度改成其他值 | ❌ 会让总天数/打卡错位，且仍不是每天四库 |
| 把每天词表落库 | ❌ 新增数据/同步字段，词库升级后过期 |
| 按 v1 的 ceil 顺序切片 | ❌ 最后几天会缺库（guding 第 30 天为 0），不满足每天四库 |
| **每库 floor 区间均匀切分（选定）** | ✅ 每库差 ≤1、每天四库、第 24 天 = 57，与 v1 一致 |

## 6. 风险

| 风险 | 缓解 |
|---|---|
| 题目生成规则与 v1 不一致 | 先只读确认 v1 代码，再决定如何对齐；不猜数字改逻辑 |
| 计划预览文案仍说「每天差 1」 | 改为「每种词库各自平均」 |
| 已完成天的打卡以天为单位，切分变化后旧进度仍有效 | 只影响每天词表，不影响 days_done 并集语义 |
| 远程写库风险 | 先备份 SQLite；只改 plans 字段；不碰其他表 |

## 7. 第 2 轮（exam 与 plan 的关系）

`splitPlan(banks, days)` 的 `banks` 由 `auth.exam` 决定：PET 用 bimo/gaopin/guding/tongyi，
KET 用 kword/kcore/kphrase/kconfuse/ksyn。计划行只存 `length / days_done`，
不存词表，因此**切换级别 = 按新级别重新切词**；打卡与掌握/错题不受影响。

- 迁移：旧站只有 PET，`map_users` 输出显式 `exam="pet"`，`write_new` 写入；
- 设置页：已有计划（`plan.length > 0`）时切换先弹确认，说明重切语义；
- 审计：`tools/check_user_exam.py` 按 mastery 词 id 前缀（b/g/d/t= PET，k= KET）
  以 90% 占比推断应属级别，默认只读，`--execute` 才更新。

KET 30 天第 24 天的 50 词 = 28+7+3+5+7（kword/kcore/kphrase/kconfuse/ksyn），
kword 题量 28×2=56；这是报障「50 词 / 56 题」的来源。
