# auth-guard · 99 自省检查报告

- 日期：2026-11-23
- 范围：登录信息缺失/过期/401 时的全站访问控制

## 检查清单

| 类别 | 检查项 | 结果 | 说明 |
|---|---|---|---|
| 需求 | F-01 全路由会话校验 | ✅ | 除 `/login`、`/register` 外均需有效 `username` |
| 需求 | F-02 无 token/过期/401 → 登录 | ✅ | 三种入口浏览器实测均回 `/login` |
| 需求 | F-03 401 全局清会话 | ✅ | `api()` 统一处理，`unauthorizedFired` 去重 |
| 需求 | F-04 多标签页/手动清除 | ✅ | `getToken()` 与 localStorage 对齐；SPA 内点导航实测回登录 |
| 需求 | F-05 登录失败不跳转 | ✅ | `/auth/login` 401 只抛给表单 |
| 设计 | 与 02-design 一致 | ✅ | 守卫 + 401 handler + 本地 exp 三层 |
| 代码 | 类型检查 | ✅ | `vue-tsc --noEmit` 通过 |
| 测试 | 前端单测 | ✅ | **98 passed**（新增 token 3 + api 2） |
| 测试 | 后端回归 | ✅ | **83 passed**（无后端改动） |
| 测试 | 构建 | ✅ | `npm run build` 通过 |
| 测试 | 浏览器 | ✅ | 见下 |
| 文档 | 阶段文档 + 功能清单 | ✅ | 01/02/99；docs/04 U8 + v1.8 |

## 浏览器实测（Chrome，1280×900）

| 场景 | 结果 |
|---|---|
| 正常 token 打开单词页 | `/english/words/browse` 正常渲染 |
| SPA 内删除 token 后点侧栏「口语」 | 跳转 `/login`，登录表单可见 |
| 无效 token 直接打开 `/english/speak/talk` | 跳转 `/login` |
| 过期 token 打开 `/english/speak/make` | 跳转 `/login` |
| 无 token 打开 `/english/reading/home` | 跳转 `/login` |

- 不再出现「页面能进但口语提示无权限」的情况。
- 测试账号及关联数据已清理，原有 4 个账号未动。

## 结论

**PASS**

## 遗留项

1. 未实现 refresh token 自动续期；本期保证失效后回登录。
2. `pet_local_only` 不再绕过登录校验；离线可玩仍保留在同步引擎层，但打开站点需要有效登录。
3. 网络错误（非 401）会回登录页；若后续需要“离线打开”，需加入本地会话快照与过期策略。
