<template>
  <div v-if="visible" class="paid-ai-notice" :class="{ prominent: props.prominent }" role="status">
    <b>{{ PAID_AI_NOT_ENABLED_TITLE }}</b>
    <span>{{ PAID_AI_NOT_ENABLED_BODY }}</span>
    <span class="free">{{ PAID_AI_FREE_TEXT }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import {
  PAID_AI_FREE_TEXT,
  PAID_AI_NOT_ENABLED_BODY,
  PAID_AI_NOT_ENABLED_TITLE,
  type AiStatus,
} from "../core/aiStatus";

const props = withDefaults(defineProps<{
  status: AiStatus | null | undefined;
  prominent?: boolean;
}>(), { prominent: false });

const visible = computed(() => !!props.status && !props.status.ai_enabled);
</script>

<style scoped>
.paid-ai-notice {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 12px;
  padding: 11px 14px;
  border: 1px solid #f0c98d;
  border-left: 4px solid var(--c-accent, #d97706);
  border-radius: var(--r-btn);
  background: var(--c-accent-soft, #fff7ed);
  color: var(--c-text-2);
  font-size: var(--fs-sub);
  line-height: 1.65;
}
.paid-ai-notice b {
  color: #b45309;
  font-size: 14.5px;
}
.paid-ai-notice .free {
  color: var(--c-primary-strong);
  font-weight: 700;
}
.paid-ai-notice.prominent {
  padding: 14px 16px;
  border-left-width: 5px;
  box-shadow: 0 6px 16px rgba(180, 83, 9, 0.08);
}
.paid-ai-notice.prominent b {
  font-size: 16px;
}
</style>
