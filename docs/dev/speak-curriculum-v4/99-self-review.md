# 口语跟读 / 造句 / 题库重组 v4 — 自省报告

> 结论：**PASS-with-notes**
>
> 数据、页面与 AI 点评链路均已完成并验证；**真实麦克风 + Qwen Realtime 转写**
> 需要在配置了 Key 的设备上人工试说一次，开发模式（模拟语音）已跑通全流程。

## 1. 完成项

| 需求 | 结果 | 证据 |
|---|---|---|
| 161 场景 → 45 | ✅ Part1 14 / Part2 16 / Part3–4 15 | 构建统计、题库页筛选 `45 / 14 / 16 / 15` |
| 跟读句 B1+ 完整句 | ✅ 135 句，每场景 3 句；全部 ≥8 词、以 `.?!` 结尾 | `speakData.test.ts`、构建校验 |
| 跟读 / 造句 / 题库同场景 | ✅ pack id = scene id = `s01…s45`，造句题嵌在场景内 | `packs` 与 `scenes` 一一对应测试 |
| 造句：中文 → 说英文 | ✅ 中文提示卡片 + 「🎤 开始说 / 说完了」 | Playwright：按钮出现、模拟语音转写成功 |
| 造句：标准答案 | ✅ 「看标准答案」+ 提交后自动展开 | Playwright：答案文本正确 |
| 造句：AI 修改建议 | ✅ `/speak/check` 新增中文提示判断，返回点评 + 优化句 | 模拟接口与 dev mock 验证 |
| 键盘兜底 | ✅ 文本框与「让 AI 看看」始终可用 | Playwright 打字路径通过 |

## 2. 数据

- 新文件 `data-src/speak/curriculum_v4.json`：45 场景 × (3 跟读 + 2 造句)。
- 构建脚本 `tools/build_speak_v4.js`：schema 4，校验场景数、id、句子完整性、答案完整性。
- 输出 `frontend/public/data/speak.json`：245KB；原始 85 问答 / 131 范文 /
  89 图 / 55 话题 / 78 句型仍保留，便于追溯。
- 场景与真题的对应关系写在 `sourceRefs`（如 `zhen2 1, 7, 15…`、`zhen34 1, 3, 4…`）。

## 3. 代码

- `core/speak.ts`：`Scene` 增加 `shadowIds / make / sourceRefs`，新增 `MakePrompt`。
- `SentencePage.vue`：场景选择（Part 筛选 + 可搜索下拉）、中文提示、语音转写、
  标准答案、AI 点评、TTS 示范；计划模式优先使用当天场景。
- `SpeakScenes.vue`：去掉空的 Part 4 页签，改为 Part 3–4。
- `SpeakShadow.vue`：无需改逻辑，45 个中文场景包自动生效。
- 后端 `/speak/check`：新增可选 `prompt_cn`，提示词先判「意思有没有说到」再给优化。

## 4. 测试

- 前端：`vitest run` **19 文件 / 144 测试通过**（新增 `speakData.test.ts` 5 例）。
- 后端：`pytest tests/ -q` **93 passed**。
- `vue-tsc --noEmit && vite build` 通过。
- Playwright（本地 preview + 打桩接口）：
  - 题库页 45 个场景、筛选计数正确；
  - 跟读页 45 个中文包、每包 3 句；
  - 造句页中文提示、语音按钮、模拟转写、AI 点评、标准答案全部正常。

## 5. 遗留与风险

1. **真实语音转写**：开发模式用脚本模拟；生产需要在有 Qwen Key 的设备上人工试说，
   确认 `transcript` 能正确回传（失败会自动提示改用键盘输入）。
2. **内容校对**：45 场景的句子为在原书语料基础上的教学改写，已做长度/完整句/字段校验；
   建议老师抽查 Part2、Part3 各 3 个场景的英文自然度与中文提示。
3. **计划节奏**：45 场景按比例铺到 1–90 天，90 天计划中相邻两天可能重复同一场景；
   如需每天不重复，可将默认计划改为 45 天或改为轮换算法。
4. Part2 仍为文字场景，图片裁切未做（与本次目标无关）。

## 6. 上线后修复（2026-11-23）

生产验证时 `/speak/check` 返回 500，日志为
`httpx.UnsupportedProtocol: Request URL is missing an 'http://' or 'https://' protocol`。

- 根因：管理页保存配置时把未填字段写成**空串**（`llm.base_url`、`llm.model` 为空），
  `get_cfg` 拿到了空串而不是默认值，URL 变成 `/chat/completions`。
- 影响面不止造句：AI 加词、`speak.qwen` 的 model/voice 同样会拿到空串。
- 修复：`ai_enrich.chat` 与 `qwen_speak.qwen_cfg` 把空串视同未配置、回退默认值；
  新增 `backend/tests/test_ai_cfg.py`（2 例）。后端 95 测试通过后重新部署。
- 复验：生产造句页输入一句话 → 真实 AI 返回「没有完全说到：缺少告诉考官名字…」
  与优化句，标准答案同时展示。**结论维持 PASS-with-notes**，仍建议人工用麦克风试说一次。
