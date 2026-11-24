<template>
  <main class="page">
    <BackButton to="/english/speak" label="返回口语" />
    <h1>{{ title }}</h1>
    <p class="sub">{{ subtitle }}</p>

    <div v-if="banner" class="banner" :class="banner.tone">{{ banner.text }}</div>
    <PaidAiNotice :status="aiStatus" />

    <div class="ctrl card">
      <div class="status">{{ status }}</div>
      <div v-if="hasPlan && phase !== 'idle'" class="timer" :class="{ warn: overTalk || overReview }">
        <template v-if="phase === 'talk'">
          对话 {{ mmss(elapsed) }} / 10:00
          <span v-if="maxSessionSec > 0"> · AI 额度剩 {{ mmss(sessionLeftSec) }}</span>
          <span v-if="overTalk"> · 可以进入 5 分钟复盘啦</span>
        </template>
        <template v-else>
          复盘 {{ mmss(reviewElapsed) }} / 5:00
          <span v-if="overReview"> · 5 分钟到了，读完这句就完成</span>
        </template>
      </div>
      <div class="ctrlbtns">
        <template v-if="phase === 'idle'">
          <PaidActionButton v-if="hasPlan || scene" :status="aiStatus" @click="start">
            开始对话
          </PaidActionButton>
          <n-button v-if="!hasPlan && scene" size="large" quaternary @click="clearScene">换一个场景</n-button>
        </template>
        <template v-else-if="phase === 'talk'">
          <n-button type="primary" size="large" secondary @click="endTalk">结束对话，进入复盘</n-button>
          <n-button size="large" quaternary @click="askHelp">怎么说？</n-button>
        </template>
      </div>
    </div>

    <!-- 无计划：从题库选一个场景直接开始 -->
    <section v-if="!hasPlan && !scene && phase === 'idle'" class="card picker">
      <div class="picker-head">
        <b>选择题库场景开始</b>
        <span>没有计划 · 自由练习，不计时、不打卡</span>
      </div>
      <div class="pfilters">
        <button
          v-for="f in SCENE_PARTS" :key="f.id" type="button"
          class="pfbtn" :class="{ on: scenePart === f.id }"
          @click="scenePart = f.id"
        >{{ f.name }}</button>
        <input v-model="sceneQ" class="psearch" type="search" placeholder="搜索场景 / 中文" />
      </div>
      <div class="plist">
        <button v-for="s in freeScenes" :key="s.id" type="button" class="pscene" @click="startScene(s)">
          <b>{{ s.title }}</b>
          <span>{{ s.cn }}</span>
          <i>{{ s.focus }}</i>
        </button>
      </div>
      <p v-if="!freeScenes.length" class="muted">没有匹配的场景</p>
    </section>

    <n-alert v-if="hint" :type="hintKind === 'praise' ? 'success' : 'info'" class="hint" :bordered="false">
      <div class="hintrow">
        <span class="tag">{{ hintKind === "praise" ? "做得好" : "小提示" }}</span>
        <span class="hint-txt">{{ hint }}</span>
        <n-button quaternary size="tiny" @click="hint = ''">×</n-button>
      </div>
    </n-alert>

    <div class="chat" ref="chatBox">
      <div v-for="m in lines" :key="m.id" class="line" :class="m.who">
        <span class="who">{{ m.who === "me" ? "我" : "AI" }}</span>
        <div class="bubble">
          <span class="txt">{{ m.text }}</span>
          <div v-if="m.who === 'me'" class="improve">
            <span v-if="m.improving" class="improving">AI 正在帮你把这句话说得更好…</span>
            <SpeakImproveCard
              v-else-if="m.improved"
              :child-said="m.text"
              :improved-en="m.improved.improved_en"
              :improved-cn="m.improved.improved_cn"
              :dims="m.improved.dims"
              @scored="onInlineScored(m, $event)"
            />
            <button v-else type="button" class="improve-btn" @click="requestImprove(m.text, true)">
              帮我改
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 5 分钟复盘：对话结束后就地展开，不再跳独立页面 -->
    <section v-if="phase === 'review'" ref="reviewBox" class="review card">
      <div class="review-head">
        <b>5 分钟复盘</b>
        <span v-if="hasPlan" class="review-time" :class="{ warn: overReview }">{{ mmss(reviewElapsed) }} / 5:00</span>
      </div>
      <p class="review-sub">把刚才 AI 优化过的句子再读一遍，85 分过关。</p>
      <p v-if="!reviewItems.length" class="muted">本次没有可复盘的句子，明天继续聊。</p>
      <div v-for="it in reviewItems" :key="it.id" class="review-item">
        <SpeakImproveCard
          show-child
          compact
          :child-said="it.child_said"
          :improved-en="it.improved_en"
          :improved-cn="it.improved_cn"
          :dims="it.dims"
          @scored="onReviewScored(it, $event)"
        />
      </div>
      <div class="review-actions">
        <n-button type="primary" size="large" @click="finishSession">完成今天练习</n-button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NAlert, NButton } from "naive-ui";
import { api, apiBeacon } from "../core/api";
import { loadSpeak, splitSpeakPlan, type PlanDayView, type Scene, type SpeakData } from "../core/speak";
import { createSpeakConn, type SpeakConn } from "../core/speakRTC";
import type { ReviewItem } from "../core/review";
import { useSpeakTime } from "../core/speakTime";
import { createImproveGuard, shouldAutoImprove } from "../core/improve";
import {
  budgetBanner, loadAiStatus, paidBlocked, paidLockText, type AiStatus,
} from "../core/aiStatus";
import BackButton from "../components/BackButton.vue";
import PaidActionButton from "../components/PaidActionButton.vue";
import PaidAiNotice from "../components/PaidAiNotice.vue";
import SpeakImproveCard from "../components/SpeakImproveCard.vue";

type Improvement = {
  child_said: string;
  improved_en: string;
  improved_cn: string;
  focus: string;
  dims: string[];
  score?: number;
  dims_ok?: string[];
};
type Line = { id: number; who: "me" | "ai"; text: string; improving?: boolean; improved?: Improvement };

const route = useRoute();
const router = useRouter();
const data = ref<SpeakData | null>(null);
const planLength = ref(0);
const scene = ref<Scene | null>(null);
const day = computed(() => Number(route.query.day ?? 1));
const hasPlan = computed(() => planLength.value > 0);
const planDays = computed<PlanDayView[]>(() =>
  hasPlan.value ? splitSpeakPlan(data.value, planLength.value) : [],
);
const planDay = computed<PlanDayView | null>(() => {
  if (!hasPlan.value || !planDays.value.length) return null;
  const idx = Math.min(Math.max(day.value, 1), planDays.value.length) - 1;
  return planDays.value[idx] ?? null;
});

// 无计划：场景题库自由选择
const scenePart = ref(0);
const sceneQ = ref("");
const SCENE_PARTS = [
  { id: 0, name: "全部" },
  { id: 1, name: "Part 1" },
  { id: 2, name: "Part 2" },
  { id: 3, name: "Part 3" },
  { id: 4, name: "Part 4" },
];
const freeScenes = computed<Scene[]>(() => {
  const needle = sceneQ.value.trim().toLowerCase();
  return (data.value?.scenes ?? []).filter((s) => {
    if (scenePart.value !== 0 && s.part !== scenePart.value) return false;
    if (!needle) return true;
    return `${s.title} ${s.cn} ${s.focus}`.toLowerCase().includes(needle);
  });
});

const conn = ref<SpeakConn | null>(null);
const aiStatus = ref<AiStatus | null>(null);
const banner = computed(() => budgetBanner(aiStatus.value));
const locked = computed(() => paidBlocked(aiStatus.value));
const lockText = computed(() => paidLockText(aiStatus.value));
const sessionId = ref(0);
const maxSessionSec = ref(0);
const sessionLeftSec = ref(0);
const improveGuard = createImproveGuard();
let wallTimer = 0;
let sessionReported = false;
const status = ref("");
const lines = ref<Line[]>([]);
const chatBox = ref<HTMLElement | null>(null);
const reviewBox = ref<HTMLElement | null>(null);
const hint = ref("");
const hintKind = ref<"hint" | "praise">("hint");
const phase = ref<"idle" | "talk" | "review">("idle");
const reviewElapsed = ref(0);
const sessionImprovements = ref<Improvement[]>([]);
const reviewItems = ref<ReviewItem[]>([]);
const overReview = computed(() => reviewElapsed.value >= 300);
let timer = 0;
let lineSeq = 0;

// 只累计孩子真正开口的秒数（服务端按天保存，刷新不丢）
const speechBase = ref(0);
const speechClock = useSpeakTime("talk", currentSpeech, () => hasPlan.value);
const elapsed = speechClock.total;
const overTalk = computed(() => elapsed.value >= 600);

function currentSpeech(): number {
  return speechBase.value + (conn.value?.speechSec() ?? 0);
}
function settleTalk(): void {
  if (conn.value) speechBase.value += conn.value.speechSec();
}

const title = computed(() =>
  scene.value ? `场景对话 · ${scene.value.title}` : hasPlan.value ? "自由对话" : "对话自由练习",
);
const subtitle = computed(() => {
  if (scene.value) {
    return hasPlan.value
      ? `${scene.value.cn} · ${scene.value.focus} · 10 分钟对话 + 5 分钟复盘`
      : `${scene.value.cn} · ${scene.value.focus} · 自由练习，不计时、不打卡`;
  }
  return hasPlan.value
    ? "15 分钟自由对话：10 分钟对话 + 5 分钟复盘；AI 会把你的回答改成更好的说法，边聊边跟读"
    : "没有计划：从题库选一个场景开始，AI 会把你的回答改成更好的说法；不计时、不打卡";
});

onMounted(async () => {
  data.value = await loadSpeak();
  aiStatus.value = await loadAiStatus();
  window.addEventListener("pagehide", onPageHide);
  try {
    const r = await api<{ length: number }>("/speak/plan");
    planLength.value = r.length ?? 0;
  } catch { /* 离线按默认 90 天 */ }
  const sid = String(route.query.scene ?? "");
  if (sid) scene.value = (data.value.scenes ?? []).find((c) => c.id === sid) ?? null;
  if (!hasPlan.value && !scene.value) status.value = "从下面题库选一个场景开始";
});
onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  if (wallTimer) clearInterval(wallTimer);
  window.removeEventListener("pagehide", onPageHide);
  reportSession(); // 路由离开/关闭页：留一条补报（幂等）
  settleTalk();
  conn.value?.close();
});

async function start(): Promise<void> {
  if (locked.value) {
    status.value = lockText.value;
    if (!aiStatus.value) aiStatus.value = await loadAiStatus(true);
    if (locked.value) return;
  }
  if (!aiStatus.value) aiStatus.value = await loadAiStatus(true);
  const patterns = recentPatterns();
  try {
    const boot = await api<{ instructions: string }>("/speak/boot", {
      method: "POST",
      body: JSON.stringify({
        mode: "talk",
        day: planDay.value?.from ?? 0,
        scene_title: scene.value?.title ?? planDay.value?.sceneTitle ?? "",
        scene_focus: scene.value?.focus ?? "",
        patterns,
      }),
    });
    conn.value = await createSpeakConn({
      mode: "talk",
      instructions: boot.instructions,
      turnDetection: "vad",
      onStatus: (s) => (status.value = s),
      onUserTranscript: (t) => {
        pushLine("me", t);
        void requestImprove(t);
      },
      onReply: (t) => {
        pushLine("ai", t);
      },
      onError: (m) => (status.value = "出错：" + m),
      onHint: (t) => {
        hintKind.value = "hint";
        hint.value = t;
      },
      onPraise: (t) => {
        hintKind.value = "praise";
        hint.value = t;
      },
      onMicClosed: () => {
        if (timer) clearInterval(timer);
        timer = 0;
        settleTalk();
        conn.value = null;
        phase.value = "idle";
        status.value = "麦克风已关闭，可以重新开始对话";
      },
    });
    lines.value = [];
    sessionImprovements.value = [];
    reviewItems.value = [];
    hint.value = "";
    status.value = "连接中…";
    phase.value = "talk";
    reviewElapsed.value = 0;
    sessionId.value = conn.value?.sessionId ?? 0;
    maxSessionSec.value = conn.value?.maxSessionSec ?? 0;
    sessionLeftSec.value = maxSessionSec.value;
    sessionReported = false;
    void loadAiStatus(true).then((s) => (aiStatus.value = s));
    if (maxSessionSec.value > 0) startWallTimer();
    if (hasPlan.value) startTimer(); // 自由练习不计时
  } catch (e) {
    status.value = (e as Error).message;
  }
}

function startScene(s: Scene): void {
  scene.value = s;
  void start();
}

function clearScene(): void {
  scene.value = null;
  status.value = "";
}

function startTimer(): void {
  if (timer) clearInterval(timer);
  timer = window.setInterval(() => {
    if (phase.value === "review") reviewElapsed.value += 1;
  }, 1000);
}

function pushLine(who: "me" | "ai", text: string): void {
  lines.value.push({ id: ++lineSeq, who, text });
  void scroll();
}

/** 每轮孩子说完 → 立即请求 PET 优化句，穿插在对话里 */
async function requestImprove(text: string, force = false): Promise<void> {
  if (!force && !shouldAutoImprove(text)) return; // P1-3：少于 4 个词不自动调用
  if (!improveGuard.take(text)) return;
  const line = [...lines.value].reverse().find((l) => l.who === "me" && l.text === text);
  if (!line || line.improved || line.improving) return;
  line.improving = true;
  try {
    const lastAi = [...lines.value].reverse().find((l) => l.who === "ai")?.text ?? "";
    const r = await api<Improvement>("/speak/improve", {
      method: "POST",
      body: JSON.stringify({
        text,
        last_ai_text: lastAi,
        scene_title: scene.value?.title ?? planDay.value?.sceneTitle ?? "",
      }),
    });
    if (r.improved_en) {
      line.improved = r;
      if (!sessionImprovements.value.some((x) => x.child_said === r.child_said)) {
        sessionImprovements.value.push(r);
      }
    }
  } catch {
    // 未配置 AI Key 或网络失败：不打断对话，结束后退回原有复盘生成
  } finally {
    line.improving = false;
  }
}

function onInlineScored(line: Line, v: { score: number; dimsOk: string[] }): void {
  if (!line.improved) return;
  line.improved.score = v.score;
  line.improved.dims_ok = v.dimsOk;
  const target = sessionImprovements.value.find((x) => x.child_said === line.improved!.child_said);
  if (target) {
    target.score = v.score;
    target.dims_ok = v.dimsOk;
  }
}

/** 结束对话 → 记时长/打卡 → 落库本次优化句 → 就地进入 5 分钟复盘 */
async function endTalk(): Promise<void> {
  if (phase.value !== "talk") return;
  phase.value = "review";
  reviewElapsed.value = 0;
  if (wallTimer) clearInterval(wallTimer);
  wallTimer = 0;
  // 计费/用量按真实会话时长；界面计时按开口时长
  const sessionSec = conn.value?.elapsedSec() ?? 0;
  const speechSec = conn.value?.speechSec() ?? 0;
  settleTalk();
  conn.value?.close();
  conn.value = null;

  try {
    sessionReported = true;
    await api("/speak/session_end", {
      method: "POST",
      body: JSON.stringify({
        seconds: sessionSec, mode: "talk", ai_seconds: speechSec, session_id: sessionId.value,
      }),
    });
  } catch { /* 离线不阻塞 */ }

  let logId = 0;
  const sourceDays = planDay.value?.sourceDays ?? [];
  const transcript = lines.value.map((l) => ({ role: l.who === "me" ? "user" : "assistant", text: l.text }));
  const turns = lines.value.filter((l) => l.who === "me").length;
  // 刚点开始就结束不记打卡，避免“0 秒完成”
  const shouldLog = turns > 0 || elapsed.value >= 60;
  if (shouldLog) {
    for (const [i, sourceDay] of sourceDays.entries()) {
      try {
        const r = await api<{ ok: boolean; log_id: number }>("/speak/log", {
          method: "POST",
          body: JSON.stringify({
            mode: "talk",
            ref: scene.value?.id ?? "",
            day: sourceDay,
            turns,
            score: 0,
            issues: [],
            transcript: i === 0 ? transcript : [],
          }),
        });
        if (i === 0) logId = r.log_id ?? 0;
      } catch { /* 离线不阻塞 */ }
    }
  }

  let items: ReviewItem[] = [];
  if (logId && sessionImprovements.value.length) {
    try {
      const r = await api<{ items: ReviewItem[] }>("/speak/review/import", {
        method: "POST",
        body: JSON.stringify({
          log_id: logId,
          items: sessionImprovements.value.map((x) => ({
            child_said: x.child_said,
            improved_en: x.improved_en,
            improved_cn: x.improved_cn,
            focus: x.focus,
            dims: x.dims,
          })),
        }),
      });
      items = r.items ?? [];
    } catch { /* 离线不阻塞 */ }
  }
  // 兜底：没有即时优化句时，仍按整段对话生成复盘
  if (logId && !items.length) {
    try {
      const r = await api<{ items: ReviewItem[] }>("/speak/review", {
        method: "POST",
        body: JSON.stringify({ log_id: logId }),
      });
      items = r.items ?? [];
    } catch { /* 无 Key 等：直接显示完成 */ }
  }
  reviewItems.value = items;
  await nextTick();
  reviewBox.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function onReviewScored(it: ReviewItem, v: { score: number; dimsOk: string[] }): Promise<void> {
  await gradeReview(it, v.score, v.dimsOk);
}

async function gradeReview(it: ReviewItem, score: number, dimsOk: string[]): Promise<void> {
  try {
    const r = await api<ReviewItem>("/speak/review/grade", {
      method: "POST",
      body: JSON.stringify({ id: it.id, score, dims_ok: dimsOk }),
    });
    it.done = r.done ?? it.done;
  } catch { /* 离线不阻塞 */ }
}

function recentPatterns(): string[] {
  if (!data.value || !planDay.value) return [];
  const byId = new Map(data.value.shadow.map((s) => [s.id, s]));
  return planDay.value.shadowIds
    .map((id) => byId.get(id)?.en ?? "")
    .filter(Boolean)
    .slice(0, 3);
}

async function askHelp(): Promise<void> {
  const lastAi = [...lines.value].reverse().find((l) => l.who === "ai")?.text ?? "";
  try {
    const r = await api<{ cn: string; en: string; en_cn: string }>("/speak/help", {
      method: "POST",
      body: JSON.stringify({
        scene_title: scene.value?.title ?? planDay.value?.sceneTitle ?? "",
        last_ai_text: lastAi,
      }),
    });
    hintKind.value = "hint";
    hint.value = [r.cn, r.en, r.en_cn].filter(Boolean).join(" · ");
  } catch (e) {
    status.value = "求助失败：" + (e as Error).message;
  }
}

function finishSession(): void {
  conn.value?.close();
  conn.value = null;
  if (hasPlan.value) {
    void router.push("/english/speak");
    return;
  }
  // 自由练习：留在本页，回到场景选择
  phase.value = "idle";
  scene.value = null;
  lines.value = [];
  reviewItems.value = [];
  sessionImprovements.value = [];
  hint.value = "";
  status.value = "";
}

/** 页面关闭/切走：用 keepalive 补报会话秒数（P0-2；带 Authorization，sendBeacon 无法带）。 */
function reportSession(): void {
  if (phase.value !== "talk" || sessionReported || !conn.value) return;
  sessionReported = true;
  const c = conn.value;
  void apiBeacon("/speak/session_end", {
    seconds: c.elapsedSec(),
    ai_seconds: c.speechSec(),
    mode: "talk",
    session_id: sessionId.value,
  });
}

function onPageHide(): void {
  reportSession();
}

/** AI 可用时长到点：自动收尾进入复盘（P0-1 硬停用）。 */
function startWallTimer(): void {
  if (wallTimer) clearInterval(wallTimer);
  wallTimer = window.setInterval(() => {
    if (phase.value !== "talk" || !conn.value) return;
    const used = conn.value.elapsedSec();
    sessionLeftSec.value = Math.max(0, maxSessionSec.value - used);
    if (maxSessionSec.value > 0 && used >= maxSessionSec.value) {
      hintKind.value = "hint";
      hint.value = "本次 AI 额度用完了，先进入复盘；免费功能仍可用。";
      void endTalk();
    } else if (maxSessionSec.value > 0 && used >= maxSessionSec.value * 0.8) {
      status.value = `AI 额度快用完了，约剩 ${Math.max(0, maxSessionSec.value - used)} 秒`;
    }
  }, 5000);
}

async function scroll(): Promise<void> {
  await nextTick();
  chatBox.value?.scrollTo({ top: chatBox.value.scrollHeight });
}
function mmss(s: number): string {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.card { background: var(--c-surface); border: 1px solid var(--c-line); border-radius: var(--r-card); box-shadow: var(--shadow-card); }
.banner { margin-bottom: 12px; padding: 10px 14px; border-radius: var(--r-btn); font-size: var(--fs-sub); font-weight: 600; }
.banner.warn { background: var(--c-accent-soft); color: var(--c-accent); border: 1px solid var(--c-accent); }
.banner.danger { background: var(--c-danger-soft); color: var(--c-danger); border: 1px solid var(--c-danger); }
.ctrl { padding: 16px; margin-bottom: 12px; text-align: center; }
.ctrlbtns { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
.status { color: var(--c-text-2); margin-bottom: 10px; min-height: 20px; }
.picker { padding: 14px; margin-bottom: 12px; }
.picker-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
.picker-head b { color: var(--c-text); font-size: 15px; }
.picker-head span { color: var(--c-text-2); font-size: 12.5px; }
.pfilters { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
.pfbtn {
  border: 1px solid var(--c-line); background: var(--c-surface); color: var(--c-text);
  border-radius: 999px; padding: 6px 12px; font: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
}
.pfbtn.on { background: var(--c-primary-strong); border-color: var(--c-primary-strong); color: #fff; }
.psearch {
  flex: 1; min-width: 160px; max-width: 300px; border: 1px solid var(--c-line);
  border-radius: 999px; padding: 7px 13px; font: inherit; font-size: 13px;
  color: var(--c-text); background: var(--c-surface);
}
.plist {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 8px; max-height: 340px; overflow: auto; padding-right: 4px;
}
.pscene {
  text-align: left; border: 1px solid var(--c-line); background: var(--c-surface);
  border-radius: var(--r-btn); padding: 10px 12px; cursor: pointer;
  display: flex; flex-direction: column; gap: 2px; font: inherit; color: var(--c-text);
  transition: border-color var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out);
}
.pscene:hover { border-color: var(--c-primary); transform: translateY(-1px); }
.pscene:focus-visible { outline: 3px solid var(--c-accent); outline-offset: 2px; }
.pscene b { font-size: 14px; }
.pscene span { color: var(--c-text-2); font-size: 12.5px; }
.pscene i { color: var(--c-text-3); font-size: 12px; font-style: normal; line-height: 1.4; }
.timer { font-variant-numeric: tabular-nums; font-weight: 700; color: var(--c-primary); margin-bottom: 10px; }
.timer.warn { color: var(--c-accent); }
.hint { display: flex; align-items: center; gap: 8px; padding: 10px 14px; margin-bottom: 12px; background: var(--c-primary-soft); border-left: 4px solid var(--c-primary); }
.tag { font-size: var(--fs-sub); font-weight: 700; color: var(--c-primary); flex-shrink: 0; }
.hint-txt { flex: 1; color: var(--c-text); }
.chat { display: flex; flex-direction: column; gap: 8px; padding-bottom: 20px; }
.line { display: flex; gap: 8px; align-items: flex-start; }
.line.me { flex-direction: row-reverse; }
.who { background: var(--c-mint-bg); color: var(--c-primary); border-radius: var(--r-sm); padding: 2px 8px; font-size: var(--fs-sub); font-weight: 700; flex-shrink: 0; }
.line.me .who { background: var(--c-primary-soft); }
.bubble { display: flex; flex-direction: column; max-width: 78%; }
.line.me .bubble { align-items: flex-end; }
.txt { background: var(--c-surface); border-radius: var(--r-btn); padding: 10px 14px; color: var(--c-text); box-shadow: var(--shadow-sm); }
.line.me .txt { background: var(--c-primary-soft); }
.improve { width: 100%; }
.improving { display: inline-block; color: var(--c-text-2); font-size: var(--fs-sub); padding: 4px 2px; }
.improve-btn { border: 1px dashed var(--c-line); background: var(--c-surface); color: var(--c-primary-strong); border-radius: var(--r-pill); padding: 5px 12px; font: inherit; font-size: 12px; font-weight: 700; cursor: pointer; }
.improve-btn:hover { background: var(--c-primary-soft); }
.review { margin-top: 18px; padding: 16px; }
.review-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; color: var(--c-text); }
.review-time { color: var(--c-primary); font-variant-numeric: tabular-nums; font-weight: 700; }
.review-time.warn { color: var(--c-accent); }
.review-sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 12px; }
.muted { color: var(--c-text-2); font-size: var(--fs-sub); }
.review-item { margin-bottom: 10px; }
.review-actions { display: flex; justify-content: flex-end; margin-top: 14px; }
</style>
