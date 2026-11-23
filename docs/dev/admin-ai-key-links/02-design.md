# 管理后台 AI 配置增加 Key 获取链接 — 设计

## 1. 改动

`frontend/src/views/AdminPage.vue`：

| 面板 | 提示文案 |
|---|---|
| AI 加词 | 需在 **阿里云百炼 · API-KEY** 创建 Key，并开通通义千问文本模型；Key 只存在服务端配置表里，保存后仅回显尾 4 位。 |
| 口语对话 | 需在 **阿里云百炼 · API-KEY** 创建 Key（可与「AI 加词」共用），并在控制台开通实时语音模型；Key 只存在服务端配置表里，保存后仅回显尾 4 位。 |

链接：`https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key`
（百炼控制台 API-KEY 页面；地域在控制台右上角切换，国内部署默认北京）。

## 2. 复用现有样式

沿用 SOE 面板的 `.notice / .ni / .notice p / .notice a`，无需新增 CSS，
三个 AI 配置面板的提示样式保持一致。

## 3. 取舍

- 只给「获取 Key」入口，不链接模型/业务空间文档，避免链接随控制台改版失效；
  业务空间 ID 的说明继续放在输入框下方 `fhint`。
- 不修改后端：`llm.api_key` 与 `speak.qwen.api_key` 仍独立存储，提示中说明可共用同一个 Key。

## 4. 风险

| 风险 | 缓解 |
|---|---|
| 百炼控制台 URL 改版 | 使用官方文档给出的 `/model/settings/api-key` 路径；失效时只影响提示链接 |
| 地域不一致 | 链接指向北京地域；其他地域可在控制台右上角切换，Key 与 Base URL 必须同地域 |
