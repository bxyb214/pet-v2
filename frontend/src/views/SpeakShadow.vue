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
        : "没有计划：按你的水平从题库选句子，不计时、不打卡。" }}
    </p>

    <div v-if="banner" class="banner" :class="banner.tone">{{ banner.text }}</div>
    <div v-if="lockText" class="lockbar">
      <b>付费 AI 未启用</b>
      <span>{{ lockText }}</span>
    </div>

    <!-- 5 分钟目标：只提示，不强制；有计划才计时 -->
    <div v-if="hasPlan" class="card targetbar" :class="{ over: overGoal }">
      <span class="target-label">今日跟读</span>
      <b class="target-time">{{ mmss(elapsed) }}</b>
      <span class="target-goal">/ 5:00</span>
      <span class="target-hint">
        {{ overGoal ? "已到 5 分钟，练完这句就休息吧" : `剩余 ${mmss(Math.max(0, 300 - elapsed))}` }}
      </span>
    </div>

    <!-- 无计划：智能选句（跨库）或指定句子组 -->
    <div v-if="!hasPlan && freePacks.length" class="card freebar">
      <div class="free-head">
        <b>选择题库</b>
        <span>目标难度 {{ diffLabel(target) }} · 自由练习不计时</span>
        <button type="button" class="resort" @click="resort">换一组</button>
      </div>
      <div class="packs">
        <button type="button" class="packchip" :class="{ on: !packId }" @click="pickPack('')">
          智能选句
        </button>
        <button
          v-for="p in freePacks" :key="p.id" type="button"
          class="packchip" :class="{ on: p.id === packId }"
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
        <div class="meta">
          <span class="diff">{{ diffLabel(item.difficulty) }}</span>
          <span>{{ item.words }} 词</span>
          <span>{{ item.packName }}</span>
        </div>
        <div v-if="item.tip" class="tip">{{ item.tip }}</div>
        <div class="sent-actions">
          <n-button size="small" secondary @click="tts">
            {{ locked ? "听示范（浏览器朗读）" : "听示范（AI 朗读）" }}
          </n-button>
          <n-button size="small" quaternary @click="next">换一句 →</n-button>
          <span class="idx">{{ itemIdx + 1 }} / {{ orderedItems.length }}</span>
        </div>
      </div>

      <div class="ctrl card">
        <div class="status">{{ status }}</div>
        <div class="ctrlbtns">
          <template v-if="!soe">
            <n-button type="primary" size="large" :disabled="locked" @click="start">
              跟读评分
            </n-button>
            <n-button v-if="locked" size="large" secondary @click="listenAndRepeat">
              自己读一遍
            </n-button>
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
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NTag } from "naive-ui";
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";
import {
  loadSpeak, sourceRangeText, splitSpeakPlan,
  type PlanDayView, type ShadowItem, type SpeakData,
} from "../core/speak";
import { SoeEval, type SoeWord } from "../core/soe";
import { useSpeakTime } from "../core/speakTime";
import {
  pickSentences, sortSentences, targetDifficulty, weakWordsFromRecent,
  type BankSentence, type RecentShadow,
} from "../core/sentenceBank";
import {
  budgetBanner, loadAiStatus, paidBlocked, paidLockText, type AiStatus,
} from "../core/aiStatus";
import { say, playAudioUrl } from "../core/say";
import BackButton from "../components/BackButton.vue";

type ShadowResult = { score: number; words: SoeWord[]; tips: string[] };

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const data = ref<SpeakData | null>(null);
const planLength = ref(0);
const loaded = ref(false);
const itemIdx = ref(0);
const packId = ref("");
const pickNonce = ref(0);
const aiStatus = ref<AiStatus | null>(null);
const recent = ref<RecentShadow[]>([]);
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

const recentScores = computed(() => recent.value.map((r) => r.score ?? 0).filter((n) => n > 0));
const recentIds = computed(() => recent.value.map((r) => r.sentence_id ?? "").filter(Boolean));
const weakWords = computed(() => weakWordsFromRecent(recent.value));
const target = computed(() => targetDifficulty(recentScores.value));
const today = computed(() => new Date().toISOString().slice(0, 10));

const bankSentences = computed<BankSentence[]>(() => data.value?.shadow ?? []);

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

/** 计划：保留 pack 主题，包内按难度/个性化排序；自由：跨库智能选句或指定包。 */
const orderedItems = computed<ShadowItem[]>(() => {
  if (!data.value) return [];
  if (hasPlan.value && planDay.value) {
    const byId = new Map(data.value.shadow.map((s) => [s.id, s]));
    const picked = planDay.value.shadowIds.map((id) => byId.get(id)).filter(Boolean) as ShadowItem[];
    const groups = new Map<string, ShadowItem[]>();
    for (const s of picked) {
      if (!groups.has(s.pack)) groups.set(s.pack, []);
      groups.get(s.pack)!.push(s);
    }
    const out: ShadowItem[] = [];
    for (const list of groups.values()) {
      out.push(
        ...sortSentences({
          sentences: list,
          recentScores: recentScores.value,
          recentIds: recentIds.value,
          weakWords: weakWords.value,
          packId: list[0]?.pack,
          userId: auth.username,
          date: today.value,
        }) as ShadowItem[],
      );
    }
    return out;
  }
  if (packId.value) {
    return sortSentences({
      sentences: bankSentences.value.filter((s) => s.pack === packId.value),
      recentScores: recentScores.value,
      recentIds: recentIds.value,
      weakWords: weakWords.value,
      packId: packId.value,
      userId: auth.username,
      date: today.value,
    }) as ShadowItem[];
  }
  return pickSentences({
    sentences: bankSentences.value,
    recentScores: recentScores.value,
    recentIds: recentIds.value,
    weakWords: weakWords.value,
    count: 5,
    userId: auth.username,
    date: `${today.value}#${pickNonce.value}`,
  }).items as ShadowItem[];
});

const item = computed<ShadowItem | null>(() => {
  if (!orderedItems.value.length) return null;
  return orderedItems.value[itemIdx.value % orderedItems.value.length];
});

const soe = ref<SoeEval | null>(null);
const status = ref("");
const result = ref<ShadowResult | null>(null);
const banner = computed(() => budgetBanner(aiStatus.value));
const locked = computed(() => paidBlocked(aiStatus.value));
const lockText = computed(() => paidLockText(aiStatus.value));

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
    const [p, st, rec] = await Promise.all([
      api<{ length: number }>("/speak/plan").catch(() => ({ length: 0 })),
      loadAiStatus(),
      api<{ items: RecentShadow[] }>("/speak/shadow/recent?limit=10").catch(() => ({ items: [] })),
    ]);
    planLength.value = p.length ?? 0;
    aiStatus.value = st;
    recent.value = rec.items ?? [];
  } finally {
    loaded.value = true;
  }
  status.value = locked.value
    ? "跟读评分需要开通付费 AI；现在可以先听示范自己读。"
    : "点「跟读评分」，允许麦克风后朗读，读完点「提交」";
});
onBeforeUnmount(() => {
  soe.value?.stop();
  soe.value = null;
});

function start(): void {
  if (!item.value || soe.value) return;
  if (locked.value) {
    status.value = lockText.value;
    return;
  }
  result.value = null;
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
      void logPractice(item.value!, r);
    },
    onError: (m) => {
      status.value = "出错：" + m;
      void loadAiStatus(true).then((s) => (aiStatus.value = s));
    },
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

/** 无付费 AI：只播放示范，孩子自己跟读（P2-4 免费降级）。 */
function listenAndRepeat(): void {
  if (item.value) say(item.value.en);
  status.value = "听完示范，自己大声读一遍即可；跟读评分需要开通付费 AI。";
}

function stop(): void {
  soe.value?.stop();
  soe.value = null;
  if (!hasPlan.value) {
    status.value = "已结束本次练习，可换一组重新开始";
    return;
  }
  void router.push("/english/speak");
}

function pickPack(id: string): void {
  if (id === packId.value) return;
  soe.value?.stop();
  soe.value = null;
  packId.value = id;
  itemIdx.value = 0;
  result.value = null;
  status.value = "点「跟读评分」，允许麦克风后朗读，读完点「提交」";
}
function resort(): void {
  pickNonce.value += 1;
  itemIdx.value = 0;
  result.value = null;
}

/** 每次评分落一条历史（day=0，带 sentence_id/words）；计划日摘要单独写。 */
async function logPractice(it: ShadowItem, r: { score: number; words: SoeWord[] }): Promise<void> {
  try {
    await api("/speak/log", {
      method: "POST",
      body: JSON.stringify({
        mode: "shadow", ref: it.pack, sentence_id: it.id,
        day: 0, turns: 1, score: r.score,
        issues: [], words: r.words, transcript: [],
      }),
    });
  } catch { /* 离线不阻塞 */ }
  if (!planDay.value) return;
  for (const sourceDay of planDay.value.sourceDays) {
    try {
      await api("/speak/log", {
        method: "POST",
        body: JSON.stringify({
          mode: "shadow", ref: it.pack, sentence_id: it.id,
          day: sourceDay, turns: 1, score: r.score,
          issues: [], words: r.words, transcript: [],
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
  const text = item.value?.en ?? "";
  if (!text) return;
  if (locked.value) {
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
    say(text);
  }
}
function diffLabel(d: number | undefined): string {
  const levels = ["A1", "A2", "B1", "B1+", "B2"];
  return levels[Math.max(0, Math.min(4, (d ?? 3) - 1))];
}
function mmss(s: number): string {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}
function back(): void {
  soe.value?.stop();
  soe.value = null;
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
.banner { margin-bottom: 12px; padding: 10px 14px; border-radius: var(--r-btn); font-size: var(--fs-sub); font-weight: 600; }
.banner.warn { background: var(--c-accent-soft); color: var(--c-accent); border: 1px solid var(--c-accent); }
.banner.danger { background: var(--c-danger-soft); color: var(--c-danger); border: 1px solid var(--c-danger); }
.lockbar { display: flex; flex-direction: column; gap: 2px; margin-bottom: 12px; padding: 10px 14px; border-radius: var(--r-btn); background: var(--c-accent-soft); color: var(--c-text-2); font-size: var(--fs-sub); }
.lockbar b { color: var(--c-accent); }
.targetbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 10px 14px; margin-bottom: 12px; color: var(--c-text-2); font-size: var(--fs-sub); }
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
.resort { margin-left: auto; border: 1px solid var(--c-line); background: var(--c-surface); color: var(--c-primary-strong); border-radius: var(--r-pill); padding: 5px 12px; font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer; }
.resort:hover { background: var(--c-primary-soft); }
.packs { display: flex; gap: 8px; flex-wrap: wrap; }
.packchip { border: 1px solid var(--c-line); background: var(--c-surface); color: var(--c-text-2); border-radius: 999px; padding: 6px 12px; font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.packchip i { font-style: normal; font-size: 12px; opacity: 0.65; }
.packchip.on { background: var(--c-primary-strong); border-color: var(--c-primary-strong); color: #fff; }
.packchip.on i { opacity: 0.85; }
.packchip:focus-visible { outline: 3px solid var(--c-accent); outline-offset: 2px; }
.sent { padding: 18px; margin-bottom: 12px; }
.en { font-size: var(--fs-title); color: var(--c-text); font-weight: 600; }
.cn { color: var(--c-text-2); margin-top: 6px; }
.meta { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; color: var(--c-text-3); font-size: 12.5px; }
.diff { color: var(--c-primary-strong); font-weight: 700; }
.tip { color: var(--c-accent); margin-top: 8px; font-size: var(--fs-sub); }
.sent-actions { margin-top: 12px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
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
