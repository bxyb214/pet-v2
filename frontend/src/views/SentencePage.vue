<template>
  <main class="page">
    <BackButton to="/english/speak" label="返回口语" />
    <h1>
      造句练习
      <span v-if="planDay" class="daychip">第 {{ planDay.day }} 天 · {{ sourceRangeText(planDay) }}</span>
    </h1>
    <p class="sub">
      看中文，用英文说出来。按住「参考答案」可以边看边听，AI 会给出建议和一句更好的示范句，跟读示范句还能评分存档。
      <template v-if="hasPlan">今天目标 10 分钟。</template>
    </p>

    <div v-if="banner" class="banner" :class="banner.tone">{{ banner.text }}</div>

    <div v-if="hasPlan" class="card targetbar" :class="{ over: overGoal }">
      <span class="target-label">今日造句</span>
      <b class="target-time">{{ mmss(elapsed) }}</b>
      <span class="target-goal">/ 10:00</span>
      <span class="target-hint">
        {{ overGoal ? "已到 10 分钟，造完这句就休息吧" : `剩余 ${mmss(Math.max(0, 600 - elapsed))}` }}
      </span>
    </div>

    <LoadingBlock v-if="loading" />
    <template v-else>
      <div class="filters">
        <template v-if="hasPlan">
          <span class="topics-label">今日话题</span>
          <button
            v-for="s in planScenes" :key="s.id" type="button"
            class="gbtn" :class="{ on: sceneId === s.id }"
            @click="pickScene(s.id)"
          >{{ s.cn }}<i>{{ s.title }}</i></button>
          <span v-if="!planScenes.length" class="muted">今天没有可用的造句话题。</span>
        </template>
        <template v-else>
          <button
            v-for="f in partFilters" :key="f.id" type="button"
            class="gbtn" :class="{ on: part === f.id }" @click="pickPart(f.id)"
          >{{ f.name }}</button>
          <n-select
            v-model:value="sceneId" class="scene-select" :options="sceneOptions"
            placeholder="选择场景" filterable @update:value="pickScene"
          />
        </template>
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
          <div class="hint">点「开始说」，用英文把这句意思说出来；说完点小绿下面的「提交」。</div>

          <div class="saybar">
            <PaidActionButton v-if="!recording" :status="aiStatus" :disabled="checking" @click="startSpeak">
              {{ mine ? "🎤 再说一次" : "🎤 开始说" }}
            </PaidActionButton>
            <span class="status">{{ status }}</span>
            <n-popover
              v-model:show="answerPeek" trigger="manual" placement="top-end"
              :disabled="!prompt || recording"
            >
              <template #trigger>
                <button
                  type="button" class="peek-btn" :class="{ on: answerPeek }"
                  :disabled="!prompt || recording"
                  title="按住显示参考答案并朗读，松手停止"
                  @pointerdown.prevent="startPeek"
                  @pointerup="endPeek"
                  @pointercancel="endPeek"
                  @lostpointercapture="endPeek"
                  @keydown.space.prevent="startPeek"
                  @keyup.space.prevent="endPeek"
                  @keydown.enter.prevent="startPeek"
                  @keyup.enter.prevent="endPeek"
                  @blur="endPeek"
                  @contextmenu.prevent
                >参考答案</button>
              </template>
              <div class="peek">
                <b>参考答案</b>
                <span class="ans">{{ prompt?.answer }}</span>
                <i>松手收起并停止朗读</i>
              </div>
            </n-popover>
          </div>

          <!-- AI 点评：中文建议 + PET 优秀示范句；只对示范句提供跟读评分与存档 -->
          <div v-if="fb" class="fb" :class="{ good: fb.ok }">
            <div class="fb-head">
              <div class="fb-title">{{ fb.ok ? "意思说到了！" : "再改一点就更好了" }}</div>
              <n-button v-if="ttsReady" size="tiny" secondary @click="toggleAdvice">
                {{ adviceBusy ? "❚❚ 停止朗读" : "🔊 朗读建议" }}
              </n-button>
            </div>
            <div v-if="mine" class="heard">AI 听到的是：{{ mine }}</div>
            <div class="fb-comment">{{ fb.comment }}</div>
            <div v-if="fb.improved" class="model">
              <div class="model-label">AI 示范句 <span>PET 优秀水平以上</span></div>
              <SpeakImproveCard
                :child-said="mine"
                :improved-en="fb.improved"
                :improved-cn="''"
                compact
                local-only
                :eval="false"
              />
              <SpeakEvalBlock
                :ref-text="fb.improved"
                :ai-status="aiStatus"
                local-advice
                @starting="silencePlayback"
                @scored="onModelScored"
              />
            </div>
          </div>
        </div>
      </div>

      <section v-if="myTakes.length" class="card takes-panel">
        <div class="takes-h">
          <b>我的本地录音</b>
          <span>保存在这台设备 · 共 {{ myTakes.length }} 条 · 跟读 AI 示范句后存档 · 换设备不同步</span>
        </div>
        <div class="take-list">
          <div v-for="t in myTakes" :key="t.id" class="take">
            <button
              type="button" class="tk-play"
              :title="playingId === t.id ? '停止播放' : '播放我的录音'"
              @click="playTake(t)"
            >{{ playingId === t.id ? "❚❚" : "▶" }}</button>
            <b class="tk-score" :class="{ best: bestTakeIds.has(t.id) }">
              {{ t.score > 0 ? `${t.score} 分` : "未评分" }}
            </b>
            <i v-if="bestTakeIds.has(t.id)" class="tk-tag">最高分</i>
            <span class="tk-time">{{ fmtTakeTime(t.at) }}</span>
            <span class="tk-label">{{ takeLabel(t.promptKey) }}</span>
            <span class="tk-text">{{ t.transcript }}</span>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { NButton, NPopover, NSelect } from "naive-ui";
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";
import {
  loadSpeak, planDayScenes, resolvePlanDay, sourceRangeText, splitSpeakPlan,
  type DayCheck, type PlanDayView, type Scene, type SpeakData,
} from "../core/speak";
import { startMakeRecording, type MakeRec } from "../core/makeRecorder";
import { useSpeakTime } from "../core/speakTime";
import { addTake, newTakeId, takeStorageKey } from "../core/takes";
import { useUserTakeList, type TakeView } from "../core/takeList";
import {
  budgetBanner, loadAiStatus, paidBlocked, paidLockText, type AiStatus,
} from "../core/aiStatus";
import { say, stopAudioUrl, stopSpeaking } from "../core/say";
import { adviceBusy, readAdvice, stopAdvice } from "../core/adviceSpeech";
import { loadTtsConfig } from "../core/ttsConfig";
import { playLocalTts } from "../core/tts";
import { devMode } from "../core/devMode";
import BackButton from "../components/BackButton.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import PaidActionButton from "../components/PaidActionButton.vue";
import SpeakEvalBlock from "../components/SpeakEvalBlock.vue";
import SpeakImproveCard from "../components/SpeakImproveCard.vue";

const route = useRoute();
const data = ref<SpeakData | null>(null);
const loading = ref(true);
const part = ref(0);
const sceneId = ref("");
const pi = ref(0);
const mine = ref("");
const checking = ref(false);
const answerPeek = ref(false);
const fb = ref<{ ok: boolean; comment: string; improved: string } | null>(null);
const status = ref("");
const listening = ref(false);
const recording = ref(false);
const aiStatus = ref<AiStatus | null>(null);
const banner = computed(() => budgetBanner(aiStatus.value));
const locked = computed(() => paidBlocked(aiStatus.value));
const lockText = computed(() => paidLockText(aiStatus.value));
let rec: MakeRec | null = null;
let finished = false;
let holdPointer: number | null = null;

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
const planScenes = computed<Scene[]>(() => planDayScenes(data.value, planDay.value));
const scene = computed(() => scenes.value.find((s) => s.id === sceneId.value) ?? null);
const prompts = computed(() => scene.value?.make ?? []);
const prompt = computed(() => prompts.value[pi.value] ?? null);

// ---- 我的录音：只有跟读 AI 示范句并评分后才进 IndexedDB 存档
// （最近 3 次 + 最高分）
const auth = useAuthStore();
const ttsReady = ref(false);

const promptKey = computed(() => (prompt.value ? `${sceneId.value}:${prompt.value.id}` : ""));
const takeKey = computed(() => takeStorageKey(auth.username, promptKey.value));
const username = computed(() => auth.username);
const { takes: myTakes, playingId, togglePlay, stopPlay: stopTakePlay, refresh: refreshMyTakes } = useUserTakeList(username);

/** 跨题目列表里按题目分别标出最高分，避免拿别的题分数比较。 */
const bestTakeIds = computed(() => {
  const best = new Map<string, TakeView>();
  for (const t of myTakes.value) {
    if (t.score <= 0) continue;
    const cur = best.get(t.promptKey);
    if (!cur || t.score > cur.score || (t.score === cur.score && t.at > cur.at)) {
      best.set(t.promptKey, t);
    }
  }
  return new Set([...best.values()].map((t) => t.id));
});

/** 开始录音/评分或播放另一段声音前：先停掉所有回放，避免麦克风收到叠音 */
function silencePlayback(): void {
  stopTakePlay();
  stopAdvice();
  stopAudioUrl();
  stopSpeaking();
}

/** 播放一条本地录音：先停掉参考答案/建议，避免叠音。 */
function playTake(t: TakeView): void {
  if (playingId.value === t.id) {
    togglePlay(t);
    return;
  }
  silencePlayback();
  togglePlay(t);
}

// ---- 参考答案：按住显示 + 朗读，松手收起并停止
function startPeek(e: Event): void {
  const p = prompt.value;
  if (!p || recording.value) return;
  if (typeof PointerEvent !== "undefined" && e instanceof PointerEvent) {
    holdPointer = e.pointerId;
    try { (e.currentTarget as HTMLElement | null)?.setPointerCapture?.(e.pointerId); } catch { /* noop */ }
  }
  if (answerPeek.value) return;
  answerPeek.value = true;
  silencePlayback();
  say(p.answer);
}

function endPeek(e?: Event): void {
  const isPointer = typeof PointerEvent !== "undefined" && e instanceof PointerEvent;
  if (isPointer && holdPointer !== null && e.pointerId !== holdPointer) return;
  if (isPointer && holdPointer !== null) {
    try { (e.currentTarget as HTMLElement | null)?.releasePointerCapture?.(holdPointer); } catch { /* noop */ }
  }
  closePeek();
}

function closePeek(): void {
  const wasOpen = answerPeek.value || holdPointer !== null;
  answerPeek.value = false;
  holdPointer = null;
  if (wasOpen) stopSpeaking();
}

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
  // 预热本地发音配置：参考答案与 AI 反馈都只用本地 TTS，按钮按配置显隐
  ttsReady.value = (await loadTtsConfig()).enabled;
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
      planDay.value = resolvePlanDay(planDays, checks, Number(route.query.day ?? 0));
      const sid = planDayScenes(data.value, planDay.value)[0]?.id;
      if (sid) sceneId.value = sid;
    }
  } catch { /* 离线时不影响造句 */ }
  if (!hasPlan.value && !sceneId.value && scenes.value.length) {
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
  stopTakePlay();
  stopAdvice();
  closePeek();
});

function pickPart(id: number): void {
  part.value = id;
  const first = scenes.value.find((s) => id === 0 || s.part === id);
  if (first) pickScene(first.id);
}
function pickScene(id: string): void {
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
  fb.value = null;
  status.value = "";
  listening.value = false;
  recording.value = false;
  finished = false;
  closePeek();
  stopAdvice();
  rec?.close();
  rec = null;
}

async function startSpeak(): Promise<void> {
  if (!prompt.value || rec) return;
  if (locked.value) {
    status.value = lockText.value;
    return;
  }
  closePeek();
  silencePlayback();
  finished = false;
  mine.value = "";
  fb.value = null;
  status.value = "开启麦克风…";
  try {
    rec = await startMakeRecording({
      onStatus: (s) => { status.value = s; },
      onError: (msg) => {
        status.value = msg;
        recording.value = false;
        rec = null;
      },
      onSubmit: submitAttempt,
      onCancel: cancelAttempt,
    });
    recording.value = true;
    status.value = "可以开始说，说完点小绿下面的「提交」";
  } catch (e) {
    status.value = "语音不可用：" + (e as Error).message + "（请检查麦克风后重试）";
    recording.value = false;
    rec = null;
  }
}

/** 数字人「提交」：没开口时提醒继续读，有声音才结束录音去转写 */
function submitAttempt(): void {
  if (!rec || listening.value || finished) return;
  if (rec.speechSec() <= 0) {
    status.value = "还没听到声音，对着麦克风说一遍再点「提交」";
    return;
  }
  void finishSpeak();
}

/** 数字人「取消」：放弃这次录音，不评分 */
function cancelAttempt(): void {
  rec?.close();
  rec = null;
  recording.value = false;
  fb.value = null;
  status.value = "已取消本次造句，点「开始说」重新开始";
}

/** 提交：结束录音 → 上传 ASR 转写 → 文字点评。录音 Blob 用完即弃（只有跟读示范句才存档）。 */
async function finishSpeak(): Promise<void> {
  const r = rec;
  if (!r || listening.value) return;
  listening.value = true;
  status.value = "正在转写…";
  try {
    const blob = await r.stop();
    rec = null;
    recording.value = false;
    const said = await transcribe(blob);
    if (!said.trim()) {
      listening.value = false;
      status.value = "没有听清，请再说一次。";
      return;
    }
    mine.value = said.trim();
    status.value = "已转写，正在请 AI 点评…";
    await check();
  } catch (e) {
    status.value = (e as Error).message || "转写失败，请重试";
  } finally {
    listening.value = false;
  }
}

/** 录音上传 → ASR 转写英文（multipart：api() 走 JSON，这里裸 fetch 带鉴权头） */
async function transcribe(blob: Blob | null): Promise<string> {
  // 开发环境没有真实录音：空表单直接拿后端 mock 转写，链路可点通
  if (!blob || blob.size === 0) {
    if (devMode.value) {
      const r = await api<{ text: string }>("/speak/transcribe", { method: "POST" });
      return r.text;
    }
    return "";
  }
  const token = localStorage.getItem("pet_access") ?? "";
  const form = new FormData();
  const ext = blob.type.includes("mp4") ? "m4a" : blob.type.includes("wav") ? "wav" : "webm";
  form.append("file", blob, `take.${ext}`);
  const res = await fetch("/api/v1/speak/transcribe", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail ?? `转写失败 (${res.status})`);
  return String(body?.text ?? "");
}

function stopSpeak(): void {
  rec?.close();
  rec = null;
  recording.value = false;
  status.value = "";
}

/** 页面关闭时停掉麦克风与回放（录音本就不持久化，无需补报会话）。 */
function onPageHide(): void {
  rec?.close();
  rec = null;
  recording.value = false;
  stopTakePlay();
}

async function check(): Promise<void> {
  if (!prompt.value || !mine.value.trim()) return;
  void logMake();
  if (locked.value) {
    fb.value = { ok: false, comment: lockText.value, improved: "" };
    status.value = "";
    return;
  }
  checking.value = true;
  fb.value = null;
  try {
    const res = await api<{ ok: boolean; comment: string; improved: string }>("/speak/check", {
      method: "POST",
      body: JSON.stringify({
        pattern: prompt.value.answer,
        prompt_cn: prompt.value.prompt_cn,
        sentence: mine.value.trim(),
      }),
    });
    fb.value = res;
    status.value = "";
    // 建议和示范句都用本地 TTS 读（不回落浏览器）；按钮可随时停止/重读
    readFeedback(res);
  } catch (e) {
    fb.value = { ok: false, comment: "AI 暂时不可用：" + (e as Error).message, improved: "" };
  }
  checking.value = false;
}

/** 跟读 AI 示范句评分后：这次录音 + 分数进「我的录音」（最近 3 次 + 最高分） */
function onModelScored(v: { score: number; blob: Blob | null }): void {
  const key = takeKey.value;
  const promptId = promptKey.value;
  const transcript = fb.value?.improved ?? "";
  if (!key || !promptId || !transcript || !v.blob || v.blob.size === 0) return;
  void saveTake(key, promptId, Math.round(v.score), transcript, v.blob);
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

/** 本地中文读建议 → 读完再本地读 AI 示范句；全程不回落浏览器 */
function readFeedback(res: { comment: string; improved: string }): void {
  void readAdvice([res.comment], {
    fallback: false,
    onDone: () => {
      if (fb.value === res && res.improved) void playLocalTts(res.improved);
    },
  });
}

/** 手动停止/重读当前 AI 建议（含示范句） */
function toggleAdvice(): void {
  const cur = fb.value;
  const text = cur?.comment?.trim();
  if (!cur || !text) return;
  if (adviceBusy.value) {
    stopAdvice();
    return;
  }
  readFeedback(cur);
}

function mmss(s: number): string {  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}

// ---- 我的录音（评分后落库）

/** 跟读评分后落库：题目 + 时间 + 分数 + AI 示范句 + 录音 WAV（key/promptId 即时捕获，避免中途切题写错） */
async function saveTake(
  key: string,
  promptId: string,
  score: number,
  transcript: string,
  blob: Blob,
): Promise<void> {
  if (!key || !promptId || !transcript || !blob || blob.size === 0) return;
  const at = Date.now();
  try {
    await addTake({
      id: newTakeId(at),
      key,
      promptKey: promptId,
      at,
      score,
      transcript,
      mime: blob.type || "audio/wav",
      blob,
    });
    await refreshMyTakes();
  } catch { /* 存不进（隐私模式/配额）不影响练习 */ }
}

function takeLabel(promptKey: string): string {
  const i = promptKey.indexOf(":");
  const sid = i >= 0 ? promptKey.slice(0, i) : promptKey;
  const pid = i >= 0 ? promptKey.slice(i + 1) : "";
  const s = scenes.value.find((x) => x.id === sid);
  if (!s) return "";
  const idx = (s.make ?? []).findIndex((m) => m.id === pid);
  return idx >= 0 ? `${s.cn} · 第 ${idx + 1} 题` : s.cn;
}

/** 今天只显示时间，跨天补上日期，方便在「我的本地录音」里找。 */
function fmtTakeTime(at: number): string {
  const d = new Date(at);
  const hm = hhmm(at);
  return d.toDateString() === new Date().toDateString()
    ? hm
    : `${d.getMonth() + 1}-${d.getDate()} ${hm}`;
}

function hhmm(at: number): string {
  const d = new Date(at);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.daychip {
  margin-left: 8px; padding: 2px 10px; border-radius: 999px;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  font-size: 12.5px; font-weight: 700; vertical-align: middle;
}
.topics-label { color: var(--c-text-2); font-size: 12.5px; font-weight: 700; }
.muted { color: var(--c-text-2); font-size: var(--fs-sub); }
.gbtn i { margin-left: 6px; font-style: normal; font-size: 11.5px; opacity: 0.72; }
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
.status { flex: 1 1 180px; min-width: 0; color: var(--c-text-2); font-size: var(--fs-sub); }
.peek-btn {
  margin-left: auto; flex: none;
  min-height: 34px; padding: 6px 14px; border-radius: var(--r-btn);
  border: 1px solid var(--c-line); background: var(--c-surface); color: var(--c-text);
  font: inherit; font-size: var(--fs-sub); font-weight: 700; cursor: pointer;
  user-select: none; -webkit-touch-callout: none; touch-action: none;
}
.peek-btn:hover, .peek-btn.on { border-color: var(--c-primary); color: var(--c-primary-strong); background: var(--c-primary-soft); }
.peek-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.peek { display: flex; flex-direction: column; gap: 4px; max-width: min(340px, 80vw); }
.peek b { font-size: 12px; color: var(--c-text-2); }
.peek .ans { font-weight: 700; color: var(--c-text); line-height: 1.5; }
.peek i { font-style: normal; font-size: 11.5px; color: var(--c-text-3); }
.fb { margin-top: 14px; padding: 12px; border-radius: var(--r-btn); background: #fef3c7; }
.fb.good { background: var(--c-primary-soft); }
.fb-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 4px; }
.fb-title { flex: 1 1 auto; font-weight: 800; color: var(--c-text); }
.heard { color: var(--c-text-2); font-size: var(--fs-sub); margin-bottom: 6px; }
.fb-comment { color: var(--c-text); font-size: var(--fs-sub); line-height: 1.6; }
.model { margin-top: 10px; }
.model-label { font-size: 12.5px; font-weight: 700; color: var(--c-text); margin-bottom: 6px; }
.model-label span { margin-left: 6px; font-weight: 600; color: var(--c-primary-strong); }
.fb .imp-card { max-width: 100%; margin-top: 0; background: #fff; }
.takes-panel { margin-top: 16px; padding: 16px; }
.takes-h { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.takes-h b { color: var(--c-text); font-size: 14px; }
.takes-h span { color: var(--c-text-2); font-size: 12px; }
.take-list { max-height: 360px; overflow: auto; margin-top: 8px; padding-right: 2px; }
.take { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 8px; padding: 8px 10px; border-radius: var(--r-btn); background: var(--c-mint-bg); }
.take:first-child { margin-top: 0; }
.tk-play { width: 30px; height: 30px; border-radius: 999px; border: 1px solid var(--c-line, #d1d5db); background: var(--c-surface); color: var(--c-primary); font-size: 12px; cursor: pointer; }
.tk-play:hover { border-color: var(--c-primary); }
.tk-score { font-size: 13px; color: var(--c-text); font-variant-numeric: tabular-nums; }
.tk-score.best { color: var(--c-primary); }
.tk-tag { font-style: normal; font-size: 11px; font-weight: 700; color: var(--c-primary); background: var(--c-primary-soft); border-radius: 999px; padding: 2px 8px; }
.tk-time { font-size: 12px; color: var(--c-text-3); font-variant-numeric: tabular-nums; }
.tk-label { font-size: 11.5px; color: var(--c-text-2); background: var(--c-surface); border: 1px solid var(--c-line); border-radius: 999px; padding: 1px 8px; }
.tk-text { flex: 1; min-width: 160px; font-size: var(--fs-sub); color: var(--c-text); }
@media (max-width: 560px) {
  .status { flex-basis: 100%; order: 3; }
  .tk-text { flex-basis: 100%; min-width: 0; }
}
</style>
