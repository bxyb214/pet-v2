# speak-v2 · 99 自省检查报告

- 日期：2026-11-22
- 范围：口语板块迁移（数据 / 后端 Realtime 代理 / 前端 WebRTC / 90 天计划）

## 检查清单

| 项 | 结果 | 说明 |
|---|---|---|
| 数据迁移 | ✅ | speak.json 178KB：shadow 305 / packs 60 / free 300 / scenes 54 / 90 天阶段表；pack→shadow 引用完整性校验零问题 |
| 后端模型 | ✅ | speak_logs / speak_days 两表，Alembic 迁移 eda43aedbffd 升降级演练通过 |
| 权限 | ✅ | `require_speak` 依赖（perms 含 speak），未开通 403，测试覆盖 |
| boot | ✅ | 服务端拼提示词：shadow 评测 JSON 指令 + target；talk 场景/句型 + 历史问题摘要 + 均分（测试覆盖拼装语义） |
| sdp | ✅ | 带 Key 代理换 SDP，Key 不出服务端；无 Key 503（测试覆盖）；错误消息透传含 model 与业务空间提示 |
| log/days | ✅ | 记录 + 90 天打卡（shadow/talk 双标记、score 取历史最高），测试覆盖 |
| tts | ✅ | dashscope TTS + sha1 磁盘缓存（data/tts，与 sqlite 同卷），无 Key 503 |
| 前端 WebRTC | ✅ | speakRTC.ts 精简移植：先协商收发 → session.updated 后挂麦 → session.update（voice/instructions/turn_detection）→ 事件流（transcript/reply/error 恢复）；voice 从 sdp 响应取 |
| 页面 | ✅ | SpeakHome（90 天打卡日历 + 三入口 + 54 场景分组）、SpeakShadow（逐句跟读/手动判停/评分词块/建议）、SpeakTalk（VAD 对话/场景模式） |
| 纯函数测试 | ✅ | phaseOfDay / dayDone / parseShadowReply（围栏容错）10+ 用例 |
| 全量 | ✅ | 后端 34 passed（+8）、前端 65 passed（+10）、vue-tsc/build 通过 |

## 问题与修复

1. `SpeakDay` 新建时 Python 属性 flush 前为 None → 构造时显式默认值。
2. vite build 清空 dist 会连带删 85MB 音频（触发批量删除确认）→ `emptyOutDir: false`。
3. speakRTC opts 收敛：sdp/voice 入参移除，voice 由 /speak/sdp 响应返回。

## 结论

**PASS-with-notes**：真机 WebRTC 需浏览器麦克风实测，无法离线验证——部署后首测项。

---

## 2026-11-22 AI 接口升级（对齐最新版本）

| 项 | 旧 | 新 |
|---|---|---|
| Realtime 对话模型 | qwen3.5-omni-flash-realtime | **qwen3.8-omni-flash-realtime**（支持 Function Call / MCP / semantic_vad）；qwen3.8 系列必须绑定业务空间（workspace），未配置时服务端显式报错 |
| VAD | server_vad(threshold/silence) | **semantic_vad**（过滤附和声/背景音，减少误触发） |
| 音色默认 | Ryan | **Tina**（qwen3.8 默认音色） |
| LLM 加词补全 | qwen-turbo | **qwen3.8-flash**（OpenAI 兼容，0.8 元/百万输入 Token） |
| TTS | qwen3-tts-flash（multimodal-generation 端点） | 不变（当前最新） |
| 发音精准评测 | 无（腾讯 SOE 基础版 v20180724 官方已宣布即将下线，**不迁旧版**） | **智聆口语评测（新版）**：WSS `soe.cloud.tencent.com/soe/api/{appid}`，HMAC-SHA1 签名（签名原文=除 signature 外参数字典序排序拼 `soe.cloud.tencent.com/soe/api/{appid}?k=v&…`，Base64(HmacSHA1(key=SecretKey))），后端 `/speak/soe_url` 出签名 URL，SecretKey 不出服务端；前端 `core/soe.ts` AudioWorklet 采 16k PCM（40ms/1280B 分包，ScriptProcessor 兜底），句子模式 eval_mode=1、score_coeff=1.0（儿童苛刻度）、voice_format=0 |

配套变更：
- `speak.soe` 配置进 app_cfg（appid/secret_id/secret_key/engine/coeff），管理页 AdminPage.vue 统一配置三组（LLM / speak.qwen / speak.soe），掩码回显 + 回写自动还原真 Key。
- SpeakShadow 增「精准发音评分（腾讯云）」入口，SOE 结果（SuggestedScore + 逐词 PronAccuracy）映射为统一评分卡（≥60 词记 ok）。
- 测试：后端 test_soe.py 9 用例（签名确定性/参数排序/超限/路由 503→200/掩码合并回写/qwen3.8 workspace 校验）；前端 soe.test.ts 3 用例。全量：后端 43 passed、前端 68 passed、vue-tsc/build 通过。

## 遗留项

1. 管理页口语模型配置 UI（api_key/workspace/model/voice/shadow_model/tts 存 `app_cfg.speak.qwen` JSON）——cfg 接口已支持，缺专门表单。
2. SOE 腾讯云发音评测（旧站 soe_eval）未迁——跟读先用 Qwen Realtime 自评。
3. usage 用量统计（M4）未迁。
4. shadow 跟读句自动换句后需重开连接（当前一句一连接，VAD 手动模式重连成本低但可优化为复用）。
