# 品牌改名与登录/注册文案调整 — 自省报告（第 2 轮）

> 结论：**PASS**

## 1. 完成项

| 需求 | 结果 | 证据 |
|---|---|---|
| 注册页要点改「邀请码找小淏要，一次性使用」 | ✅ | Playwright：`.pts li` 首条为该文案 |
| 浏览器标题去掉「PET 备考」 | ✅ | `document.title` = 「火焰学习」 |
| 火焰 SVG favicon | ✅ | `frontend/public/favicon.svg`；`<link rel="icon" href="/favicon.svg">` |
| favicon 16px 可辨识 | ✅ | 16/32/64px 渲染截图 `_work/ui/favicon-sizes.png` |

## 2. 实现说明

- favicon 为 64×64 viewBox：深绿（#14532d）圆角方块 + 橙黄渐变火焰，
  和顶栏 🔥、登录页火焰图标一致；纯静态 SVG，无依赖。
- `index.html` 上传后由 nginx 直接从 `dist` 提供，`/favicon.svg` 返回
  `200 image/svg+xml`。

## 3. 测试

- `vitest run`：139 测试通过。
- `vue-tsc --noEmit && vite build`：通过，`dist/favicon.svg` 存在。
- 本地 `vite preview`（4179）与生产 8088 均核对标题、icon link、注册页要点。

## 4. 遗留

- 浏览器可能缓存旧 favicon；强制刷新（Ctrl/Cmd+Shift+R）后生效。
- 未生成 PNG/ICO 回退；现代浏览器均支持 SVG favicon。
