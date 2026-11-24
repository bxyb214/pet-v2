# 左侧栏按宽度折叠 — 自省

> 日期：2026-11-24；对应 [01 需求](01-requirements.md)、[02 设计](02-design.md)。
> 结论：**PASS-with-notes**（代码/测试/构建完成；尚未部署生产，见 §4）。

## 1. 需求覆盖

| 编号 | 实现 | 验证 |
|---|---|---|
| SC-1 | 自动模式：`width < 1280` 收起，否则展开 | 1440/1280 → 240px；1279/1200 → 74px |
| SC-2 | 侧栏顶部「收起/展开」按钮，`aria-expanded` + `aria-label` + `title` | 按钮标签随状态切换；点击后 300ms 过渡完成，宽度 74↔240 |
| SC-3 | 手动选择写 `localStorage.pet_sider`；自动模式监听 resize | 1200：展开后刷新仍 240；收起后刷新仍 74；1440：收起后刷新仍 74 |
| SC-4 | 768–1023 固定 74px 且按钮 `display:none`；<768 侧栏隐藏、汉堡按钮显示 | 1000px：74px、toggle none；390px：侧栏 display none |
| SC-5 | 收起态隐藏标题/页脚/文字，图标居中；按钮/学科/板块均有 `title` | 复用平板图标条样式；截图与 DOM 类名核对 |

## 2. 实现要点

- 新增纯逻辑 `frontend/src/core/siderPref.ts`（`parseSiderPref` / `isSiderCollapsed` / `SIDER_AUTO_WIDTH=1280`），
  组件只负责读窗口、读写 localStorage，合并/业务逻辑零改动。
- `AppLayout.vue`：`siderPref` 与 `siderCollapsed` 同步初始化（无首屏异步），
  resize 仅在自动模式跟随；手动模式优先。localStorage 读写包 `try/catch`（隐私模式）。
- 侧栏 `.collapsed` 复用既有平板样式；新增 `overflow: hidden` 防止宽窄过渡时文字溢出。
- 选择 1280 的依据：内容 960 + 内边距 56 + 侧栏 240 ≈ 1256，低于此宽度展开会压缩内容。
- 未改页面宽度规则、手机抽屉、后端接口与同步语义；无新增依赖。

## 3. 测试与构建

| 项 | 结果 |
|---|---|
| `npx vitest run` | **203 passed**（新增 `siderPref.test.ts` 4 例） |
| `vue-tsc --noEmit` + `vite build` | 通过；入口 `assets/index-BfBwLgBT.js` |
| Playwright（本地 dist + 打桩 API） | 六档宽度默认值正确；切换/刷新记忆正确；toggle 在 <1024 隐藏 |
| 横向溢出（1440/820/390 × 浏览/数学首页/四年级教材/进度） | 12 项全部 `scrollWidth == clientWidth` |

## 4. 遗留与风险

1. **尚未部署生产 8088**：`dist` 已在本地构建，等确认后走 `deploy_nas.py` + 强制重建 nginx 不影响侧栏；侧栏改动纯前端，nginx/API 无需变更。
2. 手动选择长期生效（跨宽度、跨会话）；若想恢复「按宽度自动」，清除 `localStorage.pet_sider` 即可。
   这一入口未做 UI（属于低频操作），如需可在设置页补「侧栏跟随窗口」开关。
3. 侧栏宽度过渡 180ms；测试在点击后等待 300ms 读取最终宽度。
4. 平板（768–1023）仍固定图标条，没有切换按钮——与改造前一致，避免窄屏下展开挤压内容。
