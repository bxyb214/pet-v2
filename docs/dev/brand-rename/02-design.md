# 品牌改名与登录/注册文案调整 — 设计

## 1. 改动点

| 文件 | 改动 |
|---|---|
| `frontend/src/components/AuthShell.vue` | `mark-name` → 火焰学习；叶子 SVG → 火焰 SVG（保持 17px、描边风格） |
| `frontend/src/layouts/AppLayout.vue` | 顶栏 Logo emoji 🌿 → 🔥，`logo-txt` → 火焰学习 |
| `frontend/src/layouts/SiderNav.vue` | 侧栏底部「绿野成长 · 每天进步一点点」→「火焰学习 · 每天进步一点点」 |
| `frontend/index.html` | `<title>` → 火焰学习 · PET 备考 |
| `frontend/src/views/Login.vue` | 删除副标题；`.head h2` 去掉底部间距、删除 `.head p` 规则 |
| `frontend/src/views/Register.vue` | 非首个账号副标题 →「找小淏要注册码后注册」 |

## 2. 设计取舍

- 只替换文案与图标，**不动**主题色与布局：`--c-primary` 绿色仍按
  `docs/05` 的 Design Token 使用，避免一次改名引发全站视觉回归。
- 图标用同一套线性描边风格（`stroke-width=2`、`aria-hidden`），
  与 AuthShell 原有图标一致；顶栏沿用 emoji，降低改动面。
- 浏览器标题保留「PET 备考」，便于家长/学生识别用途。
- 「绿野成长」作为设计语言内部名称保留在 `docs/05`，不再出现在界面。

## 3. 兼容与风险

| 风险 | 说明 |
|---|---|
| 旧文案被测试断言 | 已检索 `frontend/src/**/*.test.ts`，无相关断言 |
| 图标改变影响布局 | 同为 17px SVG / 单字符 emoji，不改变排版 |
| 注册页首个账号流程 | `isFirst` 分支文案不变，仅普通注册分支调整 |

## 4. 第 2 轮

- `frontend/index.html`：`<title>火焰学习</title>`，新增
  `<link rel="icon" type="image/svg+xml" href="/favicon.svg">`。
- `frontend/public/favicon.svg`：64×64 viewBox，深绿圆角方块 + 橙黄渐变火焰；
  16px 下仍能看出火光，与顶栏 🔥 一致。
- 注册页 `points` 首条改为「邀请码找小淏要，一次性使用」。
- 只改静态资源，无接口/依赖变更。
