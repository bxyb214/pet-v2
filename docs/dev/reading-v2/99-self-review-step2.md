# reading-v2 第二步 — 自省检查报告（99-self-review-step2）

日期：2026-11-22
范围：R7 精读进度 / R8 阅读错题本 / R9 阅读计划 / R10 手动加句

## 检查清单

| 检查项 | 结果 |
|---|---|
| Alembic 迁移（plans 加阅读字段 + custom_sentences 表 + word_id 拓宽至 160） | PASS — upgrade→downgrade→upgrade 演练通过；SQLite alter_column 走 batch 模式；补上 env.py 漏导入 models.extra（初始迁移漏了 app_cfg/custom_words，本迁移一并建上） |
| SyncData 扩展双侧合并（plan 阅读字段独立并集 / custom_sentences 按 sid 服务端优先） | PASS — pytest 26（+2 新例）、vitest 45（+9 新例） |
| 阅读计划切分不变量（Part 级不重不漏 / 余量末天吸收 / readingDayOf 反查） | PASS — vitest 3 例 |
| 错题维度（meaning/blank/grammar:g<i>）+ 复习只考欠的维度 | PASS — sentenceDims/itemForDim 测试 |
| R7 续学 | 实现完成（progressOf/setStudyIdx + ReadingStudy onMounted 恢复 idx），无单测（依赖 jsdom localStorage 交互，E2E 补） |
| 朗读红线保持 | PASS — 复习题走同一渲染路径，答题前无朗读 |
| E2E 同步冒烟（pull 空结构 → push 阅读计划+自定义句 → 全量回读） | PASS |
| 全量构建 | PASS — vue-tsc + vite build |

## 产物

- 后端：`models/learning.py`（Plan 两列 / word_id 160）、`models/extra.py`（CustomSentence）、`schemas/sync.py`、`services/merge.py`、`api/v1/sync.py`、迁移 `9add58f2e2c2_reading_step2`
- 前端：`core/merge.ts`（EMPTY_PLAN/mergeCustomSentences）、`core/plan.ts`（buildReadingPlan/validateReadingPlan/readingDayOf）、`core/reading.ts`（withCustomSentences/customSid/sentenceDims/itemForDim）、`stores/learning.ts`（setReadingPlan/deleteReadingPlan/markReadingDayDone/addCustomSentence/removeCustomSentence/setStudyIdx/progressOf）、`views/ReadingHome.vue`（错题入口）、`ReadingStudy.vue`（续学）、`ReadingQuiz.vue`（重写：错题优先+维度记账+计划打勾）、`PlanPage.vue`（阅读计划区）、新页 `AddSentencePage.vue`（/reading/add）

## 结论

**PASS-with-notes**

## 遗留项

1. `readingDayOf` 在 ReadingQuiz 完卷打勾时重算切分（与 PlanPage 同序同函数逻辑，但 Math.ceil 计算内联在 finishBookkeeping 里）——建议后续抽到 plan.ts 共用一处。
2. 加句页暂无 AI 补全（翻译/关键短语手填），后续复用 enrich 模式。
3. 阅读错题的 word_id 用句子 id / custom sid，与词汇 word id 同存 mistakes 表——天然无冲突（id 空间不同），但管理后台统计时要区分。
4. 自定义句挂在 part 上，若该 part 无原句（理论上不存在）会被忽略——数据约束由 UI 选择器保证。
5. 续学 E2E（Playwright）仍未排期。
