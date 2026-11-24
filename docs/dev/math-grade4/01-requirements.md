# 数学 · 四年级课程上线 + 视频登录鉴权 — 需求

> 日期：2026-11-24；分支 `feat/ai-budget`；关联 [02 设计](02-design.md)、[99 自省](99-self-review.md)。

## 1. 背景与目标

用户已把李永乐「一课通关」四年级视频上传到 NAS
`/vol2/1000/media/felix/math/grade_4/`（51 个 mp4，约 17.0 GB）。
现状：四年级教材是 `comingSoon: true` 的空占位，页面显示「即将上线」。

同时提出新的访问约束：**视频文件较大，访问必须是登录用户，直接通过链接不行**。
现有的 `/media/math/` 是 nginx 静态直出，任何人拿到 URL 都能下载/播放。

目标：

1. 四年级课程在站内上线（教材页、视频页、进度页、首页年级卡）。
2. `/media/math/` 只允许本站登录用户取流；无登录态的直接链接不可用。
3. 不破坏已确认可用的 iPad AirPlay 投屏，不把视频字节流经 FastAPI。
4. 进度仍复用 `progress`（`math:v:<lessonId>`），不改同步合并语义。

## 2. 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| G4-1 | 首页同时展示三、四年级大卡，各自进度/继续学习；五年级仍「即将上线」 | P0 |
| G4-2 | 四年级教材页 51 节按主题分组，课号 01–50（42.1/42.2，缺 30/38）＋练习题 | P0 |
| G4-3 | 难度/类型标签取自文件名（校内A/拓展B/浅奥C/讲座/回放）；未标注的留空不显示 | P1 |
| G4-4 | 四年级视频可播放、拖动、倍速、全屏、AirPlay；进度跨设备同步 | P0 |
| G4-5 | 未登录直接访问 `/media/math/...` → 401；登录用户播放页自动带上鉴权参数 | P0 |
| G4-6 | 鉴权参数短时效（默认 6 小时），退出登录后前端不再复用 | P1 |

## 3. 验收标准（Given / When / Then）

| 编号 | Given | When | Then |
|---|---|---|---|
| G4-AC1 | 已登录 | 打开 `/math` | 看到「三年级」「四年级」两张已上线大卡；五年级虚线「即将上线」 |
| G4-AC2 | 已登录 | 点四年级 → 教材页 | 51 行、19 个主题分组；42.1/42.2 在 42 之后；练习题在最后 |
| G4-AC3 | 打开四年级任一课 | 播放并拖动 | 播放正常，Range 返回 206；播完记「已学完」 |
| G4-AC4 | 未登录 / 不带令牌 | `curl /media/math/grade_4/01...mp4` | 401，取不到任何字节 |
| G4-AC5 | 已登录 | 视频页 / 直接带 `?mt=` 请求 | 200/206，可拖动；令牌伪造或过期 → 401 |
| G4-AC6 | iPad Safari | 点「投屏」 | AirPlay 仍可用（由电视端凭 URL 中的 `mt` 取流） |
| G4-AC7 | 两台设备分别看四年级不同课 | 同步完成 | 完成记录取并集，互不覆盖 |

## 4. 非目标

- 不做后台上传/删除/排序；新增课时仍改 `data-src/math/yongle.json` 后重新构建。
- 不转码、不抽字幕、不提供下载按钮；mp4 需浏览器原生可播。
- 不按用户/课程做细粒度授权（登录即可看全部课程）。
- 不改 `progress` 表结构、同步合并语义与错题 dims 记账。

## 5. 影响面

- 数据：`data-src/math/yongle_grade3.json` → `yongle.json`；四年级 51 节；`tools/build_math.js`。
- 前端：`views/MathHome.vue`（多年级大卡）、`views/MathLesson.vue`（媒体令牌）、
  `core/mediaToken.ts`（新增）、`core/math.ts`（URL 带 `mt`）、`layouts/SiderNav.vue`。
- 后端：`api/v1/media.py`（新增，签发/校验媒体令牌）、`core/security.py`、`core/config.py`、
  `api/v1/__init__.py`；无表结构变更、无 Alembic 迁移。
- 部署：`deploy/nginx.conf` 增加 `auth_request`；compose 透传 `PET_MEDIA_TOKEN_HOURS`。
- 运维：NAS 目录需对容器可读（现状已可读）；部署后 nginx 需 force-recreate。
