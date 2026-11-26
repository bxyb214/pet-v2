<template>
  <main class="page">
    <BackButton to="/english/speak" label="返回口语" />
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

    <LoadingBlock v-if="loading" />
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
          <div class="hint">点「开始说」，用英文把这句意思说出来；说完点小绿下面的「提交」。</div>

          <div class="saybar">
            <PaidActionButton v-if="!rec" :status="aiStatus" :disabled="checking" @click="startSpeak">
              {{ mine ? "🎤 再说一次" : "🎤 开始说" }}
            </PaidActionButton>
            <n-button v-if="locked" size="large" secondary @click="play(prompt?.answer ?? '')">
              听标准答案（浏览器朗读）
            </n-button>
            <span class="status">{{ status }}</span>
          </div>

          <div class="actions">
            <n-button v-if="attemptUrl" secondary @click="playMine">听我说的</n-button>
            <n-button quaternary @click="answerShown = !answerShown">
              {{ answerShown ? "收起标准答案" : "看标准答案" }}
            </n-button>
          </div>

          <div v-if="answerShown" class="answer">
            <n-tag size="small" type="info" :bordered="false">标准答案</n-tag>
            <span class="ans">{{ prompt.answer }}</span>
            <n-button size="tiny" secondary @click="play(prompt.answer)">听示范</n-button>
          </div>

          <!-- AI 点评：文字意见 + 优化句跟读（听示范 / 手动点按钮才评分） -->
          <div v-if="fb" class="fb" :class="{ good: fb.ok }">
            <div class="fb-title">{{ fb.ok ? "意思说到了！" : "再改一点就更好了" }}</div>
            <div v-if="mine" class="heard">AI 听到的是：{{ mine }}</div>
            <div class="fb-comment">{{ fb.comment }}</div>
            <SpeakImproveCard
              v-if="fb.improved && !fb.ok"
              :child-said="mine"
              :improved-en="fb.improved"
              :improved-cn="''"
              show-child
              compact
              @scored="onScored"
            />
          </div>

          <div v-if="takes.length" class="takes">
            <div class="takes-h">
              <b>我的录音</b>
              <span>跟读评分过的保留最近 3 次 + 最高分</span>
            </div>
            <div v-for="t in takes" :key="t.id" class="take">
              <button
                type="button" class="tk-play"
                :title="playingId === t.id ? '停止播放' : '播放我的录音'"
                @click="togglePlay(t)"
              >{{ playingId === t.id ? "❚❚" : "▶" }}</button>
              <b class="tk-score" :class="{ best: t.id === bestId }">
                {{ t.score > 0 ? `${t.score} 分` : "未评分" }}
              </b>
              <i v-if="t.id === bestId" class="tk-tag">最高分</i>
              <span class="tk-time">{{ hhmm(t.at) }}</span>
              <span class="tk-text">{{ t.transcript }}</span>
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
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";
import {
  loadSpeak, planDayDone, splitSpeakPlan,
  type DayCheck, type PlanDayView, type Scene, type SpeakData,
} from "../core/speak";
import { startMakeRecording, type MakeRec } from "../core/makeRecorder";
import { useSpeakTime } from "../core/speakTime";
import { addTake, newTakeId, takeStorageKey } from "../core/takes";
import { useTakeList } from "../core/takeList";
import {
  budgetBanner, loadAiStatus, paidBlocked, paidLockText, type AiStatus,
} from "../core/aiStatus";
import { say, playAudioUrl } from "../core/say";
import { devMode } from "../core/devMode";
import BackButton from "../components/BackButton.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import PaidActionButton from "../components/PaidActionButton.vue";
import PaidAiNotice from "../components/PaidAiNotice.vue";
import SpeakImproveCard from "../components/SpeakImproveCard.vue";

const route = useRoute();
const data = ref<SpeakData | null>(null);
const loading = ref(true);
const part = ref(0);
const sceneId = ref("");
const pi = ref(0);
const mine = ref("");
const checking = ref(false);
const answerShown = ref(false);
const fb = ref<{ ok: boolean; comment: string; improved: string } | null>(null);
const status = ref("");
const listening = ref(false);
const aiStatus = ref<AiStatus | null>(null);
const banner = computed(() => budgetBanner(aiStatus.value));
const locked = computed(() => paidBlocked(aiStatus.value));
const lockText = computed(() => paidLockText(aiStatus.value));
let rec: MakeRec | null = null;
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

// ---- 我的录音：本次尝试只在页面内存保留（不评分不落库，刷新/切题即删）；
// 手动跟读评分后才进 IndexedDB 存档（最近 3 次 + 最高分）
const auth = useAuthStore();
const attemptScore = ref(0);
let attemptBlob: Blob | null = null;
const attemptUrl = ref("");

const promptKey = computed(() => (prompt.value ? `${sceneId.value}:${prompt.value.id}` : ""));
const takeKey = computed(() => takeStorageKey(auth.username, promptKey.value));
const { takes, playingId, bestId, togglePlay, refresh: refreshTakes } = useTakeList(takeKey);

function dropAttempt(): void {
  if (attemptUrl.value) {
    try { URL.revokeObjectURL(attemptUrl.value); } catch { /* noop */ }
  }
  attemptUrl.value = "";
  attemptBlob = null;
  attemptScore.value = 0;
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
  answerShown.value = false;
  fb.value = null;
  status.value = "";
  listening.value = false;
  finished = false;
  dropAttempt();
  rec?.close();
  rec = null;
}

async function startSpeak(): Promise<void> {
  if (!prompt.value || rec) return;
  if (locked.value) {
    status.value = lockText.value;
    return;
  }
  finished = false;
  mine.value = "";
  fb.value = null;
  answerShown.value = false;
  dropAttempt();
  status.value = "开启麦克风…";
  try {
    rec = await startMakeRecording({
      onStatus: (s) => { status.value = s; },
      onError: (msg) => {
        status.value = msg;
        rec = null;
      },
      onSubmit: submitAttempt,
      onCancel: cancelAttempt,
    });
    status.value = "可以开始说，说完点小绿下面的「提交」";
  } catch (e) {
    status.value = "语音不可用：" + (e as Error).message + "（请检查麦克风后重试）";
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
  dropAttempt();
  rec?.close();
  rec = null;
  fb.value = null;
  answerShown.value = false;
  status.value = "已取消本次造句，点「开始说」重新开始";
}

/** 提交：结束录音 → 上传 ASR 转写 → 文字点评。录音 Blob 只留页面内存。 */
async function finishSpeak(): Promise<void> {
  const r = rec;
  if (!r || listening.value) return;
  listening.value = true;
  status.value = "正在转写…";
  try {
    const blob = await r.stop();
    rec = null;
    if (blob && blob.size > 0) {
      dropAttempt();
      attemptBlob = blob;
      attemptUrl.value = URL.createObjectURL(blob);
    }
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

/** 「听我说的」：回放本次真实录音（内存 object URL，刷新/切题即失） */
function playMine(): void {
  if (!attemptUrl.value) return;
  void new Audio(attemptUrl.value).play().catch(() => { /* 自动播放被拦截时静默 */ });
}

function stopSpeak(): void {
  rec?.close();
  rec = null;
  status.value = "";
}

/** 页面关闭时停掉麦克风（录音本就不持久化，无需补报会话）。 */
function onPageHide(): void {
  rec?.close();
  rec = null;
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

/** 跟读优化句评分后：分数落到本次录音，进入「最近 3 次 + 最高分」存档 */
function onScored(v: { score: number }): void {
  attemptScore.value = v.score;
  void saveTake(takeKey.value, promptKey.value, Math.round(v.score), mine.value.trim());
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

// ---- 我的录音（评分后落库）

/** 手动跟读评分后落库：题目 + 时间 + 分数 + 转写 + 录音 Blob（key/promptId 即时捕获，避免中途切题写错） */
async function saveTake(key: string, promptId: string, score: number, transcript: string): Promise<void> {
  const blob = attemptBlob;
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
      mime: blob.type || "audio/webm",
      blob,
    });
    if (key === takeKey.value) await refreshTakes();
  } catch { /* 存不进（隐私模式/配额）不影响练习 */ }
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
.fb .imp-card { max-width: 100%; margin-top: 8px; background: #fff; }
.takes { margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--c-line, #e5e7eb); }
.takes-h { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.takes-h b { color: var(--c-text); font-size: 14px; }
.takes-h span { color: var(--c-text-2); font-size: 12px; }
.take { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 8px; padding: 8px 10px; border-radius: var(--r-btn); background: var(--c-mint-bg); }
.tk-play { width: 30px; height: 30px; border-radius: 999px; border: 1px solid var(--c-line, #d1d5db); background: var(--c-surface); color: var(--c-primary); font-size: 12px; cursor: pointer; }
.tk-play:hover { border-color: var(--c-primary); }
.tk-score { font-size: 13px; color: var(--c-text); font-variant-numeric: tabular-nums; }
.tk-score.best { color: var(--c-primary); }
.tk-tag { font-style: normal; font-size: 11px; font-weight: 700; color: var(--c-primary); background: var(--c-primary-soft); border-radius: 999px; padding: 2px 8px; }
.tk-time { font-size: 12px; color: var(--c-text-3); font-variant-numeric: tabular-nums; }
.tk-text { flex: 1; min-width: 160px; font-size: var(--fs-sub); color: var(--c-text); }
</style>
