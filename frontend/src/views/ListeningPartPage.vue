<template>
  <main class="page">
    <BackButton to="/english/listening/home" label="返回听力" />
    <h1>{{ label }}</h1>
    <p class="sub">{{ hasSubs ? "听音频 · 对照字幕（可隐藏）· 0.8–1.2 倍速" : "听音频 · 0.8–1.2 倍速" }}</p>

    <LoadingBlock v-if="!loaded" />
    <EmptyState v-else-if="error" :title="error" plain />
    <EmptyState
      v-else-if="!test || !pt"
      title="未找到对应的听力内容"
      desc="从听力列表重新选择一个 Part。"
      plain
    />
    <template v-else>
      <!-- 播放器 -->
      <div class="player card">
        <audio
          ref="audioEl"
          :src="pt.audio"
          preload="metadata"
          @timeupdate="onTime"
          @loadedmetadata="onMeta"
          @play="playing = true"
          @pause="playing = false"
          @ended="onEnded"
        ></audio>

        <div class="p-controls">
          <button type="button" class="btn play" @click="togglePlay">{{ playing ? "⏸ 暂停" : "▶ 播放" }}</button>

          <div class="rates" role="group" aria-label="播放速度">
            <button
              v-for="r in RATES" :key="r"
              type="button"
              class="rate"
              :class="{ on: rate === r }"
              :aria-pressed="rate === r"
              @click="setRate(r)"
            >{{ r.toFixed(1) }}×</button>
          </div>

          <button
            v-if="hasSubs"
            type="button"
            class="toggle"
            :class="{ on: showSubs }"
            :aria-pressed="showSubs"
            @click="showSubs = !showSubs"
          >字幕 {{ showSubs ? "开" : "关" }}</button>
        </div>

        <div class="p-time-row">
          <span class="ptime">{{ fmtTime(cur) }}</span>
          <div class="p-bar" @click="seek($event)">
            <div class="p-fill" :style="{ width: dur ? (cur / dur) * 100 + '%' : '0%' }"></div>
          </div>
          <span class="ptime end">{{ fmtTime(dur) }}</span>
        </div>
      </div>

      <!-- 字幕：随音频高亮并自动滚动，可隐藏；无原文时整块不显示 -->
      <div v-if="hasSubs" v-show="showSubs" ref="subBox" class="sub-box card" aria-live="off">
        <div
          v-for="(s, i) in pt.sentences" :key="i"
          :data-idx="i"
          class="sub-line"
          :class="{ on: i === activeIdx }"
          @click="jump(s.t0)"
        >{{ s.text }}</div>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { activeSentenceIdx, loadListening, type LTest } from "../core/listening";
import { useAuthStore } from "../stores/auth";
import BackButton from "../components/BackButton.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import EmptyState from "../components/EmptyState.vue";

/** 需求指定的五档速度（默认 1.0） */
const RATES = [0.8, 0.9, 1.0, 1.1, 1.2];

const route = useRoute();
const auth = useAuthStore();

const test = ref<LTest | null>(null);
const partNo = ref(0);
const loaded = ref(false);
const error = ref("");
const pt = computed(() => test.value?.parts.find((p) => p.part === partNo.value) ?? null);
const hasSubs = computed(() => !!pt.value && pt.value.sentences.length > 0);
const label = computed(() =>
  test.value ? `${test.value.title} · Part ${partNo.value}${pt.value?.label ? " · " + pt.value.label : ""}` : "听力",
);

const audioEl = ref<HTMLAudioElement | null>(null);
const playing = ref(false);
const cur = ref(0);
const dur = ref(0);
const rate = ref(1.0);
const activeIdx = ref(-1);
const showSubs = ref(true);
const subBox = ref<HTMLElement | null>(null);

onMounted(async () => {
  try {
    const d = await loadListening(auth.exam);
    test.value = d.tests.find((t) => t.no === Number(route.params.testNo)) ?? null;
    partNo.value = Number(route.params.part);
  } catch {
    error.value = "听力数据加载失败";
  } finally {
    loaded.value = true;
  }
  await nextTick();
  if (audioEl.value) audioEl.value.playbackRate = rate.value;
});

/** 当前句变化时，把该行滚到字幕框中部 */
watch(activeIdx, () => {
  void scrollActiveIntoView();
});
watch(showSubs, (on) => {
  if (on) void scrollActiveIntoView();
});

async function scrollActiveIntoView(): Promise<void> {
  if (!showSubs.value || activeIdx.value < 0) return;
  await nextTick();
  const box = subBox.value;
  const line = box?.querySelector<HTMLElement>(`[data-idx="${activeIdx.value}"]`);
  if (!box || !line) return;
  const target = line.offsetTop - box.clientHeight / 2 + line.clientHeight / 2;
  box.scrollTo({ top: target, behavior: "smooth" });
}

function togglePlay(): void {
  const a = audioEl.value;
  if (!a) return;
  if (a.paused) {
    void a.play().catch(() => { playing.value = false; });
  } else {
    a.pause();
  }
}

function setRate(r: number): void {
  rate.value = r;
  if (audioEl.value) audioEl.value.playbackRate = r;
}

function onTime(): void {
  const a = audioEl.value;
  if (!a || !pt.value) return;
  cur.value = a.currentTime;
  const idx = activeSentenceIdx(pt.value.sentences, a.currentTime);
  if (idx !== activeIdx.value) activeIdx.value = idx;
}

function onMeta(): void {
  const a = audioEl.value;
  if (!a) return;
  dur.value = Number.isFinite(a.duration) ? a.duration : pt.value?.duration ?? 0;
  a.playbackRate = rate.value;
}

function onEnded(): void {
  playing.value = false;
  activeIdx.value = -1;
}

function seek(e: MouseEvent): void {
  const a = audioEl.value;
  if (!a || !dur.value) return;
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
  a.currentTime = ratio * dur.value;
}

function jump(t: number): void {
  const a = audioEl.value;
  if (!a) return;
  a.currentTime = t;
  if (a.paused) void a.play().catch(() => { playing.value = false; });
}

function fmtTime(t: number): string {
  if (!Number.isFinite(t) || t < 0) t = 0;
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); margin: 0 0 6px; }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }

.card {
  background: var(--c-surface); border: 1px solid var(--c-line);
  border-radius: var(--r-card); box-shadow: var(--shadow-card); padding: 16px;
}

.player { margin-bottom: 14px; }
.p-controls { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.btn.play { min-width: 104px; }

.rates {
  display: inline-flex; gap: 2px; padding: 3px;
  background: var(--c-mint-bg); border-radius: 999px;
}
.rate {
  border: 0; background: transparent; border-radius: 999px;
  padding: 6px 10px; min-height: 32px;
  font: inherit; font-size: 13px; font-weight: 700; color: var(--c-text-2);
  cursor: pointer; transition: background var(--dur-2) var(--ease-out), color var(--dur-2) var(--ease-out);
}
.rate:hover { color: var(--c-primary-strong); }
.rate.on { background: var(--c-primary-strong); color: #fff; }

.toggle {
  margin-left: auto; border: 1px solid var(--c-line); background: var(--c-surface);
  color: var(--c-text-2); border-radius: 999px; padding: 7px 14px;
  font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; min-height: 36px;
}
.toggle.on { background: var(--c-primary-soft); border-color: var(--c-primary); color: var(--c-primary-strong); }

.p-time-row { display: flex; align-items: center; gap: 10px; margin-top: 14px; }
.ptime { color: var(--c-text-2); font-size: var(--fs-sub); font-variant-numeric: tabular-nums; min-width: 40px; }
.ptime.end { text-align: right; }
.p-bar { flex: 1; height: 8px; background: var(--c-mint-bg); border-radius: 4px; cursor: pointer; position: relative; }
.p-fill { height: 100%; background: var(--c-primary); border-radius: 4px; }

.sub-box {
  position: relative; max-height: 320px; overflow-y: auto;
  padding: 10px 12px; overscroll-behavior: contain;
}
.sub-line {
  padding: 5px 8px; border-radius: 8px; cursor: pointer;
  color: var(--c-text-2); font-size: var(--fs-sub); line-height: 1.6;
  transition: background var(--dur-2) var(--ease-out), color var(--dur-2) var(--ease-out);
}
.sub-line:hover { background: var(--c-mint-bg); }
.sub-line.on { background: var(--c-primary-soft); color: var(--c-primary-strong); font-weight: 600; }

@media (max-width: 520px) {
  .rates { order: 3; width: 100%; justify-content: space-between; }
  .toggle { margin-left: auto; }
}
</style>
