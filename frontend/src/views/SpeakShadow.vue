<template>
  <main class="page">
    <button class="ghost back" @click="back">← 返回口语</button>
    <h1>跟读纠音 <span v-if="day" class="daychip">第 {{ day }} 天</span></h1>
    <p class="sub">跟读 → 提交 → AI 打分与建议（人工判停：读完点「提交」）</p>

    <div v-if="dueCount > 0" class="card duebar">
      <span>有 {{ dueCount }} 句上次对话的复盘句到期了，先复盘效果更好</span>
      <n-button size="small" type="warning" secondary @click="router.push('/english/speak/review')">去复盘</n-button>
    </div>

    <div v-if="!item" class="empty card">加载中…</div>
    <template v-else>
      <div class="sent card">
        <div class="en">{{ item.en }}</div>
        <div class="cn">{{ item.cn }}</div>
        <div v-if="item.tip" class="tip">💡 {{ item.tip }}</div>
        <div class="sent-actions">
          <n-button size="small" secondary @click="tts">🔊 听示范（AI 朗读）</n-button>
          <n-button size="small" quaternary @click="next">换一句 →</n-button>
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
            <n-button size="large" quaternary @click="stopSoe">结束</n-button>
          </template>
          <template v-else>
            <n-button type="primary" size="large" @click="submit">提交</n-button>
            <n-button size="large" quaternary @click="stop">结束</n-button>
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
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NTag } from "naive-ui";
import { api } from "../core/api";
import { loadSpeak, parseShadowReply, type ShadowItem, type SpeakData } from "../core/speak";
import { createSpeakConn, type SpeakConn } from "../core/speakRTC";
import { SoeEval, type SoeResult } from "../core/soe";

const route = useRoute();
const router = useRouter();
const data = ref<SpeakData | null>(null);
const packIdx = ref(0);
const itemIdx = ref(0);
const day = computed(() => Number(route.query.day ?? 0));
const item = computed(() => {
  const packs = data.value?.packs ?? [];
  const p = packs[packIdx.value];
  if (!p) return null;
  const it = (data.value?.shadow ?? []).find((s) => s.id === p.ids[itemIdx.value % p.ids.length]);
  return it ?? null;
});

const conn = ref<SpeakConn | null>(null);
const soe = ref<SoeEval | null>(null);
const engine = ref<"ai" | "soe">("ai");
const status = ref("");
const lastReply = ref("");
const result = ref<ReturnType<typeof parseShadowReply>>(null);
const scores = ref<number[]>([]);
const ttsEl = ref<HTMLAudioElement | null>(null);

const orderedItems = computed<ShadowItem[]>(() => {
  const packs = data.value?.packs ?? [];
  const p = packs[packIdx.value];
  if (!p || !data.value) return [];
  return p.ids.map((id) => data.value!.shadow.find((s) => s.id === id)!).filter(Boolean);
});

const dueCount = ref(0);
onMounted(async () => {
  data.value = await loadSpeak();
  try {
    const r = await api<{ items: unknown[] }>("/english/speak/review/due");
    dueCount.value = (r.items ?? []).length;
  } catch { /* 离线忽略 */ }
});

function start(): void {
  if (!item.value) return;
  result.value = null;
  scores.value = [];
  engine.value = "ai";
  void run();
}
async function run(): Promise<void> {
  const boot = await api<{ instructions: string; mode: string }>("/english/speak/boot", {
    method: "POST",
    body: JSON.stringify({ mode: "shadow", day: day.value, target: item.value?.en ?? "" }),
  });
  // 取模型音色：sdp 接口回 voice；这里先连接
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
  // sdp 由 createSpeakConn 内部请求，这里只需要等待 ready（由 onStatus 反馈）
}
function submit(): void {
  // 手动判停：commit 缓冲 + 请求模型回评 JSON（session.update 已下发评测指令）
  status.value = "AI 评分中…";
  conn.value?.commitAndRespond();
}

/** 腾讯云精准评测（口语评测新版）：边说边评，提交后拿逐词准确度 */
async function startSoe(): Promise<void> {
  if (!item.value) return;
  result.value = null;
  scores.value = [];
  engine.value = "soe";
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
  } catch {
    soe.value = null;
    engine.value = "ai";
  }
}
function submitSoe(): void {
  soe.value?.submit();
}
function stopSoe(): void {
  void finish();
  soe.value?.stop();
  soe.value = null;
  void router.push("/english/speak");
}

function stop(): void {
  void finish();
  conn.value?.close();
  conn.value = null;
  void router.push("/english/speak");
}
async function finish(): Promise<void> {
  if (!scores.value.length) return;
  const avg = Math.round(scores.value.reduce((a, b) => a + b, 0) / scores.value.length);
  try {
    await api("/english/speak/log", {
      method: "POST",
      body: JSON.stringify({
        mode: "shadow", ref: item.value?.pack ?? "", day: day.value,
        turns: scores.value.length, score: avg,
        issues: result.value?.tips ?? [], transcript: [],
      }),
    });
  } catch { /* 离线不阻塞 */ }
}
function next(): void {
  const packs = data.value?.packs ?? [];
  const p = packs[packIdx.value];
  const len = Math.max(p?.ids.length ?? 1, 1);
  if (itemIdx.value + 1 < len) itemIdx.value++;
  else { itemIdx.value = 0; packIdx.value = (packIdx.value + 1) % Math.max(packs.length, 1); }
  result.value = null;
}
async function tts(): Promise<void> {
  try {
    const r = await api<{ b64: string; mime: string }>("/english/speak/tts", {
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
function back(): void {
  void router.push("/english/speak");
}
</script>

<style scoped>
.page { width: 100%; }
.duebar { display: flex; align-items: center; gap: 10px; justify-content: space-between; padding: 10px 14px; margin-bottom: 12px; color: var(--c-text-2); font-size: var(--fs-sub); background: var(--c-primary-soft); }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.daychip { font-size: var(--fs-sub); color: var(--c-primary); font-weight: 600; }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.empty { padding: 40px; text-align: center; color: var(--c-text-2); }
.sent { padding: 18px; margin-bottom: 12px; }
.en { font-size: var(--fs-title); color: var(--c-text); font-weight: 600; }
.cn { color: var(--c-text-2); margin-top: 6px; }
.tip { color: var(--c-accent); margin-top: 8px; font-size: var(--fs-sub); }
.sent-actions { margin-top: 12px; display: flex; gap: 8px; }
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
.w { display: inline-block; margin: 0 6px 6px 0; padding: 3px 8px; border-radius: var(--r-sm); background: var(--c-bg-mint); color: var(--c-primary); font-weight: 600; }
.w.bad { background: var(--c-danger-soft); color: var(--c-danger); text-decoration: line-through; }
.tips { color: var(--c-text-2); font-size: var(--fs-sub); margin: 8px 0 0; padding-left: 18px; }
.res-actions { margin-top: 12px; display: flex; gap: 8px; }
.chip { background: var(--c-bg-mint); border: 1px solid var(--c-border); border-radius: 999px; padding: 5px 12px; cursor: pointer; color: var(--c-text-2); }
</style>
