<!-- 跟读评分块：造句页/复盘页复用；界面与「跟读纠音」结果保持一致 -->
<template>
  <div class="eval">
    <div class="row">
      <PaidActionButton :status="aiStatus" :disabled="busy" @click="start">跟读评分</PaidActionButton>
      <span class="status">{{ status || idleHint }}</span>
    </div>

    <div v-if="result" class="result" :class="{ good: result.score >= 85, ok: result.score >= 60 }">
      <div class="score">{{ result.score }}<small>/100</small></div>
      <div class="engine">跟读评分 · 腾讯云智聆</div>
      <div v-if="metrics.length" class="metrics">
        <span v-for="m in metrics" :key="m.label" class="metric" :class="{ low: m.value < 60 }">
          <b>{{ m.value }}</b>{{ m.label }}
        </span>
      </div>
      <div v-if="result.words.length" class="words">
        <button
          v-for="(w, i) in result.words" :key="i" type="button"
          class="wchip" :class="{ bad: !w.ok }"
          :title="`${w.w}${w.acc != null ? ' · 准确度 ' + w.acc : ''} · 点击听发音`"
          :disabled="audioPending(w.w)"
          @click="sayWord(w.w)"
        >
          <span v-if="audioPending(w.w)" class="audio-spin" aria-hidden="true" />
          {{ w.w }}<i v-if="w.acc != null">{{ w.acc }}</i>
        </button>
      </div>
      <div v-if="tips.length" class="tips-h-row">
        <p class="tips-h">改进建议</p>
        <button type="button" class="tips-play" :disabled="audioPending(adviceText(tips))" @click="replayTips">
          <span v-if="audioPending(adviceText(tips))" class="audio-spin" aria-hidden="true" />🔊 朗读建议
        </button>
      </div>
      <ul v-if="tips.length" class="tips">
        <li v-for="(t, i) in tips" :key="i">{{ t }}</li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { SoeEval, soeTips, type SoeResult } from "../core/soe";
import { audioPending, say } from "../core/say";
import { adviceText, readAdvice, stopAdvice } from "../core/adviceSpeech";
import { type AiStatus } from "../core/aiStatus";
import PaidActionButton from "./PaidActionButton.vue";

const props = withDefaults(defineProps<{
  /** 要跟读/评分的参考文本 */
  refText: string;
  aiStatus: AiStatus | null | undefined;
  /** 建议朗读只用本地 TTS，不回落浏览器（造句页 AI 示范句） */
  localAdvice?: boolean;
}>(), { localAdvice: false });
const emit = defineEmits<{
  (e: "scored", v: { score: number; blob: Blob | null }): void;
  (e: "starting"): void;
}>();

const busy = ref(false);
const status = ref("");
const result = ref<(SoeResult & { tips: string[] }) | null>(null);
let soe: SoeEval | null = null;

const idleHint = computed(() =>
  "点「跟读评分」，允许麦克风后朗读这句，读完点小绿下面的「提交」",
);

const metrics = computed(() => {
  const r = result.value;
  if (!r) return [];
  const out: { label: string; value: number }[] = [];
  if (r.accuracy != null) out.push({ label: "准确度", value: r.accuracy });
  if (r.fluency != null) out.push({ label: "流利度", value: r.fluency });
  if (r.completion != null) out.push({ label: "完整度", value: r.completion });
  return out;
});
const tips = computed(() => result.value?.tips ?? []);

function sayWord(w: string): void {
  if (!w) return;
  stopAdvice();
  say(w);
}

function replayTips(): void {
  void readAdvice(tips.value, { fallback: !props.localAdvice });
}

function reset(): void {
  soe?.stop();
  soe = null;
  busy.value = false;
  result.value = null;
  status.value = "";
  stopAdvice();
}

watch(() => props.refText, () => reset());
onBeforeUnmount(() => {
  soe?.stop();
  soe = null;
  stopAdvice();
});

function start(): void {
  const refText = props.refText.trim();
  if (!refText || soe) return;
  stopAdvice();
  emit("starting");
  result.value = null;
  busy.value = false;
  status.value = "开启麦克风…";
  const ev = new SoeEval({
    refText,
    onStatus: (s) => (status.value = s),
    onBusy: (b) => (busy.value = b),
    onResult: (r) => {
      const t = soeTips(r);
      result.value = { ...r, tips: t };
      void readAdvice(t, { fallback: !props.localAdvice });
      emit("scored", { score: r.score, blob: ev.takeAudio() });
    },
    onError: (m) => (status.value = "出错：" + m),
    onMicClosed: () => (status.value = "麦克风已关闭，可重新点「跟读评分」"),
    onStopped: () => {
      busy.value = false;
      if (soe === ev) soe = null;
    },
  });
  soe = ev;
  void ev.start().catch(() => {
    ev.stop();
    if (soe === ev) soe = null;
  });
}
</script>

<style scoped>
.eval { margin-top: 10px; }
.row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.status { color: var(--c-text-2); font-size: var(--fs-sub); }
.result { margin-top: 12px; padding: 14px; border-radius: var(--r-btn); border: 1px solid var(--c-line); background: var(--c-surface); }
.result.good { border-color: var(--c-primary); }
.result.ok { border-color: var(--c-accent); }
.score { font-size: 32px; font-weight: 800; color: var(--c-primary); line-height: 1.1; }
.score small { font-size: var(--fs-sub); color: var(--c-text-2); }
.engine { font-size: var(--fs-sub); color: var(--c-text-2); margin-top: 2px; }
.metrics { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.metric { display: inline-flex; align-items: baseline; gap: 5px; padding: 4px 11px; border-radius: 999px; background: var(--c-mint-bg, #f6faf7); color: var(--c-text-2); font-size: 12.5px; font-weight: 600; }
.metric b { font-size: 15px; color: var(--c-primary-strong, #15803d); font-variant-numeric: tabular-nums; }
.metric.low b { color: var(--c-accent, #b45309); }
.words { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.wchip { display: inline-flex; align-items: baseline; gap: 5px; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--c-line); background: #fff; color: var(--c-text); font: inherit; font-size: 13px; cursor: pointer; }
.wchip:hover { border-color: var(--c-primary); }
.wchip i { font-style: normal; font-size: 11px; color: var(--c-text-3); }
.wchip.bad { background: var(--c-accent-soft, #fff7ed); border-color: var(--c-accent, #d97706); color: #b45309; }
.tips-h-row { margin: 12px 0 0; display: flex; align-items: center; gap: 10px; }
.tips-h { margin: 0; font-weight: 700; color: var(--c-text); font-size: 14px; }
.tips-play {
  border: 1px solid var(--c-line); background: var(--c-surface);
  color: var(--c-text-2); border-radius: 999px; padding: 2px 10px;
  font-size: 12px; cursor: pointer;
}
.tips-play:hover { color: var(--c-text); }
.tips { color: var(--c-text-2); font-size: var(--fs-sub); margin: 6px 0 0; padding-left: 18px; line-height: 1.7; }
</style>
