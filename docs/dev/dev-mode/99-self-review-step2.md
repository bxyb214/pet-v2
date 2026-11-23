# dev-mode · 99 自省检查报告（step2：登录/注册页 DEV 标识）

- 日期：2026-11-23
- 范围：未登录页面（登录、注册）显示开发环境标识
- 关联设计：[02-design §3.4](02-design.md)

## 检查清单

| 类别 | 检查项 | 结果 | 说明 |
|---|---|---|---|
| 需求 | 登录页显示开发环境标识 | ✅ | 8089 `/login` 右上角「开发环境 · DEV」 |
| 需求 | 注册页显示开发环境标识 | ✅ | 8089 `/register` 同上 |
| 需求 | 正式环境不显示 | ✅ | 8088 `/login`、`/register` 均无 `.dev-flag` 节点 |
| 设计 | 与 02 §3.4 一致 | ✅ | 复用 `devMode` + `ensureDevMode()`，AuthShell 统一实现 |
| 代码 | 类型检查 / 构建 | ✅ | `npm run build`（vue-tsc --noEmit + vite）通过 |
| 测试 | 前端单测 | ✅ | **139 passed**（无新增用例；未引入新依赖） |
| 测试 | 浏览器实测 | ✅ | Playwright：dev 两页 true；prod 两页 false |
| 测试 | 移动端 | ✅ | 390×844 下 `top:10px`，不遮挡卡片与表单 |
| 部署 | 开发环境 | ✅ | `--profile dev` 发布，healthz `dev_mode=true` |
| 部署 | 生产环境 | ✅ | `--profile prod` 发布，healthz `dev_mode=false`；两端均服务 `assets/index-COFRN1r3.js` |
| 依赖 | 新增依赖 | ✅ | 无（未引入 `@vue/test-utils`，静态标识按人工/浏览器验证） |
| 数据 | schema | ✅ | 无变更 |

## 实现摘要

- `AuthShell.vue`：`onMounted(() => ensureDevMode())`；`devMode` 为真时渲染 `.dev-flag`。
- `devMode.ts`：注释补充登录/注册页行为。
- 样式复用 `--c-accent` / `--c-accent-soft` / `--shadow-1`，桌面与移动端各一档定位。

## 结论

**PASS**
