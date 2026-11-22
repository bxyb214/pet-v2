<template>
  <main class="page">
    <h1>阅读精读</h1>
    <p class="sub" v-if="data">{{ data.meta.sentences }} 句 · {{ data.meta.gq }} 道语法题 · 考点覆盖 {{ data.meta.points_covered }}/42</p>

    <!-- 错题复习入口 -->
    <n-alert v-if="dueCount" type="warning" class="review-card" :bordered="false">
      <div class="card-h">
        <span>📖 阅读错题复习 · <b>{{ dueCount }}</b> 题维度到期</span>
        <n-button type="warning" size="small" @click="startReview">开始复习</n-button>
      </div>
    </n-alert>

    <!-- 阅读计划（从单词计划页迁来，属于阅读板块） -->
    <ReadingPlanCard class="plan-card" />

    <!-- 语法专项：10 天手风琴，默认只展开一天 -->
    <section v-if="data" class="card">
      <div class="card-h">
        <div>
          <p class="title">语法专项 · 按考点</p>
          <p class="desc">《{{ data.grammar.book }}》 · 10 天 · {{ data.meta.points_covered }} 个考点</p>
        </div>
        <n-button size="small" quaternary @click="toggleAllDays">{{ allDaysOpen ? "全部收起" : "全部展开" }}</n-button>
      </div>
      <div class="gdays">
        <div v-for="d in data.grammar.days" :key="d.day" class="gday">
          <button class="gday-h" :aria-expanded="isDayOpen(d.day)" @click="toggleDay(d.day)">
            <svg class="chev" :class="{ open: isDayOpen(d.day) }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6" /></svg>
            <b class="gday-n">DAY {{ d.day }}</b>
            <span class="gday-name">{{ d.name }}</span>
            <span class="gday-cnt">{{ d.points.length }} 个考点</span>
            <span class="gday-act">{{ isDayOpen(d.day) ? "收起" : "展开" }}</span>
          </button>
          <div class="gbody" :class="{ open: isDayOpen(d.day) }">
            <div class="ginner">
              <div class="chips">
                <button
                  v-for="p in d.points"
                  :key="p.c"
                  class="chip"
                  :disabled="!(gIndex[p.c]?.length)"
                  :title="gIndex[p.c]?.length ? `${p.name}（${gIndex[p.c].length} 题）` : '暂无题'"
                  @click="startGrammar(p.c, p.name)"
                ><b>{{ p.c }}</b>{{ p.name }}<i v-if="gIndex[p.c]?.length">{{ gIndex[p.c].length }}</i></button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 教材分组 -->
    <section v-for="b in bookGroups" :key="b.id" class="fold">
      <button class="fold-h" :aria-expanded="!!openMap[b.id]" @click="toggle(b.id)">
        <svg class="chev" :class="{ open: openMap[b.id] }" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6" /></svg>
        <span class="fold-t">
          <b>{{ b.name }}</b>
          <span class="desc">{{ b.desc }}</span>
        </span>
        <span class="meta">{{ b.testCount }} 套 · {{ b.sentCount }} 句</span>
        <span class="fold-act">{{ openMap[b.id] ? "收起" : "展开" }}</span>
      </button>
      <div class="fold-b" :class="{ open: openMap[b.id] }">
        <div class="fold-inner">
          <div v-for="t in b.tests" :key="t.no" class="card testcard">
            <div class="card-h">
              <div>
                <p class="title">{{ t.title }} <span class="muted">· {{ testSentences(t).length }} 句</span></p>
                <p v-if="t.note" class="desc">{{ t.note }}</p>
              </div>
              <n-button type="primary" size="small" @click="startQuiz(t.no, 0)">测整套</n-button>
            </div>
            <div class="parts">
              <n-button v-for="p in t.parts" :key="p.part" secondary size="small" @click="startStudy(t.no, p.part)">
                Part {{ p.part }} · {{ p.kind }}
              </n-button>
              <n-button v-for="p in t.parts" :key="'q' + p.part" quaternary size="small" @click="startQuiz(t.no, p.part)">
                测 Part {{ p.part }}
              </n-button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 加句：操作入口放浮动按钮，不占页签 -->
    <router-link to="/english/reading/add" class="fab">＋ 加句</router-link>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { NAlert, NButton } from "naive-ui";
import ReadingPlanCard from "../components/ReadingPlanCard.vue";
import { useLearningStore } from "../stores/learning";
import {
  grammarIndex, loadReading, testSentences, withCustomSentences,
  type ReadingData, type RTest,
} from "../core/reading";

const router = useRouter();
const learning = useLearningStore();
const data = ref<ReadingData | null>(null);
const openMap = reactive<Record<string, boolean>>({});
/** 语法专项手风琴：只展开一天，默认上次看的那天 */
const DAY_KEY = "pet_grammar_day";
const lastDay = Number(localStorage.getItem(DAY_KEY) ?? "1");
const openDays = reactive<Record<number, boolean>>({ [Number.isFinite(lastDay) && lastDay > 0 ? lastDay : 1]: true });

function isDayOpen(day: number): boolean {
  return !!openDays[day];
}
function toggleDay(day: number): void {
  const willOpen = !openDays[day];
  for (const k of Object.keys(openDays)) openDays[Number(k)] = false;
  if (willOpen) {
    openDays[day] = true;
    localStorage.setItem(DAY_KEY, String(day));
  }
}
const allDaysOpen = computed(() => {
  const days = data.value?.grammar.days ?? [];
  return days.length > 0 && days.every((d) => openDays[d.day]);
});
function toggleAllDays(): void {
  const days = data.value?.grammar.days ?? [];
  const next = !allDaysOpen.value;
  for (const d of days) openDays[d.day] = next;
}

onMounted(async () => {
  const base = await loadReading();
  data.value = withCustomSentences(base, learning.data.custom_sentences);
  // 只有 1 本书时默认展开，多本默认收起（05 规范）
  const books = data.value.books.filter((b) => data.value!.tests.some((t) => (t.book || "t2") === b.id));
  if (books.length === 1) openMap[books[0].id] = true;
});

// R8 到期错题数（按句子维度）
const dueCount = computed(() => {
  const today = new Date().toISOString().slice(0, 10);
  return learning.data.mistakes.filter((m) => m.dims.length && m.due_at && m.due_at <= today).length;
});

function startReview(): void {
  void router.push({ path: "/english/reading/quiz/0", query: { review: "1" } });
}

const gIndex = computed(() => grammarIndex(data.value?.tests ?? []));

const bookGroups = computed(() => {
  const d = data.value;
  if (!d) return [];
  return d.books
    .filter((b) => d.tests.some((t) => (t.book || "t2") === b.id))
    .map((b) => {
      const tests = d.tests.filter((t) => (t.book || "t2") === b.id);
      return {
        ...b, tests,
        testCount: tests.length,
        sentCount: tests.reduce((a, t) => a + testSentences(t).length, 0),
      };
    });
});

function toggle(id: string): void {
  openMap[id] = !openMap[id];
}

function startStudy(testNo: number, part: number): void {
  void router.push(`/english/reading/study/${testNo}/${part}`);
}

function startQuiz(testNo: number, part: number): void {
  void router.push({ path: `/english/reading/quiz/${testNo}`, query: part ? { part: String(part) } : {} });
}

function startGrammar(c: number, name: string): void {
  void router.push({ path: `/english/reading/quiz/0`, query: { gc: String(c), label: name } });
}
</script>

<style scoped>
.page { width: 100%; }
h1 { font-size: var(--fs-display); color: var(--c-primary-strong); margin-bottom: 4px; }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 16px; }
.review-card { margin-bottom: 14px; }
.review-card .card-h { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.card { background: var(--c-card); border-radius: var(--r-card); box-shadow: var(--shadow-card); padding: 16px; margin-bottom: 14px; }
.card-h { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.title { font-size: var(--fs-title); font-weight: 500; margin: 0 0 2px; }
.muted { color: var(--c-text-2); font-weight: 400; font-size: var(--fs-sub); }
.desc { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0; }
.btn { background: var(--c-primary); color: #fff; border: 0; border-radius: var(--r-btn); padding: 10px 18px; font-size: var(--fs-body); min-height: 44px; cursor: pointer; white-space: nowrap; }
.gdays { display: flex; flex-direction: column; }
.gday + .gday { border-top: 1px solid var(--c-line); }
.gday-h {
  display: flex; align-items: center; gap: 10px; width: 100%; padding: 12px 4px; background: none;
  border: 0; cursor: pointer; text-align: left; min-height: 48px; font: inherit;
}
.gday-h:hover { background: var(--c-mint-bg, #f2faf5); border-radius: 8px; }
.gday-n { font-size: 13.5px; color: var(--c-primary-strong); letter-spacing: .5px; flex: none; width: 62px; }
.gday-name { font-size: 15px; font-weight: 600; color: var(--c-text); flex: 1; min-width: 0; }
.gday-cnt { font-size: 13px; color: var(--c-text-2); white-space: nowrap; }
.gday-act { font-size: 13px; color: var(--c-primary-strong); background: var(--c-primary-soft); padding: 4px 12px; border-radius: 999px; white-space: nowrap; }
.gbody { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .24s ease; }
.gbody.open { grid-template-rows: 1fr; }
.ginner { overflow: hidden; min-height: 0; }
.gbody.open .ginner { padding: 2px 0 12px 72px; }
@media (max-width: 767px) {
  .gday-name { font-size: 14px; }
  .gday-cnt { display: none; }
  .gbody.open .ginner { padding-left: 0; }
}

/* 悬浮「加句」入口（加句是操作，不占页签） */
.fab {
  position: fixed; right: 26px; bottom: 30px; z-index: 15;
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--c-primary); color: #fff; text-decoration: none;
  padding: 12px 18px; border-radius: 999px; font-weight: 700; font-size: 14.5px;
  box-shadow: 0 8px 22px rgba(22, 163, 74, 0.28);
}
.fab:hover { background: var(--c-primary-strong); }
@media (max-width: 767px) {
  .fab { right: 14px; bottom: 16px; padding: 10px 14px; font-size: 14px; }
  .page { padding-bottom: 56px; }
}
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { background: var(--c-primary-soft); color: var(--c-primary-strong); border: 0; border-radius: var(--r-pill); padding: 7px 12px; font-size: var(--fs-sub); cursor: pointer; }
.chip b { margin-right: 4px; }
.chip i { font-style: normal; margin-left: 4px; opacity: 0.7; }
.chip:disabled { opacity: 0.35; cursor: not-allowed; }
.plan-card { margin-bottom: 14px; }
.fold { border: 1px solid var(--c-line); border-radius: var(--r-card); margin-bottom: 14px; background: var(--c-card); overflow: hidden; }
.fold-h { display: flex; align-items: center; gap: 12px; width: 100%; padding: 14px 16px; background: none; border: 0; cursor: pointer; text-align: left; min-height: 60px; }
.fold-h:hover { background: var(--c-mint-bg, #f2faf5); }
.chev { flex: none; color: var(--c-text-2); transition: transform 0.2s ease, color 0.2s; }
.chev.open { transform: rotate(90deg); color: var(--c-primary); }
.fold-t { flex: 1; min-width: 0; }
.fold-t b { font-size: var(--fs-title); display: block; }
.fold-t .desc { display: block; }
.meta { color: var(--c-text-2); font-size: var(--fs-sub); white-space: nowrap; }
.fold-act { flex: none; font-size: 13px; font-weight: 700; color: var(--c-primary-strong); background: var(--c-primary-soft); padding: 6px 14px; border-radius: 999px; white-space: nowrap; }
.fold-b { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.26s ease; }
.fold-b.open { grid-template-rows: 1fr; }
.fold-inner { overflow: hidden; min-height: 0; padding: 0 16px; }
.fold-b.open .fold-inner { padding-bottom: 16px; }
.testcard { box-shadow: none; border: 1px solid var(--c-line); }
.parts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.partbtn { background: var(--c-primary-soft); color: var(--c-primary-strong); border: 0; border-radius: var(--r-pill); padding: 9px 14px; font-size: var(--fs-sub); min-height: 44px; cursor: pointer; }
.partbtn.quiz { background: var(--c-card); border: 1px solid var(--c-line); color: var(--c-text-1); }
</style>
