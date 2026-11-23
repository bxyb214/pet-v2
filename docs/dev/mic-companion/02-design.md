# 麦克风数字人陪练 — 设计

## 1. 结构

```text
speakRTC.getUserMedia（真实） / devSpeak（模拟）
SoeEval.start（真实/模拟）
        │ 成功拿到音频后
        ▼
core/micPresence.holdMic(stop)  ──►  micActive = true
        │                               │
        │                               ▼
        │                     AppLayout 渲染 <MicCompanion>
        │                     .main.mic-on 让出右侧 1/3
        ▼
「关闭麦克风」→ stopMic() → 各 stop：页面清理 + 关闭连接/轨道 → releaseMic()
        ▼
micActive = false → 数字人消失、内容区恢复
```

## 2. 麦克风占用登记（`core/micPresence.ts`）

- 模块级 `Map<id, stop>` + `micActive` 响应式布尔；`holdMic(stop)` 返回幂等释放函数。
- 只有**真正拿到麦克风之后**才登记；权限被拒/连接失败不会出现数字人。
- `stopMic()` 复制一份回调后逐个执行，单个失败不影响其他；回调内部负责关闭连接/轨道并释放。
- 开发环境没有真实麦克风，但 `createDevSpeakConn` / `SoeEval` 开发分支同样登记，
  保证数字人可测；面板文案改为「模拟语音中」。

## 3. 接入点

| 位置 | 登记时机 | stop 行为 |
|---|---|---|
| `core/speakRTC.ts` | `getUserMedia` 成功、音频已加入 PeerConnection 后 | `onMicClosed()` → `conn.close()`（停轨道、DataChannel、PC） |
| `core/devSpeak.ts` | 模拟连接创建时 | `onMicClosed()` → 清定时器、标记关闭 |
| `core/soe.ts` | 真实：`getUserMedia` 成功后；开发：`start()` 模拟就绪时 | `onMicClosed()` → `stop()`（ws、worklet、AudioContext、轨道） |
| `SpeakShadow.vue` | 通过上述 conn/SOE | 结算已开口秒数、清空实例、状态提示可重新开始 |
| `SpeakTalk.vue` | Realtime conn | 停止计时、结算开口秒数、phase 回 idle、提示可重新开始 |
| `SpeakImproveCard.vue` | 卡片内 SOE | 结束评分态，提示需要时再点「跟读这句」 |

页面通过新增的可选回调 `onMicClosed` 清理自身状态；core 负责真正关闭音频。
`onMicClosed` 先于 core 关闭执行，页面仍可读到 `speechSec()` 结算时长。

## 4. 数字人面板（`components/MicCompanion.vue`）

- 纯 SVG 卡通数字人（耳机 + 麦克风杆），配呼吸浮动、眨眼、声波扩散、5 根音量条动画，
  全部只动 `transform/opacity/height`；`prefers-reduced-motion` 下关闭动画。
- 顶部状态胶囊：正式环境「麦克风开启中」绿底；开发环境「模拟语音中」暖橙底。
- 名称「小绿 · AI 陪练」+ 一句提示；开发环境提示“数字人为预览，未调用真实麦克风”。
- 面板最下方整宽红色药丸按钮「关闭麦克风」（麦克风划线图标），高度 ≥50px，
  `aria-label` 与可见文字一致，键盘可用。

### 4.1 尺寸与响应式

| 视口 | 形态 | 尺寸 |
|---|---|---|
| ≥1101px | 右侧浮动面板，垂直居中 | `clamp(320px, 33vw, 420px)` 宽 × `min(72vh, 640px)` 高 |
| 900–1100px | 右侧浮动面板收窄 | 300px 宽 × 72vh |
| ≤899px（手机/竖屏 iPad） | 底部面板 | 左右各 10px，高 `38vh`（250–330px） |

内容区让位由 `AppLayout` 控制：

- 桌面：`.main.mic-on { padding-right: clamp(320px,33vw,420px) + 32px }`；
- ≤1100px：`padding-right: 324px`；
- ≤899px：`padding-bottom: calc(38vh + 30px)`，内容向上滚动，不被面板盖住。

## 5. 备选方案与取舍

| 方案 | 结论 |
|---|---|
| 只显示一个“麦克风开启”小图标 | ❌ 不满足“数字人 + 1/3 屏”的要求，孩子感知弱 |
| 在每个口语页各写一份面板 | ❌ 重复、容易与采集状态不同步 |
| 由页面在 conn/soe 存在时显示 | ❌ 页面拿不到 `getUserMedia` 的真实成功时机，且内嵌卡片难同步 |
| 关闭麦克风仅静音轨道、保留会话 | ❌ Realtime 依赖用户音频，静音后会话无意义；直接结束更诚实 |
| **全局占用登记 + 统一面板（选定）** | ✅ 采集状态单一来源，所有入口一致，关闭一次清理全部占用 |

## 6. 风险

| 风险 | 缓解 |
|---|---|
| 多个采集同时存在（对话 + 内嵌跟读） | 登记表支持多占用；`stopMic` 全部停止，全部释放后数字人才消失 |
| 关闭回调中再次 release 造成递归 | 释放函数幂等；`conn.close()/stop()` 内再次释放为 no-op |
| 面板挡住对话内容 | 布局层为麦克风状态预留右侧/底部空间，而不是纯浮层覆盖 |
| 开发环境误以为调用了真麦克风 | 状态胶囊与提示明确写「模拟」 |
| 用户关闭麦克风后不知如何继续 | 页面状态提示“可以重新开始”，开始按钮恢复 |
| 窄屏横向滚动 | ≤899px 改底部面板；按钮整宽，无固定宽度溢出 |
