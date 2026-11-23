# 口语跟读 / 造句 / 题库重组 v4 — 设计

## 1. 数据模型

新增 `data-src/speak/curriculum_v4.json`，一份文件承载 45 个场景：

```jsonc
{
  "version": 4,
  "scenes": [{
    "id": "s01",
    "part": 1,                       // 1 访谈 / 2 图片描述 / 3 讨论
    "title": "Greetings and introductions",
    "cn": "问候与介绍",
    "focus": "完整句回答 + 原因/举例扩展",
    "openers": ["Good morning! How are you today?"],
    "sourceRefs": ["215话题 1-5", "essays 68"],
    "shadow": [{ "en": "...", "cn": "...", "tip": "..." }],   // 3 条
    "make":  [{ "prompt_cn": "...", "answer": "...", "pattern": "reason" }] // 2 条
  }]
}
```

`tools/build_speak_v3.js` 改为优先读取该文件（schema 4），派生：

| 输出字段 | 规则 |
|---|---|
| `packs` | 每个场景一包：`{ id: scene.id, name: title, part, ids, order }` |
| `shadow` | `id = s01-1`，`pack = s01`，`packName = title` |
| `scenes` | 原样输出，补 `shadowIds` 与 `make[].id` |
| `make` 题 | 只嵌在 `scenes[].make`，不单独建表 |
| `part1bank / essays / patterns / rubric / zhen2 / zhen34` | 保留，作为原始教辅与句型库 |

构建时校验：45 个场景、id 唯一、每场 3 条 shadow / 2 条 make、`en` 以句号/问号/感叹号结尾、
无空字段。旧 161 场景仅保留在 `zhen2/zhen34` 原始目录字段，不再生成 `scenes`。

## 2. 场景清单（45）

- **Part1 访谈（14）**：问候与介绍、个人信息与家庭、校园学习、日常生活、衣服与购物、
  饮食、休闲爱好、住宿与家务、旅行度假、地方与家乡、音乐与媒体、社交与朋友、运动与健康、自然与环境。
- **Part2 图片描述（16）**：课堂学习、图书馆阅读、用餐、家庭烹饪、球场运动、骑行与滑板、
  公园休闲、海边、商场购物、生日庆祝、家庭居家、电子设备、出行与交通、观光游览、音乐演奏、农场动物。
- **Part3–4 讨论（15）**：礼物与奖品、旅行物品、活动地点、假期活动、校园与规则、家务与家庭、
  英语学习、环境与城市、健康生活、饮食与烹饪、电影与媒体、庆祝与派对、金钱与预算、科技与手机、志愿与助人。

Part2 的 89 张真题图、Part3 的 55 个话题在 `sourceRefs` 中分组挂到对应场景；
不再让题库页出现 161 个条目。

## 3. 前端

### 3.1 跟读（SpeakShadow）

- `packs` 变为 45 个场景包，包名即场景名；计划模式按比例取包不变。
- 每句显示英文、中文与 `tip`（朗读要点）。

### 3.2 题库（SpeakScenes）

- 自动读新 `scenes`，Part 筛选后为 14/16/15。

### 3.3 造句（SentencePage）

改为场景驱动的三步：

```text
选场景 → 显示中文提示（make.prompt_cn）
  → 「开始说」：Qwen Realtime（shadow 模式）转写用户这一句
  → 「说完了」：拿到 transcript → POST /speak/check
  → 页面同时展示：AI 点评 / 优化句 / 标准答案
```

- 自定义 instructions：只转写、不聊天，返回与跟读相同的 JSON 结构（`transcript/score/words/tips/say`）。
- 语音失败或没有麦克风：保留文本框，「用键盘输入」走同一个 `/speak/check`。
- 计划模式：优先用 `planDay.sceneIds[0]` 选场景，未命中再取第一个场景。
- 提交成功即调用原有 `logMake()` 打卡；用时统计语义不变。

### 3.4 后端 `/speak/check`

入参扩展（向后兼容）：`pattern`（标准答案）、`prompt_cn`（可选中文提示）、`sentence`。
提示词改为：先判断是否表达了中文提示的意思，再按 PET B1 给出中文点评与优化句；
`dev_mock.check` 仍按原样返回。

## 4. 构建与测试

- `node tools/build_speak_v4.js`（或 v3 内置）输出 `frontend/public/data/speak.json`。
- 新增 `tools/check_speak_v4.py`（可选）与前端 `core/speak.test.ts` 断言：
  - 45 场景、每场 3 句跟读、2 道造句；
  - 所有跟读句以 `.`/`?`/`!` 结尾且 ≥8 词；
  - 场景 id 与 pack id 一一对应。
- 现有 `speakPlan.test.ts` 的 161 场景只是通用夹具，不改断言。

## 5. 风险

| 风险 | 缓解 |
|---|---|
| 45 场景内容质量不齐 | 构建校验句子完整性；人工抽查每部分 |
| 语音转写依赖 Qwen Key | 键盘输入兜底；AI 不可用时仍显示标准答案 |
| 旧计划按 161 场景切分 | 场景按比例取，天数与打卡不变；只是每天场景更聚焦 |
| 真题内容版权/准确性 | 只引用目录标题做分组；不把参考答案冒充实录 |
