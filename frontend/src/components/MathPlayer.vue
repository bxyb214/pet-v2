<template>
  <div ref="box" class="player-wrap">
    <div class="player">
      <video
        ref="video"
        class="video"
        :src="src"
        playsinline
        webkit-playsinline
        x-webkit-airplay="allow"
        preload="metadata"
        @loadedmetadata="onMeta"
        @timeupdate="onTime"
        @play="playing = true"
        @pause="onPause"
        @ended="markDone"
        @error="onError"
        @click="toggle"
      ></video>

      <button
        v-if="!playing && !errorMsg" type="button" class="bigplay"
        aria-label="播放" @click="toggle"
      >
        <n-icon :component="PlayOutline" size="34" />
      </button>

      <div v-if="errorMsg" class="verr">{{ errorMsg }}</div>
    </div>

    <div class="controls">
      <button
        type="button" class="playbtn"
        :aria-label="playing ? '暂停' : '播放'" @click="toggle"
      >
        <n-icon :component="playing ? PauseOutline : PlayOutline" size="22" />
        <span class="playtxt">{{ playing ? "暂停" : "播放" }}</span>
      </button>

      <span class="time tnum">{{ formatTime(current) }} / {{ formatTime(duration) }}</span>

      <n-slider
        class="seek"
        :value="current"
        :max="duration || 1"
        :step="1"
        :tooltip="false"
        :disabled="!duration"
        @update:value="seek"
      />

      <div class="rates" role="group" aria-label="倍速">
        <button
          v-for="r in SPEEDS" :key="r" type="button" class="rate"
          :class="{ on: rate === r }" :aria-pressed="rate === r" @click="setRate(r)"
        >{{ r }}x</button>
      </div>

      <button v-if="castSupported" type="button" class="tool" title="投屏到电视" @click="cast">
        <n-icon :component="TvOutline" size="20" /><span class="tool-txt">投屏</span>
      </button>
      <button type="button" class="tool" aria-label="全屏" title="全屏" @click="fullscreen">
        <n-icon :component="ExpandOutline" size="20" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { NIcon, NSlider } from "naive-ui";
import { ExpandOutline, PauseOutline, PlayOutline, TvOutline } from "@vicons/ionicons5";
import { formatTime, SPEEDS } from "../core/math";

const props = defineProps<{
  /** 稳定标识：离开页面/切课时用它写进度，避免拿错当前课 */
  lessonId: string;
  src: string;
  /** 上次看到的位置（秒）；学完传 0 */
  startAt: number;
}>();

const emit = defineEmits<{
  (e: "save", lessonId: string, seconds: number, done: boolean): void;
  (e: "ended"): void;
}>();

const RATE_KEY = "pet_math_rate";
const video = ref<HTMLVideoElement | null>(null);
const box = ref<HTMLElement | null>(null);
const playing = ref(false);
const current = ref(0);
const duration = ref(0);
const errorMsg = ref("");
const castSupported = ref(false);
const rate = ref(readRate());

let lastEmit = 0;
let doneEmitted = false;

type CastVideo = HTMLVideoElement & {
  webkitShowPlaybackTargetPicker?: () => void;
  webkitEnterFullscreen?: () => void;
  remote?: { prompt?: () => Promise<void> };
};

function readRate(): number {
  const n = Number(localStorage.getItem(RATE_KEY));
  return SPEEDS.includes(n as (typeof SPEEDS)[number]) ? n : 1;
}

function onMeta(): void {
  const v = video.value;
  if (!v) return;
  duration.value = Number.isFinite(v.duration) ? v.duration : 0;
  v.playbackRate = rate.value;
  // 续播：离开头和结尾都还有距离才跳，避免一打开就"学完"
  if (props.startAt > 10 && duration.value && props.startAt < duration.value - 10) {
    v.currentTime = props.startAt;
  }
  current.value = v.currentTime;
}

function onTime(): void {
  const v = video.value;
  if (!v) return;
  current.value = v.currentTime;
  if (!duration.value || !Number.isFinite(v.duration)) duration.value = v.duration || 0;
  // 兜底：个别环境 ended 不触发；只在"正在播放"且到结尾时算，避免拖动进度条直接完成
  if (!v.paused && duration.value && v.currentTime >= duration.value - 0.5) markDone();
  if (Date.now() - lastEmit > 15000) {
    lastEmit = Date.now();
    emit("save", props.lessonId, v.currentTime, false);
  }
}

function markDone(): void {
  if (doneEmitted) return;
  const v = video.value;
  if (!v) return;
  doneEmitted = true;
  emit("save", props.lessonId, duration.value || v.currentTime, true);
  emit("ended");
}

function onPause(): void {
  playing.value = false;
  const v = video.value;
  if (v && v.currentTime > 0) emit("save", props.lessonId, v.currentTime, false);
}

function toggle(): void {
  const v = video.value;
  if (!v) return;
  if (v.paused) {
    void v.play().catch(() => {
      errorMsg.value = "无法开始播放，请检查网络后再试。";
    });
  } else {
    v.pause();
  }
}

function seek(raw: number | number[]): void {
  const sec = Array.isArray(raw) ? raw[0] : raw;
  const v = video.value;
  if (!v || !Number.isFinite(sec)) return;
  v.currentTime = sec;
  current.value = sec;
}

function setRate(r: number): void {
  rate.value = r;
  localStorage.setItem(RATE_KEY, String(r));
  if (video.value) video.value.playbackRate = r;
}

function onError(): void {
  errorMsg.value = "视频加载失败：请检查网络，或稍后再试。";
}

async function cast(): Promise<void> {
  const v = video.value as CastVideo | null;
  if (!v) return;
  if (typeof v.webkitShowPlaybackTargetPicker === "function") {
    v.webkitShowPlaybackTargetPicker();
    return;
  }
  if (v.remote?.prompt) {
    try {
      await v.remote.prompt();
    } catch {
      errorMsg.value = "没有找到可投屏的设备（请确认电视与 iPad 在同一网络）。";
    }
  }
}

async function fullscreen(): Promise<void> {
  const el = box.value;
  if (!el) return;
  if (document.fullscreenElement) {
    await document.exitFullscreen();
    return;
  }
  try {
    await el.requestFullscreen();
  } catch {
    // iOS Safari 不支持容器全屏，回退原生视频全屏（控件交给系统）
    (video.value as CastVideo | null)?.webkitEnterFullscreen?.();
  }
}

/** 从头开始（父组件「从头看」调用） */
function restart(): void {
  doneEmitted = false;
  errorMsg.value = "";
  const v = video.value;
  if (!v) return;
  v.currentTime = 0;
  current.value = 0;
  void v.play().catch(() => { /* 用户可再点播放 */ });
}

defineExpose({ restart });

function saveOnHide(): void {
  if (document.visibilityState !== "hidden") return;
  const v = video.value;
  if (v && v.currentTime > 0) emit("save", props.lessonId, v.currentTime, false);
}

onMounted(() => {
  const v = video.value as CastVideo | null;
  castSupported.value = !!v && (
    typeof v.webkitShowPlaybackTargetPicker === "function" || !!v.remote?.prompt
  );
  document.addEventListener("visibilitychange", saveOnHide);
});

onBeforeUnmount(() => {
  document.removeEventListener("visibilitychange", saveOnHide);
  const v = video.value;
  if (v && v.currentTime > 0) emit("save", props.lessonId, v.currentTime, false);
});
</script>

<style scoped>
.player-wrap { width: 100%; }
.player {
  position: relative; width: 100%; aspect-ratio: 16 / 9; overflow: hidden;
  background: var(--c-text); border-radius: var(--r-card) var(--r-card) 0 0;
}
.video { display: block; width: 100%; height: 100%; object-fit: contain; background: var(--c-text); }
.bigplay {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  width: 78px; height: 78px; border-radius: 50%; border: 0; cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--c-surface); color: var(--c-primary-strong);
  box-shadow: var(--shadow-3); transition: transform var(--dur-2) var(--ease-out);
}
.bigplay:hover { transform: translate(-50%, -50%) scale(1.05); }
.verr {
  position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
  color: var(--c-surface); font-size: var(--fs-body); text-align: center; padding: 20px;
}

.controls {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 14px; background: var(--c-surface);
  border: 1px solid var(--c-line); border-top: 0;
  border-radius: 0 0 var(--r-card) var(--r-card);
}
.playbtn {
  display: inline-flex; align-items: center; gap: 6px; min-height: 44px; padding: 0 14px;
  border: 0; border-radius: var(--r-btn); cursor: pointer;
  background: var(--c-primary-strong); color: #fff; font: inherit; font-weight: 700;
}
.playtxt { font-size: 14px; }
.time { color: var(--c-text-2); font-size: 13px; flex: none; }
.seek { flex: 1 1 180px; min-width: 120px; }
.rates { display: flex; gap: 4px; }
.rate {
  min-width: 48px; min-height: 40px; padding: 0 8px; cursor: pointer;
  border: 1px solid var(--c-line-strong); border-radius: 999px;
  background: var(--c-surface); color: var(--c-text-2);
  font: inherit; font-size: 13px; font-weight: 700;
  transition: all var(--dur-1) var(--ease-out);
}
.rate.on { background: var(--c-primary-soft); border-color: var(--c-primary); color: var(--c-primary-strong); }
.tool {
  display: inline-flex; align-items: center; gap: 4px; min-height: 40px; padding: 0 10px;
  border: 1px solid var(--c-line); border-radius: var(--r-btn);
  background: var(--c-surface); color: var(--c-text-2); cursor: pointer; font: inherit;
}
.tool:hover { color: var(--c-primary-strong); border-color: var(--c-primary); }
.tool-txt { font-size: 13px; font-weight: 700; }

@media (max-width: 520px) {
  .playtxt { display: none; }
  .controls { gap: 8px; padding: 8px 10px; }
  .seek { flex-basis: 100%; order: 5; }
  .tool-txt { display: none; }
}
</style>
