# 数学 · 李永乐「一课通关」— 设计

> 对应需求：`01-requirements.md`（MT1–MT7）。日期：2026-11-23。

## 1. 方案概览

```text
浏览器
 ├─ GET /data/math.json            nginx → dist/data/math.json（课程清单，构建产物）
 ├─ GET /media/math/grade_3/<file>  nginx alias → /media/math（只读挂载 NAS 媒体目录）
 │                                  支持 Range（nginx 静态模块），拖动/断点续播
 └─ POST /api/v1/sync/push         复用 progress：
      key = "math:v:<lessonId>"
      idx = 已看秒数（取大）
      seen 含 "done" = 学完（并集）

NAS 宿主 /vol2/1000/media/felix/math/grade_3/*.mp4
      └─ docker 只读卷 → nginx:/media/math（workers 以 uid 101 读取）
```

- 视频**不经 FastAPI**：大文件由 nginx `sendfile` 直出，Range 天然支持；后端不承担字节流。
- 进度**不新增表/字段**：复用 `progress` 的既有合并语义（`seen` 并集、`idx` 取大），不触碰红线。
- 课程清单是构建产物：`data-src/math/yongle_grade3.json` → `tools/build_math.js` → `frontend/public/data/math.json`。

## 2. 契约

### 2.1 静态数据 `GET /data/math.json`

```json
{
  "version": 1,
  "series": [{
    "id": "yongle-g3",
    "title": "李永乐一课通关",
    "grade": 3,
    "gradeName": "三年级",
    "mediaDir": "grade_3",
    "lessons": [{
      "id": "g3-40", "no": "40", "title": "枚举法（一）",
      "tag": "拓展B", "group": "枚举法",
      "file": "40 枚举法(一)(拓展B).mp4", "size": 214295563
    }]
  }]
}
```

- `file` 保留 NAS 真实文件名（不重命名用户媒体）；前端 `encodeURIComponent` 后拼接。
- 排序：`no` 按数值（`43.1` / `43.2` 排在 `43` 之后）。

### 2.2 媒体 `GET /media/math/<mediaDir>/<file>`

- `200` 全量；`206 Partial Content` + `Content-Range`（Range 请求）；`404` 文件不存在；`403` 容器无读权限。
- 响应头：`Accept-Ranges: bytes`，`Cache-Control: public, max-age=3600`；不压缩。
- nginx 片段：

```nginx
location /media/math/ {
    alias /media/math/;
    add_header Accept-Ranges bytes always;
    add_header Cache-Control "public, max-age=3600";
    gzip off;
}
```

- compose（prod / dev 两处相同）：

```yaml
volumes:
  - ${PET_MATH_MEDIA:-/vol2/1000/media/felix/math}:/media/math:ro
```

### 2.3 同步 `POST /api/v1/sync/push`（不改）

数学进度写入既有 `progress[]`：

```json
{"key": "math:v:g3-40", "seen": ["done"], "idx": 735}
```

- 未学完：`seen` 为空，`idx` = 已看秒数。
- 学完：`seen` 追加 `"done"`（只增不减，天然不可撤销）。
- 合并：服务端 `merge.py` 与前端 `merge.ts` 已有语义（seen 并集 / idx 取大），**无改动**。
- 副作用评估：`progress` 的其它消费者仅按自己的 key 前缀读取（阅读 `read:*`），不会读到 `math:*`。

## 3. 数据模型

无表结构变更、无 Alembic 迁移。`progress.key` 长度上限 128，`math:v:g3-43.1` 远小于上限。

## 4. 前端

### 4.1 路由与导航

```ts
const MATH_TABS = [
  { label: "课程", to: "/math/lessons" },
  { label: "学习进度", to: "/math/progress" },
];
// /math                 → redirect /math/lessons
// /math/lessons         Meta: subject=math, module=lessons, tabs=MATH_TABS
// /math/lessons/:id     Meta: subject=math, module=lessons
// /math/progress        Meta: subject=math, module=progress, tabs=MATH_TABS
```

- `RouteMeta.module` 联合类型追加 `"lessons" | "progress"`。
- `SiderNav` 在 `subject === "math"` 时展示两个板块入口（一课通关 / 学习进度）。
- 顺带修复侧栏学科色块类名：现有 CSS 用 `.en/.cn/.ma`，绑定却是 `english/chinese/math`，数学/语文高亮从未生效；改为显式 `cls` 字段。

### 4.2 组件树

```text
MathHome.vue
 ├─ 概览卡（已学完 x/13、进度条、继续学习）
 └─ 主题分组 → 课程行（序号 / 标题 / 标签 / 状态 / 进度）

MathLesson.vue
 ├─ BackButton + 标题/标签
 ├─ 播放器 .player
 │   ├─ <video playsinline x-webkit-airplay="allow">
 │   └─ 控制条：播放/暂停、n-slider 进度、mm:ss、倍速 1.0/1.25/1.5、投屏、全屏
 ├─ 已学完横幅 /「从头看」
 └─ 上一课 · 下一课

MathProgress.vue
 ├─ 统计（已学完 / 学习中 / 未开始）
 ├─ 13 格进度墙（done / watching / todo，点击进入）
 └─ 学习中清单（上次看到 mm:ss → 继续）
```

### 4.3 纯逻辑 `core/math.ts`

| 函数 | 说明 |
|---|---|
| `loadMath()` | fetch `/data/math.json`，模块级缓存 |
| `videoUrl(lesson, mediaDir)` | `/media/math/<dir>/<encodeURIComponent(file)>` |
| `lessonKey(id)` | `math:v:<id>` |
| `isDone(rec)` | `rec?.seen.includes("done")` |
| `statusOf(rec)` | done / watching / todo（未学完且 idx>0） |
| `seriesProgress(lessons, recOf)` | `{total, done, watching, todo, percent}` |
| `nextLesson(lessons, recOf)` | 第一节未学完；全学完返 null |
| `SPEEDS` | `[1, 1.25, 1.5]` |

### 4.4 store

`stores/learning.ts` 新增：

```ts
recordVideoProgress(key: string, seconds: number, done = false): void
```

- `idx = max(旧值, floor(seconds))`；`done` 时向 `seen` 追加 `"done"`；无变化不写。
- 写入后 `markDirty()`（本地持久化 + 防抖同步）。

### 4.5 播放器行为

- 保存时机：`timeupdate` 每 15 秒一次、`pause`、`ended`、离开页面；避免每秒推送。
- 续播：`loadedmetadata` 后，未学完且 `10 < idx < duration - 10` → `currentTime = idx`。
- 学完：`ended` → `recordVideoProgress(..., true)`，展示「已学完」和下一课。
- 倍速：`playbackRate` + `localStorage["pet_math_rate"]`（仅本地，不进同步）。
- 投屏：`video.webkitShowPlaybackTargetPicker`（Safari/iPad AirPlay）优先；否则
  `video.remote.prompt()`（Remote Playback / Cast）。按钮仅在能力存在时显示。
- 全屏：优先容器 `requestFullscreen()`（保留自定义控制条）；iOS 回退 `video.webkitEnterFullscreen()`。
  AirPlay 由接收端播放，倍速以电视端为准（页面上注明）。

## 5. 备选方案与取舍

| 方案 | 结论 | 理由 |
|---|---|---|
| A. FastAPI 流式接口 `GET /api/v1/math/media/{id}` + `FileResponse` | 否 | 大文件占满 API 线程；nginx sendfile 更稳；现有音频也是静态直出；家庭局域网无逐请求鉴权需求 |
| B. 视频拷进 `frontend/dist` 随部署包上传 | 否 | 5.4 GB，部署包/构建时间不可接受；`emptyOutDir:false` 下易残留 |
| C. 新增 `math_progress` 表 + 同步字段 | 否 | 触碰同步红线；`progress` 的 seen/idx 语义正好够用 |
| D. 在 NAS 建 ASCII 软链接再服务 | 否（本次） | 增加仓库外状态；中文名用 `encodeURIComponent` 可稳定访问；如后续改名再统一迁移 |
| E. 用原生 `<video controls>` 省事 | 否 | 无法放 1.0/1.25/1.5 三档自定义倍速与品牌化控制条 |

## 6. 风险与缓解

| 风险 | 缓解 |
|---|---|
| **容器读不到媒体**（实测宿主目录原为 mode 000，nginx uid 101 被拒） | 上线前对媒体目录执行 `chmod -R a+rX`；docs/06 写明；部署后用 Range 请求验证 206 |
| 2 GB 视频首次 seek 慢 | `preload="metadata"` + Range；nginx sendfile；媒体缓存 1h |
| 中文/空格/括号文件名 | 清单保留原名，前端逐段 `encodeURIComponent`；单测断言 |
| Safari 不支持容器全屏 | 回退 `webkitEnterFullscreen`（原生控件） |
| AirPlay 期间倍速无效 | 页面提示"投屏后倍速以电视为准" |
| 进度推送过频 | 15 秒节流 + 无变化不写；同步引擎本身 1.2s 防抖 |
| 手机 390px 控制条溢出 | 控制条分组换行；`check_overflow` 加入新路由 |
| 端口 8088 直连时无鉴权 | 与现有音频一致；媒体目录仅含课程视频，不含隐私数据 |
