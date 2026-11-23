# 数学课程数据源

`yongle_grade3.json` 是「李永乐一课通关」三年级的课程清单（13 节，课号 40–50，含 43.1/43.2）。

- 视频文件不在这里，也不进 git：它们位于 NAS 的
  `/vol2/1000/media/felix/math/grade_3/`，由 nginx 以 `/media/math/` 只读直出。
- `file` 必须与 NAS 上的真实文件名完全一致（保留中文、空格、半角括号）；页面会做 URL 编码。
- 新增/调整课程：
  1. 改本文件（`group` 决定页面分组顺序，`tag` 是难度/类型胶囊）；
  2. `node tools/build_math.js` 生成 `frontend/public/data/math.json`；
  3. `cd frontend && npm run build` 后部署；
  4. 在 NAS 上补读权限：`sudo chmod -R a+rX /vol2/1000/media/felix/math`。

进度不需要在这里配置：前端按 `math:v:<lessonId>` 写入同步的 `progress`，
播放到结尾才记 `done`，否则只记已看秒数。
