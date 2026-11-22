# reading-v2 迭代 — 设计（02）

## 数据链

```
PET/js/reading-data.js（旧站最终产物，window.PET_GRAMMAR + window.PET_READING）
  └─ node tools/build_reading_v2.js
       ├─ 规范化：test3–6 缺 no → 从 title/test 字段回填；补 book=t2 默认值
       ├─ 校验：id 唯一 / key∈en / gram.c∈1–42 / parse≥3 / gq 四选项+答案合法+why
       └─ 写 frontend/public/data/reading.json
            { grammar:{book,days}, books:[{id,name,desc}],
              tests:[{no,book,title,note,parts:[{part,kind,focus,sentences:[...]}]}],
              meta:{sentences,gq,built} }
```

句子字段平移：`id/en/cn/key/quiz/point/note/tense/parse/gram/gq/cs`。

## 前端结构

- `core/reading.ts`：`loadReading()`（fetch `/data/reading.json`，模块级缓存）、`bookOf(test)`、`testSentences(test)`、`buildQuizItems(sentences, pool, cap=24)` 纯函数（meaning/blank/grammar 三题型，干扰项取自全库 pool）、`grammarIndex(tests)`（c → 题目数组）。
- `views/ReadingHome.vue`：教材折叠组（沿用 05 规范组件模式）+ 语法专项 chips（按 10 天分组，无题考点禁用）+ 每 test 卡片（测整套 / Part 按钮）。
- `views/ReadingStudy.vue`：Part 内逐句 prev/next，展示 en/cn/parse/gram/note，`speechSynthesis` 听整句；末句「去做题」。
- `views/ReadingQuiz.vue`：复用测验组件模式（进度条 + ABCD 选项 + 底部提交）；答题前不朗读，反馈后「听整句」；完卷写 progress + 成绩单。
- 路由：`/reading`、`/reading/study/:testNo/:part`、`/reading/quiz/:testNo?part=` 与 `/reading/quiz/gc/:c`（语法专项）。查询参数带 label。

## 关键决策

1. **干扰项池 = 全库句子**（与旧站一致）：meaning 用其他句 cn、blank 用其他句 key；池不足 3 时该题跳过（旧站同语义）。
2. **quiz 构建为纯函数**：shuffle 注入随机源，测试可确定性断言。
3. **进度 key 设计**：`read:<bookId>:<testNo>:<part|all>`，idx 固定 1，seen 存做题日期（幂等重复写并集无害）。
4. test `no` 缺失时以 title 中数字回填，仍缺失则按位置编号（100+i 兜底不会触发）。
