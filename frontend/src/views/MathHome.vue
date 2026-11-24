<template>
  <main class="page">
    <h1>{{ course?.title ?? "李永乐 · 一课通关" }}</h1>
    <p class="sub">{{ course?.desc ?? "小学数学思维课，按年级分册。" }}</p>

    <LoadingBlock v-if="loading" />
    <EmptyState
      v-else-if="!available.length"
      title="暂时没有已上线的教材"
      desc="新年级上线后会自动出现在这里。"
    />
    <template v-else>
      <section v-for="b in available" :key="b.id" class="featured card">
        <div class="f-main">
          <n-tag type="success" size="small" round :bordered="false">已上线</n-tag>
          <div class="f-grade">
            <b>{{ b.gradeName }}</b>
            <span>数学思维</span>
          </div>
          <p class="f-desc">
            {{ b.lessons.length }} 节课 · {{ groupsOf(b.lessons).length }} 个主题 · 看完整节才算学完
          </p>
          <div class="chips">
            <span v-for="g in groupsOf(b.lessons)" :key="g.name" class="chip">
              {{ g.name }} <i class="tnum">{{ g.lessons.length }}</i>
            </span>
          </div>
        </div>

        <div class="f-side">
          <div class="f-stat tnum">
            <b>{{ statOf(b).done }}</b><span>/ {{ statOf(b).total }} 节已学完</span>
          </div>
          <div class="bar" role="progressbar" :aria-valuenow="statOf(b).percent" aria-valuemin="0" aria-valuemax="100">
            <i :style="{ width: statOf(b).percent + '%' }"></i>
          </div>
          <p class="f-meta">学习中 {{ statOf(b).watching }} 节 · 还没开始 {{ statOf(b).todo }} 节</p>
          <n-button type="primary" size="large" block class="f-go" @click="continueLearn(b)">
            {{ goLabel(b) }}
          </n-button>
          <n-button secondary size="large" block @click="openBook(b)">
            查看 {{ b.lessons.length }} 节课
          </n-button>
        </div>
      </section>

      <section v-if="soon.length" class="other">
        <h2>后续年级</h2>
        <p class="other-hint">视频上传后会自动出现在这里，进度按年级分别记录。</p>
        <div class="soon-row">
          <div v-for="b in soon" :key="b.id" class="soon-card">
            <b>{{ b.gradeName }}</b>
            <span>即将上线</span>
          </div>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NTag } from "naive-ui";
import {
  availableBooks, bookProgress, groupsOf, lessonKey, loadMath, nextLesson,
  type MathBook, type MathData, type VideoRec,
} from "../core/math";
import { useLearningStore } from "../stores/learning";
import LoadingBlock from "../components/LoadingBlock.vue";
import EmptyState from "../components/EmptyState.vue";

const router = useRouter();
const learning = useLearningStore();
const data = ref<MathData | null>(null);
const loading = ref(true);

const course = computed(() => data.value?.course ?? null);
const books = computed<MathBook[]>(() => data.value?.books ?? []);
/** 每个已上线年级一张大卡（三、四年级都上线后并排展示，五年级仍为占位） */
const available = computed(() => availableBooks(books.value));
const soon = computed(() => books.value.filter((b) => b.comingSoon));

function recOf(id: string): VideoRec | null {
  return learning.progressOf(lessonKey(id));
}
function statOf(b: MathBook) {
  return bookProgress(b, recOf);
}
function goLabel(b: MathBook): string {
  const stat = statOf(b);
  if (!stat.total || stat.done === stat.total) return "再学一遍";
  return stat.done || stat.watching ? "继续学习" : "开始学习";
}

function openBook(b: MathBook): void {
  void router.push(`/math/books/${encodeURIComponent(b.id)}`);
}
function continueLearn(b: MathBook): void {
  const l = nextLesson(b.lessons, recOf);
  if (l) void router.push(`/math/books/${encodeURIComponent(b.id)}/${encodeURIComponent(l.id)}`);
  else openBook(b);
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
h1 { color: var(--c-text); font-size: var(--fs-display); margin: 0 0 4px; }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 16px; }
.card {
  background: var(--c-surface); border: 1px solid var(--c-line);
  border-radius: var(--r-card); box-shadow: var(--shadow-card);
}
.empty { padding: 32px 16px; text-align: center; color: var(--c-text-2); }

.featured {
  display: flex; gap: 24px; flex-wrap: wrap; align-items: stretch;
  padding: 22px 24px; margin-bottom: 22px;
  background: linear-gradient(135deg, var(--c-primary-soft) 0%, var(--c-surface) 62%);
  border-color: var(--c-primary);
}
.f-main { flex: 1 1 340px; min-width: 0; }
.f-grade { display: flex; align-items: baseline; gap: 10px; margin: 8px 0 4px; }
.f-grade b { color: var(--c-primary-strong); font-size: 40px; font-weight: 800; line-height: 1.05; letter-spacing: 1px; }
.f-grade span { color: var(--c-text-2); font-size: 14px; font-weight: 600; }
.f-desc { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 12px; }
.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  font-size: 12px; font-weight: 600; color: var(--c-text-2);
  background: var(--c-surface); border: 1px solid var(--c-line);
  border-radius: 999px; padding: 4px 10px;
}
.chip i { font-style: normal; color: var(--c-primary-strong); font-weight: 800; margin-left: 2px; }

.f-side { flex: 0 1 300px; min-width: 240px; display: flex; flex-direction: column; gap: 8px; justify-content: center; }
.f-stat b { color: var(--c-primary-strong); font-size: 34px; font-weight: 800; }
.f-stat span { color: var(--c-text-2); font-size: 14px; font-weight: 600; margin-left: 4px; }
.bar { height: 12px; border-radius: 999px; background: var(--c-line); overflow: hidden; }
.bar i { display: block; height: 100%; border-radius: inherit; background: var(--c-primary); transition: width var(--dur-3) var(--ease-out); }
.f-meta { color: var(--c-text-2); font-size: 13px; margin: 0 0 4px; }
.f-go { margin-top: 2px; }

.other h2 { font-size: 17px; color: var(--c-text); margin: 0 0 4px 4px; display: flex; align-items: center; gap: 8px; }
.other h2::before { content: ""; width: 6px; height: 18px; border-radius: 3px; background: var(--c-primary); }
.other-hint { color: var(--c-text-2); font-size: 13px; margin: 0 0 10px 18px; }
.soon-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
.soon-card {
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  min-height: 68px; padding: 12px 18px;
  border: 1.5px dashed var(--c-line-strong); border-radius: var(--r-btn);
  background: var(--c-mint-bg); color: var(--c-text-2);
}
.soon-card b { font-size: 19px; color: var(--c-text-2); }
.soon-card span { font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: var(--c-surface); }

@media (max-width: 520px) {
  .featured { padding: 16px; gap: 16px; }
  .f-grade b { font-size: 32px; }
  .f-side { min-width: 100%; }
}
</style>
