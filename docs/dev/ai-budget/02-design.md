# AI 优化与额度 · 设计（P0–P2）

> 对应 [01-requirements](01-requirements.md)。不新增第三方依赖。

## 1. 方案概览

```text
浏览器
 ├─ 免费动作：题库/计划/时长/复盘到期/浏览器 TTS/看答案 ──► 无闸门
 └─ 付费动作：sdp/tts/soe_url/improve/help/check/review/boot(talk)/enrich
        │ Authorization
        ▼
 FastAPI
   deps.require_paid_ai(user, db)
        ├─ ai_enabled=false ─────────────► 403 AI_NOT_ENABLED
        ├─ 日/月已用 ≥ 预算 ─────────────► 429 AI_BUDGET_EXHAUSTED
        ├─ 记录 usage_alerts（80%/100%，按周期去重）
        └─ 放行 → 真正调用 Qwen / SOE / LLM → usage.record_*（同一事务提交）
        ▲
        └─ services/budget.py（限额、余额、max_session_sec、超时会话补记）
```

- 闸门在服务端，前端只做展示与降级，无法绕过。
- `usages.est_cost_milli` 仍是唯一账本；预算按日/月聚合它。
- Realtime 会话由 `ai_sessions` 跟踪：`sdp` 创建，`session_end` 关闭；超过 30 分钟未关闭，
  在下一次闸门/状态查询时按 `max_session_sec` 估算补记并关闭。

## 2. API 契约

### 2.1 用户端

`GET /api/v1/speak/ai_status`（登录即可，不查预算）

```json
{
  "ai_enabled": true,
  "speak_enabled": true,
  "daily": {"used_milli": 120, "budget_milli": 500, "ratio": 0.24, "stage": 0, "reset_at": "2026-11-25T00:00:00+08:00"},
  "monthly": {"used_milli": 1200, "budget_milli": 10000, "ratio": 0.12, "stage": 0, "reset_at": "2026-12-01T00:00:00+08:00"},
  "remaining_milli": 380,
  "max_session_sec": 1800,
  "blocked": false,
  "reason": "",
  "message": ""
}
```

- `stage`：0 正常，1 ≥80%，2 ≥100%。
- `blocked=true` 时 `reason ∈ {not_enabled, daily_exhausted, monthly_exhausted}`。
- `max_session_sec = min(1800, floor(remaining_milli / COST_PER_SEC_MILLI))`，`COST_PER_SEC_MILLI≈0.1`。

`POST /speak/sdp`（付费）

请求不变；响应增加：

```json
{"sdp": "v=0...", "model": "qwen3.8-omni-flash-realtime", "voice": "Tina", "vad": "semantic_vad", "session_id": 12, "max_session_sec": 900}
```

`POST /speak/session_end`（免费，只记账）

```json
{"seconds": 600, "ai_seconds": 120, "mode": "talk", "session_id": 12}
→ {"est_cost_milli": 87, "remaining_milli": 413}
```

`POST /speak/tts`（付费）

```json
{"text": "In this photo I can see ...", "voice": ""}
→ {"url": "/api/v1/speak/tts/file/<sha1>.wav", "mime": "audio/wav", "cached": true, "chars": 42}
```

`GET /speak/tts/file/{name}`：只允许 `[0-9a-f]{40}\.wav`，`Cache-Control: public, max-age=31536000, immutable`。

`GET /speak/shadow/recent?limit=10`：`{"items":[{"id":1,"sentence_id":"s01-1","score":88,"ref":"s01","created_at":"..."}]}`

`POST /speak/log` 的 `LogIn` 增加 `sentence_id: str = ""`、`words: list[dict] = []`。

### 2.2 管理端

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/admin/ai/overview` | 今日费用、告警数、已开通用户数、Provider 配置摘要、TTS 缓存 |
| GET | `/admin/ai/prices` | `usage.prices` + `ai.budget` + `speak.tts_cache` |
| PUT | `/admin/ai/prices` | 保存上述三类配置（单次只写一个 key 也可沿用 `/admin/cfg`） |
| GET | `/admin/users` | 行内增加 `ai_enabled`、预算、今日/本月已用、`alert_stage` |
| PUT | `/admin/users/{id}/ai` | `{"enabled":bool,"daily_milli":int|null,"monthly_milli":int|null}` |
| POST | `/admin/users/{id}/ai/reset_alert` | 清除该用户告警去重记录 |
| GET | `/admin/usage/alerts?month=` | 告警列表 |
| GET | `/admin/usage/report?month=` | 月度预测、按日、按人汇总 |
| GET | `/admin/usage/export?month=` | CSV（date,user,rt_seconds,soe_calls,llm_in,llm_out,tts_chars,est_cost_milli） |
| GET | `/admin/tts_cache` | `{files,bytes,max_mb}` |
| DELETE | `/admin/tts_cache` | 清空缓存 |
| POST | `/admin/test/{kind}` | `llm / tts / soe / realtime` 最小连通性检查 |

错误统一（仅闸门）：

```json
{"detail": {"code": "AI_NOT_ENABLED", "message": "此功能调用外部 AI 接口，有费用，需要找小淏开通。"}}
{"detail": {"code": "AI_BUDGET_EXHAUSTED", "message": "今日 AI 额度已用完，免费功能仍可用。", "reset_at": "2026-11-25T00:00:00+08:00"}}
```

### 2.3 配置

- `ai.budget`（JSON，app_cfg）：`daily_milli=500, monthly_milli=10000, alert_ratio=0.8, hard_stop=true, currency=CNY, timezone=Asia/Shanghai`。
- `usage.prices` 增加 `tts_per_kchar=0.08`（元/千字符，估算值，可改）。
- `speak.tts_cache`（JSON）：`{"max_mb": 512}`。
- `speak.qwen` 增加：`fallback_model`、`vad`（`semantic_vad|server_vad|smart_turn|smart_turn_v2`）、`mcp`（bool）。

## 3. 数据模型

### 3.1 Alembic（单迁移，可回滚）

```text
users
  + ai_enabled BOOLEAN NOT NULL DEFAULT 0
  + ai_daily_budget_milli INTEGER NULL
  + ai_monthly_budget_milli INTEGER NULL

usages
  + tts_calls INTEGER NOT NULL DEFAULT 0        # 实际调用 TTS 次数（未命中）
  + tts_chars INTEGER NOT NULL DEFAULT 0        # 计费字符数（未命中）
  + tts_cache_hits INTEGER NOT NULL DEFAULT 0   # 缓存命中次数（不计费）

speak_logs
  + sentence_id VARCHAR(32) NOT NULL DEFAULT ''
  + words TEXT NOT NULL DEFAULT '[]'            # SOE 逐词结果 [{"w","ok"}]

usage_alerts (new)
  id PK, user_id, period('day'|'month'), period_key, stage(1|2), created_at
  UNIQUE(user_id, period, period_key, stage)

ai_sessions (new)
  id PK, user_id, mode, started_at, closed_at NULL, status('open'|'closed'|'expired'),
  seconds, ai_seconds, text_in_tok, est_cost_milli
```

迁移数据：`UPDATE users SET ai_enabled=1 WHERE is_admin=1`。
新管理员（首次 claim）在 `auth.claim` 中直接 `ai_enabled=True`。

### 3.2 成本模型

```text
cost = rt_audio_in_tok/1e6*rt_audio_in + rt_audio_out_tok/1e6*rt_audio_out
     + rt_text_in_tok/1e6*rt_text_in + rt_text_out_tok/1e6*rt_text_out
     + soe_calls*soe
     + llm_in_tok/1e6*llm_in + llm_out_tok/1e6*llm_out
     + tts_chars/1000*tts_per_kchar
```

文本 token 估算（服务端，不信任客户端）：`text_in_tok = ceil(instructions_chars/4)`（默认 1200 字符），
`text_out_tok = ceil(ai_seconds*3)`。

## 4. 前端变更

### 4.1 新增核心模块

- `core/aiStatus.ts`：`loadAiStatus(force?)` 模块级缓存、`paidBlocked(status)`、`budgetBanner(status)`；
  纯函数 `deriveBlockReason`、`formatResetAt` 可测。
- `core/sentenceBank.ts`：`targetDifficulty(recentScores)`、`hashSeed`、`pickSentences(input)`；
  输入 `{sentences, recent, weakWords, packId?, count, userId, date}`；输出稳定排序后的句子。
- `core/say.ts` 增加 `playWordAudio(audioPath, word)`：先试静态音频，失败/缺失回退 `say(word)`；
  `speak(text)` 用于 TTS 失败/免费降级的浏览器朗读。
- `core/improve.ts`：`shouldAutoImprove(text)`（≥4 词）与 `ImprovementQueue` 节流（同句去重、最多 1 并发）。

### 4.2 页面

| 页面 | 变更 |
|---|---|
| `SpeakShadow` | 免费/额度不足显示锁定条；无钱仍可浏览器朗读与看句；难度选句；`sentence_id`/`words` 上报；TTS 用 URL；TTS 失败回退浏览器 |
| `SentencePage` | 同场景复用 Realtime 连接；无付费权限时隐藏语音入口、保留看答案 + 浏览器朗读；TTS URL |
| `SpeakTalk` | 开始前查 `ai_status`；80%/100% 横幅；`pagehide` 用 `sendBeacon` 补报 `session_end`；显示 `max_session_sec` 到点结束；improve 节流 + 「帮我改」按钮 |
| `SpeakHome` | 顶部显示额度横幅（若已加载）；付费入口锁定态 |
| `WordStudyCard` / `QuizPage` | 静态音频失败回退 `say`；学习卡/测验反馈增加「听整句」 |
| `AdminPage` | 拆为 `admin/AdminOverview`、`AdminAiConfig`、`AdminUsers`、`AdminUsage`；顶层四组，每组独立保存 |

### 4.3 免费降级

- 未开通：跟读页只显示句子、浏览器朗读、提示「跟读评分需要找小淏开通」；造句页可看答案、浏览器朗读；
  对话页开始按钮禁用并提示。
- 额度用尽：与未开通同样的锁定，但文案改为「今日/本月额度已用完，免费功能仍可用」。

## 5. 备选方案与取舍

- **备选 A：前端拦截付费按钮，不查服务端。** 否决：可绕过、无法应对多端/改本地缓存。
- **备选 B：按供应商账单月结，不做实时预算。** 否决：孩子连续使用会超支，无法硬停用。
- **备选 C：Realtime 文本 token 直接移除。** 部分采纳：保留字段并做服务端估算，避免账本字段空转；
  比例很小，估算误差可接受。
- **备选 D：跟读也复用 SOE 连接。** 否决：SOE 每次签名/评测是独立会话，复用收益低、风险高；
  复用改为造句页的 Realtime 连接。

## 6. 风险清单

| 风险 | 缓解 |
|---|---|
| 旧账号升级后付费接口全部 403 | 迁移把管理员置为开通；普通用户按方案默认关闭，管理页一键开通 |
| shadow 会话漏记 | `sdp` 建 `ai_sessions`，30 分钟超时补记；`sendBeacon` 双保险 |
| TTS 缓存无限增长 | 512MB 上限 + mtime LRU；管理页可清理 |
| 选句算法不稳定 | 纯函数 + 稳定 hash；单测覆盖 ±1、不重复、同日稳定 |
| 管理页重写影响现有配置 | 保留 `/admin/cfg` 契约与掩码合并；按组分保存 |
| 半双工影响打断体验 | 仅 AI 说话期间暂停轨道，`response.done` 立即恢复 |
| 无法在本机跑前端检查 | 记录在 99 自省；交付前在装有 Node 的机器执行 vue-tsc/vitest/build |
