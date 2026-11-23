# 会话失效守卫 — 设计

## 1. 三层防线

```text
点击导航
  → router.beforeEach
      ├─ 公共路由 /login /register：放行
      ├─ getToken() 为空 → /login
      ├─ isTokenExpired() → auth.logout() → /login
      ├─ auth.restore()（无 username 时请求 /auth/me）
      │    └─ 401 → 清会话；网络错误 → 未登录
      └─ username 为空 → /login
           ↓
业务组件发请求
  → api() 收到 401（登录/刷新除外）
      ├─ setToken(null)
      ├─ 全局 handler：auth.logout() + router.replace('/login')
      └─ 继续抛错给调用方
```

## 2. 关键实现

### 2.1 `core/api.ts`

- `getToken()` 每次与 `localStorage.pet_access` 对齐，避免多标签页/手动清除后内存 token 仍生效。
- `setUnauthorizedHandler(fn)` 由 `main.ts` 注册；401 时只触发一次（`unauthorizedFired` 去重）。
- `/auth/login`、`/auth/refresh` 的 401 不触发全局跳转，交给表单显示错误。

### 2.2 `core/token.ts`

本地解析 JWT payload 的 `exp`：过期、缺 `exp`、格式错误都视为失效。
这只是快速拦截，最终仍以服务端 401 为准。

### 2.3 `stores/auth.ts`

- `restore()`：无 token → `logout()`；过期 → `logout()`；否则无 `username` 时请求 `/auth/me`。
- `/auth/me` 401 → `logout()`；网络错误 → `clearSession()`，由守卫回登录页。
- 新增 `clearSession()`，只清登录态；`logout()` 额外断开同步引擎并清 token。

### 2.4 `router/index.ts`

守卫改为全局校验：除两个公共路由外，任何路径都必须有 `username`；
再执行管理员 / 口语权限判断。移除 `pet_local_only` 对登录校验的绕过。

### 2.5 `main.ts`

注册全局 401 handler：`logout()` + `router.replace('/login')`。
使用 `replace` 避免用户点返回又回到失效页面。

## 3. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 只在管理页/口语页调用 `restore()` | ❌ 就是本次 bug：其他页面无校验 |
| 每个页面自行判断登录 | ❌ 重复、易漏 |
| 只在路由守卫判断 token 是否存在 | ❌ 无法发现过期/被拒绝的 token |
| **全局守卫 + 全局 401 handler（选定）** | ✅ 覆盖导航与请求两条路径 |

## 4. 风险

| 风险 | 缓解 |
|---|---|
| 401 handler 重定向循环 | 只对非登录接口触发；登录页不再触发导航 |
| 多请求同时 401 多次跳转 | `unauthorizedFired` 去重 |
| 网络错误被误判为未登录 | 只有 401 清会话；其他错误清内存态但保留 token，恢复网络后可再验证 |
| 本地 token 过期时间与服务端不一致 | 本地只做快速拦截，最终以 401 为准 |

## 5. 测试

- 单测：`core/token.test.ts`（过期/缺 exp/格式错误）、`core/api.test.ts`（401 清 token、登录接口不跳转）。
- 浏览器：无 token、删 token 后 SPA 点击、无效 token、过期 token 四种入口均回 `/login`。
