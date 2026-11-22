# speak 数据源（data-src/speak/）

来源：`pet-v2/_work/speak_textbooks/` 下的 PET 口语官方教辅（**仅 PET，KET/FCE 内容不用**）。

## 文件清单

| 文件 | 来源书 | 内容 | 提取方式 |
|---|---|---|---|
| `part1_85.json` | 2024新版PET口语215话题 p2-43 | 85 题 Part1 问答（题干/译文/参考答案）+ 17 分类 | `tools/extract_speak_215.py` 文本层解析，85/85 全量 |
| `part1_130.json` | 同上 p44-69 | 131 条话题范文（含原书重复编号 51b） | 同上，131/130 全量（原书编号笔误多出 1 条） |
| `patterns.json` | 新版PET口语模板 p4-12 + 满分宝典 p6/p9 交叉核对 | 11 组 78 句型（Part1-4），**造句模块核心** | 人工转录（260dpi 逐页核对） |
| `rubric.json` | PET口语满分宝典 p3 | 剑桥评分标准：总体表现 + 四维（语法词汇/话语连贯/发音/交流）1-5 分档 | 人工转录（300dpi 复核「重音一般很准」） |
| `toc_zhen2.json` | 24-26真题-Part2 目录 | 89 个真题图片描述场景标题 | 目录页视觉转录 |
| `toc_zhen34.json` | 24-26真题-Part3-4 目录 | 55 个真题讨论话题标题 | 目录页视觉转录 |
| `demos.json` | 新版PET口语模板 p9-10/p14-15 | Part2 描述示范 2 篇（18 句）+ Part3 讨论对话 11 轮 | 文本层转录；中文为对照翻译（非原书） |

## 构建链

```
data-src/speak/*.json ──→ node tools/build_speak_v3.js [--dry] ──→ frontend/public/data/speak.json (schema v3)
```

speak.json v3 在旧字段（shadow/packs/free/scenes/plan）基础上新增：
`part1bank`(85) / `essays`(131) / `patterns`(78句) / `rubric` / `categories`(17) / `zhen2`(89) / `zhen34`(55) / `meta.sources`。

## 模块对应

| 前端模块 | 数据 |
|---|---|
| 跟读 | shadow/packs：Part1 85 题问答（按 17 分类分 17 包）+ Part2 示范 18 句 + Part3 示范 11 轮 |
| 造句（新） | patterns：11 组 78 句 |
| 实时对话 | scenes：Part1 17 分类场景 + Part2 89 真题图场景 + Part3(+4) 55 真题话题 |

## 红线与备注

- 全部内容来自原书，解析/转录跳过的条目都在脚本输出里报告，**不臆造**
- 真题册参考答案（zhen2/zhen34 每题详解）尚未逐页补录——目录标题先入数据，答案按页核对后增量追加
- Part2 图片裁切（`frontend/public/img/speak/`）待做，工具可参考旧站 `tools/crop_pics.py`
- 满分宝典/模板书用 2020 官方 Part 编号；215话题书未分 Part（全部按 Part1 访谈处理）
