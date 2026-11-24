# AI 优化与额度（ai-budget）— 自省报告

> 结论：**PASS**
>
> 后端与前端逻辑均有测试覆盖；`vue-tsc`、`vitest`、`vite build`、`check_tokens.py`、
> `check_overflow.js`（26 条路由 × 1440/820/390）全部通过；`speak.json` 已按 schema 5 重新生成。
> 仅剩需要真实 Key 的联调验收，见 §5。

## 1. 完成项

| 需求 | 结果 | 证据 |
|---|---|---|
| P0-1 每用户预算、80% 告警、100% 硬停、付费 AI 默认关、服务端闸门 | ✅ | `models/user.py`、`services/budget.py`、`core/deps.py`；403 `AI_NOT_ENABLED` / 429 `AI_BUDGET_EXHAUSTED`；`test_budget.py` |
| P0-2 计量补全（跟读会话、TTS 字符/缓存、enrich LLM、超时补记、文本 token、可配置单价） | ✅ | `services/usage.py`、`speak_profile.py`、`api/v1/speak*.py`、`ai_enrich.enrich_word(user_id)`；`test_tts_cache.py` |
| P0-3 跟读句库难度/词数/focus/source/active + 难度选句 | ✅ | `tools/build_speak_v4.js` schema 5；`speak.json` 已重新生成；`core/sentenceBank.ts` + `sentenceBank.test.ts` |
| P0-4 管理页拆为概览 / AI 配置 / 用户与额度 / 用量与预算 | ✅ | `views/AdminPage.vue` + `views/admin/*`（每个文件 ≤400 行，`adm-` 前缀共用样式） |
| P0-5 单词音频兜底 + 「听整句」 | ✅ | `core/say.ts`、`WordStudyCard.vue`、`QuizPage.vue` |
| P1-1 Realtime 主/备模型、VAD、MCP 开关、自动回退 | ✅ | `qwen_speak.proxy_sdp`、`pick_vad`；管理页可配 |
| P1-2 画像每日复用、会话总结后失效 | ✅ | `speak_profile.get_profile(rebuild=False)`、`invalidate()` |
| P1-3 improve 节流（≥4 词自动，否则点「帮我改」） | ✅ | `core/improve.ts`、`SpeakTalk.vue` |
| P1-4 TTS 缓存 512MB LRU、管理页查看/清理 | ✅ | `qwen_speak.enforce_tts_cache`、`/admin/tts_cache` |
| P1-5 同场景/句型包内复用 Realtime 连接 | ✅ | `speakRTC.updateInstructions`、`SentencePage.vue` 保留 `connLocal` |
| P2-1 AI 说话时静音麦克风（半双工） | ✅ | `speakRTC.ts` 监听 `response.created/done` |
| P2-2 TTS 静态 URL 替代 base64 | ✅ | `/speak/tts/file/{name}` + `immutable` 缓存头；前端全部改用 `playAudioUrl` |
| P2-3 月末预测 + CSV 导出 | ✅ | `/admin/usage/report`、`/admin/usage/export`、`api.downloadFile` |
| P2-4 免费用户降级 | ✅ | `core/aiStatus.ts`、各口语页锁定态、浏览器 `speechSynthesis` 兜底 |
| P2-5 弱词加权选句 | ✅ | `sentenceBank.rank()` 命中 `focus` 加权、`weakWordsFromRecent` |

## 2. 测试与检查

- 后端：`python -m pytest tests/ -q` → **117 passed**（基线 98 + 新增 19）。
  - `tests/test_budget.py`：未开通/预算为 0、日/月边界、告警去重、`max_session_sec`、
    `session_end` 幂等、跨用户会话拒绝、超时会话补记。
  - `tests/test_tts_cache.py`：缓存统计/LRU/清理、上限下限、命中不计费/未命中计费、静态 URL 头。
  - `tests/test_admin_ai.py`：额度覆盖与 null 恢复、非管理员 403、价格/预算保存、概览/报表/CSV/告警/重置、缓存接口、无 Key 连通性测试。
  - 迁移测试 `test_migration.py` 通过（新迁移 `e1a2b3c4d5e6`）。
- 前端：`vitest run` → **185 passed / 23 files**，含新增 `sentenceBank.test.ts`、`improve.test.ts`、`aiStatus.test.ts`。
- 类型与构建：`vue-tsc --noEmit` 退出码 0；`vite build` 成功。
- 设计令牌：`python tools/check_tokens.py` → OK（51 files / 40 tokens）。
- 横向溢出：`node tools/check_overflow.js` → 26 条路由 × 1440/820/390 **无横向溢出**。
- 数据：`node tools/build_speak_v4.js` 重新生成 `frontend/public/data/speak.json`（schema 5，
  45 包 / 135 跟读句 / 90 造句题 / 300 自由句；`shadow[0]` 带 `difficulty/words/focus/source/active`）。

## 3. 约束核对

- 未新增依赖；前端 HTTP 仍全部走 `core/api.ts`（新增 `apiBeacon`、`downloadFile` 也在此文件）。
- `src/core/` 纯逻辑可测；合并/同步语义与错题 `dims` 记账未改动。
- 密钥只从环境变量或 `app_cfg` 读取；管理接口只回尾 4 位，保存时掩码值自动还原。
- 新增文件均 ≤400 行；后端 snake_case、类 PascalCase；Vue 使用 `<script setup lang="ts">`。
- 数据文件未手改；`tools/build_speak_v4.js` 是唯一生成入口。
- 管理页对接口缺字段做了防御（概览/报表/缓存返回部分字段时不崩溃），便于后端未升级时仍可打开。

## 4. 风险与取舍

- **预算与账单是估算**：按官方换算率与配置单价计算，不替代供应商账单；管理页提供月度 CSV 对账。
- **告警是站内 + 管理端**：不接微信/邮件，避免新增外部依赖。
- **免费用户仍可听/读跟读句**，但不请求 SOE、不评分；这是产品取舍，已写入 04/S16。
- **管理页只有概览页在自动溢出检查中打开**；四个页签共用 `adm-` 布局与断点，其余页签由人工点选，未单独跑浏览器脚本。

## 5. 仍需真实环境验收（不阻塞本地完成）

1. 配置真实 Key 后：TTS 合成与缓存命中（第二次不计费、静态 URL 可播放）。
2. Realtime 主模型不可用时的自动回退、`session.update` 复用连接。
3. 关闭页面时 `session_end` 的 `sendBeacon` 补报与账单幂等（后端已有单测，需线上确认网关不拦 keepalive）。
4. 管理页四个页签的真实数据渲染与移动端人工验收。

## 6. 结论

**PASS**：P0–P2 全部落地，后端 117、前端 185 测试通过，类型检查、构建、令牌与溢出检查均绿，
数据已按新 schema 重新生成。剩余项均需真实供应商 Key 或人工点选验收，不影响代码完成判定。
