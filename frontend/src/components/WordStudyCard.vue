<template>
  <div class="card" :class="{ flipped }" role="button" tabindex="0" @click="flipped = !flipped" @keydown.enter.prevent="flipped = !flipped" @keydown.space.prevent="flipped = !flipped">
    <template v-if="!flipped">
      <p class="word">{{ word.en }}</p>
      <p v-if="word.phonetic" class="phon">{{ word.phonetic }}</p>
      <p class="hint">点击翻面看释义</p>
    </template>
    <template v-else>
      <p class="cn">{{ word.cn || "（暂无释义）" }}</p>
      <p class="meta">
        <span v-if="word.pos" class="pos">{{ word.pos }}</span>
        <span class="en">{{ word.en }}</span>
      </p>
      <p v-if="word.example" class="ex">
        {{ word.example }}
        <button type="button" class="exsay" aria-label="听整句" @click.stop="sayExample">听整句</button>
      </p>
      <p class="hint">点击翻回英文</p>
    </template>

    <button v-if="word.en" type="button" class="audio" aria-label="听发音" @click.stop="play">
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" />
        <path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { PlanWord } from "../core/plan";
import { englishOnly, playWordAudio, say } from "../core/say";

const props = defineProps<{ word: PlanWord }>();
const flipped = ref(false);

function play(): void {
  // 必须在点击事件里同步朗读：iOS Safari 只认手势内的 speechSynthesis 调用
  playWordAudio(props.word.en);
}
function sayExample(): void {
  const text = englishOnly(String(props.word.example ?? ""));
  if (text) say(text);
}
</script>

<style scoped>
.card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 230px;
  padding: 34px 24px 30px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  background: var(--c-card);
  box-shadow: var(--shadow-1);
  cursor: pointer;
  text-align: center;
  transition: border-color var(--dur-2) var(--ease-out), background var(--dur-2) var(--ease-out);
}
.card:hover { border-color: #cfeadd; }
.card:focus-visible { outline: 2px solid var(--c-primary); outline-offset: 2px; }
.word {
  margin: 0;
  font-family: var(--font-word);
  font-size: clamp(30px, 6vw, 46px);
  font-weight: 800;
  line-height: 1.25;
  color: var(--c-text);
  word-break: break-word;
  overflow-wrap: anywhere;
}
.phon { margin: 10px 0 0; font-family: var(--font-en); font-size: 14px; color: var(--c-text-3); }
.hint { margin: 20px 0 0; font-size: 12px; color: var(--c-text-3); }
.cn {
  margin: 0;
  font-size: clamp(20px, 4vw, 26px);
  font-weight: 700;
  line-height: 1.5;
  color: var(--c-text);
  word-break: break-word;
  overflow-wrap: anywhere;
}
.meta { margin: 12px 0 0; display: flex; gap: 8px; align-items: baseline; justify-content: center; flex-wrap: wrap; }
.pos { font-size: 12px; font-weight: 700; color: var(--c-accent); }
.en { font-family: var(--font-word); font-size: 15px; color: var(--c-text-2); }
.ex {
  margin: 14px 0 0;
  max-width: 560px;
  font-family: var(--font-en);
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--c-text-2);
}
.audio {
  position: absolute;
  right: 14px;
  top: 14px;
  width: 38px;
  height: 38px;
  border: 1px solid var(--c-line);
  border-radius: 50%;
  background: #fff;
  color: var(--c-primary-strong);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.audio:hover { background: var(--c-primary-soft); border-color: #cfeadd; }
.exsay { margin-left: 8px; border: 1px solid var(--c-line); background: #fff; color: var(--c-primary-strong); border-radius: var(--r-pill); padding: 3px 10px; font: inherit; font-size: 11.5px; font-weight: 700; cursor: pointer; }
.exsay:hover { background: var(--c-primary-soft); }
@media (prefers-reduced-motion: reduce) {
  .card { transition: none; }
}
</style>
