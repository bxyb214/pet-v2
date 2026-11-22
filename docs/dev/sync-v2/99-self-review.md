# sync-v2 / 99 自省检查报告

日期：2026-11-22 · 范围：docs/dev/sync-v2（01-requirements / 02-design）

| 类别 | 检查项                                                                                                          | 结果 |
| -- | ------------------------------------------------------------------------------------------------------------ | -- |
| 需求 | F-1 pull / F-2 push / F-3 合并语义 / F-4 前端 merge.ts / F-5 四类数据 — 全部有实现与测试                                       | ✅  |
| 设计 | 实现与 02-design.md 一致：API 契约、合并规则、数据模型逐条对应                                                                     | ✅  |
| 代码 | pytest 18 passed；vitest 6 passed；vue-tsc + vite build 通过                                                     | ✅  |
| 代码 | 无硬编码密钥/绝对路径；json 已正常 import；`__import__` hack 已清除                                                            | ✅  |
| 测试 | 合并核心（merge.py / merge.ts）覆盖全部规则分支：并集、取欠得多、单侧保留、idx 取大、并集排序                                                   | ✅  |
| 测试 | 关键不变量：409 → 合并 → 重试成功且旧数据不丢（test_push_conflict_409_and_merge_retry）                                          | ✅  |
| 测试 | 测试库与开发库隔离（conftest 独立 sqlite 临时文件）                                                                           | ✅  |
| 依赖 | 无新增依赖                                                                                                        | ✅  |
| 数据 | learning.py 4 张新表随 create_all 建；Alembic 尚未接入（见遗留项 1）                                                         | ⚠️ |
| 同步 | **触碰了合并语义**：新增 mistakes 的 stage/due_at/repeats 记忆曲线字段合并规则（取「欠得多」）——符合用户 V6/V7 批注意图，但属于红线变更，**待用户追认**（见遗留项 2） | ⚠️ |
| 文档 | 01-requirements / 02-design / 99-self-review 齐全；README 待功能全部迁移后统一更新                                          | ✅  |

## 结论：PASS-with-notes

### 遗留项

1. **Alembic 未接入**：当前 `create_all` 建表。接入 Alembic（生成初始迁移 + 后续变更可逆）排在下一迭代开头。
2. ~~记忆曲线字段合并规则待追认~~ → **已追认（2026-11-22，用户确认）**：mistakes 合并取 stage/due_at/repeats 的「欠得多」状态。
3. **前端 store 接线未做**：merge.ts 已就绪并有同语义测试，Pinia store 的 pull/push/防抖/45s 静默拉取接线是 sync 迭代第二步（涉及本地持久化层重构）。
4. FastAPI `on_event` 弃用警告：换 lifespan（低优先级）。
