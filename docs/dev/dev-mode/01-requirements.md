# 开发/测试模式 — 需求

## 背景

测试环境没有配置 Qwen / 腾讯 SOE 的 Key，进入口语、造句、加词等页面会 503，
无法把「登录 → 跟读 → 对话 → 优化 → 复盘 → 打卡」整条链路走通；同时测试时也不应产生外部 AI 费用。

## 用户故事

- US-01：作为开发者，我一眼能看出当前是测试环境，避免把测试数据/模拟结果当成正式结果。
- US-02：作为测试者，我不配置任何 AI Key 也能完成所有口语与加词流程。
- US-03：作为维护者，我用一个环境变量开关开发模式，正式部署不受影响。

## 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| F-01 | 开发模式下，顶栏用户名位置显示 `DEV` 标签，隐藏用户名与头像 | P0 |
| F-02 | 开发模式由后端 `PET_DEV_MODE=1` 控制，并通过 `/api/v1/healthz` 暴露给前端 | P0 |
| F-03 | 开发模式下所有 AI 接口返回确定性结果，不调用 Qwen / SOE / 外部 TTS | P0 |
| F-04 | 开发模式下 Realtime 对话与 SOE 跟读使用前端模拟，不建立第三方连接 | P0 |
| F-05 | 正式环境（`PET_DEV_MODE` 未设置或 0）行为与现状完全一致 | P0 |

## 边界与非目标

- 不修改数据库 schema，不写入模拟的 AI 费用。
- 不改变真实 AI 接口的请求/响应结构；模拟结果字段与真实结果一致。
- 不在前端硬编码开发模式；不做“按域名自动判断”。

## 验收标准

- Given 测试环境设置 `PET_DEV_MODE=1`，When 登录后打开任意页面，Then 顶栏显示 `DEV`，不显示用户名与头像。
- Given 开发模式，When 进入口语跟读并点「提交」，Then 返回 100 分且每个目标词 `ok=true`。
- Given 开发模式，When 进入自由对话，Then 自动出现 AI/孩子对话，优化句可跟读评分，结束后出现复盘句。
- Given 开发模式，When 使用造句、加词、听示范，Then 分别返回通过判定、模拟词条、可播放提示音。
- Given 开发模式，When 调用 `/speak/sdp` 或 `/speak/soe_url`，Then 返回 503 开发环境提示，不发起外部请求。
- Given 未设置 `PET_DEV_MODE`，When 打开站点，Then 无 `DEV` 标签，AI 行为与原来一致。

## 影响面

- 后端：`Settings.dev_mode`、`healthz`、`services/dev_mock.py`、口语路由、`ai_enrich`、`speak_profile`、`speak_review`。
- 前端：`core/devMode.ts`、`core/devSpeak.ts`、`core/speakRTC.ts`、`core/soe.ts`、`layouts/AppLayout.vue`。
- 部署：`deploy/docker-compose.yml`、`deploy/.env.example`、`docs/06`。
