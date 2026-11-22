# listening-v2 · 02 设计

## 数据链

```
PET/js/listening-data.js ──tools/build_listening_v2.js──▶ frontend/public/data/listening.json
PET/audio/listen/*.mp3 ──cp──▶ frontend/public/audio/listen/   (85MB, 24 文件)
PET/img/listen/*.png  ──cp──▶ frontend/public/img/listen/      (42 文件)
```

迁移规范化：
- 音频路径 → `/audio/listen/<file>`；图片 → `/img/listen/<file>`（站点绝对路径）
- 校验：tests 6 / parts 24 / items 150（42/72/36）、每 part 有 transcript 与 audio、choice 恰 3 选项、picture 有 img、fill answer 为字符串

## 前端模块

### `core/listening.ts`（纯函数 + 加载）

```ts
type LItem = { no, stem, answer, img?, options?, t0 }   // kind 由 part 决定
type LPart = { part, qRange, label, kind: "picture"|"choice"|"fill", audio, duration, transcript, sentences:[{t0,t1?,text}], items }
loadListening()            // fetch /data/listening.json，模块级缓存
isFillCorrect(input, answer)  // trim + 小写 + 全半角空白归一
gradePart(part, answers)   // → { right, total, wrongNos }，fill 用 isFillCorrect
mistakeKey(book, partNo, itemNo)  // `listen:t{book}:p{part}:q{no}`（book 已是 t1 前缀）
speak(text)                // 复用 reading.speak 的实现路径（本模块自带防重复）
```

### 页面

- **ListeningHome.vue**（`/listening`）：错题到期提示条 + 教材折叠（foldHtml 语义：单本默认展开）+ test 卡片（4 Part 行：label / 题数 / ✓ 已完成标记）→ 进入 Part 页
- **ListeningPartPage.vue**（`/listening/:testNo/:part`）：
  - 顶部音频播放器（自定义进度条 + 点击跳转 + 1/1.25 倍速切换）
  - 字幕区：当前句高亮（timeupdate 轮询 t0 区间）、点击句子跳转、「题 N」分隔条跳题目起点
  - 题目区：picture 显示题图；choice 三选项；fill 单输入框
  - 提交 → gradePart → 反馈区（对/错 + 每题回听按钮跳 t0）→ 错题记账 + ≥全部作答记进度
  - 到期错题置顶重考（只出欠的题）

## 状态接线

- `learning.recordWrong(key, ["q"])` / `recordRight(key, "q")`：与词汇同一条记忆曲线
- `learning.recordProgress("listen:{book}:{testNo}:{part}")`：完卷记进度
- 答题页不自动播放（浏览器手势限制），首帧给「▶ 播放本 Part 音频」

## 测试

`core/listening.test.ts`：isFillCorrect 归一化（大小写/空格/全角）、gradePart 三题型判分、mistakeKey 格式。
