<template>
  <div class="card" :class="{ flipped }">
    <template v-if="!flipped">
      <p class="word">{{ word.en }}</p>
      <p v-if="word.phonetic && !word.alt" class="phon">{{ word.phonetic }}</p>
      <button type="button" class="flipbtn" @click="flipped = true">
        {{ word.alt ? "看同义说法" : "看释义" }}
      </button>
      <button v-if="word.en" type="button" class="audio" aria-label="听发音" :disabled="audioPending(word.en)" @click="play">
        <span v-if="audioPending(word.en)" class="audio-spin" aria-hidden="true" />
        <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" />
          <path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" />
        </svg>
      </button>
    </template>
    <template v-else>
      <!-- 同义替换库：两个同义英文短语成对，中文只作辅助 -->
      <div v-if="word.alt" class="synpair">
        <p class="syn-line">
          <span class="syn-tag">原短语</span>
          <span class="syn-en">{{ word.en }}</span>
          <button type="button" class="exsay" aria-label="听原短语" :disabled="audioPending(word.en)" @click.stop="play">
            <span v-if="audioPending(word.en)" class="audio-spin" aria-hidden="true" />听
          </button>
        </p>
        <p class="syn-line">
          <span class="syn-tag alt">同义</span>
          <span class="syn-alt">{{ word.alt }}</span>
          <button type="button" class="exsay" aria-label="听同义说法" :disabled="audioPending(String(word.alt))" @click.stop="sayAlt">
            <span v-if="audioPending(String(word.alt))" class="audio-spin" aria-hidden="true" />听
          </button>
        </p>
        <p v-if="synCn" class="syn-cn">{{ synCn }}</p>
      </div>
      <div v-else class="cnrow">
        <p class="cn">{{ word.cn || "（暂无释义）" }}</p>
        <button v-if="word.en" type="button" class="sayword" :disabled="audioPending(word.en)" @click="play">
          <span v-if="audioPending(word.en)" class="audio-spin" aria-hidden="true" />
          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" />
            <path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" />
          </svg>
          听单词
        </button>
      </div>
      <p v-if="!word.alt" class="meta">
        <span v-if="word.pos" class="pos">{{ word.pos }}</span>
        <span class="en">{{ word.en }}</span>
      </p>
      <p v-if="word.example" class="ex">
        {{ word.example }}
        <button type="button" class="exsay" aria-label="听整句" :disabled="audioPending(String(word.example))" @click.stop="sayExample">
          <span v-if="audioPending(String(word.example))" class="audio-spin" aria-hidden="true" />听整句
        </button>
      </p>
      <button type="button" class="flipbtn" @click="flipped = false">翻回英文</button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { PlanWord } from "../core/plan";
import { englishOnly, audioPending, playWordAudio, say } from "../core/say";

const props = defineProps<{ word: PlanWord }>();
const flipped = ref(false);

/** 同义库两个短语的中文释义（相同则只显示一次） */
const synCn = computed(() => {
  const parts = [props.word.cn, props.word.alt_cn]
    .map((s) => String(s ?? "").trim())
    .filter(Boolean);
  return [...new Set(parts)].join("；");
});

function play(): void {
  // 必须在点击事件里同步朗读：iOS Safari 只认手势内的 speechSynthesis 调用
  playWordAudio(props.word.en);
}
function sayExample(): void {
  const text = englishOnly(String(props.word.example ?? ""));
  if (text) say(text);
}
function sayAlt(): void {
  const text = englishOnly(String(props.word.alt ?? ""));
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
  text-align: center;
  transition: border-color var(--dur-2) var(--ease-out), background var(--dur-2) var(--ease-out);
}
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
.cnrow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}
.cn {
  margin: 0;
  font-size: clamp(20px, 4vw, 26px);
  font-weight: 700;
  line-height: 1.5;
  color: var(--c-text);
  word-break: break-word;
  overflow-wrap: anywhere;
}
.sayword {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 11px;
  border: 1px solid #bfe3d1;
  border-radius: var(--r-pill);
  background: var(--c-primary-soft);
  color: var(--c-primary-strong);
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.sayword:hover { background: #dff5e9; }
.flipbtn {
  margin-top: 22px;
  padding: 9px 24px;
  border: 1px solid #bfe3d1;
  border-radius: var(--r-pill);
  background: var(--c-primary-soft);
  color: var(--c-primary-strong);
  font: inherit;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  transition: background var(--dur-2) var(--ease-out), border-color var(--dur-2) var(--ease-out);
}
.flipbtn:hover { background: #dff5e9; border-color: #a9dcc0; }
.flipbtn:focus-visible { outline: 2px solid var(--c-primary); outline-offset: 2px; }
.meta { margin: 12px 0 0; display: flex; gap: 8px; align-items: baseline; justify-content: center; flex-wrap: wrap; }
.pos { font-size: 12px; font-weight: 700; color: var(--c-accent); }
.en { font-family: var(--font-word); font-size: 15px; color: var(--c-text-2); }
.synpair {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 620px;
}
.syn-line {
  margin: 0;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 9px;
  flex-wrap: wrap;
}
.syn-tag {
  flex: 0 0 auto;
  padding: 1px 8px;
  border: 1px solid var(--c-line);
  border-radius: var(--r-pill);
  font-size: 11px;
  font-weight: 800;
  color: var(--c-text-3);
}
.syn-tag.alt {
  color: var(--c-primary-strong);
  border-color: #bfe3d1;
  background: var(--c-primary-soft);
}
.syn-en {
  font-family: var(--font-word);
  font-size: clamp(18px, 3.4vw, 24px);
  font-weight: 700;
  line-height: 1.45;
  color: var(--c-text);
  word-break: break-word;
  overflow-wrap: anywhere;
}
.syn-alt {
  font-family: var(--font-word);
  font-size: clamp(22px, 4.2vw, 30px);
  font-weight: 800;
  line-height: 1.4;
  color: var(--c-primary-strong);
  word-break: break-word;
  overflow-wrap: anywhere;
}
.syn-cn {
  margin: 2px 0 0;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.6;
  color: var(--c-text-2);
}
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
