# sync-v2 / 02 设计方案

## 1. 概览

```
前端 store 修改 → markDirty → 防抖 1.2s → POST /sync/push {rev, data}
                    ├─ 200 → 用返回 rev 更新本地基线
                    └─ 409 → merge(server.data, local.data) → 重试 push（最多 3 次）
登录/每 45s → GET /sync/pull → merge(server.data, local.data) → 写本地
```

## 2. API 契约

**GET /api/v1/sync/pull** → `{"rev": 7, "data": {mastery:[...], mistakes:[...], progress:[...], plan:{...}}}`

**POST /api/v1/sync/push**
```json
{"rev": 7, "data": {"mastery": [{"word_id": "w1", "mastered_dims": ["spell"]}]} }
```
- 200 → `{"rev": 8, "data": {...合并后全量...}}`
- 409 → `{"detail": "rev 冲突", "rev": 9, "data": {...服务端最新全量...}}`

Pydantic schema：`SyncItemMastery{word_id, mastered_dims[]}`、`SyncItemMistake{word_id, dims[], stage, due_at, repeats}`、
`SyncItemProgress{key, seen[], idx}`、`SyncPlan{length, days_done[]}`，容器 `SyncData{mastery[], mistakes[], progress[], plan}`。

## 3. 合并规则（红线 + 新增记忆曲线字段的规则）

| 数据 | 键 | 规则 |
|------|-----|------|
| mastery | word_id | mastered_dims 并集 |
| mistakes | word_id | dims 并集；stage 取小（欠得多）；due_at 取早；repeats 取小 |
| progress | key | seen 并集；idx 取大 |
| plan | 用户单条 | 同一代际 days_done 并集；创建/删除/改天数按 `plan_updated_at`（阅读 `reading_updated_at`）取较新一侧，删除写入 0 + 空打卡后不会被服务端旧计划并回来 |

> 计划时间戳是红线的**最小扩展**：同一代际的 days_done 仍然并集；只有创建/删除/改天数
> 这种结构性变更才切换代际。老数据时间戳为 0，保持原并集行为。

> **新增记忆曲线字段（stage/due_at/repeats）的合并规则为本设计的红线变更**：原则是「保留欠得多的状态」，
> 避免多端重复做题导致间隔被意外跳级。**待用户追认**（已在 99-self-review 标注）。

## 4. 数据模型

- `users.data_rev INT DEFAULT 1`（每次成功 push +1）。
- `mastery(user_id, word_id, mastered_dims TEXT, PK(user_id,word_id))`
- `mistakes(user_id, word_id, dims TEXT, stage INT, due_at TEXT, repeats INT, PK(user_id,word_id))`
- `progress(user_id, key TEXT, seen TEXT(JSON), idx INT, PK(user_id,key))`
- `plans(user_id, length INT, days_done TEXT(JSON), plan_updated_at BIGINT, reading_updated_at BIGINT, PK(user_id))`

日期统一 ISO 字符串（YYYY-MM-DD），避免时区序列化问题。

## 5. 备选方案与否决

- 增量 delta 同步（按变更日志）：否决——单用户数据量 < 10k 条，全量+合并更简单可靠。
- 服务端为准（last-write-wins）：否决——会丢多端进度，违背 U4 语义。

## 6. 风险

- 重复 push 竞态：rev 乐观锁覆盖；前端最多重试 3 次后降级为仅本地。
- 媒体/词库 ID 变更导致合并错位：word_id 用构建链稳定 slug，迁移脚本校验。
