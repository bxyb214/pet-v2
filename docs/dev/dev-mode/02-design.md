# 开发/测试模式 — 设计

## 1. 开关与暴露

```text
deploy/.env: PET_DEV_MODE=1
        │
        ▼
api: Settings.dev_mode ──► GET /api/v1/healthz { dev_mode: true }
        │
        ├─ AppLayout 显示 DEV（隐藏用户名/头像）
        └─ createSpeakConn / SoeEval 在首次使用时读取并走模拟
```

- 后端 `Settings.dev_mode: bool = False`，环境变量 `PET_DEV_MODE`。
- `healthz` 每次请求读取 `get_settings()`，便于测试切换；正式 compose 默认 `0`。
- 前端 `core/devMode.ts` 缓存一次 `healthz` 结果（`ensureDevMode()`）；Realtime/SOE 在使用前 await。

## 2. 后端模拟（`services/dev_mock.py`）

所有结果都是确定性的，字段与真实接口一致：

| 接口 / 路径 | 开发模式行为 |
|---|---|
| `POST /speak/improve` | 规范化孩子原话（首字母、句号、`like play → like playing`），`dims=["grammar:sentence"]` |
| `POST /speak/check` | `ok=true`，中文模拟点评，`improved` 为规范化句子 |
| `POST /speak/help` | 返回固定的中文提示 + 英文示范句 |
| `POST /speak/review` | 从 transcript 取孩子真实说过的句子，最多 3 条，确定性改写 |
| `POST /speak/tts` | 返回 0.25 秒提示音 WAV（base64），不写缓存、不调外部 TTS |
| `POST /words/custom/enrich` | 返回固定词性/释义/例句模板 |
| `POST /speak/sdp` | 503「开发环境不连接语音服务」 |
| `POST /speak/soe_url` | 503「开发环境不调用 SOE」 |
| `/speak/boot`、`/speak/log` | 画像/摘要走确定性 fallback，不调用 LLM |
| `/speak/session_end` | 不记用量、不产生费用，返回 `est_cost_milli=0` |
| `ai_enrich.chat` | 开发模式直接抛 `RuntimeError`（兜底闸门，防止漏网调用） |

`usage.record_llm` 在开发模式不执行；开发期间的用量表保持 0。

## 3. 前端模拟

### 3.1 Realtime（`core/devSpeak.ts`）

`createSpeakConn()` 先 `await ensureDevMode()`；开发模式返回 `createDevSpeakConn()`：

- **shadow**：点「提交」后 450ms 返回满分 JSON，目标句从 instructions 中解析。
- **talk**：1.2s 后 AI 开场；3s 起按脚本产生「孩子说 → AI 回」，触发即时优化与复盘链路。
- `elapsedSec` / `speechSec` 用本地计时，使 5/10/15 分钟提示可测。

### 3.2 SOE（`core/soe.ts`）

`SoeEval.start()` 开发模式不请求 `/speak/soe_url`、不开麦克风；`submit()` 500ms 后返回 100 分，
每个词 `ok=true`；`speechSec()` 按练习时长计。

### 3.3 顶栏

`AppLayout.vue` 在 `devMode` 为真时：

- 用户名位置显示 `DEV` 药丸（`--c-accent` 语义色），`title` 提示“开发环境：AI 接口返回模拟结果”；
- 隐藏用户名与头像（头像首字来自用户名）；
- 设置 / 管理 / 退出保持可用。

## 4. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 用 `import.meta.env.DEV` 判断 | ❌ 只覆盖 `vite dev`，Docker 测试环境是生产构建，无法覆盖 |
| 按 hostname 自动判断 | ❌ 局域网 NAS 也会误判，危险 |
| 前端逐接口 mock | ❌ 后端仍可能被其他客户端调用，且无法保证“零外部请求” |
| **后端显式开关 + healthz（选定）** | ✅ 单一来源，测试/正式可切换，前后端一致 |

## 5. 风险

| 风险 | 缓解 |
|---|---|
| 开发模式误开到正式环境 | `.env.example` 默认 0；`docs/06` 明确说明；顶栏 DEV 明显可见 |
| 模拟结果被当成真实评分 | 页面保留 DEV 标签；模拟文案标注“开发环境模拟” |
| 漏掉某个 AI 调用 | `ai_enrich.chat` 兜底抛错；sdp/soe_url 显式 503；pytest 覆盖 |
| 前端 healthz 失败 | `ensureDevMode()` 失败按 false 处理，回到真实路径并显示后端错误 |

## 6. 测试

- 后端：`tests/test_dev_mode.py`（healthz、无 Key 的 improve/check/help/tts/enrich/review、sdp/soe_url 503）。
- 前端：`core/devSpeak.test.ts`（目标句解析、满分结果、fallback）。
- 手工：Docker 测试环境设 `PET_DEV_MODE=1`，走通跟读 → 对话 → 复盘 → 造句 → 加词。
