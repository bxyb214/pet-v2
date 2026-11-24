# 用户端 AI 计费统计 — 设计

> 日期：2026-11-24；对应需求：[01-requirements](01-requirements.md)

## 1. 方案概览

```text
设置页 /settings（非管理员可见入口卡）
        │  router.push('/settings/usage')
        ▼
UsagePage.vue
        │  GET /api/v1/usage/me?month=YYYY-MM
        ▼
api/v1/usage.py  ──►  services/budget.status()  额度/开关/剩余
        │        └─►  services/usage.py        区间汇总 + 逐日明细
        ▼
usages 表（只读；无 schema 变更）
```

数据流：

1. 页面进入时以当前月调用一次 `/usage/me`。
2. 服务端从 `usages` 按 `user_id` + 日期区间汇总；同时调用 `budget.status` 取日/月预算状态。
3. 页面渲染额度卡、四区间汇总、所选月逐日表。
4. 用户切换月份时只重新请求 `/usage/me?month=...`，不重复请求额度状态之外的接口。

## 2. API 契约

### `GET /api/v1/usage/me`

鉴权：`Authorization: Bearer <access_token>`；无需管理员。

Query：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `month` | string | 否 | `YYYY-MM`；缺省当月（北京时间）。非法格式 422。 |

响应 `200`（示例）：

```json
{
  "month": "2026-11",
  "status": {
    "ai_enabled": true,
    "speak_enabled": true,
    "daily": {
      "used_milli": 12,
      "budget_milli": 500,
      "ratio": 0.024,
      "stage": 0,
      "reset_at": "2026-11-25T00:00:00+08:00"
    },
    "monthly": {
      "used_milli": 120,
      "budget_milli": 10000,
      "ratio": 0.012,
      "stage": 0,
      "reset_at": "2026-12-01T00:00:00+08:00"
    },
    "remaining_milli": 488,
    "max_session_sec": 1450,
    "blocked": false,
    "reason": "",
    "message": "",
    "alert_stage": 0
  },
  "totals": {
    "today": {
      "active_days": 1, "rt_seconds": 120, "rt_ai_seconds": 40,
      "soe_calls": 3, "llm_in_tok": 100, "llm_out_tok": 50, "llm_tok": 150,
      "tts_calls": 1, "tts_chars": 300, "tts_cache_hits": 2, "est_cost_milli": 12
    },
    "week": { "active_days": 2, "...": "同上字段" },
    "month": { "active_days": 5, "...": "同上字段" },
    "year": { "active_days": 20, "...": "同上字段" }
  },
  "days": [
    {
      "day": "2026-11-01", "rt_seconds": 120, "rt_ai_seconds": 40,
      "soe_calls": 3, "llm_in_tok": 100, "llm_out_tok": 50, "llm_tok": 150,
      "tts_calls": 1, "tts_chars": 300, "tts_cache_hits": 2, "est_cost_milli": 12
    }
  ]
}
```

说明：

- `est_cost_milli` 单位为 0.001 元，与现有记账一致。
- `totals.today` 恒为北京时间今天；`totals.week` 为本周一至今天；`totals.month` 为所选 `month`；`totals.year` 为当前自然年。
- `days` 只包含所选月份**有记账**的日期，按日期升序。
- `status.daily/monthly` 是当前时刻的额度状态，不随 `month` 参数变化。

错误：

| 状态 | 场景 |
|---|---|
| 401 | 未登录 / token 失效 |
| 422 | `month` 不是 `YYYY-MM` |

Pydantic schema（`backend/app/schemas/usage.py`）：

- `BudgetPeriodOut`
- `AiStatusOut`
- `UsageMetricsOut`
- `UsageTotalsOut(UsageMetricsOut)`，增加 `active_days`
- `UsageDayOut(UsageMetricsOut)`，增加 `day`
- `UsageTotalsBundle`：`today/week/month/year`
- `MyUsageOut`：`month/status/totals/days`

## 3. 数据模型

无变更。只读 `usages`：

| 字段 | 用途 |
|---|---|
| `day` | 区间过滤与逐日分组 |
| `rt_seconds` / `rt_ai_seconds` | 对话时长 |
| `soe_calls` | 跟读评测次数 |
| `llm_in_tok` / `llm_out_tok` | LLM token |
| `tts_chars` / `tts_calls` / `tts_cache_hits` | TTS 计费字符与缓存 |
| `est_cost_milli` | 预估费用 |

`budget.status()` 原有「告警去重写入」行为保留；本页只是读取，不新增记账点。

## 4. 前端变更

### 组件树

```text
SettingsPage.vue
└─ n-card（v-if="!auth.isAdmin"）「AI 计费」
   ├─ 今日 / 本月预估费用
   └─ n-button → /settings/usage

UsagePage.vue（新）
├─ 返回设置
├─ 额度状态卡（未开通 / 可用 / 已用尽 + 日/月进度）
├─ 四区间汇总卡（今日 / 本周 / 所选月 / 今年）
├─ 月份选择 + 逐日明细表
└─ 计费口径说明
```

### 路由

```ts
{
  path: "settings/usage",
  component: () => import("../views/UsagePage.vue"),
  meta: { crumbs: ["设置", "AI 计费"] },
}
```

### 类型与请求

新增 `frontend/src/core/usage.ts`：

- `UsageMetrics` / `UsageTotals` / `UsageDay` / `MyUsage`
- `loadMyUsage(month?: string)`：调用 `/usage/me`
- `fmtMilli` / `fmtMinutes` / `fmtChars` / `localMonth`：展示格式化纯函数，附 vitest

额度类型复用 `core/aiStatus.ts` 的 `AiStatus`。

### UI

- 沿用「绿野成长」token：`--c-primary`、`--c-line`、`--c-text-2/3`、`--r-card`、`--shadow-1`。
- 统计卡 4 列，窄屏 2 列；明细表外层横向滚动，避免窄屏溢出。
- 未开通 AI：中性提示并隐藏预算进度，历史用量照常展示；额度 80%：黄色；100%：红色。与口语页横幅口径一致。

## 5. 备选方案与取舍

**被否方案 A：在 `/settings` 里直接塞完整明细表。**
设置页已经有两张卡，再塞月度明细会让页面过长；独立页面更利于后续扩展（如导出、按功能拆分）。

**被否方案 B：复用 `/speak/usage_today` + `/speak/ai_status`，前端多次请求。**
只能拿今日数据，周/月/年需要额外接口；且 `usage` 是通用记账，不应绑定在 `speak` 路由下。
新增 `/usage/me` 一次返回所需数据，路径语义也更准确。

**采用方案：独立 `/usage/me` + `/settings/usage` 页面。**
好处：用户数据隔离清晰、接口可复用、前端只发一次请求；代价是新增一个 router 与 schema 文件，可接受。

## 6. 风险清单

| 风险 | 影响 | 缓解 |
|---|---|---|
| 越权读取他人用量 | 隐私泄露 | 接口不接受 `user_id`，只用 `get_current_user()` 的 `user.id`；测试覆盖双用户隔离 |
| 时区导致「今天/本周」错位 | 统计口径不一致 | 复用 `usage.today()` 的北京时间；周起点按北京时间周一计算 |
| 月份参数注入/非法值 | 查询异常 | FastAPI `Query(pattern=...)` 校验 `YYYY-MM`；非法 422 |
| 历史月份/空数据 | 页面空白或报错 | 服务端返回零值 + 空 `days`，前端显示空状态 |
| 页面加载触发额度告警写入 | 副作用 | 沿用 `budget.status` 既有幂等去重；不新增写路径 |
| 窄屏表格溢出 | 体验问题 | 表格容器横向滚动，汇总卡 2 列折叠 |

## 7. 测试计划

- 后端 `tests/test_usage_me.py`：
  - 未登录 401。
  - 新用户零值、无明细、`ai_enabled=false`。
  - 双用户数据隔离（A 查不到 B 的金额与明细）。
  - 今日 / 本周 / 所选月 / 今年区间汇总正确；跨年数据不混入今年。
  - `month` 非法 422；历史空月份返回零值。
  - 响应不含 `user_id` 字段。
- 前端 `core/usage.test.ts`：格式化函数边界（0、秒、分钟、万字符、月份补零）。
- 构建：`npm run build`（`vue-tsc --noEmit` + vite）。
- 手工：普通用户设置页入口、明细页、月份切换、未开通提示；管理员设置页不显示入口。
