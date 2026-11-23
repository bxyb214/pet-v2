<template>
  <main class="page">
    <BackButton @click="back" />
    <h1>
      跟读纠音
      <span v-if="planDay" class="daychip">第 {{ planDay.day }} 天 · {{ sourceRangeText(planDay) }}</span>
    </h1>
    <p class="sub">
      {{ hasPlan
        ? "听示范 → 点「跟读评分」→ 朗读 → 提交，看分数和读不准的词 · 今天目标 5 分钟"
        : "没有计划：从题库选一组句子自由练习，不计时、不打卡。" }}
    </p>

    <!-- 5 分钟目标：只提示，不强制；有计划才计时 -->
    <div v-if="hasPlan" class="card targetbar" :class="{ over: overGoal }">
      <span class="target-label">今日跟读</span>
      <b class="target-time">{{ mmss(elapsed) }}</b>
      <span class="target-goal">/ 5:00</span>
      <span class="target-hint">
        {{ overGoal ? "已到 5 分钟，练完这句就休息吧" : `剩余 ${mmss(Math.max(0, 300 - elapsed))}` }}
      </span>
    </div>

    <!-- 无计划：选择题库句子组开始 -->
    <div v-if="!hasPlan && freePacks.length" class="card freebar">
      <div class="free-head">
        <b>选择题库</b>
        <span>自由练习 · 不计时、不打卡</span>
      </div>
      <div class="packs">
        <button
          v-for="p in freePacks" :key="p.id" type="button"
          class="packchip" :class="{ on: p.id === activePackId }"
          @click="pickPack(p.id)"
        >{{ p.name }} <i>{{ p.count }}</i></button>
      </div>
    </div>

    <div v-if="!loaded" class="empty card">加载中…</div>
    <div v-else-if="!item" class="empty card">
      {{ hasPlan ? "今天的跟读内容为空" : "题库内容为空" }}
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
          <template v-if="!soe">
            <n-button type="primary" size="large" @click="start">跟读评分</n-button>
          </template>
          <template v-else>
            <n-button type="primary" size="large" @click="submit">提交</n-button>
            <n-button size="large" quaternary @click="stop">结束练习</n-button>
          </template>
        </div>
      </div>

      <div v-if="result" class="result card" :class="{ good: result.score >= 85, ok: result.score >= 60 }">
        <div class="score">{{ result.score }}<small>/100</small></div>
        <div class="engine">跟读评分 · 腾讯云智聆</div>
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
          <n-button quaternary @click="stop">{{ hasPlan ? "结束练习（保存记录）" : "结束练习" }}</n-button>
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
  loadSpeak, sourceRangeText, splitSpeakPlan,
  type PlanDayView, type ShadowItem, type SpeakData,
} from "../core/speak";
import { SoeEval, type SoeWord } from "../core/soe";
import { useSpeakTime } from "../core/speakTime";
import BackButton from "../components/BackButton.vue";

type ShadowResult = { score: number; words: SoeWord[]; tips: string[] };

const route = useRoute();
const router = useRouter();
const data = ref<SpeakData | null>(null);
const planLength = ref(0);
const loaded = ref(false);
const itemIdx = ref(0);
const packId = ref("");
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

/** 无计划：按句子库（pack）自由选择，库内顺序不变 */
const freePacks = computed(() => {
  const d = data.value;
  if (!d) return [];
  const counts = new Map<string, number>();
  for (const s of d.shadow) counts.set(s.pack, (counts.get(s.pack) ?? 0) + 1);
  return [...d.packs]
    .sort((a, b) => a.order - b.order)
    .map((p) => ({ id: p.id, name: p.name, count: counts.get(p.id) ?? 0 }))
    .filter((p) => p.count > 0);
});
const activePackId = computed(() => packId.value || freePacks.value[0]?.id || "");
const freeItems = computed<ShadowItem[]>(() => {
  if (!data.value || !activePackId.value) return [];
  return data.value.shadow.filter((s) => s.pack === activePackId.value);
});
const orderedItems = computed<ShadowItem[]>(() => {
  if (!hasPlan.value) return freeItems.value;
  if (!data.value || !planDay.value) return [];
  const byId = new Map(data.value.shadow.map((s) => [s.id, s]));
  return planDay.value.shadowIds.map((id) => byId.get(id)).filter((s): s is ShadowItem => !!s);
});
const item = computed<ShadowItem | null>(() => {
  if (!orderedItems.value.length) return null;
  return orderedItems.value[itemIdx.value % orderedItems.value.length];
});

const soe = ref<SoeEval | null>(null);
const status = ref("");
const result = ref<ShadowResult | null>(null);
const scores = ref<number[]>([]);
const ttsEl = ref<HTMLAudioElement | null>(null);

// 只累计“真正开口”的秒数，并由服务端按天保存，刷新不丢
const speechBase = ref(0);
const clock = useSpeakTime("shadow", currentSpeech, () => hasPlan.value);
const elapsed = clock.total;
const overGoal = computed(() => elapsed.value >= 300);

function currentSpeech(): number {
  return speechBase.value + (soe.value?.speechSec() ?? 0);
}
function settleSpeech(): void {
  if (soe.value) speechBase.value += soe.value.speechSec();
}

onMounted(async () => {
  try {
    data.value = await loadSpeak();
    try {
      const r = await api<{ length: number }>("/speak/plan");
      planLength.value = r.length ?? 0;
    } catch { /* 离线按无计划处理 */ }
    if (!hasPlan.value) packId.value = freePacks.value[0]?.id ?? "";
  } finally {
    loaded.value = true;
  }
  status.value = "点「跟读评分」，允许麦克风后朗读，读完点「提交」";
});
onBeforeUnmount(() => {
  soe.value?.stop();
  soe.value = null;
});

function start(): void {
  if (!item.value || soe.value) return;
  result.value = null;
  scores.value = [];
  settleSpeech();
  const ev = new SoeEval({
    refText: item.value.en,
    onStatus: (s) => (status.value = s),
    onResult: (r) => {
      const bad = r.words.filter((w) => !w.ok).map((w) => w.w);
      result.value = {
        score: r.score,
        words: r.words,
        tips: bad.length ? [`读不准的词：${bad.join("、")}，多听几遍示范再试试`] : [],
      };
      scores.value.push(r.score);
    },
    onError: (m) => (status.value = "出错：" + m),
    onMicClosed: () => {
      status.value = "麦克风已关闭，可重新开始跟读";
    },
    onStopped: () => {
      settleSpeech();
      soe.value = null;
    },
  });
  soe.value = ev;
  void ev.start().catch(() => {
    ev.stop();
    soe.value = null;
  });
}
function submit(): void {
  soe.value?.submit();
}

function stop(): void {
  soe.value?.stop();
  soe.value = null;
  void finish();
  if (!hasPlan.value) {
    status.value = "已结束本次练习，可换一组重新开始";
    return;
  }
  void router.push("/english/speak");
}

/** 无计划时切换句子库：结束当前采集并从新库第一句开始 */
function pickPack(id: string): void {
  if (id === activePackId.value) return;
  soe.value?.stop();
  soe.value = null;
  packId.value = id;
  itemIdx.value = 0;
  result.value = null;
  scores.value = [];
  status.value = "点「跟读评分」，允许麦克风后朗读，读完点「提交」";
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
  status.value = "点「跟读评分」，允许麦克风后朗读，读完点「提交」";
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
  soe.value?.stop();
  soe.value = null;
  void finish();
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
.freebar { padding: 12px 14px; margin-bottom: 12px; }
.free-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 9px; }
.free-head b { color: var(--c-text); font-size: 14.5px; }
.free-head span { color: var(--c-text-2); font-size: 12.5px; }
.packs { display: flex; gap: 8px; flex-wrap: wrap; }
.packchip {
  border: 1px solid var(--c-line); background: var(--c-surface); color: var(--c-text-2);
  border-radius: 999px; padding: 6px 12px; font: inherit; font-size: 13px; font-weight: 600;
  cursor: pointer; display: inline-flex; align-items: center; gap: 5px;
}
.packchip i { font-style: normal; font-size: 12px; opacity: 0.65; }
.packchip.on { background: var(--c-primary-strong); border-color: var(--c-primary-strong); color: #fff; }
.packchip.on i { opacity: 0.85; }
.packchip:focus-visible { outline: 3px solid var(--c-accent); outline-offset: 2px; }
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
.words { margin-top: 10px; }
.tips { color: var(--c-text-2); font-size: var(--fs-sub); margin: 8px 0 0; padding-left: 18px; }
.res-actions { margin-top: 12px; display: flex; gap: 8px; }
</style>
