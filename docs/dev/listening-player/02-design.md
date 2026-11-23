# 听力 Part 页改版 — 设计

## 方案概览

把 `ListeningPartPage` 从「音频 + 题目 + 作答 + 判分」改为纯播放器：

```
返回听力列表
标题 / Part 标签
┌ 播放器 ────────────────────────────┐
│ [播放/暂停]  0.8 0.9 1.0 1.1 1.2  [字幕 开] │
│ 00:00 ─────────●────────────── 09:18 │
└────────────────────────────────────┘
┌ 字幕（可隐藏，滚动）────────────────┐
│ … Boy: What are you bringing…       │
│ ▸ Girl: My mum bought some…         │  ← 当前句高亮
│ …                                   │
└────────────────────────────────────┘
```

## 前端变更

| 文件 | 变更 |
|---|---|
| `views/ListeningHome.vue` | 修正 `goPart` 为 `/english/listening/part/:testNo/:part`；删错题提醒、完成勾选与相关 store 依赖；更新文案 |
| `views/ListeningPartPage.vue` | 重写为纯播放器 + 可隐藏滚动字幕；移除题目/作答/判分/错题记账 |
| `router/index.ts` | 删除听力「错题」页签与 `/english/listening/review` 路由，改为重定向到首页；`/listening/review` 同步指向首页 |

## 关键实现

- 复用 `core/listening.ts` 的 `loadListening` 与 `activeSentenceIdx`，不改数据层。
- 倍速常量 `RATES = [0.8, 0.9, 1.0, 1.1, 1.2]`；切换时写 `audio.playbackRate`。
- 字幕高亮由 `timeupdate` 计算当前句索引；`watch(activeIdx)` + `nextTick` 把当前行滚到字幕容器中部。
- 字幕默认显示，按钮带 `aria-pressed`；隐藏用 `v-show`，不销毁音频。
- 音频事件 `play/pause/ended` 同步 `playing` 状态，避免按钮显示与真实状态不一致。

## 数据与接口

无 schema/API 变更。`items` 字段保留在 JSON 中但页面不再读取。

## 风险

| 风险 | 缓解 |
|---|---|
| 用户已有的听力错题记录失去入口 | 数据保留，不删除；后续如需要可另做复习页 |
| 旧书签指向错题页 | 路由改为 redirect 到听力首页，避免落到单词页 |
| 自动滚动带动整页 | 只改字幕容器 `scrollTop`，不使用 `scrollIntoView` |
