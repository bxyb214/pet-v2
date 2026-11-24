# 数学 · 四年级课程上线 + 视频登录鉴权 — 设计

> 对应需求：[01 需求](01-requirements.md)（G4-1 ~ G4-6）。日期：2026-11-24。

## 1. 方案概览

```text
课程清单：NAS grade_4/*.mp4（51 个）
   └─ 一次性脚本生成 data-src/math/yongle.json（真实文件名 + 大小）
        └─ node tools/build_math.js → frontend/public/data/math.json

播放：GET /media/math/grade_4/<file>?mt=<媒体令牌>
   nginx auth_request → GET /api/v1/media/auth（校验 X-Media-Token）
        └─ 通过后 alias /media/math/（sendfile + Range，仍不经 FastAPI）

令牌：POST /api/v1/media/token（Authorization: Bearer access_token）
   └─ JWT type="media"，sub=user_id，有效期 PET_MEDIA_TOKEN_HOURS（默认 6h）

进度：progress key = math:v:<lessonId>，idx 取大 / seen 并集（不改）
```

## 2. 数据与页面

### 2.1 课程清单

- 源文件更名 `yongle_grade3.json` → `yongle.json`（已含三个年级，原名会误导）。
- 四年级 51 节按 NAS 实际文件名生成，**不手抄文件名**：用 paramiko/SFTP 读 `listdir_attr`，
  按课号映射标题/分组；构建脚本只做校验与排序。
- `tag`：文件名最后一个括号里是 `校内A / 拓展B / 浅奥C` 时作为难度标签；
  `(可看回放)` → `回放`，`讲座` → `讲座`。未标注的课 `tag: ""`，页面不显示，不臆造难度。
- 课号：`01`–`50`，`42.1`/`42.2` 为讲座与期末回放；NAS 缺 30、38，不补空行；
  练习题文件课号记为 `练`，构建排序把它放最后。
- 分组 19 个：大数的认识 / 线与角 / 乘法 / 平行四边形和梯形 / 面积 / 页面问题 / 除法 /
  阶段测试 / 三角形 / 行程问题 / 四则运算 / 运算律 / 多位数的计算 / 简易方程 / 小数 /
  专题讲座 / 平均数 / 等差数列 / 练习。
- `tools/build_math.js`：允许空 `tag`；排序遇到非数字课号（`练`）排最后。

### 2.2 首页多年级

原 `MathHome` 只把 `firstBook()` 渲染成大卡，其余「已上线」书不会出现在任何区块。
改为 `availableBooks()` 逐本渲染大卡（每本独立进度、继续学习、查看 N 节课）；
`comingSoon` 书仍进「后续年级」虚线卡。

## 3. 视频鉴权

### 3.1 为什么不用 Cookie

`<video>` 请求可以自动带同源 Cookie，理论上 `auth_request` 校验 Cookie 最简单；
但 iOS AirPlay 把媒体 URL 交给电视端，接收端取流**不带本站 Cookie** →
投屏会 401。已上线的三年级 AirPlay 是用户确认过的功能，不能回退。

因此令牌放查询串 `?mt=`：普通播放与 AirPlay 走同一 URL，电视端也能通过 `auth_request`。

### 3.2 令牌

- `make_media_token(user_id)`：JWT `type="media"`，`sub=user_id`，`exp=now+6h`。
  复用现有 `PET_JWT_SECRET`，**不能**用于业务接口（`get_current_user` 只认 `access`）。
- `POST /api/v1/media/token`：需 `Authorization: Bearer <access>`；返回 `{token, expires_at}`。
- `GET /api/v1/media/auth`：读 `X-Media-Token`；`decode_token(..., "media")` 通过**且用户仍存在** → 204，否则 401。
- 前端 `core/mediaToken.ts`：内存缓存，距过期 <5 分钟重取；并发合并为一次请求；
  退出登录 `clearMediaToken()`。不写 localStorage，避免令牌长期驻留。
- 令牌有效期覆盖一节课（最长 2 GB 讲座）并有 6 小时余量；过期后重新进视频页会自动换新。

### 3.3 nginx

```nginx
location = /_media_auth {
    internal;
    proxy_pass http://api:8000/api/v1/media/auth;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header X-Media-Token $arg_mt;
}

location /media/math/ {
    auth_request /_media_auth;
    alias /media/math/;
    add_header Cache-Control "private, max-age=3600";
    gzip off;
}
```

- 每个 Range 请求会有一次本地子请求（毫秒级、无外部调用）；视频字节仍由 nginx 直出。
- `proxy_pass` 不含变量，`api` 在启动时解析，无需 resolver。
- 官方 `nginx:1.27-alpine` 含 `http_auth_request_module`（已在 NAS 上 `nginx -V` 确认）。
- 缓存从 `public` 改为 `private`：带令牌的 URL 不进入共享缓存。

## 4. 备选方案与取舍

| 方案 | 结论 | 原因 |
|---|---|---|
| A. Cookie + `auth_request` | 否 | AirPlay 由电视端取流，无 Cookie → 投屏 401 |
| B. FastAPI `FileResponse` 直出 + Bearer/查询令牌 | 否 | 17 GB 课程经 uvicorn 流式转发，占 worker、易被拖动请求拖垮 |
| C. nginx `secure_link` 签名 URL | 否 | 功能等价但需另造一套签名/过期格式，且无法顺手校验用户是否仍存在；`auth_request` 复用现有 JWT 更简单 |
| D. 令牌放 URL，`auth_request` 校验 | **采用** | 兼容 AirPlay、字节不经 API、实现最小 |
| E. 只给四年级加鉴权 | 否 | 三年级同样是大文件，用户要求的是「视频」整体 |

## 5. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 带令牌 URL 被复制/出现在日志 | 6 小时过期；`Cache-Control: private`；令牌仅能取流、不能调业务接口；局域网家庭场景可接受 |
| 令牌过期时正在看长视频 | 默认 6 小时，长于最长单课；过期后重新进入页面自动换新 |
| 每次 Range 都走一次鉴权子请求 | 本机 `proxy_pass`，无外部调用；SQLite 主键查询；实测拖动正常 |
| 51 节/19 组页面过长 | 分组折叠不在本期；按课号顺序浏览，首页只展示主题胶囊 |
| AirPlay 真机未在自动化覆盖 | 设计上保留 URL 令牌；部署后需用户在 iPad 上复测投屏 |
| nginx 配置未生效 | 部署后 `--force-recreate nginx` + `nginx -t`，并用 401/206 两条 curl 验收 |

## 6. 测试

- 后端 `tests/test_media_auth.py` 6 例：未登录签发 401；正常签发/校验 204；
  access 令牌不能当媒体令牌；缺失/伪造 401；过期 401；用户删除后 401。
- 前端 `core/math.test.ts`：URL 带 `mt`；`core/mediaToken.test.ts`：缓存、临期重取、
  logout 清理、并发去重。
- 构建：`node tools/build_math.js` 校验 id 唯一、mp4、空 tag；`vue-tsc` + `vite build`。
