# 口语 15+15 与手动计划 — 设计

## 方案概览

```
口语首页
 ├─ 计划卡：无计划 → 创建；有计划 → 仅删除
 │    └─ 日历 / 当天场景（来自 161 题库）
 ├─ 跟读页：5 分钟计时提示 + 按计划日取 packs 句子
 ├─ 造句页：10 分钟计时提示
 ├─ 对话页：15 分钟（10 分钟对话 + 5 分钟复盘）
 │    └─ 每轮即时优化 + 就地跟读 → 结束同页复盘
 └─ 场景题库：161 个真题场景按 Part 独立浏览/练习
```

复盘不再有独立页面；`SPEAK_TABS` 为 计划 / 跟读 / 造句 / 对话 / 题库。

## 后端

| 文件 | 变更 |
|---|---|
| `models/speak.py` | 新增 `SpeakPlan`（user_id PK、length、updated_at） |
| `alembic/versions/f3a9c1d7e2b4_speak_plan.py` | 新建 `speak_plans` 表，`down_revision=b7c1f2a90d34` |
| `api/v1/speak.py` | 新增 `GET/PUT/DELETE /speak/plan`；新增 `POST /speak/improve`；新增 `POST /speak/review/import` |
| `services/speak_review.py` | 新增 `import_items()`：同一 log + child_said 幂等更新，不清已有评分 |
| `core/deps.py` | 管理员支持 `!speak` 显式关闭；否则保持默认开通 |
| `api/v1/admin.py` | 管理员关闭自己时写入 `!speak`，开启时清除 |
| `tests/test_speak.py` | 计划 CRUD、复盘导入/评分 |
| `tests/test_admin_perms.py` | 管理员关闭/重开自己的口语权限 |

### API 契约

```
GET    /api/v1/speak/plan          → {"length": 0|1..90}
PUT    /api/v1/speak/plan          {"length": 1..90} → {"length": n}
DELETE /api/v1/speak/plan          → {"length": 0}
POST   /api/v1/speak/improve       {"text","last_ai_text","scene_title"}
       → {"child_said","improved_en","improved_cn","focus","dims"}
POST   /api/v1/speak/review/import {"log_id","items":[{child_said,improved_en,improved_cn,focus,dims}]}
       → {"items":[ReviewItem...]}
```

`/speak/improve` 走 `ai_enrich.chat` 并记账；未配 Key 返回 503，前端静默跳过、结束后退回
原有 `/speak/review` 整段生成。

## 前端

| 文件 | 变更 |
|---|---|
| `core/speak.ts` | 扩展 `SpeakPlan.days`；新增 `splitSpeakPlan(data, length)`、`planDayDone`、`sourceRangeText` |
| `core/speakPlan.test.ts` | 30/90/7 天切分、覆盖性、旧编号不使用、完成判定 |
| `views/SpeakHome.vue` | 无计划只显示创建、有计划只显示删除；日历按用户天数；当天场景；入口改为 5+10+15；移除首页全部场景展开 |
| `views/SpeakShadow.vue` | 5 分钟计时提示；按计划日取 packs 句子；按 sourceDays 写打卡；移除复盘跳转 |
| `views/SentencePage.vue` | 10 分钟计时提示 |
| `views/SpeakTalk.vue` | 15 分钟（10+5）计时提示；每轮 `/speak/improve` 内联卡；结束就地复盘；导入+评分 |
| `views/SpeakScenes.vue` | 新增 161 场景题库：按 Part 筛选、搜索、单独进入对话 |
| `components/SpeakImproveCard.vue` | 优化句展示、TTS、SOE 跟读、评分反馈 |
| `views/SpeakReview.vue` | 删除（能力并入对话页） |
| `router/index.ts` | 移除「复盘」页签/路由；新增「题库」页签/路由；旧链接重定向 |
| `views/AdminPage.vue` | 管理员开关不再禁用；文案改为可关闭自己 |

### 计划切分

- 源天数固定 90（`plan.days.length`），用户天数 N 连续分组，不重不漏。
- 每日内容按比例从 `packs` 取（19 个包，114 句）和 `scenes` 取（161 个场景），
  **不使用**旧的 `plan.days[].shadow/scene` 编号。
- 每个计划日同时保留 `shadowIds`、`sceneIds`、`sceneTitles`；首页显示当天场景，题库独立浏览。
- 完成判断：该计划日包含的所有原始天都有 `shadow_done && talk_done`。
- 计划卡动作：`hasPlan` 时只渲染删除，否则只渲染创建；改天数必须先删后建。

### 计时

- 跟读：进入页面开始计时，300s 后变色提示，不强制退出。
- 造句：进入页面开始计时，600s 后变色提示。
- 对话：从「开始对话」计时，600s 后提示可进入复盘；复盘从点击结束时计时，300s 后提示。
- 所有计时段都只做 UI 提示，不自动关闭连接或跳页。

## 数据与红线

- 口语计划存独立表，**不进入** SyncData / merge_plan，合并语义零改动。
- 复盘句仍走 `speak_reviews` 的 1/2/4/7/15 天记忆曲线，dims 记账规则不变。
- 密钥仍只在服务端配置。

## 风险

| 风险 | 缓解 |
|---|---|
| 旧 plan.days 编号与 v3 不一致 | 内容改从 packs/scenes 按比例取，并加单测防回归 |
| 每轮调用 LLM 增加费用 | 仅对 ≥3 字符的回答调用；失败静默；用量照常记账 |
| 管理员关闭自己后无法用口语 | 管理后台只依赖 `is_admin`，仍可重新打开 |
| 老复盘链接 404 | 路由重定向到口语首页 |
