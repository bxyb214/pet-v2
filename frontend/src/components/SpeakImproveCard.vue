<template>
  <div class="imp-card" :class="{ compact }">
    <div v-if="showChild" class="said">
      <span class="tag">你说的</span>
      <span class="said-t">{{ childSaid }}</span>
    </div>
    <div class="row">
      <span class="tag good">可以这样说</span>
      <span class="better">{{ improvedEn }}</span>
    </div>
    <div v-if="improvedCn" class="cn">{{ improvedCn }}</div>
    <div v-if="dims?.length" class="chips">
      <n-tag v-for="d in dims" :key="d" size="small" type="success" :bordered="false" round>{{ dimLabel(d) }}</n-tag>
    </div>

    <div class="actions">
      <n-button size="small" secondary :loading="audioPending(improvedEn)" @click="playDemo">🔊 听示范</n-button>
      <template v-if="eval">
        <n-button v-if="!evaluating" size="small" type="primary" @click="startEval">跟读这句</n-button>
        <template v-else>
          <n-button size="small" type="primary" @click="submitEval">读完了，评分</n-button>
          <n-button size="small" quaternary @click="cancelEval">取消</n-button>
        </template>
      </template>
    </div>

    <div v-if="status" class="status">{{ status }}</div>

    <div v-if="result" class="result" :class="{ good: result.score >= PASS, mid: result.score >= MIN && result.score < PASS }">
      <span class="score">{{ result.score }}<small>/100</small></span>
      <span class="tip">{{ plan?.tip }}</span>
      <span class="words">
        <n-tag v-for="(w, i) in result.words" :key="i" size="small" :bordered="false" :type="w.ok ? 'default' : 'error'" round>{{ w.w }}</n-tag>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref } from "vue";
import { NButton, NTag } from "naive-ui";
import { dimLabel, gradePlan, MIN, PASS, type GradePlan } from "../core/review";
import { SoeEval, type SoeResult } from "../core/soe";
import { audioPending } from "../core/say";
import { playLocalTts, playTts } from "../core/tts";
import { stopAdvice } from "../core/adviceSpeech";

const props = withDefaults(defineProps<{
  childSaid: string;
  improvedEn: string;
  improvedCn?: string;
  dims?: string[];
  showChild?: boolean;
  compact?: boolean;
  /** 是否在卡片内提供「跟读这句」评分；造句页改在 AI 示范句下方统一评分 */
  eval?: boolean;
  /** 只用本地 TTS 听示范，不回落浏览器（造句页 AI 反馈） */
  localOnly?: boolean;
}>(), { improvedCn: "", dims: () => [], showChild: false, compact: false, eval: true, localOnly: false });

const emit = defineEmits<{ (e: "scored", v: { score: number; dimsOk: string[] }): void }>();

const evaluating = ref(false);
const status = ref("");
const result = ref<SoeResult | null>(null);
const plan = ref<GradePlan | null>(null);
let soe: SoeEval | null = null;

onBeforeUnmount(() => soe?.stop());

async function playDemo(): Promise<void> {
  stopAdvice();
  if (props.localOnly) {
    const ok = await playLocalTts(props.improvedEn);
    if (!ok) status.value = "本地发音暂不可用，请稍后再试";
    return;
  }
  await playTts(props.improvedEn);
}

async function startEval(): Promise<void> {
  result.value = null;
  plan.value = null;
  status.value = "";
  const ev = new SoeEval({
    refText: props.improvedEn,
    onStatus: (s) => (status.value = s),
    onResult: (r) => onScored(r),
    onError: (m) => {
      status.value = m;
      evaluating.value = false;
    },
    onMicClosed: () => {
      soe = null;
      evaluating.value = false;
      status.value = "麦克风已关闭，需要时再点「跟读这句」";
    },
  });
  soe = ev;
  try {
    await ev.start();
    if (soe === ev) evaluating.value = true;
  } catch {
    ev.stop();
    evaluating.value = false;
  }
}

function submitEval(): void {
  soe?.submit();
  status.value = "评分中…";
}

function cancelEval(): void {
  soe?.stop();
  soe = null;
  evaluating.value = false;
  status.value = "";
}

function onScored(r: SoeResult): void {
  evaluating.value = false;
  result.value = r;
  const gp = gradePlan(r.score, props.dims ?? []);
  plan.value = gp;
  emit("scored", { score: r.score, dimsOk: gp.dims_ok });
}
</script>

<style scoped>
.imp-card {
  background: var(--c-mint-bg, #f6faf7); border: 1px solid var(--c-line);
  border-radius: var(--r-btn); padding: 10px 12px; margin-top: 6px; max-width: 78%;
}
.imp-card.compact { max-width: 100%; margin-top: 0; }
.said { display: flex; gap: 8px; align-items: flex-start; margin-bottom: 6px; }
.said-t { color: var(--c-text-2); text-decoration: line-through; }
.row { display: flex; gap: 8px; align-items: flex-start; }
.tag { flex-shrink: 0; font-size: var(--fs-sub); font-weight: 700; color: var(--c-text-2); background: #fff; border-radius: var(--r-sm); padding: 2px 8px; }
.tag.good { color: var(--c-primary); background: var(--c-primary-soft); }
.better { color: var(--c-text); font-weight: 700; line-height: 1.5; }
.cn { color: var(--c-text-2); font-size: var(--fs-sub); margin-top: 4px; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
.actions { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.status { color: var(--c-text-2); font-size: var(--fs-sub); margin-top: 6px; }
.result { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 8px; }
.score { font-size: 24px; font-weight: 800; color: var(--c-accent); }
.result.good .score { color: var(--c-primary); }
.score small { font-size: var(--fs-sub); color: var(--c-text-2); }
.tip { color: var(--c-text-2); font-size: var(--fs-sub); }
.words { display: flex; gap: 6px; flex-wrap: wrap; }
</style>
