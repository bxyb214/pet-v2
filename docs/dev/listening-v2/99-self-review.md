# listening-v2 · 99 自省检查报告

- 日期：2026-11-22
- 范围：听力板块迁移（数据 / 页面 / 错题本 / 进度）

## 检查清单

| 项 | 结果 | 说明 |
|---|---|---|
| 数据迁移校验 | ✅ | tests 6 / parts 24 / items 150（42/72/36）/ sentences 1799，字幕 t0 规范升序（修复 5 处旧数据乱序），音频/图片路径存在性校验通过 |
| 媒体进产物 | ✅ | dist/audio/listen 24 文件（85MB）、dist/img/listen 42 文件、listening.json 297KB |
| 纯函数测试 | ✅ | listening.test.ts 10 个：isFillCorrect 归一化 / gradePart 三题型 / 未作答算错 / 业务键格式 / activeSentenceIdx 二分与边界 |
| 前端全量 | ✅ | 55 passed（7 文件），vue-tsc + build 通过 |
| 后端回归 | ✅ | 26 passed（本轮后端零改动） |
| 朗读红线 | ✅ | 听力语义与词汇相反：音频答题前可反复听（听力本身考听），反馈区可回听题目起点 t0 |
| 错题本接入 | ✅ | 业务键 `listen:t{book}:p{part}:q{no}`，走同一记忆曲线（recordWrong/recordRight），review 页只考到期题 |
| 进度记录 | ✅ | `listen:{book}:{testNo}:{part}`，完卷才记（seen 并集），首页 ✓ 标记 |
| 1.25 倍速 | ✅ | 播放器倍速切换（M 组需求顺带落地） |

## 问题与修复

1. 旧数据 5 个 part 字幕 t0 乱序（OCR 时间轴拼接）→ 迁移脚本统一排序。
2. ListeningReview 模板绑定错位（cur 是 Job 包装对象）与嵌套引号 → 三轮修正后 vue-tsc 通过。

## 结论

**PASS**（无保留事项）

## 遗留项

1. 听力计划未做（用户未提，词汇/阅读模式稳定后可复制 Part 级切分）。
2. 字幕点击跳转的 E2E（浏览器手势/自动播放策略）留 Playwright 冒烟。
3. dist 含 85MB 音频，git 不宜入库（.gitignore 需补 public/audio；部署走 compose 卷或 CI 拷贝）——待部署迭代处理。
