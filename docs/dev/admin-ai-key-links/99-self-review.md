# 管理后台 AI 配置增加 Key 获取链接 — 自省报告

> 结论：**PASS**

## 1. 完成项

| 需求 | 结果 | 证据 |
|---|---|---|
| AI 加词提示 + 获取链接 | ✅ 提示框与链接正常渲染 | Playwright：notice 文案、`href` 均为百炼 API-KEY 页 |
| 口语对话提示 + 获取链接 | ✅ 提示框与链接正常渲染，说明可与 AI 加词共用 | 同上 |
| 样式与 SOE 一致 | ✅ 复用 `.notice`，无新增 CSS | 截图 `_work/ui/admin-llm-link.png`、`admin-qwen-link.png` |
| 链接安全 | ✅ `target="_blank" rel="noopener"` | 代码检查 |

链接：`https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key`

## 2. 测试

- `vitest run`：139 测试通过。
- `vue-tsc --noEmit && vite build`：通过。
- 本地预览（4179）用管理员身份 + 打桩接口核对两个面板。

## 3. 说明

- 仅前端文案改动，后端 Key 存储/掩码/回显逻辑未动。
- 两个配置仍分别保存；提示已说明可以填同一个 Key。
- 百炼控制台若改版导致链接失效，只影响提示入口，不影响配置功能。
