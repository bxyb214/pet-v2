<template>
  <main class="page">
    <button class="ghost back" @click="back">← 返回听力列表</button>
    <h1>听力错题复习</h1>
    <p class="sub">只考欠的题 · 答对划掉走间隔 · 答错回 1 天</p>

    <div v-if="!jobs.length" class="empty card">🎉 没有到期的听力错题。</div>
    <template v-else>
      <div class="q card" :class="{ right: judged === 'right', wrong: judged === 'wrong' }">
        <div class="q-head">
          <span class="qno">{{ cur.item?.no }}</span>
          <span class="qstem">{{ cur.item?.stem }}</span>
        </div>
        <img v-if="cur.item?.img" class="qimg" :src="cur.item?.img" alt="" />
        <template v-if="kind === 'fill'">
          <input
            v-model="fillInput"
            class="fill-input"
            type="text"
            :disabled="judged !== null"
            :placeholder="judged !== null ? '已判' : '输入答案'"
            @keyup.enter="submitFill"
          />
        </template>
        <template v-else>
          <button
            v-for="(opt, oi) in cur.item?.options ?? []" :key="oi"
            class="opt"
            :class="{ picked: pick === oi, correct: judged !== null && oi === cur.item?.answer, wrongPick: judged !== null && pick === oi && oi !== cur.item?.answer }"
            :disabled="judged !== null"
            @click="pickChoice(oi)"
          >
            <span class="opt-key">{{ String.fromCharCode(65 + oi) }}</span>
            <img v-if="kind === 'picture'" class="opt-img" :src="opt" alt="" />
            <span v-else class="opt-text">{{ opt }}</span>
          </button>
        </template>
        <div v-if="judged" class="feedback">
          <span v-if="judged === 'right'" class="ok">✓ 答对！</span>
          <span v-else class="no">✗ 正确答案：{{ correctText }}</span>
        </div>
      </div>
      <div class="actions">
        <span class="count">{{ done }} / {{ jobs.length }} 已复习</span>
        <button v-if="judged" class="btn" @click="next">下一题 →</button>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useLearningStore } from "../stores/learning";
import { isFillCorrect, loadListening, mistakeKey, type LItem } from "../core/listening";

const router = useRouter();
const learning = useLearningStore();

type Job = { key: string; item: LItem; book: string; partNo: number };
const jobs = ref<Job[]>([]);
const cursor = ref(0);
const pick = ref<number | null>(null);
const fillInput = ref("");
const judged = ref<"right" | "wrong" | null>(null);
let loaded = false;

const cur = computed(() => jobs.value[cursor.value] ?? ({} as Job));
const kind = computed<"picture" | "choice" | "fill">(() => {
  const j = jobs.value[cursor.value];
  if (!j) return "choice";
  if (j.item.options) return "choice";
  return "fill";
});
const correctText = computed(() => {
  const it = cur.value.item as LItem;
  if (typeof it.answer === "number" && it.options) return `${String.fromCharCode(65 + it.answer)}. ${it.options[it.answer]}`;
  return String(it.answer);
});
const done = computed(() => cursor.value + (judged.value ? 1 : 0));

onMounted(async () => {
  const d = await loadListening();
  loaded = true;
  const today = new Date().toISOString().slice(0, 10);
  const map = new Map<string, { item: LItem; book: string; partNo: number }>();
  for (const t of d.tests) {
    for (const p of t.parts) {
      for (const it of p.items) {
        map.set(mistakeKey(t.book, p.part, it.no), { item: it, book: t.book, partNo: p.part });
      }
    }
  }
  const due = learning.data.mistakes
    .filter((m) => m.word_id.startsWith("listen:") && m.due_at <= today)
    .map((m) => ({ key: m.word_id, info: map.get(m.word_id) }))
    .filter((x) => !!x.info) as { key: string; info: { item: LItem; book: string; partNo: number } }[];
  jobs.value = due.map((x) => ({ key: x.key, item: x.info.item, book: x.info.book, partNo: x.info.partNo }));
});

function pickChoice(oi: number): void {
  if (!loaded || judged.value) return;
  pick.value = oi;
  judge(oi === cur.value.item?.answer);
}
function submitFill(): void {
  if (!loaded || judged.value || !fillInput.value.trim()) return;
  judge(isFillCorrect(fillInput.value, String(cur.value.item?.answer ?? "")));
}
function judge(ok: boolean): void {
  judged.value = ok ? "right" : "wrong";
  const j = jobs.value[cursor.value];
  if (!j) return;
  if (ok) learning.recordRight(j.key, "q");
  else learning.recordWrong(j.key, ["q"]);
}
function next(): void {
  if (cursor.value >= jobs.value.length - 1) { back(); return; }
  cursor.value++;
  pick.value = null;
  fillInput.value = "";
  judged.value = null;
}
function back(): void {
  void router.push("/english/listening");
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.empty { padding: 40px; text-align: center; color: var(--c-text-2); }
.q { padding: 16px; }
.q.right { border-color: var(--c-primary); }
.q.wrong { border-color: var(--c-danger); }
.q-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.qno {
  background: var(--c-primary); color: #fff; border-radius: 50%;
  min-width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center;
  font-size: var(--fs-sub); font-weight: 700;
}
.qstem { color: var(--c-text); }
.qimg { max-width: 100%; border-radius: var(--r-sm); margin-bottom: 10px; }
.fill-input {
  width: 100%; min-height: 44px; border: 1px solid var(--c-border); border-radius: var(--r-sm);
  padding: 8px 12px; font-size: var(--fs-body);
}
.opt {
  display: flex; align-items: center; gap: 10px; width: 100%;
  background: var(--c-bg-mint); border: 1px solid var(--c-border); border-radius: var(--r-sm);
  padding: 10px 12px; margin-bottom: 6px; cursor: pointer; text-align: left; min-height: 44px;
}
.opt.picked { border-color: var(--c-primary); }
.opt.correct { border-color: var(--c-primary); background: var(--c-primary-soft); }
.opt.wrongPick { border-color: var(--c-danger); background: var(--c-danger-soft); }
.opt-key { font-weight: 700; color: var(--c-primary); }
.opt-img { max-height: 120px; border-radius: var(--r-sm); }
.opt-text { color: var(--c-text); }
.feedback { margin-top: 10px; font-weight: 600; }
.feedback .ok { color: var(--c-primary); }
.feedback .no { color: var(--c-danger); }
.actions { margin: 14px 0 40px; display: flex; align-items: center; gap: 12px; }
.count { color: var(--c-text-2); font-size: var(--fs-sub); }
</style>
