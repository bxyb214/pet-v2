# data-src — 学习数据源

存放四个板块的源数据 JSON（从旧项目 `_work/`、`PET/js/*.js` 迁移整理）：

```
data-src/
├─ vocab/     # 必默 / 高频 / 固搭 / 同义 四库（源：PET/js/data.js）
├─ reading/   # testN.json + SCHEMA.md（源：_work/gen/）
├─ listening/ # 题目+原文 JSON（源：_work/listen/src/）
└─ speak/     # shadow.json / scenes.json（源：_work/speak_src/）
```

构建：`python tools/build_data.py`（待实现）→ 产出 `frontend/public/data/*.js` + 媒体清单。
迁移期约定：音频/图片文件放 NAS 的 `media/` volume（本地开发放仓库根 `media/`，已 gitignore）。
