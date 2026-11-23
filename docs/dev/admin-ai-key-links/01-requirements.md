# 管理后台 AI 配置增加 Key 获取链接 — 需求

## 背景

「AI 加词」和「口语对话」都需要阿里云百炼（DashScope）API Key，但管理页只有
输入框，没有像「发音评测 · 腾讯 SOE」那样的控制台链接，管理员不知道去哪里申请。

## 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| F-01 | 「AI 加词」面板增加提示框，链接到阿里云百炼 API-KEY 页面 | P0 |
| F-02 | 「口语对话」面板增加提示框，链接到同一页面，并说明 Key 可与 AI 加词共用 | P0 |
| F-03 | 文案与腾讯 SOE 提示保持同一视觉样式（`.notice`） | P1 |

## 边界与非目标

- 不改 key 的存储、掩码和保存逻辑；不在前端硬编码任何 Key。
- 不把两个配置合并成一个字段（仍各自保存，提示可填同一个 Key）。
- 不新增依赖。

## 验收标准

- 两个面板均显示带链接的提示框，链接为
  `https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key`。
- 链接在新标签页打开（`target="_blank" rel="noopener"`）。
- `vitest`、`vue-tsc`、`vite build` 通过。
