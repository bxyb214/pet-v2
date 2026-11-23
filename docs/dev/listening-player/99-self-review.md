# listening-player · 99 自省检查报告

- 日期：2026-11-23
- 范围：听力 Part 页改为纯播放器 + 可隐藏滚动字幕；修复 Part 跳转；下线听力错题入口

## 检查清单

| 类别 | 检查项 | 结果 | 说明 |
|---|---|---|---|
| 需求 | F-01～F-07 是否实现 | ✅ | Part 跳转、播放器、五档倍速、字幕高亮/滚动/隐藏、移除答题、下线错题入口、首页文案均已落地 |
| 设计 | 实现与 02-design 是否一致 | ✅ | 仅改 3 个前端文件 + 文档；数据层与后端零改动 |
| 代码 | 类型检查 | ✅ | `npm run build`（vue-tsc --noEmit + vite build）通过 |
| 代码 | 残留引用 | ✅ | `LISTEN_TABS` 与 `ListeningReview` 路由引用已清除，`ListeningReview.vue` 已删除；无硬编码密钥/绝对路径 |
| 代码 | 旧路径 redirect | ✅ | 阅读模块 `/reading/study/:testNo/:part`、`/reading/quiz/:testNo` 同步改为函数式 redirect，参数可正确展开 |
| 测试 | 单元测试 | ✅ | vitest 10 文件 / 82 用例全过 |
| 测试 | 浏览器冒烟 | ✅ | Chrome headless：首页点击 Part 1 → `/part/1/1`；5 档倍速；0.9× 生效；字幕 88 行、隐藏/恢复；页面 input=0、题卡=0、提交=0；点字幕第 41 行 → 高亮 + 容器 scrollTop=1207 + 开始播放；返回按钮回首页；旧链接 `/english/listening/1/1` 正确补全参数；`review` 回首页；console 无报错 |
| 依赖 | 新增依赖 | ✅ | 无新增；根目录 playwright 为既有 devDependency |
| 数据 | schema / 迁移 | ✅ | 无变更；`items` 字段保留但页面不再渲染 |
| 同步 | 是否触碰合并语义 | ✅ | 未触碰；仅停止写入听力错题/进度，不影响既有数据 |
| 部署 | 是否影响容器 | ✅ | 仅前端 dist；nginx 直接挂载，无需重启 |
| 文档 | 阶段文档 | ✅ | 01/02/99 已落盘；`docs/01` §2.3、`docs/04` L2–L4/L7 已同步 |

## 问题与修复

1. **Part 点击回单词页**：`ListeningHome` 拼成 `/english/listening/:no/:part`，与路由
   `/english/listening/part/:testNo/:part` 不符，命中兜底 redirect。
2. **旧路径 redirect 参数不展开**：Vue Router 的字符串 redirect 不会替换 `:params`，
   改为函数式 redirect；同时兼容旧错误链接。
3. **返回按钮**指向不存在的 `/english/listening`，改为 `/english/listening/home`。
4. **`.sub` 类名冲突**：页面副标题与字幕容器同名，导致样式互相污染；字幕容器改为 `.sub-box`。

## 结论

**PASS**

## 遗留项

1. 历史听力错题数据仍保留在本地/服务端，无界面入口，未做清理。
