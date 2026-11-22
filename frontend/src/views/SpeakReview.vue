<template>
  <main class="page">
    <button class="ghost back" @click="back">← 返回口语</button>
    <h1>口语复盘</h1>
    <p class="sub">把你刚才说过的话，换成更好的说法再读一遍。读到 85 分就算过关。</p>

    <div v-if="loading" class="card empty">加载中…</div>
    <div v-else-if="!items.length" class="card empty">
      今天没有要复盘的句子啦 🎉
      <div class="mt">
        <button class="btn" @click="back">回口语首页</button>
      </div>
    </div>

    <template v-else>
      <div class="progress">{{ idx + 1 }} / {{ items.length }}</div>

      <div class="card item">
        <div class="row">
          <span class="tag">你说的</span>
          <span class="said">{{ cur.child_said }}</span>
        </div>
        <div class="row">
          <span class="tag good">可以这样说</span>
          <span class="better">{{ cur.improved_en }}</span>
        </div>
        <div v-if="cur.improved_cn" class="cn">{{ cur.improved_cn }}</div>
        <div class="chips">
          <n-tag size="small" type="success" :bordered="false" round>{{ focusLabel(cur.focus) }}</n-tag>
          <n-tag v-for="d in cur.dims" :key="d" size="small" :bordered="false" round>{{ dimLabel(d) }}</n-tag>
        </div>

        <div class="actions">
          <n-button secondary @click="playDemo">🔊 听示范</n-button>
          <n-button v-if="!evaluating" type="primary" @click="startEval">开始跟读</n-button>
          <template v-else>
            <n-button type="primary" @click="submitEval">读完了，评分</n-button>
            <n-button quaternary @click="cancelEval">取消</n-button>
          </template>
        </div>

        <div v-if="status" class="status">{{ status }}</div>

        <div v-if="result" class="result" :class="{ good: result.score >= PASS, mid: result.score >= MIN && result.score < PASS }">
          <div class="score">{{ result.score }}<small>/100</small></div>
          <div class="tip">{{ plan?.tip }}</div>
          <div class="words">
            <n-tag v-for="(w, i) in result.words" :key="i" size="small" :bordered="false" :type="w.ok ? 'default' : 'error'" round>
              {{ w.w }}
            </n-tag>
          </div>
          <n-button type="primary" @click="next">{{ idx + 1 < items.length ? "下一句" : "完成复盘" }}</n-button>
        </div>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NTag } from "naive-ui";
import { api } from "../core/api";
import { dimLabel, focusLabel, gradePlan, MIN, PASS, type GradePlan, type ReviewItem } from "../core/review";
import { SoeEval, type SoeResult } from "../core/soe";

const router = useRouter();
const items = ref<ReviewItem[]>([]);
const idx = ref(0);
const loading = ref(true);
const evaluating = ref(false);
const status = ref("");
const result = ref<SoeResult | null>(null);
const plan = ref<GradePlan | null>(null);
let soe: SoeEval | null = null;

const cur = computed(() => items.value[idx.value]);

onMounted(async () => {
  try {
    const r = await api<{ items: ReviewItem[] }>("/english/speak/review/due");
    items.value = r.items ?? [];
  } catch {
    items.value = [];
  }
  loading.value = false;
});
onBeforeUnmount(() => soe?.stop());

async function playDemo(): Promise<void> {
  try {
    const r = await api<{ b64: string; mime: string }>("/english/speak/tts", {
      method: "POST",
      body: JSON.stringify({ text: cur.value.improved_en }),
    });
    const audio = new Audio(`data:${r.mime};base64,${r.b64}`);
    void audio.play();
  } catch (e) {
    status.value = "示范播放失败：" + (e as Error).message;
  }
}

async function startEval(): Promise<void> {
  result.value = null;
  plan.value = null;
  status.value = "";
  soe = new SoeEval({
    refText: cur.value.improved_en,
    onStatus: (s) => (status.value = s),
    onResult: (r) => void onScored(r),
    onError: (m) => {
      status.value = m;
      evaluating.value = false;
    },
  });
  try {
    await soe.start();
    evaluating.value = true;
  } catch {
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

async function onScored(r: SoeResult): Promise<void> {
  evaluating.value = false;
  result.value = r;
  const p = gradePlan(r.score, cur.value.dims);
  plan.value = p;
  try {
    await api("/english/speak/review/grade", {
      method: "POST",
      body: JSON.stringify({ id: cur.value.id, score: r.score, dims_ok: p.dims_ok }),
    });
  } catch { /* 离线不阻塞 */ }
}

async function next(): Promise<void> {
  soe?.stop();
  soe = null;
  result.value = null;
  plan.value = null;
  status.value = "";
  if (idx.value + 1 < items.value.length) {
    idx.value += 1;
    return;
  }
  // 重新拉一次到期队列（刚评过的若未过关会再次到期，但先回首页避免刷屏）
  void router.push("/english/speak");
}
function back(): void {
  soe?.stop();
  void router.push("/english/speak");
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.empty { padding: 28px 16px; text-align: center; color: var(--c-text-2); }
.mt { margin-top: 14px; }
.progress { color: var(--c-text-2); font-size: var(--fs-sub); margin-bottom: 8px; }
.item { padding: 16px; }
.row { display: flex; gap: 10px; align-items: flex-start; margin-bottom: 10px; }
.tag { flex-shrink: 0; font-size: var(--fs-sub); font-weight: 700; color: var(--c-text-2); background: var(--c-bg-mint); border-radius: var(--r-sm); padding: 2px 8px; }
.tag.good { color: var(--c-primary); background: var(--c-primary-soft); }
.said { color: var(--c-text-2); text-decoration: line-through; }
.better { color: var(--c-text); font-weight: 700; font-size: 20px; }
.cn { color: var(--c-text-2); font-size: var(--fs-sub); margin: -2px 0 10px 0; }
.chips { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }
.chip { font-size: var(--fs-sub); border-radius: 999px; padding: 2px 10px; }
.chip.focus { background: var(--c-primary-soft); color: var(--c-primary); font-weight: 700; }
.chip.dim { background: var(--c-bg-mint); color: var(--c-text-2); }
.actions { display: flex; gap: 10px; flex-wrap: wrap; }
.status { color: var(--c-text-2); font-size: var(--fs-sub); margin-top: 10px; }
.result { margin-top: 14px; text-align: center; }
.score { font-size: 36px; font-weight: 800; color: var(--c-warn, #d97706); }
.result.good .score { color: var(--c-primary); }
.result.mid .score { color: var(--c-warn, #d97706); }
.score small { font-size: var(--fs-sub); color: var(--c-text-2); }
.tip { color: var(--c-text-2); margin: 2px 0 8px; }
.words { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; margin-bottom: 12px; }
.w { background: var(--c-bg-mint); color: var(--c-text); border-radius: var(--r-sm); padding: 2px 8px; }
.w.bad { background: #fee2e2; color: #b91c1c; }
</style>
