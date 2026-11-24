# 数学课程数据源

`yongle.json` 是「李永乐一课通关」课程清单（schema v2）：

- `course`：课程信息（标题、简介）。
- `books[]`：按年级分册的教材。现在三年级（`yongle-g3`，13 节）与四年级（`yongle-g4`，51 节）
  已上线；五年级（`yongle-g5`）只有占位，`comingSoon: true`、`lessons: []`，
  页面显示「即将上线」，上传视频后把课时补进来、去掉 `comingSoon` 即自动上线。

视频文件不在这里，也不进 git：位于 NAS 的
`/vol2/1000/media/felix/math/<mediaDir>/`（三年级 `grade_3/`，四年级 `grade_4/`），
由 nginx 以 `/media/math/` 只读直出；**取流需要登录**（`?mt=` 短时效媒体令牌，见 docs/dev/math-grade4）。

- `file` 必须与 NAS 上的真实文件名完全一致（保留中文、空格、半角括号）；页面会做 URL 编码。
- `tag` 是难度/类型胶囊；文件名没标注难度的课留空字符串，页面不显示，不臆造难度。
- 课时 `id` 跨年级必须唯一（进度键是 `math:v:<lessonId>`）。
- 新增/调整课程：
  1. 改本文件（`group` 决定分组顺序；新年级补一节 `books[]` 项）；
  2. `node tools/build_math.js` 生成 `frontend/public/data/math.json`；
  3. `cd frontend && npm run build` 后部署；
  4. 在 NAS 上补读权限：`sudo chmod -R a+rX /vol2/1000/media/felix/math`。

进度不需要在这里配置：前端按 `math:v:<lessonId>` 写入同步的 `progress`，
播放到结尾才记 `done`，否则只记已看秒数。
