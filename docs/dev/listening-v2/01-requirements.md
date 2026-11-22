# listening-v2 · 01 需求（F-3 / R 组延续）

> 迭代目标：听力板块迁移到 v2，并与 v2 的进度 / 错题本 / 同步体系打通。

## 功能范围

| # | 需求 | 说明 |
|---|------|------|
| L1 | 教材折叠首页 | Trainer 1（6 套）按教材折叠分组；每 test 卡片列出 4 个 Part（题型标签 + 题数 + 完成状态） |
| L2 | Part 练习页 | 音频播放器（进度条点击跳转 / 1.25 倍速）+ 逐句字幕（自动高亮当前句、点字幕跳音频、**点「题 N」分隔条跳该题起点**）+ 该 Part 题目作答 |
| L3 | 三题型 | picture 图选（题目配图）/ choice 三选一 / fill 笔记填空（大小写不敏感判分） |
| L4 | 听音红线 | 听力与词汇相反：**答题前必须能听音频**（听力本身考听）；提交前可反复听；反馈区可回听该题起点（t0 跳转） |
| L5 | 错题本接入 | 每题一维（`q`）：答错 → 错题本记 `listen:t{book}:p{part}:q{no}`，走同一记忆曲线；Part 测验到期错题优先 |
| L6 | 进度记录 | `listen:{book}:{testNo}:{part}`：Part 全部作答提交后记完成日期（seen 并集） |
| L7 | 数据迁移 | `PET/js/listening-data.js` → `frontend/public/data/listening.json`，音频 85MB + 选项图 42 张拷入 `frontend/public/{audio,img}/listen/` |

## 非目标（本轮不做）

- 听力计划（用户未提；词汇/阅读计划模式稳定后可复制）
- 手动加听力题
- 逐词评分（属口语板块）

## DoD

1. 迁移脚本校验零错误（题数 / 字幕 / 音频路径存在性）
2. pytest 26 + vitest ≥45 全绿，新增 listening 纯函数测试
3. build 通过，listening.json + 媒体文件进 dist
4. 自省报告落盘
