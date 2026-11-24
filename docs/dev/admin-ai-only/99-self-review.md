# 管理后台只保留 AI 限制 — 自省报告

> 日期：2026-11-24；分支：`feat/ai-budget`；对应需求：[01-requirements](01-requirements.md) / [02-design](02-design.md)

## 逐项自查

| 类别 | 检查项 | 结果 |
|---|---|---|
| 需求 | F-01 ~ F-06 均有实现；AC-01 ~ AC-06 已验证 | ✅ |
| 设计 | 与 [02-design](02-design.md) 一致：口语权限删除，AI 闸门保持 | ✅ |
| 代码 | 后端删除 `require_speak` / `effective_perms` / `_has_perm` / perms 接口；前端删除锁定与开关 | ✅ |
| 测试 | 后端 125 passed（删 4 个权限用例，新增 3 个）；前端 203 passed | ✅ |
| 构建 | `npm run build`（Node 22.20.0）通过 | ✅ |
| 依赖 | 无新增 | ✅ |
| 数据 | 无 schema 变化；`users.perms` 保留为历史字段 | ✅ |
| 同步 | 未触碰合并语义、错题本维度、计划语义 | ✅ |
| 文档 | 02 API/数据模型、04 S4/S10/M1/变更记录、AI 方案、开发文档已更新 | ✅ |
| 部署 | 本地 8088 实测通过；生产 NAS 部署代码未改动 | ✅ |

## 实测记录

| 项 | 结果 |
|---|---|
| `/auth/me` | 返回 `username/display_name/is_admin/exam/ai_enabled`，无 `perms` |
| 免费口语接口 | 普通账号（`ai_enabled=false`、无 perms）：`/speak/days`、`/speak/plan`、`/speak/ai_status`、`boot(shadow)` 均 200 |
| 付费闸门 | 同一账号 `boot(talk)` → 403 `AI_NOT_ENABLED`；管理员打开 AI 后 `boot(talk)` → 200 |
| 管理用户列表 | `/admin/users` 每行无 `perms`，仍有 `ai_enabled`、今日/本月用量、预算、告警 |
| 旧权限接口 | 后端单测断言 `PUT /admin/users/{id}/perms` → 404（本地 dev_static 对非 GET 未知路径返回 405，见遗留） |
| 管理 UI | 源码中账号行只剩「AI」开关；文案「口语对所有账号开放」；无「口语」开关/`toggleSpeak` |
| 口语页面 | 源码中已无 `locked` / `showLocked` / `?locked=1` 分支与弹框；路由守卫不再拦截口语子页 |
| 设置页 | 「可用板块」固定显示「词汇 · 阅读 · 听力 · 口语」 |

## 变更文件

- 后端：`core/deps.py`、`api/v1/speak.py`、`api/v1/admin.py`、`api/v1/auth.py`、`schemas/auth.py`、`models/user.py`
- 前端：`views/admin/AdminUsers.vue`、`views/SpeakHome.vue`、`views/SettingsPage.vue`、`router/index.ts`、`stores/auth.ts`
- 测试：删除 `tests/test_admin_perms.py`；更新 `tests/test_speak.py`、`tests/test_admin_ai.py`
- 文档：`docs/02`、`docs/04`、`docs/AI优化与额度方案.md`

## 遗留与注意

- `users.perms` 列保留（旧迁移数据），不再读、写、返回；未做数据库迁移。
- 本地 `tools/dev_local.py` 的 SPA 通配路由对未知 `PUT/POST /api/...` 返回 405（生产 FastAPI 为 404），
  仅影响本地开发对已删除接口的探测；接口本身已不存在。
- 项目 ruff 配置仍会报既有 `B008`（FastAPI `Depends` 默认参数）等风格项；本次改动文件在 `F/E9` 规则下无错误。
- 验证用的临时账号 `smoke_admin` / `smoke_kid` 已从本地 `backend/data/pet.db` 删除。
- 变更尚未提交（用户未要求提交）。

## 结论

**PASS-with-notes**
