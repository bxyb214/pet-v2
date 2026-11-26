<template>
  <n-button
    :type="props.variant === 'primary' ? 'primary' : 'default'"
    :secondary="props.variant === 'secondary'"
    :quaternary="props.variant === 'quaternary'"
    size="large"
    :disabled="props.disabled"
    :class="['paid-action-btn', { 'is-locked': locked }]"
    :aria-disabled="locked || props.disabled"
    @click="onClick"
  >
    <slot />
  </n-button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NButton, useMessage } from "naive-ui";
import { paidBlocked, paidClickHint, type AiStatus } from "../core/aiStatus";

const props = withDefaults(defineProps<{
  status: AiStatus | null | undefined;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "quaternary";
}>(), { disabled: false, variant: "primary" });
const emit = defineEmits<{ (e: "click"): void }>();

const message = useMessage();
const locked = computed(() => paidBlocked(props.status));
const hint = computed(() => paidClickHint(props.status));

function onClick(): void {
  if (locked.value) {
    message.warning(hint.value, { duration: 6000 });
    return;
  }
  emit("click");
}
</script>

<style scoped>
/* 原生 disabled 不派发 click；这里用 aria-disabled + 灰色变量保留点击提示。 */
.paid-action-btn.is-locked {
  --n-color: #eef2f0 !important;
  --n-color-hover: #e8edea !important;
  --n-color-pressed: #e2e8e4 !important;
  --n-color-focus: #e8edea !important;
  --n-text-color: #8a958e !important;
  --n-text-color-hover: #7d8981 !important;
  --n-text-color-pressed: #737f77 !important;
  --n-text-color-focus: #7d8981 !important;
  --n-border: 1px solid #dce4df !important;
  --n-border-hover: 1px solid #d3ddd7 !important;
  --n-border-pressed: 1px solid #c9d4cd !important;
  --n-border-focus: 1px solid #d3ddd7 !important;
  --n-ripple-color: transparent !important;
  box-shadow: none;
  cursor: not-allowed;
}
</style>
