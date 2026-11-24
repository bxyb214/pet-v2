<template>
  <div class="empty-state" :class="{ plain }">
    <p class="es-title">{{ title }}</p>
    <p v-if="desc" class="es-desc">{{ desc }}</p>
    <div v-if="$slots.action" class="es-action"><slot name="action" /></div>
  </div>
</template>

<script setup lang="ts">
/**
 * 全站统一的空态：一句说明 + 最多一个主动作。
 * plain 用于嵌在已有卡片里（不再叠一层卡片）。
 */
withDefaults(defineProps<{ title: string; desc?: string; plain?: boolean }>(), {
  desc: "",
  plain: false,
});
</script>

<style scoped>
.empty-state {
  background: var(--c-surface);
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  padding: 32px 20px;
  text-align: center;
}
.empty-state.plain {
  background: none;
  border: 0;
  box-shadow: none;
  padding: 24px 0;
}
.es-title {
  margin: 0;
  font-size: var(--fs-title);
  font-weight: 800;
  color: var(--c-text);
}
.es-desc {
  margin: 8px 0 0;
  font-size: var(--fs-sub);
  color: var(--c-text-2);
  line-height: 1.7;
}
.es-action { margin-top: 18px; }
</style>
