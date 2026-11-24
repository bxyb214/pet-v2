<template>
  <div v-if="r" class="ac-test" :class="r.ok ? 'ok' : 'bad'">
    {{ r.ok ? "✓" : "✕" }} {{ r.detail }}{{ r.dev ? "（开发环境）" : "" }}
  </div>
</template>

<script setup lang="ts">
import type { TestResult } from "./types";

defineProps<{ r: TestResult | null }>();
</script>

<style scoped>
.ac-test { margin-top: 14px; padding: 9px 12px; border-radius: var(--r-sm); font-size: 12.5px; line-height: 1.6; }
.ac-test.ok { background: var(--c-primary-soft); color: var(--c-primary-strong); }
.ac-test.bad { background: var(--c-danger-soft); color: var(--c-danger); }
</style>
