# AI 优化与额度 · 需求（P0–P2）

> 依据：[AI优化与额度方案](../../AI优化与额度方案.md)（2026-11-24 草案，第 2 节修订清单）。
> 状态：实现中。默认值采用方案建议（日 ¥0.50 / 月 ¥10.00，80% 告警、100% 硬停用；管理员可开通）。

## 1. 背景与目标

口语是唯一持续产生外部费用的板块，但当前计量有盲区（shadow 会话、TTS、AI 加词），
也没有「付费 AI 默认关闭 + 按人预算 + 硬停用」的闸门。本功能补齐计量、预算与告警，
拆分管理页信息架构，并落地跟读句库、TTS 缓存治理、Realtime 模型配置与 A/B 能力。

## 2. 用户故事

- US-01 作为管理员，我希望给某个账号开通/关闭付费 AI，以便费用只发生在被授权的孩子身上。
- US-02 作为管理员，我希望给每个孩子设置日/月预算，并在 80% 时看到告警、100% 时自动停用付费接口。
- US-03 作为孩子，我希望未开通或额度用完时仍能浏览口语题库、用浏览器朗读、看标准答案。
- US-04 作为孩子，我希望跟读句子根据我的水平选难度，别太难也别太简单。
- US-05 作为管理员，我希望把「AI 配置 / 用户与额度 / 用量与预算」分开，避免误改。
- US-06 作为管理员，我希望看清 Realtime/TTS/SOE/LLM 的用量与预估费用，并能导出对账。
- US-07 作为管理员，我希望能在不换 Key 的情况下切换 Realtime 主/回退模型并保留一键回退。

## 3. 功能点

### P0

| 编号 | 功能 | 验收要点 |
|---|---|---|
| F-P0-1 | 每用户预算、付费闸门、告警 | `ai_enabled=false` → 403 `AI_NOT_ENABLED`；日/月超预算 → 429 `AI_BUDGET_EXHAUSTED`；80%/100% 站内横幅；管理员可开通/改预算/重置告警 |
| F-P0-2 | 计量补全 | shadow 会话上报；TTS 记字符/命中/费用；`enrich_word` 记 LLM；`sendBeacon` 补报 + 服务端超时补记；Realtime 文本 token 按估算写入；TTS/SOE/RT/Chat 单价可配 |
| F-P0-3 | 跟读句库 + 难度选句 | 句子含 difficulty/words/focus/source/active；按最近 3 次得分选 ±1 难度；免费模式跨库、计划模式包内排序；纯前端、可测试 |
| F-P0-4 | 管理页信息架构拆分 | 顶层「概览 / AI 配置 / 用户与额度 / 用量与预算」；每组独立保存；Key 只回显尾 4 位 |
| F-P0-5 | 单词音频兜底 | 静态音频失败回退浏览器 `say`；计划学习/测验补「听整句」入口 |

### P1

| 编号 | 功能 | 验收要点 |
|---|---|---|
| F-P1-1 | Realtime 模型 A/B 与配置档 | 主/回退/跟读模型、VAD 类型可配；主模型失败自动回退一次；管理页一键切回 |
| F-P1-2 | 画像按日缓存 | talk boot 复用当日画像；会话摘要生成后当日失效重建 |
| F-P1-3 | `improve` 节流 | 少于 4 个词不自动调用，改为用户点「帮我改」；调用次数明显下降 |
| F-P1-4 | TTS 缓存治理 | 默认 512MB 上限，按 mtime LRU；管理页显示数量/大小并可清理；失败不写缓存 |
| F-P1-5 | Realtime 连接复用 | 造句同一场景内复用连接，切换题目只发 `session.update`，减少 SDP 握手 |

### P2

| 编号 | 功能 | 验收要点 |
|---|---|---|
| F-P2-1 | 半双工/静音抑制 | AI 说话时暂停麦克风轨道，`response.done` 后恢复 |
| F-P2-2 | TTS 静态 URL | 接口返回可缓存的 URL，不再把 base64 WAV 塞进 JSON |
| F-P2-3 | 月度预测与账单核对 | 管理页显示月预测与按日明细；CSV 导出 |
| F-P2-4 | 免费用户降级 | 锁定付费按钮 + 明确文案；浏览器 TTS、看答案、无评分跟读可用 |
| F-P2-5 | 弱音素参与选句 | 记录 SOE 读错的词；选句时对命中 recent weak words 的句子加权 |

## 4. 边界与非目标

- 不替换 Realtime 默认模型；A/B 只提供配置能力，是否切换由管理员决定。
- 不做全量 TTS 预生成；只保留手动按 pack 预热的接口位（本期不做 UI 预热）。
- 不接入邮件/短信；告警仅站内横幅 + 管理端列表。
- 不改同步合并语义（红线）、不改错题本 dims 记账（红线）。
- 免费用户仍可使用口语模块的全部页面与静态数据；只是不调用付费接口。

## 5. 验收标准（Given/When/Then）

1. Given 用户 `ai_enabled=false`，When 调用 `/speak/improve`，Then 403 且 `detail.code=AI_NOT_ENABLED`。
2. Given 用户今日已用 ≥ 日预算，When 调用 `/speak/tts`，Then 429 且 `detail.code=AI_BUDGET_EXHAUSTED`。
3. Given 用量达到 80%，Then `/speak/ai_status` 返回 `stage=1`，前端显示黄色横幅；同一日只提示一次。
4. Given talk 会话在页面关闭时未调用 `session_end`，When 客户端 `sendBeacon` 补报，Then 记账一次；若 30 分钟仍无结束，Then 服务端按估算上限补记。
5. Given 同一句 TTS 第二次播放，Then 返回 `cached=true` 且不调用 TTS、不计费。
6. Given 最近 3 次跟读平均分 ≥85，Then 目标难度 +1；候选句均在 ±2（尽量 ±1）。
7. Given 免费用户进入跟读页，Then 不请求 SOE/TTS，可用浏览器朗读并查看句子。
8. Given 管理员清空 TTS 缓存，Then 缓存目录大小归零，后续播放重新生成。
9. Given 主 Realtime 模型返回非 2xx，Then 配置了回退模型时自动重试一次并返回实际使用的模型。
10. Given 管理页保存 LLM 组配置，Then 只写该组字段，不影响其他组与账号。

## 6. 影响面

- 后端：`users` / `usages` / `speak_logs` 加列；新增 `usage_alerts`、`ai_sessions`；新增 `services/budget.py`；`services/usage.py` 扩展 TTS 计量；`api/v1/speak.py` 拆出媒体路由；`api/v1/admin.py` 扩展额度/报表/缓存；`qwen_speak.py` 配置档与 TTS 缓存治理。
- 前端：`core/aiStatus.ts`、`core/sentenceBank.ts`、`core/say.ts`；`SpeakShadow` / `SentencePage` / `SpeakTalk` / `speakRTC`；`WordStudyCard` / `QuizPage`；`views/AdminPage.vue` 拆为多个组件。
- 数据：`data-src/speak/curriculum_v4.json` 兼容旧字段；`tools/build_speak_v4.js` 生成 difficulty/words/focus/source/active。
- 文档：`docs/02`、`docs/04`（v1.33）、`docs/05`、`docs/07`、本目录 01/02/99。
