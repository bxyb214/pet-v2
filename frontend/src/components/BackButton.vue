<template>
  <button type="button" class="back-btn" @click="go">
    <span class="arrow" aria-hidden="true">←</span>
    <span>{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const props = withDefaults(defineProps<{ to?: string; label?: string }>(), {
  to: "/english/speak",
  label: "返回口语",
});
const router = useRouter();

function go(): void {
  void router.push(props.to);
}
</script>

<style scoped>
/* iPad / 触屏优先：大点击区、高对比、阴影，避免小文字链接难点 */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 10px 20px 10px 16px;
  margin: 0 0 16px;
  background: var(--c-surface);
  color: var(--c-primary-strong);
  border: 1.5px solid var(--c-primary);
  border-radius: 999px;
  box-shadow: var(--shadow-1);
  font: inherit;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
  transition: background var(--dur-2) var(--ease-out), transform var(--dur-1) var(--ease-out),
    box-shadow var(--dur-2) var(--ease-out);
}
.back-btn:hover { background: var(--c-primary-soft); box-shadow: var(--shadow-2); }
.back-btn:active { transform: scale(0.97); }
.back-btn:focus-visible { outline: 3px solid color-mix(in srgb, var(--c-primary) 45%, transparent); outline-offset: 2px; }
.arrow { font-size: 20px; line-height: 1; }

/* 平板（iPad）再放大一档，手指点得准 */
@media (min-width: 768px), (pointer: coarse) {
  .back-btn { min-height: 54px; padding: 12px 24px 12px 18px; font-size: 17px; }
  .arrow { font-size: 22px; }
}
</style>
