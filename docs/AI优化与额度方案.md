# PET v2 AI 优化与额度方案（已实施）

> 状态：**已实施**（2026-11-24，分支 `feat/ai-budget`）。本文件保留为设计与验收基线；实现细节、测试与已知缺口见 [dev/ai-budget](dev/ai-budget/)。
> 关联：[07 口语实时对话方案](07-口语实时对话方案.md)、[04 功能清单](04-功能清单.md)、[06 部署与运维](06-部署与运维.md)。
> 本文件取代此前对话中的 P0–P2 口头清单；第 2 节是修订后的正式版本。

## 0. 结论先行

1. **单词、阅读的发音不调用 AI**：浏览器 `speechSynthesis` / 静态音频，边际成本为 0。当前的主要问题是计划学习/测验的词音频文件缺失，以及例句没有发音入口。
2. **口语是唯一持续产生费用的板块**：4 类接口——Qwen Realtime、腾讯 SOE、Qwen TTS、Qwen Chat。Realtime 约占七成。
3. **跟读句不做全量预生成**：句库可能更换，采用「未命中再生成、只生成一次、按句缓存」；同时建立带难度的跟读句库，由 PET 选择合适难度。
4. **每个用户默认能用口语模块，但付费 AI 默认关闭**：调用外部 AI 前提示费用，需管理员（小淏）开通；开通后按用户预算记账，80% 告警、100% 硬停用。
5. **管理页拆分**：AI 配置、用户与额度、用量与预算三块分开，不再把所有东西混在一个标签条里。
6. **Realtime 模型不盲目替换**：`qwen3.8-omni-flash-realtime` 与 `qwen-audio-3.1-realtime-flash` 同价，先做 A/B；确认 15 分钟上下文、工具调用、VAD 兼容后再切换。

## 1. 现状盘点

### 1.1 发音链路

| 场景 | 实现 | AI 费用 |
|---|---|---|
| 词库浏览（单词/例句） | 浏览器 `speechSynthesis`（`core/say.ts`，优先 en-GB） | 0 |
| 计划学习卡（单词） | 浏览器 `speechSynthesis`（`core/say.ts`，点击内同步调用） | 0 |
| 计划测试/测验（单词） | 同上（`QuizPage.vue`）；w2m 答题前自动朗读，其余答后手动 | 0 |
| 阅读精读/测验 | 浏览器 `speechSynthesis`（`core/reading.ts:128`，en-US） | 0 |
| 口语示范 | Qwen TTS（`qwen_speak.py:191`），按句 sha1 磁盘缓存 | 按字符，未记账 |

### 1.2 口语 AI 调用

| 接口 | 模型/服务 | 用途 | 触发 | 当前记账 |
|---|---|---|---|---|
| Realtime | `qwen3.8-omni-flash-realtime` | talk 对话；shadow 的「AI 点评」 | 每次会话/每次跟读建立 WebRTC | 仅 talk 的 `session_end` |
| SOE | 腾讯智聆口语评测新版 | 精准发音、优化句跟读、复盘跟读 | 每次签发 WSS URL | ✅ 按 20 词折 1 次 |
| TTS | `qwen3-tts-flash` | 跟读目标句、句型、优化句示范 | 用户点播放 | ❌ 只缓存 |
| Chat | `qwen3.8-flash`（OpenAI 兼容） | `improve` / `help` / `check` / `review` / 摘要 / 画像 / 加词 | 对应接口 | 除 `enrich` 外基本 ✅ |

### 1.3 成本基线

单价来自 `backend/app/services/usage.py:21` 与 `docs/07`（配置值，不是供应商账单）：

| 项 | 单价 |
|---|---|
| Realtime 音频输入 | 6 元/M tok，7 tok/s |
| Realtime 音频输出 | 12 元/M tok，12.5 tok/s |
| Chat 输入/输出 | 0.8 / 2.7 元/M tok |
| SOE | 资源包约 0.001 元/次；后付费约 0.005 元/次 |
| TTS | 按字符，**无单价、无记账** |

| 场景 | 每天 | 每月/人 |
|---|---|---|
| 单词 + 阅读发音 | ¥0 | ¥0 |
| 5 分钟跟读 + 10 分钟造句 + 15 分钟对话 | ≈¥0.13–0.18（不含 TTS） | ≈¥4–5.5 |
| 30 分钟全部 Realtime（文档旧估法） | ¥0.22–0.34 | ¥7–10 |
| 重度 60 分钟 talk/天 | ≈¥0.38 | ≈¥11 |

### 1.4 计量盲区（预算的前置问题）

- shadow 的 Realtime 时长没有上报：只有 talk 调 `/speak/session_end`。
- TTS 不记次数/字符/费用。
- `enrich_word` 调了 LLM 但没有 `record_llm`。
- talk 中途关页不调 `session_end`，会漏记。
- `rt_text_in/out_tok` 字段存在但从未写入。
- 结论：**不先补齐计量，预算硬停用就不可信。**

## 2. 修订后的优化清单

### 2.1 原建议 → 修订

| 原建议 | 修订后 | 原因 |
|---|---|---|
| P1-5 固定内容全量预生成 TTS | **P0-3 跟读句库 + 懒缓存**：未命中再生成，只生成一次 | 句子可能更换；全量预生成会白花钱、产生孤儿文件 |
| P2-9 直接换更便宜的 Realtime | **P1-1 模型 A/B 与可配置切换**：先评估再换 | 两个模型同价；真正的差异在上下文、VAD、工具调用、延迟 |
| P2-11 加预算/告警 | **P0-1 每用户预算 + 80% 告警 + 100% 硬停用** | 这是产品与成本控制的核心，不再放 P2 |
| （新增）管理页 AI 与用户混排 | **P0-4 管理页信息架构拆分** | 配置、账号、额度、用量是四类操作，混在一起容易误操作 |

### 2.2 P0（上线前必须）

**P0-1 每用户预算、告警与付费闸门**

- 口语模块默认可用；付费 AI 默认关闭，需管理员（小淏）开通。
- 每个用户有日预算与月预算；80% 告警，100% 停用付费接口。
- 所有付费接口统一走服务端闸门，前端不可绕过。
- 详见第 5 节。

**P0-2 计量补全**

- shadow 结束上报 Realtime 时长（`elapsedSec`/`speechSec`）。
- `/speak/tts` 记录字符数、是否命中缓存、预估费用。
- `enrich_word` 记录 `record_llm`。
- talk `pagehide` 用 `sendBeacon` 补报；服务端记录会话开始时间，超时未结束按估算补记。
- Realtime 文本 token 按 instructions/transcript 估算写入 `rt_text_*`，或明确从成本模型中移除该项。
- 为 TTS/SOE/Realtime/Chat 分别保留可配置单价。

**P0-3 跟读句库 + TTS 懒缓存**

- 建立统一跟读句库，带难度、词数、语音重点、来源、启用状态。
- PET 按最近得分和难度选句；自由模式跨库选，计划模式保留 pack 主题、在包内按难度排序。
- TTS：先查缓存，未命中再调模型，成功写缓存；同一句只生成一次。
- 详见第 3 节。

**P0-4 管理页 AI 配置重构**

- 顶层分「AI 配置 / 用户与额度 / 用量与预算」，AI 配置不再和账号管理混在一起。
- 每个分组独立保存，避免一个全局“保存配置”误改账号。
- 详见第 6 节。

**P0-5 单词音频修复/兜底**（2026-11-24 修订）

- ~~部署时补齐 `/media/audio`，或播放失败回退到浏览器 `say(word)`。~~
- 旧站的 mp3 是「整组音频」，词库 `audio` 字段并不是单词发音，本站也从未托管该目录；
  已改为单词一律走浏览器 `say(word)`，并在点击事件内**同步**调用（iOS Safari 只在手势内发声）。
  详见 [dev/word-audio-ios](dev/word-audio-ios/)。
- 例句发音入口统一：浏览页已有，计划学习/测验已补“听整句”。

### 2.3 P1（体验与成本）

**P1-1 Realtime 模型 A/B**

- 增加“主模型 / 回退模型 / 跟读模型”配置；先并行评估 `qwen3.8-omni-flash-realtime` 与 `qwen-audio-3.1-realtime-flash`。
- 通过后再切默认；保留一键回退。详见第 4 节。

**P1-2 画像按日缓存**

- `get_profile` 当前默认 `rebuild=True`，每次 talk boot 都重建；改为当日有缓存直接复用，跨天或新会话摘要后失效。
- 预计每次会话省 1 次 LLM 调用与约 1 秒延迟。

**P1-3 `improve` 节流**

- 每句 ≥3 字就调用过于频繁；改为 ≥4–5 个词、或用户主动点“帮我改”时调用。
- 预计减少 30–50% 的 `improve` 调用，主要是延迟与并发收益。

**P1-4 TTS 缓存治理**

- 缓存按 mtime 做 LRU，设置容量上限（如 512MB），后台可查看/清理。
- 句子文本变化会产生新 hash；旧文件由 GC 清理。
- 不做全库预生成；可在管理页对单个 pack 手动“预热”。

**P1-5 跟读复用连接**

- 一个 pack 内复用一条 Realtime 连接，句间发 `session.update`，减少 SDP/握手开销。

### 2.4 P2（规模化后再做）

- **P2-1 半双工/静音抑制**：AI 说话时暂停麦克风轨道，减少输入音频；需评估打断体验。
- **P2-2 TTS 改静态 URL**：不再把 base64 WAV 塞进 JSON，浏览器可直接缓存。
- **P2-3 预算预测与月账单核对**：按真实账单校准单价，生成 CSV/月度报表。
- **P2-4 免费用户降级策略**：浏览器 TTS 兜底、无评分跟读、本地句型练习。
- **P2-5 更多难度维度**：用 SOE 的逐词准确率自动标记弱音素，参与选句。

## 3. 跟读句库与 TTS 缓存

### 3.1 数据形态

在 `data-src/speak` 增加/补齐字段，由 `tools/build_speak_v3.js` 产出到 `frontend/public/data/speak.json`：

```json
{
  "id": "sh-042",
  "pack": "p2-3-8",
  "packName": "Part2 Photos",
  "part": 2,
  "en": "In this photo I can see three people having a meal.",
  "cn": "在这张照片里我能看到三个人在吃饭。",
  "difficulty": 3,
  "words": 11,
  "focus": ["photo-description", "there-is"],
  "source": "demo",
  "active": true
}
```

- `difficulty`：1=A1，2=A2，3=B1，4=B1+，5=B2；先人工/规则标注，后续可校准。
- `words`：构建时自动计算。
- `focus`：语音/表达重点，可用于弱项加权；没有也不影响选句。
- `active=false` 的句子不参与选择，但保留历史引用。
- 句库是数据层；计划仍可按 pack 选主题，自由模式跨库按难度选。

### 3.2 难度选择算法（纯前端、可测试）

放在 `frontend/src/core/{sentenceBank}.ts`，不新增 AI 调用：

1. 取最近 3 次跟读平均分：≥85 目标难度 +1；<60 −1；其余不变；范围 1–5。
2. 候选：`active && |difficulty - target| <= 1`；不足时放宽到 ±2。
3. 排序权重：
   - 未练过优先；
   - 最近练过的降权；
   - 词数与目标长度接近（如 8–15 词）优先；
   - `focus` 命中最近错词/弱项优先；
   - 最后用 `hash(userId|date|id)` 做稳定抖动，避免每天顺序完全一样。
4. 每个 pack 取 N 句（默认 5）；自由模式可跨 pack。
5. 计划模式：保留现有 `plan.days[].shadow` 主题映射，在 pack 内用难度排序；后续可改为直接按难度抽句。

**验收**：给定目标难度，输出都在 ±1；最近 N 句不重复；同一用户同一天结果稳定；无 AI 调用。

### 3.3 TTS 懒缓存

现有实现已经是懒缓存（`qwen_speak.py:207-231`）：

```text
key = sha1(model | voice | text)
if cache hit: return audio
else: call TTS once -> write wav -> return
```

本次只补：

- **只生成一次**：同一 key 永远命中；句子改字后 key 变化，重新生成一次。
- **不预生成整库**：句库可能更换，预热只做手动、按 pack、可选。
- **记账**：未命中时记录字符数与费用；命中不记。
- **容量治理**：512MB 上限，按 mtime LRU；后台显示数量/大小，可清理。
- **失败不写缓存**：避免把错误音频固化。

### 3.4 验收

- Given 同一句第二次播放，Then 不再调用 TTS，返回 `cached=true`。
- Given 句子文本被替换，Then 生成新缓存，旧文件可被 GC。
- Given 缓存达到上限，Then 按最久未使用清理，播放不受影响。
- Given 用户没有付费 AI 权限，Then 仍可用浏览器 TTS 朗读，不调用 Qwen TTS。

## 4. Realtime 模型对比与替换评估

> 公开资料检索不到字面名为 `qwen3.8-audio-flash-realtime` 的模型；官方实时语音家族中对应的是 **`qwen-audio-3.1-realtime-flash`**。若控制台里确有 `qwen3.8-audio-flash-realtime`，请以控制台模型卡和报价为准。

### 4.1 对比

| 维度 | `qwen3.8-omni-flash-realtime` | `qwen-audio-3.1-realtime-flash` |
|---|---|---|
| 定位 | 实时全模态（文本/音频/图片/视频） | 实时语音 S2S（纯语音） |
| 输入/输出 | 音频、文本、图片、视频 → 文本/音频 | 音频、文本 → 文本/音频 |
| 上下文 | 196,608 输入 / 65,536 输出；音频历史 100 轮/600s；视频 50 轮/240s | 262,144 上下文；最大输入 245,760 / 输出 16,384；音频历史 50 轮/300s |
| 协议 | WebSocket / WebRTC / AOQ | WebSocket / WebRTC / AOQ |
| 工具调用 | ✅ Function Calling / MCP | ✅ Function Calling / 联网搜索 |
| 轮次检测 | `semantic_vad`（当前代码使用） | `server_vad` / `smart_turn` / `smart_turn_v2`（推荐 v2） |
| 音色 | 56 种，默认 Tina | 默认 `longanqian_v3.1`，支持声音复刻 |
| 业务空间 | 必须绑定 workspace | 文档同样使用 workspace 端点 |
| 限流 | 60 RPM / 2M TPM | 60 RPM / 100k TPM |
| 北京 Flash 价 | 文本入 1.5 / 音频入 6 / 文本出 4.5 / 音频出 12（元/M tok） | 同左（同档同价） |
| 计费细节 | 输出音频与其转写文本分别计费（公开资料） | 文本+音频同时输出时只计音频 |
| 延迟 | 公开资料约 591ms 首 token / 978ms 首音频（6s 输入） | 定位更快/更低延迟，但无公开硬指标 |

### 4.2 是否替换

**不建议直接替换，建议 A/B 后再决定。**

- 相同价位下，`audio-3.1-flash` 的优势是纯语音、更简单、限流更低但足够、可能更低延迟；劣势是音频历史只有 300s，而 PET 一次 talk 是 10–15 分钟，可能丢早期上下文。
- `omni-flash` 的优势是 600s 音频历史、MCP、更多音色、2M TPM；劣势是全模态能力用不上、配置更重。
- 当前代码依赖 `semantic_vad`、`hint`/`praise` 工具、`response.audio_transcript.*` 事件；切换前必须逐项验证。
- 建议把“模型 + 音色 + VAD 类型 + 能力开关”做成配置档（profile），而不是把模型名散落在代码里。

### 4.3 A/B 方案

| 项 | 做法 |
|---|---|
| 分组 | 同一用户按会话交替，或按账号固定分组 |
| 场景 | Part 1 / Part 2 / Part 3 各 10 场，10–15 分钟 |
| 指标 | 首音频延迟、15 分钟上下文保持、工具调用成功率、打断恢复、转写准确率、每场费用 |
| 通过线 | 工具调用 ≥95%；上下文无“忘掉前文”；延迟不劣于现网 20%；费用不升 |
| 回退 | 管理页一键切回 `qwen3.8-omni-flash-realtime`，无需发版 |
| 上线 | 通过后默认切 audio-3.1-flash；omni 保留为回退 |

## 5. 预算、告警与开通

### 5.1 权益分层

| 能力 | 默认用户 | 付费 AI（需开通） |
|---|---|---|
| 口语计划、题库、句子库、页面浏览 | ✅ | |
| 浏览器 TTS 朗读 | ✅ | |
| 静态单词/听力音频 | ✅ | |
| 跟读评分（SOE/AI） | | ✅ |
| 自由对话（Realtime） | | ✅ |
| Qwen TTS 示范 | | ✅ |
| `improve` / `help` / `check` / `review` / 画像 | | ✅ |
| AI 加词补全 | | ✅ |
| 手动加词、本地练习 | ✅ | |

- 口语模块本身**默认对全部账号开放**；付费接口默认关闭。
- 用户点付费按钮时提示：**“此功能调用外部 AI 接口，有费用，需要找小淏开通。”**
- 未开通时付费按钮显示锁定态；免费功能不受影响。

### 5.2 预算模型

- 每个用户两条预算：**日预算**、**月预算**（可只启用月预算；日预算用于防单日失控）。
- 全局默认值存 `app_cfg['ai.budget']`，用户可单独覆盖：

```json
{
  "daily_milli": 500,
  "monthly_milli": 10000,
  "alert_ratio": 0.8,
  "hard_stop": true,
  "currency": "CNY",
  "timezone": "Asia/Shanghai"
}
```

- 单位统一 `0.001 元`，与 `usages.est_cost_milli` 一致。
- 建议默认：日 ¥0.50、月 ¥10.00（约为正常用量的 3 倍余量）；管理员可按人调整。
- 计费周期：日按北京时间 00:00；月按每月 1 日 00:00。

### 5.3 闸门与硬停用

所有付费接口统一依赖 `require_paid_ai(user, db)`：

1. `ai_enabled = false` → **403 `AI_NOT_ENABLED`**，消息提示找小淏开通。
2. 今日/本月已用 ≥ 预算 → **429 `AI_BUDGET_EXHAUSTED`**，返回下次重置时间。
3. 否则放行，并在响应里带 `remaining_milli` 供前端提示。

接口矩阵：

| 免费（不查预算） | 付费（走闸门） |
|---|---|
| `/speak/plan` `/speak/days` `/speak/log` `/speak/time*` `/speak/review/due` `/speak/review/grade` | `/speak/sdp` `/speak/soe_url` `/speak/tts` `/speak/improve` `/speak/help` `/speak/check` `/speak/review` |
| `/speak/boot`（shadow，不生成画像） | `/speak/boot`（talk，生成画像） |
| `/words/custom` 手动增删改 | `/words/custom/enrich` |

**Realtime 的硬停用**：

- `/speak/sdp` 放行前计算剩余预算可支撑的最大秒数，返回 `max_session_sec`。
- 前端在 80% 时提示，到 `max_session_sec` 自动结束并进入复盘。
- 正常结束由 `/speak/session_end` 结算；中途关页用 `sendBeacon` 补报。
- 服务端记录会话开始时间；超过 30 分钟未收到结束，按预估上限补记，避免白用。
- 允许一次会话轻微超支，但下一次付费调用立即被 429 拦住。

### 5.4 告警

| 阈值 | 用户端 | 管理端 |
|---|---|---|
| 80% | 顶部黄色横幅：“AI 额度已用 80%，用完将暂停付费功能” | 用户行黄色，`alert_stage=1` |
| 100% | 红色横幅：“今日/本月 AI 额度已用完，免费功能仍可用” | 用户行红色，`alert_stage=2` |
| 未开通 | 付费按钮锁 + 提示找小淏开通 | 用户行显示“未开通” |

- 告警只发一次（按日/月周期去重），避免每次请求重复弹。
- 目前没有邮件/短信基础设施，先做站内横幅 + 管理端列表；后续可接微信/邮件。
- 管理端提供“重置告警”“调整预算”“查看明细”。

### 5.5 数据与迁移

- `users` 增加：
  - `ai_enabled`（bool，默认 false）
  - `ai_daily_budget_milli`（int，nullable，null=用全局默认）
  - `ai_monthly_budget_milli`（int，nullable）
- 新增 `usage_alerts`（user_id, period, stage, notified_at）或复用 `usages` 加 `alert_stage`；推荐单独表，便于按日/月周期去重。
- `app_cfg` 增加 `ai.budget`；`usage.prices` 增加 `tts_per_kchar`。
- 迁移时：现有管理员置 `ai_enabled=true` 并给足预算；普通用户 `ai_enabled=false`，口语模块可见但付费按钮锁定。
- 现有 `speak` 权限位与新的 `ai_enabled` 解耦；`speak` 不再作为付费 AI 的开关。

## 6. 管理页 AI 配置重构

### 6.1 信息架构

当前是一个扁平标签条（AI 加词 / 口语对话 / SOE / 账号与邀请码 / 用量），配置和账号混在一起。改为三层：

```text
管理后台
├─ 概览（今日花费、告警数、已开通用户数、Provider 状态）
├─ AI 配置
│  ├─ 文本模型（LLM）
│  ├─ 实时语音（Realtime）
│  ├─ 语音合成（TTS）
│  ├─ 发音评测（SOE）
│  ├─ 单价与默认预算
│  └─ 缓存
├─ 用户与额度
│  ├─ 账号
│  ├─ 邀请码
│  └─ 额度（按用户）
└─ 用量与预算
   ├─ 当日
   ├─ 本月
   └─ 告警
```

### 6.2 AI 配置（只放“全局能力”）

- 每个 Provider 一组：Key（只回显尾 4 位）、Endpoint、模型、音色、超时/重试。
- Realtime 增加：主模型、回退模型、跟读模型、VAD 类型、是否启用 MCP。
- TTS 增加：模型、音色、缓存上限、手动清理、单 pack 预热。
- 每组独立“保存”，不再用一个全局保存按钮跨账号生效。
- 增加“测试连接”：LLM 发一条最小消息；TTS 合成 1 句；SOE 只验签不发起评测；Realtime 做一次 SDP 握手（不建长会话）。
- 单价与默认预算单独一页：Realtime/Chat/SOE/TTS 单价、日/月默认预算、告警比例、硬停用开关。
- 不在这里管理账号、邀请码、单个用户的额度。

### 6.3 用户与额度（只放“人”）

- 账号表增加列：口语模块（默认开，只读）、AI 付费（开关）、今日已用、本月已用、额度状态。
- 行内操作：开通/关闭 AI、编辑预算、重置告警、查看用量明细。
- 预算编辑放在抽屉里，避免主表过宽；支持“恢复全局默认”。
- 邀请码仍是独立卡片，不混入 AI 配置。

### 6.4 用量与预算（只放“账”）

- 当日/本月按人汇总：Realtime 秒数、SOE 次数、LLM token、TTS 字符、预估费用。
- 预算进度条：已用/日预算、已用/月预算；80% 黄、100% 红。
- 告警列表：谁在什么时候触发、当前状态、是否已处理。
- 可导出 CSV，便于和供应商账单核对。

### 6.5 交互约定

- AI 配置页的保存只影响该组配置；用户页的开关即时生效。
- 所有 Key 输入框默认密码态；保存后只回显尾 4 位。
- 危险操作（清空缓存、重置预算、关闭 AI）需二次确认。
- 移动端仍可用：分组折叠，表格横向滚动。

## 7. 实施顺序与验收

| 阶段 | 内容 | 关键验收 |
|---|---|---|
| A（P0） | 计量补全、预算表/闸门、告警、管理页拆分、单词音频兜底 | 未开通 403；超预算 429；80% 告警；免费功能可用；账本与调用点一致 |
| B（P0/P1） | 跟读句库字段与选句、TTS 懒缓存治理 | 选句在 ±1 难度；同句只生成一次；缓存上限生效 |
| C（P1） | Realtime A/B、画像缓存、`improve` 节流、连接复用 | A/B 通过线；每次会话少一次画像 LLM；improve 调用下降 |
| D（P2） | 半双工、TTS 静态 URL、月账单核对、弱音素选句 | 成本/延迟/体验指标达标 |

### 7.1 测试清单

- 后端：预算闸门 403/429、日/月边界、告警去重、Realtime 超时补记、迁移可回滚。
- 前端：未开通提示、80%/100% 横幅、免费功能降级、管理页分组保存。
- 数据：句库难度字段完整、选句确定性、无重复。
- 成本：用模拟 usage 验证 `est_cost_milli` 与各调用点一致。

### 7.2 风险

| 风险 | 缓解 |
|---|---|
| Realtime 会话中途超预算 | 返回 `max_session_sec`，前端到时结束；超时补记 |
| 模型切换后 VAD/工具不兼容 | 配置档 + A/B + 一键回退 |
| 难度标注主观 | 先规则标注，抽样人工校准；保留反馈入口 |
| 管理页改动大 | 先拆信息架构，再逐组迁移，不做一次性重写 |
| 单价与账单不一致 | 月度 CSV 核对，价格存配置不改代码 |
| 免费用户误以为功能坏了 | 锁定态 + 明确文案 + 免费替代（浏览器 TTS） |

### 7.3 待确认

1. `qwen3.8-audio-flash-realtime` 的确切模型 ID、合同价与限流（公开资料对应的是 `qwen-audio-3.1-realtime-flash`）。
2. 默认预算：建议日 ¥0.50 / 月 ¥10.00，是否按这个起点。
3. 免费用户是否保留“浏览器 TTS + 无评分跟读”，还是只读题库。
4. 计划模式是否继续按 pack 主题选句，还是完全按难度抽句。
5. 告警渠道：先站内 + 管理端，是否还需要微信/邮件。
6. “小淏”是唯一开通人，还是管理员角色都可以开通。

### 7.4 实施回执（2026-11-24）

| 优先级 | 落地内容 | 代码位置 |
|---|---|---|
| P0-1 | 每账号 `ai_enabled` + 日/月预算覆盖；80% 告警、100% 硬停；服务端闸门 403/429；首个 claim 管理员自动开通 | `models/user.py`、`services/budget.py`、`core/deps.py`、迁移 `e1a2b3c4d5e6` |
| P0-2 | 跟读会话跟踪、TTS 字符/缓存计费、`enrich_word` LLM、`session_end` 幂等与超时补记、Realtime 文本 token 估算、可配置单价 | `services/usage.py`、`services/budget.py`、`api/v1/speak*.py` |
| P0-3 | 跟读句库 `difficulty/words/focus/source/active`；按最近得分选难度、避开最近、弱词加权、稳定抖动 | `tools/build_speak_v4.js`（schema 5）、`core/sentenceBank.ts` |
| P0-4 | 管理页拆为概览 / AI 配置 / 用户与额度 / 用量与预算；配置按组保存与连通性测试 | `views/AdminPage.vue`、`views/admin/*`、`api/v1/admin_ai.py` |
| P0-5 | 单词音频缺失回退浏览器朗读；单词学习/测验增加「听整句」 | `core/say.ts`、`WordStudyCard.vue`、`QuizPage.vue` |
| P1 | Realtime 主/备模型与 VAD、画像每日复用、improve ≥4 词自动调用、TTS 缓存 512MB LRU、同场景连接复用 | `qwen_speak.py`、`speak_profile.py`、`core/improve.ts`、`core/speakRTC.ts` |
| P2 | 半双工静音、TTS 静态 URL、月末预测 + CSV、免费降级与弱词选句 | `speakRTC.ts`、`speak_media.py`、`AdminUsage.vue`、`aiStatus.ts` |

**待确认项的处理**：默认预算采用日 ¥0.50 / 月 ¥10.00（可在管理页改）；免费用户保留「浏览器朗读 + 跟读可听可读但不评分」；告警先做站内与管理端；计划模式仍按 pack/场景选句，自由模式才跨库按难度抽句。

**本地校验**：`speak.json` 已按 schema 5 重新生成（45 包 / 135 跟读句 / 90 造句 / 300 自由句）；
后端 117、前端 185 测试通过，`vue-tsc`、`vite build`、`check_tokens.py`、26 条路由 × 1440/820/390 的
`check_overflow.js` 均通过。

**仍需真实环境验收**：TTS 真实合成与缓存命中、Realtime 主备切换、页面关闭时 `session_end` 的
`sendBeacon` 补报；这些需要供应商 Key，不阻塞代码完成判定。

## 8. 参考

- 阿里云百炼 · Realtime API 概述：https://help.aliyun.com/zh/model-studio/realtime-api-overview
- 阿里云百炼 · 模型价格：https://help.aliyun.com/zh/model-studio/model-pricing
- Qwen-Audio Realtime 用户指南：https://help.aliyun.com/zh/model-studio/qwen-audio-realtime-user-guides
- `qwen-audio-3.1-realtime-flash` 模型卡：https://docs.qwencloud.com/models/qwen-audio-3-1-realtime-flash
- `qwen3.8-omni-flash-realtime` 模型卡：https://docs.qwencloud.com/models/qwen3-8-omni-flash-realtime
- 公开检索时间：2026-11-24；具体以百炼控制台与合同价为准。
