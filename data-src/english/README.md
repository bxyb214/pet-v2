# data-src/english — 英语内容资料模板

> English 分 **KET / PET / FCE**（初中英语后续再加），页面逻辑共用，内容按级别独立。
> **PET** 的五个模块已从现有构建产物导出到模板；**KET** 已回填单词（必默 / 高频 / 固搭 / 同义）、
> 阅读（五本教材 24 套）、语法（10 天核心语法）、听力（五本教材 24 套音频）和口语（45 个场景）。
> KET 的阅读/语法/听力/口语由 `tools/build_ket_content.py` 构建到 `public/data/ket/`。

## 目录

```text
data-src/english/
├─ README.md
├─ ket/  words.xlsx  reading.xlsx  grammar.xlsx  listening.xlsx  speaking.xlsx
├─ pet/  同上
└─ fce/  同上
```

- 模板由 `tools/make_content_templates.py` 生成，**不要手改 xlsx 结构**；
  已填内容会被脚本默认跳过，只有加 `--force` 才会覆盖。
- 现有数据导出：`tools/export_content.py`（PET 全模块 + KET 单词）。导出会重建目标工作簿，
  已有数据时需加 `--force`；导出后再用校验器确认。
- 每份工作簿第一页是「说明」，之后每页第 1 行是表头；不要合并单元格、不要加标题行。
- 校验：`backend/.venv/Scripts/python.exe tools/check_content.py --exam ket --module reading`
  （mac/Linux 用 `backend/.venv/bin/python`）。有空表只提示「尚无数据」，不会报错。

## 级别与书目

每个级别各 5 本书：Trainer 1、Trainer 2、青少年 1/2/3。阅读和听力使用书目。

| 级别 | Trainer 1 | Trainer 2 | 青少年 1/2/3 |
|---|---|---|---|
| PET | `t1`（沿用，现有进度不变） | `t2`（沿用） | `teen1` / `teen2` / `teen3` |
| KET | `k-t1` | `k-t2` | `k-teen1` / `k-teen2` / `k-teen3` |
| FCE | `f-t1` | `f-t2` | `f-teen1` / `f-teen2` / `f-teen3` |

- 书目 ID 必须全站唯一：阅读/听力进度键是 `read:<book>:<test>:<part>`、
  `listen:<book>:<test>:<part>`，不带级别。
- `test_no` 在级别内唯一。PET 现有：Trainer 2 = 1–6、Trainer 1 = 101–106；
  新书按 100 一段（青少年 1 = 201–206、青少年 2 = 301–306、青少年 3 = 401–406）。
- 句子 ID 全级别唯一，建议 `<book_id>-t<test_no>-p<part>-s<n>`，如 `k-t1-t1-p1-s01`。

## 各模块表结构

### words.xlsx

| 工作表 | 列 |
|---|---|
| 必默 / 高频 / 固搭 | 分组、英文、中文、音标、词性、英文例句、例句中文、用法/辨析、音频 |
| 同义 | 分组、原短语、原短语中文、同义短语、同义短语中文、音频 |

- 必默/高频/固搭：英文、中文必填；同义：原短语、同义短语必填。
- 去重：必默/高频/固搭按英文（去首尾空格、连续空白归一、转小写）去重；
  同义库按「原短语 + 同义短语」这一对去重（同一原短语可有多个同义说法）。
- 跨库重复只提示不删。
- KET 的「核心词 + 易混词 → 必默」合并由 `tools/build_data.py` 从旧源完成；
  导出到模板时同表去重（重复行补空字段、合并释义/分组；同义库按「原短语 + 同义短语」
  保留多个说法），空英文/空同义短语行跳过。

### reading.xlsx

| 工作表 | 列 |
|---|---|
| 书目 | book_id、书名、简介 |
| 套题 | book_id、test_no、标题、备注 |
| Part | book_id、test_no、part、题型、重点 |
| 句子 | book_id、test_no、part、句子ID、英文、中文、关键信息、题型、考点、考点标签、解析、时态 |
| 成分 | 句子ID、成分、文本 |
| 语法点 | 句子ID、考点编号、考点名称、说明 |
| 语法题 | 句子ID、题干、A、B、C、D、答案、解析、考点编号 |

- 题型：`meaning` / `blank` / `grammar`，多个用逗号分隔；PET 现有句子三型全考。
- 每个句子至少 1 道语法题、至少 3 块成分；语法题答案填 1–4。
- 关键信息若填写，必须是英文原句里的片段。
- 考点填 `grammar.xlsx`「语法体系」里的编号；考点标签是页面上展示的一句话。
- 语法点编号必须能在 `grammar.xlsx` 的「语法体系」里找到。

### grammar.xlsx

| 工作表 | 列 |
|---|---|
| 语法体系 | 天、天名称、考点编号、考点名称 |
| 例句 | 句子ID、英文、中文、考点编号、考点名称、说明 |
| 成分 | 句子ID、成分、文本 |
| 语法题 | 句子ID、题干、A、B、C、D、答案、解析、考点编号 |

- 例句 ID 不能与 reading.xlsx 的句子 ID 重复；语法题可引用任一侧的句子。
- 每个例句至少 1 道语法题；每个考点建议至少 1 道题。

### listening.xlsx

| 工作表 | 列 |
|---|---|
| 书目 | book_id、书名、简介 |
| 套题 | book_id、test_no、标题、时长(秒) |
| Part | book_id、test_no、part、题型、标签、题号范围、音频文件、时长(秒) |
| 题目 | book_id、test_no、part、题号、题干、答案、选项A/B/C、配图、起始时间t0 |
| 原文 | book_id、test_no、part、序号、t0、t1、文本 |

- 题型：`picture` / `choice` / `fill`。
- `choice` 填 3 个选项；`picture` 只填配图（选项可空）；答案都填 1–3。`fill` 填答案文本。
- 音频建议 `<book_id>-t<test_no>-p<part>.mp3`，放在 `frontend/public/audio/listen/`。
- 配图建议 `img/listen/<book_id>-t<test_no>-q<题号>.png`。
- 原文 t0/t1 按 part 内升序；缺时间轴时播放器不能逐句高亮。

### speaking.xlsx

| 工作表 | 列 |
|---|---|
| 场景包 | pack_id、part、名称、中文、学习目标、level、顺序 |
| 跟读句 | 句子ID(可空)、pack_id、英文、中文、提示、难度、重读词、来源、启用 |
| 造句题 | 题ID(可空)、pack_id、中文提示、参考答案、句型 |
| 场景 | 场景ID、pack_id、part、标题、中文、level、开场白、跟读句IDs(可空)、造句题IDs(可空) |
| 句型库(可选) | part、组ID、组名、组中文、英文、中文 |
| Part1题库(可选) | 序号、问题、中文、参考答案 |
| 范文(可选) | 编号、问题、参考答案 |

- part 1–4；pack_id 唯一，顺序用于计划切分。KET 只用 Part 1（个人信息与日常问答）和 Part 2（图片讨论）。
- 跟读句/造句题的 pack_id 必须存在；句子/题 ID 可空，构建时按 `<pack_id>-<序号>` 生成。
- 口语计划不用填，页面按 packs / scenes 和用户选择天数自动切分；KET 当前 45 个场景，页面默认 45 天计划。

## 通用规则

- 级别由路径决定，表里不填级别。
- 答案在 Excel 里用 1 基（1–4 / 1–3），构建 JSON 时转 0 基。
- 音频/图片用 ASCII slug；路径写相对 `frontend/public` 的地址。
- `frontend/public/data/*.json` 是生成产物，**不要手改**；改数据改模板/`data-src` 后重新构建。

## 生成与校验

```bash
# Windows
PY=backend/.venv/Scripts/python.exe
# mac / Linux
# PY=backend/.venv/bin/python

$PY tools/make_content_templates.py                 # 缺失才生成 15 份
$PY tools/make_content_templates.py --force         # 覆盖（会覆盖已填内容）
$PY tools/export_content.py                         # 现有 PET + KET 单词 → 模板（有数据需 --force）
$PY tools/export_content.py --exam ket --dry         # 先看行数
$PY tools/check_content.py                          # 全部级别 + 模块
$PY tools/check_content.py --exam ket --module listening
```

## 当前进度

- 已完成：模板、校验器、KET 词库合并（核心词 + 易混词 → 必默，生难词 → 高频，短语 → 固搭）。
- 已导出：PET 单词 / 阅读 / 语法 / 听力 / 口语，KET 单词。
- KET 已接入：阅读（五本教材 24 套 360 句）、语法（10 天 / 20 考点 / 20 例句）、听力（五本教材 24 套 120 个 Part 音频；2021 真题带 400 句原文，其余纯音频）、口语（45 个场景 / 135 条跟读句 / 90 道造句题；Part 1 25 个、Part 2 20 个）。构建命令 `tools/build_ket_content.py --exam ket`，产物为 `frontend/public/data/ket/{reading,listening,speak}.json`；前端按 `auth.exam` 加载。
- KET 待补：听力题目/选项原文未提供。
- 构建脚本：PET 仍走旧链（`build_reading_v2.js` 等），KET 走 `build_ket_content.py`；后续可把 PET 也迁到模板构建。
