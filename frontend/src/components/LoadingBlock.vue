<template>
  <div class="loading-block" :class="{ plain }" role="status" aria-live="polite">{{ text }}</div>
</template>

<script setup lang="ts">
/**
 * 全站统一的加载态：默认是独立卡片；
 * 嵌在已有卡片/小节里时传 plain，只保留一行提示。
 */
withDefaults(defineProps<{ text?: string; plain?: boolean }>(), {
  text: "正在加载…",
  plain: false,
});
</script>

<style scoped>
.loading-block {
  background: var(--c-surface);
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  padding: 28px 18px;
  text-align: center;
  color: var(--c-text-2);
  font-size: var(--fs-sub);
}
.loading-block.plain {
  background: none;
  border: 0;
  box-shadow: none;
  padding: 16px 0;
}
</style>
