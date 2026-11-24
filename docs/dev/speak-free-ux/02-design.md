# 口语免费功能提示与按钮体验 — 设计

> 日期：2026-11-24；对应需求：[01-requirements](01-requirements.md)

## 1. 方案概览

```text
aiStatus.ts
├─ paidBlocked()        已有：未开通 / 额度用尽
├─ paidClickHint()      新增：点击锁定按钮时的完整提示
└─ PAID_AI_FREE_TEXT    新增：免费功能清单常量

components/
├─ PaidAiNotice.vue     新增：未开通提示卡（口语入口 + 各练习页共用）
└─ PaidActionButton.vue 新增：AI 锁定态置灰但可点击，点击弹 toast

views/
├─ SpeakHome.vue        提示卡；移除旧 paidhint 内联文案
├─ SentencePage.vue     提示卡；开始说按钮；听标准答案文案
├─ SpeakShadow.vue      提示卡；删除「自己读一遍」；示范朗读浏览器直出
└─ SpeakTalk.vue        提示卡；开始对话按钮
```

数据流：

1. 页面加载后调用现有 `GET /api/v1/speak/ai_status`，得到 `ai_enabled` / `blocked`。
2. `PaidAiNotice` 只在 `ai_enabled=false` 时渲染，展示完整费用说明与免费功能清单；
   额度用尽仍由现有 `budgetBanner` 红色/黄色横幅提示，避免重复。
3. `PaidActionButton` 在 `paidBlocked(status)=true` 时呈现置灰样式，但保留点击事件；
   点击只弹前端 toast，不调用任何付费接口。
4. 未开通用户的「听示范」直接执行 `say(text)`，不进入 `POST /speak/tts` 分支。

## 2. API 契约

无新增、无修改。继续使用：

`GET /api/v1/speak/ai_status` → `AiStatus`

```json
{
  "ai_enabled": false,
  "speak_enabled": true,
  "daily": { "used_milli": 0, "budget_milli": 500, "ratio": 0, "stage": 0, "reset_at": "" },
  "monthly": { "used_milli": 0, "budget_milli": 10000, "ratio": 0, "stage": 0, "reset_at": "" },
  "remaining_milli": 0,
  "max_session_sec": 0,
  "blocked": true,
  "reason": "not_enabled",
  "message": "",
  "alert_stage": 0
}
```

前端只读该响应，不新增字段。`/speak/tts` 在未开通时不调用。

## 3. 数据模型

无变更，无 Alembic 迁移。

## 4. 前端变更

### 4.1 `core/aiStatus.ts`

新增常量与纯函数，保留已有 `paidLockText` 对额度用尽的文案，避免影响既有测试与调用方：

```ts
export const PAID_AI_NOT_ENABLED_TITLE = "付费 AI 未启用";
export const PAID_AI_NOT_ENABLED_BODY = "此功能调用外部 AI 接口，有费用，需要找小淏开通。";
export const PAID_AI_FREE_TEXT = "免费功能：题库浏览、浏览器朗读、看标准答案。";

/** 点击置灰按钮 / toast 用；未开通返回完整提示，额度用尽返回服务端原因。 */
export function paidClickHint(st: AiStatus | null | undefined): string {
  if (!st) return "";
  if (!st.ai_enabled) {
    return `${PAID_AI_NOT_ENABLED_BODY}${PAID_AI_FREE_TEXT}`;
  }
  if (st.blocked) return st.message || "AI 额度已用完，免费功能仍可用。";
  return "";
}
```

### 4.2 `components/PaidAiNotice.vue`

```text
Props: status: AiStatus | null | undefined; prominent?: boolean
v-if: status && !status.ai_enabled
内容:
  付费 AI 未启用
  此功能调用外部 AI 接口，有费用，需要找小淏开通。
  免费功能：题库浏览、浏览器朗读、看标准答案。
```

样式沿用暖橙 token（`--c-accent` / `--c-accent-soft`），左侧 4px 强调边；
`prominent` 只加大字号、内边距和投影，用于口语入口和造句页。

### 4.3 `components/PaidActionButton.vue`

```text
Props: status, disabled?
内部:
  locked = paidBlocked(status)
  hint = paidClickHint(status)
  class.is-locked → 覆盖 Naive UI 按钮 CSS 变量为灰色
  aria-disabled = locked || disabled
  click:
    locked → message.warning(hint)
    disabled → 不处理
    否则 emit("click")
```

选择「不设置原生 `disabled`」的原因：原生禁用按钮在多数浏览器不派发点击事件，
无法做到「灰色但仍可点击提示」。这里用 `aria-disabled` + 灰色 CSS 变量表达不可用语义，
用点击拦截阻止真正动作。

### 4.4 页面调整

- `SpeakHome.vue`：`PaidAiNotice` 替换 `.paidhint`，打开 `prominent`；删除 `paidLock`/`paidLocked` 局部计算。
- `SentencePage.vue`：`PaidAiNotice` 替换 `.lockbar`；开始按钮改用 `PaidActionButton`（仅 `checking` 时原生禁用）；
  锁定态按钮文案改为「听标准答案（浏览器朗读）」；`play()` 在状态未知时也直接浏览器朗读，避免误调付费 TTS。
- `SpeakShadow.vue`：`PaidAiNotice` 替换 `.lockbar`；跟读评分改用 `PaidActionButton`；
  删除「自己读一遍」按钮与 `listenAndRepeat()`；`tts()` 在未开通/状态未知时同步调用 `say()`。
- `SpeakTalk.vue`：`PaidAiNotice` 替换 `.lockbar`；开始对话改用 `PaidActionButton`。
- 已开通用户：按钮、AI 朗读、评分、对话行为不变。

## 5. 备选方案与取舍

**被否方案 A：继续用原生 `disabled` + `title` 提示。**
原生禁用按钮不触发 click，移动端也没有 hover/title；无法满足「点击弹出提示」。

**被否方案 B：每个页面复制提示文案和灰色按钮 CSS。**
四处重复，后续改文案容易出现不一致；抽成 `PaidAiNotice` / `PaidActionButton` 两个小组件，
页面只组合，改动集中。

**被否方案 C：未开通时把「听示范」改成纯文本说明，不提供朗读。**
违反「免费功能包含浏览器朗读」的既有降级策略，也会降低免费用户的学习体验。

**采用方案：共享提示/按钮组件 + 浏览器朗读直出。**
改动集中在前端呈现层，无接口、数据与计费影响；代价是新增两个组件文件。

## 6. 风险清单

| 风险 | 影响 | 缓解 |
|---|---|---|
| 灰色按钮看起来能点但实际无动作 | 用户反复点击 | 点击立即 toast 完整提示；`aria-disabled` + `cursor: not-allowed` |
| Naive UI 主题覆盖灰色样式 | 锁定按钮仍显示绿色 | 组件内用 `!important` 覆盖按钮颜色/文字/边框 CSS 变量；构建后目测 |
| 未开通用户误触付费 TTS | 产生费用 | `tts()/play()` 在 `!ai_enabled` 或状态未知时直接 `say()`，不进入 API 分支 |
| 浏览器语音在 iOS 上被吞 | 点朗读没声音 | 保持 `say()` 在点击事件同步栈内调用；不先 await 网络 |
| 额度用尽与未开通提示重复 | 页面信息过载 | `PaidAiNotice` 仅在 `ai_enabled=false` 渲染；额度用尽沿用横幅 |
| toast 内容过长 | 移动端遮挡 | 使用 Naive UI message 自动换行；只展示一次、6 秒后消失 |

## 7. 测试计划

- `core/aiStatus.test.ts`：
  - 未开通 → `paidClickHint` 同时包含「需要找小淏开通」和「免费功能：题库浏览、浏览器朗读、看标准答案。」；
  - 已开通且可用 → 空串；
  - 额度用尽 → 服务端 message 或默认额度文案。
- 前端全量 `npm test`。
- `npm run build`（`vue-tsc --noEmit` + vite）。
- 手工：
  - 未开通账号查看口语首页、造句、跟读、对话四页的提示卡；
  - 点击三个置灰主按钮，确认 toast 出现；
  - 跟读页不再出现「自己读一遍」；
  - 点击「听示范（浏览器朗读）」时 Network 面板无 `/speak/tts` 请求；
  - 造句页按钮文案为「听标准答案（浏览器朗读）」；
  - 已开通账号不显示提示卡，AI 朗读与评分不受影响。
