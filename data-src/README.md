# data-src — 学习数据源

> 本目录只放**口语**与**数学**的结构化源数据；词库/阅读/听力的构建脚本读取上级旧站 `../PET/js/*.js`。
> 产物统一输出到 `frontend/public/data/*.json`（不入 git）。运行期 JSON 是生成文件，不要手改。

```text
data-src/
├─ speak/      part1_85 / part1_130 / patterns / rubric / toc_zhen2 / toc_zhen34 / demos / curriculum_v4
└─ math/       yongle.json（李永乐一课通关课程清单）
```

## 构建链

| 数据 | 命令 | 源 | 产物 |
|---|---|---|---|
| 词库（PET + KET） | `python tools/build_data.py` | `../PET/js/data.js`、`ket-data.js` | `banks.json` |
| 阅读 | `node tools/build_reading_v2.js` | `../PET/js/reading-data.js` | `reading.json` |
| 听力 | `node tools/build_listening_v2.js` | `../PET/js/listening-data.js` | `listening.json` |
| 口语 | `node tools/build_speak_v4.js` | `data-src/speak/*.json` | `speak.json`（schema 5） |
| 数学 | `node tools/build_math.js` | `data-src/math/yongle.json` | `math.json`（schema 2） |

- 脚本支持 `--dry`（只校验、不写文件）。
- 音频/图片（`frontend/public/audio`、`public/img`）体积大，不进 git，由部署阶段整目录同步。
- 详细口语数据说明见 [speak/README.md](speak/README.md)。

## 约定

- 构建脚本必须校验 ID 唯一、枚举合法、计数与源一致；跳过或修正的条目要在输出中报告，**不臆造**。
- 媒体文件一律 ASCII slug（如 `t1-p1.mp3`、`sc1-1.png`）。
- 修改数据结构时同步更新对应 README 与前端 `src/core/` 的类型。
