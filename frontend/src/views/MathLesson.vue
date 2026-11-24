<template>
  <main class="page">
    <BackButton :to="backTo" :label="`返回${book?.gradeName ?? ''}课程`" />

    <LoadingBlock v-if="loading" />
    <EmptyState v-else-if="!lesson || !book" title="没有找到这节课" desc="回到课程目录重新选择。">
      <template #action>
        <n-button type="primary" @click="router.push('/math')">返回课程</n-button>
      </template>
    </EmptyState>
    <template v-else>
      <header class="head">
        <span class="hno tnum">{{ lesson.no }}</span>
        <div class="htxt">
          <h1>{{ lesson.title }}</h1>
          <div class="meta">
            <span class="grade">{{ book.gradeName }}</span>
            <span v-if="lesson.tag" class="tag">{{ lesson.tag }}</span>
            <span class="grp">{{ lesson.group }}</span>
          </div>
        </div>
      </header>

      <MathPlayer
        v-if="src"
        ref="player"
        :key="lesson.id"
        :lesson-id="lesson.id"
        :src="src"
        :start-at="startAt"
        @save="onSave"
      />
      <div v-else class="card empty">
        {{ mediaError || "视频加载中…" }}
      </div>

      <p class="hint">
        <n-icon :component="TvOutline" size="16" />
        iPad 上用 Safari 打开，点控制条上的「投屏」即可选电视播放；投屏后倍速以电视为准。
      </p>

      <div v-if="done" class="donebar">
        <n-icon :component="CheckmarkCircleOutline" size="22" class="d-ico" />
        <b>这一节学完了</b>
        <span v-if="next" class="d-sub">接着学下一节吧</span>
        <span v-else class="d-sub">这个年级的课都学完了，厉害！</span>
        <n-button v-if="next" type="primary" class="d-go" @click="go(next.id)">下一节</n-button>
      </div>

      <div class="nav">
        <n-button v-if="prev" secondary size="large" @click="go(prev.id)">
          上一节 · {{ prev.no }}
        </n-button>
        <span v-else></span>
        <n-button quaternary size="large" @click="restart">从头看</n-button>
        <n-button v-if="next" secondary size="large" @click="go(next.id)">
          下一节 · {{ next.no }}
        </n-button>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NIcon } from "naive-ui";
import { CheckmarkCircleOutline, TvOutline } from "@vicons/ionicons5";
import BackButton from "../components/BackButton.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import EmptyState from "../components/EmptyState.vue";
import MathPlayer from "../components/MathPlayer.vue";
import {
  findBook, isDone, lessonKey, loadMath, videoUrl,
  type MathBook, type MathData, type MathLesson,
} from "../core/math";
import { mediaToken } from "../core/mediaToken";
import { useLearningStore } from "../stores/learning";

const route = useRoute();
const router = useRouter();
const learning = useLearningStore();
const data = ref<MathData | null>(null);
const loading = ref(true);
const player = ref<InstanceType<typeof MathPlayer> | null>(null);

const bookId = computed(() => String(route.params.bookId ?? ""));
const book = computed<MathBook | null>(() =>
  data.value ? findBook(data.value.books, bookId.value) : null,
);
const lessons = computed<MathLesson[]>(() => book.value?.lessons ?? []);
const index = computed(() =>
  lessons.value.findIndex((l) => l.id === String(route.params.lessonId)),
);
const lesson = computed<MathLesson | null>(() => lessons.value[index.value] ?? null);
const prev = computed<MathLesson | null>(() => lessons.value[index.value - 1] ?? null);
const next = computed<MathLesson | null>(() => lessons.value[index.value + 1] ?? null);
const backTo = computed(() => `/math/books/${encodeURIComponent(bookId.value)}`);

const rec = computed(() => {
  const l = lesson.value;
  return l ? learning.progressOf(lessonKey(l.id)) : null;
});
const done = computed(() => isDone(rec.value));
/** 学完从头放；没学完从上次位置续播 */
const startAt = computed(() => (done.value ? 0 : rec.value?.idx ?? 0));
/** 视频必须是登录用户：先换取短时效媒体令牌，再拼进 src（AirPlay 也能取流） */
const token = ref("");
const mediaError = ref("");
const src = computed(() =>
  lesson.value && book.value && token.value
    ? videoUrl(book.value.mediaDir, lesson.value.file, token.value)
    : "",
);

function onSave(id: string, seconds: number, wasDone: boolean): void {
  learning.recordVideoProgress(lessonKey(id), seconds, wasDone);
}
function go(id: string): void {
  void router.push(`/math/books/${encodeURIComponent(bookId.value)}/${encodeURIComponent(id)}`);
}
function restart(): void {
  player.value?.restart();
}

onMounted(async () => {
  try {
    data.value = await loadMath();
    try {
      token.value = await mediaToken();
    } catch {
      mediaError.value = "视频加载需要登录，请重新登录后再试。";
    }
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page { width: 100%; }
.card { background: var(--c-surface); border: 1px solid var(--c-line); border-radius: var(--r-card); box-shadow: var(--shadow-card); }
.empty { padding: 40px 20px; text-align: center; color: var(--c-text-2); }
.empty p { margin: 0 0 14px; }

.head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.hno {
  flex: none; width: 54px; height: 54px; border-radius: 14px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  font-size: 19px; font-weight: 800;
}
.htxt { min-width: 0; }
h1 { color: var(--c-text); font-size: var(--fs-title); margin: 0 0 4px; line-height: 1.3; }
.meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.grade {
  font-size: 12px; font-weight: 800; padding: 2px 10px; border-radius: 999px;
  background: var(--c-primary); color: #fff;
}
.tag {
  font-size: 12px; font-weight: 700; padding: 2px 9px; border-radius: 999px;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
}
.grp { color: var(--c-text-2); font-size: 13px; }

.hint {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  color: var(--c-text-2); font-size: 13px; margin: 12px 2px 0;
}
.donebar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin-top: 14px; padding: 12px 16px; border-radius: var(--r-btn);
  background: var(--c-primary-soft); color: var(--c-text);
}
.d-ico { color: var(--c-primary-strong); }
.d-sub { color: var(--c-text-2); font-size: var(--fs-sub); }
.d-go { margin-left: auto; }
.nav { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-top: 16px; flex-wrap: wrap; }

@media (max-width: 520px) {
  .hno { width: 46px; height: 46px; font-size: 16px; }
  h1 { font-size: 19px; }
  .nav { justify-content: center; }
}
</style>
