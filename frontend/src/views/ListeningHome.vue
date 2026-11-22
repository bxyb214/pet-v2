<template>
  <main class="page">
    <h1>听力</h1>
    <p class="sub">官方真题 · 听音频 → 答题 → 提交判分（错题自动进错题本）</p>

    <n-alert v-if="dueCount" type="warning" :bordered="false" class="mistake-bar" @click="goReview">
      🔁 到期错题 {{ dueCount }} 题 · 点击复习
    </n-alert>

    <div v-if="!data" class="empty card">加载中…</div>
    <template v-else>
      <section v-for="b in data.books" :key="b.id" class="book">
        <button class="book-head" :aria-expanded="!!openMap[b.id]" @click="toggle(b.id)">
          <svg class="chev" :class="{ open: openMap[b.id] }" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6" /></svg>
          <span class="book-name">{{ b.name }}</span>
          <span class="book-desc">{{ b.desc }}</span>
          <span class="fold-act">{{ openMap[b.id] ? "收起" : "展开" }}</span>
        </button>
        <div class="book-b" :class="{ open: openMap[b.id] }">
          <div class="book-inner">
            <div v-for="t in testsOf(b.id)" :key="t.no" class="test-card card">
              <div class="test-head">
                <span class="test-title">{{ t.title }}</span>
                <span class="dur">{{ fmtDur(t.duration) }}</span>
              </div>
              <div class="part-list">
                <button
                  v-for="p in t.parts" :key="p.part"
                  class="part-row"
                  :class="{ done: isDone(t, p) }"
                  @click="goPart(t.no, p.part)"
                >
                  <span class="pcheck" :class="{ on: isDone(t, p) }">{{ isDone(t, p) ? "✓" : "" }}</span>
                  <span class="plabel">Part {{ p.part }} · {{ p.label || p.kind }}</span>
                  <span class="pmeta">{{ p.qRange }} · {{ p.items.length }} 题</span>
                  <svg class="pgo" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6" /></svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { NAlert } from "naive-ui";
import { useLearningStore } from "../stores/learning";
import { loadListening, progressKey, type ListeningData, type LPart, type LTest } from "../core/listening";

const router = useRouter();
const learning = useLearningStore();
const data = ref<ListeningData | null>(null);
const openMap = reactive<Record<string, boolean>>({});

onMounted(async () => {
  const d = await loadListening();
  data.value = d;
  // 单本教材默认展开（05 规范）
  if (d.books.length === 1) openMap[d.books[0].id] = true;
});

function toggle(id: string): void {
  openMap[id] = !openMap[id];
}
function testsOf(bookId: string): LTest[] {
  return (data.value?.tests ?? []).filter((t) => t.book === bookId);
}
function isDone(t: LTest, p: LPart): boolean {
  const rec = learning.progressOf(progressKey(t.book, t.no, p.part));
  return !!rec && rec.seen.length > 0;
}
function goPart(no: number, part: number): void {
  void router.push(`/english/listening/${no}/${part}`);
}
function goReview(): void {
  void router.push("/english/listening/review");
}
function fmtDur(sec: number): string {
  const m = Math.round(sec / 60);
  return `约 ${m} 分钟`;
}
const dueCount = computed(() => {
  const today = new Date().toISOString().slice(0, 10);
  return learning.data.mistakes.filter((m) => m.word_id.startsWith("listen:") && m.due_at <= today).length;
});
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-display); margin: 0 0 6px; }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 18px; }
.mistake-bar {
  background: var(--c-accent-soft, #fffbeb); color: var(--c-accent); border-radius: var(--r-md);
  padding: 12px 16px; margin-bottom: 16px; cursor: pointer; font-weight: 600;
}
.book { margin-bottom: 14px; }
.book-head {
  display: flex; align-items: center; gap: 12px; width: 100%;
  background: var(--c-surface); border: 1px solid var(--c-line); border-radius: var(--r-card);
  padding: 14px 16px; cursor: pointer; text-align: left; min-height: 60px;
}
.book-head:hover { background: var(--c-mint-bg, #f2faf5); }
.chev { flex: none; color: var(--c-text-2); transition: transform 0.2s ease, color 0.2s; }
.chev.open { transform: rotate(90deg); color: var(--c-primary); }
.book-name { font-weight: 700; color: var(--c-text); font-size: var(--fs-title); white-space: nowrap; }
.book-desc { color: var(--c-text-2); font-size: var(--fs-sub); flex: 1; min-width: 0; }
.fold-act { flex: none; font-size: 13px; font-weight: 700; color: var(--c-primary-strong); background: var(--c-primary-soft); padding: 6px 14px; border-radius: 999px; white-space: nowrap; }
.book-b { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.26s ease; }
.book-b.open { grid-template-rows: 1fr; }
.book-inner { overflow: hidden; min-height: 0; padding: 0 2px; }
.book-b.open .book-inner { padding: 12px 2px 2px; }
.test-card { margin-bottom: 12px; padding: 14px 16px; background: var(--c-surface); border: 1px solid var(--c-line); border-radius: var(--r-card); }
.test-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
.test-title { font-weight: 700; color: var(--c-text); font-size: var(--fs-body); }
.dur { font-weight: 400; color: var(--c-text-2); font-size: var(--fs-sub); }
.part-list { display: flex; flex-direction: column; gap: 6px; }
.part-row {
  display: flex; align-items: center; gap: 10px; width: 100%;
  background: var(--c-mint-bg, #f6faf7); border: 1px solid transparent; border-radius: 10px;
  padding: 10px 12px; cursor: pointer; text-align: left; min-height: 48px;
  font: inherit; color: var(--c-text); transition: background 0.15s, border-color 0.15s;
}
.part-row:hover { background: var(--c-primary-soft); border-color: color-mix(in srgb, var(--c-primary) 30%, transparent); }
.part-row.done { background: var(--c-primary-soft, #e7f6ec); }
.pcheck { width: 20px; height: 20px; border-radius: 50%; border: 1.5px solid var(--c-line); display: inline-flex; align-items: center; justify-content: center; font-size: 12px; color: #fff; flex: none; }
.pcheck.on { background: var(--c-primary); border-color: var(--c-primary); }
.plabel { flex: 1; min-width: 0; font-weight: 600; font-size: 15px; }
.pmeta { color: var(--c-text-2); font-size: var(--fs-sub); white-space: nowrap; }
.pgo { color: var(--c-text-2); flex: none; }
.empty { padding: 40px; text-align: center; color: var(--c-text-2); }

@media (max-width: 767px) {
  .book-desc { display: none; }
  .pmeta { display: none; }
  .part-row { min-height: 48px; }
}
</style>
