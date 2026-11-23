# dev-mode · 99 自省检查报告

- 日期：2026-11-23
- 范围：开发/测试模式开关、DEV 标识、AI 模拟、Realtime/SOE 前端模拟、测试环境验证

## 检查清单

| 类别 | 检查项 | 结果 | 说明 |
|---|---|---|---|
| 需求 | F-01 DEV 标签、隐藏用户名/头像 | ✅ | 浏览器实测顶栏为 `DEV | 设置 | 退出`，`.username` 节点 0 |
| 需求 | F-02 后端开关 + healthz 暴露 | ✅ | `PET_DEV_MODE=1` → `{"dev_mode":true}` |
| 需求 | F-03 AI 接口确定性结果 | ✅ | improve / check / help / review / enrich / tts 均无 Key 通过 |
| 需求 | F-04 Realtime / SOE 前端模拟 | ✅ | 对话自动产生多轮，跟读直接 100 分 |
| 需求 | F-05 正式环境不变 | ✅ | 开关默认 0；原有无 Key 503 用例仍通过 |
| 设计 | 与 02-design 一致 | ✅ | 单一 healthz 来源；`ai_enrich.chat` 兜底闸门；sdp/soe_url 显式 503 |
| 代码 | 类型检查 | ✅ | `npx vue-tsc --noEmit` 通过 |
| 代码 | 后端测试 | ✅ | **83 passed**（新增 dev-mode 9 项） |
| 测试 | 前端单测 | ✅ | **93 passed**（新增 devSpeak 3 项） |
| 测试 | 构建 | ✅ | `npm run build` 通过 |
| 测试 | 浏览器冒烟 | ✅ | 见下 |
| 数据 | 迁移 | ✅ | 无 schema 变更 |
| 部署 | 容器 | ✅ | 重建 api；healthz `dev_mode=true`；nginx 正常 |
| 费用 | 外部调用 | ✅ | sdp/soe_url 直接 503；session_end 返回 cost=0；用量不写 |
| 文档 | 阶段文档 + 部署说明 | ✅ | 01/02/99；docs/04 C6、docs/05、docs/06、README 已同步 |

## 浏览器实测（Chrome，1280×900）

- 登录后顶栏显示 `DEV`，用户名与头像均不显示。
- 跟读：点「跟读评分」→「提交」→ **100/100**（开发环境模拟，麦克风不出声也不连腾讯）。
- 对话：AI 开场 → 自动出现孩子句 → 即时优化卡片 `I like playing football with my friends.`；
  点「结束对话，进入复盘」→ 复盘句 1 条 → 跟读评分 **100/100**。
- 造句：输入 `i like play football` → 反馈“说得不错”+ 优化句 `I like playing football.`。
- `/speak/improve`、`/speak/review/import`、`/speak/time` 均 200；console 无报错。
- 测试账号与产生的发言/复盘/时长数据已清理，原有 4 个账号未动。

## 结论

**PASS**

## 遗留项

1. 开发模式只验证了模拟链路，真实 Qwen / SOE 链路需在正式环境配置 Key 后回归。
2. 开发对话为固定脚本（3 组循环），用于跑通交互而非评估教学内容。
3. 开发模式时长按页面计时（非麦克风能量检测），仅用于测试计时/打卡显示。
4. 复盘数据从服务端返回前，页面会短暂显示“本次没有可复盘的句子”；数据到达后正常，属现有加载时序。
