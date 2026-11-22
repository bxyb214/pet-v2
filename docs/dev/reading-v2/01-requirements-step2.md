# reading-v2 第二步 — 需求（01-requirements）

用户输入（2026-11-22）：「reading 精读也要有进度，以及错题本。也需要制定计划，也需要手动增加新的句子，在某一个 test part 的文章中（自动选取的句子不一定是孩子不懂的）」。

## 功能需求

| # | 需求 | 说明 |
|---|---|---|
| R7 | 精读进度 | 学习页逐句进度持久化（key=`rstudy:book:test:part`，idx=已学到的句子下标），再次进入**续学**；完成即记完成日期 |
| R8 | 阅读错题本 | 句子按维度记账进 mistakes（word_id=句子 id）：meaning / blank / grammar:g<下标>；答错该维度重欠 + 回 1 天间隔（与词汇同一条记忆曲线语义）；测验**错题优先**出题（只考欠的维度）；首页显示到期数与「错题复习」入口 |
| R9 | 阅读计划 | 独立于词汇计划的**阅读计划**：用户自选天数，按 Part 顺序切分（ceil），当天所属 Part 测验 ≥60% 才打勾；可删除重建；词汇与阅读**各自独立勾选** |
| R10 | 手动加句 | 在指定 test+part 中添加自定义句子（en 必填，cn/key/note 选填）；进入该 Part 的精读与测验；走同步通道（custom_sentences，第五类+1）；可删除 |

## 边界

- 加句暂不做 AI 补全（后续复用 /words/custom/enrich 模式）。
- 阅读计划不跨教材选择——按数据顺序（Trainer 2 前 6 套 → Trainer 1 后 6 套？以 reading.json tests 顺序为准）线性覆盖全部 Part。
- 阅读错题不做手动删除（与词汇 V6 一致，走记忆曲线毕业）。

## DoD

1. Alembic 迁移：plans 表加 reading_length / reading_days_done；新表 custom_sentences。
2. SyncData 扩展 custom_sentences 与 plan 阅读字段，双侧合并语义一致并有测试。
3. 前端：store 新动作、ReadingStudy 续学、ReadingQuiz 错题优先 + 维度记账、ReadingHome 错题入口、PlanPage 阅读计划区、AddSentencePage。
4. 全量构建 + 测试通过；自省报告落盘。
