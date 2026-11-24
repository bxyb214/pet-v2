# 数学 · 四年级课程上线 + 视频登录鉴权 — 自省

> 日期：2026-11-24；分支 `feat/ai-budget`（未提交）；对应 [01 需求](01-requirements.md)、[02 设计](02-design.md)。
> 结论：**PASS-with-notes**（AirPlay 与 iPad 真机画面需人工复测，见 §6）。

## 1. 需求覆盖

| 编号 | 实现 | 验证 |
|---|---|---|
| G4-1 | 首页改为 `availableBooks()` 逐本渲染大卡；五年级仍「即将上线」 | 生产 Playwright：`cards=2`、年级 `[三年级, 四年级]`、soon `[五年级]` |
| G4-2 | 四年级 51 节、19 主题，课号 01–50（含 42.1/42.2，缺 30/38）＋练习题 | 生产：`rows=51`、`groups=19`、首行 `01 大数的读写`、末行 `练 练习题 第01-20讲` |
| G4-3 | 标签取自文件名；未标注的课 `tag=""`，页面不渲染胶囊 | 首行无难度胶囊；22/23/24 等显示 拓展B/浅奥C |
| G4-4 | 播放器复用；`video src` 带 `?mt=`；Range 支持 | 生产：`video src has mt: true`、`readyState=4`、`duration=1343.32s`、媒体响应 `206` |
| G4-5 | `/media/math/` 挂 `auth_request`；令牌由登录态接口签发 | 生产：无令牌 `/media/...` 401；带令牌 206；篡改令牌 401；三年级同样规则 |
| G4-6 | 令牌 6 小时、内存缓存、退出清理、并发去重 | `core/mediaToken.test.ts` 4 例；退出登录 `clearMediaToken()` |

## 2. 数据与页面

- `data-src/math/yongle_grade3.json` 更名 `yongle.json`（含三/四/五年级），
  四年级课时由 NAS 实际文件名生成（SFTP `listdir_attr`，不手抄文件名），共 51 节 / 17.03 GB。
- 文件名未带难度括号的课（如 01–21、37/39、练习题）`tag` 留空，不臆造难度；
  `tools/build_math.js` 允许空 tag，并把非数字课号（`练`）排到最后。
- 11–13 三个同名文件在标题上补「（一）（二）（三）」以便区分；`15/16 页面问题`
  保留用户原始命名（未改成「页码」）。42.1/42.2 归「专题讲座」。
- 首页原有逻辑只渲染 `firstBook()`，四年级上线后会从「后续年级」消失且无处可点；
  已改为逐本大卡，这是本次必要的 UI 修改。

## 3. 鉴权实现

- 新后端 `api/v1/media.py`：`POST /media/token`（需 Bearer access，签发 6h `type=media` JWT）、
  `GET /media/auth`（nginx 子请求，校验 `X-Media-Token` 且用户仍存在 → 204/401）。
  `core/security.make_media_token`；`core/config.media_token_hours=6`（`PET_MEDIA_TOKEN_HOURS` 可覆盖）。
- nginx：`auth_request /_media_auth`；缓存改 `private`；nginx 官方镜像确认含 `http_auth_request_module`。
- 前端：`core/mediaToken.ts` 内存缓存/临期 5 分钟重取/并发去重；`MathLesson` 先取令牌再出 `<video>`；
  `videoUrl(..., token)` 拼 `?mt=`；退出登录清理。

### 实现中发现的坑

`auth_request` 子请求 **不继承原请求的 query**，最初 `proxy_set_header X-Media-Token $arg_mt;`
在子请求里恒为空 → 有效令牌仍 401。改为在父 location `set $media_token $arg_mt;`，
子请求使用 `$media_token` 后通过。已写入 `deploy/nginx.conf` 注释，避免后续回退。

## 4. 测试与构建

| 项 | 结果 |
|---|---|
| 后端 pytest | **123 passed**（新增 `tests/test_media_auth.py` 6 例） |
| 前端 vitest | **199 passed**（新增 `mediaToken.test.ts` 4 例 + `videoUrl` 带令牌 1 例） |
| `node tools/build_math.js` | 3 本教材 / 64 节；三 13、四 51、五 0（占位） |
| `vue-tsc --noEmit` + `vite build` | 通过；入口 `assets/index-Cts0Eszv.js` |
| dist 数据 | `dist/data/math.json` 四年级 51 节 |

## 5. 部署与生产验证（2026-11-24）

- `tools/deploy_nas.py deploy --profile prod`：api 重建 + 迁移 head + 健康检查通过；
  nginx 配置变更后执行 `up -d --force-recreate nginx`，`nginx -t` 通过。
- 媒体鉴权（宿主发起）：
  - 无令牌 `Range 0-99` → **401**
  - 有效 `?mt=` → **206**，`Content-Range: bytes 0-99/227241077`
  - 篡改令牌 → **401**；三年级带令牌 → **206**
  - HEAD 无令牌 401 / 带令牌 200；`bytes=1000000-` 206；无 Range 的整段请求 200（浏览器先 HEAD 再分段取流可用）
- 页面（Playwright，真实生产 + 真实视频）：
  - `/math`：两张已上线大卡、五年级占位；`查看 51 节课`
  - `/math/books/yongle-g4`：51 行 / 19 组 / 四年级徽章
  - `/math/books/yongle-g4/g4-01`：video 带 `mt`、`readyState=4`、`duration=1343.32s`、媒体 206
  - `/math/progress`：四年级胶囊可选，点击后「四年级进度墙」
- 横向溢出（真实生产 × 1440/820/390）：`/math`、`/math/books/yongle-g4`、
  `/math/books/yongle-g4/g4-01`、`/math/progress` 的 `scrollWidth == innerWidth`，无溢出。
- 临时令牌文件已删除；`_work/` 诊断脚本不入 git。

## 6. 遗留与风险

1. **AirPlay 真机未复测**：令牌放 URL 正是为了兼容电视端取流，但本次只在桌面 Chromium
   验证播放；需用户在 iPad Safari 上点「投屏」确认（三年级此前已确认可用）。
2. **URL 令牌可复制**：6 小时内拿到完整链接的人可看该视频；令牌不能调业务接口、
   不进 localStorage、缓存为 `private`。家庭局域网场景可接受；若需更严可缩短 `PET_MEDIA_TOKEN_HOURS`。
3. **令牌会出现在 nginx access log**（URL 查询串）；日志仅管理员可读。
4. 课号 30/38 在 NAS 上不存在，未补空位；如后续上传需改 `yongle.json` 重新构建。
5. 四年级「页面问题」疑似应为「页码问题」，但保留用户文件名与标题，不做改写。
6. 视频总时长较长，首页/教材页 51 行在手机上偏长；当前未做分组折叠。
