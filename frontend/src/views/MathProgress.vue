<template>
  <main class="page">
    <h1>学习进度</h1>
    <p class="sub">看完整节才算学完；进度会跟账号同步，换设备也能接着学。</p>

    <div v-if="loading" class="card empty">加载中…</div>
    <div v-else-if="!series" class="card empty">暂时没有课程</div>
    <template v-else>
      <div class="card stats">
        <div class="stat done">
          <b class="tnum">{{ stat.done }}</b><span>已学完</span>
        </div>
        <div class="stat watching">
          <b class="tnum">{{ stat.watching }}</b><span>学习中</span>
        </div>
        <div class="stat todo">
          <b class="tnum">{{ stat.todo }}</b><span>还没开始</span>
        </div>
        <div class="bar-box">
          <div class="bar" role="progressbar" :aria-valuenow="stat.percent" aria-valuemin="0" aria-valuemax="100">
            <i :style="{ width: stat.percent + '%' }"></i>
          </div>
          <div class="bar-meta">
            共 {{ stat.total }} 节，完成 {{ stat.percent }}%
            <n-button v-if="next" type="primary" size="small" class="cont" @click="open(next)">
              继续学
            </n-button>
            <n-button v-else type="primary" size="small" class="cont" @click="open(lessons[0])">
              再学一遍
            </n-button>
          </div>
        </div>
      </div>

      <section class="card wallcard">
        <h2>进度墙</h2>
        <p class="wallhint">13 格对应 13 节课，绿色 = 学完，橙色 = 学到一半。</p>
        <div class="wall">
          <button
            v-for="l in lessons" :key="l.id" type="button"
            class="tile" :class="statusOf(recOf(l.id))" @click="open(l)"
            :aria-label="`${l.no} ${l.title} ${statusLabel(l.id)}`"
          >
            <span class="t-no tnum">{{ l.no }}</span>
            <span class="t-ico">
              <n-icon v-if="statusOf(recOf(l.id)) === 'done'" :component="CheckmarkCircleOutline" size="18" />
              <span v-else-if="statusOf(recOf(l.id)) === 'watching'" class="dot"></span>
            </span>
            <span class="t-title">{{ l.title }}</span>
            <span class="t-state">{{ statusLabel(l.id) }}</span>
          </button>
        </div>
      </section>

      <section class="card watchingcard">
        <h2>正在学</h2>
        <p v-if="!watching.length" class="wallhint">
          {{ stat.total && stat.done === stat.total ? "全部学完了，太棒了！" : "还没有学到一半的课，去挑一节开始吧。" }}
        </p>
        <div v-else class="wlist">
          <button
            v-for="l in watching" :key="l.id" type="button"
            class="wrow" @click="open(l)"
          >
            <span class="w-no tnum">{{ l.no }}</span>
            <span class="w-txt">
              <b>{{ l.title }}</b>
              <i>上次看到 {{ formatTime(recOf(l.id)?.idx ?? 0) }}</i>
            </span>
            <span class="w-go">继续</span>
            <n-icon :component="ChevronForwardOutline" size="18" class="chev" />
          </button>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NIcon } from "naive-ui";
import { CheckmarkCircleOutline, ChevronForwardOutline } from "@vicons/ionicons5";
import {
  formatTime, lessonKey, loadMath, nextLesson, seriesProgress, statusOf,
  type MathData, type MathLesson, type VideoRec,
} from "../core/math";
import { useLearningStore } from "../stores/learning";

const router = useRouter();
const learning = useLearningStore();
const data = ref<MathData | null>(null);
const loading = ref(true);

const series = computed(() => data.value?.series[0] ?? null);
const lessons = computed<MathLesson[]>(() => series.value?.lessons ?? []);

function recOf(id: string): VideoRec | null {
  return learning.progressOf(lessonKey(id));
}
const stat = computed(() => seriesProgress(lessons.value, recOf));
const next = computed(() => nextLesson(lessons.value, recOf));
const watching = computed(() => lessons.value.filter((l) => statusOf(recOf(l.id)) === "watching"));

function statusLabel(id: string): string {
  const st = statusOf(recOf(id));
  if (st === "done") return "已学完";
  if (st === "watching") return "学到一半";
  return "还没看";
}
function open(l: MathLesson): void {
  void router.push(`/math/lessons/${encodeURIComponent(l.id)}`);
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
.card { background: var(--c-surface); border: 1px solid var(--c-line); border-radius: var(--r-card); box-shadow: var(--shadow-card); }
.empty { padding: 32px 16px; text-align: center; color: var(--c-text-2); }

.stats { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; padding: 16px 20px; margin-bottom: 16px; }
.stat { display: flex; flex-direction: column; align-items: center; min-width: 76px; }
.stat b { font-size: 26px; line-height: 1.15; }
.stat span { font-size: 12px; font-weight: 600; }
.stat.done b { color: var(--c-primary-strong); }
.stat.watching b { color: var(--c-accent); }
.stat.todo b { color: var(--c-text-2); }
.bar-box { flex: 1; min-width: 200px; }
.bar { height: 12px; border-radius: 999px; background: var(--c-line); overflow: hidden; }
.bar i { display: block; height: 100%; border-radius: inherit; background: var(--c-primary); transition: width var(--dur-3) var(--ease-out); }
.bar-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; color: var(--c-text-2); font-size: var(--fs-sub); margin-top: 8px; }
.cont { margin-left: auto; }

.wallcard { padding: 16px 18px; margin-bottom: 16px; }
.wallcard h2, .watchingcard h2 { font-size: 17px; color: var(--c-text); margin: 0 0 4px; }
.wallhint { color: var(--c-text-2); font-size: 13px; margin: 0 0 12px; }
.wall { display: grid; grid-template-columns: repeat(auto-fill, minmax(104px, 1fr)); gap: 10px; }
.tile {
  position: relative; display: flex; flex-direction: column; align-items: flex-start; gap: 4px;
  min-height: 96px; padding: 10px 12px; text-align: left;
  border: 1.5px solid var(--c-line); border-radius: var(--r-btn);
  background: var(--c-surface); color: var(--c-text); cursor: pointer; font: inherit;
  transition: transform var(--dur-1) var(--ease-out), border-color var(--dur-2) var(--ease-out);
}
.tile:hover { transform: translateY(-1px); border-color: var(--c-primary); }
.tile.done { background: var(--c-primary-soft); border-color: var(--c-primary); }
.tile.watching { background: var(--c-accent-soft); border-color: var(--c-accent); }
.t-no { font-size: 19px; font-weight: 800; color: var(--c-primary-strong); }
.tile.watching .t-no { color: var(--c-accent); }
.t-ico { position: absolute; right: 8px; top: 8px; color: var(--c-primary-strong); }
.dot { display: block; width: 9px; height: 9px; border-radius: 50%; background: var(--c-accent); }
.t-title { font-size: 12px; font-weight: 600; line-height: 1.35; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.t-state { margin-top: auto; font-size: 11px; color: var(--c-text-2); font-weight: 700; }
.tile.done .t-state { color: var(--c-primary-strong); }
.tile.watching .t-state { color: var(--c-accent); }

.watchingcard { padding: 16px 18px; }
.wlist { display: flex; flex-direction: column; gap: 8px; }
.wrow {
  display: flex; align-items: center; gap: 10px; width: 100%; min-height: 56px;
  padding: 8px 12px; text-align: left; font: inherit; color: var(--c-text); cursor: pointer;
  background: var(--c-mint-bg); border: 1px solid var(--c-line); border-radius: var(--r-btn);
}
.wrow:hover { border-color: var(--c-primary); }
.w-no {
  flex: none; width: 38px; height: 38px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--c-surface); color: var(--c-accent); font-weight: 800;
}
.w-txt { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.w-txt b { font-size: 15px; }
.w-txt i { font-style: normal; font-size: 12px; color: var(--c-text-2); }
.w-go { color: var(--c-primary-strong); font-weight: 700; font-size: 13px; }
.chev { color: var(--c-text-3); }

@media (max-width: 520px) {
  .stats { gap: 10px; padding: 14px; }
  .stat { min-width: 60px; }
  .stat b { font-size: 22px; }
  .bar-box { flex-basis: 100%; }
  .wall { grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); }
}
</style>
