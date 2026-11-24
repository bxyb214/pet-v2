# 管理后台只保留 AI 限制 — 需求

> 功能编号：`admin-ai-only`；日期：2026-11-24；关联：[04 功能清单](../../04-功能清单.md) M1/M5、[06 部署与运维](../../06-部署与运维.md)

## 1. 背景与目标

「用户与额度」里同时有「口语」和「AI」两个开关，口语权限还串联了路由守卫、首页锁定弹框、
`/admin/users/{id}/perms` 接口与 `effective_perms` 逻辑。实际使用中口语入口无需按人限制，
真正需要控制的是会产费用的 AI 调用。目标：删除口语权限及开关，管理后台只保留 **AI 开关 + 额度**。

## 2. 用户故事

- **US-01**：作为管理员，我只用控制每个账号的 AI 开关与额度，不再维护口语开通状态。
- **US-02**：作为普通账号，我登录后即可使用口语入口与免费功能，不需要等管理员开通口语。
- **US-03**：作为维护者，我希望删除口语权限的死代码与接口，避免两套权限概念混淆。

## 3. 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| F-01 | `用户与额度` 账号行删除「口语」开关，只保留「AI」开关、用量、额度与告警操作 | P0 |
| F-02 | 后端删除口语权限闸门：`require_speak` / `effective_perms` / `_has_perm`；口语路由只要求登录 | P0 |
| F-03 | 付费 AI 闸门保持不变：`ai_enabled` + 日/月预算；未开通 403 `AI_NOT_ENABLED`，用尽 429 | P0 |
| F-04 | 删除 `PUT /admin/users/{id}/perms`；`/auth/me`、登录/注册响应与 `/admin/users` 不再返回 `perms` | P0 |
| F-05 | 前端删除口语锁定：路由守卫、口语首页锁定弹框、设置页「可用板块」条件判断 | P0 |
| F-06 | 文档与测试同步；`users.perms` 列保留为历史数据，不做迁移/删除 | P1 |

## 4. 边界与非目标

- 不改付费 AI 的判定语义（`ai_enabled`、日/月预算、80% 告警、100% 硬停）。
- 不改同步合并、错题本维度、计划语义。
- 不做数据库迁移删除 `users.perms`（历史迁移数据保留，但不再参与鉴权与响应）。
- 不新增依赖。

## 5. 验收标准

- **AC-01**（F-02）：新注册、`ai_enabled=false`、`perms` 为空的普通账号：
  `POST /speak/boot`（shadow）、`GET /speak/days`、`GET/PUT /speak/plan`、`GET /speak/ai_status` 均可用。
- **AC-02**（F-03）：同一账号调用 `POST /speak/sdp`、`/speak/soe_url`、`/speak/improve` 等付费接口返回
  403 `AI_NOT_ENABLED`；管理员打开 AI 开关后，在预算内可继续（受真实 Key 配置影响）。
- **AC-03**（F-01）：`/admin` →「用户与额度」账号行只有 AI 开关，无「口语」开关与权限文案。
- **AC-04**（F-04）：`/auth/me`、登录/注册/刷新响应、`/admin/users` 均无 `perms`；
  `PUT /admin/users/{id}/perms` 返回 404。
- **AC-05**（F-05）：口语首页、跟读/造句/对话页对任意登录账号可进入，无「未开通口语」提示。
- **AC-06**：后端 pytest、前端 vitest、`npm run build` 全部通过。

## 6. 影响面

| 类别 | 内容 |
|---|---|
| 后端 | `core/deps.py`、`api/v1/speak.py`、`api/v1/admin.py`、`api/v1/auth.py`、`schemas/auth.py` |
| 前端 | `views/admin/AdminUsers.vue`、`views/SpeakHome.vue`、`views/SettingsPage.vue`、`router/index.ts`、`stores/auth.ts` |
| 数据 | 无 schema 变化；`users.perms` 保留但不读不写 |
| 测试 | 删除 `test_admin_perms.py`；改写 `test_speak.py` 的权限用例 |
| 依赖 | 无新增 |
