# 左侧栏按宽度折叠 — 设计

> 对应需求：[01 需求](01-requirements.md)（SC-1 ~ SC-5）。日期：2026-11-24。

## 1. 方案

```text
窗口宽度 ──┐
           ├─ 手动偏好（localStorage.pet_sider = open | closed | 无）
           ▼
   core/siderPref.ts: isSiderCollapsed(width, pref)
           │
           ▼
   AppLayout: .sider.collapsed（74px 图标条）/ 默认 240px
           │
           ├─ ≥1024：显示「收起/展开」按钮；手动点击写入偏好
           ├─ 768–1023：CSS 强制 74px，按钮隐藏
           └─ <768：CSS 隐藏侧栏，沿用顶栏汉堡 + 抽屉
```

### 1.1 纯逻辑

`frontend/src/core/siderPref.ts`：

- `SIDER_AUTO_WIDTH = 1280`。
- `parseSiderPref(raw)`：只认 `open` / `closed`，其余（含 `null`）为自动。
- `isSiderCollapsed(width, pref)`：手动优先；自动时 `width < 1280` 收起。

选择 1280 的依据：内容最大宽 960 + 左右内边距 56 + 侧栏 240 ≈ 1256；
低于 1280 时展开侧栏会真正压缩内容，收起才有收益。

### 1.2 组件

`layouts/AppLayout.vue`：

- `siderPref` / `siderCollapsed` 在 `setup` 同步初始化（读取 `window.innerWidth`），避免首屏先展开再收起。
- `window.resize`：仅自动模式跟随宽度；手动模式保持不变。
- 切换按钮在侧栏顶部：展开时右对齐显示「收起」，收起时居中只显示方向图标；
  `aria-expanded`、`aria-label`（展开侧栏 / 收起侧栏）、`title` 同步。
- 收起样式复用平板图标条：隐藏 `.sider-title/.sider-foot/.s-txt/.n-name`，学科与板块按钮居中。
- 侧栏加 `overflow: hidden`，宽窄过渡时文字不会溢出到内容区。
- localStorage 写入包 `try/catch`，隐私模式只本次会话生效。

### 1.3 与既有断点的关系

| 宽度 | 侧栏 | 切换按钮 |
|---|---|---|
| ≥1280 | 240px（默认）/ 74px（手动收起） | 显示 |
| 1024–1279 | 74px（默认）/ 240px（手动展开） | 显示 |
| 768–1023 | 固定 74px | 隐藏 |
| <768 | 隐藏（抽屉） | 隐藏 |

## 2. 备选方案

| 方案 | 结论 | 原因 |
|---|---|---|
| A. 只做 CSS 媒体查询，无按钮 | 否 | 用户无法在窄屏桌面临时展开，也记不住偏好 |
| B. 按页面类型自动折叠（视频/答题） | 否（本期） | 学习中途切页会跳变；需求明确按宽度默认 |
| C. 收起为 0（完全隐藏） | 否 | 桌面失去导航；图标条保留学科/板块切换 |
| D. 偏好存服务端同步 | 否 | 纯展示偏好，跨设备意义不大；localStorage 足够 |

## 3. 风险

| 风险 | 缓解 |
|---|---|
| 首屏闪烁（先宽后窄） | setup 同步算初始值，无异步请求 |
| 手动收起后换到大屏仍是收起，用户困惑 | 按钮常驻且 `title` 明确；清 `pet_sider` 可回到自动 |
| 过渡期间文字溢出 | 侧栏 `overflow: hidden`，文字先隐藏再变宽 |
| 平板用户看到无按钮的图标条 | 与改造前一致，属于既有断点行为 |

## 4. 测试

- `core/siderPref.test.ts` 4 例：自动阈值、手动展开/收起优先、非法值回自动。
- Playwright（本地 dist + 打桩 API）：1440/1280/1279/1200/1000/390 六档宽度；
  1200 与 1440 各验证「切换 → 刷新 → 保持」。
- `vue-tsc` + `vite build`；相关路由横向溢出检查。
