<template>
  <main class="page">
    <BackButton />
    <h1>造句练习</h1>
    <p class="sub">
      看中文，用英文说出来。说完可以看标准答案，AI 会告诉你怎么说得更好。
      <template v-if="hasPlan">今天目标 10 分钟。</template>
    </p>

    <div v-if="banner" class="banner" :class="banner.tone">{{ banner.text }}</div>
    <PaidAiNotice :status="aiStatus" />

    <div v-if="hasPlan" class="card targetbar" :class="{ over: overGoal }">
      <span class="target-label">今日造句</span>
      <b class="target-time">{{ mmss(elapsed) }}</b>
      <span class="target-goal">/ 10:00</span>
      <span class="target-hint">
        {{ overGoal ? "已到 10 分钟，造完这句就休息吧" : `剩余 ${mmss(Math.max(0, 600 - elapsed))}` }}
      </span>
    </div>

    <div v-if="loading" class="card empty">加载中…</div>
    <template v-else>
      <div class="filters">
        <button
          v-for="f in partFilters" :key="f.id" type="button"
          class="gbtn" :class="{ on: part === f.id }" @click="pickPart(f.id)"
        >{{ f.name }}</button>
        <n-select
          v-model:value="sceneId" class="scene-select" :options="sceneOptions"
          placeholder="选择场景" filterable @update:value="pickScene"
        />
      </div>

      <div v-if="scene" class="card panel">
        <div class="gname">{{ scene.title }} <span class="gcn">{{ scene.cn }}</span></div>

        <div class="prompts">
          <button
            v-for="(m, i) in prompts" :key="m.id" type="button"
            class="prompt-card" :class="{ on: i === pi }" @click="pickPrompt(i)"
          >
            <span class="pno">第 {{ i + 1 }} 题</span>
            <span class="pcn">{{ m.prompt_cn }}</span>
          </button>
        </div>

        <div v-if="prompt" class="practice">
          <div class="prompt-big">{{ prompt.prompt_cn }}</div>
          <div class="hint">点「开始说」，用英文把这句意思说出来；说完点「说完了」。</div>

          <div class="saybar">
            <template v-if="!conn">
              <PaidActionButton :status="aiStatus" :disabled="checking" @click="startSpeak">
                {{ mine ? "🎤 再说一次" : "🎤 开始说" }}
              </PaidActionButton>
              <n-button v-if="locked" size="large" secondary @click="play(prompt?.answer ?? '')">
                听标准答案（浏览器朗读）
              </n-button>
            </template>
            <template v-else>
              <n-button type="primary" size="large" :loading="listening" @click="finishSpeak">
                {{ listening ? "AI 正在听…" : "说完了，提交" }}
              </n-button>
              <n-button size="large" quaternary @click="stopSpeak">取消</n-button>
            </template>
            <span class="status">{{ status }}</span>
          </div>

          <div class="actions">
            <n-button v-if="heard" secondary @click="play(heard)">听我说的</n-button>
            <n-button quaternary @click="answerShown = !answerShown">
              {{ answerShown ? "收起标准答案" : "看标准答案" }}
            </n-button>
          </div>

          <div v-if="answerShown" class="answer">
            <n-tag size="small" type="info" :bordered="false">标准答案</n-tag>
            <span class="ans">{{ prompt.answer }}</span>
            <n-button size="tiny" secondary @click="play(prompt.answer)">听示范</n-button>
          </div>

          <div v-if="fb" class="fb" :class="{ good: fb.ok }">
            <div class="fb-title">{{ fb.ok ? "意思说到了！" : "再改一点就更好了" }}</div>
            <div v-if="heard" class="heard">AI 听到的是：{{ heard }}</div>
            <div class="fb-comment">{{ fb.comment }}</div>
            <div v-if="fb.improved" class="fb-better">
              <n-tag size="small" type="success" :bordered="false">更好的说法</n-tag>
              <span class="better">{{ fb.improved }}</span>
              <n-button size="tiny" secondary @click="play(fb.improved)">听示范</n-button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { NButton, NSelect, NTag } from "naive-ui";
import { api, apiBeacon } from "../core/api";
import {
  loadSpeak, parseShadowReply, planDayDone, splitSpeakPlan,
  type DayCheck, type PlanDayView, type Scene, type SpeakData,
} from "../core/speak";
import { createSpeakConn, type SpeakConn } from "../core/speakRTC";
import { useSpeakTime } from "../core/speakTime";
import {
  budgetBanner, loadAiStatus, paidBlocked, paidLockText, type AiStatus,
} from "../core/aiStatus";
import { say, playAudioUrl } from "../core/say";
import BackButton from "../components/BackButton.vue";
import PaidActionButton from "../components/PaidActionButton.vue";
import PaidAiNotice from "../components/PaidAiNotice.vue";

const route = useRoute();
const data = ref<SpeakData | null>(null);
const loading = ref(true);
const part = ref(0);
const sceneId = ref("");
const pi = ref(0);
const mine = ref("");
const heard = ref("");
const checking = ref(false);
const answerShown = ref(false);
const fb = ref<{ ok: boolean; comment: string; improved: string } | null>(null);
const status = ref("");
const listening = ref(false);
const conn = ref<SpeakConn | null>(null);
const aiStatus = ref<AiStatus | null>(null);
const banner = computed(() => budgetBanner(aiStatus.value));
const locked = computed(() => paidBlocked(aiStatus.value));
const lockText = computed(() => paidLockText(aiStatus.value));
let connLocal: SpeakConn | null = null;
let finished = false;

const activeSec = ref(0);
const planLength = ref(0);
const hasPlan = computed(() => planLength.value > 0);
const clock = useSpeakTime("make", () => activeSec.value, () => hasPlan.value);
const elapsed = clock.total;
const overGoal = computed(() => elapsed.value >= 600);
const planDay = ref<PlanDayView | null>(null);
let timer = 0;
let makeLogged = false;

const scenes = computed<Scene[]>(() => data.value?.scenes ?? []);
const scene = computed(() => scenes.value.find((s) => s.id === sceneId.value) ?? null);
const prompts = computed(() => scene.value?.make ?? []);
const prompt = computed(() => prompts.value[pi.value] ?? null);
const partFilters = [
  { id: 0, name: "全部" },
  { id: 1, name: "Part 1" },
  { id: 2, name: "Part 2" },
  { id: 3, name: "Part 3–4" },
];
const sceneOptions = computed(() =>
  scenes.value
    .filter((s) => part.value === 0 || s.part === part.value)
    .map((s) => ({ label: `${s.cn} · ${s.title}`, value: s.id }))
);

onMounted(async () => {
  window.addEventListener("pagehide", onPageHide);
  data.value = await loadSpeak();
  loading.value = false;
  aiStatus.value = await loadAiStatus();
  try {
    const [p, d] = await Promise.all([
      api<{ length: number }>("/speak/plan"),
      api<{ days: DayCheck[] }>("/speak/days"),
    ]);
    planLength.value = p.length ?? 0;
    if (hasPlan.value) {
      const planDays = splitSpeakPlan(data.value, planLength.value);
      const checks: Record<number, DayCheck> = {};
      for (const c of d.days ?? []) checks[c.day] = c;
      const qDay = Number(route.query.day ?? 0);
      planDay.value = qDay
        ? planDays[qDay - 1] ?? null
        : planDays.find((x) => !planDayDone(x, checks)) ?? planDays[0] ?? null;
      const sid = planDay.value?.sceneIds[0];
      if (sid && scenes.value.some((s) => s.id === sid)) {
        sceneId.value = sid;
        part.value = scenes.value.find((s) => s.id === sid)?.part ?? 0;
      }
    }
  } catch { /* 离线时不影响造句 */ }
  if (!sceneId.value && scenes.value.length) {
    sceneId.value = scenes.value[0].id;
    part.value = scenes.value[0].part;
  }
  timer = window.setInterval(() => {
    if (hasPlan.value && document.visibilityState === "visible") activeSec.value += 1;
  }, 1000);
});
onBeforeUnmount(() => {
  window.removeEventListener("pagehide", onPageHide);
  if (timer) clearInterval(timer);
  stopSpeak();
});

function pickPart(id: number): void {
  part.value = id;
  const first = scenes.value.find((s) => id === 0 || s.part === id);
  if (first) pickScene(first.id);
}
function pickScene(id: string): void {
  // 跨场景不复用语音连接：先按本次连接上报并关闭，下一场景重新握手。
  if (id !== sceneId.value) closeConn();
  sceneId.value = id;
  pi.value = 0;
  resetAttempt();
}
function pickPrompt(i: number): void {
  pi.value = i;
  resetAttempt();
}
function resetAttempt(): void {
  mine.value = "";
  heard.value = "";
  answerShown.value = false;
  fb.value = null;
  status.value = "";
  if (listening.value) closeConn();
  else conn.value = null;
}

function voiceInstructions(p: { prompt_cn: string }): string {
  return [
    "You are an English transcription assistant for a PET speaking app.",
    "The student will say ONE English sentence to express this Chinese idea:",
    `「${p.prompt_cn}」`,
    "Do not chat and never ask questions. Transcribe exactly what the student says, even if it is wrong.",
    'Reply with ONE compact JSON object: {"transcript":"what you heard","score":0-100,',
    '"words":[],"tips":["中文建议，最多 2 条"],"say":"one short encouragement"}.',
    "If you hear no speech, use transcript \"\" and ask the student to try again in Chinese.",
    "Output JSON only.",
  ].join("\n");
}

async function startSpeak(): Promise<void> {
  if (!prompt.value || conn.value) return;
  if (locked.value) {
    status.value = lockText.value;
    return;
  }
  finished = false;
  heard.value = "";
  fb.value = null;
  answerShown.value = false;
  // P1-5：同一场景复用连接，只更新提示词，不再重复 SDP 握手
  if (connLocal && !connLocal.closed) {
    connLocal.updateInstructions?.(voiceInstructions(prompt.value));
    conn.value = connLocal;
    status.value = "可以开始说，说完点「说完了」";
    return;
  }
  status.value = "连接语音服务…";
  try {
    const c = await createSpeakConn({
      mode: "shadow",
      turnDetection: "manual",
      instructions: voiceInstructions(prompt.value),
      onStatus: (s) => { status.value = s; },
      onUserTranscript: (t) => { if (t) heard.value = t; },
      onReply: (t) => {
        const r = parseShadowReply(t);
        if (r?.transcript) heard.value = r.transcript;
        if (!finished) void finishWithTranscript();
      },
      onError: (msg) => {
        status.value = msg;
        closeConn();
      },
    });
    connLocal = c;
    conn.value = c;
  } catch (e) {
    status.value = "语音不可用：" + (e as Error).message + "（请检查麦克风后重试）";
    closeConn();
  }
}

function finishSpeak(): void {
  if (!connLocal) return;
  listening.value = true;
  status.value = "AI 正在听…";
  connLocal.commitAndRespond();
  window.setTimeout(() => {
    if (!listening.value) return;
    if (heard.value.trim()) {
      void finishWithTranscript();
      return;
    }
    listening.value = false;
    status.value = "没有听清，请再说一次。";
    closeConn();
  }, 8000);
}

async function finishWithTranscript(): Promise<void> {
  finished = true;
  listening.value = false;
  const said = heard.value.trim();
  conn.value = null; // 释放界面按钮，但保留 connLocal 供下一句复用
  if (!said) {
    status.value = "没有听清，请再说一次。";
    return;
  }
  mine.value = said;
  status.value = "已转写，正在请 AI 点评…";
  await check();
}

function stopSpeak(): void {
  closeConn();
  status.value = "";
}

/** 关闭连接前按服务端会话补报一次（幂等；页面关闭走 keepalive）。 */
function reportConn(c: SpeakConn | null): void {
  if (!c || !c.sessionId) return;
  apiBeacon("/speak/session_end", {
    seconds: c.elapsedSec(),
    ai_seconds: c.speechSec(),
    mode: "make",
    session_id: c.sessionId,
  });
}

function onPageHide(): void {
  const c = connLocal;
  connLocal = null;
  conn.value = null;
  reportConn(c);
  try { c?.close(); } catch { /* noop */ }
}

function closeConn(): void {
  const c = connLocal;
  connLocal = null;
  conn.value = null;
  listening.value = false;
  reportConn(c);
  try { c?.close(); } catch { /* noop */ }
}

async function check(): Promise<void> {
  if (!prompt.value || !mine.value.trim()) return;
  void logMake();
  if (locked.value) {
    fb.value = { ok: false, comment: lockText.value, improved: "" };
    answerShown.value = true;
    status.value = "";
    return;
  }
  checking.value = true;
  fb.value = null;
  try {
    fb.value = await api<{ ok: boolean; comment: string; improved: string }>("/speak/check", {
      method: "POST",
      body: JSON.stringify({
        pattern: prompt.value.answer,
        prompt_cn: prompt.value.prompt_cn,
        sentence: mine.value.trim(),
      }),
    });
    answerShown.value = true;
    status.value = "";
  } catch (e) {
    fb.value = { ok: false, comment: "AI 暂时不可用：" + (e as Error).message, improved: "" };
  }
  checking.value = false;
}

/** 造句任务打卡：标记当天计划日包含的原始天 make_done（每页只写一次） */
async function logMake(): Promise<void> {
  if (makeLogged || !planDay.value) return;
  makeLogged = true;
  for (const d of planDay.value.sourceDays) {
    try {
      await api("/speak/log", {
        method: "POST",
        body: JSON.stringify({ mode: "make", day: d, turns: 0, score: 0, issues: [], transcript: [] }),
      });
    } catch { /* 离线不阻塞 */ }
  }
}

async function play(text: string): Promise<void> {
  if (!text) return;
  // 未开通或状态未知都不请求付费 TTS，避免产生费用 / 读到服务端缓存。
  if (!aiStatus.value || locked.value) {
    say(text);
    return;
  }
  try {
    const r = await api<{ url: string }>("/speak/tts", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    await playAudioUrl(r.url, text);
  } catch {
    say(text); // 免费降级 / TTS 失败时用浏览器朗读
  }
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
.empty { padding: 28px 16px; text-align: center; color: var(--c-text-2); }
.filters { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
.gbtn { border: 1px solid var(--c-line, #d1d5db); background: var(--c-surface); color: var(--c-text); border-radius: 999px; padding: 6px 12px; font-size: var(--fs-sub); cursor: pointer; }
.gbtn.on { background: var(--c-primary); border-color: var(--c-primary); color: #fff; font-weight: 700; }
.scene-select { min-width: 260px; flex: 1; max-width: 420px; }
.panel { padding: 16px; }
.gname { font-weight: 800; color: var(--c-text); margin-bottom: 10px; }
.gcn { font-weight: 400; color: var(--c-text-2); font-size: var(--fs-sub); margin-left: 6px; }
.prompts { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 8px; margin-bottom: 14px; }
.prompt-card {
  text-align: left; background: var(--c-mint-bg); border: 1px solid transparent;
  border-radius: var(--r-btn); padding: 10px 12px; cursor: pointer;
  display: flex; flex-direction: column; gap: 4px;
}
.prompt-card.on { border-color: var(--c-primary); background: var(--c-primary-soft); }
.pno { color: var(--c-primary); font-size: 12px; font-weight: 700; }
.pcn { color: var(--c-text); font-size: var(--fs-sub); line-height: 1.6; }
.practice { border-top: 1px dashed var(--c-line, #e5e7eb); padding-top: 12px; }
.prompt-big { font-size: 17px; font-weight: 700; color: var(--c-text); line-height: 1.7; }
.hint { color: var(--c-text-2); font-size: var(--fs-sub); margin: 4px 0 10px; }
.saybar { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
.status { color: var(--c-text-2); font-size: var(--fs-sub); }
.actions { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.answer { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 12px; padding: 10px 12px; border-radius: var(--r-btn); background: var(--c-mint-bg); }
.ans { font-weight: 600; color: var(--c-text); }
.fb { margin-top: 14px; padding: 12px; border-radius: var(--r-btn); background: #fef3c7; }
.fb.good { background: var(--c-primary-soft); }
.fb-title { font-weight: 800; margin-bottom: 4px; color: var(--c-text); }
.heard { color: var(--c-text-2); font-size: var(--fs-sub); margin-bottom: 6px; }
.fb-comment { color: var(--c-text); font-size: var(--fs-sub); line-height: 1.6; }
.fb-better { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
.better { font-weight: 700; color: var(--c-text); }
</style>
