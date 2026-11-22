<template>
  <main class="page" v-if="ready">
    <!-- 结果页 -->
    <template v-if="finished">
      <section class="card done-card">
        <p class="title">本轮完成！</p>
        <p class="sub">答对 {{ correct }} / {{ items.length }} 题</p>
        <div class="actions">
          <button class="btn" @click="restart">再来一轮</button>
          <button class="ghost" @click="back">返回阅读</button>
        </div>
      </section>
    </template>

    <!-- 答题页 -->
    <template v-else-if="q">
      <div class="topbar">
        <button class="ghost" @click="back">退出</button>
        <p class="label">{{ label }}</p>
        <span class="pos">{{ idx + 1 }} / {{ items.length }}</span>
      </div>
      <div class="bar"><i :style="{ width: ((idx + 1) / items.length) * 100 + '%' }"></i></div>

      <section class="card">
        <p class="dimlabel">{{ TYPE_LABEL[q.type] }}</p>
        <p class="prompt">{{ q.prompt }}</p>

        <div v-if="!answered" class="answers">
          <button
            v-for="(o, i) in q.options"
            :key="i"
            class="optcard"
            @click="submit(i)"
          ><span class="key">{{ "ABCD"[i] }}</span>{{ o.label }}</button>
        </div>

        <!-- 反馈区：答题后才给听整句（朗读红线） -->
        <div v-else class="feedback" :class="lastCorrect ? 'ok' : 'bad'">
          <p class="fbtitle">{{ lastCorrect ? "✓ 答对了！" : "正确答案：" + correctLabel }}</p>
          <p v-if="!lastCorrect && q.type === 'grammar' && q.q?.why" class="fbwhy">{{ q.q.why }}</p>
          <p v-if="!lastCorrect && q.type !== 'grammar'" class="fbsent">{{ q.s.en }}</p>
          <p v-if="q.type !== 'meaning'" class="fbcn">{{ q.s.cn }}</p>
          <button class="audiobtn" @click="speak(q.s.en)">🔊 听整句</button>
          <button class="btn nextbtn" @click="next">下一题</button>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useLearningStore } from "../stores/learning";
import {
  buildQuizItems, grammarIndex, itemForDim, loadReading, speak, withCustomSentences,
  type QuizItem, type RSentence,
} from "../core/reading";
import { partKey, readingDayOf, type ReadingPartRef } from "../core/plan";

const TYPE_LABEL: Record<string, string> = { meaning: "读懂句意", blank: "选词填空", grammar: "语法选择" };

const route = useRoute();
const router = useRouter();
const learning = useLearningStore();

const ready = ref(false);
const items = ref<QuizItem[]>([]);
const idx = ref(0);
const answered = ref(false);
const lastCorrect = ref(false);
const finished = ref(false);
const correct = ref(0);
const label = ref("");
const progressKey = ref("");
const partRef = ref<ReadingPartRef | null>(null);

const q = computed(() => items.value[idx.value] ?? null);
const correctLabel = computed(() => q.value?.options.find((o) => o.correct)?.label ?? "");

const today = new Date().toISOString().slice(0, 10);

function dueDims(s: RSentence): string[] {
  const m = learning.data.mistakes.find((x) => x.word_id === s.id);
  if (!m || !m.dims.length || !m.due_at || m.due_at > today) return [];
  return m.dims;
}

function reviewItems(sentences: RSentence[], pool: RSentence[]): QuizItem[] {
  const out: QuizItem[] = [];
  for (const s of sentences) {
    for (const dim of dueDims(s)) {
      const it = itemForDim(s, dim, pool);
      if (it) out.push(it);
    }
  }
  return out;
}

onMounted(async () => {
  const base = await loadReading();
  const d = withCustomSentences(base, learning.data.custom_sentences);
  const allSentences = d.tests.flatMap((x) => x.parts.flatMap((p) => p.sentences));
  const testNo = Number(route.params.testNo);
  const gc = route.query.gc ? Number(route.query.gc) : null;
  const review = route.query.review === "1";

  if (review) {
    // R8 错题复习：只考欠的维度
    items.value = reviewItems(allSentences, allSentences);
    label.value = "阅读错题复习（只考欠的维度）";
  } else if (gc != null) {
    // 语法专项
    const pool = grammarIndex(d.tests)[gc] ?? [];
    items.value = pool.slice(0, 20);
    label.value = `语法专项 · ${route.query.label ?? "考点 " + gc}（20 题上限）`;
  } else {
    const t = d.tests.find((x) => x.no === testNo);
    if (!t) { ready.value = true; return; }
    const partQ = route.query.part ? Number(route.query.part) : 0;
    const sentences: RSentence[] = partQ
      ? (t.parts.find((p) => p.part === partQ)?.sentences ?? [])
      : t.parts.flatMap((p) => p.sentences);
    // R8 错题优先：到期错题（只考欠的维度）排前面，其余题照常
    const rev = reviewItems(sentences, allSentences);
    const rest = buildQuizItems(sentences, allSentences);
    items.value = [...rev, ...rest];
    label.value = `${t.title}${partQ ? " · Part " + partQ : " · 全套"}${rev.length ? `（含 ${rev.length} 道错题）` : ""}`;
    progressKey.value = `read:${t.book || "t2"}:${t.no}:${partQ || "all"}`;
    if (partQ) partRef.value = { book: t.book || "t2", testNo: t.no, part: partQ };
  }
  ready.value = true;
});

/** 当前题对应句子上的错题维度键 */
function dimOf(item: QuizItem): string {
  if (item.type === "grammar" && item.q) {
    const i = item.s.gq.indexOf(item.q);
    return `grammar:g${i >= 0 ? i : 0}`;
  }
  return item.type; // meaning / blank
}

function submit(i: number): void {
  if (!q.value || answered.value) return;
  answered.value = true;
  lastCorrect.value = q.value.options[i].correct;
  const dim = dimOf(q.value);
  if (lastCorrect.value) {
    correct.value += 1;
    learning.recordRight(q.value.s.id, dim); // 错题本划维度（不在错题本时无副作用）
  } else {
    learning.recordWrong(q.value.s.id, [dim]); // 该维度重欠 + 回 1 天间隔（R8）
  }
}

function next(): void {
  if (idx.value >= items.value.length - 1) {
    finished.value = true;
    finishBookkeeping();
    return;
  }
  idx.value += 1;
  answered.value = false;
}

function finishBookkeeping(): void {
  if (correct.value < items.value.length * 0.6) return;
  // R6 测验完成进度
  if (progressKey.value) learning.recordProgress(progressKey.value);
  // R9 阅读计划打勾：Part 测验达标 → 反查所属天
  if (partRef.value && learning.data.plan.reading_length > 0) {
    const parts: ReadingPartRef[] = [];
    // 与 PlanPage 同序：按 reading.json tests 顺序展开（loadReading 缓存即同源）
    void loadReading().then((d) => {
      for (const t of d.tests) for (const p of t.parts) parts.push({ book: t.book || "t2", testNo: t.no, part: p.part });
      const quota = Math.ceil(parts.length / learning.data.plan.reading_length);
      let acc = 0;
      for (let day = 1; day <= learning.data.plan.reading_length; day++) {
        const slice = parts.slice(acc, acc + quota);
        acc += quota;
        if (slice.some((p) => partKey(p) === partKey(partRef.value!))) {
          learning.markReadingDayDone(day);
          break;
        }
      }
    });
  }
}

function restart(): void {
  idx.value = 0;
  correct.value = 0;
  answered.value = false;
  finished.value = false;
}

function back(): void {
  void router.push("/english/reading");
}
</script>

<style scoped>
.page { width: 100%; }
.topbar { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.label { flex: 1; margin: 0; color: var(--c-text-2); font-size: var(--fs-sub); }
.pos { color: var(--c-text-2); font-size: var(--fs-sub); }
.bar { height: 6px; background: var(--c-line); border-radius: 3px; margin-bottom: 16px; overflow: hidden; }
.bar i { display: block; height: 100%; background: var(--c-primary); transition: width var(--t-med); }
.card { background: var(--c-card); border-radius: var(--r-card); box-shadow: var(--shadow-card); padding: 20px; }
.dimlabel { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 8px; }
.prompt { font-size: var(--fs-body); line-height: 1.7; margin: 0 0 16px; }
.answers { display: grid; gap: 8px; }
.optcard { background: var(--c-card); border: 1px solid var(--c-line); border-radius: var(--r-btn); padding: 13px 16px; font-size: var(--fs-body); min-height: 52px; text-align: left; cursor: pointer; }
.optcard:hover { border-color: var(--c-primary); background: var(--c-primary-soft); }
.key { display: inline-block; width: 24px; color: var(--c-primary-strong); font-weight: 600; }
.feedback { border-radius: var(--r-card); padding: 16px; margin-top: 8px; }
.feedback.ok { background: var(--c-primary-soft); }
.feedback.bad { background: #fef2f2; }
.fbtitle { font-weight: 500; margin: 0 0 6px; font-size: var(--fs-title); }
.ok .fbtitle { color: var(--c-primary-strong); }
.bad .fbtitle { color: var(--c-danger); }
.fbwhy { margin: 0 0 6px; font-size: var(--fs-sub); line-height: 1.6; }
.fbsent { margin: 0 0 4px; font-size: var(--fs-sub); }
.fbcn { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 8px; }
.audiobtn { background: var(--c-primary-soft); color: var(--c-primary-strong); border: 0; border-radius: var(--r-pill); padding: 10px 16px; min-height: 44px; cursor: pointer; }
.nextbtn { float: right; }
.done-card { text-align: center; }
.title { font-size: var(--fs-title); font-weight: 500; margin: 0 0 4px; }
.sub { color: var(--c-text-2); margin: 0 0 16px; }
.actions { display: flex; gap: 10px; justify-content: center; }
.ghost { background: none; border: 0; color: var(--c-primary-strong); font-size: var(--fs-body); min-height: 44px; cursor: pointer; padding: 0 8px; }
</style>
