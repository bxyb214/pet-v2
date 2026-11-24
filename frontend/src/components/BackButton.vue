<template>
  <button
    type="button"
    class="back-btn"
    :class="variant"
    @click="go"
  >
    <svg class="arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M14.5 5 7.5 12l7 7" />
    </svg>
    <span>{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useDialog } from "naive-ui";

/**
 * 统一返回控件：
 * - pill：详情页首行，48/54px；
 * - text：沉浸页工具条、结算页、设置页，44px 高但视觉更轻；
 * - confirm：离开会丢进度时传入提示文案，点击先二次确认。
 * 目标固定写在 to 上，不依赖浏览器 history。
 */
const props = withDefaults(defineProps<{
  to: string;
  label: string;
  variant?: "pill" | "text";
  confirm?: string;
}>(), { variant: "pill" });

const router = useRouter();
const dialog = useDialog();

function leave(): void {
  void router.push(props.to);
}

function go(): void {
  if (!props.confirm) {
    leave();
    return;
  }
  dialog.warning({
    title: "确定离开？",
    content: props.confirm,
    positiveText: "退出",
    negativeText: "继续",
    onPositiveClick: leave,
  });
}
</script>

<style scoped>
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
.arrow { width: 20px; height: 20px; flex: none; }

/* 轻量形态：不占版面，但保留 44px 触控高度 */
.back-btn.text {
  gap: 2px;
  min-height: 44px;
  padding: 6px 12px 6px 4px;
  margin: 0;
  background: transparent;
  border-color: transparent;
  border-radius: var(--r-sm);
  box-shadow: none;
  font-size: 15px;
}
.back-btn.text .arrow { width: 18px; height: 18px; }
.back-btn.text:hover { background: var(--c-primary-soft); box-shadow: none; }
.back-btn.text:active { transform: none; }

/* 平板（iPad）再放大一档，手指点得准 */
@media (min-width: 768px), (pointer: coarse) {
  .back-btn.pill { min-height: 54px; padding: 12px 24px 12px 18px; font-size: 17px; }
  .back-btn.pill .arrow { width: 22px; height: 22px; }
}
</style>
