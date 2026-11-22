# sync-v2（第二步：前端接线）/ 99 自省检查报告

日期：2026-11-22 · 范围：前端同步引擎接线（`core/sync.ts` + `stores/learning.ts`）

| 类别 | 检查项 | 结果 |
|------|--------|------|
| 需求 | U4 多端同步 / U5 防抖 1.2s + 静默 45s / U6 离线可玩 / U7 本地模式开关 — 全部有实现 | ✅ |
| 设计 | 引擎依赖注入（pull/push/持久化/定时器可替换），与 02-design §1 数据流一致 | ✅ |
| 代码 | vitest 16 passed（merge 6 + engine 5 + store 5）；vue-tsc + vite build 通过 | ✅ |
| 代码 | API 客户端已带 409 detail（服务端全量数据）供引擎合并重试 | ✅ |
| 测试 | 红线不变量（store 层）：dims 空 → 自动移出错题本并记掌握；答错 → 全维度重欠 + stage 回 0 | ✅ |
| 测试 | 引擎场景：pull 合并、防抖只推一次、push rev 前进、409 → 合并重试、网络失败 offline 且本地不丢 | ✅ |
| 依赖 | 新增 devDependency：jsdom（vitest DOM 环境，localStorage 测试必需） | ✅ |
| 同步 | 未改动合并语义本身（merge.ts 未变）；记忆曲线字段规则已获用户追认 | ✅ |
| 文档 | 本报告落盘；V11/P1 决议已入 04-功能清单 v1.1 | ✅ |

## 结论：PASS-with-notes

### 遗留项

1. **Alembic 未接入**（顺延，词汇迭代开头处理）。
2. **Quiz 提交页未接 store**：学习页面的答题动作尚未调用 `recordMastery/recordWrong/markPlanDayDone`（等词汇板块迭代时接线）。
3. **login 页未调用 `learning.connect()`**：路由守卫与登录后自动 connect 在下个迭代一起做（顺带加路由鉴权）。
4. 双开标签页并发写 localStorage 未加锁（家庭场景低风险，暂不处理）。
