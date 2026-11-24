<template>
  <main class="page">
    <header class="head">
      <div>
        <h1>语法专项</h1>
        <p v-if="data" class="sub">
          《{{ data.grammar.book }}》 · {{ data.grammar.days.length }} 天 · {{ pointsTotal }} 个考点 · {{ data.meta.gq }} 道题
        </p>
      </div>
      <div v-if="data" class="headstat">
        <b class="tnum">{{ pointsTotal }}</b>
        <span>考点</span>
      </div>
    </header>

    <section v-if="data" class="card">
      <div class="card-h">
        <div>
          <p class="title">按天过一遍</p>
          <p class="desc">点开一天，选一个考点开始练；练完的考点会累计到错题本的记忆曲线里</p>
        </div>
        <button class="ghost" @click="toggleAllDays">{{ allDaysOpen ? "全部收起" : "全部展开" }}</button>
      </div>

      <div class="gdays">
        <div v-for="d in data.grammar.days" :key="d.day" class="gday">
          <button class="gday-h" :aria-expanded="isDayOpen(d.day)" @click="toggleDay(d.day)">
            <span class="dnum tnum">{{ d.day }}</span>
            <span class="dname">{{ d.name }}</span>
            <span class="dcnt tnum">{{ d.points.length }} 个考点</span>
            <svg class="chev" :class="{ open: isDayOpen(d.day) }" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M6 9l6 6 6-6" />
            </svg>
          </button>
          <div class="gbody" :class="{ open: isDayOpen(d.day) }">
            <div class="ginner">
              <div class="chips">
                <button
                  v-for="p in d.points"
                  :key="p.c"
                  class="chip"
                  :disabled="!(gIndex[p.c]?.length)"
                  :title="gIndex[p.c]?.length ? `${p.name}（${gIndex[p.c].length} 题）` : '暂无题目'"
                  @click="startGrammar(p.c, p.name)"
                >
                  <span class="cno tnum">{{ p.c }}</span>
                  <span class="cname">{{ p.name }}</span>
                  <span v-if="gIndex[p.c]?.length" class="ccnt tnum">{{ gIndex[p.c].length }} 题</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <LoadingBlock v-else plain text="正在加载语法要点…" />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { useLearningStore } from "../stores/learning";
import LoadingBlock from "../components/LoadingBlock.vue";
import {
  grammarIndex, loadReading, withCustomSentences, type ReadingData,
} from "../core/reading";

const router = useRouter();
const learning = useLearningStore();
const data = ref<ReadingData | null>(null);

/** 只展开一天，默认上次看的那天 */
const DAY_KEY = "pet_grammar_day";
const lastDay = Number(localStorage.getItem(DAY_KEY) ?? "1");
const openDays = reactive<Record<number, boolean>>({
  [Number.isFinite(lastDay) && lastDay > 0 ? lastDay : 1]: true,
});

const pointsTotal = computed(() =>
  (data.value?.grammar.days ?? []).reduce((n, d) => n + d.points.length, 0),
);
const allDaysOpen = computed(() => {
  const days = data.value?.grammar.days ?? [];
  return days.length > 0 && days.every((d) => openDays[d.day]);
});

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
function toggleAllDays(): void {
  const next = !allDaysOpen.value;
  for (const d of data.value?.grammar.days ?? []) openDays[d.day] = next;
}

onMounted(async () => {
  const base = await loadReading();
  data.value = withCustomSentences(base, learning.data.custom_sentences);
});

const gIndex = computed(() => grammarIndex(data.value?.tests ?? []));

function startGrammar(c: number, name: string): void {
  void router.push({ path: "/english/reading/quiz/0", query: { gc: String(c), label: name } });
}
</script>

<style scoped>
.page { width: 100%; }

.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
h1 {
  margin: 0 0 4px;
  font-size: var(--fs-display);
  font-weight: 800;
  letter-spacing: 0.2px;
  color: var(--c-text);
}
.sub { margin: 0; font-size: 13px; color: var(--c-text-2); line-height: 1.6; }
.headstat {
  display: flex; align-items: baseline; gap: 5px;
  padding: 6px 12px; border-radius: var(--r-pill);
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  white-space: nowrap;
}
.headstat b { font-size: 18px; font-weight: 800; }
.headstat span { font-size: 12px; }

.card {
  background: var(--c-card);
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  padding: 16px 18px 8px;
}
.card-h {
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 12px; margin-bottom: 8px;
}
.title { margin: 0 0 3px; font-size: 15px; font-weight: 800; color: var(--c-text); }
.desc { margin: 0; font-size: 12.5px; color: var(--c-text-2); line-height: 1.6; }
.ghost {
  flex: none;
  background: none; border: 1px solid var(--c-line);
  color: var(--c-text-2); font-size: 12.5px; font-weight: 600;
  padding: 6px 12px; border-radius: var(--r-pill); cursor: pointer;
  transition: border-color var(--dur-2) var(--ease-out), color var(--dur-2) var(--ease-out);
}
.ghost:hover { border-color: #a9dcc0; color: var(--c-primary-strong); }

/* ---------- 天 ---------- */
.gdays { display: flex; flex-direction: column; }
.gday + .gday { border-top: 1px solid var(--c-line); }
.gday-h {
  display: flex; align-items: center; gap: 12px;
  width: 100%; padding: 12px 6px; min-height: 56px;
  background: none; border: 0; cursor: pointer; text-align: left; font: inherit;
  border-radius: var(--r-sm);
  transition: background var(--dur-2) var(--ease-out);
}
.gday-h:hover { background: var(--c-mint-bg); }

/* 日号做成小方块，和计划墙的格子呼应 */
.dnum {
  flex: none;
  width: 30px; height: 30px; border-radius: 9px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  font-size: 13px; font-weight: 800;
}
.dname { flex: 1; min-width: 0; font-size: 15px; font-weight: 700; color: var(--c-text); }
.dcnt { font-size: 12.5px; color: var(--c-text-3); white-space: nowrap; }
.chev { flex: none; color: var(--c-text-3); transition: transform var(--dur-2) var(--ease-out); }
.chev.open { transform: rotate(180deg); color: var(--c-primary); }

.gbody { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.24s var(--ease-out); }
.gbody.open { grid-template-rows: 1fr; }
.ginner { overflow: hidden; min-height: 0; }
.gbody.open .ginner { padding: 2px 0 14px 42px; }

/* ---------- 考点 ---------- */
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  display: inline-flex; align-items: center; gap: 7px;
  background: #fff;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  padding: 7px 12px 7px 8px;
  font-size: 13px; color: var(--c-text);
  cursor: pointer; min-height: 40px;
  transition: border-color var(--dur-2) var(--ease-out),
    background var(--dur-2) var(--ease-out), transform var(--dur-1) var(--ease-out);
}
.chip:hover:not(:disabled) {
  border-color: #a9dcc0; background: #fbfefc; transform: translateY(-1px);
}
.cno {
  flex: none;
  min-width: 21px; height: 21px; padding: 0 5px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 6px;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  font-size: 11px; font-weight: 800;
}
.cname { line-height: 1.4; }
.ccnt {
  font-size: 11px; color: var(--c-text-3);
  background: #f4f8f6; border-radius: var(--r-pill); padding: 1px 6px;
}
.chip:disabled { opacity: 0.4; cursor: not-allowed; }

.loading { color: var(--c-text-2); font-size: 13px; padding: 24px 4px; }

@media (max-width: 767px) {
  h1 { font-size: 22px; }
  .headstat { display: none; }
  .card { padding: 14px 12px 6px; }
  .card-h { flex-direction: column; align-items: stretch; }
  .ghost { align-self: flex-start; }
  .dnum { width: 26px; height: 26px; border-radius: 8px; font-size: 12px; }
  .dname { font-size: 14px; }
  .dcnt { display: none; }
  .gbody.open .ginner { padding-left: 0; }
  .chip { font-size: 12.5px; }
}
</style>
