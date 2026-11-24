<template>
  <main class="page">
    <BackButton to="/math" label="返回课程" />

    <LoadingBlock v-if="loading" />
    <EmptyState
      v-else-if="!book || book.comingSoon || !book.lessons.length"
      title="这个年级的课程还没上线"
      desc="上线后会自动出现在课程首页。"
    >
      <template #action>
        <n-button type="primary" @click="router.push('/math')">返回课程</n-button>
      </template>
    </EmptyState>
    <template v-else>
      <header class="head">
        <span class="grade tnum">{{ book.gradeName }}</span>
        <div class="htxt">
          <h1>{{ courseTitle }}</h1>
          <p class="head-sub">
            {{ book.lessons.length }} 节课 · {{ groups.length }} 个主题 · 看完整节才算学完
          </p>
        </div>
      </header>

      <div class="card overview">
        <div class="ov-num tnum">
          {{ stat.done }}<span class="ov-total">/ {{ stat.total }}</span>
          <span class="ov-label">节已学完</span>
        </div>
        <div class="ov-mid">
          <div class="bar" role="progressbar" :aria-valuenow="stat.percent" aria-valuemin="0" aria-valuemax="100">
            <i :style="{ width: stat.percent + '%' }"></i>
          </div>
          <div class="ov-meta">
            学习中 {{ stat.watching }} 节 · 还没开始 {{ stat.todo }} 节
          </div>
        </div>
        <n-button type="primary" size="large" class="ov-go" @click="continueLearn">
          {{ stat.done === stat.total ? "再学一遍" : "继续学习" }}
        </n-button>
      </div>

      <section v-for="g in groups" :key="g.name" class="group">
        <h2>{{ g.name }}</h2>
        <div class="lessons">
          <button
            v-for="l in g.lessons" :key="l.id" type="button"
            class="lesson-row" @click="open(l)"
          >
            <span class="no tnum">{{ l.no }}</span>
            <span class="lt">
              <b>{{ l.title }}</b>
              <i v-if="l.tag" class="tag">{{ l.tag }}</i>
            </span>
            <span class="state" :class="statusOf(recOf(l.id))">{{ stateText(l.id) }}</span>
            <n-icon :component="ChevronForwardOutline" size="18" class="chev" />
          </button>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NIcon } from "naive-ui";
import { ChevronForwardOutline } from "@vicons/ionicons5";
import BackButton from "../components/BackButton.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import EmptyState from "../components/EmptyState.vue";
import {
  bookProgress, findBook, formatTime, groupsOf, lessonKey, loadMath, nextLesson, statusOf,
  type MathBook, type MathData, type MathLesson, type VideoRec,
} from "../core/math";
import { useLearningStore } from "../stores/learning";

const route = useRoute();
const router = useRouter();
const learning = useLearningStore();
const data = ref<MathData | null>(null);
const loading = ref(true);

const courseTitle = computed(() => data.value?.course.title ?? "李永乐一课通关");
const book = computed<MathBook | null>(() =>
  data.value ? findBook(data.value.books, String(route.params.bookId)) : null,
);
const groups = computed(() => groupsOf(book.value?.lessons ?? []));

function recOf(id: string): VideoRec | null {
  return learning.progressOf(lessonKey(id));
}
const stat = computed(() =>
  book.value ? bookProgress(book.value, recOf) : { total: 0, done: 0, watching: 0, todo: 0, percent: 0 },
);

function stateText(id: string): string {
  const rec = recOf(id);
  const st = statusOf(rec);
  if (st === "done") return "已学完";
  if (st === "watching") return `看到 ${formatTime(rec?.idx ?? 0)}`;
  return "还没看";
}
function open(l: MathLesson): void {
  if (!book.value) return;
  void router.push(`/math/books/${encodeURIComponent(book.value.id)}/${encodeURIComponent(l.id)}`);
}
function continueLearn(): void {
  if (!book.value) return;
  const next = nextLesson(book.value.lessons, recOf) ?? book.value.lessons[0];
  if (next) open(next);
}

onMounted(async () => {
  try {
    data.value = await loadMath();
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page { width: 100%; }
.card {
  background: var(--c-surface); border: 1px solid var(--c-line);
  border-radius: var(--r-card); box-shadow: var(--shadow-card);
}
.empty { padding: 32px 16px; text-align: center; color: var(--c-text-2); }
.empty p { margin: 0 0 14px; }

.head { display: flex; align-items: center; gap: 14px; margin-bottom: 14px; }
.grade {
  flex: none; display: inline-flex; align-items: center; justify-content: center;
  min-width: 86px; height: 62px; padding: 0 14px; border-radius: 16px;
  background: var(--c-primary); color: #fff; font-size: 22px; font-weight: 800;
  letter-spacing: 1px; box-shadow: var(--shadow-1);
}
.htxt { min-width: 0; }
h1 { margin: 0 0 2px; color: var(--c-text); font-size: var(--fs-title); line-height: 1.3; }
.head-sub { margin: 0; color: var(--c-text-2); font-size: var(--fs-sub); }

.overview {
  display: flex; align-items: center; gap: 18px; flex-wrap: wrap;
  padding: 18px 20px; margin-bottom: 20px;
  background: linear-gradient(135deg, var(--c-primary-soft), var(--c-surface) 72%);
}
.ov-num { color: var(--c-primary-strong); font-size: 34px; font-weight: 800; line-height: 1.1; }
.ov-total { color: var(--c-text-2); font-size: 18px; font-weight: 700; margin-left: 2px; }
.ov-label { display: block; color: var(--c-text-2); font-size: 13px; font-weight: 600; margin-top: 2px; }
.ov-mid { flex: 1; min-width: 180px; }
.bar { height: 12px; border-radius: 999px; background: var(--c-line); overflow: hidden; }
.bar i { display: block; height: 100%; border-radius: inherit; background: var(--c-primary); transition: width var(--dur-3) var(--ease-out); }
.ov-meta { color: var(--c-text-2); font-size: var(--fs-sub); margin-top: 8px; }
.ov-go { min-width: 132px; }

.group { margin-bottom: 18px; }
.group h2 {
  font-size: 17px; color: var(--c-text); margin: 0 0 8px 4px;
  display: flex; align-items: center; gap: 8px;
}
.group h2::before { content: ""; width: 6px; height: 18px; border-radius: 3px; background: var(--c-primary); }
.lessons { display: flex; flex-direction: column; gap: 8px; }
.lesson-row {
  display: flex; align-items: center; gap: 12px; width: 100%;
  min-height: 64px; padding: 10px 14px; text-align: left;
  background: var(--c-surface); border: 1px solid var(--c-line);
  border-radius: var(--r-btn); box-shadow: var(--shadow-sm);
  font: inherit; color: var(--c-text); cursor: pointer;
  transition: border-color var(--dur-2) var(--ease-out), background var(--dur-2) var(--ease-out);
}
.lesson-row:hover { border-color: var(--c-primary); background: var(--c-mint-bg); }
.lesson-row:active { transform: scale(0.995); }
.no {
  flex: none; width: 46px; height: 46px; border-radius: 12px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  font-size: 16px; font-weight: 800;
}
.lt { flex: 1; min-width: 0; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.lt b { font-size: 16px; color: var(--c-text); }
.tag {
  font-style: normal; font-size: 12px; font-weight: 700;
  padding: 2px 8px; border-radius: 999px;
  background: var(--c-mint-bg); color: var(--c-text-2); border: 1px solid var(--c-line);
}
.state { flex: none; font-size: 13px; font-weight: 700; padding: 4px 10px; border-radius: 999px; }
.state.todo { background: var(--c-line); color: var(--c-text-2); }
.state.watching { background: var(--c-accent-soft); color: var(--c-accent); }
.state.done { background: var(--c-primary-soft); color: var(--c-primary-strong); }
.chev { color: var(--c-text-3); flex: none; }

@media (max-width: 520px) {
  .grade { min-width: 70px; height: 54px; font-size: 18px; padding: 0 10px; }
  .overview { gap: 12px; padding: 14px; }
  .ov-num { font-size: 28px; }
  .ov-go { width: 100%; }
  .lesson-row { gap: 8px; padding: 8px 10px; }
  .no { width: 40px; height: 40px; font-size: 14px; }
  .state { display: none; }
}
</style>
