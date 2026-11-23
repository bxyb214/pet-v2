<template>
  <main class="page">
    <BackButton @click="back" />
    <h1>{{ title }}</h1>
    <p class="sub">{{ subtitle }}</p>

    <div class="ctrl card">
      <div class="status">{{ status }}</div>
      <div v-if="phase !== 'idle'" class="timer" :class="{ warn: overTalk || overReview }">
        <template v-if="phase === 'talk'">
          对话 {{ mmss(elapsed) }} / 10:00
          <span v-if="overTalk"> · 可以进入 5 分钟复盘啦</span>
        </template>
        <template v-else>
          复盘 {{ mmss(reviewElapsed) }} / 5:00
          <span v-if="overReview"> · 5 分钟到了，读完这句就完成</span>
        </template>
      </div>
      <div class="ctrlbtns">
        <n-button v-if="phase === 'idle'" type="primary" size="large" @click="start">开始对话</n-button>
        <template v-else-if="phase === 'talk'">
          <n-button type="primary" size="large" secondary @click="endTalk">结束对话，进入复盘</n-button>
          <n-button size="large" quaternary @click="askHelp">怎么说？</n-button>
        </template>
      </div>
    </div>

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
          <div v-if="m.who === 'me' && (m.improving || m.improved)" class="improve">
            <span v-if="m.improving" class="improving">AI 正在帮你把这句话说得更好…</span>
            <SpeakImproveCard
              v-else-if="m.improved"
              :child-said="m.text"
              :improved-en="m.improved.improved_en"
              :improved-cn="m.improved.improved_cn"
              :dims="m.improved.dims"
              @scored="onInlineScored(m, $event)"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- 5 分钟复盘：对话结束后就地展开，不再跳独立页面 -->
    <section v-if="phase === 'review'" ref="reviewBox" class="review card">
      <div class="review-head">
        <b>5 分钟复盘</b>
        <span class="review-time" :class="{ warn: overReview }">{{ mmss(reviewElapsed) }} / 5:00</span>
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
import { api } from "../core/api";
import { loadSpeak, splitSpeakPlan, type PlanDayView, type Scene, type SpeakData } from "../core/speak";
import { createSpeakConn, type SpeakConn } from "../core/speakRTC";
import type { ReviewItem } from "../core/review";
import { useSpeakTime } from "../core/speakTime";
import BackButton from "../components/BackButton.vue";
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
const planDays = computed<PlanDayView[]>(() =>
  splitSpeakPlan(data.value, planLength.value || 90),
);
const planDay = computed<PlanDayView | null>(() => {
  const idx = Math.min(Math.max(day.value, 1), planDays.value.length) - 1;
  return planDays.value[idx] ?? null;
});

const conn = ref<SpeakConn | null>(null);
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
const speechClock = useSpeakTime("talk", currentSpeech);
const elapsed = speechClock.total;
const overTalk = computed(() => elapsed.value >= 600);

function currentSpeech(): number {
  return speechBase.value + (conn.value?.speechSec() ?? 0);
}
function settleTalk(): void {
  if (conn.value) speechBase.value += conn.value.speechSec();
}

const title = computed(() => (scene.value ? `场景对话 · ${scene.value.title}` : "自由对话"));
const subtitle = computed(() =>
  scene.value
    ? `${scene.value.cn} · ${scene.value.focus} · 10 分钟对话 + 5 分钟复盘`
    : "15 分钟自由对话：10 分钟对话 + 5 分钟复盘；AI 会把你的回答改成更好的说法，边聊边跟读",
);

onMounted(async () => {
  data.value = await loadSpeak();
  try {
    const r = await api<{ length: number }>("/speak/plan");
    planLength.value = r.length ?? 0;
  } catch { /* 离线按默认 90 天 */ }
  const sid = String(route.query.scene ?? "");
  if (sid) scene.value = (data.value.scenes ?? []).find((c) => c.id === sid) ?? null;
});
onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  settleTalk();
  conn.value?.close();
});

async function start(): Promise<void> {
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
    });
    lines.value = [];
    sessionImprovements.value = [];
    reviewItems.value = [];
    hint.value = "";
    status.value = "连接中…";
    phase.value = "talk";
    reviewElapsed.value = 0;
    startTimer();
  } catch (e) {
    status.value = (e as Error).message;
  }
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
async function requestImprove(text: string): Promise<void> {
  if (text.trim().length < 3) return;
  const line = [...lines.value].reverse().find((l) => l.who === "me" && l.text === text);
  if (!line) return;
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
  // 计费/用量按真实会话时长；界面计时按开口时长
  const sessionSec = conn.value?.elapsedSec() ?? 0;
  settleTalk();
  conn.value?.close();
  conn.value = null;

  try {
    await api("/speak/session_end", { method: "POST", body: JSON.stringify({ seconds: sessionSec, mode: "talk" }) });
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
  void router.push("/english/speak");
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
function back(): void {
  settleTalk();
  conn.value?.close();
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.card { background: var(--c-surface); border: 1px solid var(--c-line); border-radius: var(--r-card); box-shadow: var(--shadow-card); }
.ctrl { padding: 16px; margin-bottom: 12px; text-align: center; }
.ctrlbtns { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
.status { color: var(--c-text-2); margin-bottom: 10px; min-height: 20px; }
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
.review { margin-top: 18px; padding: 16px; }
.review-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; color: var(--c-text); }
.review-time { color: var(--c-primary); font-variant-numeric: tabular-nums; font-weight: 700; }
.review-time.warn { color: var(--c-accent); }
.review-sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 12px; }
.muted { color: var(--c-text-2); font-size: var(--fs-sub); }
.review-item { margin-bottom: 10px; }
.review-actions { display: flex; justify-content: flex-end; margin-top: 14px; }
</style>
