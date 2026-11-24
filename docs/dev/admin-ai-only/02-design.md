# 管理后台只保留 AI 限制 — 设计

> 对应需求：[01-requirements](01-requirements.md)

## 1. 方案概览

```text
登录用户 ──▶ 口语路由（get_current_user）
              ├─ 免费：boot(shadow) / log / days / plan / time / ai_status / review/due …
              └─ 付费：boot(talk) / sdp / soe_url / improve / review / check / help …
                        └─ require_paid_ai：ai_enabled + 日/月预算

管理后台「用户与额度」
  └─ 每账号：AI 开关 + 今日用量 + 额度覆盖 + 告警清除
```

口语不再有按人权限；AI 开关是唯一的付费能力闸门。

## 2. 后端变更

| 文件 | 变更 |
|---|---|
| `core/deps.py` | 删除 `effective_perms`、`_has_perm`、`require_speak`；`require_paid_ai` 改为 `Depends(get_current_user)`，其余预算判定不变 |
| `api/v1/speak.py` | 所有 `Depends(require_speak)` → `Depends(get_current_user)`；付费接口继续用 `require_paid_ai` / `check_paid_or_raise` |
| `api/v1/admin.py` | 删除 `PermIn` 与 `PUT /users/{id}/perms`；`_user_row` 去掉 `perms` 字段 |
| `api/v1/auth.py` | 登录/注册/刷新/claim/me 不再输出 `perms` |
| `schemas/auth.py` | `TokenOut` / `UserOut` 删除 `perms` |
| `models/user.py` | `perms` 列保留（历史数据），注释改为「历史字段，不再参与鉴权」 |

`users.perms` 不做迁移：旧值（`speak` / `!speak` / `!listen`）保留但不读不写，避免不必要的数据变更。

## 3. 前端变更

| 文件 | 变更 |
|---|---|
| `views/admin/AdminUsers.vue` | 删除「口语」开关、`toggleSpeak`、`speakBusy`、`perms` 类型字段；文案改为「AI 开关是唯一付费闸门」 |
| `views/SpeakHome.vue` | 删除 `locked` / `showLocked` 与未开通占位、弹框、`?locked=1` 处理；保留 AI 未开通横幅 |
| `router/index.ts` | 删除「未开通口语 → 重定向 `?locked=1`」守卫 |
| `views/SettingsPage.vue` | 「可用板块」固定为「词汇 · 阅读 · 听力 · 口语」 |
| `stores/auth.ts` | 删除 `perms` state、`TokenResp.perms`、登录/恢复时的赋值与注释 |

`aiStatus.ts` 的付费锁定逻辑不变：`ai_enabled=false` 时显示「需要找小淏开通」并锁定付费按钮。

## 4. 测试变更

| 文件 | 处理 |
|---|---|
| `tests/test_admin_perms.py` | 删除（接口与口语权限不存在） |
| `tests/test_speak.py` | 原「无 speak → 403」改为「无 perms 也可用免费口语接口」；补一条「付费 talk 仍 403 `AI_NOT_ENABLED`」 |
| 其余测试 | 保留 `perms="speak"` 的赋值无害；可逐步清理，不作为本次验收条件 |

## 5. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 保留 `perms` 字段与接口，只隐藏 UI | 否决：留下死接口与两套权限概念，后续仍会误用 |
| 删除 `users.perms` 列并迁移数据 | 否决：需要不可逆迁移且无收益；历史数据保留即可 |
| 口语按用户限制改为「AI 额度」控制 | **采用**：成本问题由 AI 开关/预算解决，入口本身不需要权限 |

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 误删 AI 闸门，导致付费接口无限制 | `require_paid_ai` 与 `check_paid_or_raise` 保持原逻辑；用例覆盖 403/429 |
| 旧客户端读 `perms` 报错 | 单页应用随包发布，`/auth/me` 与登录同源更新；前端不再读取该字段 |
| 旧数据含 `!speak` 导致误解 | 后端不再读取；文档注明为历史字段 |
| 删除接口后旧脚本 404 | 仓库内无调用方；管理 UI 已移除入口 |
