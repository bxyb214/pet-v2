# 数学 · 李永乐「一课通关」— 自省

> 结论：**PASS-with-notes**（AirPlay 设备投屏与 iPad 真机播放需人工验证，用户已确认真机可用；见 §6）
> 第二步「课程 → 年级教材」结构调整见 §8，结论同为 PASS-with-notes。
> 日期：2026-11-23（§8 同日追加）。对应需求 `01-requirements.md`、设计 `02-design.md`。

## 1. 需求覆盖

| 编号 | 实现 | 验证 |
|---|---|---|
| MT1 | 侧栏数学 → `/math/lessons`；两页签「课程 / 学习进度」；旧 `/math` 重定向 | 生产 Playwright：侧栏含「数学 / 一课通关 / 学习进度」；页签 `课程|学习进度` |
| MT2 | 13 节、5 个主题分组、课号 40–50（含 43.1/43.2）、难度标签、状态 | 生产：`rows=13, groups=5`；分组与标签截图核对 |
| MT3 | 播放器播放/暂停、拖动、时间、全屏；nginx 静态直出 + Range | 生产：视频 metadata `duration=2306.6s, readyState=4`；媒体请求 3 次均 `206`；2 GB 文件 `Range 100-199 → 206` |
| MT4 | 1.0 / 1.25 / 1.5 三档，本地记住 | 生产：点 1.25x → `playbackRate=1.25`，`localStorage.pet_math_rate=1.25` |
| MT5 | 播到结尾才学完；未学完续播；进度同步 | 生产：播种 `idx=754` → 打开即 `currentTime=754`；播到结尾 → `ended`、出现「已学完」、本地与 push 均为 `{key:"math:v:g3-42",seen:["done"],idx:1731}`；首页状态变「已学完」 |
| MT6 | iPad Safari AirPlay；Remote Playback 兜底 | 代码按 `webkitShowPlaybackTargetPicker` / `remote.prompt` 分支；按钮按能力显示。**真机投屏未在自动化中验证** |
| MT7 | 进度页：统计、13 格墙、正在学清单 | 生产：`tiles=13, done=1, watching=1`；「上次看到 12:34」 |

## 2. 设计与实现一致性

- 方案与 `02-design.md` 一致：视频走 nginx `/media/math`（不经过 FastAPI），清单走
  `data-src → tools/build_math.js → public/data/math.json`，进度复用 `progress`。
- 偏差 1：播放器落在 `components/MathPlayer.vue`（设计写组件树时按组件处理，合理）。
- 偏差 2：为防"拖动到结尾即学完"，兜底判定只在**正在播放且距结尾 0.5s 内**触发；
  `ended` 仍是主判定。
- 偏差 3：额外修复 `tools/check_overflow.js` 的假 token（见 §5），否则冒烟只在登录页。

## 3. 代码与测试

| 项 | 结果 |
|---|---|
| `vue-tsc --noEmit` | 通过 |
| 前端 vitest | **158 passed**（新增 `core/math.test.ts` 13 例 + store 1 例） |
| 后端 pytest | **97 passed**（无后端代码改动） |
| `vite build` | 通过；`dist/data/math.json` 已生成 |
| `tools/check_tokens.py` | 通过（38 文件 / 40 token） |
| `check_overflow.js`（20+3 路由 × 1440/820/390） | 无横向溢出 |
| 生产 Playwright（打桩 API + 真实静态/视频） | 见 §1 数值 |

- 单文件行数：MathHome ≈210、MathLesson ≈190、MathProgress ≈330、MathPlayer ≈300。
- 无新增依赖；无硬编码密钥；媒体目录用 compose 默认值 + `PET_MATH_MEDIA` 覆盖。
- 同步合并语义未改：`progress` 的 `seen` 并集 / `idx` 取大原样使用。

## 4. 部署与运维

- 生产 8088 已部署；nginx 挂载 `/vol2/1000/media/felix/math → /media/math:ro`。
- **发现并处理**：NAS 媒体目录原为 mode `000`，容器内 `uid=101(nginx)` 无法读取（root 可以）。
  已在宿主执行 `chmod -R a+rX /vol2/1000/media/felix/math`，复测 uid 101 可读；docs/06 已写明新视频同样要补。
- **发现并处理**：修改 `deploy/nginx.conf` 后 `docker compose up -d` 不重建 nginx（bind mount 文件 inode），
  容器继续读旧文件。已用 `up -d --force-recreate nginx` 应用，docs/06 记录该运维要点。
- 媒体不进部署包，部署体积不变（dist 仍只含 JSON/音频）。

## 5. 工具修复

`tools/check_overflow.js` 原来用 `access_token: "t"`。路由守卫会解析 JWT `exp`，非 JWT 直接判过期并回登录页，
因此历史溢出检查实际只扫了登录页。改为 JWT 形状的假 token 后，本功能才真正扫到业务页面（结果仍全部通过）。
该问题同时影响既有页面的历史冒烟结论，建议后续回归时以此版本为准。

## 6. 遗留与风险

1. **iPad 真机投屏未验证**：无真机/Apple TV 环境。代码路径与按钮显示已就绪，
   需人工在 iPad Safari 打开视频页 → 点「投屏」→ 选择电视确认；AirPlay 时倍速以电视端为准。
2. **iPhone 全屏**：容器全屏在 iOS 不可用时回退原生视频全屏（控件交给系统），功能可用但样式不同。
3. **2 GB 课程（43.1）首播起播较慢**：已用 `preload="metadata"` + Range；弱网仍可能等待。
4. **媒体无逐请求鉴权**：与现有听力音频一致，仅家庭局域网使用；不含隐私数据。
   （2026-11-24 已被 [math-grade4](../math-grade4/01-requirements.md) 取代：`/media/math/` 改为登录 + 媒体令牌。）
5. 生产口语 Key 仍待更新（与本功能无关，见 v1.29）。

## 7. 文档

- 新增：`docs/dev/math-yongle/01-requirements.md`、`02-design.md`、本文件；`data-src/math/README.md`。
- 更新：`docs/02`（架构/数据链/进度键）、`docs/04`（MT 段 + v1.30）、`docs/05`（数学组件模式 + v0.15）、
  `docs/06`（媒体卷、权限、nginx 重建）、`deploy/.env.example`、`tools/check_overflow.js`。

## 8. 第二步：课程 → 年级教材（结构调整）

### 8.1 需求覆盖（`01-requirements.md` §7）

| 编号 | 实现 | 验证 |
|---|---|---|
| S2-AC1 | `李永乐一课通关` 成为课程（`/math`），下设按年级分册的教材 | 生产：首页 `h1=李永乐一课通关`；教材页 `/math/books/yongle-g3` |
| S2-AC2 | 四年级、五年级占位，显示「即将上线」，不参与进度统计 | 生产：首页 `soon=2`；进度页年级选择 `三年级\|四年级 即将上线\|五年级 即将上线` |
| S2-AC3 | 突出当前是三年级 | 首页 40px `三年级` 特色卡 + 「已上线」标；教材页 62px 绿色年级牌；课时页年级胶囊；进度页「三年级进度墙」 |
| S2-AC4 | 旧链接兼容 | 生产：`/math/lessons/g3-40 → /math/books/yongle-g3/g3-40` |

### 8.2 实现与数据

- 数据 schema v2：`data-src/math/yongle_grade3.json` 顶层 `course` + `books[]`（每本含 `mediaDir`），
  `tools/build_math.js` 校验 `comingSoon` 书可为空、在售书不可为空、课时 id 跨年级唯一。
- 路由四层：`/math` → `/math/books/:bookId` → `/math/books/:bookId/:lessonId`，加 `/math/progress`；
  旧 `/math/lessons*` 重定向到三年级。
- 进度键仍是 `math:v:<lessonId>`，`progress` 表结构、同步合并语义（`seen` 并集 / `idx` 取大）零改动。
- 课时 `src` 由 `book.mediaDir` + `lesson.file` 拼出，新增年级只改 `data-src` 与 NAS 目录。

### 8.3 代码与测试

| 项 | 结果 |
|---|---|
| `vue-tsc --noEmit` | 通过 |
| 前端 vitest | **161 passed**（`core/math.test.ts` 扩到按书 / 按年级进度） |
| `vite build` | 通过；`dist/data/math.json` schema v2 |
| `tools/check_tokens.py` | 通过 |
| `check_overflow.js`（含新路由 × 1440/820/390） | 无横向溢出 |
| 生产 Playwright（打桩 API + 真实视频） | 首页 `三年级 / soon=2 / tabs=教材\|学习进度`；教材 `rows=13, groups=5`；视频 `duration=1731.3s, readyState=4`、`206`、`1.25x`；播完出现「这一节学完了」，本地与 push 均为 `{key:"math:v:g3-42",seen:["done"],idx:1731}`；进度页 `tiles=13, done=1, watching=1`、标题「三年级进度墙」；旧链接重定向正确 |

- 单文件行数：MathHome ≈200、MathBook ≈240、MathLesson ≈190、MathProgress ≈330，均 ≤400。
- 无新增依赖；无新增密钥；媒体仍只读挂载 `/vol2/1000/media/felix/math`。

### 8.4 偏差与遗留

1. 播放器从 `views` 移到 `components/MathPlayer.vue`（第一步遗留，仍按设计作为组件）。
2. 课程首页页签仍叫「教材 / 学习进度」：选中「教材」即课程页（年级卡列表），与旧导航习惯衔接；
   若后续年级增多，可考虑改名「年级」。
3. 旧 `/math/lessons*` 重定向写死到 `yongle-g3`，因为历史链接只可能属于三年级。
4. 媒体权限：新增年级目录上传后仍需 `chmod -R a+rX`（docs/06 已写）。
