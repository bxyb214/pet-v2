> 2026-11-23 后续：本方案把四库合起来按总数平分；因与 v1「每种词库各自平均」不一致，
> 已改为每库独立 floor 区间切分，见 [vocab-plan-split-migration](../vocab-plan-split-migration/02-design.md)。

# 词汇计划预览校验修复 — 设计

## 1. 根因

`banks.json` 同时包含 PET 四库与 KET 五库。`PlanPage` 用
`availableBankKeys(banks, bankMeta, auth.exam)` 只切当前级别的库：

```ts
const plan = splitPlan(banks.value, days.value, activeKeys.value);
validateOk.value = validatePlan(banks.value, plan);   // ❌ 没传 activeKeys
```

`validatePlan` 默认遍历 `Object.keys(banks)`，把另一个级别的非空库也当成计划的一部分；
这些库在计划中为空，长度对不上 → 必然返回 `false`。
按钮 `v-if="previewDays.length && validateOk"`，所以只剩预览、无法确认。

## 2. 校验修复

`validatePlan(banks, plan, keys?)` 增加与 `splitPlan` 一致的 `keys` 参数，
只校验本次参与切分的库：

```ts
const order = (keys ?? Object.keys(banks)).filter((k) => (banks[k] ?? []).length > 0);
```

`PlanPage` 调用时传入 `activeKeys.value`。不传 `keys` 的旧用法仍校验全部非空库。

## 3. 切分调整（每天多一个少一个）

原实现按库 `ceil(库长/天数)` 切片：天数接近库长时会出现尾部空天，
且各天总量可能相差较大（例如 30 天时首日 57 词、末日 38 词）。改为按总数平分：

```text
total = Σ 当前级别词库长度
base  = floor(total / days)
rem   = total % days
第 d 天目标 = base + (d < rem ? 1 : 0)
```

每天从各库**轮流各取 1 个**，直到达到当天目标：

- 每天词量固定为 `base` 或 `base + 1`，相差不超过 1；
- 词数足够时不会产生空天；
- 各库内部顺序不变（游标只前进），不重不漏；
- 每天尽量覆盖所有启用词库，而不是前几天只切必默。

余下的 `while` 循环带 `progressed` 防御：所有库取完后立即退出。

## 4. 视图侧加固

- `banksReady`：`loadBanks()` 完成前置 false；`validDays` 增加 `activeKeys.length > 0`，
  词库未加载时「预览」不可点。
- `watch(days)`：天数变化即清空 `previewDays` 与 `validateOk`，避免确认时沿用旧天数。
- 预览摘要文案改为「每天约 N 词，多一个少一个」。
- 预览卡片展示全部天数（原 `slice(0, 8)` 去掉），30/45 天都能看到最后一天。

## 5. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 在校验里跳过「计划中为空」的库 | ❌ 会把真正的漏词也放过 |
| 保留每库 ceil 切片，仅修校验 | ❌ 天数大时仍有空天、每日差异大，不符合需求 |
| 全局连续切片再按天装填 | ❌ 前几天会只包含必默库，失去每天四库 |
| **校验传 keys + 按总数轮流切分（选定）** | ✅ 与级别隔离一致，每天均衡且覆盖各库 |

## 6. 测试

- `plan.test.ts`：30/10/45 天切分每日词量差 ≤1、无空天、库内顺序不变；
  子集词库校验通过、全量校验误报的回归用例；篡改仍能检出。
- 浏览器：PET 账号创建 30 天计划 → 预览无错误 → 确认生成 → 删除清理。
