<template>
  <main class="page">
    <BackButton @click="back" />
    <h1>
      跟读纠音
      <span v-if="planDay" class="daychip">第 {{ planDay.day }} 天 · {{ sourceRangeText(planDay) }}</span>
    </h1>
    <p class="sub">跟读 → 提交 → AI 打分与建议（读完点「提交」）· 今天目标 5 分钟</p>

    <!-- 5 分钟目标：只提示，不强制 -->
    <div class="card targetbar" :class="{ over: overGoal }">
      <span class="target-label">今日跟读</span>
      <b class="target-time">{{ mmss(elapsed) }}</b>
      <span class="target-goal">/ 5:00</span>
      <span class="target-hint">
        {{ overGoal ? "已到 5 分钟，练完这句就休息吧" : `剩余 ${mmss(Math.max(0, 300 - elapsed))}` }}
      </span>
    </div>

    <div v-if="!loaded" class="empty card">加载中…</div>
    <div v-else-if="!item" class="empty card">
      今天的跟读内容为空
      <div class="mt"><n-button @click="router.push('/english/speak')">返回口语</n-button></div>
    </div>
    <template v-else>
      <div class="sent card">
        <div class="en">{{ item.en }}</div>
        <div class="cn">{{ item.cn }}</div>
        <div v-if="item.tip" class="tip">💡 {{ item.tip }}</div>
        <div class="sent-actions">
          <n-button size="small" secondary @click="tts">🔊 听示范（AI 朗读）</n-button>
          <n-button size="small" quaternary @click="next">换一句 →</n-button>
          <span class="idx">{{ itemIdx + 1 }} / {{ orderedItems.length }}</span>
        </div>
      </div>

      <div class="ctrl card">
        <div class="status">{{ status }}</div>
        <div class="ctrlbtns">
          <template v-if="!conn && !soe">
            <n-button type="primary" size="large" @click="start">开始跟读（AI 点评）</n-button>
            <n-button size="large" secondary @click="startSoe">精准发音评分（腾讯云）</n-button>
          </template>
          <template v-else-if="soe">
            <n-button type="primary" size="large" @click="submitSoe">提交</n-button>
            <n-button size="large" quaternary @click="stopSoe">结束练习</n-button>
          </template>
          <template v-else>
            <n-button type="primary" size="large" @click="submit">提交</n-button>
            <n-button size="large" quaternary @click="stop">结束练习</n-button>
          </template>
        </div>
      </div>

      <div v-if="result" class="result card" :class="{ good: result.score >= 85, ok: result.score >= 60 }">
        <div class="score">{{ result.score }}<small>/100</small></div>
        <div class="engine">{{ engine === "soe" ? "腾讯云精准评测" : "AI 点评" }}</div>
        <div v-if="result.say" class="say">{{ result.say }}</div>
        <div v-if="result.transcript" class="heard">AI 听到的是：{{ result.transcript }}</div>
        <div class="words">
          <n-tag v-for="(w, i) in result.words" :key="i" size="small" :bordered="false" :type="w.ok ? 'default' : 'error'" round>
            {{ w.w }}
          </n-tag>
        </div>
        <ul v-if="result.tips.length" class="tips">
          <li v-for="(t, i) in result.tips" :key="i">{{ t }}</li>
        </ul>
        <div class="res-actions">
          <n-button type="primary" @click="next">下一句 →</n-button>
          <n-button quaternary @click="stop">结束练习（保存记录）</n-button>
        </div>
      </div>
    </template>

    <audio ref="ttsEl" style="display:none"></audio>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NTag } from "naive-ui";
import { api } from "../core/api";
import {
  loadSpeak, parseShadowReply, sourceRangeText, splitSpeakPlan,
  type PlanDayView, type ShadowItem, type SpeakData,
} from "../core/speak";
import { createSpeakConn, type SpeakConn } from "../core/speakRTC";
import { SoeEval, type SoeResult } from "../core/soe";
import { useSpeakTime } from "../core/speakTime";
import BackButton from "../components/BackButton.vue";

const route = useRoute();
const router = useRouter();
const data = ref<SpeakData | null>(null);
const planLength = ref(0);
const loaded = ref(false);
const itemIdx = ref(0);
const day = computed(() => Number(route.query.day ?? 1));

const planDays = computed<PlanDayView[]>(() =>
  splitSpeakPlan(data.value, planLength.value || 90),
);
const planDay = computed<PlanDayView | null>(() => {
  const idx = Math.min(Math.max(day.value, 1), planDays.value.length) - 1;
  return planDays.value[idx] ?? null;
});
const orderedItems = computed<ShadowItem[]>(() => {
  if (!data.value || !planDay.value) return [];
  const byId = new Map(data.value.shadow.map((s) => [s.id, s]));
  return planDay.value.shadowIds.map((id) => byId.get(id)).filter((s): s is ShadowItem => !!s);
});
const item = computed<ShadowItem | null>(() => {
  if (!orderedItems.value.length) return null;
  return orderedItems.value[itemIdx.value % orderedItems.value.length];
});

const conn = ref<SpeakConn | null>(null);
const soe = ref<SoeEval | null>(null);
const engine = ref<"ai" | "soe">("ai");
const status = ref("");
const lastReply = ref("");
const result = ref<ReturnType<typeof parseShadowReply>>(null);
const scores = ref<number[]>([]);
const ttsEl = ref<HTMLAudioElement | null>(null);

// 只累计“真正开口”的秒数，并由服务端按天保存，刷新不丢
const speechBase = ref(0);
const activeKind = ref<"ai" | "soe" | null>(null);
const clock = useSpeakTime("shadow", currentSpeech);
const elapsed = clock.total;
const overGoal = computed(() => elapsed.value >= 300);

function currentSpeech(): number {
  if (activeKind.value === "ai") return speechBase.value + (conn.value?.speechSec() ?? 0);
  if (activeKind.value === "soe") return speechBase.value + (soe.value?.speechSec() ?? 0);
  return speechBase.value;
}
function settleSpeech(): void {
  if (activeKind.value === "ai" && conn.value) speechBase.value += conn.value.speechSec();
  if (activeKind.value === "soe" && soe.value) speechBase.value += soe.value.speechSec();
  activeKind.value = null;
}

onMounted(async () => {
  try {
    data.value = await loadSpeak();
    try {
      const r = await api<{ length: number }>("/speak/plan");
      planLength.value = r.length ?? 0;
    } catch { /* 离线按默认 90 天 */ }
  } finally {
    loaded.value = true;
  }
});
onBeforeUnmount(() => {
  settleSpeech();
  conn.value?.close();
  soe.value?.stop();
});

function start(): void {
  if (!item.value) return;
  result.value = null;
  scores.value = [];
  engine.value = "ai";
  void run();
}
async function run(): Promise<void> {
  try {
    const boot = await api<{ instructions: string; mode: string }>("/speak/boot", {
      method: "POST",
      body: JSON.stringify({ mode: "shadow", day: planDay.value?.from ?? 0, target: item.value?.en ?? "" }),
    });
    conn.value = await createSpeakConn({
      mode: "shadow",
      instructions: boot.instructions,
      turnDetection: "manual",
      onStatus: (s) => (status.value = s),
      onUserTranscript: () => { /* 转录到时补齐 */ },
      onReply: (t) => {
        lastReply.value = t;
        const r = parseShadowReply(t);
        if (r) {
          result.value = r;
          scores.value.push(r.score);
        }
      },
      onError: (m) => (status.value = "出错：" + m),
    });
    activeKind.value = "ai";
  } catch (e) {
    status.value = (e as Error).message;
  }
}
function submit(): void {
  status.value = "AI 评分中…";
  conn.value?.commitAndRespond();
}

async function startSoe(): Promise<void> {
  if (!item.value) return;
  result.value = null;
  scores.value = [];
  engine.value = "soe";
  settleSpeech();
  conn.value?.close();
  conn.value = null;
  const ev = new SoeEval({
    refText: item.value.en,
    onStatus: (s) => (status.value = s),
    onResult: (r: SoeResult) => {
      const bad = r.words.filter((w) => !w.ok).map((w) => w.w);
      result.value = {
        transcript: "",
        score: r.score,
        words: r.words,
        tips: bad.length ? [`读不准的词：${bad.join("、")}，多听几遍示范再试试`] : [],
        say: "",
      };
      scores.value.push(r.score);
    },
    onError: (m) => (status.value = "出错：" + m),
  });
  soe.value = ev;
  try {
    await ev.start();
    activeKind.value = "soe";
  } catch {
    soe.value = null;
    engine.value = "ai";
  }
}
function submitSoe(): void {
  soe.value?.submit();
}
function stopSoe(): void {
  settleSpeech();
  void finish();
  soe.value?.stop();
  soe.value = null;
  void router.push("/english/speak");
}

function stop(): void {
  settleSpeech();
  void finish();
  conn.value?.close();
  conn.value = null;
  void router.push("/english/speak");
}
async function finish(): Promise<void> {
  if (!scores.value.length || !planDay.value) return;
  const avg = Math.round(scores.value.reduce((a, b) => a + b, 0) / scores.value.length);
  for (const sourceDay of planDay.value.sourceDays) {
    try {
      await api("/speak/log", {
        method: "POST",
        body: JSON.stringify({
          mode: "shadow", ref: item.value?.pack ?? "", day: sourceDay,
          turns: scores.value.length, score: avg,
          issues: result.value?.tips ?? [], transcript: [],
        }),
      });
    } catch { /* 离线不阻塞 */ }
  }
}
function next(): void {
  if (!orderedItems.value.length) return;
  itemIdx.value = (itemIdx.value + 1) % orderedItems.value.length;
  result.value = null;
}
async function tts(): Promise<void> {
  try {
    const r = await api<{ b64: string; mime: string }>("/speak/tts", {
      method: "POST",
      body: JSON.stringify({ text: item.value?.en ?? "" }),
    });
    const el = ttsEl.value;
    if (el) {
      el.src = `data:${r.mime};base64,${r.b64}`;
      void el.play();
    }
  } catch (e) {
    status.value = (e as Error).message;
  }
}
function mmss(s: number): string {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}
function back(): void {
  settleSpeech();
  void finish();
  conn.value?.close();
  soe.value?.stop();
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.daychip { font-size: var(--fs-sub); color: var(--c-primary); font-weight: 600; margin-left: 6px; }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.empty { padding: 40px; text-align: center; color: var(--c-text-2); }
.mt { margin-top: 14px; }
.card { background: var(--c-surface); border: 1px solid var(--c-line); border-radius: var(--r-card); box-shadow: var(--shadow-card); }
.targetbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 10px 14px; margin-bottom: 12px; color: var(--c-text-2); font-size: var(--fs-sub);
}
.target-label { font-weight: 700; color: var(--c-text); }
.target-time { color: var(--c-primary); font-variant-numeric: tabular-nums; font-size: 16px; }
.target-goal { color: var(--c-text-2); }
.target-hint { margin-left: auto; color: var(--c-text-2); }
.targetbar.over { background: var(--c-accent-soft, #fffbeb); border-color: var(--c-accent, #f59e0b); }
.targetbar.over .target-hint { color: var(--c-accent, #b45309); font-weight: 600; }
.sent { padding: 18px; margin-bottom: 12px; }
.en { font-size: var(--fs-title); color: var(--c-text); font-weight: 600; }
.cn { color: var(--c-text-2); margin-top: 6px; }
.tip { color: var(--c-accent); margin-top: 8px; font-size: var(--fs-sub); }
.sent-actions { margin-top: 12px; display: flex; gap: 8px; align-items: center; }
.idx { margin-left: auto; color: var(--c-text-2); font-size: var(--fs-sub); }
.ctrl { padding: 16px; margin-bottom: 12px; text-align: center; }
.ctrlbtns { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
.status { color: var(--c-text-2); margin-bottom: 10px; min-height: 20px; }
.result { padding: 18px; }
.result.good { border-color: var(--c-primary); }
.result.ok { border-color: var(--c-accent); }
.score { font-size: 36px; font-weight: 800; color: var(--c-primary); }
.score small { font-size: var(--fs-sub); color: var(--c-text-2); }
.engine { font-size: var(--fs-sub); color: var(--c-text-2); margin-top: 2px; }
.say { color: var(--c-text); margin-top: 4px; }
.heard { color: var(--c-text-2); font-size: var(--fs-sub); margin-top: 6px; }
.words { margin-top: 10px; }
.tips { color: var(--c-text-2); font-size: var(--fs-sub); margin: 8px 0 0; padding-left: 18px; }
.res-actions { margin-top: 12px; display: flex; gap: 8px; }
</style>
