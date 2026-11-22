# reading-v2 迭代 — 自省检查报告（99）

日期：2026-11-22
范围：阅读板块迁移（R1–R6）

## 检查清单

| 检查项 | 结果 |
|---|---|
| 数据迁移校验（id 唯一/key∈en/gram 1–42/gq 四选项/parse≥3） | PASS — 0 问题，12 套 test / 207 句 / 416 语法题 / 42 考点全覆盖 |
| reading.json 进产物（dist/data/） | PASS（676KB，含 banks.json 434KB） |
| 三题型构建不变量（4 选项恰 1 正确、挖空正确、cap、干扰池不足跳过） | PASS — vitest 6 例 |
| grammarIndex 聚合 | PASS |
| 朗读红线（答题前无朗读，反馈区听整句） | PASS — ReadingQuiz 仅反馈区有 speak 按钮 |
| 进度记录走 learning store（同步通道上行） | PASS — recordProgress（seen 并集 / idx 取大） |
| 路由守卫覆盖新页面 | PASS（全局 beforeEach） |
| 全量构建 + 测试 | PASS — vue-tsc+vite build、36 tests（6 files） |

## 本迭代产物

- `tools/build_reading_v2.js`（含规范化：test3–6 缺 no 回填）
- `frontend/public/data/reading.json`
- `core/reading.ts` + `core/reading.test.ts`
- `views/ReadingHome.vue`（教材折叠 + 语法专项 chips）/ `ReadingStudy.vue`（逐句精读）/ `ReadingQuiz.vue`（测验 + 语法专项复用）
- `stores/learning.ts` 新增 `recordProgress`

## 结论

**PASS**（无保留事项）

## 遗留项

1. ReadingStudy 的 parse/gram/note 在窄屏（<380px）的排布未实测，iPad 适配迭代（C4）统一处理。
2. 语法专项 label 用路由 query 传考点名，直接输入 URL 时 label 会缺省为「考点 N」——可接受。
3. 阅读进度目前只在测验完卷且 ≥60% 正确率时写入；「精读学习完成」不计进度（与旧站语义一致，如需改再议）。
4. 首页「计划今日入口」联动仍未做（词汇迭代遗留，随计划迭代统一）。
